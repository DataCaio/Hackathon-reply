"""Resolution-independent count-gate geometry."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from hackathon_reply.contracts import Point


@dataclass(frozen=True)
class CountGate:
    start: Point
    end: Point
    flow_direction: int = 1
    epsilon: float = 1e-9

    def __post_init__(self) -> None:
        if hypot(self.end[0] - self.start[0], self.end[1] - self.start[1]) == 0:
            raise ValueError("count gate must have non-zero length")
        if self.flow_direction not in {-1, 1}:
            raise ValueError("flow_direction must be 1 or -1")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive")

    @classmethod
    def vertical(cls, normalized_x: float, flow_direction: str = "positive") -> "CountGate":
        if not 0 <= normalized_x <= 1:
            raise ValueError("normalized_x must be within 0..1")
        return cls((normalized_x, 0.0), (normalized_x, 1.0), _direction(flow_direction))

    @classmethod
    def horizontal(cls, normalized_y: float, flow_direction: str = "positive") -> "CountGate":
        if not 0 <= normalized_y <= 1:
            raise ValueError("normalized_y must be within 0..1")
        return cls((0.0, normalized_y), (1.0, normalized_y), _direction(flow_direction))

    def side(self, normalized_point: Point) -> float:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length = hypot(dx, dy)
        # The right-hand normal makes positive flow increase x for a vertical gate.
        normal = (dy / length, -dx / length)
        return (
            (normalized_point[0] - self.start[0]) * normal[0]
            + (normalized_point[1] - self.start[1]) * normal[1]
        )

    def crossed(self, previous_side: float, current_side: float) -> bool:
        if self.flow_direction == 1:
            return previous_side <= -self.epsilon and current_side >= self.epsilon
        return previous_side >= self.epsilon and current_side <= -self.epsilon

    def normalized_point(self, point: Point, width: int, height: int) -> Point:
        if width <= 0 or height <= 0:
            raise ValueError("frame dimensions must be positive")
        return (point[0] / width, point[1] / height)


def _direction(value: str) -> int:
    if value == "positive":
        return 1
    if value == "negative":
        return -1
    raise ValueError("flow_direction must be positive or negative")
