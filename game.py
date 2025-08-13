import math, os, json
from enum import Enum, auto
from control import StonevaleControl, AshmoorControl, Sign


class Signal:
    def __init__(self):
        self.sign = Sign.RED
        self.track = -1
    
    def set_green(self, track=-1):
        self.track = track
        self.sign = Sign.GREEN
    
    def set_red(self):
        self.track = -1
        self.sign = Sign.RED


#unit attitude: rail, prev_unit, next_unit, signal-rerated attitudes
class StartUnit:
    def __init__(self, start_coord):
        self.prev_units = [self]
        self.selected_prev_unit = self
        self.rail = [start_coord]

        self.is_occupied = True
        self.up_sign = Sign.RED

    def set_next_units(self, next_units):
        self.next_units = next_units
        self.selected_next_unit = next_units[0]


class EndUnit:
    def __init__(self, prev_units):
        self.prev_units = prev_units
        self.selected_prev_unit = prev_units[0]
        self.rail = [prev_units[0].rail[-1]]

        self.is_occupied = True
        self.down_sign = Sign.RED


class StraightUnit:
    def __init__(self, length, prev_units):
        self.prev_units = prev_units
        self.selected_prev_unit = prev_units[0]

        start_coord = prev_units[0].rail[-1]
        self.rail = self._create_rail(start_coord, length)

        self.is_occupied = False
        self.is_blocked = False
        self.is_controled = False
        self.up_sign = Sign.GREEN
        self.down_sign = Sign.GREEN

    def set_next_units(self, next_units):
        self.next_units = next_units
        self.selected_next_unit = next_units[0]

    def select_prev_unit(self, index):
        self.selected_prev_unit = self.prev_units[index]

    def select_next_unit(self, index):
        self.selected_next_unit = self.next_units[index]

    def _create_rail(self, start_coord, length):
        return [(start_coord[0] + i, start_coord[1])
                     for i in range(length)]


