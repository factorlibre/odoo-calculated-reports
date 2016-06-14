# -*- coding: utf-8 -*-
# © 2015 FactorLibre <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import pickle
import time
import logging
from datetime import datetime
from openerp import api, models, fields
from openerp.service import report
from openerp.addons.celery_queue.decorators import CeleryTask

_logger = logging.getLogger(__name__)


class report_calculation(models.Model):
    _name = 'report.calculation'

    _rec_name = 'report_name'

    @api.model
    def _get_calculation_states(self):
        return [
            ('draft', 'Draft'),
            ('processing', 'Processing'),
            ('done_calculation', 'Done Calculation'),
            ('printed', 'Printed')
        ]

    @api.multi
    @api.depends('print_date', 'create_date', 'calculation_result_ids',
                 'calculation_result_ids.enqueued_date',
                 'calculation_result_ids.calculation_date')
    def _get_state(self):
        calculation_result_env = self.env['report.calculation.result']
        for calculation in self:
            calculation.state = 'draft'
            if calculation.print_date:
                calculation.state = 'printed'
                continue
            results = calculation_result_env.search([
                ('calculation_id', '=', calculation.id)
            ])
            if not results:
                continue
            queued_results = calculation_result_env.search([
                ('calculation_id', '=', calculation.id),
                ('enqueued_date', '!=', False),
                ('calculation_date', '=', False)
            ])
            if queued_results:
                calculation.state = 'processing'
                continue
            completed_results = calculation_result_env.search([
                ('calculation_id', '=', calculation.id),
                ('calculation_date', '=', False)
            ])
            if not completed_results:
                calculation.state = 'done_calculation'

    report_name = fields.Char('Report Name', readonly=True)
    report_class = fields.Text('Report Class', readonly=True)
    report_data = fields.Text('Report Data', readonly=True)
    report_context = fields.Text('Report Context', readonly=True)
    enqueued_print_task = fields.Text('Enqueued Print UUID', readonly=True)
    calculation_result_ids = fields.One2many(
        'report.calculation.result', 'calculation_id',
        'Calculation Results', readonly=True)
    create_date = fields.Datetime('Creation Date', readonly=True)
    print_date = fields.Datetime('Print Date', readonly=True)
    state = fields.Selection(
        string="State", selection='_get_calculation_states',
        compute='_get_state', store=True)

    @api.multi
    def print_report(self):
        if self.env.context.get('print_queue'):
            return self.print_report_queue()
        return self.print_report_function()

    @CeleryTask(queue='financial-reports')
    @api.multi
    def print_report_queue(self):
        return self.print_report_function()

    @api.multi
    def print_report_function(self):
        self.ensure_one()
        cr, uid = self.env.cr, self.env.uid
        calculation = self
        attachment_env = self.env['ir.attachment']
        att_ids = attachment_env.search([
            ('res_model', '=', 'report.calculation'),
            ('res_id', '=', calculation.id),
            ('datas_fname', 'ilike', calculation.report_name.replace('.', '_'))
        ])
        if att_ids:
            _logger.warning(
                "Already exists a printed report for report.calculation %s "
                "Skipping the report print. If you want to print the report "
                "again please remove the existing attachment and try again" % (
                    calculation.id))
            return False
        report_context = dict(self.env.context)
        if calculation.report_context:
            report_context = dict(pickle.loads(base64.b64decode(
                calculation.report_context)))
        report_context.update({
            'calculation_id': calculation.id,
            'return_calculated_report': True
        })
        report_key = report.exp_report(
            cr.dbname, uid, calculation.report_name, [calculation.id],
            datas=pickle.loads(base64.b64decode(calculation.report_data)),
            context=report_context)
        while 1:
            res = report.exp_report_get(cr.dbname, uid, report_key)
            if res.get('state'):
                break
            time.sleep(0.2)

        extension = res.get('format')
        report_file = res.get('result')

        calculation.write({
            'print_date': datetime.now(),
        })
        file_name = "{}.{}".format(
            calculation.report_name.replace('.', '_'),
            extension)
        attachment_env.create({
            'res_model': 'report.calculation',
            'res_id': calculation.id,
            'datas': report_file,
            'name': file_name,
            'datas_fname': file_name
        })
        return True

    @api.multi
    def enqueue_calculations(self):
        calculation_result_env = self.env['report.calculation.result']
        for calculation in self:
            calculation_results = calculation_result_env.search([
                ('calculation_id', '=', calculation.id),
                ('enqueued_date', '=', False)
            ])
            if calculation_results:
                calculation_results.get_function_result()
        return True

    @api.model
    def enqueue_report_print(self):
        to_print_calculations = self.search([
            ('state', '=', 'done_calculation'),
            ('enqueued_print_task', '=', False)
        ])
        for to_print_calculation in to_print_calculations:
            enqueued_print_task = to_print_calculation.print_report_queue()
            to_print_calculation.write({
                'enqueued_print_task': enqueued_print_task
            })
        return True

    @api.model
    def enqueue_report_calculation(self):
        to_enqueue_calculations = self.search([
            ('state', '=', 'draft')
        ])
        if to_enqueue_calculations:
            to_enqueue_calculations.enqueue_calculations()
        return True


class report_calculation_result(models.Model):
    _name = 'report.calculation.result'

    _rec_name = 'function'

    calculation_id = fields.Many2one(
        'report.calculation', 'Calculation', readonly=True,
        required=True, ondelete='cascade')
    function = fields.Char('Function', readonly=True)
    args = fields.Text('ARGS', readonly=True)
    args_hash = fields.Char('Args Hash', readonly=True)
    kwargs = fields.Text('KWARGS', readonly=True)
    result = fields.Text('Result', readonly=True)
    create_date = fields.Datetime('Creation Date', readonly=True)
    enqueued_date = fields.Datetime('Enqueued Date', readonly=True)
    calculation_date = fields.Datetime('Calculation Date', readonly=True)

    @api.multi
    def get_function_result(self):
        try:
            self.write({
                'enqueued_date': datetime.now()
            })
        except Exception:
            self.env.cr.rollback()
        finally:
            self.env.cr.commit()

        for result in self:
            result.report_calculation_result_delay()
        return True

    @api.model
    def search_enqueue_calculations(self, cr, uid, context=None):
        calculation_domain = [('enqueued_date', '=', False)]
        calculation_results = self.search(calculation_domain)
        if calculation_results:
            calculation_results.get_function_result()
        return True

    @CeleryTask(queue='financial-reports')
    @api.multi
    def report_calculation_result_delay(self):
        """Calculates method defined in report calculation as a delayed job
        """
        self.ensure_one()
        report_calculation_result = self
        report_calculation = report_calculation_result.calculation_id
        report_context = self.env.context
        report_class = pickle.loads(base64.b64decode(
            report_calculation.report_class))
        cr, uid = self.env.cr, self.env.uid
        report_class_instance = report_class(cr, uid,
                                             report_calculation.report_name,
                                             report_context)
        func_name = report_calculation_result.function
        fargs = pickle.loads(report_calculation_result.args)
        fkwargs = {}
        if report_calculation_result.kwargs:
            fkwargs = pickle.loads(report_calculation_result.kwargs)
        result = getattr(report_class_instance, func_name)(*fargs, **fkwargs)
        result = base64.b64encode(pickle.dumps(result))
        report_calculation_result.write({
            'result': result,
            'calculation_date': datetime.now()
        })
        return True
