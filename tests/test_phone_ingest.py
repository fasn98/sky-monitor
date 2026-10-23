from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from astropy.io import fits

from conftest import DngFactory, JpegFactory
from skymonitor.ingest.phone import (
    Site,
    _expand,
    bayer_pattern_string,
    convert_to_fits,
    dms_to_degrees,
    main,
    parse_metadata,
    pending_files,
    read_exif,
)

DATA_DIR = Path(__file__).parent / "data" / "phone"


# ---------------------------------------------------------------- pure helpers


def test_dms_to_degrees_signs() -> None:
    assert dms_to_degrees([26, 55, 30], "S") == pytest.approx(-26.925)
    assert dms_to_degrees([49, 3, 36], "W") == pytest.approx(-49.06)
    assert dms_to_degrees([10, 30, 0], "N") == pytest.approx(10.5)


def test_dms_to_degrees_rejects_bad_ref() -> None:
    with pytest.raises(ValueError):
        dms_to_degrees([1, 2, 3], "X")


def test_bayer_pattern_string() -> None:
    assert bayer_pattern_string(np.array([[0, 1], [3, 2]]), b"RGBG") == "RGGB"
    assert bayer_pattern_string(np.array([[1, 0], [2, 3]]), b"RGBG") == "GRBG"


# --------------------------------------------------------------------- metadata


def test_metadata_full_exif(make_jpeg: JpegFactory) -> None:
    path = make_jpeg()
    meta = parse_metadata(path, read_exif(path))
    # 21:15:30.250 at -03:00 -> 00:15:30.250 UTC next day
    assert meta.date_obs_utc == datetime(2026, 10, 23, 0, 15, 30, 250000, tzinfo=UTC)
    assert meta.time_source == "exif_offset"
    # 3-digit subsec -> 1 ms resolution, plus the 30 s exposure (start/mid/end unknown)
    assert meta.date_obs_uncertainty_s == pytest.approx(30.001)
    assert meta.exposure_s == 30.0
    assert meta.iso == 800
    assert meta.latitude_deg == pytest.approx(-26.925)
    assert meta.longitude_deg == pytest.approx(-49.06)
    assert meta.elevation_m == pytest.approx(15.0)
    assert meta.location_source == "exif_gps"
    assert meta.warnings == ()


def test_missing_offset_uses_explicit_fallback(make_jpeg: JpegFactory) -> None:
    path = make_jpeg(offset=None)
    meta = parse_metadata(path, read_exif(path), fallback_tz=ZoneInfo("America/Sao_Paulo"))
    assert meta.time_source == "fallback_tz"
    assert meta.date_obs_utc == datetime(2026, 10, 23, 0, 15, 30, 250000, tzinfo=UTC)
    assert any("Fuso" in w for w in meta.warnings)


def test_missing_offset_without_fallback_omits_time(make_jpeg: JpegFactory) -> None:
    path = make_jpeg(offset=None)
    meta = parse_metadata(path, read_exif(path))
    assert meta.date_obs_utc is None
    assert meta.time_source is None


def test_missing_gps_uses_fallback_site(make_jpeg: JpegFactory) -> None:
    path = make_jpeg(gps=False)
    site = Site(-26.99, -48.63, 5.0)
    meta = parse_metadata(path, read_exif(path), fallback_site=site)
    assert meta.location_source == "fallback_site"
    assert (meta.latitude_deg, meta.longitude_deg) == (-26.99, -48.63)


def test_missing_gps_without_fallback_omits_location(make_jpeg: JpegFactory) -> None:
    path = make_jpeg(gps=False)
    meta = parse_metadata(path, read_exif(path))
    assert meta.latitude_deg is None and meta.location_source is None


# ------------------------------------------------------------------------- FITS


def test_jpeg_to_fits_header_and_data(make_jpeg: JpegFactory, tmp_path: Path) -> None:
    out, _ = convert_to_fits(make_jpeg(), tmp_path / "out")
    with fits.open(out) as hdul:
        hdr, data = hdul[0].header, hdul[0].data
    assert data.shape == (3, 48, 64)
    assert hdr["DATE-OBS"] == "2026-10-23T00:15:30.250"
    assert hdr["EXPTIME"] == 30.0
    assert hdr["ISOSPEED"] == 800
    assert hdr["INSTRUME"] == "samsung SM-S921B"
    assert hdr["SITELAT"] == pytest.approx(-26.925)
    assert hdr["LINEAR"] is False
    assert hdr["ROWORDER"] == "TOP-DOWN"


def test_missing_values_are_omitted_not_invented(make_jpeg: JpegFactory, tmp_path: Path) -> None:
    out, _ = convert_to_fits(make_jpeg(exposure=None, gps=False), tmp_path / "out")
    with fits.open(out) as hdul:
        hdr = hdul[0].header
    assert "EXPTIME" not in hdr
    assert "SITELAT" not in hdr
    history = " ".join(str(h) for h in hdr["HISTORY"])
    assert "ExposureTime" in history


def test_unsupported_suffix(tmp_path: Path) -> None:
    bad = tmp_path / "x.png"
    bad.write_bytes(b"")
    with pytest.raises(ValueError):
        convert_to_fits(bad, tmp_path)


# -------------------------------------------------------------------------- CLI


