"""Compatibility namespace for the field recheck ticket vocabulary."""

from ..missing_review.contracts import ReviewHold, ReviewOrder, ScenarioBand
from ..missing_review.service import *  # noqa: F401,F403
from ..missing_review.service import (  # noqa: F401
    build_review_orders,
    candidate_combinations,
    evaluate_review,
    reconcile_review_orders,
)

RecheckOrder = ReviewOrder
RecheckHold = ReviewHold
RecheckScenario = ScenarioBand
build_recheck_orders = build_review_orders
build_recheck_order = evaluate_review
recheck_missing_waves = build_review_orders
reconcile_recheck_orders = reconcile_review_orders

__all__ = (
    'ReviewHold', 'ReviewOrder', 'ScenarioBand', 'RecheckOrder', 'RecheckHold',
    'RecheckScenario', 'build_review_orders', 'evaluate_review',
    'candidate_combinations', 'reconcile_review_orders', 'build_recheck_orders',
    'build_recheck_order', 'recheck_missing_waves', 'reconcile_recheck_orders',
)
