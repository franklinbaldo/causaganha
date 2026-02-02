"""CausaGanha - Lawyer performance ratings from Brazilian judicial data."""

import decimal

# Fix for "decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]"
# appearing in sqlglot/ibis interactions.
# This ensures we don't crash on benign decimal conversion signals.
decimal.getcontext().traps[decimal.InvalidOperation] = False
