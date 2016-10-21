#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (C) 2010-2012 Associazione OpenERP Italia
#   (<http://www.openerp-italia.org>).
#   Copyright(c)2008-2010 SIA "KN dati".(http://kndati.lv) All Rights Reserved.
#                   General contacts <info@kndati.lv>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys
import logging
import openerp
import xlsxwriter # XLSX export
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
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
    """ Model name: CampaignCampaign
    """    
    _inherit = 'campaign.campaign'
    
    # -------------------------------------------------------------------------
    # Button event:
    # -------------------------------------------------------------------------
    def export_report_as_xlsx(self, cr, uid, ids, context=None):
        ''' Export report in XLSX file
        '''
        def get_image(path, code, extension):
            ''' Generate image name
            '''
            name = '%s.%s' % (
                os.path.join(path, line[0]),
                extension,
                )
            # Test if file exists:
            if os.path.isfile(name):
                return name
            else:
                return False     
           
        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        path = '/home/administrator/photo/xls/campaign'
        objects = self.browse(cr, uid, ids, context=context)
        filename = 'export.xlsx' #'%s.xlsx' % campaign_proxy.code
        fullname = os.path.join(path, filename)
        data = {} # Not from wizard
        
        # ---------------------------------------------------------------------
        # Create and open Workbook:
        # ---------------------------------------------------------------------
        WB = xlsxwriter.Workbook(fullname)
        WS = WB.add_worksheet()#campaign_proxy.code)
        
        # ---------------------------------------------------------------------
        # Format elements:
        # ---------------------------------------------------------------------
        format_header = WB.add_format({
            'bold': True, 
            'font_name': 'Arial',
            'font_size': 11,
            })

        format_title = WB.add_format({
            'bold': True, 
            'font_color': 'black',
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'center',
            'bg_color': 'gray',
            'border': 1,
            })

        format_hidden = WB.add_format({
            'font_color': 'white',
            'font_name': 'Arial',
            'font_size': 8,
            })

        format_data = WB.add_format({
            'font_name': 'Arial',
            'font_size': 10,
            })
        
        # ---------------------------------------------------------------------
        # Export
        # ---------------------------------------------------------------------
        # Init setup:
        self.get_total_pack_block(cr, uid, objects, context=context) # no data
        
        # Column dimension:        
        WS.set_column ('A:A', 0, None, {'hidden': 1}) # ID column        
        WS.set_column ('B:B', 30) # Image colums
        
        # set language:

        row = 1
        context_lang = context.get('lang', 'it_IT')
        for o in objects: # NOTE: only one from button
            context['lang'] = o.partner_id.lang or 'it_IT'
            
            path = os.path.expanduser(o.thumb_album_id.path)            
            extension = o.thumb_album_id.extension_image
            
            # -----------------------------------------------------------------
            # Header:
            # -----------------------------------------------------------------            
            WS.write(row, 1, _('CAMPAIGN'), format_header)
            WS.write(row, 2, o.name, format_header)
            WS.write(row, 4, _('Customer:'), format_header)
            WS.write(row, 5, o.partner_id.name, format_header)            
            row += 1
            
            # -----------------------------------------------------------------
            # Body:
            # -----------------------------------------------------------------
            for mode, line in self.get_product_pack(
                    cr, uid, o.product_ids, data, context=context):
                row += 1
                # -------------------------------------------------------------
                # Body mode:    
                # -------------------------------------------------------------
                # Title:
                WS.set_row(row, 30)
                if mode == 'HEADER':
                    WS.write(row, 1, _('Imagine'), format_title)
                    col = 1
                    for field in line:
                        col += 1
                        WS.set_column (col, col, 20) # Col large
                        WS.write(row, col, field, format_title)
                        
                    # Add 2 extra col:                   
                    WS.write(row, col + 1, _('Campaign'), format_title)
                    WS.write(row, col + 2, _('Order'), format_title)
                    
                # Hidden:               
                elif mode == 'HIDDEN':
                    WS.set_row(row, 0)
                    WS.write(row, 0, 'id', format_hidden)
                    col = 2 + len(line)
                    WS.write(row, col, 'qty', format_hidden)
                    WS.write(row, col + 1, 'qty_ordered', format_hidden)
                    
                # Body:
                else: # Product line
                    WS.set_row(row, 50)
                    WS.write(row, 0, mode, format_hidden) 
                    image = get_image(path, line[0], extension)
                    if image:
                        WS.insert_image(row, 1, image, {
                            'x_scale': 1, 'y_scale': 1, 
                            'x_offset': 2, 'y_offset': 2,                            
                            })
                    else:
                        WS.write(row, 1, 'No image', format_data)        
                    col = 1
                    for field in line:
                        col += 1
                        WS.write(row, col, field, format_data)        
        WB.close()
        context['lang'] = context_lang # previous lang
        return True
    
    # -------------------------------------------------------------------------    
    # Report functions:    
    # -------------------------------------------------------------------------    
    def _get_active_objects(self, cr, uid, data=None, context=None):
        ''' Return active campaign
        '''
        if data is None:
            data = {} # TODO manage filter confirmed draft 
            
        campaign_pool = self.pool.get('campaign.campaign')

        if data.get('mode', False) == 'draft':
            domain = [('state', 'in', ('draft', 'confirmed'))]
        else: # only confirmed
            domain = [('state', '=', 'confirmed')]
            
        campaign_ids = campaign_pool.search(cr, uid, domain, context=context)
        if not campaign_ids:
            raise osv.except_osv(
                _('Report error!'), 
                _('No data, change filter'),
                )
            
        return campaign_pool.browse(cr, uid, campaign_ids, context=context)    

    def get_total_pack_block(self, cr, uid, objects, data=None, context=None):
        ''' Read all package objects for decide how much colums
        '''
        if data is not None:
            objects = self._get_active_objects(
                cr, uid, data=data, context=context)
            
        self.pack_max = 1
        for campaign in objects:
            for line in campaign.product_ids:
                product = line.product_id
                if product.has_multipackage:
                    tot = sum([item.number for item in product.multi_pack_ids])
                else:
                    tot = 1    
                if tot > self.pack_max:
                    self.pack_max = tot                    
        return ''       

    def get_product_pack(self, cr, uid, relations, data=None, context=None):
        ''' Create a list for all package in product
            [(l, h, p, w)] 
            fill extra element till pack_max
        '''
        if data is None:
            data = {}        
            from_wizard = False
        else:    
            from_wizard = True

        res = []
        empty = ['', '', '', ''] # XXX loop block if empty
        
        # ---------------------------------------------------------------------
        #                               Header block:
        # ---------------------------------------------------------------------
        header_data = [
            _('Product code'),
            _('Product name'),
            _('Reserved quantity'),
            _('Pricelist\n(VAT included)'),
            _('Transfer price\n(VAT excluded)'),
            _('Seat height'),
            _('Extra comment'),
            _('Height'),
            _('Width'),
            _('Length'),            
            _('Product weight'),
            _('Mounted'),
            _('Package unit'),
            _('EAN'),
            _('Material\n(structure, coatings, padding, plans etc.)'),
            _('Color/s\n(write all color present)'),
            _('Wash informations'),
            _('Removable cover'),
            _('Extra info'),
            ]
        if from_wizard:
            header_data.append(_('Availability'))
            
        for i in range(0, self.pack_max):
            header_data.extend([    
                _('Length # %s') % (i + 1), 
                _('Height # %s') % (i + 1), 
                _('Depth # %s') % (i + 1), 
                _('Weight # %s') % (i + 1), 
                ])
        res.append(('HEADER', header_data))

        # ---------------------------------------------------------------------
        #                               Hidden block:
        # ---------------------------------------------------------------------
        # Static data list:
        hidden_data = [
            'id', 'default_code', '', '', '', '', '', '', '', '', '', '']
        if from_wizard:
            hidden_data.append('')

        # Dynamic part:
        for i in range(0, self.pack_max):
            hidden_data.extend(empty)

        res.append(('HIDDEN', hidden_data))

        # ---------------------------------------------------------------------
        #                            Data block:
        # ---------------------------------------------------------------------
        for relation in relations:
            product = relation.product_id # readability

            # Ean part:
            ean = product.ean13 or '' # normal
            if relation.packaging_id:
                if relation.packaging_id.ean:
                    ean = relation.packaging_id.ean # normal different pack
                else:
                    if ean: # warning:
                        ean = '%s (prod.)' % ean

            # ------------
            # Common part:
            # ------------
            data = [
                # Product:
                product.default_code,

                # Relation:
                '%s %s' % (
                    relation.description or product.name or '?', 
                    product.colour or ''),
                int(relation.qty),
                #relation.price,
                relation.price * 1.22, # TODO parametrize
                relation.campaign_price,
                product.seat_height,
                product.campaign_comment,
                product.height,
                product.width,
                product.length,
                product.weight,
                _('Yes') if product.campaign_mounted else _('No'),
                int(relation.q_x_pack),
                # Product:
                ean,
                product.campaign_material or '',
                product.campaign_color or '',
                product.campaign_wash or '',
                _('Yes') if product.campaign_cover else _('No'),
                [item.name for item in product.extra_ids],
                
                #0.0, #TODO what data?!?!? int(product.qty),
                ]

            if from_wizard:
                data.append(int(product.mx_lord_qty or 0.0))

            if product.has_multipackage:
                # -------------------------------------------------------------
                #                   Multipackage product:
                # -------------------------------------------------------------
                i = 0                    

                for pack in product.multi_pack_ids: # Loop on all elements
                    i += pack.number or 1
                    for item in range(0, pack.number or 1):
                        data.extend([ # pack
                            pack.height,
                            pack.width, 
                            pack.length,
                            pack.weight,                            
                            ])  

            elif relation.packaging_id: # extra pack setted
                # -------------------------------------------------------------
                #                  Extra package selected:
                # -------------------------------------------------------------
                i = 1 # only one
                
                data.extend([ # extra pack selected
                    relation.packaging_id.pack_h,
                    relation.packaging_id.pack_l, 
                    relation.packaging_id.pack_p, 
                    relation.packaging_id.weight,                            
                    ])                  
            else:
                i = 1 # only one
                # -------------------------------------------------------------
                #                    Default package:
                # -------------------------------------------------------------
                data.extend([ # extra pack selected
                    product.pack_h,
                    product.pack_l, 
                    product.pack_p, 
                    product.weight,                            
                    ])   
                       
            # -----------------------
            # Add empty extra fields:               
            # -----------------------
            for item in range(0, self.pack_max - i):
                data.extend(empty)
                       
            res.append((relation.id, data))            
        return res            
    
