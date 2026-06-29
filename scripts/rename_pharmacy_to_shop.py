import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
skip = {'.git', 'venv', '__pycache__', 'staticfiles', 'node_modules'}
replacements = [
    ('apps.shop', 'apps.shop'),
    ("'shop.", "'shop."),
    ("('shop',", "('shop',"),
    ("to='shop.", "to='shop."),
    ('ShopConfig', 'ShopConfig'),
    ("include('apps.shop", "include('apps.shop"),
]

for path in list(root.rglob('*.py')):
    if any(p in path.parts for p in skip):
        continue
    text = path.read_text(encoding='utf-8')
    orig = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding='utf-8')
        print(path.relative_to(root))
