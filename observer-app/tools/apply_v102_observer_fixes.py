from pathlib import Path

service = Path('observer-app/app/src/main/java/com/rizwan/snaptubeobserver/ObserverService.java')
s = service.read_text()

# v1.0.1 is applied first by the workflow. Build v1.0.2 on top of that source.
s = s.replace('import java.util.ArrayDeque;\n', 'import java.util.ArrayDeque;\nimport java.util.Arrays;\n', 1)

s = s.replace(
    '    private static final long POLL_MS = 1500L;\n',
    '    private static final long POLL_MS = 750L;\n'
    '    private static final int SCAN_LIMIT = 1500;\n'
    '    private static final long MARK_DEBOUNCE_MS = 1200L;\n',
    1)

anchor = '    private boolean baselineTaken = false;\n'
if anchor not in s:
    raise SystemExit('baseline field anchor missing')
s = s.replace(anchor, anchor + '    private long lastMarkElapsed = -10000L;\n', 1)

old_mark = '''        if (ACTION_MARK.equals(action)) {\n            appendLog("========== USER MARK: SnapTube phase changed here ==========");\n            updateNotification("MARK saved • " + clock.format(new Date()));\n            return START_STICKY;\n        }\n'''
new_mark = '''        if (ACTION_MARK.equals(action)) {\n            long now = SystemClock.elapsedRealtime();\n            if (now - lastMarkElapsed >= MARK_DEBOUNCE_MS) {\n                lastMarkElapsed = now;\n                appendLog("========== USER MARK: SnapTube phase changed here ==========");\n                updateNotification("MARK saved • " + clock.format(new Date()));\n            }\n            return START_STICKY;\n        }\n'''
if old_mark not in s:
    raise SystemExit('mark action anchor missing')
s = s.replace(old_mark, new_mark, 1)

s = s.replace('        appendLog("SnapTube Observer v1.0.1");', '        appendLog("SnapTube Observer v1.0.2");', 1)
s = s.replace('        appendLog("File poll interval=" + POLL_MS + " ms; network poll=" + NETWORK_POLL_MS + " ms");',
              '        appendLog("File poll interval=" + POLL_MS + " ms; network poll=" + NETWORK_POLL_MS + " ms; scanLimit=" + SCAN_LIMIT);', 1)
s = s.replace('        appendLog("Tip: when SnapTube shows Converting, tap MARK in this notification.");',
              '        appendLog("MARK is optional. Fast converting is captured automatically by file polling.");', 1)

s = s.replace('            scanFileTree(root, 0, files, 300);', '            scanFileTree(root, 0, files, SCAN_LIMIT);', 1)
s = s.replace('            if (root != null) scanDocumentTree(root, 0, files, 300);', '            if (root != null) scanDocumentTree(root, 0, files, SCAN_LIMIT);', 1)

old_scan_file = '''    private void scanFileTree(File f, int depth, List<ObservedFile> out, int limit) {\n        if (f == null || out.size() >= limit || depth > 4 || !f.exists()) return;\n        if (f.isFile()) {\n            out.add(ObservedFile.fromFile(f));\n            return;\n        }\n        File[] children;\n        try { children = f.listFiles(); } catch (Exception e) { return; }\n        if (children == null) return;\n        for (File child : children) {\n            if (out.size() >= limit) break;\n            scanFileTree(child, depth + 1, out, limit);\n        }\n    }\n'''
new_scan_file = '''    private void scanFileTree(File f, int depth, List<ObservedFile> out, int limit) {\n        if (f == null || out.size() >= limit || depth > 5 || !f.exists()) return;\n        if (f.isFile()) {\n            out.add(ObservedFile.fromFile(f));\n            return;\n        }\n        File[] children;\n        try { children = f.listFiles(); } catch (Exception e) { return; }\n        if (children == null) return;\n        // Recent files/directories first, so a new or growing SnapTube download is never\n        // hidden behind hundreds of old files in the root folder.\n        try { Arrays.sort(children, (a, b) -> Long.compare(b.lastModified(), a.lastModified())); }\n        catch (Throwable ignored) { }\n        for (File child : children) {\n            if (out.size() >= limit) break;\n            scanFileTree(child, depth + 1, out, limit);\n        }\n    }\n'''
if old_scan_file not in s:
    raise SystemExit('file scan method anchor missing')
s = s.replace(old_scan_file, new_scan_file, 1)

old_scan_doc = '''    private void scanDocumentTree(DocumentFile f, int depth, List<ObservedFile> out, int limit) {\n        if (f == null || out.size() >= limit || depth > 4 || !f.exists()) return;\n        if (f.isFile()) {\n            out.add(ObservedFile.fromDocument(f));\n            return;\n        }\n        DocumentFile[] children;\n        try { children = f.listFiles(); } catch (Exception e) { return; }\n        for (DocumentFile child : children) {\n            if (out.size() >= limit) break;\n            scanDocumentTree(child, depth + 1, out, limit);\n        }\n    }\n'''
new_scan_doc = '''    private void scanDocumentTree(DocumentFile f, int depth, List<ObservedFile> out, int limit) {\n        if (f == null || out.size() >= limit || depth > 5 || !f.exists()) return;\n        if (f.isFile()) {\n            out.add(ObservedFile.fromDocument(f));\n            return;\n        }\n        DocumentFile[] children;\n        try { children = f.listFiles(); } catch (Exception e) { return; }\n        try { Arrays.sort(children, (a, b) -> Long.compare(b.lastModified(), a.lastModified())); }\n        catch (Throwable ignored) { }\n        for (DocumentFile child : children) {\n            if (out.size() >= limit) break;\n            scanDocumentTree(child, depth + 1, out, limit);\n        }\n    }\n'''
if old_scan_doc not in s:
    raise SystemExit('document scan method anchor missing')
