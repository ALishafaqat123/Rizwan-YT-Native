from pathlib import Path

service = Path('observer-app/app/src/main/java/com/rizwan/snaptubeobserver/ObserverService.java')
s = service.read_text()

# v1.0.1 and v1.0.2 are applied first by CI.
s = s.replace('    private static final long NETWORK_POLL_MS = 5000L;\n',
              '    private static final long NETWORK_POLL_MS = 2000L;\n', 1)

anchor = '    private long lastMarkElapsed = -10000L;\n'
if anchor not in s:
    raise SystemExit('v1.0.2 field anchor missing')
s = s.replace(anchor, anchor +
'''    private long observationWallStart = 0L;\n    private String detectedStage = "WAITING";\n''', 1)

begin_anchor = '        startedElapsed = SystemClock.elapsedRealtime();\n'
if begin_anchor not in s:
    raise SystemExit('begin observation time anchor missing')
s = s.replace(begin_anchor, begin_anchor + '        observationWallStart = System.currentTimeMillis();\n        detectedStage = "WAITING";\n', 1)

s = s.replace('        appendLog("SnapTube Observer v1.0.2");', '        appendLog("SnapTube Observer v1.0.3");', 1)
s = s.replace(
    '        appendLog("File poll interval=" + POLL_MS + " ms; network poll=" + NETWORK_POLL_MS + " ms; scanLimit=" + SCAN_LIMIT);',
    '        appendLog("File poll=" + POLL_MS + " ms; network poll=" + NETWORK_POLL_MS + " ms; candidateLimit=" + SCAN_LIMIT);',
    1)
s = s.replace(
    '        appendLog("MARK is optional. Fast converting is captured automatically by file polling.");',
    '        appendLog("UI percentage is ignored. STAGE lines are inferred from real temp/final file states.");',
    1)

# Only retain temp/download files and files modified close to this observation. This prevents
# a shifting top-N list of hundreds of old videos from creating false DELETE/RENAME events.
old_file_leaf = '''        if (f.isFile()) {\n            out.add(ObservedFile.fromFile(f));\n            return;\n        }\n'''
new_file_leaf = '''        if (f.isFile()) {\n            if (shouldTrackFile(f.getName(), f.lastModified())) out.add(ObservedFile.fromFile(f));\n            return;\n        }\n'''
if old_file_leaf not in s:
    raise SystemExit('file leaf anchor missing')
s = s.replace(old_file_leaf, new_file_leaf, 1)

old_doc_leaf = '''        if (f.isFile()) {\n            out.add(ObservedFile.fromDocument(f));\n            return;\n        }\n'''
new_doc_leaf = '''        if (f.isFile()) {\n            String name = f.getName() == null ? "" : f.getName();\n            if (shouldTrackFile(name, f.lastModified())) out.add(ObservedFile.fromDocument(f));\n            return;\n        }\n'''
if old_doc_leaf not in s:
    raise SystemExit('document leaf anchor missing')
s = s.replace(old_doc_leaf, new_doc_leaf, 1)

# Run stage classification before previousFiles is replaced so this poll's transitions remain visible.
needle = '''            previousFiles.clear();\n            previousFiles.putAll(now);\n        }\n\n        ObservedFile latest = latestMedia(files);\n'''
replacement = '''            updateDetectedStage(files, now);\n            previousFiles.clear();\n            previousFiles.putAll(now);\n        }\n\n        if (!baselineTaken) updateDetectedStage(files, now);\n        ObservedFile latest = latestMedia(files);\n'''
if needle not in s:
    raise SystemExit('stage insertion anchor missing')
s = s.replace(needle, replacement, 1)

# The baseline branch sets baselineTaken before reaching the post-block check above, so classify there too.
baseline_old = '''            previousFiles.putAll(now);\n            baselineTaken = true;\n            appendLog("BASELINE files=" + now.size());\n'''
baseline_new = '''            previousFiles.putAll(now);\n            baselineTaken = true;\n            appendLog("BASELINE diagnosticFiles=" + now.size());\n            updateDetectedStage(files, now);\n'''
if baseline_old not in s:
    raise SystemExit('baseline anchor missing')
s = s.replace(baseline_old, baseline_new, 1)

# Remove redundant post-baseline classifier introduced above; baseline branch already handles it.
s = s.replace('        if (!baselineTaken) updateDetectedStage(files, now);\n        ObservedFile latest = latestMedia(files);',
              '        ObservedFile latest = latestMedia(files);', 1)

insert_before = '    private long readDurationMs(ObservedFile f) {\n'
if insert_before not in s:
    raise SystemExit('duration method anchor missing')
