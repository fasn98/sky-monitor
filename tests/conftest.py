"""Shared fixtures: synthetic JPEGs with controlled EXIF.

These images are generated at test time (no external data, no license issues).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from PIL.ExifTags import GPS, IFD, Base
from PIL.TiffImagePlugin import IFDRational

JpegFactory = Callable[..., Path]


@pytest.fixture
def make_jpeg(tmp_path: Path) -> JpegFactory:
    def _make(
        name: str = "frame.jpg",
        *,
        datetime_original: str | None = "2026:10:22 21:15:30",
        offset: str | None = "-03:00",
        subsec: str | None = "250",
        exposure: tuple[int, int] | None = (30, 1),
        iso: int | None = 800,
        gps: bool = True,
        size: tuple[int, int] = (64, 48),
    ) -> Path:
        img = Image.new("RGB", size, (10, 12, 14))
        exif = Image.Exif()
        exif[Base.Make] = "samsung"
        exif[Base.Model] = "SM-S921B"
        exif[Base.Orientation] = 1
        e: Any = exif.get_ifd(IFD.Exif)
        if datetime_original is not None:
            e[Base.DateTimeOriginal] = datetime_original
        if offset is not None:
            e[Base.OffsetTimeOriginal] = offset
        if subsec is not None:
            e[Base.SubsecTimeOriginal] = subsec
        if exposure is not None:
            e[Base.ExposureTime] = IFDRational(*exposure)
        if iso is not None:
            e[Base.ISOSpeedRatings] = iso
        e[Base.FocalLength] = IFDRational(22, 10)
        e[Base.FocalLengthIn35mmFilm] = 13
        if gps:
            g: Any = exif.get_ifd(IFD.GPSInfo)
            g[GPS.GPSLatitudeRef] = "S"
            g[GPS.GPSLatitude] = (IFDRational(26), IFDRational(55), IFDRational(30))
            g[GPS.GPSLongitudeRef] = "W"
            g[GPS.GPSLongitude] = (IFDRational(49), IFDRational(3), IFDRational(36))
            g[GPS.GPSAltitudeRef] = b"\x00"
            g[GPS.GPSAltitude] = IFDRational(15)
        path = tmp_path / name
        img.save(path, "JPEG", exif=exif)
        return path

    return _make


DngFactory = Callable[..., Path]

# DNG tag IDs from the Adobe DNG Specification 1.4 and TIFF/EP.
_DNG_VERSION = 50706
_UNIQUE_CAMERA_MODEL = 50708
_CFA_REPEAT_PATTERN_DIM = 33421
_CFA_PATTERN = 33422
_BLACK_LEVEL = 50714
_WHITE_LEVEL = 50717
_COLOR_MATRIX_1 = 50721
_AS_SHOT_NEUTRAL = 50728
_PHOTOMETRIC_CFA = 32803

# CFAPattern values: 0 = red, 1 = green, 2 = blue.
_CFA_CODES = {"R": 0, "G": 1, "B": 2}


@pytest.fixture
def make_dng(tmp_path: Path) -> DngFactory:
    """Write a minimal synthetic DNG (readable by LibRaw) with a known Bayer pattern."""
    import numpy as np
    import tifffile

    def _make(
        name: str = "frame.dng", *, pattern: str = "RGGB", shape: tuple[int, int] = (32, 48)
    ) -> Path:
        h, w = shape
        data = (np.arange(h * w, dtype=np.uint16).reshape(h, w) % 900) + 64
        identity = (1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1)
        tags = [
            (_DNG_VERSION, "B", 4, (1, 4, 0, 0), True),
            (_UNIQUE_CAMERA_MODEL, "s", 0, "Synthetic Test Cam", True),
            (_CFA_REPEAT_PATTERN_DIM, "H", 2, (2, 2), True),
            (_CFA_PATTERN, "B", 4, tuple(_CFA_CODES[c] for c in pattern), True),
            (_BLACK_LEVEL, "H", 1, (64,), True),
            (_WHITE_LEVEL, "H", 1, (1023,), True),
            (_COLOR_MATRIX_1, "2i", 9, identity, True),
            (_AS_SHOT_NEUTRAL, "2I", 3, (1, 1, 1, 1, 1, 1), True),
        ]
        path = tmp_path / name
        tifffile.imwrite(path, data, photometric=_PHOTOMETRIC_CFA, bitspersample=16, extratags=tags)
        np.save(tmp_path / f"{name}.npy", data)
        return path

    return _make
