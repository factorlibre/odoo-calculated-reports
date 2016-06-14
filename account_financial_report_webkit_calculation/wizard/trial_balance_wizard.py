# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import pickle
from datetime import datetime
from openerp import api, fields, models
from openerp.addons.account_financial_report_webkit.report.trial_balance \
    import TrialBalanceWebkit
from openerp.addons.account_financial_report_webkit_xls.report.\
    trial_balance_xls import trial_balance_xls


class AccountTrialBalanceWizard(models.TransientModel):
    _inherit = "trial.balance.webkit"

    calculate_in_background = fields.Boolean(
        'Calculate in background', default=True)

    @api.multi
    def calculate_background_report_values(self, print_action):
        context = self.env.context
        report_calculation_env = self.env['report.calculation']
        calculation_result_env = self.env['report.calculation.result']
        data = print_action.get('datas')
        report_name = print_action.get('report_name')
        trial_class = TrialBalanceWebkit
        if context.get('xls_export'):
            trial_class = trial_balance_xls
        calculation = report_calculation_env.create({
            'report_name': report_name,
            'report_data': base64.b64encode(pickle.dumps(data)),
            'report_context': base64.b64encode(pickle.dumps(context)),
            'report_class': base64.b64encode(pickle.dumps(trial_class))
        })
        ctx = dict(context)
        ctx['calculation_id'] = calculation.id
        ctx['calculate_data'] = True
        calculation_result_env.create({
            'calculation_id': calculation.id,
            'function': 'dummy',
            'result': base64.b64encode(pickle.dumps(True)),
            'enqueued_date': datetime.now(),
            'calculation_date': datetime.now()
        })
        return True

    @api.multi
    def check_report(self):
        print_action = super(AccountTrialBalanceWizard, self).check_report()
        if self.calculate_in_background:
            return self.calculate_background_report_values(print_action)
        return print_action