class Parser(report_sxw.rml_parse):
    counters = {}
    context = False
    
    def __init__(self, cr, uid, name, context):
        self.context = context
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
            'load_context_image': self.load_context_image,
            'get_total_pack_block': self.get_total_pack_block,
            'get_product_pack': self.get_product_pack,
        })

    def get_objects(self, objects, data=None):
        ''' Return active campaign
        '''
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {}
        
        return self.pool.get('campaign.campaign')._get_active_objects(
            cr, uid, data=data, context=context)
        
    def load_context_image(self, album_id, product_id):
        ''' Load image from album (used in ODT document, not in ODS)      
        '''
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {'album_id': album_id}
        
        product_pool = self.pool.get('product.product')
        product_proxy = product_pool.browse(cr, uid, product_id, 
            context={'album_id': album_id})                 
        return product_proxy.product_image_context
   
    def get_total_pack_block(self, objects, data=None):
        ''' Read all package objects for decide how much colums
        '''
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {}
        
        return self.pool.get('campaign.campaign').get_total_pack_block(
            cr, uid, objects, data=data, context=context)

    def get_product_pack(self, relations, data=None):
        ''' Create a list for all package in product
            [(l, h, p, w)] 
            fill extra element till pack_max
        '''
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {}

        return self.pool.get('campaign.campaign').get_product_pack(
            cr, uid, relations, data=data, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
