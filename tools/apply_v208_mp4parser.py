from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text()

# Add MP4Parser imports after the existing Media3 imports.
needle = 'import androidx.media3.muxer.Mp4Muxer;\n'
imports = '''import androidx.media3.muxer.Mp4Muxer;\nimport org.mp4parser.Container;\nimport org.mp4parser.muxer.Movie;\nimport org.mp4parser.muxer.Track;\nimport org.mp4parser.muxer.builder.DefaultMp4Builder;\nimport org.mp4parser.muxer.container.mp4.MovieCreator;\n'''
if needle not in s:
    raise SystemExit('Media3 import anchor not found')
s = s.replace(needle, imports, 1)

# Add FileChannel import.
needle = 'import java.nio.ByteBuffer;\n'
if needle not in s:
    raise SystemExit('ByteBuffer import anchor not found')
s = s.replace(needle, needle + 'import java.nio.channels.FileChannel;\n', 1)

# Replace mux selection with MP4Parser -> Media3 -> Android fallback.
old = '''        String muxEngine = "Media3 batched";\n        try {\n            muxWithMedia3Batched(videoFile, audioFile, mergedTemp);\n        } catch (Exception batchedError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Android fallback";\n            muxWithAndroid(videoFile, audioFile, mergedTemp);\n        }'''
new = '''        String muxEngine = "MP4Parser container";\n        try {\n            muxWithMp4Parser(videoFile, audioFile, mergedTemp);\n        } catch (Exception parserError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Media3 fallback";\n            try {\n                muxWithMedia3Batched(videoFile, audioFile, mergedTemp);\n            } catch (Exception batchedError) {\n                if (mergedTemp.exists()) mergedTemp.delete();\n                muxEngine = "Android fallback";\n                muxWithAndroid(videoFile, audioFile, mergedTemp);\n            }\n        }'''
if old not in s:
    raise SystemExit('mux selection block not found')
s = s.replace(old, new, 1)

# Insert the container-level mux method immediately before Media3 mux.
anchor = '    private void muxWithMedia3Batched(File videoFile, File audioFile, File outputFile) throws Exception {\n'
if anchor not in s:
    raise SystemExit('Media3 method anchor not found')
method = r'''    private void muxWithMp4Parser(File videoFile, File audioFile, File outputFile) throws Exception {
        Movie videoMovie = null;
        Movie audioMovie = null;
        try {
            if (outputFile.exists() && !outputFile.delete())
                throw new Exception("Could not replace MP4Parser output file.");

            videoMovie = MovieCreator.build(videoFile.getAbsolutePath());
            audioMovie = MovieCreator.build(audioFile.getAbsolutePath());

            Track videoTrack = null;
            Track audioTrack = null;
            for (Track t : videoMovie.getTracks()) {
                if ("vide".equals(t.getHandler())) { videoTrack = t; break; }
            }
            for (Track t : audioMovie.getTracks()) {
                if ("soun".equals(t.getHandler())) { audioTrack = t; break; }
            }
            if (videoTrack == null || audioTrack == null)
                throw new Exception("MP4Parser input track missing.");

            Movie outMovie = new Movie();
            outMovie.addTrack(videoTrack);
            outMovie.addTrack(audioTrack);
            try { outMovie.setMatrix(videoMovie.getMatrix()); } catch (Exception ignored) { }

            Container container = new DefaultMp4Builder().build(outMovie);
            try (FileOutputStream fos = new FileOutputStream(outputFile);
                 FileChannel channel = fos.getChannel()) {
                container.writeContainer(channel);
                channel.force(true);
            }
        } finally {
            if (videoMovie != null) {
                for (Track t : videoMovie.getTracks()) try { t.close(); } catch (Exception ignored) { }
            }
            if (audioMovie != null) {
                for (Track t : audioMovie.getTracks()) try { t.close(); } catch (Exception ignored) { }
            }
        }
    }

'''
s = s.replace(anchor, method + anchor, 1)
p.write_text(s)

# Version and dependency are applied after the V2.0.7 patch.
g = Path('app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 207', 'versionCode 208')
b = b.replace("versionName '2.0.7-no-wasted-wait-timing-preview'", "versionName '2.0.8-container-fast-mux-preview'")
if "org.mp4parser:isoparser:1.9.56" not in b:
    b = b.replace("    implementation 'androidx.media3:media3-muxer:1.9.1'\n",
                  "    implementation 'androidx.media3:media3-muxer:1.9.1'\n    implementation 'org.mp4parser:isoparser:1.9.56'\n")
g.write_text(b)

print('V2.0.8 MP4Parser mux patch applied')
