import concurrent.futures
import threading
from collections import namedtuple
from typing import Optional

from django.db import connection
from django_regional.models import Language


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
        if language:
            return language.name_en
        else:
            return "simple"

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
        search_all = []
        for s in search:
            s = s.replace("'", "''")  # Zabezpieczenie apostrofów
            part = s.split()

            processed_parts = []
            for p in part:
                if p == "":
                    continue

                # Usunięcie lub zastąpienie znaków specjalnych
                p = p.replace("&", "")  # Usuń operatory AND
                p = p.replace("|", "")  # Usuń operatory OR
                p = p.replace("!", "")  # Usuń operatory NOT
                p = p.replace("(", "")  # Usuń nawiasy otwierające
                p = p.replace(")", "")  # Usuń nawiasy zamykające
                p = p.replace(":", "")  # Usuń dwukropki

                # Jeśli po usunięciu znaków specjalnych słowo nie jest puste, dodaj je
                if p:
                    processed_parts.append(p + ":*")

            # Łączenie słów z operatorem & (AND)
            if processed_parts:
                part_all = " & ".join(processed_parts)
                part_all = f"({part_all})"
                search_all.append(part_all)

        # Łączenie różnych fraz wyszukiwania z operatorem | (OR)
        value = " | ".join(search_all)

        param_name = "ts_search_str"

        function = f"to_tsquery('{self.get_full_text_search_lang(language)}', %({param_name})s)"
        return function, param_name, value
