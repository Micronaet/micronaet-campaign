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
import xlrd
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

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """

    _inherit = 'sale.order'
    
    # -------------------------------------------------------------------------
    #                                Utility:
    # -------------------------------------------------------------------------
    def import_campaign_like_order_from_xls(self, cr, uid, ids, context=None):
        ''' Campaign like order
        '''        
        assert len(ids) == 1, 'Only one order a time!'

        if context is None:
            context = {}

        # Pool used:        
        product_pool = self.pool.get('product.product')
        line_pool = self.pool.get('sale.order.line')
        order_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        # Parameters:
        filepath = '/home/administrator/photo/xls/campaign' # TODO parametrize
        max_check = 1000 # max number of line used for check start elements
        max_param = 1000 # max number of column used for check hidden parameter
        filename = 'campaign.xls'
        fullname = os.path.join(filepath, filename)
        
        _logger.info('Start import from path: %s' % fullname)

        # ---------------------------------------------------------------------
        #                Open XLS document (first WorkSheet):
        # ---------------------------------------------------------------------
        try:
            # from xlrd.sheet import ctype_text
            wb = xlrd.open_workbook(fullname)
            ws = wb.sheet_by_index(0)
        except:
            raise osv.except_osv(
                _('Import file: %s') % fullname, 
                _('Error opening XLS file: %s' % (sys.exc_info(), )),
                )

        i = 0
        for line in range(0, max_check):
            i += 1
            try:
                row = ws.row(line)
            except:
                break # end of file    
            
            # XXX different columns (now change in code)
            name = row[2].value
            default_code = row[2].value
            product_uom_qty = row[9].value
            price_unit = row[10].value
             
            if not default_code:
                _logger.error('%s. No default code, jumped' % i)
                continue                
                
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code),
                ], context=context)

            if product_ids:
                product_id = product_ids[0]
            else:
                # Create simple product
                _logger.error('%s. Product not found %s, created!' % (
                    i, default_code))
                product_id = product_pool.create(cr, uid, {
                    'name': '%s %s' % (name, default_code),
                    'default_code': default_code,
                    }, context=context)
                    
            product_proxy = product_pool.browse(
                cr, uid, product_id, context=context)        

            # -----------------------------------------------------------------
            # Create sale order line:
            # -----------------------------------------------------------------
            # Raise onchange:
            line_data = line_pool.product_id_change_with_wh(
                cr, uid, False, 
                order_proxy.pricelist_id.id, 
                product_proxy.id, 
                product_uom_qty,
                uom=product_proxy.uom_id.id, # TODO change 
                qty_uos=0, 
                uos=False, 
                name=product_proxy.name, 
                partner_id=order_proxy.partner_id.id,
                lang=order_proxy.partner_id.lang, 
                update_tax=True, 
                date_order=order_proxy.date_order, 
                packaging=False, 
                fiscal_position=order_proxy.fiscal_position.id, 
                flag=False, 
                warehouse_id=order_proxy.warehouse_id.id,
                context=context,
                ).get('value', {})
                
            # Complete data:                    
            line_data.update({
                'order_id': order_proxy.id,
                'product_id': product_proxy.id,
                'product_uom_qty': product_uom_qty,
                'product_uom': product_proxy.uom_id.id, # no uom_id
                'price_unit': price_unit,
                'date_deadline': order_proxy.date_deadline,
                # TODO measure data?!?
                })

            # Tax ID correction:
            if 'tax_id' in line_data:
                line_data['tax_id'] = [(6, 0, line_data['tax_id'])]      
            line_pool.create(cr, uid, line_data, context=context) 
        
        # TODO update log data on campaign.campaign            
        _logger.info('End import XLS product file: %s' % fullname)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
