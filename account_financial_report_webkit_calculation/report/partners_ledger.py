# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
import base64
import pickle
import hashlib
import shelve
import uuid
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.celery_report_calculation_base.decorators \
    import get_calculation_context
from openerp.addons.account_financial_report_webkit.report.partners_ledger \
    import PartnersLedgerWebkit


@get_calculation_context
def partner_ledger__init__(self, cr, uid, name, context):
    partner_ledger__init__.origin(self, cr, uid, name, context)


def _pre_compute_partner_ledger_lines(self, objects, data, ids,
                                      report_type=None):
    new_ids = data['form']['chart_account_id']
    main_filter = self._get_form_param('filter', data, default='filter_no')
    target_move = self._get_form_param('target_move', data, default='all')
    start_date = self._get_form_param('date_from', data)
    stop_date = self._get_form_param('date_to', data)
    start_period = self.get_start_period_br(data)
    stop_period = self.get_end_period_br(data)
    fiscalyear = self.get_fiscalyear_br(data)
    partner_ids = self._get_form_param('partner_ids', data)
    result_selection = self._get_form_param('result_selection', data)

    if main_filter == 'filter_no' and fiscalyear:
        start_period = self.get_first_fiscalyear_period(fiscalyear)
        stop_period = self.get_last_fiscalyear_period(fiscalyear)

    filter_type = ('payable', 'receivable')
    if result_selection == 'customer':
        filter_type = ('receivable',)
    if result_selection == 'supplier':
        filter_type = ('payable',)

    accounts = self.get_all_accounts(new_ids, exclude_type=['view'],
                                     only_type=filter_type)

    if not accounts:
        raise osv.except_osv(_('Error'), _('No accounts to print.'))

    if main_filter == 'filter_date':
        start = start_date
        stop = stop_date
    else:
        start = start_period
        stop = stop_period

    period_pool = self.pool['account.period']
    start_serialized = start
    stop_serialized = stop
    if isinstance(start, period_pool.__class__):
        start_serialized = start.id
    if isinstance(stop, period_pool.__class__):
        stop_serialized = stop.id

    return self._compute_partner_ledger_lines(
        accounts, main_filter, target_move, start_serialized, stop_serialized,
        partner_filter=partner_ids)


def _compute_partner_ledger_lines(self, accounts_ids, main_filter,
                                  target_move, start, stop,
                                  partner_filter=False, acc_shelve=None):
    period_pool = self.pool['account.period']
    cr, uid = self.cr, self.uid
    calculation_result_pool = self.pool['report.calculation.result']

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
        for acc_id in accounts_ids:
            fargs = [[acc_id], main_filter,
                     target_move, start_serialized, stop_serialized]
            fkwargs = {'partner_filter': partner_filter}
            args_sha1 = hashlib.sha1()
            args_sha1.update(str(acc_id))
            args_hash = args_sha1.hexdigest()
            if self.localcontext.get('return_calculated_report'):
                if acc_shelve is None or str(acc_id) in acc_shelve:
                    continue
                result_ids = calculation_result_pool.search(cr, uid, [
                    ('calculation_id', '=', calculation_id),
                    ('function', '=', '_compute_partner_ledger_lines'),
                    ('args_hash', '=', args_hash),
                ])
                if result_ids:
                    calculation_result = calculation_result_pool.browse(
                        cr, uid, result_ids[0])
                    result = pickle.loads(base64.b64decode(
                        calculation_result.result))
                    if result and acc_shelve is not None:
                        acc_shelve[str(acc_id)] = result[acc_id]
            elif self.localcontext.get('calculate_data'):
                calculation_result_pool.create(cr, uid, {
                    'calculation_id': calculation_id,
                    'function': '_compute_partner_ledger_lines',
                    'args': pickle.dumps(fargs),
                    'kwargs': pickle.dumps(fkwargs),
                    'args_hash': args_hash
                })
        if acc_shelve is not None or self.localcontext.get('calculate_data'):
            return True
    return _compute_partner_ledger_lines.origin(
        self, accounts_ids, main_filter, target_move, start, stop,
        partner_filter=partner_filter)


def _partner_ledger_get_ledger_lines_data(self, account):
    if self.localcontext.get('acc_shelve_name'):
        acc_shelve = shelve.open(self.localcontext['acc_shelve_name'],
                                 flag='r')
        if not str(account.id) in acc_shelve:
            return {}
        result = acc_shelve[str(account.id)]
        acc_shelve.close()
        return result
    else:
        return self.localcontext.get('ledger_lines', {}).get(account.id)


