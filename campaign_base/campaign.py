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
    def check_image_album_presence_report(self, cr, uid, ids, context=None):
        ''' Open report for check image
        '''
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'campaign_campaign_check_image_report', 
            'context': context,
            }
    def check_image_album_presence_calc_report(self, cr, uid, ids, context=None):
        ''' Open report for check image with calc
        '''        
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'campaign_campaign_check_image_report', 
            'context': context,
            'datas': {'with_cost': True},
            }
    
    def check_image_album_presence(self, cr, uid, ids, context=None):
        ''' Check if the product_ids in campaign are in album
        '''        
        product_ids = [
            item.product_id.id for item in self.browse(
                cr, uid, ids, context=context)[0].product_ids]
        
        # Get view for check image:
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(
            cr, uid, 
            'product_image_base', 'view_product_product_check_tree')[1]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Check campaign image'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'product.product',
            'view_id': view_id, # False
            'views': [(view_id, 'tree'), (False, 'form')],
            'domain': [('id', 'in', product_ids)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }
            
    def reset_log_event(self, cr, uid, ids, context=None):
        ''' Remove log
        '''
        return self.write(cr, uid, ids, {'log': False}, context=context)

    def reload_base_campaign_price(self, cr, uid, ids, context=None):
        ''' Reload cost and pricelist
        '''
        assert len(ids) == 1, 'Button for one campaign a time!'
        
        campaign = self.browse(cr, uid, ids, context=context)[0]
        line_pool = self.pool.get('campaign.product')

        for line in campaign.product_ids:
            line_pool.write(cr, uid, line.id, {
                'cost': line.product_id.__getattribute__(
                    campaign.base_cost), # param.
                'price': line.product_id.lst_price,                
                }, context=context)
        return True

    def generate_campaign_price(self, cr, uid, ids, context=None):
        ''' Force campaign price depend on cost group
        '''
        assert len(ids) == 1, 'Button for one campaign a time!'
        
        cost_pool = self.pool.get('campaign.cost.type')
        product_pool = self.pool.get('campaign.product')
        
        campaign = self.browse(cr, uid, ids, context=context)[0]

        # Link rule to product:
        self.assign_type_price_to_product(cr, uid, campaign, context=context)
        for product_line in campaign.product_ids:
            data = cost_pool.get_campaign_price(campaign, product_line)
            #campaign_price = cost_pool.get_campaign_price(
            #    product.cost, product.price, 
            #    campaign, product, product.cost_type_id,
            #    )
            product_pool.write(cr, uid, product_line.id, data, 
                context=context) # TODO check no dependency problems!!         
        return True
        
    # -------------------------------------------------------------------------
    #                                Utility:
    # -------------------------------------------------------------------------
    def create_campaing_sale_order(self, cr, uid, ids, context=None):
        ''' Create sale order from campaign product
            # TODO manage also update!!!
        '''
        assert len(ids) == 1, 'Only one campaign a time!'
        current_proxy = self.browse(cr, uid, ids, context=context)[0]

        # Pool used
        order_pool = self.pool.get('sale.order')
        sol_pool = self.pool.get('sale.order.line')
        
        # Check parent if present
        sale_id = False
        if current_proxy.parent_id:
            if current_proxy.parent_id.sale_id:
                sale_id = current_proxy.parent_id.sale_id.id
            else:   
                raise osv.except_osv(
                    _('Child campaign'), 
                    _('This is a child campaign, confirm the parent one\'s'),
                    )
        
        # ---------------------------------------------------------------------
        # Check presence of order and create:
        # ---------------------------------------------------------------------
        # Get data from campaign:
        partner_id = current_proxy.partner_id.id        
        date = current_proxy.to_date
        deadline = current_proxy.date_deadline or date # dedaline or end date!
        
        # ---------------------------------------------------------------------
        #                    Create order header
        # ---------------------------------------------------------------------
        if not sale_id:            
            data = order_pool.onchange_partner_id(
                cr, uid, False, partner_id, context=context).get('value', {})
            data.update({
                'partner_id': partner_id,
                'date_order': date,
                'date_deadline': deadline,
                'campaign_id': current_proxy.id,
                })
            sale_id = order_pool.create(cr, uid, data, context=context)
            
        # Read header for get element for line:    
        order_proxy = order_pool.browse(cr, uid, sale_id, context=context)
          
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
                order_proxy.pricelist_id.id, 
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
                fiscal_position=order_proxy.fiscal_position.id, 
                flag=False, 
                warehouse_id=order_proxy.warehouse_id.id,
                context=context,
                ).get('value', {})
                
            line_data.update({
                'order_id': sale_id,
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
            'sale_id': sale_id, # link to order 
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
    def generate_sale_order(self, cr, uid, ids, context=None):
        ''' Button for generate order in cancel campaign for error
        '''
        self.create_campaing_sale_order(cr, uid, ids, context=context)
        # Write here res_id returned?
        self.write(cr, uid, ids, {
            'state': 'closed',
            }, context=context)
        return self.write_object_change_state(cr, uid, ids, context=context)
        
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

    def _get_total_volume(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for campaign in self.browse(cr, uid, ids, context=context):
            volume = 0.0
            for product in campaign.product_ids:
                volume += product.volume #* product.qty
            res[campaign.id] = volume
        return res

    def _get_transport_unit(self, cr, uid, ids, fields, args, context=None):
        ''' Fields function for calculate 
        '''
        res = {}
        for campaign in self.browse(cr, uid, ids, context=context):
            if  campaign.transport_id and campaign.transport_id.volume:
                res[campaign.id] = campaign.transport_cost / \
                    campaign.transport_id.volume
            else:
                res[campaign.id] = 0.0
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
        'parent_id': fields.many2one('campaign.campaign', 'Parent'),    
            
        # Album for product photo        
        'with_photo': fields.boolean('With photo'), # TODO so album!!
        'with_detail': fields.boolean('With detail', # XXX needed?
            help='One product may have more than one other detail photo'), 
        'thumb_album_id': fields.many2one(
            'product.image.album', 'Album Thumb', 
                help='Album for thumb low resolution photo (XLS files)'), 
        'album_id': fields.many2one('product.image.album', 'Album HQ', 
            help='Album for ZIP HQ images'), 
        
        # Product qty generation parameters for / from wizard:
        'use_rate': fields.float('Use rate', digits=(16, 3)),
        'set_min_qty': fields.integer('Set min. qty', 
            help='If present is the minimum qty value'),
        'min_qty': fields.integer('Min. qty', 
            help='If product is not >= min qty will be discard'),
        'max_qty': fields.integer('Max. qty', 
            help='If product > max qty will be used max qty instead'),
        
        # Price creation: TODO not used for now!
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
            help='''Pricelist used for this campaign (calculate end price 
                'before discount'''), 

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
        'volume_total': fields.function(
            _get_total_volume, method=True, type='float', string='Tot. Volume',
            store=False), 
                        
        # Function fields:
        # TODO total cost and revenue (for all products) campaign and order

        'base_cost': fields.selection([
            ('standard_price', 'Cost FOB Supplier'),
            #('cost_in_stock', 'Cost FCO Company'),
            #('cost_for_sale', 'Cost FCO Customer'),
            ('company_cost', 'Cost FCO Company'),
            ('customer_cost', 'Cost FCO Customer'),
            ], 'Base cost', required=True, 
            help='Choose base cost from product to campaign'),

        'transport_id': fields.many2one(
            'product.cost.transport', 'Default transport'),
        'transport_cost': fields.float('Transport cost', 
            digits_compute=dp.get_precision('price_accuracy'), 
            help='Total cost for one tranport method choosen'),
        'transport_unit': fields.function(
            _get_transport_unit, method=True, 
            type='float', string='Transport unit', store=False), 
       
        'state': fields.selection([
            ('draft', 'Draft'), # not working no stock operation
            ('confirmed', 'Confirmed'), # stock operation confirmed
            ('closed', 'Closed'), # Unload stock depend on order
            ('cancel', 'Cancel'), # Remove stock info as no exist
            ], 'State', readonly=True),
        }

    _defaults = {
        'code': lambda s, cr, uid, ctx: s.pool.get('ir.sequence').get(
            cr, uid, 'campaign.campaign'),
        'from_date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATE_FORMAT),
        'base_cost': lambda *x: 'cost_in_stock',    
        'state': lambda *x: 'draft',        
        }

class CampaignCostType(orm.Model):
    """ Model name: Campaign cost type
    """    
    _name = 'campaign.cost.type'
    _description = 'Campaign cost type'
    
    # Parameters used:
    _excluded_fields = (
        'create_uid', 'create_date', 'write_uid', 'write_date', 
        'model_id', 'type_id', 'id')
    _excluded_type = ('one2many', 'many2many', 'related', 'function')    
    
     # Button for templating:
    def save_as_model(self, cr, uid, ids, context=None):
        ''' Save all selected cost element as model
        '''
        # Pool used:
        model_pool = self.pool.get('campaign.cost.model')
        item_pool = self.pool.get('campaign.cost.model.item')

        cost_proxy = self.browse(cr, uid, ids, context=context)[0]
        name = cost_proxy.model_name
        if not name:
            raise osv.except_osv(
                _('Name error!'),
                _('Set a name for model before create!'),
                )
                
        # Create model:
        model_id = model_pool.create(cr, uid, {
            'name': name}, context=context)
            
        # Add cost elements: 
        for cost in cost_proxy.rule_ids:
            # loop on field:
            data = {'model_id': model_id}
            for field in cost._columns.keys():
                field_type = cost._columns[field]._type
                
                # Jump exluded field or excluded type
                if field in self._excluded_fields or \
                        field_type in self._excluded_type:
                    continue
                    
                if field_type == 'many2one':
                    data[field] = cost.__getattribute__(field).id
                else:       
                    data[field] = cost.__getattribute__(field)
            item_pool.create(cr, uid, data, context=context)
            
        # Reset model name after create:        
        self.write(cr, uid, ids, {
            'model_name': False}, context=context)        
        return True
        
    def load_from_model(self, cr, uid, ids, context=None):    
        ''' Load from model cost (deleted before)
        '''
        # Pool used:
        model_pool = self.pool.get('campaign.cost.model')
        cost_pool = self.pool.get('campaign.cost')

        cost_proxy = self.browse(cr, uid, ids, context=context)[0]
        type_id = ids[0]
        model_id = cost_proxy.model_id.id
        if not model_id:
            raise osv.except_osv(
                _('Model error!'),
                _('Set a model name before load cost!'),
                )
        
        # Delete previouse element:
        cost_ids = cost_pool.search(cr, uid, [
            ('type_id', '=', type_id)], context=context)        
        cost_pool.unlink(cr, uid, cost_ids, context=context)    
            
        # Add cost elements from template: 
        for cost in model_pool.browse(
                cr, uid, model_id, context=context).rule_ids:
            # loop on field:
            data = {'type_id': type_id}
            for field in cost._columns.keys():
                field_type = cost._columns[field]._type
                
                # Jump exluded field or excluded type
                if field in self._excluded_fields or \
                        field_type in self._excluded_type:
                    continue    
                    
                if field_type == 'many2one':
                    data[field] = cost.__getattribute__(field).id
                else:       
                    data[field] = cost.__getattribute__(field)
            cost_pool.create(cr, uid, data, context=context)
            
        # Reset model id after create:        
        self.write(cr, uid, ids, {
            'model_id': False}, context=context)        
        
        return True
        
    def get_campaign_price(self, campaign, product_line):
        ''' Master function for calculate price depend on rules:
            cost: cost price for product
            price: sale price for product
            volume_rate: 
            BROWSE OBJ:
            cost_type: all rules for product cost type
            campaign: campaign, used for get extra cost or discount
            product: used to get extra info from product (ex. volume)            
        '''
        # ---------------------------------------------------------------------
        # Initial setup:
        # ---------------------------------------------------------------------
        # Pool used:
        partner_pool = self.pool.get('res.partner')

        cost = product_line.cost
        price = product_line.price
        cost_type_id = product_line.cost_type_id
        data = {
            'warning': '',
            'error': '',
            'calc': '',
            }

        # ---------------------------------------------------------------------
        # Starting check:
        # ---------------------------------------------------------------------
        if not cost_type_id:
            data['calc'] += _('??|Use sale price|%s|=%s\n') % (price, price)
            data['error'] += _('No cost type use sale price\n')
            data['campaign_price'] = price # use sale price
            return data
        
        # ---------------------------------------------------------------------
        # Product cost generation:
        # ---------------------------------------------------------------------
        total = 0.0
        for rule in cost_type_id.rule_ids: # sequence order:
            # Read rule parameters
            base = rule.base
            mode = rule.mode #fixed or perc
            value = rule.value
            category = rule.category
            
            # -----------------------------------------------------------------
            # Base evaluation:
            # -----------------------------------------------------------------
            if base == 'previous':
                base_value = total                
                if not total: # no for first rule!    
                    data['warning'] += _(
                        '#%s. Start total not present!\n') % rule.sequence
            elif base == 'cost':
                if not total: # Init setup depend on first rule
                    total = cost 
                    data['calc'] += _('0|Start value||%s\n') % total
                base_value = cost
            else: # 'price':
                if not total: # Init setup depend on first rule
                    total = price
                    data['calc'] += _('0|Start value||%s\n') % total
                base_value = price

            # -----------------------------------------------------------------
            # Calc depend on category:
            # -----------------------------------------------------------------
            # Mandatory field for operation:
            if not value and category in ('discount', 'recharge'):
                data['error'] += _(
                    '%s| Value not present\n') % rule.sequence # go ahead

            if category == 'transport':     
                if product_line.qty:
                    unit_volume = product_line.volume / product_line.qty
                else:
                    data['warning'] += _(
                        '#%s. Cannot get unit volume!\n') % rule.sequence
                    unit_volume = 0.0    
                v = campaign.transport_unit * unit_volume
                total += v
                data['calc'] += _(
                    '%s|+Transport|%s x %s(m3) = %s|%s\n') % (
                        rule.sequence,
                        campaign.transport_unit, 
                        unit_volume,
                        v,
                        total,
                        )
            elif category == 'packaging':                     
                # cost for pack (forced or product one's)
                pack_cost = rule.value or (
                    product_line.packaging_id.package_extra_cost \
                    if product_line.packaging_id else 0.0)

                total += pack_cost
                data['calc'] += _(
                    '%s|+Re-pack|%s%s|%s\n') % (
                        rule.sequence,
                        pack_cost, 
                        _(' (forced)') if rule.value else '',
                        total,
                        )
            elif category == 'discount':
                if mode == 'fixed':
                    total -= value
                    data['calc'] += _(
                        '%s|-Discount (fixed)|%s|%s\n') % (                        
                            rule.sequence,
                            value,
                            total,
                            )
                else: # 'percentual'
                    v = base_value * value / 100.0
                    total -= v
                    data['calc'] += _(
                        '%s|-Discount (%s)|%s x %s / 100 = %s|%s\n') % (                        
                            rule.sequence,
                            '%',
                            base_value,
                            value,
                            v,
                            total,
                            )
            else: # 'recharge'
                if mode == 'fixed':
                    total += value
                    data['calc'] += _(
                        '%s|+Recharge (fixed)|%s|%s\n') % (                        
                            rule.sequence,
                            value,
                            total,
                            )
                else: # 'percentual'
                    v = base_value * value / 100.0
                    total += v
                    data['calc'] += _(
                        '%s|+Recharge (%s)|%s x %s / 100 = %s|%s\n') % (                        
                            rule.sequence,
                            '%',
                            base_value,
                            value,
                            v,
                            total,
                            )
                    
        data['campaign_price'] = total
        data['calc'] += _('|TOTAL||%s\n') % total
        return data
        
    _columns = {
        'name': fields.char('Cost type', size=64, required=True, 
            help='Cost depend on product category'), 
        'campaign_id': fields.many2one('campaign.campaign', 'Campaign', 
            help='Campaign referente', ondelete='cascade'),
        'model_name': fields.char('Model name', size=40, 
            help='Name used for generate model element'),
        # TODO add filter for product    
        }

class CampaignCostModel(orm.Model):
    """ Model name: Campaign cost model
    """    
    _name = 'campaign.cost.model'
    _description = 'Campaign cost model'
    
    _columns = {
        'name': fields.char('Name', size=40, required=True),
        'note': fields.text('Note'),
        }
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name reference must be unique!'),
        ]    
        
