# -*- coding: utf-8 -*-
# © 2015 FactorLibre <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Report Calculations with Celery (Base Module)',
    'version': '8.0.1.0.0',
    'author': 'Factorlibre',
    'license': 'AGPL-3',
    'category': 'Generic Modules',
    'website': 'http://factorlibre.com',
    'depends': [
        'base',
        'celery_queue'
    ],
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'views/report_calculation_view.xml',
        'data/report_calculation_cron.xml'
    ]
}
