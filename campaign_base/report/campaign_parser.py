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
    
    _name = 'campaign.campaign'
    
    def export_report_as_xlsx(self, cr, uid, ids, context=None):
        ''' Export report in XLSX file
        '''
        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        path = '/home/administrator/photo/xls/campaign'
        campaign_proxy = self.browse(cr, uid, ids, context=context)
        fullname = '%s.xlsx' % campaign_proxy.code
        
        # ---------------------------------------------------------------------
        # Create and open Workbook:
        # ---------------------------------------------------------------------
        WB = xlsxwriter.Workbook(fullname)
        WS = WB.add_worksheet(campaign_proxy.code)
        
        # ---------------------------------------------------------------------
        # Format elements:
        # ---------------------------------------------------------------------
        bold = workbook.add_format({'bold': True})
        
        # ---------------------------------------------------------------------
        # Export
        # ---------------------------------------------------------------------
        # Init setup:
        get_total_pack_block(objects, data)
        # Header:
        
        # Body:
        
        
        WB.close()
        return True
    
    # -------------------------------------------------------------------------    
    # Report functions:    
    # -------------------------------------------------------------------------    
    def get_total_pack_block(self, objects, data=None):
        ''' Read all package objects for decide how much colums
        '''
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {}
        
        if data is not None:
            objects = self._get_active_objects(data)
            
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

    def get_product_pack(self, relations, data=None):
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
            _('Codice prodotto'),
            _('Nome prodotto'),
            _('Quantità riservata'),
            _('Prezzo listino (IVA inclusa)'),
            _('Prezzo acquisto (IVA esclusa)'),
            _('Altezza seduta'),
            _('Commenti Aggiuntivi'),
            _('Peso Prodotto'),
            _('Arriva Montato'),
            _('Unità Imballo'),
            _('Ean'),
            ]
        if from_wizard:
            header_data.append(_('Disponibilità'))
            
        for i in range(0, self.pack_max):
            header_data.extend([    
                _('Lunghezza # %s') % (i + 1), 
                _('Altezza # %s') % (i + 1), 
                _('Profondità # %s') % (i + 1), 
                _('Peso # %s') % (i + 1), 
                ])
        res.append(('HEADER', header_data))

        # ---------------------------------------------------------------------
        #                               Hidden block:
        # ---------------------------------------------------------------------
        # Static data list:
        hidden_data = [
            'id', 'default_code', '', '', '', '', '', '', '', '', '']#, '']
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
            # ------------
            # Common part:
            # ------------
            data = [
                # Product:
                product.default_code,

                # Relation:
                relation.description,
                int(relation.qty),
                relation.price,
                relation.campaign_price,                        

                product.seat_height,
                product.campaign_comment,
                product.weight,
                _('Sì') if product.campaign_mounted else _('No'),
                int(relation.q_x_pack),
                # Product:
                product.ean13 or '',
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

    def _get_active_objects(self, data=None):
        ''' Return active campaign
        '''
        cr = self.cr
        uid = self.uid
        context = {}

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
        
    def get_objects(self, objects, data=None):
        ''' If wizard call return list of all campaign 
            else current objects
        '''
        if data is None:
            return objects
            
        return self._get_active_objects(data)    
        
    
    def load_context_image(self, album_id, product_id):
        ''' Load image from album
        '''
        cr = self.cr
        uid = self.uid
        context = {'album_id': album_id}
        
        product_pool = self.pool.get('product.product')
        product_proxy = product_pool.browse(self.cr, self.uid, product_id, 
            context={'album_id': album_id})                 
        return product_proxy.product_image_context
   
    def get_total_pack_block(self, objects, data=None):
        ''' Read all package objects for decide how much colums
        '''
        return self.pool.get('campaign.campaign').get_total_pack_block(
            objects, data=data)

    def get_product_pack(self, relations, data=None):
        ''' Create a list for all package in product
            [(l, h, p, w)] 
            fill extra element till pack_max
        '''
        return self.pool.get('campaign.campaign').get_product_pack(
            relations, data=data)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
