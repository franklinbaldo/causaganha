"""CausaGanha: Judicial Analysis Platform."""

import decimal

# Fix for "decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]"
# appearing in sqlglot/ibis interactions during import of DuckDB backend.
# This occurs during Oracle compiler initialization in ibis.
decimal.getcontext().traps[decimal.InvalidOperation] = False
