from dataclasses import dataclass
from math import sqrt, fsum
from statistics import median


@dataclass(frozen=True, slots=True)
class DomainStudy:
    counts: tuple[int, int, int]
    rate: float | None
    midpoint: float | None
    expected: float | None
    drift: float | None

def order_mix_domains(vectors):
    travel_per_picker = []
    truck_buffer = []
    merge_pressure = []
    bulk_lift = []
    small_pick = []
    walk_to_load = []
    wave_takt = []
    merge_ready = []
    for measurement in vectors:
        unobserved = frozenset(measurement.missing)
        lines, bulk_share, pickers, walk_m, merge_orders, slack_min = measurement.input_values
        if unobserved.isdisjoint(('lines', 'pickers', 'walk_m', 'slack_min')):
            travel_per_picker.append((round(lines*walk_m/pickers, 4), slack_min<=35))
        if unobserved.isdisjoint(('lines', 'bulk_share', 'slack_min')):
            truck_buffer.append((round(slack_min-6, 4), bulk_share>=40 and lines>=100))
        if unobserved.isdisjoint(('pickers', 'merge_orders')):
            merge_pressure.append((round(merge_orders/(1+pickers//4), 4), merge_orders>=36))
        if unobserved.isdisjoint(('lines', 'bulk_share', 'pickers')):
            bulk_lift.append((round(lines*bulk_share/100, 4), pickers<=5))
        if unobserved.isdisjoint(('lines', 'bulk_share', 'walk_m')):
            small_pick.append((round(lines*(100-bulk_share)/100, 4), walk_m>=240))
        if unobserved.isdisjoint(('walk_m', 'slack_min')):
            walk_to_load.append((round(walk_m/max(1,slack_min), 4), slack_min<=35))
        if unobserved.isdisjoint(('lines', 'bulk_share', 'pickers', 'slack_min')):
            wave_takt.append((round(lines/(pickers*max(1,slack_min-6)), 4), bulk_share>=40 and lines>=100))
        if unobserved.isdisjoint(('lines', 'merge_orders')):
            merge_ready.append((round(1-min(1,merge_orders/lines), 4), merge_orders>=36))
    return {
        '人均路径米 · 快到装车线': tuple(travel_per_picker),
        '交接净余时 · 大件混拼': tuple(truck_buffer),
        '合箱工位每班待核 · 合箱工位吃紧': tuple(merge_pressure),
        '大件通道有效行 · 班组人手紧': tuple(bulk_lift),
        '小件通道行数 · 远端货位': tuple(small_pick),
        '相对装车路径 · 快到装车线': tuple(walk_to_load),
        '准时所需每人每分行数 · 大件混拼': tuple(wave_takt),
        '未合箱比例 · 合箱工位吃紧': tuple(merge_ready),
    }


def evaluate_domains(training, current):
    references = order_mix_domains(training)
    activity = order_mix_domains(current)
    diagnostics = []
    for domain, observed in activity.items():
        baseline = references.get(domain, ())
        study = characterize(baseline, observed)
        diagnostics.append({'观察维度': domain, '训练有效量': study.counts[0], '当班有效量': study.counts[1],
                            '越线量':study.counts[2], '越线比例':study.rate, '参考中位':study.midpoint,
                            '当班中位':study.expected, '相对训练变化':study.drift})
    return diagnostics


def characterize(before, after):
    history = tuple(value for value, _ in before)
    observed = tuple(value for value, _ in after)
    violating = sum(flag for _, flag in after)
    old = median(history) if history else None
    new = median(observed) if observed else None
    pct = round(violating / len(after), 4) if after else None
    movement = round(new - old, 4) if old is not None and new is not None else None
    return DomainStudy((len(before),len(after),violating),pct,old,new,movement)
