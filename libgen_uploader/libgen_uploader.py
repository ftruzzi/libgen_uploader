from __future__ import annotations

import logging
import os
from typing import List, Union

from bs4 import BeautifulSoup

from returns.curry import partial
from returns.result import Failure, Result, Success, safe
from returns.pointfree import alt, bind, lash, map_
from returns.pipeline import flow, is_successful

from robobrowser import RoboBrowser
from robobrowser.forms.form import Form
from robobrowser.forms.fields import Submit

from .constants import (
    LIBGEN_UPLOADER_VERSION,
    FICTION_UPLOAD_URL,
    SCITECH_UPLOAD_URL,
    UPLOAD_USERNAME,
    UPLOAD_PASSWORD,
)
from .helpers import (
    LibgenMetadataException,
    LibgenUploadException,
    are_forms_equal,
    check_upload_form_response,
    check_metadata_form_response,
)

class LibgenMetadata:
    def __init__(self, *, title: str, language: str):
        pass

    # def _validate_metadata(self, **kwargs):


class LibgenUploader:
    def __init__(self):
        self._init_browser()

    def _init_browser(self):
        self._browser = RoboBrowser(
            parser="html.parser",
            user_agent=f"libgen_uploader-v{LIBGEN_UPLOADER_VERSION}",
        )
        self._browser.session.auth = (UPLOAD_USERNAME, UPLOAD_PASSWORD)

    @safe
    def _submit_form_get_response(
        self,
        form: Form,
        submit: Submit = None,
    ) -> BeautifulSoup:
        self._browser.submit_form(form, submit=submit)
        self._browser.response.raise_for_status()
        return self._browser.parsed

    def _submit_and_check_form(self, form: Form) -> Result[str, Exception]:
        return flow(
            form, self._submit_form_get_response, bind(check_metadata_form_response)
        )

    @safe
    def _upload_file(self, file_path: str) -> BeautifulSoup:
        form = self._browser.get_form()
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Upload failed: {file_path} is not a file.")

        form["file"].value = open(file_path, mode="rb")
        response = self._submit_form_get_response(form)
        if is_successful(response):
            return response.unwrap()

        raise response.failure()

    @safe
    def _fetch_metadata_from_query(
        self, form, *, metadata_source: str, metadata_query: str
    ) -> Form:
        form["metadata_source"].value = metadata_source
        form["metadata_query"].value = metadata_query
        logging.debug(
            f"Fetching metadata from {metadata_source} with query {metadata_query}"
        )
        self._submit_form_get_response(form, submit=form["fetch_metadata"])
        return self._browser.get_form()

    @safe
    def _fetch_metadata(
        self,
        form,
        *,
        metadata_source: str,
        metadata_queries: Union[str, List[str]],
        ignore_empty: bool = False,
    ) -> Form:
        if isinstance(metadata_queries, str):
            metadata_queries = [metadata_queries]

        for i, query in enumerate(metadata_queries):
            new_form = self._fetch_metadata_from_query(
                form, metadata_source=metadata_source, metadata_query=query
            )

            if is_successful(new_form):
                new_form = new_form.unwrap()
            else:
                raise new_form.failure()

            # check that form data has actually changed
            if (result := are_forms_equal(form, new_form)) == Success(False):
                return new_form

            elif result == Success(True):
                logging.debug(
                    f"No results found for metadata query {query} ({i + 1}/{len(metadata_queries)})"
                )
                if i == len(metadata_queries) - 1:
                    if ignore_empty:
                        return form

                    raise LibgenMetadataException(
                        "Failed to fetch metadata: no results"
                    )

            else:
                # this is a failure
                return result

    @safe
    def _fill_metadata(
        self,
        form: Form,
        *,
        metadata_source: str = None,
        metadata_queries: Union[str, List[str]] = "",
        title: str = None,
        language: str = None,
    ) -> Form:
        # TODO add auto metadata filling from kwargs
        if metadata_source:
            metadata_source = metadata_source.strip().lower()
            form = self._fetch_metadata(
                form, metadata_source=metadata_source, metadata_queries=metadata_queries
            )
            if is_successful(form):
                form = form.unwrap()
            else:
                raise form.failure()

        # language and title are mandatory values
        if not form["language"]:
            if language:
                form["language"].value = language
            else:
                raise LibgenMetadataException(
                    "Missing required metadata value: language"
                )

        if not form["title"]:
            if title:
                form["title"].value = title
            else:
                raise LibgenMetadataException("Missing required metadata value: title")

        # delete "fetch metadata" submit
        del form.fields["fetch_metadata"]
        return form

    def _handle_save_failure(self, f: Failure) -> Result[str, Exception]:
        exception = f.failure()

        if isinstance(exception, LibgenUploadException) and "unknown" not in (
            exc_str := str(exception).lower()
        ):
            if "asin" in exc_str:
                # bad ASIN, remove and resubmit
                logging.warning(
                    "Fetched metadata contained a bad ASIN. Trying to remove and resubmit..."
                )

                form = self._browser.get_form()
                form["asin"].value = ""
                return self._submit_and_check_form(form)

        # failed to recover, re-raise
        return Failure(exception)

    def _upload(self, **kwargs) -> Result[str, Union[str, Exception]]:
        upload_url: Result[str, Union[str, Exception]] = flow(
            kwargs["file_path"],
            self._upload_file,
            bind(check_upload_form_response),
            lambda *_: self._browser.get_form(),
            partial(
                self._fill_metadata,
                metadata_queries=kwargs["metadata_queries"],
                metadata_source=kwargs["metadata_source"],
            ),
            # self._submit_and_check_form,
            # alt(self._handle_save_failure),
        )

        return upload_url

    def upload_fiction(
        self,
        file_path: str,
        *,
        metadata_source: str = None,
        metadata_queries: Union[str, List] = "",
    ) -> Result[str, Union[str, Exception]]:
        self._init_browser()
        self._browser.open(FICTION_UPLOAD_URL)
        return self._upload(
            file_path=file_path,
            metadata_source=metadata_source,
            metadata_queries=metadata_queries,
        )

    def upload_scitech(
        self,
        file_path: str,
        *,
        metadata_source: str = None,
        metadata_queries: Union[str, List] = "",
    ) -> Result[str, Union[str, Exception]]:
        self._init_browser()
        self._browser.open(SCITECH_UPLOAD_URL)
        return self._upload(
            file_path=file_path,
            metadata_source=metadata_source,
            metadata_queries=metadata_queries,
        )
