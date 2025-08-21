import math
from typing import cast
from .enums import Sign, TrainSituation, Direction, UnitSituation
from .type_hint import (
    Coord,
    Rail,
    Color,
    UnitLike,
    SectionLike,
    LineFile,
    StationItem,
    SectionItem,
    TrainDef,
    TimetableEntry,
    ScheduleItem,
)


# MiddleUnitクラスの ABC and 親クラス
# attitude: rail, prev_unit-rerated, next_unit-rerated, signal-rerated
# methods: set_next_units, select_unit (prev and next)
class MiddleUnitBase:
    def __init__(self, prev_units: list[UnitLike]) -> None:
        self.prev_units: list[UnitLike] = prev_units
        self.prev_index: int = 0
        self.next_units: list[UnitLike] = []
        self.next_index: int = 0
        self.rail: Rail = []

        self.situation: UnitSituation = UnitSituation.FREE
        self.is_controlled: bool = False
        self.up_sign: Sign = Sign.GREEN
        self.down_sign: Sign = Sign.GREEN


class StartUnit:
    def __init__(self, start_coord: Coord) -> None:
        self.rail: Rail = [start_coord]
        self.prev_units: list[UnitLike] = []
        self.prev_index: int = 0
        self.next_units: list[UnitLike] = [EndUnit([self])]
        self.next_index: int = 0

        self.situation: UnitSituation = UnitSituation.DEAD_END
        self.is_controlled: bool = False
        self.up_sign: Sign = Sign.RED
        self.down_sign: Sign = Sign.RED


class EndUnit:
    def __init__(self, prev_units: list[UnitLike]) -> None:
        self.prev_units: list[UnitLike] = prev_units
        self.prev_index: int = 0
        self.next_units: list[UnitLike] = []
        self.next_index: int = 0
        self.rail: Rail = [self.prev_units[self.prev_index].rail[-1]]

        self.situation: UnitSituation = UnitSituation.DEAD_END
        self.is_controlled: bool = False
        self.up_sign: Sign = Sign.RED
        self.down_sign: Sign = Sign.RED


class StraightUnit(MiddleUnitBase):
    def __init__(self, prev_units: list[UnitLike], length: float) -> None:
        super().__init__(prev_units)
        x0, y0 = self.prev_units[self.prev_index].rail[-1]
        self.rail = [(x0 + i, y0) for i in range(int(length))]
        self.next_units: list[UnitLike] = [EndUnit([self])]


class CurveUnit(MiddleUnitBase):
    def __init__(self, prev_units: list[UnitLike], vector: Coord) -> None:
        super().__init__(prev_units)
        self.rail = self._create_rail(vector)
        self.next_units: list[UnitLike] = [EndUnit([self])]

    def _create_rail(self, vector: Coord) -> Rail:
        start_coord = self.prev_units[self.prev_index].rail[-1]
        length = self._calc_length(vector)
        rail = []
        config = [
            start_coord,
            (start_coord[0] + vector[0] / 2, start_coord[1]),
            (start_coord[0] + vector[0] / 2, start_coord[1] + vector[1]),
            (start_coord[0] + vector[0], start_coord[1] + vector[1]),
        ]
        for i in range(1, int(length) + 1):
            t = i / length
            point = self._cubic_bezier(t, config)
            rail.append(point)
        return rail

    def _calc_length(self, vector: Coord, resolution: int = 1000) -> float:
        config = [
            (0, 0),
            (vector[0] / 2, 0),
            (vector[0] / 2, vector[1]),
            (vector[0], vector[1]),
        ]
        prev_point = config[0]
        total_length = 0.0
        for i in range(1, resolution + 1):
            t = i / resolution
            point = self._cubic_bezier(t, config)
            total_length += math.hypot(
                prev_point[0] - point[0], prev_point[1] - point[1]
            )
            prev_point = point
        return total_length

    @staticmethod
    def _cubic_bezier(t: float, config: list[Coord]) -> Coord:
        u = 1 - t
        x = (
            u**3 * config[0][0]
            + 3 * u**2 * t * config[1][0]
            + 3 * u * t**2 * config[2][0]
            + t**3 * config[3][0]
        )
        y = (
            u**3 * config[0][1]
            + 3 * u**2 * t * config[1][1]
            + 3 * u * t**2 * config[2][1]
            + t**3 * config[3][1]
        )
        return (x, y)


class StartSection:
    def __init__(self, start_coords: list[Coord]) -> None:
        self.units: list[UnitLike] = [
            StartUnit(start_coord) for start_coord in start_coords
        ]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]:
        return [[unit] for unit in self.units]


class EndSection:
    def __init__(self, prev_sect: SectionLike):
        prev_unit_list = prev_sect.exit_unit_list
        self.units: list[UnitLike] = [EndUnit(units) for units in prev_unit_list]
        for i in range(len(self.units)):
            prev_unit_list[i][0].next_units = [self.units[i]]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]:
        del self
        raise RuntimeError("EndSectionはexit_unit_listを持ちません。")


