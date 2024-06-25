---
# piecash2

[![codecov](https://codecov.io/gh/sdementen/piecash2/branch/main/graph/badge.svg?token=piecash2_token_here)](https://codecov.io/gh/sdementen/piecash2)
[![CI](https://github.com/sdementen/piecash2/actions/workflows/main.yml/badge.svg)](https://github.com/sdementen/piecash2/actions/workflows/main.yml)

A python library to work with [GnuCash](https://www.gnucash.org/) books, a successor of the [piecash](https://github.com/sdementen/piecash) library, built on top of SQLAlchemy 2.

## Install it from PyPI

```bash
pip install piecash2
```

## Usage

```py
from piecash2 import open_book

# open the gnucash book (sqlite3 file)
Session = open_book("mybook.gnucash")
# retrieve the module
piecash = Session.module

with Session() as session:
    # query all accounts in the
    for account in session.query(piecash.Account).all():
        print(account.name)
```

## Development

Read the [CONTRIBUTING.md](CONTRIBUTING.md) file.
