from __future__ import annotations

import logging

from typing import Union

from bs4 import BeautifulSoup
from returns.result import Result, Failure, Success, safe
import robobrowser
from robobrowser.browser import RoboBrowser


class LibgenUploadException(Exception):
    pass


def calculate_md5(file_path: str):
    import hashlib

    with open(file_path, "rb") as f:
        hash = hashlib.md5()
        while chunk := f.read(8192):
            hash.update(chunk)

    return hash.hexdigest()


@safe
def check_upload_form_response(response: BeautifulSoup) -> bool:
    if error_el := response.select_one(".form_error"):
        error_text = error_el.text.strip()
        if "javascript disabled" not in error_text.lower():
            raise LibgenUploadException(f"Upload failed: {error_text}")

    # TODO find better way to detect successful file upload
    if "fetch bibliographic" in str(response).lower():
        return True

    raise LibgenUploadException("File upload failure: unknown error")


@safe
def check_metadata_form_response(
    response: BeautifulSoup,
) -> str:

    if error_el := response.select_one(".error"):
        error_text = error_el.text.strip()
        raise LibgenUploadException(f"File save failed: {error_text}")

    if "successfully saved" in str(response).lower():
        return (
            response.find(lambda el: el.name == "div" and "to share" in el.text)
            .select_one("a")
            .attrs["href"]
        )

    raise LibgenUploadException("File save error: unknown failure")


@safe
def are_forms_equal(
    first: robobrowser.forms.form.Form, second: robobrowser.forms.form.Form
) -> bool:
    first_keys = set(first.keys())
    second_keys = set(second.keys())
    if first_keys != second_keys:
        return False

    for k in first_keys:
        if first[k].value != second[k].value:
            return False

    return True
