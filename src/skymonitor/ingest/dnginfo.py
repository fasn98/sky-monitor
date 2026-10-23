"""Inspect the internal structure of a DNG file (diagnostics).

Prints, for the main IFD and every SubIFD: image shape, data type, compression,
photometric interpretation and the DNG-specific tags that matter for decoding.
Then tries to open the file with LibRaw (rawpy) and reports the result.

Used to answer questions such as "is this a Bayer (CFA) or a LinearRaw DNG?",
"which compression does the phone use?" and "was the file copied completely?".

Tag numbers: TIFF 6.0, TIFF/EP and Adobe DNG Specification 1.7.
Compression codes: 1 none, 7 lossless JPEG, 8 Deflate, 34892 lossy JPEG,
52546 JPEG XL (added in DNG 1.7).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import tifffile

_COMPRESSION_NAMES = {
    1: "none",
    7: "lossless JPEG",
    8: "Deflate",
    34892: "lossy JPEG (DNG)",
    52546: "JPEG XL (DNG 1.7)",
}
_PHOTOMETRIC_NAMES = {2: "RGB", 6: "YCbCr", 32803: "CFA (Bayer)", 34892: "LinearRaw"}
_TAGS = {
    50706: "DNGVersion",
    50708: "UniqueCameraModel",
    271: "Make",
    272: "Model",
    254: "NewSubfileType",
    33422: "CFAPattern",
    50714: "BlackLevel",
    50717: "WhiteLevel",
    50829: "ActiveArea",
}


def _code(value: Any) -> int:
    return int(getattr(value, "value", value))


def describe_page(page: Any, label: str) -> list[str]:
    comp = _code(page.compression)
    phot = _code(page.photometric)
    lines = [
        f"{label}: shape={page.shape} dtype={page.dtype} bits={page.bitspersample} "
        f"compression={comp} ({_COMPRESSION_NAMES.get(comp, '?')}) "
        f"photometric={phot} ({_PHOTOMETRIC_NAMES.get(phot, '?')})"
    ]
    for code, name in _TAGS.items():
        tag = page.tags.get(code)
        if tag is not None:
            value = tag.value
            if isinstance(value, bytes):
                value = value.decode("ascii", "replace").strip("\x00")
            lines.append(f"    {name} = {value}")
    return lines


def inspect(path: Path) -> list[str]:
    lines = [f"Arquivo: {path}", f"Tamanho: {path.stat().st_size} bytes"]
    with tifffile.TiffFile(path) as tif:
        main = tif.pages[0]
        lines += describe_page(main, "IFD0")
        for i, sub in enumerate(getattr(main, "pages", None) or []):
            lines += describe_page(sub, f"SubIFD{i}")
    try:
        import rawpy

        with rawpy.imread(str(path)) as raw:
            lines.append(
                f"LibRaw: OK, raw_image_visible={raw.raw_image_visible.shape}, "
                f"pattern={None if raw.raw_pattern is None else raw.raw_pattern.tolist()}, "
                f"colors={raw.color_desc!r}"
            )
    except Exception as exc:  # report, don't crash: this is a diagnostic tool
        lines.append(f"LibRaw: FALHA ({type(exc).__name__}: {exc})")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="skymonitor-dng-info", description="Mostra a estrutura interna de arquivos DNG."
    )
    p.add_argument("files", nargs="+", type=Path)
    args = p.parse_args(argv)
    status = 0
    for f in args.files:
        try:
            print("\n".join(inspect(f)), end="\n\n")
        except Exception as exc:
            status = 1
            print(f"{f}: não foi possível ler ({type(exc).__name__}: {exc})", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
