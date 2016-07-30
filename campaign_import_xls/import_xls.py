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
    _name = 'campaign.campaign'

    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def action_import_xls(self, cr, uid, ids, context=None):
        ''' Import quantity from campaign report:
            1. Confirmed quantity
            2. Order quantity
            
            Generate log for importation status (and error management)
        '''
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
        import pdb; pdb.set_trace()
        hidden_line = False
        # Search header line (for start import:        
        for line in range(0, max_check):
            row = ws.row(line)
            if row[0] == 'id': # header line found!
                hidden_line = True
                
                # Read columns position:
                qty = -1
                qty_ordered = -1       
                tot_param = 2 # max number or data to read
                for column in range(1, max_param):
                    if row[column] == 'qty':
                        qty = column
                        tot_param -= 1
                    if row[column] == 'qty_ordered':
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
        while not end_import:
            line += 1 # next before header (the first time)            
            try:
                row = ws.row(line)
            except: # Out of range error ends import:
                _logger.warning(_('Import end at line: %s\n') % line)
                break
                
            #  Prepare new record:
            product_data = {}
            try:
                item_id = row[0].value # ID columns is 0
                qty = row[qty].value
                qty_ordered = row[qty].value                
                
                # Float value:
                #if type(f) not in (float, int) :
                #    f = float(f.replace(',', '.'))
            except: 
                _logger.error('Error read line: %s' % line)
                continue                        
                    
        _logger.info('End import XLS product file: %s' % fullname)
        return True
        
    _columns = {
        'filename': fields.char('File name', size=80),
        }        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
