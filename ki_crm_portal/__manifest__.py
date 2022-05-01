# -*- coding: utf-8 -*-


{
    'name': "CRM Portal Account",
    'summary': """CRM Portal Account""",
    'description': """CRM Portal Account""",
    'version': "0.5",
    'category': "CRM",
    'author': "Manas Ram Satapathy",
    "depends": [
        'crm','crm_checklist'
    ],
    "data": [
        'security/ir.model.access.csv',
        'wizard/assign_lead_partners_view.xml',
        'views/res_partner_view.xml',
        'views/crm_view.xml',
        'views/crm_portal_template.xml',
    ],
    'application': False,
    'installable': True,
}
