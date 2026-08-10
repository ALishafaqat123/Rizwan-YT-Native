from pathlib import Path

# ---- Manifest: Usage Access app-op permission for NetworkStatsManager ----
manifest = Path('observer-app/app/src/main/AndroidManifest.xml')
s = manifest.read_text()
needle = '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n'
if 'android.permission.PACKAGE_USAGE_STATS' not in s:
    if needle not in s:
        raise SystemExit('manifest permission anchor missing')
    s = s.replace(needle, needle + '    <uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" />\n', 1)
manifest.write_text(s)

# ---- Main UI: make Usage Access a clear recommended step ----
main = Path('observer-app/app/src/main/java/com/rizwan/snaptubeobserver/MainActivity.java')
s = main.read_text()
s = s.replace(
    'TextView privacy = text("Diagnostic only: it watches the folder you choose and public network counters. It does not read SnapTube private files or messages.", 13, false);',
    'TextView privacy = text("Diagnostic only: it watches the folder you choose. Network tracking uses Android Usage Access only if you enable it. It does not read SnapTube private files, messages, memory or encrypted traffic.", 13, false);',
    1)
s = s.replace(
    'TextView guide = text("How to test\\n1. Select the SnapTube root/download folder.\\n2. Tap START OBSERVING.\\n3. Open SnapTube and download one HD video.\\n4. When Converting appears, pull down the notification and tap MARK.\\n5. Return here after it finishes and tap COPY FULL REPORT.", 14, false);',
    'TextView guide = text("How to test\\n1. Tap ENABLE NETWORK TRACKING and enable SnapTube Observer in Usage Access (recommended).\\n2. Select the SnapTube root/download folder.\\n3. Tap START OBSERVING.\\n4. Open SnapTube and download one HD video.\\n5. When Converting appears, pull down the notification and tap MARK.\\n6. Return here after it finishes, tap STOP, then COPY FULL REPORT.", 14, false);',
    1)
s = s.replace('Button usage = button("OPEN USAGE ACCESS (OPTIONAL)");', 'Button usage = button("ENABLE NETWORK TRACKING");', 1)
main.write_text(s)

# ---- Service: replace cross-app TrafficStats with NetworkStatsManager on its own thread ----
service = Path('observer-app/app/src/main/java/com/rizwan/snaptubeobserver/ObserverService.java')
s = service.read_text()

s = s.replace('import android.net.TrafficStats;\n',
'''import android.app.usage.NetworkStats;\nimport android.app.usage.NetworkStatsManager;\nimport android.net.ConnectivityManager;\n''', 1)

old_fields = '''    private HandlerThread workerThread;\n    private Handler worker;\n    private String directPath;\n    private Uri treeUri;\n    private int snapTubeUid = -1;\n    private String snapTubePackage = null;\n    private long previousRx = TrafficStats.UNSUPPORTED;\n    private long previousTx = TrafficStats.UNSUPPORTED;\n    private long startedElapsed = 0L;\n    private boolean baselineTaken = false;\n'''
new_fields = '''    private HandlerThread workerThread;\n    private Handler worker;\n    private HandlerThread networkThread;\n    private Handler networkWorker;\n    private static final long NETWORK_POLL_MS = 5000L;\n    private String directPath;\n    private Uri treeUri;\n    private int snapTubeUid = -1;\n    private String snapTubePackage = null;\n    private long networkStartWall = 0L;\n    private long previousNetworkRx = -1L;\n    private long previousNetworkTx = -1L;\n    private boolean networkPermissionWarned = false;\n    private long startedElapsed = 0L;\n    private boolean baselineTaken = false;\n'''
if old_fields not in s:
    raise SystemExit('service fields anchor missing')
s = s.replace(old_fields, new_fields, 1)

old_create = '''        workerThread = new HandlerThread("SnapTubeObserverWorker");\n        workerThread.start();\n        worker = new Handler(workerThread.getLooper());\n'''
new_create = '''        workerThread = new HandlerThread("SnapTubeObserverWorker");\n        workerThread.start();\n        worker = new Handler(workerThread.getLooper());\n        networkThread = new HandlerThread("SnapTubeObserverNetwork");\n        networkThread.start();\n        networkWorker = new Handler(networkThread.getLooper());\n'''
if old_create not in s:
    raise SystemExit('onCreate anchor missing')