class NormalSection:
    def __init__(self, prev_sect: SectionLike, length: float) -> None:
        prev_unit_list = prev_sect.exit_unit_list
        self.units: list[UnitLike] = [
            StraightUnit(units, length) for units in prev_unit_list
        ]
        for i in range(len(self.units)):
            for unit in prev_unit_list[i]:
                unit.next_units = [self.units[i]]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]:
        return [[unit] for unit in self.units]


class CrossingSection:
    def __init__(self, prev_sect: SectionLike, vector: Coord) -> None:
        prev_unit_list = prev_sect.exit_unit_list
        self.units: list[UnitLike] = [
            StraightUnit(prev_unit_list[0], vector[0]),
            CurveUnit(prev_unit_list[0], vector),
            CurveUnit(prev_unit_list[1], (vector[0], -vector[1])),
            StraightUnit(prev_unit_list[1], vector[0]),
        ]
        for unit in prev_unit_list[0]:
            unit.next_units = [self.units[0], self.units[1]]
        for unit in prev_unit_list[1]:
            unit.next_units = [self.units[2], self.units[3]]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]:
        return [[self.units[0], self.units[2]], [self.units[1], self.units[3]]]

    def check_pass_allowed(self, unit_index: int) -> bool:
        if self.units[1].situation is UnitSituation.BLOCKED:
            return False
        if self.units[2].situation is UnitSituation.BLOCKED:
            return False
        if self.units[0].situation is UnitSituation.BLOCKED and unit_index != 3:
            return False
        if self.units[3].situation is UnitSituation.BLOCKED and unit_index != 0:
            return False
        return True


class BranchSection:
    def __init__(self, prev_sect: SectionLike, vector: Coord) -> None:
        prev_unit_list = prev_sect.exit_unit_list
        self.units: list[UnitLike] = [
            CurveUnit(prev_unit_list[0], (vector[0], -vector[1])),
            StraightUnit(prev_unit_list[0], vector[0]),
            StraightUnit(prev_unit_list[1], vector[0]),
            CurveUnit(prev_unit_list[1], vector),
        ]
        for unit in prev_unit_list[0]:
            unit.next_units = [self.units[0], self.units[1]]
        for unit in prev_unit_list[1]:
            unit.next_units = [self.units[2], self.units[3]]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]:
        return [[unit] for unit in self.units]


class MergeSection:
    def __init__(self, prev_sect: SectionLike, vector: Coord) -> None:
        prev_unit_list = prev_sect.exit_unit_list
        self.units: list[UnitLike] = [
            CurveUnit(prev_unit_list[0], vector),
            StraightUnit(prev_unit_list[1], vector[0]),
            StraightUnit(prev_unit_list[2], vector[0]),
            CurveUnit(prev_unit_list[3], (vector[0], -vector[1])),
        ]
        for i in range(4):
            for unit in prev_unit_list[i]:
                unit.next_units = [self.units[i]]

    @property
    def exit_unit_list(self) -> list[list[UnitLike]]:
        return [[self.units[0], self.units[1]], [self.units[2], self.units[3]]]


class Line:
    def __init__(self, line_file: LineFile) -> None:
        self.sections: list[SectionLike] = self._create_sections(line_file["sections"])
        self.stations: dict[str, list[MiddleUnitBase]] = self._create_stations(
            line_file["stations"]
        )

    @staticmethod
    def get_next_pos(
        curr_unit: MiddleUnitBase, curr_index: int
    ) -> tuple[MiddleUnitBase, int]:
        if curr_index < 0:
            next_unit = curr_unit.prev_units[curr_unit.prev_index]
            next_index = curr_index + (len(next_unit.rail) - 1)
            while next_index < 0:
                next_unit = next_unit.prev_units[next_unit.prev_index]
                next_index = next_index + (len(next_unit.rail) - 1)
        elif curr_index > (len(curr_unit.rail) - 1):
            next_index = curr_index - (len(curr_unit.rail) - 1)
            next_unit = curr_unit.next_units[curr_unit.next_index]
            while next_index > (len(next_unit.rail) - 1):
                next_index = next_index - (len(next_unit.rail) - 1)
                next_unit = next_unit.next_units[next_unit.next_index]
        else:
            (next_unit, next_index) = (curr_unit, curr_index)
        if not isinstance(next_unit, MiddleUnitBase):
            raise RuntimeError("行き止まりです。")
        _next_unit = cast(MiddleUnitBase, next_unit)
        return (_next_unit, next_index)

    def update_sign(self) -> None:
        for i in range(1, len(self.sections) - 1):
            for unit in self.sections[i].units:
                if unit.is_controlled:
                    pass
                elif unit.situation is UnitSituation.OCCUPIED:
                    unit.up_sign = Sign.RED
                    unit.down_sign = Sign.RED
                else:
                    unit.up_sign = Sign.GREEN
                    unit.down_sign = Sign.GREEN
                    if (
                        unit.next_units[unit.next_index].situation
                        is UnitSituation.OCCUPIED
                    ):
                        unit.down_sign = Sign.YELLOW
                    if (
                        unit.prev_units[unit.prev_index].situation
                        is UnitSituation.OCCUPIED
                    ):
                        unit.up_sign = Sign.YELLOW

    @staticmethod
    def _create_sections(section_data: list[SectionItem]) -> list[SectionLike]:
        sections: list[SectionLike] = []
        for section in section_data:
            if section["type"] == "start":
                start_coords = cast(list[Coord], section["start"])
                sections.append(StartSection(start_coords))
            elif section["type"] == "normal":
                length = cast(float, section["length"])
                sections.append(NormalSection(sections[-1], length))
            elif section["type"] == "crossing":
                vector = cast(Coord, section["vector"])
                sections.append(CrossingSection(sections[-1], vector))
            elif section["type"] == "merge":
                vector = cast(Coord, section["vector"])
                sections.append(MergeSection(sections[-1], vector))
            elif section["type"] == "branch":
                vector = cast(Coord, section["vector"])
                sections.append(BranchSection(sections[-1], vector))
            elif section["type"] == "end":
                sections.append(EndSection(sections[-1]))
        return sections

    def _create_stations(
        self, station_data: list[StationItem]
    ) -> dict[str, list[MiddleUnitBase]]:
        stations = {}
        for station in station_data:
            if station["sect_index"] in (0, len(self.sections) - 1):
                raise RuntimeError("sect_index is out of range.")
            _units = cast(
                list[MiddleUnitBase], self.sections[station["sect_index"]].units
            )
            stations[station["name"]] = _units
        return stations