class CampaignCost(orm.Model):
    """ Model name: Campaign cost
    """    
    _name = 'campaign.cost'
    _description = 'Campaign cost'
    _rec_name = 'sequence'
    _order = 'sequence'
    
    _columns = {
        'sequence': fields.integer('Sequence'),
        'model_id': fields.many2one('campaign.cost.model', 'Cost model', 
            help='Cost model, used in inherit type 2 cost', 
            ondelete='cascade'),
        'type_id': fields.many2one('campaign.cost.type', 'Cost type', 
            help='Campaign reference', ondelete='cascade'),
        'category': fields.selection([
            ('discount', 'Discount (-)'), # sign -
            ('recharge', 'Rechange (+)'), # sign +
            ('transport', 'Transport (+)'), # sign +
            ('packaging', 'Re-packaging (+)'), # sign +            
            ], 'Category', required=True),        
        'description': fields.char('Description', size=64),
        'base': fields.selection([
            ('cost', 'Cost'),
            ('price', 'Price'),
            ('previous', 'Previous'),
            ], 'Base', required=True),
        'value': fields.float(
            'Value', digits_compute=dp.get_precision('Product Price')),
        'mode': fields.selection([
            ('fixed', 'Fixed'),
            ('percentual', 'Percentual'),
            ], 'Cost mode', required=True),
        'note': fields.char('Note', size=80),
        }
        
    _defaults = {
        # Default value:
        'base': lambda *x: 'previous',
        'mode': lambda *x: 'percentual',
        }

