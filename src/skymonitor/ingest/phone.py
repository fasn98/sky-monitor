"""Ingest adapter for smartphone sky photos (DNG RAW or JPEG) -> FITS.

Lets the downstream pipeline (calibration, cloud/trail detection) be developed and
tested with real sky images from a phone (e.g. Galaxy S24) before the all-sky camera
exists. Every output is a FITS file, the same format indi-allsky produces.

Scientific rules applied here (see CLAUDE.md):
* A value missing from EXIF is never invented: the FITS keyword is simply omitted and
  a HISTORY line records the absence.
* Fallbacks (configured time zone / site) are only used when explicitly passed in, and
  the header records that the value came from a fallback (TIMESRC / LOCSRC).
* The timestamp uncertainty is recorded (DATEUNC), because EXIF does not say whether
  DateTimeOriginal marks the start, middle or end of a long exposure.

References:
* EXIF 2.32 (CIPA DC-008-2019): DateTimeOriginal, SubSecTimeOriginal,
  OffsetTimeOriginal (added in 2.31), ExposureTime, ISOSpeedRatings
  (PhotographicSensitivity), FocalLength, FocalLengthIn35mmFilm, GPS IFD.
  Published by CIPA (Camera & Imaging Products Association).
* FITS Standard 4.0 (DATE-OBS as ISO-8601 UTC).
  https://fits.gsfc.nasa.gov/fits_standard.html
* SITELAT/SITELONG/SITEELEV, FOCALLEN, BAYERPAT, XBAYROFF/YBAYROFF and ROWORDER are
  community conventions (used by N.I.N.A., SharpCap, ASTAP and others), not part of
  the FITS standard.
* DNG decoding via rawpy (LibRaw bindings): https://letmaik.github.io/rawpy/
"""

from __future__ import annotations

import argparse
import sys
import time
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import exifread
import numpy as np
import numpy.typing as npt
from astropy.io import fits
from PIL import Image

RAW_SUFFIXES = frozenset({".dng"})
JPEG_SUFFIXES = frozenset({".jpg", ".jpeg"})
SUPPORTED_SUFFIXES = RAW_SUFFIXES | JPEG_SUFFIXES

# EXIF DateTimeOriginal has 1 s resolution unless SubSecTimeOriginal is present.
_EXIF_SECOND_RESOLUTION_S = 1.0

TimeSource = Literal["exif_offset", "fallback_tz"]
LocationSource = Literal["exif_gps", "fallback_site"]


