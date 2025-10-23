#!/usr/bin/env python3

'''
This script scrapes sql statements from the test directory, and stores them as separate files
'''

from pathlib import Path
import shutil
import sqllogic_utils
import random
import re

# globs
CORPUS_ROOT_DIR = Path(__file__).parents[2] / 'corpus'
FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/test/').expanduser()
KEY_WORD_FILE = Path(__file__).parents[1] / 'fuzz_utils/duckdb_sql.dict'

key_words = re.findall(r"^\"(\w+)\"$", KEY_WORD_FILE.read_text(), flags=re.MULTILINE)


# create sql coprus
def main():
    # delete and recreate the corpus directory
    corpus_dir = CORPUS_ROOT_DIR / 'sql'
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
        pruned_statements = [use_casing_from_dict(stmnt) for stmnt in statements if not sql_exempted(stmnt)]
        if pruned_statements:
            filename = f"{test_file.stem.replace(' ', '-')}.sql"
            (corpus_dir / filename).write_text("\n".join(pruned_statements))

    # only keep random set, to prevent the corpus is too big -> DELETE the others!
    # select_random_corpus_files(corpus_dir)


# follow the casing from the .dict file, for better keyword detection by the fuzzer
def use_casing_from_dict(statement: str):
    for kw in key_words:
        pattern = rf"\b{kw}\b"
        statement = re.sub(pattern, kw, statement, flags=re.IGNORECASE)
    return statement


# discord some sql statement that won't (yet) work well in fuzzing context
def sql_exempted(sql_statement):
    forbidden_words = [
        'enable_verification',
        '__TEST_DIR__',  # data sources not available in fuzzing context
        'read_',         # data sources not available in fuzzing context
        '${',            # sqllogic variable expansion not yet supported
        'repeat(',       # used to create long strings, which is too slow for fuzzing
    ]
    return any(word in sql_statement for word in forbidden_words)


def select_random_corpus_files(corpus_dir: Path, keep_max=20):
    if not corpus_dir.is_dir():
        raise ValueError(f"'{corpus_dir}' is not a directory!")
    all_corpus_files = list(corpus_dir.iterdir())
    if len(all_corpus_files) <= keep_max:
        return
    corpus_to_keep = set(random.sample(all_corpus_files, keep_max))
    for corpus_file in all_corpus_files:
        if corpus_file not in corpus_to_keep:
            # delete file
            corpus_file.unlink()


if __name__ == "__main__":
    main()
