from __future__ import annotations
from typing import TypedDict, Protocol, Literal
from .enums import Sign, UnitSituation


# 型エイリアス
Coord = tuple[float, float]
Size = tuple[int, int]
Rail = list[Coord]
Color = tuple[int, int, int]


# --- JSON構造の型定義（timetable.jsonに対応） ---
class TrainDef(TypedDict):
    id: str
    init_stn: str
    init_track: int
    max_speed: int
    color: tuple[int, int, int]


class ScheduleItem(TypedDict):
    station: str
    track: int
    arr_time: int | None
    dep_time: int | None
    direction: Literal["FORWARD", "BACKWARD"] | None


class TimetableEntry(TypedDict):
    train: str
    number: int
    schedule: list[ScheduleItem]


class TimetableFile(TypedDict):
    train: list[TrainDef]
    timetable: list[TimetableEntry]
    StartingStn: list[dict[str, int]]
    TerminalStn: list[dict[str, int]]


# --- JSON構造の型定義（line.jsonに対応） ---
class SectionItem(TypedDict):
    type: Literal["start", "end", "normal", "branch", "merge", "crossing"]
    start: list[Coord] | None
    length: float | None
    vector: Coord | None


class StationItem(TypedDict):
    name: str
    sect_index: int


class LineFile(TypedDict):
    sections: list[SectionItem]
    stations: list[StationItem]


# Protocol
class UnitLike(Protocol):
    prev_units: list[UnitLike]
    prev_index: int
    next_units: list[UnitLike]
    next_index: int
    rail: Rail

    situation: UnitSituation
    is_controlled: bool
    up_sign: Sign
    down_sign: Sign


class SectionLike(Protocol):
    units: list[UnitLike]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]: ...


class ControlLike(Protocol):
    sections: list[SectionLike]
    timetable: list[dict[str, int]]
    progress: int
    arr_track: int

    def update(self) -> None: ...
