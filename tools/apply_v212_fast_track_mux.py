from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text()

# Make this experiment unmistakable on screen.
s = s.replace('header.addView(pill("V2.0.11 MUX LAB", ACCENT_SOFT, ACCENT_DARK));',
              'header.addView(pill("V2.0.12 FAST TRACK", ACCENT_SOFT, ACCENT_DARK));', 1)

# Prefer a track-pass mux that avoids per-sample video/audio interleave decisions.
old_select = '''        String muxEngine = "Media3 no-copy";\n        try {\n            muxWithMedia3NoCopy(videoFile, audioFile, mergedTemp);\n        } catch (Exception noCopyError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Android fallback";\n            muxWithAndroid(videoFile, audioFile, mergedTemp);\n        }'''
new_select = '''        String muxEngine = "Media3 track-pass";\n        try {\n            muxWithMedia3TrackPass(videoFile, audioFile, mergedTemp);\n        } catch (Exception trackPassError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Media3 interleaved fallback";\n            try {\n                muxWithMedia3NoCopy(videoFile, audioFile, mergedTemp);\n            } catch (Exception noCopyError) {\n                if (mergedTemp.exists()) mergedTemp.delete();\n                muxEngine = "Android fallback";\n                muxWithAndroid(videoFile, audioFile, mergedTemp);\n            }\n        }'''
if old_select not in s:
    raise SystemExit('V2.0.11 mux selection block not found')
s = s.replace(old_select, new_select, 1)

# Add a new Media3 implementation that writes one whole track at a time. Timestamps are
# preserved, so this is still remuxing only; there is no decode/re-encode.
anchor = '    private void muxWithMedia3NoCopy(File videoFile, File audioFile, File outputFile) throws Exception {\n'
method = '''    private void muxWithMedia3TrackPass(File videoFile, File audioFile, File outputFile) throws Exception {\n        MediaExtractor videoExtractor = new MediaExtractor();\n        MediaExtractor audioExtractor = new MediaExtractor();\n        Mp4Muxer muxer = null;\n        long muxMethodStartedNs = System.nanoTime();\n        diagnosticMuxSetupNs = 0L;\n        diagnosticMuxReadNs = 0L;\n        diagnosticMuxWriteCallNs = 0L;\n        diagnosticMuxAdvanceNs = 0L;\n        diagnosticMuxCloseNs = 0L;\n        try {\n            videoExtractor.setDataSource(videoFile.getAbsolutePath());\n            audioExtractor.setDataSource(audioFile.getAbsolutePath());\n            int vs = findTrack(videoExtractor, "video/");\n            int as = findTrack(audioExtractor, "audio/");\n            if (vs < 0 || as < 0) throw new Exception("Media3 track-pass input track missing.");\n\n            MediaFormat vf = videoExtractor.getTrackFormat(vs);\n            MediaFormat af = audioExtractor.getTrackFormat(as);\n            captureMuxDiagnostics(vf);\n            diagnosticVideoSamples = 0L;\n            diagnosticAudioSamples = 0L;\n            String vm = vf.getString(MediaFormat.KEY_MIME);\n            String am = af.getString(MediaFormat.KEY_MIME);\n            if (vm == null || !"video/avc".equalsIgnoreCase(vm))\n                throw new Exception("Media3 track-pass requires H.264 video, got " + vm);\n            if (am == null || !am.toLowerCase(Locale.US).startsWith("audio/mp4a"))\n                throw new Exception("Media3 track-pass requires AAC audio, got " + am);\n\n            if (outputFile.exists() && !outputFile.delete())\n                throw new Exception("Could not replace Media3 track-pass output MP4.");\n\n            muxer = new Mp4Muxer.Builder(new FileOutputStream(outputFile))\n                    .setSampleBatchingEnabled(false)\n                    .setSampleCopyingEnabled(false)\n                    .build();\n\n            int vmux = muxer.addTrack(media3VideoFormat(vf));\n            int amux = muxer.addTrack(media3AudioFormat(af));\n            videoExtractor.selectTrack(vs);\n            audioExtractor.selectTrack(as);\n\n            int bufferSize = Math.max(8 * 1024 * 1024,\n                    Math.max(maxInputSize(vf), maxInputSize(af)) + 1024);\n            ByteBuffer buffer = ByteBuffer.allocateDirect(bufferSize);\n            diagnosticMuxSetupNs = Math.max(0L, System.nanoTime() - muxMethodStartedNs);\n\n            writeMedia3TrackPass(videoExtractor, vmux, buffer, true, muxer);\n            writeMedia3TrackPass(audioExtractor, amux, buffer, false, muxer);\n\n            long closeStartedNs = System.nanoTime();\n            muxer.close();\n            diagnosticMuxCloseNs = Math.max(0L, System.nanoTime() - closeStartedNs);\n            muxer = null;\n        } finally {\n            try { videoExtractor.release(); } catch (Exception ignored) { }\n            try { audioExtractor.release(); } catch (Exception ignored) { }\n            if (muxer != null) try { muxer.close(); } catch (Exception ignored) { }\n        }\n    }\n\n    private void writeMedia3TrackPass(MediaExtractor extractor, int muxTrack, ByteBuffer buffer,\n                                      boolean video, Mp4Muxer muxer) throws Exception {\n        while (true) {\n            long sampleTimeUs = extractor.getSampleTime();\n            if (sampleTimeUs < 0L) break;\n            int sampleFlags = extractor.getSampleFlags();\n\n            buffer.clear();\n            long readStartedNs = System.nanoTime();\n            int size = extractor.readSampleData(buffer, 0);\n            diagnosticMuxReadNs += Math.max(0L, System.nanoTime() - readStartedNs);\n            if (size < 0) break;\n\n            androidx.media3.muxer.BufferInfo muxInfo =\n                    new androidx.media3.muxer.BufferInfo(sampleTimeUs, size, sampleFlags);\n            long writeStartedNs = System.nanoTime();\n            muxer.writeSampleData(muxTrack, buffer, muxInfo);\n            diagnosticMuxWriteCallNs += Math.max(0L, System.nanoTime() - writeStartedNs);\n            if (video) diagnosticVideoSamples++; else diagnosticAudioSamples++;\n\n            long advanceStartedNs = System.nanoTime();\n            extractor.advance();\n            diagnosticMuxAdvanceNs += Math.max(0L, System.nanoTime() - advanceStartedNs);\n        }\n    }\n\n'''
if anchor not in s:
    raise SystemExit('Media3 no-copy method anchor not found')
s = s.replace(anchor, method + anchor, 1)

# Rename the report banner for screenshots.
s = s.replace('lastFinalizeReport = "V2.0.11 MUX LAB\\n" +',
              'lastFinalizeReport = "V2.0.12 FAST TRACK\\n" +', 1)

p.write_text(s)

# Version applied after V2.0.11 in CI.
g = Path('app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 211', 'versionCode 212')
b = b.replace("versionName '2.0.11-mux-phase-diagnostics-preview'", "versionName '2.0.12-fast-track-mux-preview'")
g.write_text(b)

print('V2.0.12 fast track mux patch applied')
