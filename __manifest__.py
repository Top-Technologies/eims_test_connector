{
    'name': 'EIMS DEMO',
    'summary': 'Proof of concept connector for EIMS',
    'version': '18.0.1.0.0',  # Updated version to match Odoo 18.0 path
    'category': 'Accounting/Localizations',
    'depends': ['base', 'account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/company_eims_view.xml',
        'views/partner_eims_view.xml',
        'views/eims_registered_invoice_views.xml',
        'views/eims_cancel_log_view.xml',

    ],
    'installable': True,
    'license': 'LGPL-3',
}
