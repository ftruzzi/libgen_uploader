import logging

from libgen_uploader import LibgenUploader
from returns.pipeline import is_successful


def main(args):
    u = LibgenUploader(metadata_source=args.metadata_source)

    if args.scitech:
        result = u.upload_scitech(
            file_path=args.file, metadata_query=args.metadata_query
        )
    else:
        result = u.upload_fiction(
            file_path=args.file, metadata_query=args.metadata_query
        )

    if is_successful(result):
        logging.info(f"Upload successful! URL: {result.unwrap()}.")
    else:
        logging.error("Upload failed.")
        raise result.failure()


if __name__ == "__main__":
    import argparse

    # https://bugs.python.org/issue22240
    parser = argparse.ArgumentParser(
        prog=None
        if globals().get("__spec__") is None
        else "python -m {}".format(__spec__.name.partition(".")[0])  # type: ignore
    )
    upload_type = parser.add_mutually_exclusive_group(required=True)
    upload_type.add_argument("--scitech", action="store_true", help="Upload to scitech (non-fiction) library")
    upload_type.add_argument("--fiction", action="store_true", help="Upload to fiction library")
    parser.add_argument(
        "--metadata-source",
        type=str,
        choices=[
            "local",
            "amazon_us",
            "amazon_uk",
            "amazon_de",
            "amazon_fr",
            "amazon_it",
            "amazon_es",
            "amazon_jp",
            "bl",
            "douban",
            "goodreads",
            "google_books",
            "loc",
            "rsl",
            "worldcat",
        ],
        help="Source to fetch book metadata from",
    )
    parser.add_argument(
        "--metadata-query",
        type=str,
        help="Metadata query for selected source (supports multiple, comma-separated)",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Activate debug logging"
    )
    parser.add_argument("file", type=str)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug is True else logging.INFO)

    if args.metadata_source and not args.metadata_query:
        raise parser.error("--metadata-query requires --metadata-source")

    if args.metadata_query:
        args.metadata_query = [q.strip() for q in args.metadata_query.split(",")]

    main(args)
