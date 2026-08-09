from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text(encoding='utf-8')

old = '''            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();\n            long vt = videoExtractor.getSampleTime();\n            long at = audioExtractor.getSampleTime();\n            while (vt >= 0 || at >= 0) {\n                boolean useVideo = at < 0 || (vt >= 0 && vt <= at);\n                MediaExtractor ex = useVideo ? videoExtractor : audioExtractor;\n                int track = useVideo ? vmux : amux;\n                buffer.clear();\n                int size = ex.readSampleData(buffer, 0);\n                if (size < 0) {\n                    if (useVideo) vt = -1; else at = -1;\n                    continue;\n                }\n                info.set(0, size, ex.getSampleTime(), ex.getSampleFlags());\n                muxer.writeSampleData(track, buffer, info);\n                ex.advance();\n'''
new = '''            long vt = videoExtractor.getSampleTime();\n            long at = audioExtractor.getSampleTime();\n            while (vt >= 0 || at >= 0) {\n                boolean useVideo = at < 0 || (vt >= 0 && vt <= at);\n                MediaExtractor ex = useVideo ? videoExtractor : audioExtractor;\n                int track = useVideo ? vmux : amux;\n                buffer.clear();\n                int size = ex.readSampleData(buffer, 0);\n                if (size < 0) {\n                    if (useVideo) vt = -1; else at = -1;\n                    continue;\n                }\n                androidx.media3.muxer.BufferInfo muxInfo = new androidx.media3.muxer.BufferInfo(\n                        ex.getSampleTime(), size, ex.getSampleFlags());\n                muxer.writeSampleData(track, buffer, muxInfo);\n                ex.advance();\n'''

# There are two similar loops. Replace only the first occurrence after muxWithMedia3Batched.
start = s.find('    private void muxWithMedia3Batched(')
end = s.find('    private void muxWithAndroid(', start)
if start < 0 or end < 0:
    raise SystemExit('Media3 method bounds not found')
chunk = s[start:end]
if old not in chunk:
    raise SystemExit('Media3 BufferInfo block not found')
chunk = chunk.replace(old, new, 1)
s = s[:start] + chunk + s[end:]
p.write_text(s, encoding='utf-8')
print('V2.0.5 Media3 BufferInfo fix applied')
