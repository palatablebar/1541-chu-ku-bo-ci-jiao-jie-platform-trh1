def collect_truck_load(measures, missing, estimate):
    slack_min = measures['slack_min']
    if not (slack_min<=24 or estimate>=slack_min-6):
        return None
    value=slack_min-estimate-6
    return {'现场复核':'装车交接','可复查值':round(value,3),'单位':'分钟','归档要求':'先核对装车预约并给出完成缓冲',
            '需补测':not set(missing).isdisjoint(('slack_min',))}


def collect_long_aisle(measures, missing, estimate):
    walk_m = measures['walk_m']
    if not (walk_m>=225):
        return None
    value=walk_m/60
    return {'现场复核':'远巷查位','可复查值':round(value,3),'单位':'路径分','归档要求':'确认集货料位与通道单向标识',
            '需补测':not set(missing).isdisjoint(('walk_m',))}


def collect_merge_table(measures, missing, estimate):
    merge_orders = measures['merge_orders']
    if not (merge_orders>=25):
        return None
    value=merge_orders
    return {'现场复核':'合箱清点','可复查值':round(value,3),'单位':'订单','归档要求':'盘点合箱待处理单并对齐架号',
            '需补测':not set(missing).isdisjoint(('merge_orders',))}


def collect_heavy_pack(measures, missing, estimate):
    lines = measures['lines']
    bulk_share = measures['bulk_share']
    if not (bulk_share>=32):
        return None
    value=lines*bulk_share/100
    return {'现场复核':'大件复核','可复查值':round(value,3),'单位':'行','归档要求':'记录大件通道与叉车放行人',
            '需补测':not set(missing).isdisjoint(('lines', 'bulk_share'))}


def check_wave_recap(records):
    guide = []
    for ticket in records:
        if ticket['state'] not in ('已分派','暂停','人工判读'):
            continue
        measures=ticket['measurements']
        absent=ticket['unmeasured']
        estimate=ticket['estimate']
        checks = (
            collect_truck_load(measures,absent,estimate),
            collect_long_aisle(measures,absent,estimate),
            collect_merge_table(measures,absent,estimate),
            collect_heavy_pack(measures,absent,estimate),
        )
        required=tuple(check for check in checks if check is not None)
        if not required:
            continue
        review=ticket['key']
        for check in required:
            guide.append({'签收单':review,'作业区':ticket['zone'],'处置':ticket['state'],**check})
    return guide
