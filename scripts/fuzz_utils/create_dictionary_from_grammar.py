#!/usr/bin/env python3

from pathlib import Path
import re


def main():
    DUCKDB_DIR = Path('~/git/duckdb/').expanduser()
    FILE_DIR_TO_SCRAPE = DUCKDB_DIR / 'extension/autocomplete/grammar/statements'
    SQL_DICT_FILE = Path(__file__).parent / 'duckdb_sql.dict'

    # scrape quoted keywords
    all_gram_files = FILE_DIR_TO_SCRAPE.rglob('*.gram')
    all_key_words: set[str] = set()
    for f in all_gram_files:
        key_words = set(re.findall(r"'(\w+?)'", f.read_text(), flags=re.NOFLAG))
        all_key_words.update(key_words)

    # create dictionary file
    entries = [f"\"{entry.lower()}\"" for entry in sorted(all_key_words)]
    SQL_DICT_FILE.write_text("\n".join(entries))


if __name__ == "__main__":
    main()