@dataclass(frozen=True)
class Site:
    """Observing site used only as an explicit fallback when EXIF has no GPS."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float | None = None


@dataclass(frozen=True)
class PhoneFrameMetadata:
    source_path: Path
    make: str | None = None
    model: str | None = None
    date_obs_utc: datetime | None = None
    time_source: TimeSource | None = None
    date_obs_uncertainty_s: float | None = None
    exposure_s: float | None = None
    iso: int | None = None
    focal_length_mm: float | None = None
    focal_length_35mm: float | None = None
    orientation: int | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    elevation_m: float | None = None
    location_source: LocationSource | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PixelData:
    """Pixel array plus what is needed to interpret it.

    kind == "cfa": raw Bayer mosaic, linear, shape (H, W), uint16.
    kind == "linear_rgb": demosaiced but still linear DNG ("LinearRaw"), shape (3, H, W).
    kind == "rgb": processed JPEG, gamma-encoded (non-linear), shape (3, H, W), uint8.
    """

    data: npt.NDArray[Any]
    kind: Literal["cfa", "linear_rgb", "rgb"]
    bayer_pattern: str | None = None
    black_levels: tuple[float, ...] | None = None
    white_level: int | None = None


# --------------------------------------------------------------------------- EXIF


def read_exif(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        tags: dict[str, Any] = exifread.process_file(fh, details=False)
    return tags


def _first(tags: Mapping[str, Any], key: str) -> Any | None:
    tag = tags.get(key)
    if tag is None:
        return None
    values = tag.values
    if isinstance(values, list):
        return values[0] if values else None
    return values


def _str(tags: Mapping[str, Any], key: str) -> str | None:
    value = _first(tags, key)
    if value is None:
        return None
    text = str(value).strip().strip("\x00").strip()
    return text or None


def _float(tags: Mapping[str, Any], key: str) -> float | None:
    value = _first(tags, key)
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return result if np.isfinite(result) else None


def dms_to_degrees(dms: Sequence[Any], ref: str) -> float:
    """Convert EXIF GPS (degrees, minutes, seconds) + ref (N/S/E/W) to signed degrees."""
    if len(dms) != 3:
        raise ValueError(f"GPS coordinate must have 3 components, got {len(dms)}")
    deg, minutes, seconds = (float(v) for v in dms)
    value = deg + minutes / 60.0 + seconds / 3600.0
    ref = ref.strip().upper()
    if ref in ("S", "W"):
        return -value
    if ref in ("N", "E"):
        return value
    raise ValueError(f"Invalid GPS reference {ref!r}")


def _parse_offset(text: str) -> timezone:
    sign = -1 if text.startswith("-") else 1
    hours, minutes = text.lstrip("+-").split(":")
    return timezone(sign * timedelta(hours=int(hours), minutes=int(minutes)))


def parse_metadata(
    path: Path,
    tags: Mapping[str, Any],
    *,
    fallback_tz: tzinfo | None = None,
    fallback_site: Site | None = None,
) -> PhoneFrameMetadata:
    warnings: list[str] = []

    exposure_s = _float(tags, "EXIF ExposureTime")
    if exposure_s is None:
        warnings.append("EXIF sem ExposureTime: EXPTIME omitido")

    iso_value = _first(tags, "EXIF ISOSpeedRatings")
    iso = int(iso_value) if iso_value is not None else None

    # --- time
    date_obs_utc: datetime | None = None
    time_source: TimeSource | None = None
    uncertainty: float | None = None
    raw_dt = _str(tags, "EXIF DateTimeOriginal")
    if raw_dt is None:
        warnings.append("EXIF sem DateTimeOriginal: DATE-OBS omitido")
    else:
        naive = datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
        resolution = _EXIF_SECOND_RESOLUTION_S
        subsec = _str(tags, "EXIF SubSecTimeOriginal")
        if subsec and subsec.isdigit():
            naive += timedelta(seconds=float(f"0.{subsec}"))
            resolution = 10.0 ** -len(subsec)

        offset_text = _str(tags, "EXIF OffsetTimeOriginal")
        tz: tzinfo | None = None
        if offset_text:
            try:
                tz = _parse_offset(offset_text)
                time_source = "exif_offset"
            except ValueError:
                warnings.append(f"OffsetTimeOriginal inválido: {offset_text!r}")
        if tz is None and fallback_tz is not None:
            tz = fallback_tz
            time_source = "fallback_tz"
            warnings.append(f"Fuso horário ausente no EXIF; usado o configurado ({fallback_tz})")
        if tz is None:
            warnings.append("Fuso horário desconhecido: DATE-OBS omitido")
        else:
            date_obs_utc = naive.replace(tzinfo=tz).astimezone(UTC)
            # EXIF does not define whether the stamp is start/mid/end of exposure.
            uncertainty = resolution + (exposure_s or 0.0)

    # --- location
    lat = lon = elev = None
    location_source: LocationSource | None = None
    lat_tag, lon_tag = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLongitude")
    lat_ref, lon_ref = _str(tags, "GPS GPSLatitudeRef"), _str(tags, "GPS GPSLongitudeRef")
    if lat_tag is not None and lon_tag is not None and lat_ref and lon_ref:
        try:
            lat = dms_to_degrees(lat_tag.values, lat_ref)
            lon = dms_to_degrees(lon_tag.values, lon_ref)
            location_source = "exif_gps"
            elev = _float(tags, "GPS GPSAltitude")
            if elev is not None and _first(tags, "GPS GPSAltitudeRef") == 1:
                elev = -elev
        except (ValueError, ZeroDivisionError) as exc:
            warnings.append(f"GPS inválido no EXIF: {exc}")
            lat = lon = elev = None
    if location_source is None:
        if fallback_site is not None:
            lat, lon = fallback_site.latitude_deg, fallback_site.longitude_deg
            elev = fallback_site.elevation_m
            location_source = "fallback_site"
            warnings.append("EXIF sem GPS; usado o local configurado")
        else:
            warnings.append("Local desconhecido: SITELAT/SITELONG omitidos")

    orientation = _first(tags, "Image Orientation")

    return PhoneFrameMetadata(
        source_path=path,
        make=_str(tags, "Image Make"),
        model=_str(tags, "Image Model"),
        date_obs_utc=date_obs_utc,
        time_source=time_source,
        date_obs_uncertainty_s=uncertainty,
        exposure_s=exposure_s,
        iso=iso,
        focal_length_mm=_float(tags, "EXIF FocalLength"),
        focal_length_35mm=_float(tags, "EXIF FocalLengthIn35mmFilm"),
        orientation=int(orientation) if orientation is not None else None,
        latitude_deg=lat,
        longitude_deg=lon,
        elevation_m=elev,
        location_source=location_source,
        warnings=tuple(warnings),
    )


# ------------------------------------------------------------------------- pixels


def bayer_pattern_string(raw_pattern: npt.NDArray[Any], color_desc: bytes) -> str:
    """Build a pattern such as "RGGB" from LibRaw's 2x2 index array and color list."""
    pattern = np.asarray(raw_pattern)
    if pattern.shape != (2, 2):
        raise ValueError(f"Only 2x2 CFA patterns are supported, got {pattern.shape}")
    colors = color_desc.decode("ascii")
    return "".join(colors[int(i)] for i in pattern.flatten())


