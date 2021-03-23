import libgen_uploader
from libgen_uploader.libgen_uploader import LibgenMetadata, LibgenUploader

from functools import partial
from helpers import get_return_value

import os

import pytest

from returns.result import Success, Failure
from returns.contrib.pytest import ReturnsAsserts


files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "files")


def test_validate_file_path_missing(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "missing.epub")
    assert isinstance(
        uploader.upload_fiction(file_path=file_path).failure(), FileNotFoundError
    )


def test_validate_file_path(uploader: LibgenUploader):
    file_path = os.path.join(files_path, "minimal.epub")
    assert uploader._validate_file(file_path) == Success(file_path)


@pytest.mark.vcr(record_mode="once")
def test_file_upload(uploader: LibgenUploader, returns: ReturnsAsserts):
    file_path = os.path.join(files_path, "minimal.epub")
    with returns.assert_trace(
        Success, libgen_uploader.helpers.check_upload_form_response
    ):
        uploader.upload_fiction(file_path)


@pytest.mark.vcr(record_mode="once")
def test_bytes_upload(uploader: LibgenUploader, returns: ReturnsAsserts):
    file_path = os.path.join(files_path, "minimal.epub")
    with open(file_path, "rb") as f:
        data = f.read()

    with returns.assert_trace(
        Success, libgen_uploader.helpers.check_upload_form_response
    ):
        uploader.upload_fiction(file_path)


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


# @pytest.mark.vcr(record_mode="once")
# def upload_book(uploader):
