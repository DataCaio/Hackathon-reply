"""Resolution-independent directed gate crossing."""

from __future__ import annotations

from dataclasses import dataclass

from hackathon_reply.contracts.domain import CountGate as DomainCountGate
from hackathon_reply.contracts.domain import FrameMeta


class GateError(ValueError):
    """Raised when a gate crossing input is malformed."""


@dataclass(frozen=True)
class CountGate:
    """Gate contract supporting both explicit endpoints and legacy helpers."""

    p1_norm: tuple[float, float]
    p2_norm: tuple[float, float]
    direction: str = "entry_to_exit"
    epsilon: float = 1e-6

    def __post_init__(self) -> None:
        if self.p1_norm == self.p2_norm:
            raise GateError("count gate endpoints must differ")
        if self.direction not in {"entry_to_exit", "exit_to_entry"}:
            raise GateError("count gate direction is invalid")
        if self.epsilon < 0:
            raise GateError("gate epsilon must be non-negative")

    @classmethod
    def vertical(
        cls,
        *,
        normalized_x: float,
        flow_direction: str = "positive",
        epsilon: float = 1e-6,
    ) -> "CountGate":
        if flow_direction not in {"positive", "negative"}:
            raise GateError("flow_direction must be positive or negative")
        direction = "entry_to_exit" if flow_direction == "positive" else "exit_to_entry"
        return cls((normalized_x, 0.0), (normalized_x, 1.0), direction, epsilon)

    def normalized_point(
        self,
        point_px: tuple[float, float],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float]:
        return (point_px[0] / frame_width, point_px[1] / frame_height)

    def side(self, point_norm: tuple[float, float]) -> float:
        return side_of_gate(point_norm, self)

    def crossed(self, previous_side: float, current_side: float) -> bool:
        if self.direction == "entry_to_exit":
            return previous_side > self.epsilon and current_side < -self.epsilon
        return previous_side < -self.epsilon and current_side > self.epsilon


def side_of_gate(point_norm: tuple[float, float], count_gate: DomainCountGate | CountGate) -> float:
    """Return the signed side of the directed gate line."""

    dx = count_gate.p2_norm[0] - count_gate.p1_norm[0]
    dy = count_gate.p2_norm[1] - count_gate.p1_norm[1]
    px = point_norm[0] - count_gate.p1_norm[0]
    py = point_norm[1] - count_gate.p1_norm[1]
    return dx * py - dy * px


def crossed_gate(
    previous_point_norm: tuple[float, float],
    current_point_norm: tuple[float, float],
    count_gate: DomainCountGate | CountGate,
    *,
    epsilon: float = 1e-9,
) -> bool:
    """Return true only for one directed transition across the gate line."""

    if epsilon < 0:
        raise GateError("epsilon must be non-negative")
    previous_side = side_of_gate(previous_point_norm, count_gate)
    current_side = side_of_gate(current_point_norm, count_gate)
    if count_gate.direction == "entry_to_exit":
        return previous_side > epsilon and current_side < -epsilon
    return previous_side < -epsilon and current_side > epsilon


def normalized_centroid(
    centroid_px: tuple[float, float],
    meta: FrameMeta,
) -> tuple[float, float]:
    """Convert an original-frame centroid to resolution-independent coordinates."""

    return (centroid_px[0] / meta.width, centroid_px[1] / meta.height)


def crossed_gate_pixels(
    previous_centroid_px: tuple[float, float],
    current_centroid_px: tuple[float, float],
    meta: FrameMeta,
    count_gate: CountGate,
    *,
    epsilon: float = 1e-9,
) -> bool:
    return crossed_gate(
        normalized_centroid(previous_centroid_px, meta),
        normalized_centroid(current_centroid_px, meta),
        count_gate,
        epsilon=epsilon,
    )