helpers = r'''    private boolean shouldTrackFile(String name, long modified) {
        String n = name == null ? "" : name.toLowerCase(Locale.US);
        boolean temp = n.contains("video.tmp") || n.contains("audio.tmp") || n.endsWith(".download") || n.contains("tmp.download");
        // Keep all active SnapTube temp files plus normal files touched within 2 minutes before START.
        return temp || modified >= observationWallStart - 120000L;
    }

    private void updateDetectedStage(List<ObservedFile> files, Map<String, FileState> now) {
        ObservedFile videoDownloading = null;
        ObservedFile videoReady = null;
        ObservedFile audioDownloading = null;
        ObservedFile audioReady = null;
        ObservedFile finalRecent = null;

        for (ObservedFile f : files) {
            String n = f.name == null ? "" : f.name.toLowerCase(Locale.US);
            if (n.equals("video.tmp.download") || (n.contains("video.tmp") && n.endsWith(".download"))) {
                videoDownloading = newer(videoDownloading, f);
            } else if (n.equals("video.tmp") || (n.contains("video.tmp") && !n.endsWith(".download"))) {
                videoReady = newer(videoReady, f);
            }
            if (n.equals("audio.tmp.download") || (n.contains("audio.tmp") && n.endsWith(".download"))) {
                audioDownloading = newer(audioDownloading, f);
            } else if (n.equals("audio.tmp") || (n.contains("audio.tmp") && !n.endsWith(".download"))) {
                audioReady = newer(audioReady, f);
            }
            if (f.media && !n.contains(".tmp") && !n.endsWith(".download") && f.modified >= observationWallStart) {
                finalRecent = newer(finalRecent, f);
            }
        }

        String stage;
        String evidence;
        if (videoDownloading != null) {
            stage = "VIDEO DOWNLOAD";
            evidence = fileEvidence(videoDownloading, now);
        } else if (audioDownloading != null) {
            stage = "AUDIO DOWNLOAD";
            evidence = joinEvidence(fileEvidence(videoReady, now), fileEvidence(audioDownloading, now));
        } else if (videoReady != null && audioReady != null && finalRecent != null) {
            stage = "MUX / CONVERT";
            evidence = joinEvidence(fileEvidence(videoReady, now), fileEvidence(audioReady, now), fileEvidence(finalRecent, now));
        } else if (videoReady != null && audioReady != null) {
            stage = "READY TO MUX";
            evidence = joinEvidence(fileEvidence(videoReady, now), fileEvidence(audioReady, now));
        } else if (videoReady != null) {
            stage = "VIDEO READY / AUDIO STARTUP";
            evidence = fileEvidence(videoReady, now);
        } else if (finalRecent != null) {
            stage = "FINAL FILE / COMPLETE";
            evidence = fileEvidence(finalRecent, now);
        } else {
            stage = "WAITING";
            evidence = "no active SnapTube temp/final file";
        }

        if (!stage.equals(detectedStage)) {
            detectedStage = stage;
            appendLog("STAGE >>> " + stage + " | " + evidence);
            updateNotification(stage + " • " + shortSourceLabel());
        }
    }

    private ObservedFile newer(ObservedFile a, ObservedFile b) {
        if (b == null) return a;
        if (a == null || b.modified >= a.modified) return b;
        return a;
    }

    private String fileEvidence(ObservedFile f, Map<String, FileState> now) {
        if (f == null) return "";
        FileState st = now.get(f.key);
        long dur = st == null ? -1L : st.durationMs;
        return f.name + "=" + formatBytes(f.size) + durationSuffix(dur);
    }

    private String joinEvidence(String... values) {
        StringBuilder sb = new StringBuilder();
        for (String v : values) {
            if (v == null || v.isEmpty()) continue;
            if (sb.length() > 0) sb.append(" ; ");
            sb.append(v);
        }
        return sb.length() == 0 ? "state transition" : sb.toString();
    }

'''
s = s.replace(insert_before, helpers + insert_before, 1)

service.write_text(s)

# UI: make network permission status impossible to miss before starting a test.
main = Path('observer-app/app/src/main/java/com/rizwan/snaptubeobserver/MainActivity.java')
m = main.read_text()

# Add AppOps imports.
m = m.replace('import android.app.Activity;\n', 'import android.app.Activity;\nimport android.app.AppOpsManager;\n', 1)

start_old = '''    private void startObserver() {\n        String path = getPreferences().getString("path", null);\n'''
start_new = '''    private void startObserver() {\n        if (!hasUsageAccess()) {\n            Toast.makeText(this, "Network tracking is OFF. File/stage tracking will still work, but enable Usage Access for decisive network evidence.", Toast.LENGTH_LONG).show();\n        }\n        String path = getPreferences().getString("path", null);\n'''
if start_old not in m:
    raise SystemExit('startObserver anchor missing')
m = m.replace(start_old, start_new, 1)

helper_anchor = '    private android.content.SharedPreferences getPreferences() {\n'
if helper_anchor not in m:
    raise SystemExit('MainActivity helper anchor missing')
usage_helper = r'''    private boolean hasUsageAccess() {
        if (Build.VERSION.SDK_INT < 21) return true;
        try {
            AppOpsManager appOps = (AppOpsManager) getSystemService(APP_OPS_SERVICE);
            if (appOps == null) return false;
            int mode = appOps.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS,
                    android.os.Process.myUid(), getPackageName());
            return mode == AppOpsManager.MODE_ALLOWED;
        } catch (Throwable ignored) {
            return false;
        }
    }

'''
m = m.replace(helper_anchor, usage_helper + helper_anchor, 1)

m = m.replace('MARK is optional; fast Converting is captured automatically. If you can, tap MARK when Converting appears.',
              'Ignore SnapTube percentage. Observer will auto-log VIDEO DOWNLOAD, AUDIO DOWNLOAD, MUX/CONVERT and FINAL FILE stages. MARK is optional.', 1)
main.write_text(m)

# Version bump after v1.0.2 patch.
g = Path('observer-app/app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 3', 'versionCode 4', 1)
b = b.replace("versionName '1.0.2-observer'", "versionName '1.0.3-observer'", 1)
g.write_text(b)

print('SnapTube Observer v1.0.3 stage classifier applied')
