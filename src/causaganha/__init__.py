"""CausaGanha - Lawyer performance ratings from Brazilian judicial data."""

import decimal


# Workaround for decimal.InvalidOperation crash in ibis/sqlglot interaction
decimal.getcontext().traps[decimal.InvalidOperation] = False
