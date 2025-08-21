from typing import cast
from .enums import Sign, UnitSituation
from .type_hint import SectionLike
from .module import CrossingSection


class Starting4TrackControl:  # 0:merge, 1:normal, 2:crossing, 3:normal
    def __init__(
        self, sections: list[SectionLike], timetable: list[dict[str, int]]
    ) -> None:
        self.sections: list[SectionLike] = [sections[i] for i in range(2, 6)]
        self.timetable: list[dict[str, int]] = timetable
        self.progress: int = 0
        self.arr_track: int = 0

        for section in self.sections:
            for unit in section.units:
                unit.is_controlled = True
        for unit in self.sections[0].units:
            unit.down_sign = Sign.RED
        for i in (1, 3):
            self.sections[2].units[i].up_sign = Sign.RED

    def update(self) -> None:
        for i in range(4):
            if self.sections[0].units[i].situation is UnitSituation.OCCUPIED:
                self.sections[0].units[i].down_sign = Sign.RED
        for i in range(1, 3):
            if self.sections[2].units[i].situation is UnitSituation.OCCUPIED:
                self.sections[2].units[i].up_sign = Sign.RED

        if self.progress > len(self.timetable) - 1:
            return
        if not self._check_pass_allowed():
            return
        if self.timetable[self.progress]["number"] % 2 == 1:
            self._cleared_for_dep()
        else:
            self._cleared_to_arr()
        self.progress += 1

    def _cleared_for_dep(self) -> None:
        schedule = self.timetable[self.progress]
        if schedule["track"] < 2:
            self.sections[1].units[0].prev_index = schedule["track"]
            self.sections[1].units[0].next_index = 0
            self.sections[3].units[0].prev_index = 0
            self.sections[1].units[0].situation = UnitSituation.BLOCKED
            self.sections[2].units[0].situation = UnitSituation.BLOCKED
        else:
            self.sections[1].units[1].prev_index = schedule["track"] - 2
            self.sections[1].units[1].next_index = 0
            self.sections[3].units[0].prev_index = 1
            self.sections[1].units[1].situation = UnitSituation.BLOCKED
            self.sections[2].units[2].situation = UnitSituation.BLOCKED
        self.sections[0].units[schedule["track"]].down_sign = Sign.GREEN

    def _cleared_to_arr(self) -> None:
        self.arr_track = self.timetable[self.progress]["track"]
        if self.arr_track < 2:
            self.sections[1].units[0].prev_index = self.arr_track
            self.sections[1].units[0].next_index = 1
            self.sections[3].units[1].prev_index = 0
            self.sections[1].units[0].situation = UnitSituation.BLOCKED
            self.sections[2].units[1].situation = UnitSituation.BLOCKED
            self.sections[2].units[1].up_sign = Sign.GREEN
        else:
            self.sections[1].units[1].prev_index = self.arr_track - 2
            self.sections[1].units[1].next_index = 1
            self.sections[3].units[1].prev_index = 1
            self.sections[1].units[1].situation = UnitSituation.BLOCKED
            self.sections[2].units[3].situation = UnitSituation.BLOCKED
            self.sections[2].units[3].up_sign = Sign.GREEN

    def _check_pass_allowed(self) -> bool:
        schedule = self.timetable[self.progress]
        if not isinstance(self.sections[2], CrossingSection):
            raise TypeError("sections 2 is not a CrossingSection.")
        crossing_section = cast(CrossingSection, self.sections[2])
        if schedule["number"] % 2 == 1:
            if self.sections[3].units[0].situation is UnitSituation.OCCUPIED:
                return False
            if schedule["track"] < 2:
                if self.sections[1].units[
                    0
                ].situation is not UnitSituation.BLOCKED and crossing_section.check_pass_allowed(
                    0
                ):
                    return True
            else:
                if self.sections[1].units[
                    1
                ].situation is not UnitSituation.BLOCKED and crossing_section.check_pass_allowed(
                    2
                ):
                    return True
        else:
            if (
                self.sections[schedule["track"]].units[0].situation
                is UnitSituation.OCCUPIED
            ):
                return False
            if schedule["track"] < 2:
                if self.sections[1].units[
                    0
                ].situation is not UnitSituation.BLOCKED and crossing_section.check_pass_allowed(
                    3
                ):
                    return True
            else:
                if self.sections[1].units[
                    1
                ].situation is not UnitSituation.BLOCKED and crossing_section.check_pass_allowed(
                    3
                ):
                    return True
        return False


