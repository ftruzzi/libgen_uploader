from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import ByteString, List, Union

from bs4 import BeautifulSoup
from cerberus import schema

from returns.curry import partial
from returns.result import Failure, Result, Success, safe
from returns.pointfree import alt, bind, lash, map_
from returns.pipeline import flow, is_successful

# https://github.com/jmcarp/robobrowser/issues/93
import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property

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
    match_language_to_form_option,
    validate_metadata,
)


class LibgenMetadata:
    def __init__(
        self,
        *,
        title: str = None,
        language: str = None,
        authors: List[str] = None,
        edition: str = None,
        series: str = None,
        pages: int = None,
        year: int = None,
        publisher: str = None,
        ISBNs: List[str] = None,
        description: str = None,
        comment: str = None,
    ):
        result = validate_metadata(
            {k: v for k, v in locals().items() if k != "self" and v is not None}
        )
        if result == True:
            self.title = title
            self.language = language
            self.authors = authors
            self.edition = edition
            self.series = series
            self.pages = pages
            self.year = year
            self.publisher = publisher
            self.ISBNs = ISBNs
            self.description = description
            self.comment = comment
        else:
            logging.error(f"Metadata validation failed: {result}")


class LibgenUploader:
    metadata_source = None

    def __init__(self, metadata_source: str = None):
        if metadata_source:
            self.metadata_source = metadata_source

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

    @staticmethod
    @safe
    def _validate_file(file: Union[str, bytes]):
        if isinstance(file, str):
            if not os.path.isfile(file):
                raise FileNotFoundError(f"Upload failed: {file} is not a file.")

        elif isinstance(file, bytes):
            # TODO add file data validation?
            pass

        return file

    @safe
    def _upload_file(self, file: Union[str, bytes]) -> BeautifulSoup:
        form = self._browser.get_form()
        if isinstance(file, str):
            form["file"].value = open(file, mode="rb")
        elif isinstance(file, bytes):
            form["file"].value = BytesIO(file)

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
        metadata_source: str = None,
        metadata_query: Union[str, List[str]] = None,
        ignore_empty: bool = False,
    ) -> Form:
        if not metadata_source or not metadata_query:
            return form

        metadata_source = metadata_source.strip().lower()
        if metadata_source not in (sources := form["metadata_source"].options):
            raise LibgenUploadException(
                "Invalid metadata source {}. Valid sources: {}".format(
                    metadata_source, ", ".join(s for s in sources)
                )
            )

        if isinstance(metadata_query, str):
            metadata_query = [metadata_query]

        for i, query in enumerate(metadata_query):
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
                    f"No results found for metadata query {query} ({i + 1}/{len(metadata_query)})"
                )
                if i == len(metadata_query) - 1:
                    if ignore_empty:
                        return form

                    raise LibgenMetadataException(
                        "Failed to fetch metadata: no results"
                    )

            else:
                # this is a failure
                return result

    @staticmethod
    @safe
    def _update_metadata(form: Form, *, metadata: LibgenMetadata = None) -> Form:
        if not metadata:
            return form

        # replace existing/retrieved metadata with user-provided ones
        if isinstance(metadata, LibgenMetadata):
            metadata_dict = {
                k: v for k, v in metadata.__dict__.items() if v is not None
            }
            keys_to_copy = (
                "title",
                "edition",
                "series",
                "pages",
                "year",
                "publisher",
                "description",
            )
            for k in keys_to_copy:
                if k in metadata_dict:
                    form[k].value = metadata_dict[k]

            if "language" in metadata_dict:
                # need to exactly match language to <select> options
                language_str = match_language_to_form_option(
                    metadata_dict["language"],
                    [o for o in form["language_options"].options if o != ""],
                )
                form["language"].value = language_str
                form["language_options"].value = language_str
            if "authors" in metadata_dict:
                form["authors"].value = ", ".join(a for a in metadata_dict["authors"])
            if "ISBNs" in metadata_dict:
                form["isbn"].value = ",".join(i for i in metadata_dict["ISBNs"])
            if "comment" in metadata_dict:
                form["file_commentary"].value = metadata_dict["comment"]

        return form

    @staticmethod
    @safe
    def _validate_metadata(form: Form) -> Form:
        # language and title are mandatory values
        if not form["language"]:
            raise LibgenMetadataException("Missing required metadata value: language")

        if not form["title"]:
            raise LibgenMetadataException("Missing required metadata value: title")

        # delete "fetch metadata" submit
        del form.fields["fetch_metadata"]
        return form

    def _handle_save_failure(self, exception: Exception) -> Result[str, Exception]:
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

    def _upload(self, **kwargs) -> Result[str, Exception]:
        if [kwargs["metadata_query"], kwargs["metadata_source"]].count(None) == 1:
            if kwargs["metadata_source"] is None and self.metadata_source is not None:
                kwargs["metadata_source"] = self.metadata_source
            else:
                raise LibgenUploadException(
                    "Both metadata_source and metadata_query are required to fetch metadata."
                )

        upload_url: Result[str, Exception] = flow(
            kwargs["file_path"],
            self._validate_file,
            bind(self._upload_file),
            bind(check_upload_form_response),
            map_(lambda *_: self._browser.get_form()), # type: ignore
            bind(
                partial(
                    self._fetch_metadata,
                    metadata_query=kwargs["metadata_query"],
                    metadata_source=kwargs["metadata_source"],
                )
            ),
            bind(
                partial(
                    self._update_metadata,
                    metadata=kwargs["metadata"],
                )
            ),
            bind(self._validate_metadata),
            bind(self._submit_and_check_form),
            lash(self._handle_save_failure),
        )

        return upload_url

    def upload_fiction(
        self,
        file_path: Union[str, bytes],
        *,
        metadata: LibgenMetadata = None,
        metadata_source: str = None,
        metadata_query: Union[str, List] = None,
        ignore_empty_metadata_fetch: bool = False
    ) -> Result[str, Exception]:
        self._init_browser()
        self._browser.open(FICTION_UPLOAD_URL)
        return self._upload(
            file_path=file_path,
            metadata=metadata,
            metadata_source=metadata_source,
            metadata_query=metadata_query,
        )

    def upload_scitech(
        self,
        file_path: Union[str, bytes],
        *,
        metadata: LibgenMetadata = None,
        metadata_source: str = None,
        metadata_query: Union[str, List] = None,
    ) -> Result[str, Exception]:
        self._init_browser()
        self._browser.open(SCITECH_UPLOAD_URL)
        return self._upload(
            file_path=file_path,
            metadata=metadata,
            metadata_source=metadata_source,
            metadata_query=metadata_query,
        )
