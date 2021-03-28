import os
import re

from libgen_uploader.constants import LIBGEN_UPLOADER_VERSION


def test_version_number():
    with open(os.path.join(os.path.dirname(__file__), "../pyproject.toml"), "r") as f:
        data = f.read()

    pyproject_version = re.search(r"(?<=version\s=\s\")(\d+\.)+\d(?=\")", data).group()
    assert pyproject_version == LIBGEN_UPLOADER_VERSION
