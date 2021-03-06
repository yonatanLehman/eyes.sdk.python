import os
from distutils.util import strtobool

import pytest

from applitools.selenium import (
    BatchInfo,
    BrowserType,
    Eyes,
    StitchMode,
    VisualGridRunner,
)


def vg_eyes():
    vgr = VisualGridRunner(1)
    eyes = Eyes(vgr)
    eyes.configuration.add_browser(700, 460, BrowserType.CHROME)
    return eyes


def pytest_generate_tests(metafunc):
    os.environ["TEST_BROWSERS"] = "chrome"
    stitches = [dict(stitch_mode=StitchMode.CSS), dict(stitch_mode=StitchMode.Scroll)]

    if strtobool(os.getenv("TEST_RUN_ON_VG", "False")):
        stitches = [dict(stitch_mode=StitchMode.CSS)]
        if "eyes_class" in metafunc.fixturenames:
            metafunc.parametrize("eyes_class", [vg_eyes]),

    if "batch_info" in metafunc.fixturenames:
        b_info = BatchInfo("Python SDK Desktop Sel")
        if strtobool(os.getenv("TEST_RUN_ON_VG", "False")):
            b_info = BatchInfo("Python SDK Desktop VG")
        metafunc.parametrize("batch_info", [b_info])

    if "page" in metafunc.fixturenames:
        metafunc.parametrize("page", ["mobile", "desktop", "scrolled_mobile"])
    if "eyes" in metafunc.fixturenames:
        metafunc.parametrize(
            "eyes",
            stitches,
            indirect=True,
            ids=lambda o: "CSS" if o["stitch_mode"] == StitchMode.CSS else "Scroll",
        ),
