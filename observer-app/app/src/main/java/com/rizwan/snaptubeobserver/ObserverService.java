package com.rizwan.snaptubeobserver;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.net.TrafficStats;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.SystemClock;

import androidx.documentfile.provider.DocumentFile;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class ObserverService extends Service {
    public static final String ACTION_START = "com.rizwan.snaptubeobserver.START";
    public static final String ACTION_STOP = "com.rizwan.snaptubeobserver.STOP";
    public static final String ACTION_MARK = "com.rizwan.snaptubeobserver.MARK";
    public static final String ACTION_LOG_UPDATED = "com.rizwan.snaptubeobserver.LOG_UPDATED";

    private static final String CHANNEL = "observer_channel";
    private static final int NOTIFICATION_ID = 4107;
    private static final long POLL_MS = 1500L;
    private static volatile boolean running = false;

    private HandlerThread workerThread;
    private Handler worker;
    private String directPath;
    private Uri treeUri;
    private int snapTubeUid = -1;
    private String snapTubePackage = null;
    private long previousRx = TrafficStats.UNSUPPORTED;
    private long previousTx = TrafficStats.UNSUPPORTED;
    private long startedElapsed = 0L;
    private boolean baselineTaken = false;

    private final Map<String, FileState> previousFiles = new HashMap<>();
    private final ArrayDeque<String> tailLines = new ArrayDeque<>();
    private final SimpleDateFormat clock = new SimpleDateFormat("HH:mm:ss.SSS", Locale.US);

    public static boolean isRunning() { return running; }

    public static File getReportFile(Context context) {
        File base = context.getExternalFilesDir("SnapTubeObserver");
        if (base == null) base = new File(context.getFilesDir(), "SnapTubeObserver");
        if (!base.exists()) base.mkdirs();
        return new File(base, "observer-latest.txt");
    }

    @Override public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        workerThread = new HandlerThread("SnapTubeObserverWorker");
        workerThread.start();
        worker = new Handler(workerThread.getLooper());
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        ensureForeground("Observer ready");
        if (intent == null) return START_STICKY;
        String action = intent.getAction();
        if (ACTION_STOP.equals(action)) {
            appendLog("=== STOP REQUESTED ===");
            stopObservation();
            return START_NOT_STICKY;
        }
        if (ACTION_MARK.equals(action)) {
            appendLog("========== USER MARK: SnapTube phase changed here ==========");
            updateNotification("MARK saved • " + clock.format(new Date()));
            return START_STICKY;
        }
        if (ACTION_START.equals(action)) {
            directPath = intent.getStringExtra("path");
            String tree = intent.getStringExtra("tree_uri");
            treeUri = tree == null ? null : Uri.parse(tree);
            beginObservation();
        }
        return START_STICKY;
    }

    private void beginObservation() {
        worker.removeCallbacksAndMessages(null);
        running = true;
        baselineTaken = false;
        previousFiles.clear();
        tailLines.clear();
        startedElapsed = SystemClock.elapsedRealtime();
        resetReport();
        findSnapTubeUid();
        previousRx = snapTubeUid >= 0 ? TrafficStats.getUidRxBytes(snapTubeUid) : TrafficStats.UNSUPPORTED;
        previousTx = snapTubeUid >= 0 ? TrafficStats.getUidTxBytes(snapTubeUid) : TrafficStats.UNSUPPORTED;

        appendLog("SnapTube Observer v1.0.0");
        appendLog("Started observation");
        appendLog("Source=" + sourceLabel());
        appendLog("SnapTube package=" + (snapTubePackage == null ? "NOT FOUND" : snapTubePackage) + " uid=" + snapTubeUid);
        appendLog("Poll interval=" + POLL_MS + " ms");
        appendLog("Tip: when SnapTube shows Converting, tap MARK in this notification.");
        updateNotification("Watching • " + shortSourceLabel());
        worker.post(pollRunnable);
    }

    private final Runnable pollRunnable = new Runnable() {
        @Override public void run() {
            if (!running) return;
            try { pollOnce(); }
            catch (Throwable t) { appendLog("POLL ERROR " + t.getClass().getSimpleName() + ": " + safe(t.getMessage())); }
            if (running) worker.postDelayed(this, POLL_MS);
        }
    };

    private void pollOnce() {
        List<ObservedFile> files = new ArrayList<>();
        if (directPath != null && !directPath.isEmpty()) {
            File root = new File(directPath);
            scanFileTree(root, 0, files, 300);
        } else if (treeUri != null) {
            DocumentFile root = DocumentFile.fromTreeUri(this, treeUri);
            if (root != null) scanDocumentTree(root, 0, files, 300);
        }

        Map<String, FileState> now = new HashMap<>();
        List<ObservedFile> mediaForDuration = new ArrayList<>();
        for (ObservedFile f : files) {
            FileState old = previousFiles.get(f.key);
            FileState ns = new FileState(f.name, f.size, f.modified, old == null ? -1L : old.durationMs);
            boolean changed = old == null || old.size != f.size || old.modified != f.modified;
            if (f.media && (changed || mediaForDuration.size() < 6)) mediaForDuration.add(f);
            now.put(f.key, ns);
        }

        // Always probe a few recently seen media files. A growing playable MP4 can change duration
        // even when the filesystem reports the same allocated size.
        mediaForDuration.sort((a, b) -> Long.compare(b.modified, a.modified));
        int probes = Math.min(6, mediaForDuration.size());
        for (int i = 0; i < probes; i++) {
            ObservedFile f = mediaForDuration.get(i);
            FileState ns = now.get(f.key);
            if (ns != null) ns.durationMs = readDurationMs(f);
        }

        if (!baselineTaken) {
            previousFiles.clear();
            previousFiles.putAll(now);
            baselineTaken = true;
            appendLog("BASELINE files=" + now.size());
        } else {
            for (ObservedFile f : files) {
                FileState ns = now.get(f.key);
                FileState old = previousFiles.get(f.key);
                if (old == null) {
                    appendLog("NEW " + f.name + " size=" + formatBytes(ns.size) + durationSuffix(ns.durationMs));
                } else {
                    long delta = ns.size - old.size;
                    boolean sizeChanged = delta != 0;
                    boolean durChanged = ns.durationMs >= 0 && ns.durationMs != old.durationMs;
                    boolean modifiedChanged = ns.modified != old.modified;
                    if (sizeChanged || durChanged || modifiedChanged) {
                        String type = sizeChanged && delta > 0 ? "GROW" : (sizeChanged ? "SIZE" : (durChanged ? "DURATION" : "TOUCH"));
                        appendLog(type + " " + f.name + " size=" + formatBytes(ns.size) +
                                (sizeChanged ? " delta=" + signedBytes(delta) : "") + durationSuffix(ns.durationMs));
                    }
                }
            }
            for (Map.Entry<String, FileState> e : previousFiles.entrySet()) {
                if (!now.containsKey(e.getKey())) appendLog("DELETE/RENAME " + e.getValue().name + " lastSize=" + formatBytes(e.getValue().size));
            }
            previousFiles.clear();
            previousFiles.putAll(now);
        }

        logNetworkDelta();
        ObservedFile latest = latestMedia(files);
        if (latest != null) {
            FileState st = now.get(latest.key);
            updateNotification("Watching • " + latest.name + " • " + formatBytes(latest.size) + (st == null ? "" : durationSuffix(st.durationMs)));
        }
    }

    private void logNetworkDelta() {
        long elapsed = SystemClock.elapsedRealtime() - startedElapsed;
        if (snapTubeUid < 0) {
            appendLog("NET t=" + formatElapsed(elapsed) + " SnapTube UID unavailable");
            return;
        }
        long rx = TrafficStats.getUidRxBytes(snapTubeUid);
        long tx = TrafficStats.getUidTxBytes(snapTubeUid);
        if (rx == TrafficStats.UNSUPPORTED || tx == TrafficStats.UNSUPPORTED || previousRx == TrafficStats.UNSUPPORTED || previousTx == TrafficStats.UNSUPPORTED) {
            appendLog("NET t=" + formatElapsed(elapsed) + " per-UID counters unsupported");
        } else {
            long drx = Math.max(0L, rx - previousRx);
            long dtx = Math.max(0L, tx - previousTx);
            appendLog("NET t=" + formatElapsed(elapsed) + " RX+" + formatBytes(drx) + " TX+" + formatBytes(dtx));
        }
        previousRx = rx;
        previousTx = tx;
    }

    private void scanFileTree(File f, int depth, List<ObservedFile> out, int limit) {
        if (f == null || out.size() >= limit || depth > 4 || !f.exists()) return;
        if (f.isFile()) {
            out.add(ObservedFile.fromFile(f));
            return;
        }
        File[] children;
        try { children = f.listFiles(); } catch (Exception e) { return; }
        if (children == null) return;
        for (File child : children) {
            if (out.size() >= limit) break;
            scanFileTree(child, depth + 1, out, limit);
        }
    }

    private void scanDocumentTree(DocumentFile f, int depth, List<ObservedFile> out, int limit) {
        if (f == null || out.size() >= limit || depth > 4 || !f.exists()) return;
        if (f.isFile()) {
            out.add(ObservedFile.fromDocument(f));
            return;
        }
        DocumentFile[] children;
        try { children = f.listFiles(); } catch (Exception e) { return; }
        for (DocumentFile child : children) {
            if (out.size() >= limit) break;
            scanDocumentTree(child, depth + 1, out, limit);
        }
    }

    private long readDurationMs(ObservedFile f) {
        MediaMetadataRetriever mmr = new MediaMetadataRetriever();
        try {
            if (f.file != null) mmr.setDataSource(f.file.getAbsolutePath());
            else if (f.uri != null) mmr.setDataSource(this, f.uri);
            else return -1L;
            String d = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION);
            if (d == null) return -1L;
            return Long.parseLong(d);
        } catch (Throwable ignored) {
            return -1L;
        } finally {
            try { mmr.release(); } catch (Exception ignored) { }
        }
    }

    private ObservedFile latestMedia(List<ObservedFile> files) {
        ObservedFile best = null;
        for (ObservedFile f : files) {
            if (!f.media) continue;
            if (best == null || f.modified > best.modified) best = f;
        }
        return best;
    }

    private void findSnapTubeUid() {
        snapTubeUid = -1;
        snapTubePackage = null;
        try {
            PackageManager pm = getPackageManager();
            List<ApplicationInfo> apps = pm.getInstalledApplications(0);
            for (ApplicationInfo ai : apps) {
                String label = String.valueOf(pm.getApplicationLabel(ai)).toLowerCase(Locale.US);
                String pkg = ai.packageName.toLowerCase(Locale.US);
                if (label.contains("snaptube") || pkg.contains("snaptube")) {
                    snapTubeUid = ai.uid;
                    snapTubePackage = ai.packageName;
                    return;
                }
            }
        } catch (Throwable ignored) { }
    }

    private void stopObservation() {
        running = false;
        if (worker != null) worker.removeCallbacksAndMessages(null);
        appendLog("Observation stopped");
        stopForeground(true);
        stopSelf();
    }

    private void resetReport() {
        try {
            File f = getReportFile(this);
            if (f.exists()) f.delete();
            if (f.getParentFile() != null) f.getParentFile().mkdirs();
            f.createNewFile();
        } catch (Exception ignored) { }
        getSharedPreferences("observer_runtime", MODE_PRIVATE).edit().putString("tail", "Starting…").apply();
    }

    private synchronized void appendLog(String body) {
        String line = clock.format(new Date()) + " | " + body;
        try (BufferedWriter bw = new BufferedWriter(new FileWriter(getReportFile(this), true))) {
            bw.write(line);
            bw.newLine();
        } catch (Exception ignored) { }
        tailLines.addLast(line);
        while (tailLines.size() > 42) tailLines.removeFirst();
        StringBuilder tail = new StringBuilder();
        for (String s : tailLines) tail.append(s).append('\n');
        getSharedPreferences("observer_runtime", MODE_PRIVATE).edit().putString("tail", tail.toString()).apply();
        sendBroadcast(new Intent(ACTION_LOG_UPDATED).setPackage(getPackageName()));
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "SnapTube Observer", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Keeps the diagnostic observer running while SnapTube is open");
            getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }

    private void ensureForeground(String text) {
        startForeground(NOTIFICATION_ID, buildNotification(text));
    }

    private void updateNotification(String text) {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        nm.notify(NOTIFICATION_ID, buildNotification(text));
    }

    private Notification buildNotification(String text) {
        Intent openIntent = new Intent(this, MainActivity.class);
        PendingIntent open = PendingIntent.getActivity(this, 1, openIntent, pendingFlags());
        PendingIntent mark = PendingIntent.getService(this, 2, new Intent(this, ObserverService.class).setAction(ACTION_MARK), pendingFlags());
        PendingIntent stop = PendingIntent.getService(this, 3, new Intent(this, ObserverService.class).setAction(ACTION_STOP), pendingFlags());

        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.stat_sys_download)
                .setContentTitle("SnapTube Observer")
                .setContentText(text)
                .setContentIntent(open)
                .setOngoing(running)
                .setOnlyAlertOnce(true)
                .addAction(android.R.drawable.ic_menu_edit, "MARK", mark)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "STOP", stop);
        return b.build();
    }

    private int pendingFlags() {
        int f = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) f |= PendingIntent.FLAG_IMMUTABLE;
        return f;
    }

    private String sourceLabel() {
        if (directPath != null) return directPath;
        if (treeUri != null) return treeUri.toString();
        return "none";
    }

    private String shortSourceLabel() {
        if (directPath != null) return new File(directPath).getName();
        return treeUri != null ? "selected folder" : "no folder";
    }

    private static boolean isMediaName(String name) {
        if (name == null) return false;
        String n = name.toLowerCase(Locale.US);
        return n.endsWith(".mp4") || n.endsWith(".m4v") || n.endsWith(".mkv") || n.endsWith(".webm") || n.endsWith(".3gp") || n.endsWith(".mov") || n.endsWith(".ts");
    }

    private static String formatBytes(long bytes) {
        if (bytes < 0) return "?";
        double b = bytes;
        if (b >= 1024 * 1024 * 1024) return String.format(Locale.US, "%.2f GB", b / (1024 * 1024 * 1024));
        if (b >= 1024 * 1024) return String.format(Locale.US, "%.2f MB", b / (1024 * 1024));
        if (b >= 1024) return String.format(Locale.US, "%.1f KB", b / 1024);
        return bytes + " B";
    }

    private static String signedBytes(long delta) {
        return (delta >= 0 ? "+" : "-") + formatBytes(Math.abs(delta));
    }

    private static String durationSuffix(long ms) {
        return ms >= 0 ? " dur=" + formatDuration(ms) : " dur=?";
    }

    private static String formatDuration(long ms) {
        long sec = Math.max(0L, ms / 1000L);
        long h = sec / 3600L;
        long m = (sec % 3600L) / 60L;
        long s = sec % 60L;
        return h > 0 ? String.format(Locale.US, "%d:%02d:%02d", h, m, s) : String.format(Locale.US, "%d:%02d", m, s);
    }

    private static String formatElapsed(long ms) {
        return String.format(Locale.US, "%.1fs", ms / 1000.0);
    }

    private static String safe(String s) { return s == null ? "" : s; }

    @Override public void onDestroy() {
        running = false;
        if (worker != null) worker.removeCallbacksAndMessages(null);
        if (workerThread != null) workerThread.quitSafely();
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    private static class FileState {
        final String name;
        final long size;
        final long modified;
        long durationMs;
        FileState(String name, long size, long modified, long durationMs) {
            this.name = name; this.size = size; this.modified = modified; this.durationMs = durationMs;
        }
    }

    private static class ObservedFile {
        final String key;
        final String name;
        final long size;
        final long modified;
        final boolean media;
        final File file;
        final Uri uri;

        private ObservedFile(String key, String name, long size, long modified, boolean media, File file, Uri uri) {
            this.key = key; this.name = name; this.size = size; this.modified = modified; this.media = media; this.file = file; this.uri = uri;
        }

        static ObservedFile fromFile(File f) {
            return new ObservedFile("file:" + f.getAbsolutePath(), f.getName(), f.length(), f.lastModified(), isMediaName(f.getName()), f, null);
        }

        static ObservedFile fromDocument(DocumentFile f) {
            String name = f.getName() == null ? "(unnamed)" : f.getName();
            return new ObservedFile("uri:" + f.getUri(), name, f.length(), f.lastModified(), isMediaName(name), null, f.getUri());
        }
    }
}
