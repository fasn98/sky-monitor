"""Render a FITS frame (from skymonitor-phone-ingest) as a PNG for quick visual checks.

Linear data (cfa / linear_rgb) is scaled by its saturation level (WHITELVL) and
stretched with asinh so faint detail stays visible; gamma-encoded JPEG data (rgb) is
written as is. Saturated pixels can be painted magenta to make clipping obvious.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from astropy.io import fits
from PIL import Image


def render(
    data: npt.NDArray[Any], header: Any, *, stretch: float = 10.0, mark_saturated: bool = True
) -> npt.NDArray[np.uint8]:
    kind = header.get("PIXKIND", "rgb")
    if data.ndim == 2:
        data = data[np.newaxis]
    img = np.moveaxis(np.asarray(data, dtype=float), 0, -1)  # (H, W, C)
    if kind == "rgb":
        rgb8: npt.NDArray[np.uint8] = np.clip(img, 0, 255).astype(np.uint8)
        if rgb8.shape[-1] != 3:
            rgb8 = np.repeat(rgb8, 3, axis=-1)
        return rgb8
    white = float(header.get("WHITELVL", np.nanmax(img)))
    blacks = [float(header.get(f"BLKLVL{i}", 0.0)) for i in range(img.shape[-1])]
    norm = np.clip((img - np.array(blacks)) / max(white - max(blacks), 1.0), 0, None)
    stretched = np.arcsinh(stretch * norm) / np.arcsinh(stretch)
    out: npt.NDArray[np.uint8] = (np.clip(stretched, 0, 1) * 255).astype(np.uint8)
    if out.shape[-1] == 1:
        out = np.repeat(out, 3, axis=-1)
    if mark_saturated:
        saturated = (img >= white).any(axis=-1)
        out[saturated] = (255, 0, 255)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="skymonitor-preview", description="Gera PNG de pré-visualização a partir de FITS."
    )
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("-o", "--out", type=Path, help="Pasta de saída (padrão: ao lado do FITS)")
    p.add_argument("--stretch", type=float, default=10.0, help="Intensidade do realce asinh")
    p.add_argument("--max-size", type=int, default=1600, help="Maior lado do PNG, em pixels")
    p.add_argument("--no-saturation", action="store_true", help="Não pinta saturação de magenta")
    args = p.parse_args(argv)
    for f in args.files:
        with fits.open(f) as hdul:
            rgb = render(
                hdul[0].data,
                hdul[0].header,
                stretch=args.stretch,
                mark_saturated=not args.no_saturation,
            )
            sat = float((rgb == np.array([255, 0, 255], dtype=np.uint8)).all(axis=-1).mean() * 100)
        im = Image.fromarray(rgb)
        im.thumbnail((args.max_size, args.max_size))
        out_dir = args.out or f.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{f.stem}.png"
        im.save(dest)
        print(f"OK     {f.name} -> {dest}   saturado: {sat:.1f}% dos pixels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
