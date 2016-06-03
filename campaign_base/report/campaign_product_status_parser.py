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
            'get_cells': self.get_cells,
        })

    def load_data(self, data):
        ''' Load data
        '''
        # Setup:
        data = data or {}
        cr = self.cr
        uid = self.uid
        
        # Initialize elements for report:
        self.row = []
        self.column = {}
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
        
        # Check all campaign
        for campaign in campaign_pool.browse(cr, uid, campaign_ids):
            # Check all product-items:
            for item in campaign.product_ids:
                product = item.product_id
                if product not in self.cells:
                    # Initial status:
                    (net, lord) = product_pool.get_inventory_net_lord_status(
                        cr, uid, product)
                        
                    # Generate empty element
                    self.cells[product] = [0 for day in range(0, days)]
                    self.cells[product][0] = lord # choose here what value
                # TODO data setup    
        return ''
    
    def get_filter(self, data):
        ''' Get description for filter applied
        '''
        data = data or {}
        res = ''
        res += _(' >> Period days: %s ') % data.get('days', '?')
        res += _(' >> Mode: %s ') % data.get('mode', '?')
        return res

    def get_cells(self, ):
        ''' Load data
        '''
        return (self.cells or {}).iteritems()
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
