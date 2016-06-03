#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import sys
import logging
from openerp.osv import fields, osv, expression, orm
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ProductProduct(orm.Model):
    """ Object used for get initial status
        >> create a object method instead of function for override
           depend on method used for get status
    """
    _inherit = 'product.product'

    def get_inventory_net_lord_status(self, cr, uid, product, context=None):
        ''' Return status net and lord
        '''
        return (product.qty_available, product.virtual_available)

class Parser(report_sxw.rml_parse):
    counters = {}
    context = False
    
    def __init__(self, cr, uid, name, context):
        self.context = context
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'load_data': self.load_data,
            'get_filter': self.get_filter,
            'get_counter': self.get_counter,
        })

    def load_data(self, data):
        ''' Load data
        '''
        # Setup:
        data = data or {}
        cr = self.cr
        uid = self.uid
        
        # Initialize elements for report:
        self.cols = []
        self.campaign_status = [] 
        self.cells = {}
        
        # Pools:
        campaign_pool = self.pool.get('campaign.campaign')
        product_pool = self.pool.get('product.product')
        
        # Read parameters:
        mode = data.get('mode')
        days = data.get('days')

        # Create used parameter:
        today = datetime.now()        
        
        # Get active campaign 
        if mode == 'confirmed':
            domain = [('state', '=', 'confirmed')]
        else:    
            domain = [('state', 'in', ('draft', 'confirmed'))]
        campaign_ids = campaign_pool.search(cr, uid, domain)
        if not campaign_ids:
            return '' # empty report
        
        # ---------------------------------------------------------------------
        #                    Populate cols:
        # ---------------------------------------------------------------------
        for day in range(0, days):
            # Data header format DD:MM
            self.cols.append((today + timedelta(days=day)).strftime(
                '%d-%m')) # DEFAULT_SERVER_DATE_FORMAT
            # Campaign status:     
            self.campaign_status.append('')    
        
        # ---------------------------------------------------------------------
        #                    Populate cells:
        # ---------------------------------------------------------------------
        # Check all campaign
        for campaign in campaign_pool.browse(cr, uid, campaign_ids):
            # data evaluation:
            start = datetime.strptime(
                campaign.from_date, DEFAULT_SERVER_DATE_FORMAT)
            start_pos = (start - today).days
            # TODO use for restore q after end????
            end = datetime.strptime(
                campaign.to_date, DEFAULT_SERVER_DATE_FORMAT)
            end_pos = (end - today).days            
            
            if start_pos < days: # campain start in range
                # save position where start with totals
                start_col = 0 if start_pos < 0 else start_pos
                in_range = True # start date < days period
                self.campaign_status[start_col] += _('S: %s\n') % campaign.code
            else:
                in_range = False

            # only for campaign status:
            if end_pos < days: # campain start in range
                # save position where start with totals
                end_col = 0 if end_pos < 0 else end_pos
                self.campaign_status[end_col] += _('E: %s\n') % campaign.code
            
            # Check all product-items:
            for item in campaign.product_ids:
                product = item.product_id
                if product not in self.cells:
                    # Initial status:
                    (net, lord) = product_pool.get_inventory_net_lord_status(
                        cr, uid, product)
                    self.cells[product] = [lord for i in range(0, days)]    
                        
                # Generate empty element
                # choose here what value
                if not in_range:
                    continue # date start over days
                    
                for col in range(start_col, days):
                    self.cells[product][col] -= item.qty
                        
        return ''
    
    def get_filter(self, data):
        ''' Get description for filter applied
        '''
        data = data or {}
        res = ''
        res += _(' >> Period days: %s ') % data.get('days', '?')
        res += _(' >> Mode: %s ') % data.get('mode', '?')
        return res

    def get_counter(self, item):
        ''' Load data
        '''
        if item == 'cells':
            return (self.cells or {}).iteritems()
        elif item == 'cols':
            return self.cols or []
        elif item == 'campaign':
            return self.campaign_status or []
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
