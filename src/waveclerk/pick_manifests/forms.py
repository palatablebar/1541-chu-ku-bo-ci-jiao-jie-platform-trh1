from collections.abc import Mapping
from decimal import Decimal

from .contracts import MeasureIssue


from dataclasses import dataclass


def form_number(form, sheet, name, minimum, maximum):
    from .service import number

    table = form.get(sheet)
    if not isinstance(table, Mapping):
        raise MeasureIssue(sheet, 'FORM_SECTION_REQUIRED')
    return Decimal(str(number(table.get(name), name, minimum, maximum)))


@dataclass(frozen=True, slots=True)
class PickManifestsSheet:
    order_lines: Decimal
    bulky_basis_points: Decimal
    signed_workers: Decimal
    path_centimetres: Decimal
    merging_orders: Decimal
    truck_slack_seconds: Decimal

    def fields(self):
        return {
            'lines': float(self.order_lines),
            'bulk_share': float(self.bulky_basis_points) / 100,
            'pickers': float(self.signed_workers),
            'walk_m': float(self.path_centimetres) / 100,
            'merge_orders': float(self.merging_orders),
            'slack_min': float(self.truck_slack_seconds) / 60,
        }

    def validation(self):
        fields = self.fields()
        lines = fields['lines']
        bulk_share = fields['bulk_share']
        pickers = fields['pickers']
        walk_m = fields['walk_m']
        merge_orders = fields['merge_orders']
        slack_min = fields['slack_min']
        allocated_lifts = lines*bulk_share/100
        expected_load = walk_m*lines/pickers
        effective_minutes = slack_min-6
        collector_pressure = merge_orders/max(1,pickers)
        alerts = []
        if collector_pressure > 24:
            alerts.append(('assigned', 'MERGE_LOAD_NEEDS_FOREMAN'))
        if effective_minutes <= 0:
            alerts.append(('truck', 'TRUCK_ALREADY_DUE'))
        if allocated_lifts > 120 and expected_load > 10000:
            alerts.append(('bulk', 'TWO_MAN_BULK_SHIFT_REQUIRED'))
        return tuple(alerts)


def read_pick_manifests(form):
    return PickManifestsSheet(
        order_lines=form_number(form, '批拣单', 'order_lines', 20, 210),
        bulky_basis_points=form_number(form, '批拣单', 'bulky_basis_points', 100, 5800),
        signed_workers=form_number(form, '班组签到', 'signed_workers', 2, 15),
        path_centimetres=form_number(form, '班组签到', 'path_centimetres', 4000, 40000),
        merging_orders=form_number(form, '装车时标', 'merging_orders', 0, 65),
        truck_slack_seconds=form_number(form, '装车时标', 'truck_slack_seconds', 1080, 7500),
    )


def explicit_rows(form):
    if not isinstance(form, Mapping):
        raise MeasureIssue('form', 'FORM_OBJECT_REQUIRED')
    note = read_pick_manifests(form)
    return note.fields(), note.validation()


def check_native_history(source):
    if not isinstance(source, Mapping) or 'form' not in source:
        return source
    if any(key in source for key in ('lines', 'bulk_share', 'pickers', 'walk_m', 'merge_orders', 'slack_min')):
        raise MeasureIssue('form','MIXED_FORM_AND_FLAT_READING')
    converted, flags = explicit_rows(source['form'])
    if flags:
        raise MeasureIssue(*flags[0])
    return {**source, **converted}
