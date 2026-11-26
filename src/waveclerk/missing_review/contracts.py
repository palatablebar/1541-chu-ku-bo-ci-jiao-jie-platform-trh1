from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReviewHold:
    state: str
    reason: str
    summary: str
    rule_hits: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScenarioBand:
    combination: tuple[tuple[str, float], ...]
    source_keys: tuple[str, ...]
    source_cohort: str
    values: tuple[float, ...]
    estimate: float
    lower: float | None
    upper: float | None
    side: str
    excursions: tuple[str, ...]
    rule_hits: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewOrder:
    review_id: str
    key: str
    cohort: str
    missing: tuple[str, ...]
    status: str
    reason: str
    message: str
    feature_stamp: str
    calibration_method: str
    calibration_size: int
    buffer_line: float | None
    grace_min: int
    scenarios: tuple[ScenarioBand, ...]
    min_upper: float | None
    max_upper: float | None
    side: str | None
    crosses_buffer: bool
    holds_dispatch: bool
    hold_state: str | None
    rule_hits: tuple[str, ...]
