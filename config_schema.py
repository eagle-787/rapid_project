from jsonschema import validate, ValidationError
from typing import Any, Optional, cast
import json
from pathlib import Path
from .core.type_hint import LineFile, TimetableFile
from .core.module import Line


# ---- line.json のスキーマ ----
SCHEMA_LINE: dict[str, Any] = {
    "type": "object",
    "required": ["sections", "stations"],
    "properties": {
        "sections": {
            "type": "array",
            "minItems": 1,
            "items": {
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
                "allOf": [
                    # unit_typeごとの必須キー
                    {
                        "if": {"properties": {"unit_type": {"const": "start"}}},
                        "then": {"required": ["start_coord"]},
                    },
                    {
                        "if": {"properties": {"unit_type": {"const": "normal"}}},
                        "then": {"required": ["length"]},
                    },
                    {
                        "if": {"properties": {"unit_type": {"const": "crossing"}}},
                        "then": {"required": ["vector"]},
                    },
                    {
                        "if": {"properties": {"unit_type": {"const": "merge"}}},
                        "then": {"required": ["vector"]},
                    },
                    {
                        "if": {"properties": {"unit_type": {"const": "branch"}}},
                        "then": {"required": ["vector"]},
                    },
                ],
                "additionalProperties": False,
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
            "items": {
                "type": "object",
                "required": ["id", "init_stn", "init_track", "max_speed", "color"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "init_stn": {"type": "string", "minLength": 1},
                    "init_track": {"type": "integer", "minimum": 0},
                    "max_speed": {"type": "integer", "minimum": 1},
                    "color": {
                        "type": "array",
                        "minItems": 3,
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
    # Basic station checks
    names = [s["name"] for s in line_data["stations"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate station name in line.stations")
    max_sect_index = len(line_data["sections"]) - 1
    for s in line_data["stations"]:
        if s["sect_index"] <= 0 or s["sect_index"] >= max_sect_index:
            raise ValueError(f"Station sect_index out of range: {s}")

    # Build topology for track counts
    line = Line(line_data)
    tracks_per_station = {name: len(units) for name, units in line.stations.items()}

    # Train definitions
    train_ids = {t["id"] for t in tt_data["train"]}
    for t in tt_data["train"]:
        stn = t["init_stn"]
        if stn not in tracks_per_station:
            raise ValueError(f"init_stn not found: {stn}")
        if not (0 <= t["init_track"] < tracks_per_station[stn]):
            raise ValueError(f"init_track out of range at {stn}: {t['init_track']}")

    # Timetable entries
    tt_numbers = set()
    for entry in tt_data["timetable"]:
        if entry["train_id"] not in train_ids:
            raise ValueError(f"Unknown train_id in timetable: {entry['train_id']}")
        tt_numbers.add(entry["number"])
        last_time = -1
        for stop in entry["schedule"]:
            stn = stop["station"]
            if stn not in tracks_per_station:
                raise ValueError(f"Unknown station in schedule: {stn}")
            if not (0 <= stop["track"] < tracks_per_station[stn]):
                raise ValueError(f"track out of range at {stn}: {stop['track']}")
            # direction required where dep_time exists
            if (
                "dep_time" in stop
                and stop["dep_time"] is not None
                and not stop.get("direction")
            ):
                raise ValueError(f"direction required at departure: {stn}")
            # simple non-decreasing time checks (ignore overnight)
            for key in ("arr_time", "dep_time"):
                t_ = cast(Optional[int], stop.get(key))
                if t_ is not None:
                    if last_time > t_:
                        raise ValueError(f"Non-monotonic time at {stn}: {key}")
                    last_time = t_
            if stop.get("arr_time") is not None and stop.get("dep_time") is not None:
                if stop["arr_time"] > stop["dep_time"]:
                    raise ValueError(f"arr_time > dep_time at {stn}")

    # Interlocking route orders reference valid numbers and tracks
    for item in tt_data["starting_stn"]:
        if item["number"] not in tt_numbers:
            raise ValueError(f"starting_stn.number not in timetable: {item}")
        if not (0 <= item["track"] < 4):  # layout-specific: 4-track starter
            raise ValueError(f"starting_stn.track out of range: {item}")
    for item in tt_data["terminal_stn"]:
        if item["number"] not in tt_numbers:
            raise ValueError(f"terminal_stn.number not in timetable: {item}")
        if not (0 <= item["track"] < 2):  # layout-specific: 2-track terminal
            raise ValueError(f"terminal_stn.track out of range: {item}")


if __name__ == "__main__":
    try:
        line: LineFile = load_and_validate("line.json", SCHEMA_LINE)
        tt: TimetableFile = load_and_validate("timetable.json", SCHEMA_TIMETABLE)
        semantic_checks(line, tt)
        print("OK: line.json / timetable.json are valid.")
    except Exception as e:
        print(str(e))
        raise SystemExit(1)
