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
    """ Model name: Campaign campaign
    """    
    _inherit = 'campaign.campaign'

    # Override association procedure:
    def assign_type_price_to_product(self, cr, uid, campaign, context=None):
        ''' Procedure for force assign price to product selected
        '''
        # Pool used:
        product_pool = self.pool.get('campaign.product')
        
        # Create gamma database        
        gamma = {}        
        for rule in campaign.cost_ids:
            gamma[rule.status] = rule.id
        
        for product in campaign.product_ids:
            product_pool.write(cr, uid, product.id, {
                'cost_type_id': gamma.get(product.status, False),
                }, context=context)
        return True

class CampaignCostType(orm.Model):
    """ Model name: Campaign cost type
    """    
    _inherit = 'campaign.cost.type'


    def _get_selection_list(self, cr, uid, context=None):
        ''' Get list from product
        '''
        return self.pool.get('product.template')._columns['status'].selection
        
    _columns = {
        # TODO read selection list from product.product (for future change)
        'status': fields.selection(_get_selection_list, 'Gamma'),
        }

class CampaignProduct(orm.Model):
    """ Model name: Campaign product
    """    
    _inherit = 'campaign.product'

    def _get_selection_list(self, cr, uid, context=None):
        ''' Get list from product
        '''
        return self.pool.get('product.template')._columns['status'].selection

    _columns = {
        'status': fields.related(
            'product_id', 'status', type='selection', 
            selection=_get_selection_list, string='Status'), 
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
