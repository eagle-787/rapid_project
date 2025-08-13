from enum import Enum


class Sign(Enum):
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    YELLOW = (255, 255, 0)

    @property
    def color(self):
        return self.value


class StonevaleControl:#0:merge, 1:normal, 2:crossing, 3:normal
    def __init__(self, line, timetable):
        self.sections = [line.sections[i] for i in range(2, 6)]
        self.timetable = timetable
        self.progress = 0
        self.arr_track = 0

        for section in self.sections:
            for unit in section.units:
                unit.is_controled = True
        
        for unit in self.sections[0].units:
            unit.down_sign = Sign.RED
        for i in (1, 3):
            self.sections[2].units[i].up_sign = Sign.RED
    
    def update(self):
        for i in range(4):
            if self.sections[0].units[i].is_occupied:
                self.sections[0].units[i].down_sign = Sign.RED
        for i in range(1, 3):
            if self.sections[2].units[i].is_occupied:
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

    def _cleared_for_dep(self):
        schedule = self.timetable[self.progress]
        if schedule["track"] < 2:
            self.sections[1].units[0].select_prev_unit(schedule["track"])
            self.sections[1].units[0].select_next_unit(0)
            self.sections[3].units[0].select_prev_unit(0)
            self.sections[1].units[0].is_blocked = True
            self.sections[2].units[0].is_blocked = True
        else:
            self.sections[1].units[1].select_prev_unit(schedule["track"] - 2)
            self.sections[1].units[1].select_next_unit(0)
            self.sections[3].units[0].select_prev_unit(1)
            self.sections[1].units[1].is_blocked = True
            self.sections[2].units[2].is_blocked = True
        self.sections[0].units[schedule["track"]].down_sign = Sign.GREEN

    def _cleared_to_arr(self):
        self.arr_track = self.timetable[self.progress]["track"]
        if self.arr_track < 2:
            self.sections[1].units[0].select_prev_unit(self.arr_track)
            self.sections[1].units[0].select_next_unit(1)
            self.sections[3].units[1].select_prev_unit(0)
            self.sections[1].units[0].is_blocked = True
            self.sections[2].units[1].is_blocked = True
            self.sections[2].units[1].up_sign = Sign.GREEN
        else:
            self.sections[1].units[1].select_prev_unit(self.arr_track - 2)
            self.sections[1].units[1].select_next_unit(1)
            self.sections[3].units[1].select_prev_unit(1)
            self.sections[1].units[1].is_blocked = True
            self.sections[2].units[3].is_blocked = True
            self.sections[2].units[3].up_sign = Sign.GREEN

    def _check_pass_allowed(self):
        schedule = self.timetable[self.progress]
        if schedule["number"] % 2 == 1:
            if self.sections[3].units[0].is_occupied:
                return False
            if schedule["track"] < 2:
                if not self.sections[1].units[0].is_blocked \
                    and self.sections[2].check_pass_allowed(0):
                    return True
            else:
                if not self.sections[1].units[1].is_blocked \
                    and self.sections[2].check_pass_allowed(2):
                    return True
        else:
            if self.sections[schedule["track"]].units[0].is_occupied:
                return False
            if schedule["track"] < 2:
                if not self.sections[1].units[0].is_blocked \
                    and self.sections[2].check_pass_allowed(3):
                    return True
            else:
                if not self.sections[1].units[1].is_blocked \
                    and self.sections[2].check_pass_allowed(3):
                    return True
        return False


class AshmoorControl:#0:normal, 1:crossing, 2:stn
    def __init__(self, line, timetable):
        self.sections = [line.sections[i] for i in range(9, 12)]
        self.timetable = timetable
        self.progress = 0
        self.arr_track = 0
        
        for section in self.sections:
            for unit in section.units:
                unit.is_controled = True
        for i in (2, 3):
            self.sections[1].units[i].up_sign = Sign.RED
        for i in (0, 1):
            self.sections[1].units[i].down_sign = Sign.RED
    
    def update(self):
        for i in (0, 1):
            if self.sections[1].units[i].is_occupied:
                self.sections[1].units[i].down_sign = Sign.RED
        for i in (2, 3):
            if self.sections[1].units[i].is_occupied:
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

    def _cleared_for_dep(self):
        schedule = self.timetable[self.progress]
        if schedule["track"] == 0:
            self.sections[0].units[1].select_next_unit(0)
            self.sections[2].units[0].select_prev_unit(1)
            self.sections[1].units[2].is_blocked = True
            self.sections[1].units[2].up_sign = Sign.GREEN
        else:
            self.sections[0].units[1].select_next_unit(1)
            self.sections[2].units[1].select_prev_unit(1)
            self.sections[1].units[3].is_blocked = True
            self.sections[1].units[3].up_sign = Sign.GREEN

    def _cleared_to_arr(self):
        self.arr_track = self.timetable[self.progress]["track"]
        if self.arr_track == 0:
            self.sections[0].units[0].select_next_unit(0)
            self.sections[2].units[0].select_prev_unit(0)
            self.sections[1].units[0].is_blocked = True
            self.sections[1].units[0].down_sign = Sign.GREEN
        else:
            self.sections[0].units[0].select_next_unit(1)
            self.sections[2].units[1].select_prev_unit(0)
            self.sections[1].units[1].is_blocked = True
            self.sections[1].units[1].down_sign = Sign.GREEN

    def _check_pass_allowed(self):
        schedule = self.timetable[self.progress]
        if schedule["number"] % 2 == 0: #dep
            if self.sections[0].units[1].is_occupied:
                return False
            if schedule["track"] == 0:
                if self.sections[1].check_pass_allowed(2):
                    return True
            else:
                if self.sections[1].check_pass_allowed(3):
                    return True
        else: #arr
            if self.sections[2].units[schedule["track"]].is_occupied:
                return False
            if schedule["track"] == 0:
                if self.sections[1].check_pass_allowed(0):
                    return True
            else:
                if self.sections[1].check_pass_allowed(1):
                    return True
        return False
