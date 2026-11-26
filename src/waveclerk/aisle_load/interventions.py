from dataclasses import replace
from statistics import median

from .contracts import AisleLoad, Proposal


def measure_aisle_load(values) -> AisleLoad:
    lines, bulk_share, pickers, walk_m, merge_orders, slack_min = values
    return AisleLoad(
        travel_per_picker=lines*walk_m/pickers,
        truck_buffer=slack_min-6,
        merge_pressure=merge_orders/(1+pickers//4),
        bulk_lift=lines*bulk_share/100,
        small_pick=lines*(100-bulk_share)/100,
        walk_to_load=walk_m/max(1,slack_min),
        wave_takt=lines/(pickers*max(1,slack_min-6)),
        merge_ready=1-min(1,merge_orders/lines),
    )


def propose_aisle_dispatch(values, missing=()):
    lines, bulk_share, pickers, walk_m, merge_orders, slack_min = values
    if 'pickers' not in missing and (pickers<=13 and bulk_share<49):
        yield Proposal('补两名拣货员', 'pickers', pickers, min(15,pickers+2), 2)
    if 'merge_orders' not in missing and (merge_orders>=14):
        yield Proposal('先拆合箱队列', 'merge_orders', merge_orders, max(0,merge_orders-14), 1)
    if 'walk_m' not in missing and (walk_m>=109):
        yield Proposal('改用近端集货区', 'walk_m', walk_m, max(40,walk_m-65), 1)
    if 'slack_min' not in missing and (slack_min<=110):
        yield Proposal('协商装车顺延', 'slack_min', slack_min, min(125,slack_min+15), 0)
