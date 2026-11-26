from collections import defaultdict
from math import fsum
from statistics import median


def groups_for_completion_bands(raw):
    lines, bulk_share, pickers, walk_m, merge_orders, slack_min = raw
    if slack_min<=35:
        yield '快到装车线'
    if bulk_share>=40 and lines>=100:
        yield '大件混拼'
    if merge_orders>=36:
        yield '合箱工位吃紧'
    if pickers<=5:
        yield '班组人手紧'
    if walk_m>=240:
        yield '远端货位'

def window_losses(view, line):
    actual = view.raw.outcome
    if not view.raw.observed or actual is None:
        return None
    calendar = view.estimate-actual
    urgent = actual >= line
    accounted = view.estimate >= line
    overrun = actual-line if urgent and not accounted else None
    lower = view.lower
    upper = view.upper
    missing_band = lower is None or upper is None
    breach = None if missing_band else actual < lower or actual > upper
    return calendar, overrun, breach


def replay_slices(points, threshold, *, risk_model=False):
    eligible = defaultdict(list)
    for judgment in points:
        loss = window_losses(judgment,threshold)
        if loss is None:
            continue
        for work_area in groups_for_completion_bands(judgment.raw.input_values):
            eligible[work_area].append(loss)
    table = []
    for title in ('快到装车线', '大件混拼', '合箱工位吃紧', '班组人手紧', '远端货位'):
        decisions = eligible[title]
        if not decisions:
            table.append({'难点':title,'实绩数':0,'状态':'未到实绩回报时间'})
            continue
        deltas = [bias for bias,_,_ in decisions]
        delays = [loss for _,loss,_ in decisions if loss is not None]
        violations = [observed for _,_,observed in decisions if observed is not None]
        table.append({'难点':title,'实绩数':len(decisions),'容量偏置中位':round(median(deltas),4),
                      '低估超线':len(delays),'最差超线余量':round(max(delays,default=0),3),
                      '超线累计损失':round(fsum(delays),3),'区间可识别实绩':len(violations),
                      '未覆盖实绩':sum(violations)})
    return table
