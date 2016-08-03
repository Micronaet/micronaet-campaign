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

{
    'name': 'Campaign product extra',
    'version': '0.1',
    'category': '',
    'description': '''        
        Add extra search field and group by clause depend on family module
        and gamma
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        #'product',
        'campaign_product',

        # For filter:
        'catalog_management', # Micronaet/micronaet-crm # Gamma
        'production_family', # Micronaet/micronaet-production XXX Family 
        'sql_product', # Micronaet/micronaet-sql XXX stat cat.
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        'extra_view.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
