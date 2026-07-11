import itertools
import json
from typing import Optional

from django_matrix.settings import BOOL_NAME_TRANSLATION


def convert_from_json(field: str | None) -> dict | None:
    if field:
        return json.loads(field)
    else:
        return None


def remove_trailing_zeros(number):
    number_str = str(number)
    return number_str.rstrip("0").rstrip(".") if "." in number_str else number_str


def split_list_to_chunks(input_list: list, chunk_size: int):
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i : i + chunk_size]


def split_dict_to_chunks(d: dict, chunk_size: int):
    it = iter(d)
    for i in range(0, len(d), chunk_size):
        yield {k: d[k] for k in itertools.islice(it, chunk_size)}


def bool_translate(value: any, lang: str) -> str:
    value_bool = False
    if value is not None:
        if isinstance(value, str):
            match value.lower():
                case "true":
                    value_bool = True
                case "false":
                    value_bool = False
                case _:
                    value_bool = False
        elif isinstance(value, bool):
            value_bool = value

    return BOOL_NAME_TRANSLATION.get(value_bool, {}).get(lang.lower(), value)
