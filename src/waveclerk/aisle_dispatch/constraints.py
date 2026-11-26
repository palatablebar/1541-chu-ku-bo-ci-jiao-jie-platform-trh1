from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Job


@dataclass(frozen=True, slots=True)
class WorkOrder:
    job: Job
    assessment: Any

    def __post_init__(self):
        if self.job.key != self.assessment.raw.key:
            raise ValueError('处置工位与单据不匹配')


def apply_aisle_dispatch(waves, admit: Callable, wait: Callable):
    active_aisles = Counter()
    for wave in waves:
        ticket = wave.assessment
        lines, bulk, pickers, distance, merges, slack = ticket.raw.input_values
        if active_aisles[wave.job.cohort] >= 2 and merges >= 40:
            wait(wave, 'MERGE_BENCH_OCCUPIED', '本通道的合箱复核工位已占用')
            continue
        # A third picking wave cannot catch up after its truck grace time.
        if slack <= 22 and ticket.estimate > slack and pickers <= 4:
            wait(wave, 'TRUCK_CALL_REQUIRED', '请求值班长确认是否换装车位')
            continue
        if admit(wave):
            active_aisles[wave.job.cohort] += int(merges >= 28 or distance >= 175)
