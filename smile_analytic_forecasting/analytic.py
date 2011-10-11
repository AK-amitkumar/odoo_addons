# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 Smile (<http://www.smile.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import time

from osv import osv, fields
from tools.translate import _

class AnalyticPeriod(osv.osv):
    _name = 'account.analytic.period'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'date_start': fields.date('Start of Period', required=True, states={'done':[('readonly', True)]}),
        'date_stop': fields.date('End of Period', required=True, states={'done':[('readonly', True)]}),
        'state': fields.selection([('draft', 'Opened'), ('done', 'Closed')], 'State', required=True),
        'general_period_id': fields.many2one('account.period', 'General Period', required=True),
        'fiscalyear_id': fields.related('general_period_id', 'fiscalyear_id', string='Fiscal Year', type='many2one', relation='account.fiscalyear', readonly=True),
    }

    _defaults = {
        'state': 'draft',
    }

    _order = "date_start"

    def _check_duration(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        period = self.browse(cr, uid, ids[0], context)
        if period.date_stop < period.date_start \
        or period.date_start < period.general_period_id.date_start \
        or period.date_stop > period.general_period_id.date_stop:
            return False            
        return True

    def _check_periods_overlap(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for period in self.browse(cr, uid, ids, context):
            domain = [
                ('id', '<>', period.id),
                '|',
                '&', ('date_start', '>=', period.date_start), ('date_stop', '<=', period.date_start),
                '&', ('date_start', '>=', period.date_stop), ('date_stop', '<=', period.date_stop),
            ]
            if self.search(cr, uid, domain, context=context):
                return False
        return True

    _constraints = [
        (_check_duration, 'The duration of the period is invalid or the period dates are not in the scope of the account period!', ['date_start', 'date_stop']),
        (_check_periods_overlap, 'Some periods overlap!', ['date_start', 'date_stop']),
    ]

    def get_period_id_from_date(self, cr, uid, date=False, context=None):
        date = date or time.strftime('%Y-%m-%d')
        period_id = self.search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)], limit=1, context=context)
        if not period_id:
            return False
            raise osv.except_osv(_('Error'), _('No analytic period found for this date %s') % date)
        if self.read(cr, uid, period_id[0], ['state'], context)['state'] == 'done':
            raise osv.except_osv(_('Error'), _('You cannot pass a journal entry in a period closed!'))
        return period_id[0]
AnalyticPeriod()

class AnalyticLine(osv.osv):
    _inherit = 'account.analytic.line'

    def _get_period_id(self, cr, uid, ids, name, arg, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}.fromkeys(ids, False)
        period_obj = self.pool.get('account.analytic.period')
        for line in self.read(cr, uid, ids, ['date'], context):
            res[line['id']] = period_obj.get_period_id_from_date(cr, uid, line['date'], context)
        return res

    _columns = {
        'type': fields.selection([('actual', 'Actual'), ('forecast', 'Forecast')], 'Type', required=True),
        'period_id': fields.many2one('account.analytic.period', 'Period', domain=[('state', '!=', 'done')]),
        'analysis_period_id': fields.function(_get_period_id, method=True, type='many2one', relation='account.analytic.period', string='Analysis Period', store={
            'account.analytic.line': (lambda self, cr, uid, ids, context=None: ids, ['date'], 10),
        }),
    }

    def _get_default_period_id(self, cr, uid, context=None):
        return self.pool.get('account.analytic.period').get_period_id_from_date(cr, uid, context=context)

    _defaults = {
        'type': 'actual',
        'period_id': _get_default_period_id,
    }

    def _check_period(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for line in self.browse(cr, uid, ids, context):
            if line.period_id.state == 'done':
                return False
        return True

    def _check_type_from_analysis_period(self, cr, uid, ids, entry_type='actual', context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        operator_ = entry_type == 'actual' and '__gt__' or '__lt__'
        for line in self.browse(cr, uid, ids, context):
            if line.analysis_period_id and getattr(line.analysis_period_id.date_start, operator_)(time.strftime('%Y-%m-%d')) and line.type == entry_type:
                return False
        return True

    def _check_actual_from_analysis_period(self, cr, uid, ids, context=None):
        return self._check_type_from_analysis_period(cr, uid, ids, 'actual', context)

    def _check_forecast_from_analysis_period(self, cr, uid, ids, context=None):
        return self._check_type_from_analysis_period(cr, uid, ids, 'forecast', context)
    
    _constraints = [
        (_check_period, 'You cannot pass/update a journal entry in a period closed!', ['period_id']),
        (_check_actual_from_analysis_period, 'You cannot pass an actual entry in a future period!', ['type', 'period']),
        (_check_forecast_from_analysis_period, 'You cannot pass a forecast entry in a past period!', ['type', 'period']),
    ]
AnalyticLine()