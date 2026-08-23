from pathlib import Path

p = Path('desktop-app/tools/apply_v120_preview15_watch_multi.py')
s = p.read_text(encoding='utf-8')
changes = 0

old = 'pattern.subn(replacement, s, count=1)'
count = s.count(old)
if count:
    s = s.replace(old, 'pattern.subn(lambda _m: replacement, s, count=1)')
    changes += count

old = 'BeginInvoke(KickQueueScheduler);'
if old in s:
    s = s.replace(old, 'BeginInvoke(() => KickQueueScheduler());')
    changes += 1

if changes:
    p.write_text(s, encoding='utf-8')
    print(f'Hardened Preview 15 patch in {changes} place(s)')
else:
    print('Preview 15 patch already hardened')
