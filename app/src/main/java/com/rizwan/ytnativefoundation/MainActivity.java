package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.MediaExtractor;
import android.media.MediaFormat;
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

import com.yausername.ffmpeg.FFmpeg;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import com.yausername.youtubedl_android.YoutubeDLResponse;

import java.io.File;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class MainActivity extends Activity {
    private static final String FINAL_MARKER = "__RMS_FINAL__";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private EditText urlInput;
    private TextView status;
    private ProgressBar progress;
    private Button downloadButton;
    private Button cancelButton;
    private Button quality360;
    private Button quality720;
    private Button quality1080;
    private volatile boolean engineReady = false;
    private volatile String processId = null;
    private volatile int selectedQuality = 360;

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
        sub.setText("v1.6.1 · HD audio merge + verification · Android 8.1 test");
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

        TextView qualityLabel = new TextView(this);
        qualityLabel.setText("Choose quality");
        qualityLabel.setTextColor(Color.WHITE);
        qualityLabel.setTextSize(16);
        qualityLabel.setPadding(0, dp(20), 0, dp(8));
        root.addView(qualityLabel);

        LinearLayout qualityRow = new LinearLayout(this);
        qualityRow.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(qualityRow, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        quality360 = new Button(this);
        quality720 = new Button(this);
        quality1080 = new Button(this);
        quality360.setOnClickListener(v -> selectQuality(360));
        quality720.setOnClickListener(v -> selectQuality(720));
        quality1080.setOnClickListener(v -> selectQuality(1080));

        LinearLayout.LayoutParams qp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        qualityRow.addView(quality360, qp);
        qualityRow.addView(quality720, qp);
        qualityRow.addView(quality1080, qp);
        updateQualityButtons();

        downloadButton = new Button(this);
        downloadButton.setText("Download 360p with audio");
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
        status.setText("Preparing native engine...");
        status.setTextColor(Color.rgb(210, 218, 229));
        status.setTextSize(15);
        status.setPadding(0, dp(18), 0, dp(12));
        status.setTextIsSelectable(true);
        root.addView(status);

        TextView note = new TextView(this);
        note.setText("360p keeps the proven v1.5.9 path. 720p and 1080p now require a separate audio stream, " +
                "merge with bundled FFmpeg, and verify that the final MP4 really contains an audio track before success is shown.");
        note.setTextColor(Color.rgb(132, 143, 157));
        note.setTextSize(13);
        root.addView(note);

        setContentView(scroll);
    }

    private void selectQuality(int quality) {
        if (processId != null) return;
        selectedQuality = quality;
        updateQualityButtons();
        if (downloadButton != null) {
            downloadButton.setText("Download " + quality + "p with audio");
        }
    }

    private void updateQualityButtons() {
        if (quality360 == null) return;
        quality360.setText(selectedQuality == 360 ? "360p\nSELECTED" : "360p");
        quality720.setText(selectedQuality == 720 ? "720p\nSELECTED" : "720p");
        quality1080.setText(selectedQuality == 1080 ? "1080p\nSELECTED" : "1080p");
    }

    private void setQualityButtonsEnabled(boolean enabled) {
        quality360.setEnabled(enabled);
        quality720.setEnabled(enabled);
        quality1080.setEnabled(enabled);
    }

    private void initEngine() {
        setStatus("Initializing Python/yt-dlp + FFmpeg...");
        executor.execute(() -> {
            String updateNote;
            try {
                YoutubeDL.getInstance().init(getApplicationContext());
                FFmpeg.getInstance().init(getApplicationContext());

                String before = YoutubeDL.getInstance().versionName(getApplicationContext());
                try {
                    runOnUiThread(() -> setStatus("Native engine loaded. Updating yt-dlp to latest nightly..."));
                    YoutubeDL.UpdateStatus updateStatus = YoutubeDL.getInstance().updateYoutubeDL(
                            getApplicationContext(), YoutubeDL.UpdateChannel._NIGHTLY);
                    String after = YoutubeDL.getInstance().versionName(getApplicationContext());
                    updateNote = "yt-dlp " + (after == null ? "updated" : after) + " · " +
                            (updateStatus == null ? "update checked" : updateStatus.toString());
                } catch (Exception updateError) {
                    String current = YoutubeDL.getInstance().versionName(getApplicationContext());
                    updateNote = "yt-dlp update failed; using " +
                            (current != null ? current : (before != null ? before : "bundled version")) +
                            "\n" + safeMessage(updateError);
                }

                final String readyText = updateNote;
                engineReady = true;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Native engine READY\n" + readyText +
                            "\nChoose 360p, 720p or 1080p and start download.");
                });
            } catch (Exception e) {
                runOnUiThread(() -> setStatus("ENGINE INIT FAILED\n" + safeMessage(e)));
            }
        });
    }

    private void startDownload() {
        String url = urlInput.getText().toString().trim();
        final int quality = selectedQuality;
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
        setQualityButtonsEnabled(false);
        progress.setProgress(0);
        setStatus("Resolving " + quality + "p video + playable audio...");

        executor.execute(() -> {
            try {
                YoutubeDLRequest request = new YoutubeDLRequest(url);
                request.addOption("--no-playlist");
                request.addOption("--no-mtime");
                request.addOption("--newline");
                request.addOption("--progress");
                request.addOption("--continue");
                request.addOption("--force-ipv4");
                request.addOption("--remote-components", "ejs:github");
                request.addOption("--js-runtimes", "quickjs");
                request.addOption("--extractor-args",
                        "youtube:player_client=default,-android_sdkless;formats=missing_pot");
                request.addOption("-f", formatSelectorFor(quality));
                request.addOption("--merge-output-format", "mp4");

                if (quality > 360) {
                    request.addOption("--postprocessor-args",
                            "Merger+ffmpeg_o:-c:v copy -c:a aac -b:a 192k");
                }

                request.addOption("--print", "after_move:" + FINAL_MARKER + "%(filepath)s");
                request.addOption("-o", new File(outDir,
                        "%(title).160B [%(id)s] [" + quality + "p].%(ext)s").getAbsolutePath());

                Function3<Float, Long, String, Unit> callback = (pct, eta, line) -> {
                    int p = Math.max(0, Math.min(100, Math.round(pct)));
                    String safeLine = line == null ? "" : line;
                    String lower = safeLine.toLowerCase(Locale.US);
                    boolean resuming = lower.contains("resuming download") ||
                            lower.contains("resume at") || lower.contains("continuing at");
                    boolean merging = lower.contains("[merger]") || lower.contains("merging formats");
                    runOnUiThread(() -> {
                        progress.setProgress(p);
                        String etaText = eta != null && eta >= 0 ? (" · ETA " + eta + "s") : "";
                        String phase;
                        if (merging) {
                            phase = "Merging video + audio...";
                        } else if (resuming) {
                            phase = "Resuming previous download...";
                        } else {
                            phase = "Downloading " + quality + "p video + audio...";
                        }
                        setStatus(String.format(Locale.US,
                                "%s %d%%%s\n%s",
                                phase, p, etaText, safeLine));
                    });
                    return Unit.INSTANCE;
                };

                YoutubeDLResponse response = YoutubeDL.getInstance().execute(request, activeProcess, callback);
                String finalPath = extractFinalPath(response.getOut());

                if (quality > 360) {
                    runOnUiThread(() -> setStatus("Download finished. Verifying final MP4 audio track..."));
                    if (finalPath == null || finalPath.trim().isEmpty()) {
                        throw new Exception("HD verification failed: final file path was not reported.");
                    }
                    File finalFile = new File(finalPath);
                    if (!finalFile.isFile()) {
                        throw new Exception("HD verification failed: final MP4 was not found.");
                    }
                    if (!hasAudioTrack(finalPath)) {
                        if (finalFile.exists()) finalFile.delete();
                        throw new Exception("HD verification failed: final MP4 has no audio track.");
                    }
                }

                final String savedPath = finalPath;
                runOnUiThread(() -> {
                    progress.setProgress(100);
                    String verified = quality > 360 ? "\nAudio track VERIFIED" : "";
                    String where = savedPath != null && !savedPath.trim().isEmpty()
                            ? "\n" + savedPath
                            : "\nSaved in Movies / Rizwan Media Saver";
                    setStatus("DOWNLOAD COMPLETE\n" + quality + "p video + audio" + verified + where);
                    restoreIdleUi();
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    setStatus("DOWNLOAD FAILED\n" + safeMessage(e));
                    restoreIdleUi();
                });
            }
        });
    }

    private String formatSelectorFor(int quality) {
        if (quality <= 360) {
            // Proven v1.5.9 path: keep this selector unchanged.
            return "18/" +
                    "best[height<=360][ext=mp4][vcodec^=avc1][acodec^=mp4a]/" +
                    "best[height<=360][ext=mp4][vcodec!=none][acodec!=none]/" +
                    "bestvideo[height<=360][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/" +
                    "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/" +
                    "best[height<=360][vcodec!=none][acodec!=none]/best";
        }

        // HD is deliberately strict: every valid branch contains both video AND audio.
        // There is no video-only or plain "best" fallback in v1.6.1.
        String q = String.valueOf(quality);
        return "bestvideo[height=" + q + "][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/" +
                "bestvideo[height=" + q + "][ext=mp4][vcodec^=avc1]+bestaudio/" +
                "bestvideo[height<=" + q + "][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/" +
                "bestvideo[height<=" + q + "][ext=mp4][vcodec^=avc1]+bestaudio/" +
                "bestvideo[height<=" + q + "][ext=mp4]+bestaudio[ext=m4a]/" +
                "bestvideo[height<=" + q + "][ext=mp4]+bestaudio";
    }

    private String extractFinalPath(String out) {
        if (out == null) return null;
        String[] lines = out.split("\\r?\\n");
        for (String line : lines) {
            String t = line.trim();
            if (t.startsWith(FINAL_MARKER)) {
                return t.substring(FINAL_MARKER.length()).trim();
            }
        }
        return null;
    }

    private boolean hasAudioTrack(String path) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try {
            extractor.setDataSource(path);
            for (int i = 0; i < extractor.getTrackCount(); i++) {
                MediaFormat format = extractor.getTrackFormat(i);
                String mime = format.getString(MediaFormat.KEY_MIME);
                if (mime != null && mime.startsWith("audio/")) {
                    return true;
                }
            }
            return false;
        } finally {
            extractor.release();
        }
    }

    private void restoreIdleUi() {
        downloadButton.setEnabled(true);
        cancelButton.setEnabled(false);
        setQualityButtonsEnabled(true);
        processId = null;
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
            setQualityButtonsEnabled(true);
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
        if (requestCode == 701 && (grantResults.length == 0 ||
                grantResults[0] != PackageManager.PERMISSION_GRANTED)) {
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