def test_cli_converts_directory(make_jpeg: JpegFactory, tmp_path: Path) -> None:
    make_jpeg("a.jpg")
    make_jpeg("b.jpeg", offset=None)
    out_dir = tmp_path / "fits"
    code = main([str(tmp_path), "-o", str(out_dir), "--tz", "America/Sao_Paulo"])
    assert code == 0
    assert sorted(p.name for p in out_dir.iterdir()) == ["a.fits", "b.fits"]


def test_cli_requires_lat_and_lon_together(tmp_path: Path) -> None:
    assert main([str(tmp_path), "-o", str(tmp_path / "o"), "--lat", "-27"]) == 2


# ------------------------------------------------------------ real DNG (optional)


@pytest.mark.skipif(
    not any(DATA_DIR.glob("*.dng")),
    reason="Nenhum DNG real em tests/data/phone/ (ver docs/protocolo-captura-celular.md)",
)
def test_real_dng_roundtrip(tmp_path: Path) -> None:
    dng = sorted(DATA_DIR.glob("*.dng"))[0]
    out, meta = convert_to_fits(dng, tmp_path)
    with fits.open(out) as hdul:
        hdr, data = hdul[0].header, hdul[0].data
    assert data.ndim == 2 and data.dtype == np.uint16
    assert hdr["LINEAR"] is True
    assert len(hdr["BAYERPAT"]) == 4
    assert meta.exposure_s is not None


def test_non_ascii_warnings_are_transliterated(make_jpeg: JpegFactory, tmp_path: Path) -> None:
    path = make_jpeg(offset=None)
    out, meta = convert_to_fits(path, tmp_path / "out", fallback_tz=ZoneInfo("America/Sao_Paulo"))
    assert any("horário" in w for w in meta.warnings)  # Portuguese kept for the user
    with fits.open(out) as hdul:
        history = " ".join(str(h) for h in hdul[0].header["HISTORY"])
    assert "horario" in history


# ------------------------------------------------------- synthetic DNG (LibRaw)


@pytest.mark.parametrize("pattern", ["RGGB", "GRBG", "BGGR", "GBRG"])
def test_synthetic_dng_to_fits(make_dng: DngFactory, tmp_path: Path, pattern: str) -> None:
    dng = make_dng(pattern=pattern)
    expected = np.load(dng.parent / f"{dng.name}.npy")
    out, meta = convert_to_fits(dng, tmp_path / "out")
    with fits.open(out) as hdul:
        hdr, data = hdul[0].header, hdul[0].data
    np.testing.assert_array_equal(data, expected)  # raw mosaic preserved bit-for-bit
    assert hdr["LINEAR"] is True
    assert hdr["BAYERPAT"] == pattern
    assert hdr["WHITELVL"] == 1023
    assert hdr["BLKLVL0"] == 64
    # Synthetic DNG has no EXIF time/exposure: nothing is invented.
    assert "DATE-OBS" not in hdr and "EXPTIME" not in hdr
    assert meta.date_obs_utc is None


# ------------------------------------------------------------- folders & watch


def test_expand_prefers_dng_over_jpeg_with_same_stem(
    make_dng: DngFactory, make_jpeg: JpegFactory, tmp_path: Path
) -> None:
    make_dng("20261022_193512.dng")
    make_jpeg("20261022_193512.jpg")
    make_jpeg("20261022_193600.jpg")  # JPEG without RAW twin is kept
    names = sorted(p.name for p in _expand([tmp_path]))
    assert names == ["20261022_193512.dng", "20261022_193600.jpg"]


def test_pending_files_waits_for_settle_and_skips_done(
    make_jpeg: JpegFactory, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    a = make_jpeg("a.jpg")
    b = make_jpeg("b.jpg")
    now = time.time()
    os.utime(a, (now - 60, now - 60))  # old: ready
    os.utime(b, (now, now))  # just written: not settled yet
    assert pending_files([tmp_path], out, now=now, settle_s=5) == [a]
    convert_to_fits(a, out)
    assert pending_files([tmp_path], out, now=now + 10, settle_s=5) == [b]


def test_expand_searches_subfolders(make_jpeg: JpegFactory, tmp_path: Path) -> None:
    sub = tmp_path / "2026-10-22"
    sub.mkdir()
    src = make_jpeg("night.jpg")
    src.rename(sub / "night.jpg")
    assert [p.name for p in _expand([tmp_path])] == ["night.jpg"]


def test_cli_skips_existing_outputs(make_jpeg: JpegFactory, tmp_path: Path) -> None:
    make_jpeg("a.jpg")
    out_dir = tmp_path / "fits"
    assert main([str(tmp_path), "-o", str(out_dir)]) == 0
    assert main([str(tmp_path), "-o", str(out_dir)]) == 0  # second run: skipped, not failed


def test_dng_info_reports_structure(make_dng: DngFactory) -> None:
    from skymonitor.ingest.dnginfo import inspect

    text = "\n".join(inspect(make_dng(pattern="GRBG")))
    assert "photometric=32803 (CFA (Bayer))" in text
    assert "DNGVersion" in text
    assert "LibRaw: OK" in text


def test_dng_info_reports_truncated_file(make_dng: DngFactory) -> None:
    from skymonitor.ingest.dnginfo import inspect

    dng = make_dng()
    dng.write_bytes(dng.read_bytes()[:-500])  # simulate an incomplete copy
    text = "\n".join(inspect(dng))
    assert "LibRaw:" in text
