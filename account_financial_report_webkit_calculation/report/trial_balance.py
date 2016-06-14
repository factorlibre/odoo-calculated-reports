# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.addons.celery_report_calculation_base.decorators \
    import get_calculation_context


@get_calculation_context
def trial_balance__init__(self, cr, uid, name, context):
    trial_balance__init__.origin(self, cr, uid, name, context)


@get_calculation_context
def trial_balance_xls__init__(self, cr, uid, name, context):
    trial_balance__init__.origin(self, cr, uid, name, context)
