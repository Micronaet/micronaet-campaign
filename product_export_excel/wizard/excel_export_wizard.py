#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


import os
import sys
import logging
import openerp
import xlsxwriter
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class ProductProductExcelExportWizard(orm.TransientModel):
    ''' Wizard for export product
    '''
    _name = 'product.product.excel.export.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_export(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        if context is None: 
            context = {}        
        
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        product_start = wiz_browse.product_start
        with_image = wiz_browse.with_image
        max_length = wiz_browse.max_length
        
        # Pool used:
        excel_pool = self.pool.get('excel.writer')
        product_pool = self.pool.get('product.product')
        
        # ---------------------------------------------------------------------
        #                          Excel export:
        # ---------------------------------------------------------------------
        # Setup:
        ws_name = 'Prodotti'
        header = [
            'Immagine',
            'Articolo',
            'Nome articolo',
            'Descrizione',
            'Colore',
            'Tessuto',
            'cmb',
            'Peso netto',
            'Peso lordo',
            'Pezzi per palette',
            'Pezzi per camion',
            'EAN13',
            'EAN13 Mono',
            'Listino',
            ]
            
        width = [
            30, 
            15,
            30,
            30,
            40,
            40,
            5,
            8,
            8,
            8,
            8,
            12,
            12,
            12,
            ]
        
        # ---------------------------------------------------------------------
        # Create WS:
        # ---------------------------------------------------------------------
        ws = excel_pool.create_worksheet(name=ws_name)
        excel_pool.column_width(ws_name, width)
        #excel_pool.row_height(ws_name, row_list, height=10)
        title = _('Filtro: Prodotti che iniziano per %s (%s)') % (
            product_start,
            _('Con immagine') if with_image else _('Senza immagine')
            )
        
        # ---------------------------------------------------------------------
        # Generate format used:
        # ---------------------------------------------------------------------
        excel_pool.set_format()
        f_title = excel_pool.get_format(key='title')
        f_header = excel_pool.get_format(key='header')
        f_text = excel_pool.get_format(key='text')
        f_number = excel_pool.get_format(key='number')
        
        # ---------------------------------------------------------------------
        # Write title / header    
        # ---------------------------------------------------------------------
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [title], default_format=f_title)

        row += 1
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=f_header)
        
        # ---------------------------------------------------------------------
        # Product selection:
        # ---------------------------------------------------------------------
        product_ids = []
        for start in product_start.split('|'):
            start = start.strip()
            product_ids.extend(product_pool.search(cr, uid, [
                ('default_code', '=ilike', '%s%%' % start),
                ], context=context))

        product_ids = list(set(product_ids)) # Clean double
        product_proxy = product_pool.browse(cr, uid, product_ids, 
            context=context)
        row += 1
        for product in sorted(product_proxy, key=lambda x: x.default_code):
            default_code = product.default_code or ''
            if max_length and len(default_code) > max_length:
                continue # jump product
                
            line = [
                '',
                product.default_code or '',
                product.name or '',
                product.description_sale or '',
                product.colour or '',
                product.fabric or '',
                product.volume or '',
                product.weight_net or '',
                product.weight or '',
                product.item_per_pallet or '',
                product.item_per_camion or '',
                product.ean13 or '',
                product.ean13_mono or '',
                (product.lst_price or 0.0, f_number),
                ]
                
            excel_pool.write_xls_line(
                ws_name, row, line, default_format=f_text)
            row += 1
        
        return excel_pool.return_attachment(cr, uid, _('prodotti'))

    _columns = {
        'with_image':fields.boolean('With image'),
        'max_length': fields.integer('Max length <=', 
            help='Max lenght of code'),
        'product_start': fields.text(
            'Product start', help='Start list of product, ex.: 127|128|130TX',
            required=True,
            ),
        }
    _defaults = {
        'max_length': lambda *x: 6,
        }    
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
