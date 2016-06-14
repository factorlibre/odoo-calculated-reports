# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Calculated Financial Reports webkit',
    'version': '8.0.1.0.0',
    'depends': [
        'account_financial_report_webkit',
        'account_financial_report_webkit_xls',
        'celery_report_calculation_base'
    ],
    'category': 'Sales Management',
    'author': 'Odoo Community Association (OCA),FactorLibre',
    'license': 'AGPL-3',
    'website': 'http://www.factorlibre.com',
    'data': [
        'report/reports.xml',
        'wizard/trial_balance_wizard_view.xml',
        'wizard/general_ledger_wizard_view.xml',
        'wizard/partners_ledger_wizard_view.xml'
    ],
    'installable': True,
    'application': False
}