def partner_ledger_set_context(self, objects, data, ids, report_type=None):
    """Populate a ledger_lines attribute on each browse record that will
       be used by mako template"""
    import tempfile
    tempdir = tempfile.gettempdir()

    new_ids = data['form']['chart_account_id']

    self.localcontext.update({
        '_get_ledger_lines_data': self._get_ledger_lines_data,
        '_has_ledger_lines': self._has_ledger_lines
    })

    # account partner memoizer
    # Reading form
    main_filter = self._get_form_param('filter', data, default='filter_no')
    target_move = self._get_form_param('target_move', data, default='all')
    start_date = self._get_form_param('date_from', data)
    stop_date = self._get_form_param('date_to', data)
    start_period = self.get_start_period_br(data)
    stop_period = self.get_end_period_br(data)
    fiscalyear = self.get_fiscalyear_br(data)
    partner_ids = self._get_form_param('partner_ids', data)
    result_selection = self._get_form_param('result_selection', data)
    chart_account = self._get_chart_account_id_br(data)

    if main_filter == 'filter_no' and fiscalyear:
        start_period = self.get_first_fiscalyear_period(fiscalyear)
        stop_period = self.get_last_fiscalyear_period(fiscalyear)

    # Retrieving accounts
    filter_type = ('payable', 'receivable')
    if result_selection == 'customer':
        filter_type = ('receivable',)
    if result_selection == 'supplier':
        filter_type = ('payable',)

    accounts = self.get_all_accounts(new_ids, exclude_type=['view'],
                                     only_type=filter_type)

    if not accounts:
        raise osv.except_osv(_('Error'), _('No accounts to print.'))

    if main_filter == 'filter_date':
        start = start_date
        stop = stop_date
    else:
        start = start_period
        stop = stop_period

    # when the opening period is included in the selected range of periods
    # and the opening period contains move lines, we must not compute the
    # initial balance from previous periods but only display the move lines
    # of the opening period we identify them as:
    #  - 'initial_balance' means compute the sums of move lines from
    #    previous periods
    #  - 'opening_balance' means display the move lines of the opening
    #    period
    init_balance = main_filter in ('filter_no', 'filter_period')
    initial_balance_mode = init_balance and self._get_initial_balance_mode(
        start) or False

    initial_balance_lines = {}
    if initial_balance_mode == 'initial_balance':
        initial_balance_lines = self._compute_partners_initial_balances(
            accounts, start_period, partner_filter=partner_ids,
            exclude_reconcile=False)

    acc_shelve = None
    calculated_report_result = False
    if self.localcontext.get('calculation_id') and \
            self.localcontext.get('return_calculated_report'):
        calculated_report_result = True
        acc_shelve_name = os.path.join(
            tempdir, '%s' % uuid.uuid4().hex)
        acc_shelve = shelve.open(acc_shelve_name)
        self.localcontext['acc_shelve_name'] = acc_shelve_name
    period_pool = self.pool['account.period']
    start_serialized = start
    stop_serialized = stop
    if isinstance(start, period_pool.__class__):
        start_serialized = start.id
    if isinstance(stop, period_pool.__class__):
        stop_serialized = stop.id

    ledger_lines = self._compute_partner_ledger_lines(
        accounts, main_filter, target_move, start_serialized, stop_serialized,
        partner_filter=partner_ids, acc_shelve=acc_shelve)
    if acc_shelve:
        acc_shelve.close()

    objects = self.pool.get('account.account').browse(
        self.cursor, self.uid, accounts, context=self.localcontext)

    init_balance = {}
    ledger_lines_dict = {}
    partners_order = {}
    if not calculated_report_result:
        for account in objects:
            ledger_lines_dict[account.id] = ledger_lines.get(account.id, {})
            init_balance[account.id] = initial_balance_lines.get(account.id,
                                                                 {})
            # we have to compute partner order based on inital balance
            # and ledger line as we may have partner with init bal
            # that are not in ledger line and vice versa
            ledg_lines_pids = ledger_lines.get(account.id, {}).keys()
            if initial_balance_mode:
                non_null_init_balances = dict(
                    [(ib, amounts) for ib, amounts
                     in init_balance[account.id].iteritems()
                     if amounts['init_balance'] or
                     amounts['init_balance_currency']])
                init_bal_lines_pids = non_null_init_balances.keys()
            else:
                init_balance[account.id] = {}
                init_bal_lines_pids = []

            partners_order[account.id] = self._order_partners(
                ledg_lines_pids, init_bal_lines_pids)
    else:
        for account in objects:
            init_balance[account.id] = initial_balance_lines.get(account.id,
                                                                 {})
            ledg_lines_pids = self._get_ledger_lines_data(account).keys()
            if initial_balance_mode:
                non_null_init_balances = dict(
                    [(ib, amounts) for ib, amounts
                     in init_balance[account.id].iteritems()
                     if amounts['init_balance'] or
                     amounts['init_balance_currency']])
                init_bal_lines_pids = non_null_init_balances.keys()
            else:
                init_balance[account.id] = {}
                init_bal_lines_pids = []

            partners_order[account.id] = self._order_partners(
                ledg_lines_pids, init_bal_lines_pids)

    self.localcontext.update({
        'fiscalyear': fiscalyear,
        'start_date': start_date,
        'stop_date': stop_date,
        'start_period': start_period,
        'stop_period': stop_period,
        'partner_ids': partner_ids,
        'chart_account': chart_account,
        'initial_balance_mode': initial_balance_mode,
        'init_balance': init_balance,
        'ledger_lines': ledger_lines_dict,
        'partners_order': partners_order
    })

    return super(PartnersLedgerWebkit, self).set_context(
        objects, data, new_ids, report_type=report_type)
