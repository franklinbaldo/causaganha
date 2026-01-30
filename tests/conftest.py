"""Pytest configuration and global fixtures."""

import decimal


# Fix for "decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]"
# appearing in sqlglot/ibis interactions during test collection.
# This ensures we don't crash on benign decimal conversion signals.
decimal.getcontext().traps[decimal.InvalidOperation] = False
