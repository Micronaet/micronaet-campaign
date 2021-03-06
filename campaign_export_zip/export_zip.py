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
#import xlrd
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
    def action_export_zip(self, cr, uid, ids, context=None):
        ''' Export ZIP file for all HQ Album in campaign folder
        '''
        # Parameters:
        filepath = '/home/administrator/photo/xls/campaign' # TODO parametrize
        
        image_pool = self.pool.get('product.image.file')
        campaign_proxy = self.browse(cr, uid, ids, context=context)[0]
        album = campaign_proxy.album_id # readability
        
        # Command for zip:
        zip_fullname = os.path.join(
            filepath, campaign_proxy.code.replace('/', '_'))            
        command = 'zip -j \'%s.zip\' \'%s\' '

        # Log operation:
        log_image = '' 

        # ---------------------------------------------------------------------
        # Product in campaing
        # ---------------------------------------------------------------------
        product_ids = [
            item.product_id.id for item in campaign_proxy.product_ids]

        domain = [
            ('album_id', '=', album.id),
            ('product_id', 'in', product_ids),
            ]
        if not campaign_proxy.with_detail:
            log_image += 'ZIP file with variants\n'
            domain.append(('variant', '=', False)) # no variant
            
        image_ids = image_pool.search(cr, uid, domain, context=context)
        log_image += 'Product selected: %s   >>  Found %s images\n' % (
            len(product_ids),
            len(image_ids),
            )

        path = os.path.expanduser(album.path)
        extension = album.extension_image
        log_image += 'Path: %s [Ext.: %s]\n' % (path, extension)
        
        # List for management:
        image_list = []
        selected_ids = []
        for image in image_pool.browse(cr, uid, image_ids, context=context):
            log_image += '%s\n' % image.filename
            image_list.append(os.path.join(path, image.filename))
            
            # Populate image selected:
            product_id = image.product_id.id
            if product_id not in selected_ids:
                selected_ids.append(product_id)

        if not image_list:            
            raise osv.except_osv(
                _('Export file: %s') % zip_fullname, 
                _('Image list not present!'),
                )           

        if len(product_ids) != len(selected_ids):
            log_image += 'Difference from image and selection!\n'
        
        command = command % (
            zip_fullname,
            '\' \''.join(image_list),
            )
            
        os.system('rm %s.zip' % zip_fullname)    
        os.system(command)
        
        # TODO update log data on campaign.campaign            
        log_image += 'Export ZIP image file: %s.zip\n' % zip_fullname
        
        return self.write(cr, uid, ids, {
            'zip_export_confirm': log_image,
            }, context=context)
        
        # ---------------------------------------------------------------------
        # Generate list of image Album HQ:
        # ---------------------------------------------------------------------
        #album = campaign_proxy.album_id
        #path = os.path.expanduser(album.path)
        #extension = album.extension_image        
        #album_image_list = [
        #    item.product_id.id for item in album.image_ids 
        #        if item.product_id.id]
        #image_list = []        
        #for item in campaign_proxy.product_ids:
        #    product = item.product_id
        #    if product.id in album_image_list:
        #        if not product.default_code:
        #            _logger.warning('No default code: %s' % \
        #                product.name)
        #            continue     
        #        image_list.append(
        #            os.path.join(
        #                path,
        #                '%s.%s' % (
        #                    product.default_code,
        #                    extension,
        #                    )))
        #    else:    
        #        _logger.warning('No image in album: %s' % \
        #            product.name)
        
    _columns = {
        'zip_export_confirm': fields.text('Export ZIP log', readonly=True),
        }        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
