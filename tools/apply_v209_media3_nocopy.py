from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text()

# V2.0.9 isolates the Media3 write path. MP4Parser was not effective on-device,
# so do not spend time trying it before the actual test muxer.
old = '''        String muxEngine = "MP4Parser container";\n        try {\n            muxWithMp4Parser(videoFile, audioFile, mergedTemp);\n        } catch (Exception parserError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Media3 fallback";\n            try {\n                muxWithMedia3Batched(videoFile, audioFile, mergedTemp);\n            } catch (Exception batchedError) {\n                if (mergedTemp.exists()) mergedTemp.delete();\n                muxEngine = "Android fallback";\n                muxWithAndroid(videoFile, audioFile, mergedTemp);\n            }\n        }'''
new = '''        String muxEngine = "Media3 no-copy";\n        try {\n            muxWithMedia3NoCopy(videoFile, audioFile, mergedTemp);\n        } catch (Exception noCopyError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Android fallback";\n            muxWithAndroid(videoFile, audioFile, mergedTemp);\n        }'''
if old not in s:
    raise SystemExit('V2.0.8 mux selection block not found')
s = s.replace(old, new, 1)

# Rename the Media3 method and explicitly disable both batching and sample copying.
old_sig = '    private void muxWithMedia3Batched(File videoFile, File audioFile, File outputFile) throws Exception {\n'
new_sig = '    private void muxWithMedia3NoCopy(File videoFile, File audioFile, File outputFile) throws Exception {\n'
if old_sig not in s:
    raise SystemExit('Media3 batched method not found')
s = s.replace(old_sig, new_sig, 1)

old_builder = '''            muxer = new Mp4Muxer.Builder(new FileOutputStream(outputFile))\n                    .setSampleBatchingEnabled(true)\n                    .setSampleCopyingEnabled(true)\n                    .build();'''
new_builder = '''            muxer = new Mp4Muxer.Builder(new FileOutputStream(outputFile))\n                    .setSampleBatchingEnabled(false)\n                    .setSampleCopyingEnabled(false)\n                    .build();'''
if old_builder not in s:
    raise SystemExit('Media3 builder flags not found')
s = s.replace(old_builder, new_builder, 1)

# Make any Media3 error labels match this test path.
s = s.replace('Media3 batched mux requires H.264 video, got ', 'Media3 no-copy mux requires H.264 video, got ')
s = s.replace('Media3 batched mux requires AAC audio, got ', 'Media3 no-copy mux requires AAC audio, got ')

p.write_text(s)

g = Path('app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 208', 'versionCode 209')
b = b.replace("versionName '2.0.8-container-fast-mux-preview'", "versionName '2.0.9-media3-nocopy-preview'")
g.write_text(b)

print('V2.0.9 Media3 no-copy/unbatched patch applied')
