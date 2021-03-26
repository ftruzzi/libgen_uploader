LIBGEN_UPLOADER_VERSION = "0.1.1"

FICTION_UPLOAD_URL = "https://library.bz/fiction/upload/"
SCITECH_UPLOAD_URL = "https://library.bz/main/upload/"

UPLOAD_USERNAME = "genesis"
UPLOAD_PASSWORD = "upload"

METADATA_FORM_SCHEMA = {
    # title and language are not required at this stage as they can also come from the book file or external metadata source
    "title": {"type": "string"},
    "language": {"type": "string"},
    "authors": {"type": "list", "schema": {"type": "string"}},
    "edition": {"type": "string"},
    "series": {"type": "string"},
    "pages": {"type": "integer", "min": 1},
    "year": {"type": "integer"},
    "publisher": {"type": "string"},
    "ISBNs": {"type": "list", "schema": {"type": "string"}},
    "description": {"type": "string"},
    "comment": {"type": "string"},
}