s = s.replace(old_create, new_create, 1)

old_begin = '''        worker.removeCallbacksAndMessages(null);\n        running = true;\n        baselineTaken = false;\n        previousFiles.clear();\n        tailLines.clear();\n        startedElapsed = SystemClock.elapsedRealtime();\n        resetReport();\n        findSnapTubeUid();\n        previousRx = snapTubeUid >= 0 ? TrafficStats.getUidRxBytes(snapTubeUid) : TrafficStats.UNSUPPORTED;\n        previousTx = snapTubeUid >= 0 ? TrafficStats.getUidTxBytes(snapTubeUid) : TrafficStats.UNSUPPORTED;\n\n        appendLog("SnapTube Observer v1.0.0");\n'''
new_begin = '''        worker.removeCallbacksAndMessages(null);\n        if (networkWorker != null) networkWorker.removeCallbacksAndMessages(null);\n        running = true;\n        baselineTaken = false;\n        previousFiles.clear();\n        tailLines.clear();\n        startedElapsed = SystemClock.elapsedRealtime();\n        networkStartWall = System.currentTimeMillis() - 2000L;\n        previousNetworkRx = -1L;\n        previousNetworkTx = -1L;\n        networkPermissionWarned = false;\n        resetReport();\n        findSnapTubeUid();\n\n        appendLog("SnapTube Observer v1.0.1");\n'''
if old_begin not in s:
    raise SystemExit('beginObservation anchor missing')
s = s.replace(old_begin, new_begin, 1)

old_post = '''        appendLog("Poll interval=" + POLL_MS + " ms");\n        appendLog("Tip: when SnapTube shows Converting, tap MARK in this notification.");\n        updateNotification("Watching • " + shortSourceLabel());\n        worker.post(pollRunnable);\n'''
new_post = '''        appendLog("File poll interval=" + POLL_MS + " ms; network poll=" + NETWORK_POLL_MS + " ms");\n        appendLog("Tip: when SnapTube shows Converting, tap MARK in this notification.");\n        updateNotification("Watching • " + shortSourceLabel());\n        worker.post(pollRunnable);\n        if (networkWorker != null) networkWorker.post(networkRunnable);\n'''
if old_post not in s:
    raise SystemExit('worker post anchor missing')
s = s.replace(old_post, new_post, 1)

s = s.replace('        logNetworkDelta();\n        ObservedFile latest = latestMedia(files);', '        ObservedFile latest = latestMedia(files);', 1)

