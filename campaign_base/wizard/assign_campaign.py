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

class ProductProductAssignCampaign(orm.TransientModel):
    ''' Assign product to existent campaign
    '''    
    _name = 'product.product.assign.campaign'

    # --------------
    # Wizard button:
    # --------------
    def action_assign_campaign(self, cr, uid, ids, context=None):
        ''' Assign production to selected order line
        '''
        if context is None: 
            context = {}
        product_ids = context.get('active_ids', []) # get product selected

        if not product_ids:
            _logger.warning('No product selected, no add in campaign!')
            return {'type': 'ir.actions.act_window_close'} # TODO new campaign
    
        #  -----------------------
        # Create campaign.product:        
        #  -----------------------
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]

        campaign_product_pool = self.pool.get('campaign.product')
        product_pool = self.pool.get('product.product')
        
        # Dict for check presence
        current_product = {}
        for product in wiz_proxy.campaign_id.product_ids:
            current_product[product.product_id.id] = product.id # save ID

        campaign_id = wiz_proxy.campaign_id.id
        mode = wiz_proxy.mode
        
        for product in product_pool.browse(
                cr, uid, product_ids, context=context):

            update_id = False            
            if product.id in current_product:
                if mode == 'jump':
                    continue # jump
                update_id = current_product[product.id]
            
            if update_id:        
                campaign_product_pool.write(cr, uid, update_id, {
                    'is_active': True,
                    #'campaign_id': campaign_id,
                    'qty': wiz_proxy.qty,                
                    #'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'description': product.name,
                    'cost': product.standard_price,
                    'price': product.lst_price,
                    ##'qty_ordered': 0
                    }, context=context)
            else:
                campaign_product_pool.create(cr, uid, {
                    'is_active': True,
                    'campaign_id': campaign_id,
                    'qty': wiz_proxy.qty,                    
                    'product_id': product.id,
                    'uom_id': product.uom_id.id,
                    'description': product.name,
                    'cost': product.standard_price,
                    'price': product.lst_price,
                    #'qty_ordered': 0
                    }, context=context)

        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(cr, uid, 
            'campaign_base', 'view_campaign_campaign_form')[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Campaign populated:'),
            'view_type': 'form',
            'view_mode': 'form,tree,calendar',
            'res_id': campaign_id,
            'res_model': 'campaign.campaign',
            'view_id': view_id, # False
            'views': [(False, 'form'), (False, 'tree'), (False, 'calendar')],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }            

    _columns = {
        'campaign_id': fields.many2one(
            'campaign.campaign', 'Campaign', required=True,
            domain=[('state', 'in', ('draft', 'confirmed'))],
            help='Campaign to associate'),
        'mode': fields.selection([
            ('override', 'Override product qty'),
            ('jump', 'Jump existing product'),
            ], 'mode', required=True),
        'note': fields.text(
            'Annotation', readonly=True,
            help='Annotation about product association'),
            
        # Q.ty generation:
        'available': fields.boolean('% on available', 
            help='Use available lord qty quantity'),
        'qty': fields.integer('Initial qty'),
        'use_rate': fields.float('Use rate', digits=(16, 3)),
        'min_qty': fields.integer('Min. qty'),
        'max_qty': fields.integer('Max. qty'),
        'check_min_package': fields.boolean('Check min pack', 
            help='Use min package qty multiple, es. N.10 , 4 pack >> N.8 '),            
        }
        
    _defaults = {
        'available': lambda *x: True,
        'mode': lambda *x: 'override',
        }        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
