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

class ProductTemplateExtra(orm.Model):
    """ Model name: ProductTemplateExtra
    """    
    _name = 'product.template.extra'
    _description = 'Product extra info'
    
    _columns = {
        'name': fields.char('Description', size=90, required=True, 
            translate=True),
        'note': fields.text('Note'),
        }
    
class ProductTemplate(orm.Model):
    """ Model name: ProductTemplate
    """    
    _inherit = 'product.template'
    
    _columns = {
        'campaign_cover': fields.boolean('Removeable cover'),
        'campaign_diameter': fields.float('Diameter', digits=(16, 2)),         
        'campaign_mounted': fields.boolean('Mounted'),

        'campaign_name': fields.char('Name for campaign', size=64, 
            translate=True),

        'campaign_material': fields.text('Material', translate=True),
        'campaign_color': fields.text('Color', translate=True),
        'campaign_wash': fields.text('Wash info', translate=True),
        'campaign_comment': fields.text(
            'Comment', help='Comment on dimension, product, set and measure',
            translate=True),

        'extra_ids': fields.many2many(
            'product.template.extra', 'product_template_extra_info_rel', 
            'product_id', 'extra_id', 'Extra info'), 
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
