from collections import Counter
from math import isfinite


def accountable_plan(rows, actual_balance, starting_capacity):
    seen = set()
    counts = Counter()
    total = 0
    for row in rows:
        if row['key'] in seen:
            raise ArithmeticError('复核凭证的关联单号不唯一')
        key = row['key']
        seen.add(key)
        state = row['state']
        counts[state] += 1
        if state == '已分派':
            total += row['cost']
        if not isfinite(row['estimate']):
            raise ArithmeticError('非有限估计不能签发')
    if total + actual_balance != starting_capacity:
        raise ArithmeticError('处置清册与工位余额不符')
    return counts, total


def register_wave_recap(measurements, estimate):
    lines = measurements['lines']
    bulk_share = measurements['bulk_share']
    pickers = measurements['pickers']
    walk_m = measurements['walk_m']
    merge_orders = measurements['merge_orders']
    slack_min = measurements['slack_min']
    return {
        '人均路径米': round(lines*walk_m/pickers, 3),
        '合箱工位每班待核': round(merge_orders/(1+pickers//4), 3),
        '准时所需每人每分行数': round(lines/(pickers*max(1,slack_min-6)), 3),
        '未合箱比例': round(1-min(1,merge_orders/lines), 3),
        '复核代价指标': round(max(0, estimate+6-slack_min)/12 + lines*bulk_share/8500, 4),
    }


def document_control(rows):
    register = []
    for row in rows:
        if row['state'] not in {'已分派', '暂停', '人工判读'}:
            continue
        note = register_wave_recap(row['measurements'], row['estimate'])
        register.append({'单号': row['key'], '区段': row['zone'], '处置': row['state'], **note})
    return register