old_net_start = s.index('    private void logNetworkDelta() {')
old_net_end = s.index('    private void scanFileTree(', old_net_start)
new_net = '''    private final Runnable networkRunnable = new Runnable() {\n        @Override public void run() {\n            if (!running) return;\n            try { logNetworkStatsDelta(); }\n            catch (Throwable t) {\n                if (!networkPermissionWarned) {\n                    appendLog("NET unavailable: " + t.getClass().getSimpleName() + " " + safe(t.getMessage()));\n                    networkPermissionWarned = true;\n                }\n            }\n            if (running && networkWorker != null) networkWorker.postDelayed(this, NETWORK_POLL_MS);\n        }\n    };\n\n    private void logNetworkStatsDelta() {\n        long elapsed = SystemClock.elapsedRealtime() - startedElapsed;\n        if (snapTubeUid < 0) {\n            if (!networkPermissionWarned) {\n                appendLog("NET SnapTube package/UID unavailable");\n                networkPermissionWarned = true;\n            }\n            return;\n        }\n        long[] totals;\n        try {\n            totals = queryUidNetworkTotals(snapTubeUid, networkStartWall, System.currentTimeMillis());\n        } catch (SecurityException se) {\n            if (!networkPermissionWarned) {\n                appendLog("NET permission missing — enable Usage Access for SnapTube Observer");\n                networkPermissionWarned = true;\n            }\n            return;\n        }\n        networkPermissionWarned = false;\n        long rx = totals[0];\n        long tx = totals[1];\n        if (previousNetworkRx < 0L || previousNetworkTx < 0L) {\n            previousNetworkRx = rx;\n            previousNetworkTx = tx;\n            appendLog("NET baseline t=" + formatElapsed(elapsed) + " RX=" + formatBytes(rx) + " TX=" + formatBytes(tx));\n            return;\n        }\n        long drx = Math.max(0L, rx - previousNetworkRx);\n        long dtx = Math.max(0L, tx - previousNetworkTx);\n        previousNetworkRx = rx;\n        previousNetworkTx = tx;\n        appendLog("NET t=" + formatElapsed(elapsed) + " RX+" + formatBytes(drx) + " TX+" + formatBytes(dtx));\n    }\n\n    private long[] queryUidNetworkTotals(int uid, long startMs, long endMs) {\n        NetworkStatsManager manager = (NetworkStatsManager) getSystemService(NETWORK_STATS_SERVICE);\n        if (manager == null) throw new IllegalStateException("NetworkStatsManager unavailable");\n        long rx = 0L;\n        long tx = 0L;\n        long[] wifi = queryOneNetwork(manager, ConnectivityManager.TYPE_WIFI, uid, startMs, endMs);\n        rx += wifi[0];\n        tx += wifi[1];\n        try {\n            long[] mobile = queryOneNetwork(manager, ConnectivityManager.TYPE_MOBILE, uid, startMs, endMs);\n            rx += mobile[0];\n            tx += mobile[1];\n        } catch (IllegalArgumentException ignored) { }\n        return new long[]{rx, tx};\n    }\n\n    private long[] queryOneNetwork(NetworkStatsManager manager, int networkType, int uid, long startMs, long endMs) {\n        NetworkStats stats = null;\n        long rx = 0L;\n        long tx = 0L;\n        try {\n            stats = manager.queryDetailsForUid(networkType, null, startMs, endMs, uid);\n            NetworkStats.Bucket bucket = new NetworkStats.Bucket();\n            while (stats != null && stats.hasNextBucket()) {\n                stats.getNextBucket(bucket);\n                rx += Math.max(0L, bucket.getRxBytes());\n                tx += Math.max(0L, bucket.getTxBytes());\n            }\n            return new long[]{rx, tx};\n        } finally {\n            if (stats != null) try { stats.close(); } catch (Exception ignored) { }\n        }\n    }\n\n'''
s = s[:old_net_start] + new_net + s[old_net_end:]

old_stop = '''        running = false;\n        if (worker != null) worker.removeCallbacksAndMessages(null);\n        appendLog("Observation stopped");\n'''
new_stop = '''        running = false;\n        if (worker != null) worker.removeCallbacksAndMessages(null);\n        if (networkWorker != null) networkWorker.removeCallbacksAndMessages(null);\n        appendLog("Observation stopped");\n'''
if old_stop not in s:
    raise SystemExit('stop anchor missing')
s = s.replace(old_stop, new_stop, 1)

old_destroy = '''        running = false;\n        if (worker != null) worker.removeCallbacksAndMessages(null);\n        if (workerThread != null) workerThread.quitSafely();\n        super.onDestroy();\n'''
new_destroy = '''        running = false;\n        if (worker != null) worker.removeCallbacksAndMessages(null);\n        if (networkWorker != null) networkWorker.removeCallbacksAndMessages(null);\n        if (workerThread != null) workerThread.quitSafely();\n        if (networkThread != null) networkThread.quitSafely();\n        super.onDestroy();\n'''
if old_destroy not in s:
    raise SystemExit('onDestroy anchor missing')
s = s.replace(old_destroy, new_destroy, 1)

service.write_text(s)

# Version bump so the corrected build is unmistakable.
g = Path('observer-app/app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 1', 'versionCode 2', 1)
b = b.replace("versionName '1.0.0-observer'", "versionName '1.0.1-observer'", 1)
g.write_text(b)

print('SnapTube Observer v1.0.1 NetworkStats fix applied')
