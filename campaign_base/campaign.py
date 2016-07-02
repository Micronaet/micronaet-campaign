# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
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

class CampaignCampaign(orm.Model):
    """ Model name: campaign campaign
    """    
    _name = 'campaign.campaign'
    _inherit = ['mail.thread']
    _description = 'Campaign'

    # --------
    # Utility:
    # --------
    def assign_type_price_to_product(self, cr, uid, campaign, context=None):
        ''' Procedure for force assign price to product selected
            campaign: browse object for selected campaign
        '''
        # This procedure will be overrided from module that manage product 
        # association rules. No association for base procedure!        
        return True

    # -------------------------------------------------------------------------
    #                             Button event:
    # -------------------------------------------------------------------------
    def reset_log_event(self, cr, uid, ids, context=None):
        ''' Remove log
        '''
        return self.write(cr, uid, ids, {'log': False}, context=context)

    def generate_campaign_price(self, cr, uid, ids, context=None):
        ''' Force campaign price depend on cost group
        '''
        assert len(ids) == 1, 'Button for one campaign a time!'
        
        cost_pool = self.pool.get('campaign.cost.type')
        product_pool = self.pool.get('campaign.product')
        
        campaign = self.browse(cr, uid, ids, context=context)[0]

        # Link rule to product:
        self.assign_type_price_to_product(cr, uid, campaign, context=context)
        for product in campaign.product_ids:
            campaign_price = cost_pool.get_campaign_price(
                product.cost, product.price, 
                campaign, product, product.cost_type_id,
                )
            product_pool.write(cr, uid, product.id, {
                'campaign_price': campaign_price,
                }, context=context) # TODO check no dependency problems!!         
        return True
        
    # -------------------------------------------------------------------------
    #                                Utility:
    # -------------------------------------------------------------------------
    def create_campaing_sale_order(self, cr, uid, ids, context=None):
        ''' Create sale order from campaign product
            # TODO manage also update!!!
        '''
        assert len(ids) == 1, 'Only one campaign a time!'
        
        # Current record:
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Check presence of order:
        
        # Pool used
        order_pool = self.pool.get('sale.order')
        sol_pool = self.pool.get('sale.order.line')
        
        # ---------------------------------------------------------------------
        #                    Create order header
        # ---------------------------------------------------------------------
        # TODO onchange element!!!
        partner_id = current_proxy.partner_id.id        
        date = current_proxy.to_date
        deadline = current_proxy.date_deadline or date # dedaline or end date!
        data = order_pool.onchange_partner_id(
            cr, uid, False, partner_id, context=context).get('value', {})
        data.update({
            'partner_id': partner_id,
            'date_order': date,
            'date_deadline': deadline,
            'campaign_id': current_proxy.id,
            })
        res_id = order_pool.create(cr, uid, data, context=context)
            
        # ---------------------------------------------------------------------
        #                    Create order details
        # ---------------------------------------------------------------------
        for item in current_proxy.product_ids:            
            qty = item.qty_ordered
            if qty <= 0 or not item.is_active:
                continue # jump line
            
            product_id = item.product_id.id
            # On change for calculate data:
            line_data = sol_pool.product_id_change_with_wh(
                cr, uid, False, 
                data.get('pricelist_id'), 
                product_id, 
                qty,
                uom=item.uom_id.id, # TODO change 
                qty_uos=0, 
                uos=False, 
                name=item.description, 
                partner_id=partner_id, 
                lang=context.get('lang', 'it_IT'), 
                update_tax=True, 
                date_order=date, 
                packaging=False, 
                fiscal_position=data.get('fiscal_position'), 
                flag=False, 
                warehouse_id=data.get('warehouse_id'),
                context=context,
                ).get('value', {})
                
            line_data.update({
                'order_id': res_id,
                'product_id': product_id,
                'product_uom_qty': qty,
                'product_uom': item.uom_id.id, # no uom_id
                'price_unit': item.campaign_price,
                'date_deadline': deadline,
                # TODO measure data?!?
                })
                
            # Update *2many fields:    
            if 'tax_id' in line_data:
                line_data['tax_id'] = [(6, 0, line_data['tax_id'])]      
                
            sol_pool.create(cr, uid, line_data, context=context)    
        
        # ---------------------------------------------------------------------
        #                    Update campaign
        # ---------------------------------------------------------------------
        return self.write(cr, uid, ids, {
            'sale_id': res_id, # link to order 
            }, context=context)        
        
    def write_object_change_state(self, cr, uid, ids, context=None):
        ''' Write info in thread list (used in WF actions)
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]

        # Default part of message:
        message = { 
            'subject': _('Changing state:'),
            'body': _('State variation in <b>%s</b>') % current_proxy.state,
            'type': 'comment', #'notification', 'email',
            'subtype': False,  #parent_id, #attachments,
            'content_subtype': 'html',
            'partner_ids': [],            
            'email_from': 'openerp@micronaet.it', #wizard.email_from,
            'context': context,
            }
        #message['partner_ids'].append(
        #    task_proxy.assigned_user_id.partner_id.id)
        self.message_subscribe_users(
            cr, uid, ids, user_ids=[uid], context=context)
                        
        msg_id = self.message_post(cr, uid, ids, **message)
        #if notification: 
        #    _logger.info(">> Send mail notification! [%s]" % message[
        #    'partner_ids'])
        #    self.pool.get(
        #        'mail.notification')._notify(cr, uid, msg_id, 
        #        message['partner_ids'], 
        #        context=context
        #        )       
        return    

    # -------------------------------------------------------------------------
    #                        Workflow button events
    # -------------------------------------------------------------------------
    def campaign_draft(self, cr, uid, ids, context=None):        
        self.write(cr, uid, ids, {
            'state': 'draft',
            }, context=context)
        return self.write_object_change_state(cr, uid, ids, context=context)
            

    def campaign_confirmed(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'confirmed',
            }, context=context)
        return self.write_object_change_state(cr, uid, ids, context=context)
    
            
    def campaign_closed(self, cr, uid, ids, context=None):
        self.create_campaing_sale_order(cr, uid, ids, context=context)
        # Write here res_id returned?
        self.write(cr, uid, ids, {
            'state': 'closed',
            }, context=context)
        return self.write_object_change_state(cr, uid, ids, context=context)
        # TODO return order and redirect to it

    def campaign_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'cancel',
            }, context=context)
        return self.write_object_change_state(cr, uid, ids, context=context)
    
    # -------------------------------------------------------------------------
    #                            Fields functions 
    # -------------------------------------------------------------------------    
    def _function_get_status_info(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        # TODO manage status for start info depend on state value
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=20, readonly=True),
        'from_date': fields.date('From date >=', required=True),
        'to_date': fields.date('To date <=', required=True),
        'date_deadline': fields.date('Deadline', help='For order deadline'),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True,
            help='Partner (as customer) reference for this campaign'), 
        'partner_address_id': fields.many2one('res.partner', 'Address',
            help='Partner (as customer) reference for this campaign'), 
            
        # Album for product photo        
        'with_photo': fields.boolean('With photo'), # TODO so album!!
        'with_detail': fields.boolean('With detail', # XXX needed?
            help='One product may have more than one other detail photo'), 
        'thumb_album_id': fields.many2one(
            'product.image.album', 'Thumb Album', 
                help='Album for thumb low resolution photo (XLS files)'), 
        'album_id': fields.many2one('product.image.album', 'Album', 
            help='Album for ZIP HQ images'), 
        # TODO more than one album ?        
        
        # Product qty generation parameters for / from wizard:
        'use_rate': fields.float('Use rate', digits=(16, 3)),
        'set_min_qty': fields.integer('Set min. qty', 
            help='If present is the minimum qty value'),
        'min_qty': fields.integer('Min. qty', 
            help='If product is not >= min qty will be discard'),
        'max_qty': fields.integer('Max. qty', 
            help='If product > max qty will be used max qty instead'),
        
        # Price creation: TODO decide how to use
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
            help='''Pricelist used for this campaign (calculate end price 
                'before discount'''), 
        'discount_scale': fields.char('Discount scale', size=60), 
        'volume_cost': fields.float(
            'Volume cost', digits_compute=dp.get_precision('Product Price')),

        # Order reference
        'sale_id': fields.many2one(
            'sale.order', 'Sale order', readonly=True,
            help='Sale order generated from campaign'), 
        
        'status_info': fields.function(
            _function_get_status_info, method=True, 
            type='char', size=40, string='Status info', store=False, 
            help='Text status info for start or end campaign'),             
        'note': fields.text('Note'),
        'log': fields.text('Log', readonly=True, help='Log assign operation'),
        
        # Function fields:
        # TODO total cost and revenue (for all products) campaign and order
       
        'state': fields.selection([
            ('draft', 'Draft'), # not working no stock operation
            ('confirmed', 'Confirmed'), # stock operation confirmed
            ('closed', 'Closed'), # Unload stock depend on order
            ('cancel', 'Cancel'), # Remove stock info as no exist
            ], 'State', readonly=True),
        }

    _defaults = {
        'code': lambda s, cr, uid, ctx=None: s.pool.get('ir.sequence').get(
            cr, uid, 'campaign.campaign'),
        'from_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'state': lambda *x: 'draft',
        }    

