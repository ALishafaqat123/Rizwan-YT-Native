from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text()

# Make this test build unmistakable and allow the detailed phase report to fit.
s = s.replace('header.addView(pill("V2.0.10 TEST", ACCENT_SOFT, ACCENT_DARK));',
              'header.addView(pill("V2.0.11 MUX LAB", ACCENT_SOFT, ACCENT_DARK));', 1)
s = s.replace('status.setMaxLines(8);', 'status.setMaxLines(11);', 1)

field_anchor = '    private volatile float diagnosticFps = 0f;\n'
fields = '''    private volatile float diagnosticFps = 0f;\n    private volatile long diagnosticMuxSetupNs = 0L;\n    private volatile long diagnosticMuxReadNs = 0L;\n    private volatile long diagnosticMuxWriteCallNs = 0L;\n    private volatile long diagnosticMuxAdvanceNs = 0L;\n    private volatile long diagnosticMuxCloseNs = 0L;\n'''
if field_anchor not in s:
    raise SystemExit('V2.0.10 diagnostic field anchor not found')
s = s.replace(field_anchor, fields, 1)

# Instrument only the Media3 no-copy method. Android fallback keeps the outer timing only.
method_start = s.index('    private void muxWithMedia3NoCopy(File videoFile, File audioFile, File outputFile) throws Exception {')
method_end = s.index('    private Format media3VideoFormat', method_start)
method = s[method_start:method_end]

old_try = '''        Mp4Muxer muxer = null;\n        try {\n            videoExtractor.setDataSource(videoFile.getAbsolutePath());'''
new_try = '''        Mp4Muxer muxer = null;\n        long muxMethodStartedNs = System.nanoTime();\n        diagnosticMuxSetupNs = 0L;\n        diagnosticMuxReadNs = 0L;\n        diagnosticMuxWriteCallNs = 0L;\n        diagnosticMuxAdvanceNs = 0L;\n        diagnosticMuxCloseNs = 0L;\n        try {\n            videoExtractor.setDataSource(videoFile.getAbsolutePath());'''
if old_try not in method:
    raise SystemExit('Media3 method start anchor not found')
method = method.replace(old_try, new_try, 1)

old_loop_start = '''            long vt = videoExtractor.getSampleTime();\n            long at = audioExtractor.getSampleTime();\n            while (vt >= 0 || at >= 0) {'''
new_loop_start = '''            long vt = videoExtractor.getSampleTime();\n            long at = audioExtractor.getSampleTime();\n            diagnosticMuxSetupNs = Math.max(0L, System.nanoTime() - muxMethodStartedNs);\n            while (vt >= 0 || at >= 0) {'''
if old_loop_start not in method:
    raise SystemExit('Media3 loop start anchor not found')
method = method.replace(old_loop_start, new_loop_start, 1)

old_read = '''                buffer.clear();\n                int size = ex.readSampleData(buffer, 0);'''
new_read = '''                buffer.clear();\n                long readStartedNs = System.nanoTime();\n                int size = ex.readSampleData(buffer, 0);\n                diagnosticMuxReadNs += Math.max(0L, System.nanoTime() - readStartedNs);'''
if old_read not in method:
    raise SystemExit('Media3 read anchor not found')
method = method.replace(old_read, new_read, 1)

old_write = '''                muxer.writeSampleData(track, buffer, muxInfo);\n                if (useVideo) diagnosticVideoSamples++; else diagnosticAudioSamples++;\n                ex.advance();'''
new_write = '''                long writeStartedNs = System.nanoTime();\n                muxer.writeSampleData(track, buffer, muxInfo);\n                diagnosticMuxWriteCallNs += Math.max(0L, System.nanoTime() - writeStartedNs);\n                if (useVideo) diagnosticVideoSamples++; else diagnosticAudioSamples++;\n                long advanceStartedNs = System.nanoTime();\n                ex.advance();\n                diagnosticMuxAdvanceNs += Math.max(0L, System.nanoTime() - advanceStartedNs);'''
if old_write not in method:
    raise SystemExit('Media3 write/advance anchor not found')
method = method.replace(old_write, new_write, 1)

old_close = '''            muxer.close();\n            muxer = null;'''
new_close = '''            long closeStartedNs = System.nanoTime();\n            muxer.close();\n            diagnosticMuxCloseNs = Math.max(0L, System.nanoTime() - closeStartedNs);\n            muxer = null;'''
if old_close not in method:
    raise SystemExit('Media3 close anchor not found')
method = method.replace(old_close, new_close, 1)

s = s[:method_start] + method + s[method_end:]

# Extend the V2.0.10 report with precise mux phase timing.
old_report_tail = '''                muxEngine + " • Mux " + formatElapsedMs(muxMs) +\n                " • " + formatMuxRate(muxInputBytes, muxMs) +\n                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n                " • Save " + formatElapsedMs(saveMs) +\n                " • Cleanup " + formatElapsedMs(cleanupMs) +\n                " • Total " + formatElapsedMs(totalHdMs);'''
new_report_tail = '''                muxEngine + " • Mux " + formatElapsedMs(muxMs) +\n                " • " + formatMuxRate(muxInputBytes, muxMs) + "\\n" +\n                "MuxPhase Setup " + formatElapsedNs(diagnosticMuxSetupNs) +\n                " • Read " + formatElapsedNs(diagnosticMuxReadNs) +\n                " • WriteCalls " + formatElapsedNs(diagnosticMuxWriteCallNs) + "\\n" +\n                "Advance " + formatElapsedNs(diagnosticMuxAdvanceNs) +\n                " • Close " + formatElapsedNs(diagnosticMuxCloseNs) +\n                " • Other " + formatMuxOther(muxMs) + "\\n" +\n                "Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n                " • Save " + formatElapsedMs(saveMs) +\n                " • Cleanup " + formatElapsedMs(cleanupMs) +\n                " • Total " + formatElapsedMs(totalHdMs);'''
if old_report_tail not in s:
    raise SystemExit('V2.0.10 report tail not found')
s = s.replace(old_report_tail, new_report_tail, 1)

helper_anchor = '    private String formatMuxRate(long inputBytes, long muxMs) {\n'
helpers = '''    private String formatElapsedNs(long ns) {\n        if (ns <= 0L) return "0 ms";\n        double ms = ns / 1000000.0;\n        if (ms < 1000.0) return String.format(Locale.US, "%.0f ms", ms);\n        return String.format(Locale.US, "%.1f s", ms / 1000.0);\n    }\n\n    private String formatMuxOther(long muxMs) {\n        long measuredNs = diagnosticMuxSetupNs + diagnosticMuxReadNs +\n                diagnosticMuxWriteCallNs + diagnosticMuxAdvanceNs + diagnosticMuxCloseNs;\n        long totalNs = Math.max(0L, muxMs) * 1000000L;\n        return formatElapsedNs(Math.max(0L, totalNs - measuredNs));\n    }\n\n'''
if helper_anchor not in s:
    raise SystemExit('formatMuxRate helper anchor not found')
s = s.replace(helper_anchor, helpers + helper_anchor, 1)

# Rename the report banner so screenshots identify the exact build.
s = s.replace('lastFinalizeReport = "V2.0.10 DIAG\\n" +',
              'lastFinalizeReport = "V2.0.11 MUX LAB\\n" +', 1)

p.write_text(s)

# Version applied after V2.0.10 in CI.
g = Path('app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 210', 'versionCode 211')
b = b.replace("versionName '2.0.10-full-diagnostics-preview'", "versionName '2.0.11-mux-phase-diagnostics-preview'")
g.write_text(b)

print('V2.0.11 mux phase diagnostics patch applied')
