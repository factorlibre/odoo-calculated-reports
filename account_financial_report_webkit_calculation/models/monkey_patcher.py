# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
from openerp import models
from openerp.addons.celery_report_calculation_base.decorators \
    import _patch_class_method

# To patch classes
# Common Reports
from openerp.addons.account_financial_report_webkit.report.common_reports \
    import CommonReportHeaderWebkit
# Trial balance
from openerp.addons.account_financial_report_webkit.report.trial_balance \
    import TrialBalanceWebkit
from openerp.addons.account_financial_report_webkit_xls.report.\
    trial_balance_xls import trial_balance_xls
# General ledger
from openerp.addons.account_financial_report_webkit.report.general_ledger \
    import GeneralLedgerWebkit
from openerp.addons.account_financial_report_webkit_xls.report.\
    general_ledger_xls import general_ledger_xls
# Partner Ledger
from openerp.addons.account_financial_report_webkit.report.partners_ledger \
    import PartnersLedgerWebkit
from openerp.addons.account_financial_report_webkit_xls.report.\
    partner_ledger_xls import partner_ledger_xls

# To Patch methods
from ..report.common_report import _has_ledger_lines
from ..report.trial_balance import (
    trial_balance__init__, trial_balance_xls__init__)
from ..report.general_ledger import (
    general_ledger__init__,
    _pre_compute_account_ledger_lines, _compute_account_ledger_lines,
    _general_ledger_get_ledger_lines_data, general_ledger_set_context)
from ..report.general_ledger_xls import (
    general_ledger_generate_xls_report, general_ledger__get_new_ws)
from ..report.partners_ledger import (
    partner_ledger__init__, _compute_partner_ledger_lines,
    partner_ledger_set_context, _partner_ledger_get_ledger_lines_data,
    _pre_compute_partner_ledger_lines)
from ..report.partners_ledger_xls import (
    partners_ledger_generate_xls_report, partners_ledger__get_new_ws)

_logger = logging.getLogger(__name__)


class FinancialReportsMonkeyPatcher(models.AbstractModel):
    _name = 'financial.reports.monkey.patcher'

    def _register_hook(self, cr):
        # Common Reports
        _patch_class_method(
            CommonReportHeaderWebkit, '_has_ledger_lines', _has_ledger_lines)
        # Trial Balance
        _patch_class_method(
            TrialBalanceWebkit, '__init__', trial_balance__init__)
        _patch_class_method(
            trial_balance_xls, '__init__', trial_balance_xls__init__)
        # General Ledger
        _patch_class_method(GeneralLedgerWebkit, '__init__',
                            general_ledger__init__)
        _patch_class_method(
            GeneralLedgerWebkit, '_pre_compute_account_ledger_lines',
            _pre_compute_account_ledger_lines)
        _patch_class_method(
            GeneralLedgerWebkit, '_compute_account_ledger_lines',
            _compute_account_ledger_lines)
        _patch_class_method(
            GeneralLedgerWebkit, '_get_ledger_lines_data',
            _general_ledger_get_ledger_lines_data)
        _patch_class_method(
            GeneralLedgerWebkit, 'set_context', general_ledger_set_context)
        _patch_class_method(
            general_ledger_xls, 'generate_xls_report',
            general_ledger_generate_xls_report)
        _patch_class_method(
            general_ledger_xls, '_get_new_ws', general_ledger__get_new_ws)
        # Partner Ledger
        _patch_class_method(
            PartnersLedgerWebkit, '__init__', partner_ledger__init__)
        _patch_class_method(
            PartnersLedgerWebkit, '_compute_partner_ledger_lines',
            _compute_partner_ledger_lines)
        _patch_class_method(
            PartnersLedgerWebkit, 'set_context',
            partner_ledger_set_context)
        _patch_class_method(
            PartnersLedgerWebkit, '_get_ledger_lines_data',
            _partner_ledger_get_ledger_lines_data)
        _patch_class_method(
            PartnersLedgerWebkit, '_pre_compute_partner_ledger_lines',
            _pre_compute_partner_ledger_lines)
        _patch_class_method(
            partner_ledger_xls, '_get_new_ws', partners_ledger__get_new_ws)
        _patch_class_method(
            partner_ledger_xls, 'generate_xls_report',
            partners_ledger_generate_xls_report)
        _logger.info('Registered monkey patches on db %s' % cr.dbname)
