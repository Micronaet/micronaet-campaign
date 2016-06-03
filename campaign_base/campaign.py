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

    # -------------------------------------------------------------------------
    #                             Utility
    # -------------------------------------------------------------------------
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
    def _function_get_stasus_info(self, cr, uid, ids, fields, args, context=None):
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
        'partner_id': fields.many2one('res.partner', 'Partner', required=True,
            help='Partner (as customer) reference for this campaign', 
            domain=[
                ('customer', '=', True),
                ('is_company', '=', True)]), 
            
        # Album for product photo        
        'with_photo': fields.boolean('With photo'), # TODO so album!!
        'with_detail': fields.boolean('With detail', # XXX needed?
            help='One product may have more than one other detail photo'), 
        'album_id': fields.many2one('product.image.album', 'Album'), 
        # TODO more than one album ?        
        
        # Price creation: TODO decide how to use
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
            help='''Pricelist used for this campaign (calculate end price 
                'before discount'''), 
        'discount_scale': fields.char('Discount scale', size=64), 
        
        # Order reference
        'sale_id': fields.many2one(
            'sale.order', 'Sale order', readonly=True,
            help='Sale order generated from campaign'), 
        
        'status_info': fields.function(
            _function_get_stasus_info, method=True, 
            type='char', size=40, string='Status info', store=False, 
            help='Text status info for start or end campaign'),             
        'note': fields.text('Note'),
        
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
        'state': lambda *x: 'draft',
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
            ondelete='set null',
            help='Product in campaign',     
            ),
        'campaign_id': fields.many2one('campaign.campaign', 'Campaign', 
            help='Campaign referente', required=True, 
            ondelete='cascade'),
        'description': fields.char(
            'Description', size=64, required=True),
            
        # TODO add extra description related or extra for information needed 
        # for sale purpose (ex. mount description)    
        'cost': fields.float(
            'Cost', digits_compute=dp.get_precision('Product Price'), 
            required=True),
        'price': fields.float(
            'Price', digits_compute=dp.get_precision('Product Price'),
            required=True),     
        # Add extra parameter for calculate price?
            
        'qty': fields.float(
            'Q.', digits_compute=dp.get_precision('Product Unit of Measure')
            ),     
        'qty_ordered': fields.float(
            'Q. ordered', 
            digits_compute=dp.get_precision('Product Unit of Measure')
            ),     
        'uom_id': fields.many2one( # TODO used?
            'product.uom', 'UOM', ondelete='set null', required=True),
        
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