class CampaignCostModelItem(orm.Model):
    """ Model name: Campaign cost model item
    """    
    _inherit = 'campaign.cost'
    _name = 'campaign.cost.model.item'

    # Duplicate object for save model elements    

class CampaignCostModel(orm.Model):
    """ Model name: Campaign cost model
    """    
    _inherit = 'campaign.cost.model'
    
    _columns = {
        'rule_ids': fields.one2many(
            'campaign.cost.model.item', 'model_id', 
            'Cost rule'), 
        }

class CampaignCostType(orm.Model):
    """ Model name: Campaign cost type
    """    
    _inherit = 'campaign.cost.type'

    _columns = {
        'rule_ids': fields.one2many('campaign.cost', 'type_id', 'Cost rule', 
            ondelete='cascade'),
        'model_id': fields.many2one(
            'campaign.cost.model', 'Model model'),
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
    def open_status_stock_product(self, cr, uid, ids, context=None):
        ''' Open status for product
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        
        # Search product ID
        campaign_proxy = self.browse(cr, uid, ids, context=context)[0]
        product_id = campaign_proxy.product_id.id
        
        # Return view
        model_pool = self.pool.get('ir.model.data')
        form_view_id = model_pool.get_object_reference(cr, uid, 
            'inventory_status', 'view_product_inventory_lite_form')[1]
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': product_id,
            'res_model': 'product.product',
            'view_id': form_view_id, # False
            'views': [(form_view_id, 'form')],
            #'domain': [],
            'context': context,
            'target': 'new',
            'nodestroy': False,
            }
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
    
    def correct_pack_error(self, cr, uid, ids, context=None):
        ''' 
        '''
        #TODO evaluate to create function for correct value
        
        return True
        
    # ----------------
    # Fields function:
    # ----------------
    def _get_packaging_status_element(self, cr, uid, ids, fields, args, 
            context=None):
        ''' Q. x pack are standard value in no packagin selected
        '''    
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = {}
            
            if item.packaging_id: # force pack for campaign:
                pack = item.packaging_id # readability
                q_x_pack = pack.qty or 1 # TODO raise error?                
                volume = (pack.pack_l * pack.pack_h * pack.pack_p)
                # or pack.pack_volume or 0.0
            else: # use default packaging (product one's)
                product = item.product_id # readability:
                if product.has_multipackage:
                    q_x_pack = 1
                    volume = 0.0
                    for mp in product.multi_pack_ids:
                        volume += mp.number * mp.height * mp.width * mp.length
                else: # default pack   
                    q_x_pack = product.q_x_pack or 1 # TODO raise error?
                    volume = (product.pack_l * product.pack_h * product.pack_p)
                    # or product.volume

            res[item.id]['q_x_pack'] = q_x_pack                     
            res[item.id]['pack_error'] = item.qty % q_x_pack != 0                
            res[item.id]['volume'] = (item.qty / q_x_pack) * volume / 1000000.0    
        return res        
    
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
        # Used for history elements during importation of confirmed qty:
        'qty_offered': fields.float(
            'Q.', digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Quantity offered depend on stock and company availability'
            ),
        'qty': fields.float(
            'Q.', 
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Quantity confirmed from customer',
            ),     
        'qty_ordered': fields.float(
            'Q. ordered', 
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Quantity ordered at the end of campaign'
            ),     
        'uom_id': fields.many2one( # TODO used?
            'product.uom', 'UOM', ondelete='set null'),
        
        'q_x_pack': fields.function(
            _get_packaging_status_element, method=True, 
            type='float', string='Q. x pack', store=False, multi=True), 
        'pack_error': fields.function(
            _get_packaging_status_element, method=True, 
            type='boolean', string='Pack error', store=False, multi=True,
            help='Choosen total not fit in packaging choosen'), 
        'volume': fields.function(
            _get_packaging_status_element, method=True, 
            type='float', string='Vol.', store=False, multi=True), 

        'cost_type_id': fields.many2one('campaign.cost.type', 'Cost type',
            help='Cost type reference', ondelete='set null'),

        'product_tmpl_id': fields.related(
            'product_id', 'product_tmpl_id', type='many2one', 
            relation='product.template', string='Template', 
            store=False), 
        'packaging_id': fields.many2one('product.packaging', 'Pack',
            help='Use different pack for product', ondelete='set null'),
        
        # Calc esit:
        'error': fields.text('Error', readonly=True),
        'warning': fields.text('Warning', readonly=True),
        'calc': fields.text('Calc', readonly=True),

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
        'child_ids': fields.one2many(
            'campaign.campaign', 'parent_id', 'Child'),    
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

class ProductPackaging(orm.Model):
    """ Stock product.packaging
    """    
    _inherit = 'product.packaging'

    def name_get(self, cr, uid, ids, context=None):
        """ Remove extra codebar in foreign key name
        """        
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]            
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            res.append((
                record.id, record.ul.name))
        return res
    
# TODO manage product in campaign as stock.move??
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
