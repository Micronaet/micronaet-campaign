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
    
        #  --------------------------------------------------------------------
        #                    Create / update campaign.product:        
        #  --------------------------------------------------------------------
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]

        campaign_pool = self.pool.get('campaign.campaign')
        campaign_product_pool = self.pool.get('campaign.product')
        product_pool = self.pool.get('product.product')
        
        # Dict for check presence
        current_product = {}
        for product in wiz_proxy.campaign_id.product_ids:
            current_product[product.product_id.id] = product.id # save ID

        from_selection = wiz_proxy.from_selection
        campaign_id = wiz_proxy.campaign_id.id
        mode = wiz_proxy.mode
        min_qty = wiz_proxy.min_qty
        max_qty = wiz_proxy.max_qty
        use_rate = wiz_proxy.use_rate

        # Start up parameters:
        if from_selection: # load selection in context
            product_ids = context.get('active_ids', []) # get product selected
        else: # load selection in campaign
            product_ids = [
                item.product_id.id for item in campaign_id.product_ids]

        if not product_ids:
            _logger.warning('No product selected or empty campaign!')
            return {'type': 'ir.actions.act_window_close'} # TODO new campaign
                
        # ---------------------------------------------------------------------
        #                       Loop on all selected product:
        # ---------------------------------------------------------------------
        log = ''
        product_discarded = [] # for delete in override mode
        for product in product_pool.browse(
                cr, uid, product_ids, context=context):
                            
            update_id = False            
            if product.id in current_product: # jet present
                # jump mode:
                if mode == 'jump': 
                    log += 'Jump product mode: %s\n' % product.default_code
                    continue
                # update mode:    
                update_id = current_product[product.id]

            # ---------------
            # Qty generation:
            # ---------------
            # Get data for calculare:
            lord_qty = product.mx_lord_qty
            # TODO manage campaign qty
            q_x_pack = product.q_x_pack or 1  
            
            if lord_qty > 0:
                qty = lord_qty * use_rate / 100
                qty -= qty % q_x_pack # - extra from pack
                original_qty = qty
                if min_qty and qty < min_qty:
                    qty = 0 # No in min qty treshold so not used
                if max_qty and qty > max_qty:
                    qty = max_qty                    
            else:
                qty = 0 # not used
                original_qty = qty
                
            # Test if need to be write:    
            if not qty:                
                if update_id: # deleted after in campaign
                    product_discarded.append(update_id)
                    log_msg = 'DELETED %s cause of qty: %s\n'
                else:    
                    log_msg = 'DISCARD %s cause of qty: %s\n'
                log += log_msg % (
                    product.default_code,
                    original_qty,
                    )                                          
                continue # jump element (write in log?    
            # TODO test if need to be deleted                              
            
            # TODO Price generation:
            campaign_price = product.lst_price
            
            data = {
                'is_active': True,
                'campaign_id': campaign_id,
                'qty': qty,
                'product_id': product.id,
                'uom_id': product.uom_id.id,
                'description': product.name,
                'cost': product.standard_price,
                'price': product.lst_price,            
                'campaign_price': campaign_price, # start value
                ##'qty_ordered': 0
                }
            if update_id:
                campaign_product_pool.write(
                    cr, uid, update_id, data, context=context)
            else:
                campaign_product_pool.create(
                    cr, uid, data, context=context)

        # -------------------------------------
        # Delete discarded product yet present:
        # -------------------------------------
        if product_discarded:
            campaign_product_pool.unlink(
                cr, uid, product_discarded, context=context)
                
        # ------------------------------
        # Write data on campaign header:
        # ------------------------------
        campaign_data = {
            'use_rate': use_rate,
            'min_qty': min_qty,
            'max_qty': max_qty,
            }
        if log:
            campaign_data['log'] = log
            
        campaign_pool.write(
            cr, uid, campaign_id, campaign_data, context=context)
        
        # ----------
        # Open view: 
        # ----------
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
        'from_selection': fields.boolean('From selection', 
            help='From selected product, instead take product list of campaign'
                ' for recalculate'),
        'campaign_id': fields.many2one(
            'campaign.campaign', 'Campaign', required=True,
            domain=[('state', 'in', ('draft', 'confirmed'))],
            help='Campaign to associate'),
        'mode': fields.selection([
            ('override', 'Override product qty'),
            ('jump', 'Jump existing product'),
            ], 'Mode', required=True),
        'note': fields.text(
            'Annotation', readonly=True,
            help='Annotation about product association'),
            
        # Q.ty generation:
        'use_rate': fields.float('Use rate', digits=(16, 3), required=True),
        'min_qty': fields.integer('Min. qty', required=True,
            help='If product is not >= min qty will be discard'),
        'max_qty': fields.integer('Max. qty', 
            help='If product > max qty will be used max qty instead'),
        'check_min_package': fields.boolean('Check min pack', 
            help='Use min package qty multiple, es. N.10 , 4 pack >> N.8 '),            
        }
        
    _defaults = {
        'from_selection': lambda *x: True,
        'mode': lambda *x: 'override',
        'min_qty': lambda *x: 1,
        }        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
