.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================================
Calculated Financial Reports webkit
===================================

This module is used to compute and print financial reports in background.
The reports available with this system are:

* General Ledger
* Partners Ledger
* Trial Balance

Installation
============

This module depends on celery_queue module that can be found in https://github.com/factorlibre/celery-odoo
and in celery_report_calculation_base https://github.com/factorlibre/odoo-calculated-reports


Usage
=====

To use this module create a financial report from their wizard (Of the types available)
and check the "Calculate in background" option and Print or generate the xls version as normal

This will create a report.calculation object in menu Reporting -> Calculated Reports -> Report Calculation

When this object is created, a scheduled action will enqueue the calculation tasks in Celery and the state will be Processing.

After calculation is completed the state will change to Done Calculation and this report can be printed.
Is possible to print the report in foreground or in background enqueued in Celery.
There is also another scheduled action, that search for Done calculation reports and enqueues the report print in celery.

When the report is printed an attachment is created in report.calculation object and the state changes to Printed.

In order to process reports with celery is necessary to execute a celery worker that listens in financial-reports queue.
It's important to enable only one worker with one processor to avoid concurrency errors when computing this financial reports information.

.. code:: bash

    export PYTHONPATH="/opt/odoo/odoo-server:/opt/odoo/modules/celery-dooo"
    celery -A celery_queue.tasks worker -c 1 -Q financial-reports


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/factorlibre/odoo-calculated-reports/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Hugo Santos <hugo.santos@factorlibre.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.