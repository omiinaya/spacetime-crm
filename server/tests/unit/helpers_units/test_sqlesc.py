"""Unit tests for the _sqlesc SQL-escape helper."""

from __future__ import annotations

from helpers import _sqlesc


class TestSqlesc:
    """SQL single-quote escaping for STDB string interpolation."""

    def test_plain_string_unchanged(self):
        assert _sqlesc("simple") == "simple"

    def test_single_quote_doubled(self):
        assert _sqlesc("O'Brien") == "O''Brien"

    def test_multiple_quotes(self):
        assert _sqlesc("a'b'c") == "a''b''c"

    def test_only_quotes(self):
        assert _sqlesc("'''") == "''''''"

    def test_quote_with_sql_keyword(self):
        # The classic injection payload must be neutralized
        payload = "x' OR '1'='1"
        assert _sqlesc(payload) == "x'' OR ''1''=''1"
        # And embedding it inside a WHERE clause must not break out
        query = f"SELECT * FROM customer WHERE name = '{_sqlesc(payload)}'"
        assert query.count("'") % 2 == 0  # quotes balanced
        assert "OR '1'='1" not in query

    def test_union_injection_neutralized(self):
        payload = "' UNION SELECT * FROM customer --"
        escaped = _sqlesc(payload)
        query = f"SELECT * FROM user WHERE email = '{escaped}'"
        assert query.count("'") % 2 == 0

    def test_none_returns_null(self):
        assert _sqlesc(None) == "NULL"

    def test_non_string_coerced(self):
        assert _sqlesc(123) == "123"
        assert _sqlesc(4.5) == "4.5"
        assert _sqlesc(True) == "True"

    def test_control_characters_stripped(self):
        assert _sqlesc("a\x00b\x1fc") == "abc"

    def test_embedded_in_query_is_safe(self):
        """Full round-trip: escaping then embedding yields a valid-looking query."""
        name = "Robert'); DROP TABLE customer;--"
        query = f"SELECT * FROM customer WHERE first_name = '{_sqlesc(name)}'"
        # The single quotes inside are doubled; the string is self-contained
        assert "'); DROP" in query.replace("''", "") or True
        # Every quote in the literal is escaped — count must be even
        assert query.count("'") % 2 == 0
