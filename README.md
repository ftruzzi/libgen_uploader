A Library Genesis ebook uploader

**Warning: this library is to be considered unstable/beta until v1.0.0. API may change until then.**

## Installation
```
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

Metadata support is not complete yet. The default metadata are the one contained in the book itself. You can then fetch additional metadata from the sources supported by the Library Genesis upload form, namely: TODO add metadata sources

Any fetched metadata completely replaces all metadata contained in the ebook itself (this is how the upload form works), and any custom (user-provided) metadata overrides the default/fetched ones.

```python
# session-wide metadata source
u = LibgenUploader(metadata_source="amazon_it")
u.upload_scitech("book.epub", metadata_query="9788812312312")

# book-level metadata source
u = LibgenUploader()
u.upload_scitech("book.epub", metadata_source="amazon_it", metadata_query="9788812312312")

# custom, user-provided metadata (override default/fetched)
from libgen_uploader import LibgenMetadata
m = LibgenMetadata(title="new title", authors=["John Smith", "Jack Black"])
u.upload_scitech("book.epub", metadata=m)
```