class CurveUnit:
    def __init__(self, vector, prev_units):        
        self.prev_units = prev_units
        self.selected_prev_unit = prev_units[0]

        start_coord = prev_units[0].rail[-1]
        length = self._calc_length(vector)
        self.rail = self._create_rail(start_coord, vector, length)

        self.is_occupied = False
        self.is_blocked = False
        self.is_controled = False
        self.up_sign = Sign.GREEN
        self.down_sign = Sign.GREEN

    def set_next_units(self, next_units):
        self.next_units = next_units
        self.selected_next_unit = next_units[0]

    def select_prev_unit(self, index):
        self.selected_prev_unit = self.prev_units[index]

    def select_next_unit(self, index):
        self.selected_next_unit = self.next_units[index]

    def _calc_length(self, vector, resolution=1000):
        config = [(0, 0), (vector[0] // 2, 0),
                  (vector[0] // 2, vector[1]), (vector[0], vector[1])]
        prev_point = config[0]
        total_length = 0
        for i in range(1, resolution + 1):
            t = i / resolution
            point = self._cubic_bezier(t, config)
            total_length += math.hypot(prev_point[0] - point[0], prev_point[1] - point[1])
            prev_point = point
        return int(total_length)

    def _create_rail(self, start_coord, vector, length):
        rail = []
        config = [start_coord,
                  (start_coord[0] + vector[0] // 2, start_coord[1]),
                  (start_coord[0] + vector[0] // 2, start_coord[1] + vector[1]),
                  (start_coord[0] + vector[0], start_coord[1] + vector[1])]
        for i in range(1, length + 1):
            t = i / length
            point = self._cubic_bezier(t, config)
            rail.append(point)
        return rail

    @staticmethod
    def _cubic_bezier(t, config):
        u = 1 - t
        x = u**3 * config[0][0] + 3 * u**2 * t * config[1][0] \
            + 3 * u * t**2 * config[2][0] + t**3 * config[3][0]
        y = u**3 * config[0][1] + 3 * u**2 * t * config[1][1] \
            + 3 * u * t**2 * config[2][1] + t**3 * config[3][1]
        return (x, y)


#section attitude: units
class StartSection:
    def __init__(self, start_coords):
        self.units = [StartUnit(start_coord) for start_coord in start_coords]

    def get_units(self):
        return [[unit] for unit in self.units]


class EndSection:
    def __init__(self, prev_sect, num_units):
        prev_unit_list = prev_sect.get_units()
        self.units = [EndUnit(prev_unit_list[i]) for i in range(num_units)]
        self._set_next_unit_of_prev_sect(num_units, prev_unit_list)

    def get_units(self):
        return [[unit] for unit in self.units]

    def _set_next_unit_of_prev_sect(self, num_units, prev_unit_list):
        for i in range(num_units):
            for unit in prev_unit_list[i]:
                unit.set_next_units([self.units[i]])


class NormalSection:
    def __init__(self, prev_sect, num_units, length):
        prev_unit_list = prev_sect.get_units()
        self.units = [StraightUnit(length, prev_unit_list[i]) for i in range(num_units)]
        self._set_next_unit_of_prev_sect(num_units, prev_unit_list)

    def get_units(self):
        return [[unit] for unit in self.units]
    
    def _set_next_unit_of_prev_sect(self, num_units, prev_unit_list):
        for i in range(num_units):
            for unit in prev_unit_list[i]:
                unit.set_next_units([self.units[i]])


class CrossingSection:
    def __init__(self, prev_sect, r_vector):
        prev_unit_list = prev_sect.get_units()
        self.units = self._create_units(r_vector, prev_unit_list)
        self._set_next_unit_of_prev_sect(prev_unit_list)

    def get_units(self):
        return [[self.units[0], self.units[2]], [self.units[1], self.units[3]]]
    
    def check_pass_allowed(self, unit_index):
        if not self.units[1].is_blocked and not self.units[2].is_blocked:
            if not self.units[0].is_blocked and not self.units[3].is_blocked:
                return True
            if unit_index in (0, 3) and not self.units[unit_index].is_blocked:
                return True
        return False

    def _create_units(self, r_vector, prev_unit_list):
        units = [StraightUnit(r_vector[0], prev_unit_list[0]),
                 CurveUnit(r_vector, prev_unit_list[0]),
                 CurveUnit((r_vector[0], -r_vector[1]), prev_unit_list[1]),
                 StraightUnit(r_vector[0], prev_unit_list[1])]
        return units

    def _set_next_unit_of_prev_sect(self, prev_unit_list):
        for unit in prev_unit_list[0]:
            unit.set_next_units([self.units[0], self.units[1]])
        for unit in prev_unit_list[1]:
            unit.set_next_units([self.units[2], self.units[3]])


class BranchSection:
    def __init__(self, prev_sect, r_vector, l_vector):
        prev_unit_list = prev_sect.get_units()
        self.units = self._create_units(r_vector, l_vector, prev_unit_list)
        self._set_next_unit_of_prev_sect(prev_unit_list)
    
    def get_units(self):
        return [[unit] for unit in self.units]

    def _create_units(self, r_vector, l_vector, prev_unit_list):
        units = [CurveUnit(l_vector, prev_unit_list[0]),
                 StraightUnit(l_vector[0], prev_unit_list[0]),
                 StraightUnit(r_vector[0], prev_unit_list[1]),
                 CurveUnit(r_vector, prev_unit_list[1])]
        return units

    def _set_next_unit_of_prev_sect(self, prev_unit_list):
        for unit in prev_unit_list[0]:
            unit.set_next_units([self.units[0], self.units[1]])
        for unit in prev_unit_list[1]:
            unit.set_next_units([self.units[2], self.units[3]])


class MergeSection:
    def __init__(self, prev_sect, r_vector, l_vector):
        prev_unit_list = prev_sect.get_units()
        self.units = self._create_units(r_vector, l_vector, prev_unit_list)
        self._set_next_unit_of_prev_sect(prev_unit_list)
    
    def get_units(self):
        return [[self.units[0], self.units[1]], [self.units[2], self.units[3]]]
    
    def _create_units(self, r_vector, l_vector, prev_unit_list):
        units = [CurveUnit(r_vector, prev_unit_list[0]),
                 StraightUnit(l_vector[0], prev_unit_list[1]),
                 StraightUnit(r_vector[0], prev_unit_list[2]),
                 CurveUnit(l_vector, prev_unit_list[3])]
        return units
    
    def _set_next_unit_of_prev_sect(self, prev_unit_list):
        for i in range(4):
            for unit in prev_unit_list[i]:
                unit.set_next_units([self.units[i]])


class Line:
    def __init__(self, line_file):
        self.sections, self.stations = self._create_line(line_file)

    def get_next_pos(self, curr_unit, curr_index):
        if curr_index < 0:
            next_unit = curr_unit.selected_prev_unit
            next_index = curr_index + (len(next_unit.rail) - 1)
            while next_index < 0:
                next_unit = next_unit.selected_prev_unit
                next_index = next_index + (len(next_unit.rail) - 1)
        elif curr_index > (len(curr_unit.rail) - 1):
            next_index = curr_index - (len(curr_unit.rail) - 1)
            next_unit = curr_unit.selected_next_unit
            while next_index > (len(next_unit.rail) - 1):
                next_index = next_index - (len(next_unit.rail) - 1)
                next_unit = next_unit.selected_next_unit
        else:
            (next_unit, next_index) = (curr_unit, curr_index)
        return (next_unit, next_index)

    def update_sign(self):
        for i in range(1, len(self.sections) - 1):
            for unit in self.sections[i].units:
                if unit.is_controled:
                    pass
                elif unit.is_occupied:
                    unit.up_sign = Sign.RED
                    unit.down_sign = Sign.RED
                else:
                    unit.up_sign = Sign.GREEN
                    unit.down_sign = Sign.GREEN
                    if unit.selected_next_unit.is_occupied:
                        unit.down_sign = Sign.YELLOW
                    if unit.selected_prev_unit.is_occupied:
                        unit.up_sign = Sign.YELLOW


    def _create_line(self, line_file):
        section_data = line_file["sections"]
        station_data = line_file["stations"]
        sections = [None] * len(section_data)
        stations = {}

        for i, section in enumerate(section_data):
            if section["type"] == "start":
                start_coords = [(section["start_x"], y) for y in section["start_y"]]
                sections[i] = StartSection(start_coords)
            elif section["type"] == "normal":
                sections[i] = NormalSection(sections[i - 1], section["num_units"], section["length"])
            elif section["type"] == "crossing":
                sections[i] = CrossingSection(sections[i - 1], section["r_vector"])
            elif section["type"] == "merge":
                sections[i] = MergeSection(sections[i - 1], section["r_vector"], section["l_vector"])
            elif section["type"] == "branch":
                sections[i] = BranchSection(sections[i - 1], section["r_vector"], section["l_vector"])
            elif section["type"] == "end":
                sections[i] = EndSection(sections[i - 1], section["num_units"])

        for station in station_data:
            stations[station["name"]] = [unit for unit in sections[station["sect_index"]].units]
        return sections, stations


class Situation(Enum):
    WAITTING = auto()
    MOVING = auto()


class Direction(Enum):
    FORWARD = 1
    NEUTRAL = 0
    BACKWARD = -1


class Train:
    def __init__(self, line, train, schedule):
        self.train_id = train["id"]
        self.max_speed = train["max_speed"]
        self.speed_limit = self.max_speed
        self.color = train["color"]

        self.number = schedule["number"]
        self.schedule = schedule["schedule"]
        self.progress = 0

        self.curr_unit = line.stations[train["init_stn"]][train["init_track"]]
        self.curr_index = len(self.curr_unit.rail) // 2
        self.curr_speed = 0
        self.process_time = 0
        self.direction = Direction.NEUTRAL
        self.situation = Situation.WAITTING
        self.past_unit = self.curr_unit

    def update(self, curr_minutes, line):        
        if self.situation == Situation.WAITTING:
            self._departure(curr_minutes, line)
        elif self.situation == Situation.MOVING:
            self._move(line)

        if self.past_unit != self.curr_unit:
            self.past_unit.is_occupied = False
            self.past_unit.is_blocked = False
            self.curr_unit.is_occupied = True
            self.past_unit = self.curr_unit
            
    def _departure(self, curr_minutes, line):
        if self.progress >= len(self.schedule) - 1:
            return
        if curr_minutes < self.schedule[self.progress]["dep_time"]:
            return
        if self.schedule[self.progress]["direction"] == Direction.FORWARD.name:
            self.direction = Direction.FORWARD
        elif self.schedule[self.progress]["direction"] == Direction.BACKWARD.name:
            self.direction = Direction.BACKWARD
        self.progress += 1
        target_stn = self.schedule[self.progress]["station"]
        target_track = self.schedule[self.progress]["track"]
        self.target_unit = line.stations[target_stn][target_track]
        self.situation = Situation.MOVING

    def _move(self, line): #signal add
        if self.direction == Direction.FORWARD:
            sign = self.curr_unit.selected_next_unit.down_sign
        elif self.direction == Direction.BACKWARD:
            sign = self.curr_unit.selected_prev_unit.up_sign
        if sign == Sign.GREEN:
            self.speed_limit = self.max_speed
        elif sign == Sign.YELLOW:
            self.speed_limit = 1
        else:
            remain_dist = (len(self.curr_unit.rail) // 2 - self.curr_index) * self.direction.value
            if remain_dist < 0:
                self.curr_speed = 0

        if self.curr_unit != self.target_unit:
            self._accelerate()
        else:
            self._decelerate()
        next_index = self.curr_index + self.curr_speed * self.direction.value
        self.curr_unit, self.curr_index = line.get_next_pos(self.curr_unit, next_index)

    def _accelerate(self):
        if self.process_time > 0:
                self.process_time -= 1
        elif self.curr_speed < self.speed_limit:
            self.curr_speed += 1
            self.process_time = 30

    def _decelerate(self):
        remain_dist = abs(len(self.target_unit.rail) // 2 - self.curr_index)
        dece_dist = self.curr_speed * (self.curr_speed - 1) * 10
        if remain_dist <= self.curr_speed:
            self.curr_index = len(self.target_unit.rail) // 2
            self.curr_speed = 0
            self.direction = Direction.NEUTRAL
            self.situation = Situation.WAITTING
        elif remain_dist <= dece_dist and self.curr_speed > 1:
            self.curr_speed -= 1


class Game:
    def __init__(self):
        self.line_file = self._get_json_file("line.json")
        self.timetable_file = self._get_json_file("timetable.json")
        self.line = Line(self.line_file)
        self.stonevale_control = StonevaleControl(self.line, self.timetable_file["Stonevale"])
        self.ashmoor_control = AshmoorControl(self.line, self.timetable_file["Ashmoor"])
        self.trains = self._create_train(self.timetable_file)
    
    def update(self, tick, curr_minutes):
        if tick % 30 == 0:
            self.line.update_sign()
            self.stonevale_control.update()
            self.ashmoor_control.update()
        for train in self.trains:
            train.update(curr_minutes, self.line)
    
    def _get_json_file(self, file_name):
        base_path = os.path.dirname(__file__)
        json_path = os.path.join(base_path, file_name)
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _create_train(self, timetable_file):
        train_data = timetable_file["train"]
        timetable_data = timetable_file["timetable"]
        trains = []
        for train in train_data:
            for schedule in timetable_data:
                if schedule["train"] == train["id"]:
                    trains.append(Train(self.line, train, schedule))
                    break
        return trains
