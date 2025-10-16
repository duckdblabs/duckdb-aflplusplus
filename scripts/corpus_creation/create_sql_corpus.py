#!/usr/bin/env python3

'''
This script scrapes sql statements from the test directory, and stores them as separate files
'''

from pathlib import Path
import shutil
import sqllogic_utils


def create_sql_corpus():
    global CORPUS_ROOT_DIR
    global FILE_DIR_TO_SCRAPE

    # default paths
    CORPUS_ROOT_DIR = Path(__file__).parents[2] / 'corpus'
    FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/test/').expanduser()

    corpus_dir = CORPUS_ROOT_DIR / 'sql'

    # delete and recreate the corpus directory
    shutil.rmtree(str(corpus_dir), ignore_errors=True)
    corpus_dir.mkdir()

    # create a .sql corpus file per .test file
    all_test_files = FILE_DIR_TO_SCRAPE.rglob('*.test')
    for test_file in all_test_files:
        if not test_file.is_file():
            continue
        try:
            file_content = test_file.read_text()
        except UnicodeDecodeError:
            # skip for now: non-unicode files
            continue
        statements = sqllogic_utils.get_sql_statements(file_content)
        filename = f"{test_file.stem.replace(' ', '-')}.sql"
        (corpus_dir / filename).write_text("\n".join(statements))


if __name__ == "__main__":
    create_sql_corpus()
