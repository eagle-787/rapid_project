from jsonschema import validate, ValidationError
from typing import Any
import json
from pathlib import Path
from .core.type_hint import LineFile, TimetableFile


# ---- line.json のスキーマ ----
SCHEMA_LINE: dict[str, Any] = {
    "type": "object",
    "required": ["sections", "stations"],
    "properties": {
        "sections": {
            "type": "array",
            "minItems": 1,
            "itmes": {
                "type": "object",
                "required": ["unit_type"],
                "properties": {
                    "unit_type": {
                        "enum": [
                            "start",
                            "normal",
                            "crossing",
                            "merge",
                            "branch",
                            "end",
                        ]
                    },
                    # start
                    "start_coord": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {"type": "integer", "minimum": 0},
                        },
                    },
                    # normal
                    "length": {"type": "integer", "minimum": 1},
                    # crossing / merge / branch
                    "vector": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"type": "integer", "minimum": 0},
                    },
                },
                "allof": [
                    # typeごとの必須キー
                    {
                        "if": {"properties": {"type": {"const": "start"}}},
                        "then": {"required": ["start_coord"]},
                    },
                    {
                        "if": {"properties": {"type": {"const": "normal"}}},
                        "then": {"required": ["length"]},
                    },
                    {
                        "if": {"properties": {"type": {"const": "crossing"}}},
                        "then": {"required": ["vector"]},
                    },
                    {
                        "if": {"properties": {"type": {"const": "merge"}}},
                        "then": {"required": ["vector"]},
                    },
                    {
                        "if": {"properties": {"type": {"const": "branch"}}},
                        "then": {"required": ["vector"]},
                    },
                ],
            },
        },
        "stations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "sect_index"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "sect_index": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


# ---- timetable.json のスキーマ ----
SCHEMA_TIMETABLE: dict[str, Any] = {
    "type": "object",
    "required": ["train", "timetable", "starting_stn", "terminal_stn"],
    "properties": {
        # train初期化
        "train": {
            "type": "array",
            "itmes": {
                "type": "object",
                "required": ["id", "init_stn", "init_track", "max_speed", "color"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "init_stn": {"type": "string", "minLength": 1},
                    "init_track": {"type": "integer", "minimum": 0},
                    "max_speed": {"type": "integer", "minimum": 1},
                    "color": {
                        "type": "array",
                        "minItmes": 3,
                        "maxItems": 3,
                        "items": {"type": "integer", "minimum": 0, "maximum": 255},
                    },
                },
                "additionalProperties": False,
            },
        },
        # ダイヤグラム
        "timetable": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["train_id", "number", "schedule"],
                "properties": {
                    "train_id": {"type": "string", "minLength": 1},
                    "number": {"type": "integer", "minimum": 0},
                    "schedule": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["station", "track"],
                            "properties": {
                                "station": {"type": "string", "minLength": 1},
                                "track": {"type": "integer", "minimum": 0},
                                "arr_time": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 1439,
                                },
                                "dep_time": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 1439,
                                },
                                "direction": {"enum": ["FORWARD", "BACKWARD"]},
                            },
                            "additionalProperties": False,
                        },
                    },
                },
                "additionalProperties": False,
            },
        },
        # 始点　進路設定リスト
        "starting_stn": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["number", "track"],
                "properties": {
                    "number": {"type": "integer", "minimum": 0},
                    "track": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
        },
        # 終点　進路設定リスト
        "terminal_stn": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["number", "track"],
                "properties": {
                    "number": {"type": "integer", "minimum": 0},
                    "track": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


def _pretty_error(e: ValidationError, file_name: str) -> str:
    loc = " > ".join(map(str, e.path)) if e.path else "(root)"
    return f"[{file_name}] Schema validation error at {loc}: {e.message}"


def load_and_validate(file_name: str, schema: dict[str, Any]) -> Any:
    json_path = Path(__file__).resolve().parent / file_name
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {json_path}: {e}") from e
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        raise ValueError(_pretty_error(e, file_name)) from e
    return data


# 追加の「意味的」チェック（スキーマでは表現しづらい整合性）
def semantic_checks(line_data: LineFile, tt_data: TimetableFile) -> None:
    pass


if __name__ == "__main__":
    try:
        line: LineFile = load_and_validate("line.json", SCHEMA_LINE)
        tt: TimetableFile = load_and_validate("timetable.json", SCHEMA_TIMETABLE)
        semantic_checks(line, tt)
        print("OK: line.json / timetable.json are valid.")
    except Exception as e:
        print(str(e))
        raise SystemExit(1)
