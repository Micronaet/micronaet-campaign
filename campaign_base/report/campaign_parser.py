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

class Parser(report_sxw.rml_parse):
    counters = {}
    context = False
    
    def __init__(self, cr, uid, name, context):
        self.context = context
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'load_context_image': self.load_context_image,
            'get_total_pack_block': self.get_total_pack_block,
            'get_product_pack': self.get_product_pack,
        })
    
    def load_context_image(self, album_id, product_id):
        ''' Load image from album
        '''
        product_pool = self.pool.get('product.product')
        product_proxy = product_pool.browse(self.cr, self.uid, product_id, 
            context={'album_id': album_id})            
        return product_proxy.product_image_context
   
    def get_total_pack_block(self, objects):
        ''' Read all package objects for decide how much colums
        '''
        # Readability:
        cr = self.cr
        uid = self.uid
        context = {}
        
        self.pack_max = 1
        for campaign in objects:
            for line in campaign.product_ids:
                product = line.product_id
                if product.has_multipackage:
                    tot = sum([item.number for item in product.multi_pack_ids])
                if tot > self.pack_max:
                    self.pack_max = tot    
        return self.pack_max
        

    def get_product_pack(self, product=None, header=False):
        ''' Create a list for all package in product
            [(l, h, p, w)] 
            fill extra element till pack_max
        '''
        res = []
        empty = ('', '', '', '')
        # Header block:
        if not product:
            for item in range(0, self.pack_max):
                res.append((
                    _('Lung. %s') % (item + 1), 
                    _('Alt. %s') % (item + 1), 
                    _('Prof. %s') % (item + 1), 
                    _('Peso. %s') % (item + 1), 
                    ))
            return res
                
        if product.has_multipackage:
            # Multipackage test:
            i = 0
            for pack in product.multi_pack_ids: # Loop on all elements
                i += pack.number or 1
                for item in range(0, pack.number or 1):
                    res.append((
                        pack.height,
                        pack.width, 
                        pack.length, 
                        pack.weight,
                        ))           

            # Add empty extra fields:               
            for item in range(0, self.pack_max - i):
                res.append(empty)
        else:
            # TODO
            for item in range(0, self.pack_max):
                res.append(empty)
        _logger.warning(res)        
        return res
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
