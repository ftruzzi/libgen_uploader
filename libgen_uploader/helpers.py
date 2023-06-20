from __future__ import annotations

from typing import List, Union

from bs4 import BeautifulSoup
from returns.result import safe
from robobrowser.browser import RoboBrowser
from robobrowser.forms.form import Form


class LibgenUploadException(Exception):
    def __init__(self, message: str):
        self.message = message


class LibgenMetadataException(Exception):
    def __init__(self, message: str):
        self.message = message


def calculate_md5(file_path: str):
    import hashlib

    with open(file_path, "rb") as f:
        f_hash = hashlib.md5()
        while chunk := f.read(8192):
            f_hash.update(chunk)

    return f_hash.hexdigest()


@safe
def check_upload_form_response(response: BeautifulSoup) -> bool:
    if error_el := response.select_one(".form_error"):
        error_text = error_el.text.strip()
        if "javascript disabled" not in error_text.lower():
            raise LibgenUploadException(f"Upload failed: {error_text}")

    # TODO find better way to detect successful file upload
    if "fetch bibliographic" in str(response).lower():
        return True

    raise LibgenUploadException("Upload failed: unknown error")


@safe
def check_metadata_form_response(
    response: BeautifulSoup,
) -> str:
    if error_el := response.select_one(".error") or response.select_one(".form_error"):
        error_text = error_el.text.strip()
        raise LibgenUploadException(f"File save failed: {error_text}")

    if "successfully saved" in str(response).lower():
        return (
            response.find(lambda el: el.name == "div" and "to share" in el.text)
            .select_one("a")
            .attrs["href"]
        )

    raise LibgenUploadException("File save failed: unknown failure")


@safe
def are_forms_equal(first: Form, second: Form) -> bool:
    first_keys = set(first.keys())
    second_keys = set(second.keys())
    if first_keys != second_keys:
        return False

    for k in first_keys:
        if first[k].value != second[k].value:
            return False

    return True


def epub_has_drm(book: Union[str, bytes]) -> bool:
    from io import BytesIO
    from zipfile import BadZipFile, ZipFile

    book_file = BytesIO(book) if isinstance(book, bytes) else book

    try:
        z = ZipFile(book_file)  # type: ignore
        return any("encryption.xml" in f.filename for f in z.filelist)
    except BadZipFile:
        # assuming not .epub
        return False


def validate_metadata(metadata) -> Union[bool, dict]:
    from cerberus import Validator
    from .constants import METADATA_FORM_SCHEMA

    v = Validator(METADATA_FORM_SCHEMA)
    return True if v.validate(metadata) else v.errors


def match_language_to_form_option(language: str, options: List[str]) -> str:
    for valid_language in options:
        if language.lower() == valid_language.lower().strip():
            return valid_language

    raise LibgenMetadataException(
        f"Failed to select correct language in upload form: {language} not found."
    )
