# -*- coding: utf-8 -*-
# © 2015 FactorLibre <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import pickle
from datetime import datetime


def calculated_report_result(f):
    """
    Decorator for store calculation of a method
    """
    def func_wrapper(*args, **kwargs):
        self = args[0]
        cr, uid = self.cr, self.uid
        calculation_result_pool = self.pool[
            'report.calculation.result']
        if self.localcontext.get('calculation_id') \
                and self.localcontext.get('return_calculated_report'):
            calculation_id = self.localcontext['calculation_id']
            result_ids = calculation_result_pool.search(cr, uid, [
                ('calculation_id', '=', calculation_id),
                ('function', '=', f.__name__),
                # ('args', '=', base64.b64encode(pickle.dumps(args[1:]))),
                # ('kwargs', '=', base64.b64encode(pickle.dumps(kwargs)))
            ])
            if result_ids:
                calculation_result = calculation_result_pool.browse(
                    cr, uid, result_ids[0])
                return pickle.loads(
                    base64.b64decode(calculation_result.result))
        if self.localcontext.get('calculate_data') \
                and self.localcontext.get('calculation_id'):
            calculation_result_pool.create(cr, uid, {
                'calculation_id': self.localcontext['calculation_id'],
                'function': f.__name__,
                'args': pickle.dumps(args[1:]),
                'kwargs': pickle.dumps(kwargs)
            })
            return True
        return f(*args, **kwargs)
    return func_wrapper


def calculated_report_result_eager(f):
    """
    Decorator for calculate functions result without using queue
    Its useful for recover results when generating a report
    and reuse calculated results previosly computed when printing it
    """
    def func_wrapper(*args, **kwargs):
        self = args[0]
        cr, uid = self.cr, self.uid
        calculation_result_pool = self.pool[
            'report.calculation.result']
        if self.localcontext.get('calculation_id') \
                and self.localcontext.get('return_calculated_report'):
            calculation_id = self.localcontext['calculation_id']
            result_ids = calculation_result_pool.search(cr, uid, [
                ('calculation_id', '=', calculation_id),
                ('function', '=', f.__name__),
            ])
            if result_ids:
                calculation_result = calculation_result_pool.browse(
                    cr, uid, result_ids[0])
                return pickle.loads(
                    base64.b64decode(calculation_result.result))
        result = f(*args, **kwargs)
        if self.localcontext.get('calculate_data') \
                and self.localcontext.get('calculation_id'):
            calculation_result_pool.create(cr, uid, {
                'calculation_id': self.localcontext['calculation_id'],
                'function': f.__name__,
                'enqueued_date': datetime.now(),
                'calculation_date': datetime.now(),
                'result': base64.b64encode(pickle.dumps(result))
            })
        return result
    return func_wrapper


def get_calculation_context(f):
    """
    Method for recover calculation_id and calculation method from context
    and to assign it to localcontext to call in __init__
    """
    def func_wrapper(*args, **kwargs):
        res = f(*args, **kwargs)
        self = args[0]
        context = kwargs.get('context')
        if not context:
            # If not context found in kwargs try with last param
            # This is possible not the better solution
            if isinstance(args[-1], dict):
                context = args[-1]
        if context:
            if context.get('calculation_id'):
                self.localcontext['calculation_id'] = context['calculation_id']
            if context.get('calculate_data'):
                self.localcontext['calculate_data'] = True
            if context.get('return_calculated_report'):
                self.localcontext['return_calculated_report'] = True
        return res
    return func_wrapper


def _patch_class_method(cls, name, method):
    if hasattr(cls, name):
        origin = getattr(cls, name)
        method.origin = origin
    setattr(cls, name, method)
