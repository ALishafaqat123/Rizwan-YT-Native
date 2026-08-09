from pathlib import Path

p = Path('app/build.gradle')
s = p.read_text()
needle = "    implementation 'org.mp4parser:isoparser:1.9.56'\n"
if needle not in s:
    raise SystemExit('isoparser dependency anchor not found')
if "org.mp4parser:muxer:1.9.56" not in s:
    s = s.replace(needle, needle + "    implementation 'org.mp4parser:muxer:1.9.56'\n", 1)
p.write_text(s)
print('MP4Parser muxer 1.9.56 dependency added')
