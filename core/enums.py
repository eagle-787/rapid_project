from enum import Enum, auto


class Sign(Enum):
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    YELLOW = (255, 255, 0)


class TrainSituation(Enum):
    WAITTING = auto()
    MOVING = auto()


class UnitSituation(Enum):
    OCCUPIED = auto()
    BLOCKED = auto()
    FREE = auto()
    DEAD_END = auto()


class Direction(Enum):
    FORWARD = 1
    NEUTRAL = 0
    BACKWARD = -1
