from pathlib import Path

for path in Path('apps').rglob('migrations/*.py'):
    text = path.read_text(encoding='utf-8')
    new = text.replace("('shop',", "('pharmacy',").replace("to='shop.", "to='pharmacy.")
    if new != text:
        path.write_text(new, encoding='utf-8')
        print(path)
