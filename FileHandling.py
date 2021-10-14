import json
import jsons
from typing import TextIO


def write_to_json(d: dict, fp: str) -> None:
    with open(fp, 'r+') as file:
        file.seek(0)
        json.dump(obj=d, fp=file)
        file.truncate()
        file.seek(0)


def read_from_json(fp: str) -> dict:
    with open(fp, 'r') as file:
        file.seek(0)
        jload = json.load(file)
        file.seek(0)
        return jload
