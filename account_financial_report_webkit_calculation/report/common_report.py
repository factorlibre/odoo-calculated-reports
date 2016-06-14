# -*- coding: utf-8 -*-
# © 2016 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import shelve


def _has_ledger_lines(self, account):
    if self.localcontext.get('acc_shelve_name'):
        acc_shelve = shelve.open(self.localcontext['acc_shelve_name'],
                                 flag='r')
        result = str(account.id) in acc_shelve
        acc_shelve.close()
        return result
    else:
        return account.id in self.localcontext.get('ledger_lines', {}).keys()
    return False
