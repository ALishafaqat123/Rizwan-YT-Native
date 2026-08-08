package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.MediaCodec;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMuxer;
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

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
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
        sub.setText("v1.6.3 · Android MediaMuxer HD audio merge · Android 8.1");
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
        note.setText("360p keeps the proven v1.5.9 single-file path. For 720p/1080p, H.264 MP4 video and AAC/M4A audio are downloaded separately, then Android's own MediaMuxer joins them into one verified MP4. FFmpeg is not used for HD merging.");
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
        setStatus("Initializing Python/yt-dlp + Android MediaMuxer...");
        executor.execute(() -> {
            String updateNote;
            try {
                YoutubeDL.getInstance().init(getApplicationContext());

                // Keep the bundled package available for the proven 360p fallback path,
                // but HD merging in v1.6.3 does NOT execute FFmpeg.
                try {
                    FFmpeg.getInstance().init(getApplicationContext());
                } catch (Exception ignored) {
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
                engineReady = true;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Native engine READY\n" + readyText +
                            "\nAndroid MediaMuxer READY (API " + Build.VERSION.SDK_INT + ")" +
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
                processId = null;

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

        final File mergedTemp = new File(workDir, "merged-final.mp4");
        final File finalFile = new File(outDir,
                "YouTube [" + safeId + "] [" + quality + "p].mp4");

        setStatus("HD stage 1/3: downloading " + quality + "p H.264 video stream...");

        executor.execute(() -> {
            try {
                String videoPid = "rms-hd-video-" + safeId + "-" + quality;
                processId = videoPid;
                YoutubeDLRequest videoReq = commonRequest(url);
                videoReq.addOption("-f",
                        "bestvideo[height<=" + quality + "][ext=mp4][vcodec^=avc1]");
                videoReq.addOption("-o", new File(workDir, "video.%(ext)s").getAbsolutePath());
                YoutubeDL.getInstance().execute(videoReq, videoPid,
                        progressCallback(0, 78, "HD stage 1/3: downloading H.264 video..."));
                processId = null;

                File videoFile = findCompleteFile(workDir, "video.");
                if (videoFile == null) {
                    throw new Exception("Video stage finished but the H.264 MP4 file was not found.\n" + listFiles(workDir));
                }
                if (!hasVideoTrack(videoFile.getAbsolutePath())) {
                    throw new Exception("Downloaded video file has no video track: " + videoFile.getName());
                }

                runOnUiThread(() -> setStatus("HD stage 2/3: downloading AAC/M4A audio stream..."));
                String audioPid = "rms-hd-audio-" + safeId + "-" + quality;
                processId = audioPid;
                YoutubeDLRequest audioReq = commonRequest(url);
                audioReq.addOption("-f", "bestaudio[ext=m4a][acodec^=mp4a]");
                audioReq.addOption("-o", new File(workDir, "audio.%(ext)s").getAbsolutePath());
                YoutubeDL.getInstance().execute(audioReq, audioPid,
                        progressCallback(78, 95, "HD stage 2/3: downloading AAC audio..."));
                processId = null;

                File audioFile = findCompleteFile(workDir, "audio.");
                if (audioFile == null) {
                    throw new Exception("Audio stage finished but the AAC/M4A file was not found.\n" + listFiles(workDir));
                }
                if (!hasAudioTrack(audioFile.getAbsolutePath())) {
                    throw new Exception("Downloaded audio file has no audio track: " + audioFile.getName());
                }

                runOnUiThread(() -> {
                    progress.setProgress(96);
                    cancelButton.setEnabled(false);
                    setStatus("HD stage 3/3: joining H.264 video + AAC audio with Android MediaMuxer...");
                });

                if (mergedTemp.exists()) mergedTemp.delete();
                muxWithAndroid(videoFile, audioFile, mergedTemp);

                if (!mergedTemp.isFile() || mergedTemp.length() <= 0) {
                    throw new Exception("Android MediaMuxer did not create the merged MP4.\n" + listFiles(workDir));
                }
                if (!hasVideoTrack(mergedTemp.getAbsolutePath())) {
                    throw new Exception("Merged MP4 has no video track.");
                }
                if (!hasAudioTrack(mergedTemp.getAbsolutePath())) {
                    throw new Exception("Merged MP4 has no audio track.");
                }

                runOnUiThread(() -> {
                    progress.setProgress(99);
                    setStatus("HD merge complete. Verifying and saving final MP4...");
                });

                if (finalFile.exists() && !finalFile.delete()) {
                    throw new Exception("Could not replace the old final MP4: " + finalFile.getAbsolutePath());
                }
                moveOrCopy(mergedTemp, finalFile);

                if (!finalFile.isFile() || finalFile.length() <= 0 ||
                        !hasVideoTrack(finalFile.getAbsolutePath()) ||
                        !hasAudioTrack(finalFile.getAbsolutePath())) {
                    if (finalFile.exists()) finalFile.delete();
                    throw new Exception("Final saved MP4 verification failed.");
                }

                deleteWorkFiles(workDir);
                runOnUiThread(() -> {
                    progress.setProgress(100);
                    setStatus("DOWNLOAD COMPLETE\n" + quality + "p video + audio\nAudio track VERIFIED\nAndroid MediaMuxer PASS\n" +
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

    private void muxWithAndroid(File videoFile, File audioFile, File outputFile) throws Exception {
        MediaExtractor videoExtractor = new MediaExtractor();
        MediaExtractor audioExtractor = new MediaExtractor();
        MediaMuxer muxer = null;
        boolean muxerStarted = false;

        try {
            videoExtractor.setDataSource(videoFile.getAbsolutePath());
            audioExtractor.setDataSource(audioFile.getAbsolutePath());

            int videoSourceTrack = findTrack(videoExtractor, "video/");
            int audioSourceTrack = findTrack(audioExtractor, "audio/");
            if (videoSourceTrack < 0) throw new Exception("MediaMuxer input video track not found.");
            if (audioSourceTrack < 0) throw new Exception("MediaMuxer input audio track not found.");

            MediaFormat videoFormat = videoExtractor.getTrackFormat(videoSourceTrack);
            MediaFormat audioFormat = audioExtractor.getTrackFormat(audioSourceTrack);
            String videoMime = videoFormat.getString(MediaFormat.KEY_MIME);
            String audioMime = audioFormat.getString(MediaFormat.KEY_MIME);

            if (videoMime == null || !"video/avc".equalsIgnoreCase(videoMime)) {
                throw new Exception("MediaMuxer requires H.264/AVC video, got: " + videoMime);
            }
            if (audioMime == null || !audioMime.toLowerCase(Locale.US).startsWith("audio/mp4a")) {
                throw new Exception("MediaMuxer requires AAC/M4A audio, got: " + audioMime);
            }

            if (outputFile.exists() && !outputFile.delete()) {
                throw new Exception("Could not replace temporary merged MP4.");
            }

            muxer = new MediaMuxer(outputFile.getAbsolutePath(),
                    MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);

            if (videoFormat.containsKey(MediaFormat.KEY_ROTATION)) {
                int rotation = videoFormat.getInteger(MediaFormat.KEY_ROTATION);
                if (rotation == 90 || rotation == 180 || rotation == 270) {
                    muxer.setOrientationHint(rotation);
                }
            }

            int videoMuxTrack = muxer.addTrack(videoFormat);
            int audioMuxTrack = muxer.addTrack(audioFormat);

            videoExtractor.selectTrack(videoSourceTrack);
            audioExtractor.selectTrack(audioSourceTrack);
            muxer.start();
            muxerStarted = true;

            int bufferSize = Math.max(8 * 1024 * 1024,
                    Math.max(maxInputSize(videoFormat), maxInputSize(audioFormat)) + 1024);
            ByteBuffer buffer = ByteBuffer.allocate(bufferSize);
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();

            long videoTime = videoExtractor.getSampleTime();
            long audioTime = audioExtractor.getSampleTime();

            while (videoTime >= 0 || audioTime >= 0) {
                boolean useVideo = audioTime < 0 ||
                        (videoTime >= 0 && videoTime <= audioTime);
                MediaExtractor extractor = useVideo ? videoExtractor : audioExtractor;
                int muxTrack = useVideo ? videoMuxTrack : audioMuxTrack;

                buffer.clear();
                int sampleSize = extractor.readSampleData(buffer, 0);
                if (sampleSize < 0) {
                    if (useVideo) videoTime = -1;
                    else audioTime = -1;
                    continue;
                }

                long sampleTime = extractor.getSampleTime();
                int sampleFlags = extractor.getSampleFlags();
                info.set(0, sampleSize, sampleTime, sampleFlags);
                muxer.writeSampleData(muxTrack, buffer, info);
                extractor.advance();

                if (useVideo) videoTime = videoExtractor.getSampleTime();
                else audioTime = audioExtractor.getSampleTime();
            }

            muxer.stop();
            muxerStarted = false;
        } finally {
            try {
                videoExtractor.release();
            } catch (Exception ignored) {
            }
            try {
                audioExtractor.release();
            } catch (Exception ignored) {
            }
            if (muxer != null) {
                if (muxerStarted) {
                    try {
                        muxer.stop();
                    } catch (Exception ignored) {
                    }
                }
                try {
                    muxer.release();
                } catch (Exception ignored) {
                }
            }
        }
    }

    private int findTrack(MediaExtractor extractor, String mimePrefix) {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            MediaFormat format = extractor.getTrackFormat(i);
            String mime = format.getString(MediaFormat.KEY_MIME);
            if (mime != null && mime.startsWith(mimePrefix)) return i;
        }
        return -1;
    }

    private int maxInputSize(MediaFormat format) {
        try {
            if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                return Math.max(0, format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE));
            }
        } catch (Exception ignored) {
        }
        return 0;
    }

    private void moveOrCopy(File source, File destination) throws Exception {
        if (source.renameTo(destination)) return;

        try (BufferedInputStream in = new BufferedInputStream(new FileInputStream(source));
             BufferedOutputStream out = new BufferedOutputStream(new FileOutputStream(destination))) {
            byte[] buf = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buf)) != -1) {
                out.write(buf, 0, read);
            }
            out.flush();
        }

        if (!destination.isFile() || destination.length() != source.length()) {
            if (destination.exists()) destination.delete();
            throw new Exception("Could not copy merged MP4 to Movies folder.");
        }
        source.delete();
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
            return findTrack(extractor, "audio/") >= 0;
        } finally {
            extractor.release();
        }
    }

    private boolean hasVideoTrack(String path) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try {
            extractor.setDataSource(path);
            return findTrack(extractor, "video/") >= 0;
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

    private void restoreIdleUi() {
        processId = null;
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