class CampaignCostCategory(orm.Model):
    """ Model name: Campaign cost category
    """    
    _name = 'campaign.cost.category'
    _description = 'Campaign cost category'
    
    _columns = {
        'name': fields.char(
            'Cost category', size=64),
        'note': fields.text('Note'),
        }

class CampaignCostType(orm.Model):
    """ Model name: Campaign cost type
    """    
    _name = 'campaign.cost.type'
    _description = 'Campaign cost type'
        
    def get_campaign_price(self, cost, price, campaign, product, cost_type):
        ''' Master function for calculate price depend on rules:
            cost: cost price for product
            price: sale price for product
            volume_rate: 
            BROWSE OBJ:
            cost_type: all rules for product cost type
            campaign: campaign, used for get extra cost or discount
            product: used to get extra info from product (ex. volume)            
        '''
        # --------------
        # Initial setup:
        # --------------
        # Pool used:
        partner_pool = self.pool.get('res.partner')

        # -----------
        # Start test:
        # -----------
        if not cost_type:
            _logger.warning('No cost type use sale price') # TODO correct?
            return price
        
        # ---------------------------------------------------------------------
        # Product cost generation:
        # ---------------------------------------------------------------------
        total = 0.0
        for rule in cost_type.rule_ids:
            # Read rule parameters
            sign = rule.sign
            base = rule.base
            mode = rule.mode
            value = rule.value
            text_value = rule.text_value
            
            # -----------
            # Sign coeff:
            # -----------
            if sign == 'plus':
                sign_coeff = +1.0
            else:
                sign_coeff = -1.0  
                
            # ----------------
            # Base evaluation:
            # ----------------
            if base == 'previous':
                base_value = total
            elif base == 'cost':
                base_value = cost
                if not total: # Initial setup depend on first rule
                    total = cost 
            elif base == 'price':
                base_value = price
                if not total: # Initial setup depend on first rule
                    total = price
            #elif base == 'volume':
            #    base_value = (
            #        product.volume / campaign.volume_total)                    
            else:
                _logger.error('No base value found!!!')
                # TODO raise error?        

            # -----------
            # Value type:
            # -----------
            if mode == 'fixed':
                total += sign_coeff * value
                continue # Fixed case only increment total no other operations
                
            elif mode == 'multi':
                # Convert multi discount with value
                value = sign_coeff * partner_pool.format_multi_discount(
                    text_value).get('value', 0.0)
            elif mode == 'percentual':
                value *= sign_coeff
            else:    
                _logger.error('No mode value found!!!')
                # TODO raise error?        
                    
            if not value:
                _logger.error('Percentual value is mandatory!')
                pass
            total += base_value * value / 100.0

        # --------------------------------
        # General cost depend on campaign:    
        # --------------------------------
        volume_cost = campaign.volume_cost
        discount_scale = campaign.discount_scale
        
        # TODO:
        if volume_cost:        
            total += total * product.volume / campaign.volume_total
            # TODO use heigh, width, length 
            # TODO use pack_l, pack_h, pack_p
            # TODO use packaging dimension?
            
        if discount_scale:
            discount_value = partner_pool.format_multi_discount(
                discount_scale).get('value', 0.0)
            total -= total * discount_value / 100.0

        return total
        
    _columns = {
        'name': fields.char('Cost type', size=64, required=True, 
            help='Cost depend on product category'), 
        'campaign_id': fields.many2one('campaign.campaign', 'Campaign', 
            help='Campaign referente', ondelete='cascade'),
        # TODO add filter for product    
        }

