from pathlib import Path

for path in Path('apps').rglob('migrations/*.py'):
    text = path.read_text(encoding='utf-8')
    new = text.replace("('pharmacy',", "('shop',").replace("to='pharmacy.", "to='shop.")
    if new != text:
        path.write_text(new, encoding='utf-8')
        print(path)
