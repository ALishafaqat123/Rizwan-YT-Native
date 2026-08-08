package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.net.Uri;
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

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
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
    private Button quality360;
    private Button quality720;
    private Button quality1080;
    private volatile boolean engineReady = false;
    private volatile String processId = null;
    private volatile Process ffmpegProcess = null;
    private volatile int selectedQuality = 360;
    private volatile String ffmpegSelfTest = "not tested";

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
        sub.setText("v1.6.2 · explicit HD audio download + manual FFmpeg merge");
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
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView qualityLabel = new TextView(this);
        qualityLabel.setText("Choose quality");
        qualityLabel.setTextColor(Color.WHITE);
        qualityLabel.setTextSize(16);
        qualityLabel.setPadding(0, dp(20), 0, dp(8));
        root.addView(qualityLabel);

        LinearLayout qualityRow = new LinearLayout(this);
        qualityRow.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(qualityRow, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        quality360 = new Button(this);
        quality720 = new Button(this);
        quality1080 = new Button(this);
        quality360.setOnClickListener(v -> selectQuality(360));
        quality720.setOnClickListener(v -> selectQuality(720));
        quality1080.setOnClickListener(v -> selectQuality(1080));

        LinearLayout.LayoutParams qp = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        qualityRow.addView(quality360, qp);
        qualityRow.addView(quality720, qp);
        qualityRow.addView(quality1080, qp);
        updateQualityButtons();

        downloadButton = new Button(this);
        downloadButton.setText("Download 360p with audio");
        downloadButton.setEnabled(false);
        downloadButton.setOnClickListener(v -> startDownload());
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        bp.topMargin = dp(18);
        root.addView(downloadButton, bp);

        cancelButton = new Button(this);
        cancelButton.setText("Cancel active download");
        cancelButton.setEnabled(false);
        cancelButton.setOnClickListener(v -> cancelDownload());
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
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
        status.setTextSize(14);
        status.setPadding(0, dp(18), 0, dp(12));
        status.setTextIsSelectable(true);
        root.addView(status);

        TextView note = new TextView(this);
        note.setText("360p keeps the proven v1.5.9 single-file path. For HD, video and M4A audio are downloaded separately into a private work folder, then bundled FFmpeg is run directly. Only a verified final MP4 is copied to Movies / Rizwan Media Saver.");
        note.setTextColor(Color.rgb(132, 143, 157));
        note.setTextSize(13);
        root.addView(note);

        setContentView(scroll);
    }

    private void selectQuality(int quality) {
        if (processId != null || ffmpegProcess != null) return;
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

                try {
                    ffmpegSelfTest = runFfmpegVersionTest();
                } catch (Exception ffErr) {
                    ffmpegSelfTest = "FAILED: " + safeMessage(ffErr);
                }

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
                final String ffText = ffmpegSelfTest;
                engineReady = true;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Native engine READY\n" + readyText +
                            "\nFFmpeg self-test: " + ffText +
                            "\nChoose 360p, 720p or 1080p.");
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

        downloadButton.setEnabled(false);
        cancelButton.setEnabled(true);
        setQualityButtonsEnabled(false);
        progress.setProgress(0);

        if (quality <= 360) {
            start360Download(url, outDir);
        } else {
            startHdDownload(url, quality, outDir);
        }
    }

    private void start360Download(String url, File outDir) {
        final String activeProcess = "rms360-" + UUID.randomUUID();
        processId = activeProcess;
        setStatus("Starting proven 360p video + audio path...");

        executor.execute(() -> {
            try {
                YoutubeDLRequest request = commonRequest(url);
                request.addOption("-f", "18/" +
                        "best[height<=360][ext=mp4][vcodec^=avc1][acodec^=mp4a]/" +
                        "best[height<=360][ext=mp4][vcodec!=none][acodec!=none]/" +
                        "bestvideo[height<=360][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/" +
                        "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/" +
                        "best[height<=360][vcodec!=none][acodec!=none]/best");
                request.addOption("--merge-output-format", "mp4");
                request.addOption("-o", new File(outDir,
                        "%(title).180B [%(id)s] [360p].%(ext)s").getAbsolutePath());

                YoutubeDL.getInstance().execute(request, activeProcess,
                        progressCallback(0, 100, "Downloading 360p video + audio..."));

                runOnUiThread(() -> {
                    progress.setProgress(100);
                    setStatus("DOWNLOAD COMPLETE\n360p video + audio\nSaved in Movies / Rizwan Media Saver");
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

    private void startHdDownload(String url, int quality, File outDir) {
        String videoId = getYoutubeId(url);
        if (videoId == null || videoId.isEmpty()) {
            videoId = Integer.toHexString(url.hashCode());
        }
        final String safeId = sanitize(videoId);
        final File workRoot = new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "hd-work");
        final File workDir = new File(workRoot, safeId + "-" + quality + "p");
        if (!workDir.exists()) workDir.mkdirs();

        final File finalFile = new File(outDir,
                "YouTube [" + safeId + "] [" + quality + "p].mp4");
        setStatus("HD stage 1/3: downloading " + quality + "p video stream...");

        executor.execute(() -> {
            try {
                String videoPid = "rms-hd-video-" + safeId + "-" + quality;
                processId = videoPid;
                YoutubeDLRequest videoReq = commonRequest(url);
                videoReq.addOption("-f",
                        "bestvideo[height<=" + quality + "][ext=mp4][vcodec^=avc1]/" +
                        "bestvideo[height<=" + quality + "][ext=mp4]");
                videoReq.addOption("-o", new File(workDir, "video.%(ext)s").getAbsolutePath());
                YoutubeDL.getInstance().execute(videoReq, videoPid,
                        progressCallback(0, 78, "HD stage 1/3: downloading video..."));
                processId = null;

                File videoFile = findCompleteFile(workDir, "video.");
                if (videoFile == null) {
                    throw new Exception("Video stage finished but the video file was not found.\n" + listFiles(workDir));
                }

                runOnUiThread(() -> setStatus("HD stage 2/3: downloading M4A/AAC audio stream..."));
                String audioPid = "rms-hd-audio-" + safeId + "-" + quality;
                processId = audioPid;
                YoutubeDLRequest audioReq = commonRequest(url);
                audioReq.addOption("-f", "bestaudio[ext=m4a][acodec^=mp4a]/bestaudio[ext=m4a]");
                audioReq.addOption("-o", new File(workDir, "audio.%(ext)s").getAbsolutePath());
                YoutubeDL.getInstance().execute(audioReq, audioPid,
                        progressCallback(78, 95, "HD stage 2/3: downloading audio..."));
                processId = null;

                File audioFile = findCompleteFile(workDir, "audio.");
                if (audioFile == null) {
                    throw new Exception("Audio stage finished but the M4A file was not found.\n" + listFiles(workDir));
                }
                if (!hasAudioTrack(audioFile.getAbsolutePath())) {
                    throw new Exception("Downloaded audio file has no audio track: " + audioFile.getName());
                }

                runOnUiThread(() -> {
                    progress.setProgress(96);
                    setStatus("HD stage 3/3: merging video + audio with bundled FFmpeg...");
                });

                if (finalFile.exists() && !finalFile.delete()) {
                    throw new Exception("Could not replace the old final MP4: " + finalFile.getAbsolutePath());
                }

                String mergeLog = mergeWithFfmpeg(videoFile, audioFile, finalFile);
                if (!finalFile.isFile() || finalFile.length() <= 0) {
                    throw new Exception("FFmpeg did not create the final MP4.\nFFmpeg self-test: " +
                            ffmpegSelfTest + "\n\nFFmpeg log:\n" + tail(mergeLog, 5000) +
                            "\n\nWork files:\n" + listFiles(workDir));
                }
                if (!hasAudioTrack(finalFile.getAbsolutePath())) {
                    finalFile.delete();
                    throw new Exception("Merged MP4 still has no audio track.\nFFmpeg log:\n" +
                            tail(mergeLog, 5000));
                }

                deleteWorkFiles(workDir);
                runOnUiThread(() -> {
                    progress.setProgress(100);
                    setStatus("DOWNLOAD COMPLETE\n" + quality + "p video + audio\nAudio track VERIFIED\n" +
                            finalFile.getAbsolutePath());
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

    private YoutubeDLRequest commonRequest(String url) {
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
        return request;
    }

    private Function3<Float, Long, String, Unit> progressCallback(
            int start, int end, String label) {
        return (pct, eta, line) -> {
            float raw = pct == null || pct < 0 ? 0 : Math.min(100f, pct);
            int scaled = start + Math.round((end - start) * (raw / 100f));
            String safeLine = line == null ? "" : line;
            String lower = safeLine.toLowerCase(Locale.US);
            boolean resuming = lower.contains("resuming download") ||
                    lower.contains("resume at") || lower.contains("continuing at");
            runOnUiThread(() -> {
                progress.setProgress(Math.max(start, Math.min(end, scaled)));
                String etaText = eta != null && eta >= 0 ? (" · ETA " + eta + "s") : "";
                String phase = resuming ? "Resuming previous download..." : label;
                setStatus(phase + " " + Math.round(raw) + "%" + etaText + "\n" + safeLine);
            });
            return Unit.INSTANCE;
        };
    }

    private String runFfmpegVersionTest() throws Exception {
        File ffmpeg = getFfmpegBinary();
        if (!ffmpeg.isFile()) {
            throw new Exception("libffmpeg.so missing at " + ffmpeg.getAbsolutePath());
        }
        List<String> cmd = new ArrayList<>();
        cmd.add(ffmpeg.getAbsolutePath());
        cmd.add("-version");
        ProcessBuilder pb = new ProcessBuilder(cmd).redirectErrorStream(true);
        applyFfmpegEnvironment(pb);
        Process p = pb.start();
        String out = readProcessOutput(p);
        int code = p.waitFor();
        if (code != 0) {
            throw new Exception("exit " + code + ": " + tail(out, 1000));
        }
        String first = out == null ? "" : out.trim();
        int nl = first.indexOf('\n');
        if (nl > 0) first = first.substring(0, nl).trim();
        return first.isEmpty() ? "PASS" : first;
    }

    private String mergeWithFfmpeg(File video, File audio, File output) throws Exception {
        File ffmpeg = getFfmpegBinary();
        List<String> cmd = new ArrayList<>();
        cmd.add(ffmpeg.getAbsolutePath());
        cmd.add("-y");
        cmd.add("-i");
        cmd.add(video.getAbsolutePath());
        cmd.add("-i");
        cmd.add(audio.getAbsolutePath());
        cmd.add("-map");
        cmd.add("0:v:0");
        cmd.add("-map");
        cmd.add("1:a:0");
        cmd.add("-c:v");
        cmd.add("copy");
        cmd.add("-c:a");
        cmd.add("copy");
        cmd.add("-movflags");
        cmd.add("+faststart");
        cmd.add(output.getAbsolutePath());

        ProcessBuilder pb = new ProcessBuilder(cmd).redirectErrorStream(true);
        applyFfmpegEnvironment(pb);
        Process p = pb.start();
        ffmpegProcess = p;
        String log = readProcessOutput(p);
        int code = p.waitFor();
        ffmpegProcess = null;
        if (code != 0) {
            if (output.exists()) output.delete();
            throw new Exception("FFmpeg merge failed (exit " + code + ").\n" + tail(log, 5000));
        }
        return log;
    }

    private File getFfmpegBinary() {
        ApplicationInfo ai = getApplicationInfo();
        return new File(ai.nativeLibraryDir, "libffmpeg.so");
    }

    private void applyFfmpegEnvironment(ProcessBuilder pb) {
        File base = new File(getNoBackupFilesDir(), "youtubedl-android/packages");
        File ffLib = new File(base, "ffmpeg/usr/lib");
        File pyLib = new File(base, "python/usr/lib");
        String oldLd = System.getenv("LD_LIBRARY_PATH");
        String ld = pyLib.getAbsolutePath() + ":" + ffLib.getAbsolutePath() +
                ":" + getApplicationInfo().nativeLibraryDir;
        if (oldLd != null && !oldLd.isEmpty()) ld += ":" + oldLd;
        pb.environment().put("LD_LIBRARY_PATH", ld);
        pb.environment().put("TMPDIR", getCacheDir().getAbsolutePath());
    }

    private String readProcessOutput(Process p) throws Exception {
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line).append('\n');
            }
        }
        return sb.toString();
    }

    private File findCompleteFile(File dir, String prefix) {
        File[] files = dir.listFiles();
        if (files == null) return null;
        File best = null;
        for (File f : files) {
            String n = f.getName();
            if (!f.isFile() || !n.startsWith(prefix) || n.endsWith(".part") ||
                    n.endsWith(".ytdl") || f.length() <= 0) continue;
            if (best == null || f.lastModified() > best.lastModified()) best = f;
        }
        return best;
    }

    private String listFiles(File dir) {
        File[] files = dir.listFiles();
        if (files == null || files.length == 0) return "(no work files)";
        StringBuilder sb = new StringBuilder();
        for (File f : files) {
            sb.append(f.getName()).append(" · ").append(f.length()).append(" bytes\n");
        }
        return sb.toString().trim();
    }

    private void deleteWorkFiles(File dir) {
        File[] files = dir.listFiles();
        if (files != null) {
            for (File f : files) f.delete();
        }
        dir.delete();
    }

    private boolean hasAudioTrack(String path) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try {
            extractor.setDataSource(path);
            for (int i = 0; i < extractor.getTrackCount(); i++) {
                MediaFormat format = extractor.getTrackFormat(i);
                String mime = format.getString(MediaFormat.KEY_MIME);
                if (mime != null && mime.startsWith("audio/")) return true;
            }
            return false;
        } finally {
            extractor.release();
        }
    }

    private String getYoutubeId(String value) {
        try {
            Uri uri = Uri.parse(value);
            String host = uri.getHost();
            if (host == null) return null;
            host = host.toLowerCase(Locale.US);
            if (host.contains("youtu.be")) {
                List<String> seg = uri.getPathSegments();
                return seg.isEmpty() ? null : seg.get(0);
            }
            if (host.contains("youtube.com")) {
                String v = uri.getQueryParameter("v");
                if (v != null && !v.isEmpty()) return v;
                List<String> seg = uri.getPathSegments();
                if (seg.size() >= 2 && ("shorts".equals(seg.get(0)) ||
                        "embed".equals(seg.get(0)) || "live".equals(seg.get(0)))) {
                    return seg.get(1);
                }
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private String sanitize(String s) {
        if (s == null) return "video";
        return s.replaceAll("[^A-Za-z0-9_-]", "_");
    }

    private String tail(String text, int maxChars) {
        if (text == null) return "";
        if (text.length() <= maxChars) return text;
        return "...\n" + text.substring(text.length() - maxChars);
    }

    private void restoreIdleUi() {
        processId = null;
        ffmpegProcess = null;
        downloadButton.setEnabled(true);
        cancelButton.setEnabled(false);
        setQualityButtonsEnabled(true);
    }

    private void cancelDownload() {
        String id = processId;
        if (id != null) {
            try {
                YoutubeDL.getInstance().destroyProcessById(id);
            } catch (Exception ignored) {
            }
        }
        Process fp = ffmpegProcess;
        if (fp != null) {
            try {
                fp.destroy();
            } catch (Exception ignored) {
            }
        }
        setStatus("Cancel requested.");
        restoreIdleUi();
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