class CampaignCost(orm.Model):
    """ Model name: Campaign cost
    """    
    _name = 'campaign.cost'
    _description = 'Campaign cost'
    _rec_name = 'sequence' #category_id'
    _order = 'sequence' #,category_id'
    
    _columns = {
        'sequence': fields.integer('Sequence'),
        'type_id': fields.many2one('campaign.cost.type', 'Cost type', 
            help='Campaign reference', ondelete='cascade'),
        'category_id': fields.many2one('campaign.cost.category', 'Category', 
            help='Campaign referente', ondelete='set null'),
        'description': fields.char('Description', size=64),
        'base': fields.selection([
            ('cost', 'Cost'),
            ('price', 'Price'),
            ('previous', 'Previous'),
            #('volume', 'Volume'),
            ], 'Base', required=True),
        'value': fields.float(
            'Value', digits_compute=dp.get_precision('Product Price')),
        'text_value': fields.char('Text value', size=30, 
            help='Used for multi discount element'),
        'mode': fields.selection([
            ('fixed', 'Fixed'),
            ('percentual', 'Percentual'),
            ('multi', 'Multi percentual'),
            ], 'Cost mode', required=True),
        'sign': fields.selection([
            ('add', '+'),
            ('minus', '-'),
            ], 'Sign', required=True),
        'note': fields.char('Note', size=80),
        }
        
    _defaults = {
        # Default value:
        'base': lambda *x: 'cost',
        'mode': lambda *x: 'percentual',
        'sign': lambda *x: 'add',
        }    

