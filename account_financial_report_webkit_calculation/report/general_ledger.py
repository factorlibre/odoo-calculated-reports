# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
import base64
import pickle
import hashlib
import shelve
import logging
import uuid
from openerp.addons.account_financial_report_webkit.report.general_ledger \
    import GeneralLedgerWebkit
from openerp.addons.celery_report_calculation_base.decorators \
    import get_calculation_context
_logger = logging.getLogger(__name__)


@get_calculation_context
def general_ledger__init__(self, cr, uid, name, context):
    general_ledger__init__.origin(self, cr, uid, name, context)


def _pre_compute_account_ledger_lines(self, objects, data, ids,
                                      report_type=None):
    init_balance_memoizer = {}
    new_ids = data['form']['account_ids'] or data[
        'form']['chart_account_id']
    main_filter = self._get_form_param('filter', data, default='filter_no')
    target_move = self._get_form_param('target_move', data, default='all')
    start_date = self._get_form_param('date_from', data)
    stop_date = self._get_form_param('date_to', data)
    start_period = self.get_start_period_br(data)
    stop_period = self.get_end_period_br(data)
    fiscalyear = self.get_fiscalyear_br(data)

    if main_filter == 'filter_no':
        start_period = self.get_first_fiscalyear_period(fiscalyear)
        stop_period = self.get_last_fiscalyear_period(fiscalyear)
    # computation of ledger lines
    if main_filter == 'filter_date':
        ledger_lines_start = start = start_date
        ledger_lines_stop = stop = stop_date
    else:
        start = start_period
        ledger_lines_start = start.id
        stop = stop_period
        ledger_lines_stop = stop.id
    initial_balance = self.is_initial_balance_enabled(main_filter)
    initial_balance_mode = initial_balance \
        and self._get_initial_balance_mode(start) or False
    accounts = self.get_all_accounts(new_ids, exclude_type=['view'])
    if initial_balance_mode == 'initial_balance':
        init_balance_memoizer = self._compute_initial_balances(
            accounts, start, fiscalyear)
    elif initial_balance_mode == 'opening_balance':
        init_balance_memoizer = self._read_opening_balance(accounts, start)

    return self._compute_account_ledger_lines(
        accounts, init_balance_memoizer, main_filter, target_move,
        ledger_lines_start, ledger_lines_stop)


def _compute_account_ledger_lines(self, accounts_ids,
                                  init_balance_memoizer, main_filter,
                                  target_move, start, stop, acc_shelve=None):
    period_pool = self.pool['account.period']
    cr, uid = self.cr, self.uid
    calculation_result_pool = self.pool[
        'report.calculation.result']

    start_serialized = start
    stop_serialized = stop
    if isinstance(start, period_pool.__class__):
        start_serialized = start.id
    if isinstance(stop, period_pool.__class__):
        stop_serialized = stop.id

    if main_filter != 'filter_date':
        start = period_pool.browse(self.cr, self.uid, start_serialized)
        stop = period_pool.browse(self.cr, self.uid, stop_serialized)
    if self.localcontext.get('calculation_id'):
        calculation_id = self.localcontext['calculation_id']
        for account_id in accounts_ids:
            balance_memoizer = {
                account_id: init_balance_memoizer.get(account_id)}
            fargs = [[account_id], balance_memoizer, main_filter,
                     target_move, start_serialized, stop_serialized]
            args_sha1 = hashlib.sha1()
            args_sha1.update(str(account_id))
            args_hash = args_sha1.hexdigest()
            if self.localcontext.get('return_calculated_report'):
                if acc_shelve is None or str(account_id) in acc_shelve:
                    continue
                result_ids = calculation_result_pool.search(cr, uid, [
                    ('calculation_id', '=', calculation_id),
                    ('function', '=', '_compute_account_ledger_lines'),
                    ('args_hash', '=', args_hash),
                ])
                if result_ids:
                    calculation_result = calculation_result_pool.browse(
                        cr, uid, result_ids[0])
                    result = pickle.loads(base64.b64decode(
                        calculation_result.result))
                    if result and acc_shelve is not None:
                        acc_shelve[str(account_id)] = result[account_id]
            if self.localcontext.get('calculate_data'):
                calculation_result_pool.create(cr, uid, {
                    'calculation_id': calculation_id,
                    'function': '_compute_account_ledger_lines',
                    'args': pickle.dumps(fargs),
                    'args_hash': args_hash
                })
        if acc_shelve is not None or self.localcontext.get('calculate_data'):
            return True
    return _compute_account_ledger_lines.origin(
        self, accounts_ids, init_balance_memoizer, main_filter, target_move,
        start, stop)


