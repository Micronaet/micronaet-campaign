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
    'name': 'Manage Campaign - Base',
    'version': '0.1',
    'category': 'Campaign',
    'description': '''    
        Base module for manage campaing for a company that sold external 
        furniture
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'product',
        'mail',
        'sale', # for sale generation
        'stock', # for stock movement (inventory operations)
        'product_image_base', # Image management
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        'security/campaign_group.xml',
        'security/ir.model.access.csv',    
        'campaign_view.xml',
        'counter.xml',
        'workflow/campaign_workflow.xml',
        'report/campaign_report.xml',
        'wizard/assign_campaign.xml',
        'wizard/wizard_status_report.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
