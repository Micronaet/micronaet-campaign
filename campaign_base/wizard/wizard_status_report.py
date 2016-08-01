# -*- coding: utf-8 -*-
###############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ProductProductCampaignStatusReport(orm.TransientModel):
    ''' Status of product in report
    '''    
    _name = 'product.product.campaign.status.report'
    _description = 'Campain product status wizard'
    
    # --------------
    # Button events:
    # --------------
    def print_report_product_status(self, cr, uid, ids, context=None):
        ''' Redirect to report passing parameters
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]

        datas = {}

        datas['wizard'] = True # started from wizard                
        datas['days'] = wiz_proxy.days
        datas['mode'] = wiz_proxy.mode
        datas['mode'] = wiz_proxy.mode
        report_name = wiz_proxy.report_name

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name, 
            #'campaign_campaign_product_status_report',
            'datas': datas,
            'context': context,
            }

    _columns = {
        'report_name': fields.selection([
            ('campaign_campaign_product_status_report', 
                'Stock status report'),
            ('campaign_campaign_ods_report', 
                'Campaign XLS report (with avail.)'),
            ], 'Report', required=True),
        'days': fields.integer('Days', required=True),
        'mode': fields.selection([
            ('confirmed', 'Only confirmed'),
            ('draft', 'Draft and confirmed'),
            ], 'Mode', required=True)
        }
        
    _defaults = {
        'report_name': lambda *x: 'campaign_campaign_product_status_report',            
        'days': lambda *x: 30,
        'mode': lambda *x: 'confirmed',
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
