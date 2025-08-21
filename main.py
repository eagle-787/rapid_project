import pygame
import sys
import json
from pathlib import Path
from view.drawer import Drawer, SignalDrawer, Camera
from core.module import Train, Line
from core.control import Starting4TrackControl, Terminal2TrackControl
from core.type_hint import (
    Color,
    Size,
    LineFile,
    TimetableFile,
    ControlLike,
    TrainDef,
    TimetableEntry,
)


class Game:
    def __init__(self) -> None:
        self.line_file: LineFile = self._get_json_file("line.json")
        self.timetable_file: TimetableFile = self._get_json_file("timetable.json")
        self.line: Line = Line(self.line_file)
        self.starting_control: ControlLike = Starting4TrackControl(
            self.line.sections, self.timetable_file["StartingStn"]
        )
        self.terminal_control: ControlLike = Terminal2TrackControl(
            self.line.sections, self.timetable_file["TerminalStn"]
        )
        self.trains: list[Train] = self._create_train(
            self.timetable_file["train"], self.timetable_file["timetable"]
        )

    def update(self, tick: int, curr_minutes: int) -> None:
        if tick % 30 == 0:
            self.line.update_sign()
            self.starting_control.update()
            self.terminal_control.update()
        for train in self.trains:
            train.update(curr_minutes, self.line)

    @staticmethod
    def _get_json_file(file_name):
        base_path = Path(__file__).resolve().parent
        json_path = base_path / file_name
        with json_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _create_train(
        self, train_data: list[TrainDef], timetable_data: list[TimetableEntry]
    ) -> list[Train]:
        trains = []
        for train in train_data:
            for schedule in timetable_data:
                if schedule["train"] == train["id"]:
                    trains.append(Train(self.line.stations, train, schedule))
                    break
        return trains


class Time:
    def __init__(self) -> None:
        self.ticks_per_minute: int = 60
        self.curr_minutes: int = 358

    def update(self, tick: int) -> None:
        if tick % self.ticks_per_minute == 0:
            self.curr_minutes += 1
        if self.curr_minutes >= 24 * 60:
            pygame.quit()
            sys.exit()


class Main:
    SCREEN_SIZE: Size = (1920, 1080)
    SCREEN_COLOR: Color = (255, 255, 255)
    SIM_SIZE: Size = (3840, 1080)

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(self.SCREEN_SIZE)
        self.clock = pygame.time.Clock()

        self.camera: Camera = Camera(self.SIM_SIZE)
        self.time: Time = Time()
        self.game: Game = Game()

        self.drawer: Drawer = Drawer(
            self.SIM_SIZE, self.screen, self.camera, self.game.line, self.game.trains
        )
        self.signal_drawer: SignalDrawer = SignalDrawer(
            self.screen,
            self.camera,
            self.game.line,
            self.game.starting_control,
            self.game.terminal_control,
        )

        self.tick: int = 0

    def run(self) -> None:
        while True:
            self.screen.fill(self.SCREEN_COLOR)
            self.clock.tick(60)
            self.tick += 1

            self.time.update(self.tick)
            self.game.update(self.tick, self.time.curr_minutes)

            self.drawer.draw(self.time.curr_minutes)
            self.signal_drawer.draw()

            self.__handle_event()
            pygame.display.flip()

    def __handle_event(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.camera.move_left()
        elif keys[pygame.K_d]:
            self.camera.move_right()


if __name__ == "__main__":
    simulator = Main()
    simulator.run()
