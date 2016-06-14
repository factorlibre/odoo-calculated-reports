# -*- coding: utf-8 -*-
# © 2016 FactorLibre <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import pickle
from openerp import api, fields, models
from openerp.addons.account_financial_report_webkit.report.general_ledger \
    import GeneralLedgerWebkit
from openerp.addons.account_financial_report_webkit_xls.report.\
    general_ledger_xls import general_ledger_xls
from openerp.addons.celery_queue.decorators import CeleryTask


class AccountReportGeneralLedgerWizard(models.TransientModel):
    _inherit = "general.ledger.webkit"

    calculate_in_background = fields.Boolean('Calculate in background',
                                             default=True)

    # @CeleryTask(queue='financial-reports')
    @api.multi
    def calculate_background_report_values(self, print_action):
        context = self.env.context
        report_calculation_env = self.env['report.calculation']
        data = print_action.get('datas')
        report_name = print_action.get('report_name')
        ledger_class = GeneralLedgerWebkit
        calculation = report_calculation_env.create({
            'report_name': report_name,
            'report_data': base64.b64encode(pickle.dumps(data)),
            'report_context': base64.b64encode(pickle.dumps(context)),
            'report_class': base64.b64encode(pickle.dumps(ledger_class))
        })
        ctx = dict(context)
        ctx['calculation_id'] = calculation.id
        ctx['calculate_data'] = True
        cr, uid = self.env.cr, self.env.uid
        ledger_webkit = ledger_class(
            cr, uid, report_name, ctx)
        ledger_webkit._pre_compute_account_ledger_lines(
            [], data, calculation.ids)
        return True

    @api.multi
    def check_report(self):
        print_action = super(AccountReportGeneralLedgerWizard, self).\
            check_report()
        if self.calculate_in_background:
            return self.calculate_background_report_values(print_action)
        else:
            return print_action