class CampaignCostType(orm.Model):
    """ Model name: Campaign cost type
    """    
    _inherit = 'campaign.cost.type'

    _columns = {
        'rule_ids': fields.one2many('campaign.cost', 'type_id', 'Cost rule', 
            ondelete='cascade'),
        }

class CampaignProduct(orm.Model):
    """ Model name: Campaign product
    """    
    _name = 'campaign.product'
    _description = 'Campaign product'
    _rec_name = 'product_id'
    _order = 'sequence,product_id'    
    
    # -------------
    # Button event:
    # -------------
    def assign_all(self, cr, uid, ids, context=None):
        ''' Assign all qty to order
        '''
        current_proxy = self.browse(cr, uid, ids, context=context)[0]
        return self.write(cr, uid, ids, {
            'qty_ordered': current_proxy.qty,
            }, context=context)

    def assign_zero(self, cr, uid, ids, context=None):
        ''' Assign all qty to order
        '''
        return self.write(cr, uid, ids, {
            'qty_ordered': 0,
            }, context=context)

    _columns = {
        'is_active': fields.boolean('Is active'),
        'sequence': fields.integer('Sequence'), # XXX used for order?
        'product_id': fields.many2one('product.product', 'Product', 
            required=True, #domain=[('type', 'in', ('service'))])
            ondelete='set null', help='Product in campaign',     
            ),
        'campaign_id': fields.many2one('campaign.campaign', 'Campaign', 
            help='Campaign referente', ondelete='cascade'),
        'description': fields.char(
            'Description', size=64),
            
        # TODO add extra description related or extra for information needed 
        # for sale purpose (ex. mount description)    
        'cost': fields.float(
            'Cost', digits_compute=dp.get_precision('Product Price')),
        'price': fields.float(
            'Price', digits_compute=dp.get_precision('Product Price')),     
        'campaign_price': fields.float(
            'Campaign price', digits_compute=dp.get_precision('Product Price')
            ),     
            
        'qty': fields.float(
            'Q.', digits_compute=dp.get_precision('Product Unit of Measure')
            ),     
        'qty_ordered': fields.float(
            'Q. ordered', 
            digits_compute=dp.get_precision('Product Unit of Measure')
            ),     
        'uom_id': fields.many2one( # TODO used?
            'product.uom', 'UOM', ondelete='set null'),
        
        'q_x_pack': fields.related('product_id', 'q_x_pack',
            type='float', string='Q. x pack'), 

        'cost_type_id': fields.many2one('campaign.cost.type', 'Cost type',
            help='Cost type reference', ondelete='set null'),

        # -----------------------
        # Product related fields: 
        # -----------------------
        # TODO choose which are needed!:
        # package (link)        
        # default_code
        # EAN
        # Supplier EAN
        # Volume
        # Dimension H x L x P
        # Photo status (present or not)
        }

    _defaults = {
        'sequence': lambda *x: 10,
        'is_active': lambda *x: True,
        'qty': lambda *x: 1.0,
        }    

class CampaignCampaign(orm.Model):
    """ Model name: Rel fields for Campaign Campaign
    """    
    _inherit = 'campaign.campaign'
    
    _columns = {
        'product_ids': fields.one2many(
            'campaign.product', 'campaign_id', 'Products'), 
        'cost_ids': fields.one2many(
            'campaign.cost.type', 'campaign_id', 'Costs'), 
        }

class ResPartner(orm.Model):
    """ Model name: Res partner for campaign
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'used_campaign': fields.boolean('Used for campaign', 
            help='If checked will be used for campaign customer'),
        }

class SaleOrder(orm.Model):
    """ Sale order from campaign
    """    
    _inherit = 'sale.order'
    
    _columns = {
        'campaign_id': fields.many2one(
            'campaign.campaign', 'Campaign', ondelete='set null'),
        }

class StockMove(orm.Model):
    """ Stock move for campaign
    """    
    _inherit = 'stock.move'
    
    _columns = {
        'campaign_product_id': fields.many2one(
            'campaign.product', 'Move from campaign', 
            ondelete='cascade',
            help='Line generated from campaign product line'),
        }

# TODO manage product in campaign as stock.move??
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
