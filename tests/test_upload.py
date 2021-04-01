import os

from functools import partial

import pytest

from libgen_uploader import LibgenMetadata, LibgenUploader
from libgen_uploader.helpers import check_upload_form_response
from returns.contrib.pytest import ReturnsAsserts
from returns.pipeline import is_successful
from returns.result import Success, Failure

from .helpers import get_return_value

files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "files")

@pytest.mark.vcr(record_mode="once")
def test_validate_file_path_missing(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "missing.epub")
    assert isinstance(
        uploader.upload_fiction(file_path=file_path).failure(), FileNotFoundError
    )


def test_validate_file_path(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    assert uploader._validate_file(file_path) == Success(file_path)


@pytest.mark.vcr(record_mode="once")
def test_epub_drm(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal_drm.epub")
    result = uploader.upload_fiction(file_path=file_path)
    assert is_successful(result) is False and "drm" in str(result.failure()).lower()


@pytest.mark.vcr(record_mode="once")
def test_file_upload(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    value = get_return_value(
        check_upload_form_response, partial(uploader.upload_fiction, file_path)
    )
    assert value == True


@pytest.mark.vcr(record_mode="once")
def test_bytes_upload(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    with open(file_path, "rb") as f:
        data = f.read()

    value = get_return_value(
        check_upload_form_response, partial(uploader.upload_fiction, data)
    )
    assert value == True


@pytest.mark.vcr(record_mode="once")
def test_no_metadata_results(uploader: LibgenUploader, returns: ReturnsAsserts):
    file_path = os.path.join(files_path, "minimal.epub")
    with returns.assert_trace(Failure, uploader._fetch_metadata):
        uploader.upload_fiction(
            file_path, metadata_source="amazon_de", metadata_query="012kd3o2llds"
        )


@pytest.mark.vcr(record_mode="once")
def test_metadata_fetched(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    form = get_return_value(
        uploader._fetch_metadata,
        partial(
            uploader.upload_fiction,
            file_path,
            metadata_source="amazon_it",
            metadata_query="8854165069",
        ),
    )
    assert form["title"].value == "La Divina Commedia. Ediz. integrale"


@pytest.mark.vcr(record_mode="once")
def test_custom_metadata(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    metadata = LibgenMetadata(title="custom title", authors=["author1", "author2"])
    form = get_return_value(
        uploader._update_metadata,
        partial(
            uploader.upload_fiction,
            file_path,
            metadata=metadata,
            metadata_source="amazon_it",
            metadata_query="8854165069",
        ),
    )

    assert (
        form["title"].value == "custom title"
        and form["authors"].value == "author1, author2"
    )


@pytest.mark.vcr(record_mode="once")
def test_invalid_metadata_language(uploader: LibgenUploader, returns: ReturnsAsserts):
    file_path = os.path.join(files_path, "minimal.epub")
    metadata = LibgenMetadata(language="Invalid")

    with returns.assert_trace(Failure, uploader._update_metadata):
        uploader.upload_fiction(
            file_path,
            metadata=metadata,
            metadata_source="amazon_it",
            metadata_query="8854165069",
        )


@pytest.mark.vcr(record_mode="once")
def test_custom_metadata_overrides_fetched(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    metadata = LibgenMetadata(title="custom title")
    form = get_return_value(
        uploader._update_metadata,
        partial(
            uploader.upload_fiction,
            file_path,
            metadata=metadata,
            metadata_source="amazon_it",
            metadata_query="8854165069",
        ),
    )

    assert (
        "Dante Alighieri" in form["authors"].value
        and form["title"].value == "custom title"
    )
