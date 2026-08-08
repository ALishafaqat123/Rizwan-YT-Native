package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.text.InputType;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;

import java.io.File;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class MainActivity extends Activity {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private EditText urlInput;
    private TextView status;
    private ProgressBar progress;
    private Button downloadButton;
    private Button cancelButton;
    private volatile boolean engineReady = false;
    private volatile String processId = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        ensureStoragePermission();
        initEngine();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(8, 13, 20));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(22), dp(28), dp(22), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));

        TextView title = new TextView(this);
        title.setText("Rizwan YT Native");
        title.setTextColor(Color.WHITE);
        title.setTextSize(28);
        title.setGravity(Gravity.START);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Native yt-dlp foundation · 360p single-video test");
        sub.setTextColor(Color.rgb(155, 166, 181));
        sub.setTextSize(14);
        sub.setPadding(0, dp(8), 0, dp(24));
        root.addView(sub);

        urlInput = new EditText(this);
        urlInput.setHint("Paste public YouTube video URL");
        urlInput.setHintTextColor(Color.rgb(115, 126, 140));
        urlInput.setTextColor(Color.WHITE);
        urlInput.setTextSize(16);
        urlInput.setSingleLine(true);
        urlInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        urlInput.setBackgroundColor(Color.rgb(20, 30, 42));
        urlInput.setPadding(dp(14), dp(14), dp(14), dp(14));
        root.addView(urlInput, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        downloadButton = new Button(this);
        downloadButton.setText("Download 360p with native yt-dlp");
        downloadButton.setEnabled(false);
        downloadButton.setOnClickListener(v -> startDownload());
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        bp.topMargin = dp(18);
        root.addView(downloadButton, bp);

        cancelButton = new Button(this);
        cancelButton.setText("Cancel active download");
        cancelButton.setEnabled(false);
        cancelButton.setOnClickListener(v -> cancelDownload());
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        cp.topMargin = dp(8);
        root.addView(cancelButton, cp);

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(16));
        pp.topMargin = dp(24);
        root.addView(progress, pp);

        status = new TextView(this);
        status.setText("Preparing native engine…");
        status.setTextColor(Color.rgb(210, 218, 229));
        status.setTextSize(15);
        status.setPadding(0, dp(18), 0, dp(12));
        status.setTextIsSelectable(true);
        root.addView(status);

        TextView note = new TextView(this);
        note.setText("Foundation scope: one public YouTube video, combined 360p when available. " +
                "No WebView URL replay, no Android DownloadManager, no 720p/1080p merge yet.");
        note.setTextColor(Color.rgb(132, 143, 157));
        note.setTextSize(13);
        root.addView(note);

        setContentView(scroll);
    }

    private void initEngine() {
        setStatus("Initializing bundled Python/yt-dlp engine… first launch may take a little longer.");
        executor.execute(() -> {
            try {
                YoutubeDL.getInstance().init(getApplicationContext());
                engineReady = true;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Native engine READY. Paste the same public YouTube link and tap Download 360p.");
                });
            } catch (Exception e) {
                runOnUiThread(() -> setStatus("ENGINE INIT FAILED\n" + safeMessage(e)));
            }
        });
    }

    private void startDownload() {
        String url = urlInput.getText().toString().trim();
        if (!engineReady) {
            Toast.makeText(this, "Native engine is not ready yet", Toast.LENGTH_SHORT).show();
            return;
        }
        if (!looksLikeYoutubeUrl(url)) {
            urlInput.setError("Paste a YouTube video URL");
            return;
        }
        if (!ensureStoragePermission()) return;

        File outDir = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES),
                "Rizwan Media Saver");
        if (!outDir.exists() && !outDir.mkdirs()) {
            setStatus("Could not create Movies/Rizwan Media Saver folder.");
            return;
        }

        processId = "rms-" + UUID.randomUUID();
        final String activeProcess = processId;
        downloadButton.setEnabled(false);
        cancelButton.setEnabled(true);
        progress.setProgress(0);
        setStatus("Resolving video with native yt-dlp…");

        executor.execute(() -> {
            try {
                YoutubeDLRequest request = new YoutubeDLRequest(url);
                request.addOption("--no-playlist");
                request.addOption("--no-mtime");
                request.addOption("--newline");
                request.addOption("-f", "18/best[height<=360][ext=mp4]/best[height<=360]");
                request.addOption("-o", new File(outDir,
                        "%(title).180B [%(id)s].%(ext)s").getAbsolutePath());

                Function3<Float, Long, String, Unit> callback = (pct, eta, line) -> {
                    int p = Math.max(0, Math.min(100, Math.round(pct)));
                    runOnUiThread(() -> {
                        progress.setProgress(p);
                        String etaText = eta != null && eta >= 0 ? (" · ETA " + eta + "s") : "";
                        setStatus(String.format(Locale.US,
                                "Downloading… %d%%%s\n%s",
                                p, etaText, line == null ? "" : line));
                    });
                    return Unit.INSTANCE;
                };

                YoutubeDL.getInstance().execute(request, activeProcess, callback);

                runOnUiThread(() -> {
                    progress.setProgress(100);
                    setStatus("DOWNLOAD COMPLETE\nSaved in Movies / Rizwan Media Saver");
                    downloadButton.setEnabled(true);
                    cancelButton.setEnabled(false);
                    processId = null;
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    setStatus("DOWNLOAD FAILED\n" + safeMessage(e));
                    downloadButton.setEnabled(true);
                    cancelButton.setEnabled(false);
                    processId = null;
                });
            }
        });
    }

    private void cancelDownload() {
        String id = processId;
        if (id == null) return;
        try {
            YoutubeDL.getInstance().destroyProcessById(id);
            setStatus("Cancel requested for active yt-dlp process.");
        } catch (Exception e) {
            setStatus("Cancel failed\n" + safeMessage(e));
        } finally {
            cancelButton.setEnabled(false);
            downloadButton.setEnabled(true);
        }
    }

    private boolean ensureStoragePermission() {
        if (Build.VERSION.SDK_INT >= 23 && Build.VERSION.SDK_INT <= 28) {
            if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, 701);
                return false;
            }
        }
        return true;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 701 && (grantResults.length == 0 || grantResults[0] != PackageManager.PERMISSION_GRANTED)) {
            setStatus("Storage permission is required to save the test video in Movies.");
        }
    }

    private boolean looksLikeYoutubeUrl(String url) {
        String s = url.toLowerCase(Locale.US);
        return (s.startsWith("http://") || s.startsWith("https://")) &&
                (s.contains("youtube.com/") || s.contains("youtu.be/"));
    }

    private String safeMessage(Throwable t) {
        String m = t.getMessage();
        return (m == null || m.trim().isEmpty()) ? t.toString() : m;
    }

    private void setStatus(String text) {
        status.setText(text);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
