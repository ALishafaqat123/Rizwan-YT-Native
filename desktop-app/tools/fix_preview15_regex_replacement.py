from pathlib import Path

p = Path('desktop-app/tools/apply_v120_preview15_watch_multi.py')
s = p.read_text(encoding='utf-8')
old = 'pattern.subn(replacement, s, count=1)'
count = s.count(old)
if count == 0:
    print('Preview 15 regex replacements already guarded')
else:
    s = s.replace(old, 'pattern.subn(lambda _m: replacement, s, count=1)')
    p.write_text(s, encoding='utf-8')
    print(f'Guarded {count} Preview 15 regex replacement(s)')
