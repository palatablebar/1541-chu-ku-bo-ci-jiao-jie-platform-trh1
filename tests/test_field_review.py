from waveclerk.pipeline import preview
from waveclerk.aisle_dispatch.service import operating_ledger


def note(key, measures, *, zone='甲区', state='已分派', estimate=0, hits=(), missing=()):
    return {'key':key,'zone':zone,'state':state,'estimate':estimate,'hits':hits,
            'unmeasured':missing,'measurements':dict(zip(('lines', 'bulk_share', 'pickers', 'walk_m', 'merge_orders', 'slack_min'),measures,strict=True))}


def test_field_plan_is_visible_and_references_real_tickets():
    desk = preview()
    plan = desk['sections'][6]
    assert plan['operating_title'] == '装车交接账'
    assert plan['operating_rows']
    scoped = {item['关联单据'] for item in plan['operating_rows'] if '关联单据' in item}
    assert scoped and scoped <= {row['key'] for row in desk['rows']}
    assert all(item['业务安排'] for item in plan['operating_rows'])


def test_handoff_counts_only_assigned_aisle_work():
    current = note('W-1',(130,32,3,280,35,20),estimate=30)
    later = note('W-2',(75,20,8,120,2,22),estimate=16,state='候补')
    frozen = note('W-3',(120,52,3,200,12,42),estimate=80,state='暂停')
    records = operating_ledger([later,frozen,current])
    shortlist = {row.get('关联单据'):row for row in records}
    assert shortlist['W-3']['业务安排']=='叉车通道核签'
    assert shortlist['W-1']['是否纳入当前排班']
    assert not shortlist['W-2']['是否纳入当前排班']
    assert records[-1]['已占合箱至']==33
