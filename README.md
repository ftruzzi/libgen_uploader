_A Library Genesis ebook uploader._

**This library is to be considered unstable/beta until v1.0.0. API may change until then.**

## Installation

```bash
pip install libgen-uploader
```

## Usage

This library uses [returns](https://github.com/dry-python/returns), and returns [Result containers](https://returns.readthedocs.io/en/latest/pages/result.html) which can either contain a success value or a failure/exception. Exception values are returned, not raised, so you can handle them as you wish and avoid wide `try/except` blocks or program crashes due to unforeseen exceptions.

### Uploading books

Two methods are exposed for uploading books: `upload_scitech` and `upload_fiction`.

```python
from libgen_uploader import LibgenUploader
from returns.pipeline import is_successful

u = LibgenUploader()

result = u.upload_fiction("book.epub")
if is_successful(result):
    upload_url = result.unwrap() # type: str
else:
    failure = result.failure() # type: Exception
```

### Fetching metadata

Metadata support is not complete yet. The default metadata are the one contained in the book itself. You can then fetch additional metadata from the sources supported by the Library Genesis upload form, namely:

- Other Library Genesis record (`"local"`)
- Amazon US/UK/DE/FR/IT/ES/JP (`"amazon_us"`, `"amazon_uk"`, `"amazon_de"`, `"amazon_fr"`, `"amazon_it"`, `"amazon_es"`, `"amazon_jp"`)
- British Library (`"bl"`)
- Douban.com (`"douban"`)
- Goodreads (`"goodreads"`)
- Google Books (`"google_books"`)
- Library of Congress (`"loc"`)
- Russian State Library (`"rsl"`)
- WorldCat (`"worldcat"`)

Any fetched metadata completely replaces all metadata contained in the ebook itself (this is how the upload form works), and any custom (user-provided) metadata overrides the default/fetched ones.

```python
# use metadata contained in the book
u = LibgenUploader()
u.upload_scitech("book.epub")

# session-wide metadata source
u = LibgenUploader(metadata_source="amazon_it")
u.upload_scitech("book.epub", metadata_query="9788812312312")

# book-level metadata source
u = LibgenUploader()
u.upload_scitech(
    "book.epub",
    metadata_source="amazon_it",
    metadata_query=["9788812312312", "another_isbn"] # you can pass an array of values in case the first ones don't return results
)

# custom, user-provided metadata (override default/fetched)
from libgen_uploader import LibgenMetadata

m = LibgenMetadata(title="new title", authors=["John Smith", "Jack Black"])
u.upload_scitech("book.epub", metadata=m)
```