def _general_ledger_get_ledger_lines_data(self, account):
    if self.localcontext.get('acc_shelve_name'):
        acc_shelve = shelve.open(self.localcontext['acc_shelve_name'],
                                 flag='r')
        if not str(account.id) in acc_shelve:
            return []
        if self.localcontext.get('do_centralize') and account.centralized \
                and self.localcontext.get('main_filter'):
            main_filter = self.localcontext['main_filter']
            _logger.info("CENTRALIZE LINES FOR ACCOUNT: %s" %
                         account.code)
            result = self._centralize_lines_sql_group(
                main_filter, acc_shelve[str(account.id)])
            _logger.info("END CENTRALIZE LINES FOR ACCOUNT: %s" % (
                         account.code))
        else:
            result = acc_shelve[str(account.id)]
        acc_shelve.close()
        return result
    else:
        return self.localcontext.get('ledger_lines', {}).get(account.id)
    return []


def general_ledger_set_context(self, objects, data, ids, report_type=None):
    """Populate a ledger_lines attribute on each browse record that will be
    used by mako template"""
    import tempfile
    tempdir = tempfile.gettempdir()
    cr, uid = self.cr, self.uid
    new_ids = data['form']['account_ids'] or data[
        'form']['chart_account_id']

    self.localcontext.update({
        '_get_ledger_lines_data': self._get_ledger_lines_data,
        '_has_ledger_lines': self._has_ledger_lines
    })

    # Account initial balance memoizer
    init_balance_memoizer = {}

    # Reading form
    main_filter = self._get_form_param('filter', data, default='filter_no')
    target_move = self._get_form_param('target_move', data, default='all')
    start_date = self._get_form_param('date_from', data)
    stop_date = self._get_form_param('date_to', data)
    do_centralize = self._get_form_param('centralize', data)
    self.localcontext['do_centralize'] = do_centralize
    start_period = self.get_start_period_br(data)
    stop_period = self.get_end_period_br(data)
    fiscalyear = self.get_fiscalyear_br(data)
    chart_account = self._get_chart_account_id_br(data)

    if main_filter == 'filter_no':
        start_period = self.get_first_fiscalyear_period(fiscalyear)
        stop_period = self.get_last_fiscalyear_period(fiscalyear)

    # computation of ledger lines
    if main_filter == 'filter_date':
        start = start_date
        stop = stop_date
        if not start_period:
            start_period_ids = self.pool['account.period'].find(
                cr, uid, start_date,
                context={'account_period_prefer_normal': True,
                         'company_id': fiscalyear.company_id.id})
            if start_period_ids:
                start_period = self.pool['account.period'].browse(
                    cr, uid, start_period_ids[0])
    else:
        start = start_period
        stop = stop_period

    self.localcontext['main_filter'] = main_filter

    initial_balance = main_filter in ('filter_no', 'filter_year',
                                      'filter_period', 'filter_date')
    initial_balance_mode = initial_balance \
        and self._get_initial_balance_mode(start_period) or False
    # CHECK
    # Retrieving accounts
    accounts = self.get_all_accounts(new_ids, exclude_type=['view'])
    if initial_balance_mode == 'initial_balance':
        init_balance_memoizer = self._compute_initial_balances(
            accounts, start_period, fiscalyear)
    elif initial_balance_mode == 'opening_balance':
        init_balance_memoizer = self._read_opening_balance(
            accounts, start_period)
    acc_shelve = None
    calculated_report_result = False
    if self.localcontext.get('calculation_id') and \
            self.localcontext.get('return_calculated_report'):
        calculated_report_result = True
        acc_shelve_name = os.path.join(
            tempdir, '%s' % uuid.uuid4().hex)
        acc_shelve = shelve.open(acc_shelve_name)
        self.localcontext['acc_shelve_name'] = acc_shelve_name
    if hasattr(start, 'id'):
        start = start.id
    if hasattr(stop, 'id'):
        stop = stop.id
    ledger_lines_res = self._compute_account_ledger_lines(
        accounts, init_balance_memoizer, main_filter, target_move,
        start, stop, acc_shelve=acc_shelve)
    if acc_shelve:
        acc_shelve.close()
    objects = self.pool.get('account.account').browse(
        self.cursor, self.uid, accounts, context=self.localcontext)
    init_balance = {}
    ledger_lines = {}
    if not calculated_report_result:
        ledger_lines_memoizer = ledger_lines_res
        for account in objects:
            if do_centralize and account.centralized \
                    and ledger_lines_memoizer.get(account.id):
                ledger_lines[account.id] = self._centralize_lines(
                    main_filter, ledger_lines_memoizer.get(account.id, []))
            else:
                ledger_lines[account.id] = ledger_lines_memoizer.get(
                    account.id, [])
            init_balance[account.id] = init_balance_memoizer.get(account.id)
    else:
        # Use shelve with ledger_lines_memoizer
        for account in objects:
            init_balance[account.id] = init_balance_memoizer.get(account.id)

    self.localcontext.update({
        'fiscalyear': fiscalyear,
        'start_date': start_date,
        'stop_date': stop_date,
        'start_period': start_period,
        'stop_period': stop_period,
        'chart_account': chart_account,
        'initial_balance_mode': initial_balance_mode,
        'init_balance': init_balance,
        'ledger_lines': ledger_lines
    })
    return super(GeneralLedgerWebkit, self).set_context(
        objects, data, new_ids, report_type=report_type)
