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

class ProductProductImportationTraceColumn(orm.Model):
    ''' Importation log element trace of fields
    ''' 
    _inherit = 'product.product.importation.trace.column'


    # Override function:
    def _get_field_list(self, cr, uid, context=None):
        res = super(
            ProductProductImportationTraceColumn, self)._get_field_list(
                cr, uid, context=context)
        res.extend([
            # TODO managed boolean!
            #('campaign_cover', 'Campaign: Removeable cover'),
            #('campaign_mounted', 'Campaign: Mounted'),            
            ('campaign_diameter', 'Campaign: Diameter'),            
            ('campaign_name', 'Campaign: Name'),            
            ('campaign_material', 'Campaign: Material'),            
            ('campaign_color', 'Campaign: Color'),            
            ('campaign_wash', 'Campaign: Wash info'),            
            ('campaign_comment', 'Campaign: Comment'),            
            ])
        return res           
        
    _columns = {
        'field': fields.selection(_get_field_list, 'Field linked'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