def load_pixels(path: Path) -> PixelData:
    suffix = path.suffix.lower()
    if suffix in RAW_SUFFIXES:
        import rawpy  # imported lazily: LibRaw is only needed for RAW files

        with rawpy.imread(str(path)) as raw:
            data = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
            # raw_pattern is relative to the visible area's top-left pixel. Confirmed by
            # tests on synthetic DNGs (all 4 Bayer layouts, no sensor margins).
            # [A VERIFICAR com DNG real do S24, que pode ter margens/ActiveArea.]
            raw_pattern = raw.raw_pattern
            pattern = (
                bayer_pattern_string(raw_pattern, raw.color_desc)
                if raw_pattern is not None
                else None
            )
            black = tuple(float(b) for b in raw.black_level_per_channel)
            white = int(raw.white_level)
        if data.ndim == 3:
            # Some phones write already-demosaiced "LinearRaw" DNGs (no Bayer mosaic).
            # [A VERIFICAR] which kind the S24 Pro mode produces.
            return PixelData(np.moveaxis(data, -1, 0).copy(), "linear_rgb", None, black, white)
        return PixelData(data, "cfa", pattern, black, white)
    if suffix in JPEG_SUFFIXES:
        with Image.open(path) as img:
            rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
        return PixelData(np.moveaxis(rgb, -1, 0).copy(), "rgb")
    raise ValueError(f"Unsupported file type: {path.suffix}")


# --------------------------------------------------------------------------- FITS


def build_header(meta: PhoneFrameMetadata, pixels: PixelData) -> fits.Header:
    h = fits.Header()

    def put(key: str, value: object | None, comment: str) -> None:
        if value is not None:
            h[key] = (value, comment)

    put("IMAGETYP", "LIGHT", "Frame type")
    put("ORIGIN", "sky-monitor", "Software that wrote this file")
    put("SRCFILE", meta.source_path.name, "Original phone file")
    instrument = " ".join(p for p in (meta.make, meta.model) if p) or None
    put("INSTRUME", instrument, "Camera make and model (EXIF)")
    if meta.date_obs_utc is not None:
        put(
            "DATE-OBS",
            meta.date_obs_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "UTC, from EXIF DateTimeOriginal",
        )
    put("TIMESRC", meta.time_source, "exif_offset or fallback_tz")
    put("DATEUNC", meta.date_obs_uncertainty_s, "[s] DATE-OBS uncertainty")
    put("EXPTIME", meta.exposure_s, "[s] Exposure time (EXIF)")
    put("ISOSPEED", meta.iso, "ISO sensitivity (EXIF)")
    put("FOCALLEN", meta.focal_length_mm, "[mm] Focal length (EXIF)")
    put("FOCAL35", meta.focal_length_35mm, "[mm] 35mm-equivalent focal length (EXIF)")
    put("EXIFORNT", meta.orientation, "EXIF Orientation; pixels not rotated")
    put("SITELAT", meta.latitude_deg, "[deg] Latitude, north positive")
    put("SITELONG", meta.longitude_deg, "[deg] Longitude, east positive")
    put("SITEELEV", meta.elevation_m, "[m] Elevation")
    put("LOCSRC", meta.location_source, "exif_gps or fallback_site")
    put("ROWORDER", "TOP-DOWN", "Row 0 is the top of the image")
    put("PIXKIND", pixels.kind, "cfa, linear_rgb or rgb")

    if pixels.kind == "cfa":
        put("LINEAR", True, "Pixel values are linear in flux")
        put("BAYERPAT", pixels.bayer_pattern, "CFA pattern from LibRaw")
        put("XBAYROFF", 0, "X offset of Bayer pattern")
        put("YBAYROFF", 0, "Y offset of Bayer pattern")
        put("WHITELVL", pixels.white_level, "[ADU] Saturation level")
        for i, level in enumerate(pixels.black_levels or ()):
            put(f"BLKLVL{i}", level, f"[ADU] Black level, CFA channel {i}")
    elif pixels.kind == "linear_rgb":
        put("LINEAR", True, "Linear DNG, already demosaiced")
        put("WHITELVL", pixels.white_level, "[ADU] Saturation level")
        for i, level in enumerate(pixels.black_levels or ()):
            put(f"BLKLVL{i}", level, f"[ADU] Black level, channel {i}")
    else:
        put("LINEAR", False, "JPEG: gamma-encoded, not for photometry")
        put("COLORSP", "sRGB", "Assumed JPEG color space")

    for warning in meta.warnings:
        h.add_history(_ascii(warning))
    return h


