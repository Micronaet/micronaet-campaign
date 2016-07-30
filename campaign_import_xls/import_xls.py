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

class CampaignCampaign(orm.Model):
    ''' Add import method
    '''    
    _inherit = 'campaign.campaign'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def xls_import_confirmed_qty(self, cr, uid, ids, context=None):
        ''' Import confirmed qty
        '''
        # TODO reset data before?
        if context == None:
            context = {}
        context['import_field'] = 'qty'
            
        return self.action_import_xls(cr, uid, ids, context=context)

    def xls_import_ordered_qty(self, cr, uid, ids, context=None):
        ''' Import ordered qty
        '''
        # TODO reset data before?
        if context is None:
            context = {}
        context['import_field'] = 'qty_ordered'
            
        return self.action_import_xls(cr, uid, ids, context=context)
        
    def action_import_xls(self, cr, uid, ids, context=None):
        ''' Import quantity from campaign report:
            1. Confirmed quantity
            2. Order quantity
            
            Generate log for importation status (and error management)
        '''
        if context is None:
            context = {}
        
        import_field = context.get('import_field', False)    
        if not import_field:
            raise osv.except_osv(
                _('Import error!'), 
                _('Input field not present (ordered or confirmed?)'),
                )
        
        # Parameters:
        filepath = '/home/administrator/photo/xls/campaign' # TODO parametrize
        max_check = 1000 # max number of line used for check start elements
        max_param = 1000 # max number of column used for check hidden parameter        
        
        # Pool used:
        product_pool = self.pool.get('campaign.product')
        
        campaign_proxy = self.browse(cr, uid, ids, context=context)[0]
        filename = campaign_proxy.filename
        if not filename:
            raise osv.except_osv(
                _('Import error!'), 
                _('Set file name for import'),
                )
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

        # ---------------------------------------------------------------------        
        # Identify hidden columns with parameters:
        # ---------------------------------------------------------------------        
        hidden_line = False
        # Search header line (for start import:        
        for line in range(0, max_check):
            row = ws.row(line)
            if row[0].value == 'id': # header line found!
                hidden_line = True
                
                # Read columns position:
                qty = -1
                qty_ordered = -1       
                tot_param = 2 # max number or data to read
                for column in range(1, max_param):
                    cell = row[column].value
                    if cell == 'qty':
                        qty = column
                        tot_param -= 1
                    if cell == 'qty_ordered':
                        qty_ordered = column
                        tot_param -= 1
                    if not tot_param:
                        break # end loop                                                 
                break # hidden line found!
                
        # ---------------------------------------------------------------------        
        # Check file validity:
        # ---------------------------------------------------------------------        
        # Hidden block:                
        if not hidden_line:
            raise osv.except_osv(
                _('Import file: %s') % fullname, 
                _('XLS file not coerent, no ID for check header colums'),
                )            

        # Qty columns:
        if qty < 0 or qty_ordered < 0:
            raise osv.except_osv(
                _('Import file: %s') % fullname, 
                _('No qty or qty_ordered columns found on XLS file!'),
                )            
        
        # ---------------------------------------------------------------------        
        # Read data:
        # ---------------------------------------------------------------------        
        end_import = False
        import pdb; pdb.set_trace()
        while not end_import:
            line += 1 # next before header (the first time)            
            try:
                row = ws.row(line)
            except: # Out of range error ends import:
                _logger.warning(_('Import end at line: %s\n') % line)
                break
                
            #  Prepare new record:
            data = {}
            try:
                item_id = int(row[0].value) # ID columns is 0
                if import_field == 'qty':
                    qty_value = int(row[qty].value or '0')
                    if qty_value:
                        data['qty'] = qty_value
                    
                else: # qty_ordered
                    qty_ordered_value = int(row[qty_ordered].value or '0')
                    if qty_ordered_value:
                        data['qty_ordered'] = qty_ordered_value
            except: 
                _logger.error('Error read line: %s' % line)
                continue                        
            
            if not data: # no data in cell or no integer
                _logger.error('No data to write line: %s' % line)
                continue
                                
            # --------------------------------
            # Update data in campaign.product:
            # --------------------------------
            # Check presence:
            try:
                product_proxy = product_pool.browse(
                    cr, uid, item_id, context=context)
            except:
                _logger.error('No ID %s in campaign.product' % item_id)
                continue # XXX log better
                
            # Updata data:
            data['qty_offered'] = product_proxy.qty # old                
            product_pool.write(cr, uid, item_id, data, context=context) 
        
        # TODO update log data on campaign.campaign            
        _logger.info('End import XLS product file: %s' % fullname)
        return True
        
    _columns = {
        'filename': fields.char('File name', size=80),
        'xls_import_confirm': fields.text('Log import confirm', readonly=True),
        'xls_import_order': fields.text('Log import order', readonly=True),
        }        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
