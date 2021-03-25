import pytest

from libgen_uploader import LibgenUploader


@pytest.fixture(scope="function")
def uploader():
    yield LibgenUploader()