class Train:
    def __init__(
        self,
        stations: dict[str, list[MiddleUnitBase]],
        train: TrainDef,
        schedule: TimetableEntry,
    ) -> None:
        self.train_id: str = train["id"]
        self.max_speed: int = train["max_speed"]
        self.speed_limit: int = self.max_speed
        self.color: Color = train["color"]

        self.number: int = schedule["number"]
        self.schedule: list[ScheduleItem] = schedule["schedule"]
        self.progress: int = 0

        self.curr_unit: MiddleUnitBase = stations[train["init_stn"]][
            train["init_track"]
        ]
        self.curr_index: int = len(self.curr_unit.rail) // 2
        self.curr_speed: float = 0
        self.process_time: int = 0
        self.direction: Direction = Direction.NEUTRAL
        self.situation: TrainSituation = TrainSituation.WAITTING
        self.past_unit: MiddleUnitBase = self.curr_unit

    def update(self, curr_minutes: int, line: Line) -> None:
        if self.situation == TrainSituation.WAITTING:
            self._departure(curr_minutes, line)
        elif self.situation == TrainSituation.MOVING:
            self._move(line)

        if self.past_unit != self.curr_unit:
            self.past_unit.situation = UnitSituation.FREE
            self.curr_unit.situation = UnitSituation.OCCUPIED
            self.past_unit = self.curr_unit

    def _departure(self, curr_minutes: int, line: Line) -> None:
        if self.progress >= len(self.schedule) - 1:
            return
        if not self.schedule[self.progress]["dep_time"]:
            raise RuntimeError("dep_time is not defined.")
        if curr_minutes < cast(int, self.schedule[self.progress]["dep_time"]):
            return
        if self.schedule[self.progress]["direction"] == Direction.FORWARD.name:
            self.direction = Direction.FORWARD
        elif self.schedule[self.progress]["direction"] == Direction.BACKWARD.name:
            self.direction = Direction.BACKWARD
        self.progress += 1
        target_stn = self.schedule[self.progress]["station"]
        target_track = self.schedule[self.progress]["track"]
        self.target_unit = line.stations[target_stn][target_track]
        self.situation = TrainSituation.MOVING

    def _move(self, line: Line) -> None:  # signal add
        if self.direction == Direction.FORWARD:
            sign = self.curr_unit.next_units[self.curr_unit.next_index].down_sign
        elif self.direction == Direction.BACKWARD:
            sign = self.curr_unit.prev_units[self.curr_unit.prev_index].up_sign
        if sign == Sign.GREEN:
            self.speed_limit = self.max_speed
        elif sign == Sign.YELLOW:
            self.speed_limit = 1
        else:
            remain_dist = (
                len(self.curr_unit.rail) // 2 - self.curr_index
            ) * self.direction.value
            if remain_dist < 0:
                self.curr_speed = 0

        if self.curr_unit != self.target_unit:
            self._accelerate()
        else:
            self._decelerate()
        next_index = self.curr_index + int(self.curr_speed * self.direction.value)
        self.curr_unit, self.curr_index = line.get_next_pos(self.curr_unit, next_index)

    def _accelerate(self) -> None:
        if self.process_time > 0:
            self.process_time -= 1
        elif self.curr_speed < self.speed_limit:
            self.curr_speed += 1
            self.process_time = 30

    def _decelerate(self) -> None:
        remain_dist = abs(len(self.target_unit.rail) // 2 - self.curr_index)
        dece_dist = self.curr_speed * (self.curr_speed - 1) * 10
        if remain_dist <= self.curr_speed:
            self.curr_index = len(self.target_unit.rail) // 2
            self.curr_speed = 0
            self.direction = Direction.NEUTRAL
            self.situation = TrainSituation.WAITTING
        elif remain_dist <= dece_dist and self.curr_speed > 1:
            self.curr_speed -= 1
