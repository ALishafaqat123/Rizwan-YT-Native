from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text()

# Make the test build unmistakable on-screen and allow the longer diagnostic report.
s = s.replace('header.addView(pill("V2", ACCENT_SOFT, ACCENT_DARK));',
              'header.addView(pill("V2.0.10 TEST", ACCENT_SOFT, ACCENT_DARK));', 1)
s = s.replace('status.setMaxLines(5);', 'status.setMaxLines(8);', 1)

# Diagnostic counters are populated inside the existing mux loop, so no extra full-file scan is needed.
field_anchor = '    private volatile String lastFinalizeReport = null;\n'
fields = '''    private volatile String lastFinalizeReport = null;\n    private volatile long diagnosticVideoSamples = 0L;\n    private volatile long diagnosticAudioSamples = 0L;\n    private volatile long diagnosticDurationUs = -1L;\n    private volatile float diagnosticFps = 0f;\n'''
if field_anchor not in s:
    raise SystemExit('diagnostic field anchor not found')
s = s.replace(field_anchor, fields, 1)

# Preserve input sizes before cleanup removes the work files.
audio_ok = '        if (audioFile == null || !hasAudioTrack(audioFile.getAbsolutePath())) throw new Exception("AAC audio stream was not created correctly.");\n'
size_capture = audio_ok + '''        final long diagnosticVideoBytes = videoFile.length();\n        final long diagnosticAudioBytes = audioFile.length();\n'''
if audio_ok not in s:
    raise SystemExit('audio validation anchor not found')
s = s.replace(audio_ok, size_capture, 1)

# Capture metadata and reset sample counters at the start of the Media3 no-copy mux.
media_formats = '''            MediaFormat vf = videoExtractor.getTrackFormat(vs);\n            MediaFormat af = audioExtractor.getTrackFormat(as);\n            String vm = vf.getString(MediaFormat.KEY_MIME);'''
media_formats_new = '''            MediaFormat vf = videoExtractor.getTrackFormat(vs);\n            MediaFormat af = audioExtractor.getTrackFormat(as);\n            captureMuxDiagnostics(vf);\n            diagnosticVideoSamples = 0L;\n            diagnosticAudioSamples = 0L;\n            String vm = vf.getString(MediaFormat.KEY_MIME);'''
# First occurrence is Media3 method after V2.0.9.
if media_formats not in s:
    raise SystemExit('Media3 format anchor not found')
s = s.replace(media_formats, media_formats_new, 1)

# Count samples as they are already being written by Media3. No second scan.
media_write = '''                muxer.writeSampleData(track, buffer, muxInfo);\n                ex.advance();'''
media_write_new = '''                muxer.writeSampleData(track, buffer, muxInfo);\n                if (useVideo) diagnosticVideoSamples++; else diagnosticAudioSamples++;\n                ex.advance();'''
if media_write not in s:
    raise SystemExit('Media3 write anchor not found')
s = s.replace(media_write, media_write_new, 1)

# If Media3 falls back to Android MediaMuxer, collect the same diagnostics there.
android_method = s.index('    private void muxWithAndroid(File videoFile, File audioFile, File outputFile) throws Exception {')
android_formats_pos = s.index(media_formats, android_method)
s = s[:android_formats_pos] + s[android_formats_pos:].replace(media_formats, media_formats_new, 1)
android_write = '''                muxer.writeSampleData(track, buffer, info);\n                ex.advance();'''
android_write_new = '''                muxer.writeSampleData(track, buffer, info);\n                if (useVideo) diagnosticVideoSamples++; else diagnosticAudioSamples++;\n                ex.advance();'''
android_tail = s[android_method:]
if android_write not in android_tail:
    raise SystemExit('Android write anchor not found')
android_tail = android_tail.replace(android_write, android_write_new, 1)
s = s[:android_method] + android_tail

