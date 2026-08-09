from pathlib import Path
p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text(encoding='utf-8')

bad = 'setStatus(n + "\nFast V2 engine • Android MediaMuxer ready.");'
# Here bad contains a real newline between the quotes, matching the accidental source output.
if bad not in s:
    raise SystemExit('status newline pattern not found')
s = s.replace(bad, 'setStatus(n + "\\nFast V2 engine • Android MediaMuxer ready.");', 1)

layout_block = '''            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(\n                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);\n            lp.bottomMargin = dp(7);\n            convertView.setLayoutParams(lp);\n            return convertView;\n'''
if layout_block not in s:
    raise SystemExit('playlist ListView layout block not found')
s = s.replace(layout_block, '''            return convertView;\n''', 1)

p.write_text(s, encoding='utf-8')
print('V2.0.1 compile/runtime safety fixes applied')
