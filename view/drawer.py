import math
import pygame
from ..core.enums import Sign
from ..core.type_hint import Color, Coord, ControlLike, Size
from ..core.module import Line, Train


class Camera:
    MOVE_DX: int = 12

    def __init__(self, sim_size: Size, offset_x: int = 0) -> None:
        self.sim_size: Size = sim_size
        self.offset_x: int = offset_x

    def apply(self, pos: Coord) -> Coord:
        return (pos[0] - self.offset_x, pos[1])

    def move_right(self) -> None:
        if self.offset_x < self.sim_size[0]:
            self.offset_x += self.MOVE_DX

    def move_left(self) -> None:
        if self.offset_x > 0:
            self.offset_x -= self.MOVE_DX


class SignalDrawer:
    COLOR: Color = (128, 128, 128)
    LIGHT_OUT_COLOR: Color = (105, 105, 105)
    SIZE: Size = (36, 72)
    Y: tuple[int, int, int, int] = (264, 384, 564, 684)
    R: int = 6

    def __init__(
        self,
        screen,
        camera: Camera,
        line: Line,
        starting_control: ControlLike,
        terminal_control: ControlLike,
    ) -> None:
        self.screen = screen
        self.camera: Camera = camera
        self.line: Line = line
        self.starting_control: ControlLike = starting_control
        self.terminal_control: ControlLike = terminal_control
        self.track_font = pygame.font.Font(
            "/home/kohei/apps/train_sim/rapid_project/DSEG7Modern-Bold.ttf", 48
        )

    def draw(self) -> None:
        self._draw_signal0()
        self._draw_signal1()
        self._draw_signal2()

    def _draw_signal0(self) -> None:
        for i in range(4):
            sign = self.line.sections[2].units[i].down_sign
            signal_coord = (self.line.sections[2].units[i].rail[0][0], self.Y[i])
            self._draw_sign_unit(signal_coord, sign)

        sign1 = self.line.sections[4].units[1].up_sign
        sign3 = self.line.sections[4].units[3].up_sign
        if sign1 == Sign.GREEN or sign3 == Sign.GREEN:
            sign = Sign.GREEN
        else:
            sign = Sign.RED
        track = self.starting_control.arr_track + 1
        signal_coord = (self.line.sections[4].units[3].rail[-1][0], self.Y[2])
        self._draw_sign_unit(signal_coord, sign)
        signal_coord = (signal_coord[0] + self.SIZE[0], signal_coord[1])
        self._draw_track_unit(signal_coord, sign, track)

    def _draw_signal1(self) -> None:
        unit = self.line.sections[8].units[0]
        signal_coord = (unit.rail[0][0], self.Y[1])
        self._draw_sign_unit(signal_coord, unit.down_sign)

        unit = self.line.sections[6].units[1]
        signal_coord = (unit.rail[-self.SIZE[0]][0], self.Y[2])
        self._draw_sign_unit(signal_coord, unit.up_sign)

    def _draw_signal2(self) -> None:
        for i in (0, 1):
            unit = self.line.sections[10].units[i + 2]
            signal_coord = (unit.rail[-self.SIZE[0]][0], self.Y[i + 1])
            self._draw_sign_unit(signal_coord, unit.up_sign)

        sign0 = self.line.sections[10].units[0].down_sign
        sign1 = self.line.sections[10].units[1].down_sign
        if sign0 == Sign.GREEN or sign1 == Sign.GREEN:
            sign = Sign.GREEN
        else:
            sign = Sign.RED
        track = self.terminal_control.arr_track + 1
        signal_coord = (self.line.sections[10].units[0].rail[0][0], self.Y[1])
        self._draw_sign_unit(signal_coord, sign)
        signal_coord = (signal_coord[0] + self.SIZE[0], signal_coord[1])
        self._draw_track_unit(signal_coord, sign, track)

    def _draw_track_unit(self, signal_coord: Coord, sign: Sign, track: int) -> None:
        (x, y) = self.camera.apply(signal_coord)
        pygame.draw.rect(
            self.screen, self.COLOR, (x, y, *self.SIZE), border_radius=self.R
        )
        if sign == Sign.GREEN:
            sign_track_surface = self.track_font.render(
                str(track), True, (255, 255, 255)
            )
            self.screen.blit(sign_track_surface, (x - 1, y + 12))

    def _draw_sign_unit(self, signal_coord, sign):
        (x, y) = self.camera.apply(signal_coord)
        pygame.draw.rect(
            self.screen, self.COLOR, (x, y, *self.SIZE), border_radius=self.R
        )
        if sign == Sign.RED:
            top_color = sign.value
            bottom_color = self.LIGHT_OUT_COLOR
        else:
            top_color = self.LIGHT_OUT_COLOR
            bottom_color = sign.value
        pygame.draw.circle(
            self.screen, top_color, (x + self.SIZE[0] // 2, y + self.SIZE[1] // 4), 16
        )
        pygame.draw.circle(
            self.screen,
            bottom_color,
            (x + self.SIZE[0] // 2, y + self.SIZE[1] // 4 * 3),
            16,
        )


class Drawer:
    LINE_COLOR: Color = (105, 105, 105)
    LINE_WIDTH: int = 6
    TRAIN_SIZE: Size = (108, 48)
    TRAIN_R: int = 6

    STN_COLOR: Color = (176, 196, 222)
    STN_SIZE: Size = (360, 72)
    STN_Y: tuple[int, int] = (384, 564)
    STN_R: int = 6

    def __init__(
        self, sim_size: Size, screen, camera: Camera, line: Line, trains: list[Train]
    ) -> None:
        self.screen = screen
        self.camera: Camera = camera
        self.line: Line = line
        self.trains: list[Train] = trains
        self.font = pygame.font.SysFont(None, 100)
        self.rail_surface = pygame.Surface(sim_size, pygame.SRCALPHA)
        self._rail_cache()

    def draw(self, curr_minutes: int) -> None:
        self._draw_line()
        self._draw_time(curr_minutes)
        self._draw_train()
        self._draw_station()

    def _draw_train(self) -> None:
        for train in self.trains:
            self._draw_car(train, self.TRAIN_SIZE[0] + 2)
            self._draw_car(train, 0)
            self._draw_car(train, -self.TRAIN_SIZE[0] - 2)

    def _draw_car(self, train: Train, offset: int) -> None:
        curr_index = train.curr_index + offset
        curr_unit, curr_index = self.line.get_next_pos(train.curr_unit, curr_index)
        curr_pos = curr_unit.rail[curr_index]

        next_index = curr_index + int(train.curr_speed * train.direction.value)
        next_unit, next_index = self.line.get_next_pos(curr_unit, next_index)
        next_pos = next_unit.rail[next_index]

        dx = next_pos[0] - curr_pos[0]
        dy = next_pos[1] - curr_pos[1]
        angle = math.degrees(math.atan2(-dy, dx))

        surface = pygame.Surface(self.TRAIN_SIZE, pygame.SRCALPHA)
        pygame.draw.rect(
            surface, train.color, (0, 0, *self.TRAIN_SIZE), border_radius=self.TRAIN_R
        )
        rotated_surface = pygame.transform.rotate(surface, angle)
        (x, y) = self.camera.apply(curr_pos)
        rect = rotated_surface.get_rect(center=(x, y))
        self.screen.blit(rotated_surface, rect)

    def _draw_time(self, curr_minutes: int) -> None:
        time_str = self._get_time_str(curr_minutes)
        time_surface = self.font.render(time_str, True, (0, 0, 0))
        self.screen.blit(time_surface, (60, 60))

    def _draw_line(self) -> None:
        (x, y) = self.camera.apply((0, 0))
        view_rect = pygame.Rect(
            -x, y, self.screen.get_width(), self.screen.get_height()
        )
        self.screen.blit(self.rail_surface, (0, 0), area=view_rect)

    def _draw_station(self) -> None:
        for station in self.line.stations.values():
            stn_x = station[0].rail[0][0]
            for stn_y in self.STN_Y:
                (x, y) = self.camera.apply((stn_x, stn_y))
                pygame.draw.rect(
                    self.screen,
                    self.STN_COLOR,
                    (x, y, *self.STN_SIZE),
                    border_radius=self.STN_R,
                )

    def _get_time_str(self, curr_minutes: int) -> str:
        hour = curr_minutes // 60
        minute = curr_minutes % 60
        return f"{hour:02}:{minute:02}"

    def _rail_cache(self) -> None:
        for section in self.line.sections:
            for unit in section.units:
                for coord in unit.rail:
                    pygame.draw.circle(
                        self.rail_surface, self.LINE_COLOR, coord, self.LINE_WIDTH
                    )
