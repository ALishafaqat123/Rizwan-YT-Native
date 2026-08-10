package com.rizwan.snaptubeobserver;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.List;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int REQ_TREE = 1001;
    private static final int REQ_STORAGE = 1002;
    private static final int ACCENT = Color.rgb(10, 174, 120);
    private static final int DARK = Color.rgb(30, 36, 34);

    private TextView folderText;
    private TextView stateText;
    private TextView logText;

    private final BroadcastReceiver logReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            refreshUi();
        }
    };

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildUi());
        requestStorageIfNeeded();
        refreshUi();
    }

    @Override protected void onStart() {
        super.onStart();
        registerReceiver(logReceiver, new IntentFilter(ObserverService.ACTION_LOG_UPDATED));
        refreshUi();
    }

    @Override protected void onStop() {
        try { unregisterReceiver(logReceiver); } catch (Exception ignored) { }
        super.onStop();
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(18), dp(20), dp(30));
        scroll.addView(root, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView title = text("SnapTube Observer", 28, true);
        root.addView(title);
        TextView sub = text("Watch files, playable duration and network while SnapTube downloads.", 15, false);
        sub.setTextColor(Color.DKGRAY);
        root.addView(sub, lpTop(4));

        TextView privacy = text("Diagnostic only: it watches the folder you choose and public network counters. It does not read SnapTube private files or messages.", 13, false);
        privacy.setTextColor(Color.rgb(80, 92, 88));
        root.addView(privacy, lpTop(12));

        folderText = text("Folder: not selected", 15, true);
        root.addView(folderText, lpTop(20));

        LinearLayout row1 = row();
        Button auto = button("AUTO FIND");
        auto.setOnClickListener(v -> autoFindFolder());
        row1.addView(auto, weight());
        Button choose = button("CHOOSE FOLDER");
        choose.setOnClickListener(v -> chooseFolder());
        row1.addView(choose, weightLeft());
        root.addView(row1, lpTop(10));

        stateText = text("Observer stopped", 16, true);
        root.addView(stateText, lpTop(18));

        LinearLayout row2 = row();
        Button start = button("START OBSERVING");
        start.setOnClickListener(v -> startObserver());
        row2.addView(start, weight());
        Button stop = button("STOP");
        stop.setOnClickListener(v -> sendServiceAction(ObserverService.ACTION_STOP));
        row2.addView(stop, weightLeft());
        root.addView(row2, lpTop(10));

        LinearLayout row3 = row();
        Button open = button("OPEN SNAPTube");
        open.setOnClickListener(v -> openSnapTube());
        row3.addView(open, weight());
        Button mark = button("MARK NOW");
        mark.setOnClickListener(v -> sendServiceAction(ObserverService.ACTION_MARK));
        row3.addView(mark, weightLeft());
        root.addView(row3, lpTop(10));

        TextView guide = text("How to test\n1. Select the SnapTube root/download folder.\n2. Tap START OBSERVING.\n3. Open SnapTube and download one HD video.\n4. When Converting appears, pull down the notification and tap MARK.\n5. Return here after it finishes and tap COPY FULL REPORT.", 14, false);
        guide.setTextColor(Color.rgb(55, 64, 61));
        root.addView(guide, lpTop(18));

        Button copy = button("COPY FULL REPORT");
        copy.setOnClickListener(v -> copyReport());
        root.addView(copy, lpTop(14));

        Button usage = button("OPEN USAGE ACCESS (OPTIONAL)");
        usage.setOnClickListener(v -> {
            try { startActivity(new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)); }
            catch (Exception e) { Toast.makeText(this, "Usage Access settings unavailable", Toast.LENGTH_SHORT).show(); }
        });
        root.addView(usage, lpTop(8));

        TextView live = text("Live log", 17, true);
        root.addView(live, lpTop(20));
        logText = text("No report yet.", 12, false);
        logText.setTextIsSelectable(true);
        logText.setPadding(dp(12), dp(12), dp(12), dp(12));
        logText.setBackgroundColor(Color.rgb(243, 247, 245));
        root.addView(logText, lpTop(8));

        return scroll;
    }

    private void requestStorageIfNeeded() {
        if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.READ_EXTERNAL_STORAGE}, REQ_STORAGE);
        }
    }

    private void autoFindFolder() {
        if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            requestStorageIfNeeded();
            Toast.makeText(this, "Allow storage access, then tap AUTO FIND again.", Toast.LENGTH_LONG).show();
            return;
        }
        File root = Environment.getExternalStorageDirectory();
        File[] candidates = new File[]{
                new File(root, "snaptube"),
                new File(root, "SnapTube"),
                new File(root, "Download/snaptube"),
                new File(root, "Download/SnapTube")
        };
        File found = null;
        for (File f : candidates) if (f.exists() && f.isDirectory()) { found = f; break; }
        if (found == null) found = findNamedFolder(root, 2);
        if (found == null) {
            Toast.makeText(this, "SnapTube folder not found automatically. Use CHOOSE FOLDER.", Toast.LENGTH_LONG).show();
            return;
        }
        getPreferences().edit().putString("path", found.getAbsolutePath()).remove("tree_uri").apply();
        Toast.makeText(this, "Found: " + found.getAbsolutePath(), Toast.LENGTH_LONG).show();
        refreshUi();
    }

    private File findNamedFolder(File dir, int depth) {
        if (dir == null || depth < 0 || !dir.isDirectory()) return null;
        File[] children;
        try { children = dir.listFiles(); } catch (Exception e) { return null; }
        if (children == null) return null;
        for (File child : children) {
            if (!child.isDirectory()) continue;
            String n = child.getName().toLowerCase(Locale.US);
            if (n.contains("snaptube")) return child;
        }
        if (depth == 0) return null;
        for (File child : children) {
            if (!child.isDirectory()) continue;
            String n = child.getName().toLowerCase(Locale.US);
            if (n.equals("android") || n.equals("dcim") || n.startsWith(".")) continue;
            File f = findNamedFolder(child, depth - 1);
            if (f != null) return f;
        }
        return null;
    }

    private void chooseFolder() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        startActivityForResult(i, REQ_TREE);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_TREE && resultCode == RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(uri, data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } catch (Exception ignored) { }
            getPreferences().edit().putString("tree_uri", uri.toString()).remove("path").apply();
            refreshUi();
        }
    }

    private void startObserver() {
        String path = getPreferences().getString("path", null);
        String tree = getPreferences().getString("tree_uri", null);
        if ((path == null || path.isEmpty()) && (tree == null || tree.isEmpty())) {
            Toast.makeText(this, "First choose the SnapTube folder.", Toast.LENGTH_LONG).show();
            return;
        }
        Intent i = new Intent(this, ObserverService.class).setAction(ObserverService.ACTION_START);
        if (path != null) i.putExtra("path", path);
        if (tree != null) i.putExtra("tree_uri", tree);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
        Toast.makeText(this, "Observer started. Now open SnapTube.", Toast.LENGTH_LONG).show();
        refreshUi();
    }

    private void sendServiceAction(String action) {
        Intent i = new Intent(this, ObserverService.class).setAction(action);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
    }

    private void openSnapTube() {
        PackageManager pm = getPackageManager();
        String pkg = findSnapTubePackage();
        if (pkg == null) {
            Toast.makeText(this, "SnapTube app was not found.", Toast.LENGTH_LONG).show();
            return;
        }
        Intent launch = pm.getLaunchIntentForPackage(pkg);
        if (launch != null) startActivity(launch); else Toast.makeText(this, "Could not open SnapTube.", Toast.LENGTH_LONG).show();
    }

    private String findSnapTubePackage() {
        try {
            List<ApplicationInfo> apps = getPackageManager().getInstalledApplications(0);
            for (ApplicationInfo ai : apps) {
                String label = String.valueOf(getPackageManager().getApplicationLabel(ai)).toLowerCase(Locale.US);
                String pkg = ai.packageName.toLowerCase(Locale.US);
                if (label.contains("snaptube") || pkg.contains("snaptube")) return ai.packageName;
            }
        } catch (Exception ignored) { }
        return null;
    }

    private void copyReport() {
        File f = ObserverService.getReportFile(this);
        if (!f.exists()) {
            Toast.makeText(this, "No report yet.", Toast.LENGTH_SHORT).show();
            return;
        }
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new FileReader(f))) {
            String line;
            while ((line = br.readLine()) != null) sb.append(line).append('\n');
        } catch (Exception e) {
            Toast.makeText(this, "Could not read report: " + e.getMessage(), Toast.LENGTH_LONG).show();
            return;
        }
        ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("SnapTube Observer Report", sb.toString()));
        Toast.makeText(this, "Full report copied.", Toast.LENGTH_SHORT).show();
    }

    private void refreshUi() {
        String path = getPreferences().getString("path", null);
        String tree = getPreferences().getString("tree_uri", null);
        if (folderText != null) folderText.setText("Folder: " + (path != null ? path : (tree != null ? tree : "not selected")));
        if (stateText != null) stateText.setText(ObserverService.isRunning() ? "● OBSERVING IN BACKGROUND" : "Observer stopped");
        String tail = getSharedPreferences("observer_runtime", MODE_PRIVATE).getString("tail", "No report yet.");
        if (logText != null) logText.setText(tail);
    }

    private android.content.SharedPreferences getPreferences() {
        return getSharedPreferences("observer_prefs", MODE_PRIVATE);
    }

    private LinearLayout row() {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        return r;
    }

    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(12);
        b.setTextColor(Color.WHITE);
        b.setBackgroundColor(ACCENT);
        b.setAllCaps(false);
        return b;
    }

    private TextView text(String value, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(sp);
        t.setTextColor(DARK);
        if (bold) t.setTypeface(t.getTypeface(), android.graphics.Typeface.BOLD);
        return t;
    }

    private LinearLayout.LayoutParams weight() {
        return new LinearLayout.LayoutParams(0, dp(52), 1f);
    }

    private LinearLayout.LayoutParams weightLeft() {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(52), 1f);
        lp.leftMargin = dp(8);
        return lp;
    }

    private LinearLayout.LayoutParams lpTop(int topDp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(topDp);
        return lp;
    }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
}
