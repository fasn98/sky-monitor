from __future__ import annotations

from pathlib import Path

import numpy as np
from astropy.io import fits

from skymonitor.preview import main, render


def test_render_linear_marks_saturation() -> None:
    data = np.zeros((3, 4, 4), dtype=np.uint16)
    data[:, 0, 0] = 4095  # saturated pixel
    data[:, 1, 1] = 400
    hdr = fits.Header({"PIXKIND": "linear_rgb", "WHITELVL": 4095})
    out = render(data, hdr)
    assert out.shape == (4, 4, 3) and out.dtype == np.uint8
    assert tuple(out[0, 0]) == (255, 0, 255)
    assert out[1, 1, 0] > out[2, 2, 0] == 0


def test_cli_writes_png(tmp_path: Path) -> None:
    f = tmp_path / "x.fits"
    hdr = fits.Header({"PIXKIND": "linear_rgb", "WHITELVL": 4095})
    fits.PrimaryHDU(np.full((3, 8, 8), 100, dtype=np.uint16), header=hdr).writeto(f)
    assert main([str(f)]) == 0
    assert (tmp_path / "x.png").exists()
