"""تجميع صلاحيات الشاشات حسب الأقسام."""

MODULE_GROUPS = [
    {
        'id': 'inventory',
        'label': 'المخزون',
        'icon': 'fa-boxes',
        'modules': [
            ('warehouses', 'المخازن'),
            ('categories', 'الأصناف الرئيسية'),
            ('companies', 'الشركات المنتجة'),
            ('products', 'الأصناف الفرعية'),
            ('stock', 'المخزون والتقارير'),
        ],
    },
    {
        'id': 'suppliers',
        'label': 'الموردين والمشتريات',
        'icon': 'fa-truck',
        'modules': [
            ('suppliers', 'الموردين'),
            ('purchases', 'المشتريات'),
        ],
    },
    {
        'id': 'customers',
        'label': 'العملاء والمبيعات',
        'icon': 'fa-users',
        'modules': [
            ('customers', 'العملاء'),
            ('sales', 'المبيعات'),
        ],
    },
    {
        'id': 'treasury',
        'label': 'الخزينة والمصروفات',
        'icon': 'fa-cash-register',
        'modules': [
            ('expenses', 'المصروفات'),
            ('daily_report', 'تقرير يومي'),
            ('activity_log', 'سجل الحركات'),
        ],
    },
    {
        'id': 'system',
        'label': 'النظام',
        'icon': 'fa-cog',
        'modules': [
            ('dashboard', 'لوحة التحكم'),
            ('settings', 'الإعدادات'),
        ],
    },
]