s = s.replace(old_scan_doc, new_scan_doc, 1)

old_find = '''    private void findSnapTubeUid() {\n        snapTubeUid = -1;\n        snapTubePackage = null;\n        try {\n            PackageManager pm = getPackageManager();\n            List<ApplicationInfo> apps = pm.getInstalledApplications(0);\n            for (ApplicationInfo ai : apps) {\n                String label = String.valueOf(pm.getApplicationLabel(ai)).toLowerCase(Locale.US);\n                String pkg = ai.packageName.toLowerCase(Locale.US);\n                if (label.contains("snaptube") || pkg.contains("snaptube")) {\n                    snapTubeUid = ai.uid;\n                    snapTubePackage = ai.packageName;\n                    return;\n                }\n            }\n        } catch (Throwable ignored) { }\n    }\n'''
new_find = '''    private void findSnapTubeUid() {\n        snapTubeUid = -1;\n        snapTubePackage = null;\n        try {\n            PackageManager pm = getPackageManager();\n            List<ApplicationInfo> apps = pm.getInstalledApplications(0);\n            String self = getPackageName();\n            ApplicationInfo best = null;\n            int bestScore = -1;\n            for (ApplicationInfo ai : apps) {\n                if (ai == null || ai.packageName == null || ai.packageName.equals(self)) continue;\n                String label = String.valueOf(pm.getApplicationLabel(ai)).trim().toLowerCase(Locale.US);\n                String pkg = ai.packageName.toLowerCase(Locale.US);\n                int score = -1;\n                if (label.equals("snaptube")) score = 100;\n                else if (pkg.contains("snaptube")) score = 80;\n                else if (label.contains("snaptube")) score = 60;\n                if (score > bestScore) {\n                    bestScore = score;\n                    best = ai;\n                }\n            }\n            if (best != null) {\n                snapTubeUid = best.uid;\n                snapTubePackage = best.packageName;\n            }\n        } catch (Throwable ignored) { }\n    }\n'''
if old_find not in s:
    raise SystemExit('findSnapTubeUid anchor missing')
s = s.replace(old_find, new_find, 1)

service.write_text(s)

# MainActivity: do not launch Observer itself as SnapTube, and make MARK clearly optional.
main = Path('observer-app/app/src/main/java/com/rizwan/snaptubeobserver/MainActivity.java')
m = main.read_text()
old_main_find = '''    private String findSnapTubePackage() {\n        try {\n            List<ApplicationInfo> apps = getPackageManager().getInstalledApplications(0);\n            for (ApplicationInfo ai : apps) {\n                String label = String.valueOf(getPackageManager().getApplicationLabel(ai)).toLowerCase(Locale.US);\n                String pkg = ai.packageName.toLowerCase(Locale.US);\n                if (label.contains("snaptube") || pkg.contains("snaptube")) return ai.packageName;\n            }\n        } catch (Exception ignored) { }\n        return null;\n    }\n'''
new_main_find = '''    private String findSnapTubePackage() {\n        try {\n            PackageManager pm = getPackageManager();\n            List<ApplicationInfo> apps = pm.getInstalledApplications(0);\n            String self = getPackageName();\n            ApplicationInfo best = null;\n            int bestScore = -1;\n            for (ApplicationInfo ai : apps) {\n                if (ai == null || ai.packageName == null || ai.packageName.equals(self)) continue;\n                String label = String.valueOf(pm.getApplicationLabel(ai)).trim().toLowerCase(Locale.US);\n                String pkg = ai.packageName.toLowerCase(Locale.US);\n                int score = -1;\n                if (label.equals("snaptube")) score = 100;\n                else if (pkg.contains("snaptube")) score = 80;\n                else if (label.contains("snaptube")) score = 60;\n                if (score > bestScore) { bestScore = score; best = ai; }\n            }\n            return best == null ? null : best.packageName;\n        } catch (Exception ignored) { }\n        return null;\n    }\n'''
if old_main_find not in m:
    raise SystemExit('MainActivity findSnapTubePackage anchor missing')
m = m.replace(old_main_find, new_main_find, 1)
m = m.replace('When Converting appears, pull down the notification and tap MARK.',
              'MARK is optional; fast Converting is captured automatically. If you can, tap MARK when Converting appears.', 1)
main.write_text(m)

# v1.0.1 patch leaves versionCode 2 / versionName 1.0.1-observer.
g = Path('observer-app/app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 2', 'versionCode 3', 1)
b = b.replace("versionName '1.0.1-observer'", "versionName '1.0.2-observer'", 1)
g.write_text(b)

print('SnapTube Observer v1.0.2 fixes applied')
