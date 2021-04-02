"""
Shows how to use libgen_uploader as a library to batch-upload files from a .CSV.

Example CSV:

filename,isbn,is_fiction
test.epub,9788800000000,1
test2.epub,9788800000001,0
"""
import argparse
import csv
import logging

from libgen_uploader import LibgenUploader
from returns.pipeline import is_successful


def main(args):
    reader = csv.DictReader(open(args.input_file))
    uploader = LibgenUploader(metadata_source="amazon_it", show_upload_progress=True)

    for i, row in enumerate(reader):
        if int(row["is_fiction"]):
            result = uploader.upload_fiction(
                row["filename"], metadata_query=row["isbn"]
            )
        else:
            result = uploader.upload_scitech(
                row["filename"], metadata_query=row["isbn"]
            )

        if is_successful(result):
            logging.info(
                f"{row['filename']} uploaded successfully. Upload URL: {result.unwrap()}"
            )
        else:
            logging.error(result.failure())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)

    args = parser.parse_args()
    main(args)