# Replace the V2.0.7 timing report with a fuller V2.0.10 telemetry report.
report_start = s.index('        lastFinalizeReport = "FastCheck " + formatElapsedMs(fastCheckMs) +')
report_end = s.index('        task.stage = "Finalize " + formatElapsedMs(finalizeMs);', report_start)
new_report = '''        long muxInputBytes = diagnosticVideoBytes + diagnosticAudioBytes;\n        lastFinalizeReport = "V2.0.10 DIAG\\n" +\n                "Duration " + formatDurationUs(diagnosticDurationUs) +\n                " • FPS " + formatDiagnosticFps(diagnosticFps) + "\\n" +\n                "Video " + formatBytes(diagnosticVideoBytes) +\n                " • Audio " + formatBytes(diagnosticAudioBytes) +\n                " • Final " + formatBytes(finalFile.length()) + "\\n" +\n                "Samples V " + diagnosticVideoSamples +\n                " • A " + diagnosticAudioSamples + "\\n" +\n                "FastCheck " + formatElapsedMs(fastCheckMs) +\n                " • VideoDL " + formatElapsedMs(videoDownloadMs) +\n                " • AudioDL " + formatElapsedMs(audioDownloadMs) + "\\n" +\n                muxEngine + " • Mux " + formatElapsedMs(muxMs) +\n                " • " + formatMuxRate(muxInputBytes, muxMs) +\n                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n                " • Save " + formatElapsedMs(saveMs) +\n                " • Cleanup " + formatElapsedMs(cleanupMs) +\n                " • Total " + formatElapsedMs(totalHdMs);\n\n'''
s = s[:report_start] + new_report + s[report_end:]

# Helper methods: metadata comes from the already-open MediaExtractor track format.
helper_anchor = '    private int findTrack(MediaExtractor extractor, String prefix) {\n'
helpers = '''    private void captureMuxDiagnostics(MediaFormat videoFormat) {\n        diagnosticDurationUs = -1L;\n        diagnosticFps = 0f;\n        try {\n            if (videoFormat.containsKey(MediaFormat.KEY_DURATION))\n                diagnosticDurationUs = videoFormat.getLong(MediaFormat.KEY_DURATION);\n        } catch (Exception ignored) { }\n        try {\n            if (videoFormat.containsKey(MediaFormat.KEY_FRAME_RATE)) {\n                try { diagnosticFps = videoFormat.getFloat(MediaFormat.KEY_FRAME_RATE); }\n                catch (Exception e) { diagnosticFps = videoFormat.getInteger(MediaFormat.KEY_FRAME_RATE); }\n            }\n        } catch (Exception ignored) { }\n    }\n\n    private String formatDurationUs(long durationUs) {\n        if (durationUs <= 0) return "?";\n        long totalSeconds = Math.max(0L, durationUs / 1000000L);\n        long hours = totalSeconds / 3600L;\n        long minutes = (totalSeconds % 3600L) / 60L;\n        long seconds = totalSeconds % 60L;\n        return hours > 0\n                ? String.format(Locale.US, "%d:%02d:%02d", hours, minutes, seconds)\n                : String.format(Locale.US, "%d:%02d", minutes, seconds);\n    }\n\n    private String formatDiagnosticFps(float fps) {\n        return fps > 0f ? String.format(Locale.US, "%.2f", fps) : "?";\n    }\n\n    private String formatMuxRate(long inputBytes, long muxMs) {\n        if (inputBytes <= 0L || muxMs <= 0L) return "MuxRate ?";\n        double mb = inputBytes / (1024.0 * 1024.0);\n        double seconds = muxMs / 1000.0;\n        return String.format(Locale.US, "MuxRate %.2f MB/s", mb / seconds);\n    }\n\n'''
if helper_anchor not in s:
    raise SystemExit('findTrack helper anchor not found')
s = s.replace(helper_anchor, helpers + helper_anchor, 1)

p.write_text(s)

# V2.0.10 version is applied after V2.0.9 in the workflow.
g = Path('app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 209', 'versionCode 210')
b = b.replace("versionName '2.0.9-media3-nocopy-preview'", "versionName '2.0.10-full-diagnostics-preview'")
g.write_text(b)

print('V2.0.10 full diagnostics patch applied')