class Terminal2TrackControl:  # 0:normal, 1:crossing, 2:stn
    def __init__(
        self, sections: list[SectionLike], timetable: list[dict[str, int]]
    ) -> None:
        self.sections: list[SectionLike] = [sections[i] for i in range(9, 12)]
        self.timetable: list[dict[str, int]] = timetable
        self.progress: int = 0
        self.arr_track: int = 0

        for section in self.sections:
            for unit in section.units:
                unit.is_controlled = True
        for i in (2, 3):
            self.sections[1].units[i].up_sign = Sign.RED
        for i in (0, 1):
            self.sections[1].units[i].down_sign = Sign.RED

    def update(self) -> None:
        for i in (0, 1):
            if self.sections[1].units[i].situation is UnitSituation.OCCUPIED:
                self.sections[1].units[i].down_sign = Sign.RED
        for i in (2, 3):
            if self.sections[1].units[i].situation is UnitSituation.OCCUPIED:
                self.sections[1].units[i].up_sign = Sign.RED

        if self.progress > len(self.timetable) - 1:
            return
        if not self._check_pass_allowed():
            return
        if self.timetable[self.progress]["number"] % 2 == 0:
            self._cleared_for_dep()
        else:
            self._cleared_to_arr()
        self.progress += 1

    def _cleared_for_dep(self) -> None:
        schedule = self.timetable[self.progress]
        if schedule["track"] == 0:
            self.sections[0].units[1].next_index = 0
            self.sections[2].units[0].prev_index = 1
            self.sections[1].units[2].situation = UnitSituation.BLOCKED
            self.sections[1].units[2].up_sign = Sign.GREEN
        else:
            self.sections[0].units[1].next_index = 1
            self.sections[2].units[1].prev_index = 1
            self.sections[1].units[3].situation = UnitSituation.BLOCKED
            self.sections[1].units[3].up_sign = Sign.GREEN

    def _cleared_to_arr(self) -> None:
        self.arr_track = self.timetable[self.progress]["track"]
        if self.arr_track == 0:
            self.sections[0].units[0].next_index = 0
            self.sections[2].units[0].prev_index = 0
            self.sections[1].units[0].situation = UnitSituation.BLOCKED
            self.sections[1].units[0].down_sign = Sign.GREEN
        else:
            self.sections[0].units[0].next_index = 1
            self.sections[2].units[1].prev_index = 0
            self.sections[1].units[1].situation = UnitSituation.BLOCKED
            self.sections[1].units[1].down_sign = Sign.GREEN

    def _check_pass_allowed(self) -> bool:
        schedule = self.timetable[self.progress]
        if not isinstance(self.sections[1], CrossingSection):
            raise TypeError("sections 1 is not a CrossingSection.")
        crossing_section = cast(CrossingSection, self.sections[1])
        if schedule["number"] % 2 == 0:  # dep
            if self.sections[0].units[1].situation is UnitSituation.OCCUPIED:
                return False
            if schedule["track"] == 0:
                if crossing_section.check_pass_allowed(2):
                    return True
            else:
                if crossing_section.check_pass_allowed(3):
                    return True
        else:  # arr
            if (
                self.sections[2].units[schedule["track"]].situation
                is UnitSituation.OCCUPIED
            ):
                return False
            if schedule["track"] == 0:
                if crossing_section.check_pass_allowed(0):
                    return True
            else:
                if crossing_section.check_pass_allowed(1):
                    return True
        return False
