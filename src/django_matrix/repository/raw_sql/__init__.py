import concurrent.futures
import re
import threading
from collections import namedtuple
from functools import lru_cache
from typing import Optional

from django.db import connection
from django_regional.models import Language

# Postgres has no "polish" text search configuration, so Language.name_en cannot be trusted as one.
FALLBACK_TEXT_SEARCH_CONFIG = "simple"

# to_tsquery is strict: anything outside a lexeme (operators, quotes, backslashes) is a syntax error.
# Allowlist rather than denylist — a denylist misses <, >, *, " and turns a search into an HTTP 500.
_TSQUERY_LEXEME = re.compile(r"[^\w-]+", re.UNICODE)

# The config name is interpolated into the SQL string, so shape-check it even though it came from
# pg_ts_config: a configuration created as "o'dd" would otherwise reopen the quote.
_SAFE_CONFIG_NAME = re.compile(r"\A[a-z0-9_]+\Z")


def _tsquery_lexemes(phrase: str) -> list[str]:
    """Split a user phrase into lexemes to_tsquery can parse.

    Everything that is not a word character or a hyphen is a separator. Operators (`& | ! ( ) :`),
    the phrase operator `<->`, quotes and backslashes therefore cannot reach Postgres.
    """
    return [lexeme for lexeme in _TSQUERY_LEXEME.split(phrase or "") if lexeme]


@lru_cache(maxsize=1)
def get_text_search_configs() -> frozenset[str]:
    """Text search configurations this Postgres server actually has.

    Server-level and effectively static, so it is read once. Checking the server beats hardcoding
    the stock list: a deployment that installs a custom dictionary keeps using it.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT cfgname FROM pg_ts_config")
        return frozenset(row[0] for row in cursor.fetchall() if _SAFE_CONFIG_NAME.match(row[0]))


class DbConnect:
    def fetch_all(self, sql, params):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return self.dict_fetch_all(cursor)

    def fetch_count(self, sql, params):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

    def dict_fetch_all(self, cursor):
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def named_tuple_fetch_all(self, cursor):
        nt_result = namedtuple("Result", [col[0] for col in cursor.description])
        return [nt_result(*row) for row in cursor.fetchall()]

    def count_x_pages(self, sql: str, params: dict, x: int):
        sql_count = f"SELECT count(*) FROM ({sql}) as licz"
        sql_count_params = dict(params)
        sql_count_params["limit"] = params["limit"] * x
        return self.fetch_count(sql_count, sql_count_params)

    def execute_parallel_queries(self, main_sql: str, main_params: dict, count_sql: str, count_params: dict):
        """
        Wykonuje równolegle główne zapytanie i zapytanie COUNT dla lepszej wydajności
        """

        def execute_main_query():
            from django.db import connections

            conn = connections["default"]
            with conn.cursor() as cursor:
                cursor.execute(main_sql, main_params)
                return self.dict_fetch_all(cursor)

        def execute_count_query():
            from django.db import connections

            conn = connections["default"]
            with conn.cursor() as cursor:
                cursor.execute(count_sql, count_params)
                return cursor.fetchone()[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            main_future = executor.submit(execute_main_query)
            count_future = executor.submit(execute_count_query)

            try:
                main_results = main_future.result(timeout=30)  # 30s timeout
                count_result = count_future.result(timeout=30)

                return main_results, count_result

            except concurrent.futures.TimeoutError:
                return self.fetch_all(main_sql, main_params), self.fetch_count(count_sql, count_params)

    def count_full_pages(self, sql: str, params: dict):
        sql_count = f"SELECT count(*) FROM ({sql}) as licz"
        sql_count_params = dict(params)
        return self.fetch_count(sql_count, sql_count_params)

    def get_asc_desc(self, order):
        if order in ["ASC", "DESC"]:
            return order
        else:
            return "ASC"

    def get_full_text_search_lang(self, language: Optional["Language"] = None) -> str:
        """Postgres text search configuration for a language.

        The result is interpolated into SQL, so it must never be raw `name_en`: that field is
        admin-editable, and a language Postgres does not know (Polish is the obvious one) turns
        every search into `to_tsvector('polish', ...)` — an unauthenticated HTTP 500.
        """
        if not language:
            return FALLBACK_TEXT_SEARCH_CONFIG
        name = (language.name_en or "").lower()
        return name if name in get_text_search_configs() else FALLBACK_TEXT_SEARCH_CONFIG

    def prepare_weighted_tsvector(self, fields_with_weights: dict, language: Optional["Language"] = None) -> str:
        """
        Prepare weighted tsvector for full-text search with different weights for different fields.

        Args:
            fields_with_weights: Dict with field names as keys and weights ('A', 'B', 'C', 'D') as values
            language: Language for tsvector configuration

        Returns:
            SQL string with weighted tsvector

        Example:
            fields_with_weights = {
                'pr.sku': 'A',
                'pt.name': 'B',
                'pr.search': 'C',
                'pr.tags': 'D'
            }
        """
        weighted_vectors = []
        lang_config = self.get_full_text_search_lang(language)

        for field, weight in fields_with_weights.items():
            if weight not in ["A", "B", "C", "D"]:
                weight = "D"

            if field in ["pr.search", "pr.tags", "pt.subnames"]:
                field_content = f"COALESCE(array_to_string(array(SELECT jsonb_array_elements_text({field})), ' '), '')"
            else:
                field_content = f"COALESCE({field}, '')"

            weighted_vectors.append(f"setweight(to_tsvector('{lang_config}', {field_content}), '{weight}')")

        return " || ".join(weighted_vectors)

    def prepare_tsquery(self, search: list, language: Optional["Language"] = None) -> tuple[str, str, str]:
        """Build a prefix-matching tsquery: words AND-ed within a phrase, phrases OR-ed.

        The value is bound, not interpolated, so this is about `to_tsquery` accepting it at all.
        """
        search_all = []
        for phrase in search:
            lexemes = [f"{lexeme}:*" for lexeme in _tsquery_lexemes(phrase)]
            if lexemes:
                search_all.append(f"({' & '.join(lexemes)})")

        value = " | ".join(search_all)
        param_name = "ts_search_str"
        function = f"to_tsquery('{self.get_full_text_search_lang(language)}', %({param_name})s)"
        return function, param_name, value