def _ascii(text: str) -> str:
    """FITS header text must be printable ASCII: strip accents (e.g. "horário" -> "horario")."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def convert_to_fits(
    path: Path,
    out_dir: Path,
    *,
    fallback_tz: tzinfo | None = None,
    fallback_site: Site | None = None,
    overwrite: bool = False,
) -> tuple[Path, PhoneFrameMetadata]:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    meta = parse_metadata(
        path, read_exif(path), fallback_tz=fallback_tz, fallback_site=fallback_site
    )
    pixels = load_pixels(path)
    hdu = fits.PrimaryHDU(data=pixels.data, header=build_header(meta, pixels))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.fits"
    hdu.writeto(out_path, overwrite=overwrite)
    return out_path, meta


# ---------------------------------------------------------------------------- CLI


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skymonitor-phone-ingest",
        description="Converte fotos de celular (DNG ou JPEG) em FITS para o sky-monitor.",
    )
    p.add_argument("inputs", nargs="+", type=Path, help="Arquivos ou pastas de entrada")
    p.add_argument("-o", "--out", type=Path, required=True, help="Pasta de saída")
    p.add_argument("--tz", help="Fuso de fallback, ex.: America/Sao_Paulo")
    p.add_argument("--lat", type=float, help="Latitude de fallback (graus, norte +)")
    p.add_argument("--lon", type=float, help="Longitude de fallback (graus, leste +)")
    p.add_argument("--elev", type=float, help="Altitude de fallback (m)")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument(
        "--watch",
        action="store_true",
        help="Fica observando as pastas e converte arquivos novos assim que chegam",
    )
    p.add_argument("--poll", type=float, default=10.0, help="Intervalo entre varreduras (s)")
    p.add_argument(
        "--settle",
        type=float,
        default=5.0,
        help="Só converte arquivos sem modificação há pelo menos N s (ainda copiando)",
    )
    return p


def _expand(inputs: Sequence[Path]) -> list[Path]:
    """List input files (folders are searched recursively, e.g. inbox/<date>/).
    When a folder has both X.dng and X.jpg (phones often save both),
    keep only the DNG: same stem would produce the same X.fits, and RAW is the better data.
    """
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            candidates = sorted(
                f for f in item.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES
            )
            raw_stems = {(f.parent, f.stem) for f in candidates if f.suffix.lower() in RAW_SUFFIXES}
            files.extend(
                f
                for f in candidates
                if f.suffix.lower() in RAW_SUFFIXES or (f.parent, f.stem) not in raw_stems
            )
        else:
            files.append(item)
    return files


def pending_files(
    inputs: Sequence[Path], out_dir: Path, *, now: float, settle_s: float
) -> list[Path]:
    """Files that have no FITS output yet and have not been modified for settle_s seconds."""
    ready: list[Path] = []
    for f in _expand(inputs):
        if (out_dir / f"{f.stem}.fits").exists():
            continue
        try:
            age = now - f.stat().st_mtime
        except FileNotFoundError:
            continue
        if age >= settle_s:
            ready.append(f)
    return ready


def _convert_and_report(
    paths: Sequence[Path],
    out_dir: Path,
    *,
    tz: tzinfo | None,
    site: Site | None,
    overwrite: bool,
) -> int:
    failures = 0
    for path in paths:
        if not overwrite and (out_dir / f"{path.stem}.fits").exists():
            print(f"PULADO {path.name}: FITS já existe (use --overwrite para refazer)", flush=True)
            continue
        try:
            out, meta = convert_to_fits(
                path, out_dir, fallback_tz=tz, fallback_site=site, overwrite=overwrite
            )
        except Exception as exc:
            failures += 1
            print(f"FALHA  {path}: {exc}", file=sys.stderr, flush=True)
            continue
        print(f"OK     {path.name} -> {out}", flush=True)
        for warning in meta.warnings:
            print(f"       aviso: {warning}", flush=True)
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if (args.lat is None) != (args.lon is None):
        print("Erro: --lat e --lon devem ser informados juntos.", file=sys.stderr)
        return 2
    site = Site(args.lat, args.lon, args.elev) if args.lat is not None else None
    tz = ZoneInfo(args.tz) if args.tz else None

    if not args.watch:
        failures = _convert_and_report(
            _expand(args.inputs), args.out, tz=tz, site=site, overwrite=args.overwrite
        )
        return 1 if failures else 0

    print(f"Observando {', '.join(map(str, args.inputs))} (Ctrl+C para parar)…", flush=True)
    failed: set[Path] = set()
    try:
        while True:
            todo = [
                f
                for f in pending_files(args.inputs, args.out, now=time.time(), settle_s=args.settle)
                if f not in failed
            ]
            for f in todo:
                if _convert_and_report([f], args.out, tz=tz, site=site, overwrite=False):
                    failed.add(f)  # don't retry a broken file forever
            time.sleep(args.poll)
    except KeyboardInterrupt:
        print("Parado.", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
