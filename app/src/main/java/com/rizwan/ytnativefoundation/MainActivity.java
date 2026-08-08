package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
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
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.yausername.ffmpeg.FFmpeg;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import com.yausername.youtubedl_android.mapper.VideoInfo;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class MainActivity extends Activity {
    private static final int BG = Color.rgb(7, 12, 18);
    private static final int SURFACE = Color.rgb(16, 24, 33);
    private static final int SURFACE_2 = Color.rgb(24, 34, 45);
    private static final int TEXT = Color.rgb(244, 248, 251);
    private static final int MUTED = Color.rgb(147, 160, 176);
    private static final int ACCENT = Color.rgb(39, 213, 154);
    private static final int ACCENT_DARK = Color.rgb(15, 92, 69);

    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    private EditText urlInput;
    private TextView status;
    private ProgressBar progress;
    private Button downloadButton;
    private Button cancelButton;
    private Button quality360;
    private Button quality720;
    private Button quality1080;
    private Button homeTabButton;
    private Button downloadsTabButton;
    private Button analyzeButton;
    private LinearLayout homeSection;
    private LinearLayout downloadsSection;
    private LinearLayout downloadsContainer;
    private LinearLayout previewCard;
    private ImageView previewImage;
    private TextView previewTitle;
    private TextView previewMeta;
    private TextView downloadsCount;

    private volatile boolean engineReady = false;
    private volatile String processId = null;
    private volatile int selectedQuality = 360;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        buildUi();
        ensureStoragePermission();
        initEngine();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(22), dp(18), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));

        LinearLayout brandRow = new LinearLayout(this);
        brandRow.setOrientation(LinearLayout.HORIZONTAL);
        brandRow.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(brandRow, fullWrap());

        TextView logo = new TextView(this);
        logo.setText("R");
        logo.setGravity(Gravity.CENTER);
        logo.setTextColor(Color.rgb(6, 22, 17));
        logo.setTextSize(24);
        logo.setTypeface(Typeface.DEFAULT_BOLD);
        logo.setBackground(roundBg(ACCENT, ACCENT, 18));
        LinearLayout.LayoutParams logoLp = new LinearLayout.LayoutParams(dp(54), dp(54));
        brandRow.addView(logo, logoLp);

        LinearLayout brandText = new LinearLayout(this);
        brandText.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams brandLp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        brandLp.leftMargin = dp(13);
        brandRow.addView(brandText, brandLp);

        TextView title = new TextView(this);
        title.setText("Rizwan Media Saver");
        title.setTextColor(TEXT);
        title.setTextSize(25);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        brandText.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Private downloader  •  No ads  •  v1.7.0");
        sub.setTextColor(MUTED);
        sub.setTextSize(13);
        sub.setPadding(0, dp(4), 0, 0);
        brandText.addView(sub);

        TextView engineBadge = new TextView(this);
        engineBadge.setText("360p • 720p • 1080p");
        engineBadge.setTextColor(Color.rgb(116, 226, 189));
        engineBadge.setTextSize(12);
        engineBadge.setPadding(dp(12), dp(7), dp(12), dp(7));
        engineBadge.setBackground(roundBg(Color.rgb(12, 44, 35), Color.rgb(24, 92, 69), 16));
        LinearLayout.LayoutParams badgeLp = fullWrap();
        badgeLp.topMargin = dp(18);
        root.addView(engineBadge, badgeLp);

        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setPadding(dp(4), dp(4), dp(4), dp(4));
        tabs.setBackground(roundBg(SURFACE, Color.rgb(32, 43, 56), 16));
        LinearLayout.LayoutParams tabsLp = fullWrap();
        tabsLp.topMargin = dp(18);
        root.addView(tabs, tabsLp);

        homeTabButton = new Button(this);
        downloadsTabButton = new Button(this);
        homeTabButton.setText("Home");
        downloadsTabButton.setText("Downloads");
        homeTabButton.setAllCaps(false);
        downloadsTabButton.setAllCaps(false);
        homeTabButton.setTextSize(15);
        downloadsTabButton.setTextSize(15);
        homeTabButton.setTypeface(Typeface.DEFAULT_BOLD);
        downloadsTabButton.setTypeface(Typeface.DEFAULT_BOLD);
        LinearLayout.LayoutParams tabLp1 = new LinearLayout.LayoutParams(0, dp(48), 1f);
        LinearLayout.LayoutParams tabLp2 = new LinearLayout.LayoutParams(0, dp(48), 1f);
        tabs.addView(homeTabButton, tabLp1);
        tabs.addView(downloadsTabButton, tabLp2);
        homeTabButton.setOnClickListener(v -> showTab(true));
        downloadsTabButton.setOnClickListener(v -> showTab(false));

        homeSection = new LinearLayout(this);
        homeSection.setOrientation(LinearLayout.VERTICAL);
        root.addView(homeSection, fullWrap());

        downloadsSection = new LinearLayout(this);
        downloadsSection.setOrientation(LinearLayout.VERTICAL);
        downloadsSection.setVisibility(View.GONE);
        root.addView(downloadsSection, fullWrap());

        buildHomeSection();
        buildDownloadsSection();
        showTab(true);
        setContentView(scroll);
    }

    private void buildHomeSection() {
        LinearLayout linkCard = new LinearLayout(this);
        linkCard.setOrientation(LinearLayout.VERTICAL);
        linkCard.setPadding(dp(16), dp(17), dp(16), dp(16));
        linkCard.setBackground(roundBg(SURFACE, Color.rgb(32, 44, 57), 20));
        LinearLayout.LayoutParams cardLp = fullWrap();
        cardLp.topMargin = dp(18);
        homeSection.addView(linkCard, cardLp);

        TextView linkTitle = sectionTitle("Paste a YouTube link");
        linkCard.addView(linkTitle);
        TextView linkSub = smallText("We only use the link to read video info and download your selected quality.");
        linkSub.setPadding(0, dp(5), 0, dp(13));
        linkCard.addView(linkSub);

        LinearLayout linkRow = new LinearLayout(this);
        linkRow.setOrientation(LinearLayout.HORIZONTAL);
        linkRow.setGravity(Gravity.CENTER_VERTICAL);
        linkCard.addView(linkRow, fullWrap());

        urlInput = new EditText(this);
        urlInput.setHint("https://youtube.com/...");
        urlInput.setHintTextColor(Color.rgb(105, 119, 136));
        urlInput.setTextColor(TEXT);
        urlInput.setTextSize(15);
        urlInput.setSingleLine(true);
        urlInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        urlInput.setPadding(dp(14), dp(13), dp(14), dp(13));
        urlInput.setBackground(roundBg(SURFACE_2, Color.rgb(42, 57, 72), 14));
        LinearLayout.LayoutParams inputLp = new LinearLayout.LayoutParams(0, dp(52), 1f);
        linkRow.addView(urlInput, inputLp);

        Button pasteButton = new Button(this);
        pasteButton.setText("Paste");
        pasteButton.setAllCaps(false);
        pasteButton.setTextSize(14);
        pasteButton.setTypeface(Typeface.DEFAULT_BOLD);
        pasteButton.setTextColor(Color.rgb(7, 31, 23));
        pasteButton.setBackground(roundBg(ACCENT, ACCENT, 14));
        LinearLayout.LayoutParams pasteLp = new LinearLayout.LayoutParams(dp(88), dp(52));
        pasteLp.leftMargin = dp(9);
        linkRow.addView(pasteButton, pasteLp);
        pasteButton.setOnClickListener(v -> pasteFromClipboard());

        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams actionLp = fullWrap();
        actionLp.topMargin = dp(10);
        linkCard.addView(actionRow, actionLp);

        analyzeButton = new Button(this);
        analyzeButton.setText("Analyze link");
        analyzeButton.setAllCaps(false);
        analyzeButton.setTextSize(14);
        analyzeButton.setTextColor(TEXT);
        analyzeButton.setTypeface(Typeface.DEFAULT_BOLD);
        analyzeButton.setBackground(roundBg(Color.rgb(28, 70, 58), Color.rgb(38, 110, 84), 14));
        LinearLayout.LayoutParams analyzeLp = new LinearLayout.LayoutParams(0, dp(46), 1f);
        actionRow.addView(analyzeButton, analyzeLp);
        analyzeButton.setOnClickListener(v -> analyzeLink());

        Button clearButton = new Button(this);
        clearButton.setText("Clear");
        clearButton.setAllCaps(false);
        clearButton.setTextSize(14);
        clearButton.setTextColor(Color.rgb(211, 219, 228));
        clearButton.setBackground(roundBg(Color.rgb(32, 39, 49), Color.rgb(50, 61, 74), 14));
        LinearLayout.LayoutParams clearLp = new LinearLayout.LayoutParams(dp(92), dp(46));
        clearLp.leftMargin = dp(9);
        actionRow.addView(clearButton, clearLp);
        clearButton.setOnClickListener(v -> clearPreview());

        previewCard = new LinearLayout(this);
        previewCard.setOrientation(LinearLayout.VERTICAL);
        previewCard.setPadding(dp(12), dp(12), dp(12), dp(13));
        previewCard.setBackground(roundBg(Color.rgb(13, 21, 29), Color.rgb(37, 52, 66), 18));
        previewCard.setVisibility(View.GONE);
        LinearLayout.LayoutParams previewLp = fullWrap();
        previewLp.topMargin = dp(14);
        homeSection.addView(previewCard, previewLp);

        previewImage = new ImageView(this);
        previewImage.setScaleType(ImageView.ScaleType.CENTER_CROP);
        previewImage.setBackground(roundBg(Color.rgb(25, 34, 44), Color.rgb(25, 34, 44), 14));
        previewCard.addView(previewImage, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(178)));

        previewTitle = new TextView(this);
        previewTitle.setTextColor(TEXT);
        previewTitle.setTextSize(17);
        previewTitle.setTypeface(Typeface.DEFAULT_BOLD);
        previewTitle.setPadding(dp(3), dp(12), dp(3), 0);
        previewCard.addView(previewTitle);

        previewMeta = new TextView(this);
        previewMeta.setTextColor(MUTED);
        previewMeta.setTextSize(13);
        previewMeta.setPadding(dp(3), dp(5), dp(3), 0);
        previewCard.addView(previewMeta);

        TextView qualityLabel = sectionTitle("Choose quality");
        qualityLabel.setPadding(0, dp(20), 0, dp(9));
        homeSection.addView(qualityLabel);

        LinearLayout qualityRow = new LinearLayout(this);
        qualityRow.setOrientation(LinearLayout.HORIZONTAL);
        homeSection.addView(qualityRow, fullWrap());

        quality360 = qualityButton("360p", "SD");
        quality720 = qualityButton("720p", "HD");
        quality1080 = qualityButton("1080p", "FULL HD");
        quality360.setOnClickListener(v -> selectQuality(360));
        quality720.setOnClickListener(v -> selectQuality(720));
        quality1080.setOnClickListener(v -> selectQuality(1080));

        LinearLayout.LayoutParams q1 = new LinearLayout.LayoutParams(0, dp(70), 1f);
        LinearLayout.LayoutParams q2 = new LinearLayout.LayoutParams(0, dp(70), 1f);
        LinearLayout.LayoutParams q3 = new LinearLayout.LayoutParams(0, dp(70), 1f);
        q2.leftMargin = dp(8);
        q3.leftMargin = dp(8);
        qualityRow.addView(quality360, q1);
        qualityRow.addView(quality720, q2);
        qualityRow.addView(quality1080, q3);
        updateQualityButtons();

        downloadButton = new Button(this);
        downloadButton.setText("Download 360p");
        downloadButton.setAllCaps(false);
        downloadButton.setTextSize(17);
        downloadButton.setTypeface(Typeface.DEFAULT_BOLD);
        downloadButton.setTextColor(Color.rgb(6, 28, 21));
        downloadButton.setBackground(roundBg(ACCENT, ACCENT, 16));
        downloadButton.setEnabled(false);
        downloadButton.setOnClickListener(v -> startDownload());
        LinearLayout.LayoutParams dlLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(58));
        dlLp.topMargin = dp(16);
        homeSection.addView(downloadButton, dlLp);

        cancelButton = new Button(this);
        cancelButton.setText("Cancel active download");
        cancelButton.setAllCaps(false);
        cancelButton.setTextSize(14);
        cancelButton.setTextColor(Color.rgb(217, 224, 232));
        cancelButton.setBackground(roundBg(Color.rgb(28, 35, 44), Color.rgb(50, 59, 70), 15));
        cancelButton.setEnabled(false);
        cancelButton.setOnClickListener(v -> cancelDownload());
        LinearLayout.LayoutParams cancelLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(50));
        cancelLp.topMargin = dp(9);
        homeSection.addView(cancelButton, cancelLp);

        LinearLayout activeCard = new LinearLayout(this);
        activeCard.setOrientation(LinearLayout.VERTICAL);
        activeCard.setPadding(dp(15), dp(15), dp(15), dp(15));
        activeCard.setBackground(roundBg(SURFACE, Color.rgb(32, 44, 57), 19));
        LinearLayout.LayoutParams activeLp = fullWrap();
        activeLp.topMargin = dp(17);
        homeSection.addView(activeCard, activeLp);

        TextView activeTitle = sectionTitle("Download status");
        activeCard.addView(activeTitle);

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(12));
        pp.topMargin = dp(12);
        activeCard.addView(progress, pp);

        status = new TextView(this);
        status.setText("Preparing native engine...");
        status.setTextColor(Color.rgb(205, 216, 228));
        status.setTextSize(13);
        status.setPadding(0, dp(12), 0, 0);
        status.setTextIsSelectable(true);
        activeCard.addView(status);
    }

    private void buildDownloadsSection() {
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams headerLp = fullWrap();
        headerLp.topMargin = dp(20);
        downloadsSection.addView(header, headerLp);

        LinearLayout textCol = new LinearLayout(this);
        textCol.setOrientation(LinearLayout.VERTICAL);
        header.addView(textCol, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        TextView dTitle = sectionTitle("Your downloads");
        dTitle.setTextSize(22);
        textCol.addView(dTitle);
        downloadsCount = smallText("Checking saved videos...");
        downloadsCount.setPadding(0, dp(4), 0, 0);
        textCol.addView(downloadsCount);

        Button refresh = new Button(this);
        refresh.setText("Refresh");
        refresh.setAllCaps(false);
        refresh.setTextSize(13);
        refresh.setTextColor(TEXT);
        refresh.setBackground(roundBg(SURFACE_2, Color.rgb(47, 62, 76), 14));
        refresh.setOnClickListener(v -> refreshDownloads());
        header.addView(refresh, new LinearLayout.LayoutParams(dp(92), dp(44)));

        TextView path = smallText("Movies / Rizwan Media Saver");
        path.setPadding(0, dp(12), 0, dp(12));
        downloadsSection.addView(path);

        downloadsContainer = new LinearLayout(this);
        downloadsContainer.setOrientation(LinearLayout.VERTICAL);
        downloadsSection.addView(downloadsContainer, fullWrap());
        refreshDownloads();
    }

    private TextView sectionTitle(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextColor(TEXT);
        tv.setTextSize(18);
        tv.setTypeface(Typeface.DEFAULT_BOLD);
        return tv;
    }

    private TextView smallText(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextColor(MUTED);
        tv.setTextSize(13);
        return tv;
    }

    private Button qualityButton(String quality, String label) {
        Button b = new Button(this);
        b.setText(quality + "\n" + label);
        b.setAllCaps(false);
        b.setTextSize(14);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setGravity(Gravity.CENTER);
        b.setPadding(dp(3), dp(5), dp(3), dp(5));
        return b;
    }

    private LinearLayout.LayoutParams fullWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private GradientDrawable roundBg(int fill, int stroke, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(dp(radiusDp));
        d.setStroke(dp(1), stroke);
        return d;
    }

    private void showTab(boolean home) {
        homeSection.setVisibility(home ? View.VISIBLE : View.GONE);
        downloadsSection.setVisibility(home ? View.GONE : View.VISIBLE);
        homeTabButton.setTextColor(home ? Color.rgb(7, 29, 22) : MUTED);
        downloadsTabButton.setTextColor(home ? MUTED : Color.rgb(7, 29, 22));
        homeTabButton.setBackground(roundBg(home ? ACCENT : Color.TRANSPARENT,
                home ? ACCENT : Color.TRANSPARENT, 13));
        downloadsTabButton.setBackground(roundBg(home ? Color.TRANSPARENT : ACCENT,
                home ? Color.TRANSPARENT : ACCENT, 13));
        if (!home) refreshDownloads();
    }

    private void pasteFromClipboard() {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm == null || !cm.hasPrimaryClip()) {
            Toast.makeText(this, "Clipboard is empty", Toast.LENGTH_SHORT).show();
            return;
        }
        ClipData clip = cm.getPrimaryClip();
        if (clip == null || clip.getItemCount() == 0) return;
        CharSequence text = clip.getItemAt(0).coerceToText(this);
        if (text == null) return;
        urlInput.setText(text.toString().trim());
        urlInput.setSelection(urlInput.length());
        if (engineReady) analyzeLink();
        else setStatus("Link pasted. Native engine is still preparing...");
    }

    private void clearPreview() {
        urlInput.setText("");
        previewCard.setVisibility(View.GONE);
        previewImage.setImageDrawable(null);
        previewTitle.setText("");
        previewMeta.setText("");
    }

    private void analyzeLink() {
        if (processId != null) return;
        String url = urlInput.getText().toString().trim();
        if (!looksLikeYoutubeUrl(url)) {
            urlInput.setError("Paste a YouTube video URL");
            return;
        }
        if (!engineReady) {
            setStatus("Native engine is still preparing. Try Analyze again in a moment.");
            return;
        }

        analyzeButton.setEnabled(false);
        previewCard.setVisibility(View.VISIBLE);
        previewTitle.setText("Reading video info...");
        previewMeta.setText("Please wait");
        previewImage.setImageDrawable(null);

        executor.execute(() -> {
            try {
                YoutubeDLRequest request = new YoutubeDLRequest(url);
                request.addOption("--no-playlist");
                request.addOption("--force-ipv4");
                request.addOption("--remote-components", "ejs:github");
                request.addOption("--js-runtimes", "quickjs");
                request.addOption("--extractor-args",
                        "youtube:player_client=default,-android_sdkless;formats=missing_pot");
                VideoInfo info = YoutubeDL.getInstance().getInfo(request);

                String title = info.getTitle();
                if (title == null || title.trim().isEmpty()) title = "YouTube video";
                int duration = info.getDuration();
                String thumb = info.getThumbnail();
                Bitmap bitmap = null;
                if (thumb != null && !thumb.trim().isEmpty()) {
                    try { bitmap = loadBitmap(thumb); } catch (Exception ignored) { }
                }

                final String finalTitle = title;
                final String finalMeta = (duration > 0 ? formatDuration(duration) + "  •  " : "") +
                        "Choose 360p, 720p or 1080p";
                final Bitmap finalBitmap = bitmap;
                runOnUiThread(() -> {
                    previewTitle.setText(finalTitle);
                    previewMeta.setText(finalMeta);
                    if (finalBitmap != null) previewImage.setImageBitmap(finalBitmap);
                    analyzeButton.setEnabled(true);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    previewTitle.setText("Preview unavailable");
                    previewMeta.setText("Download can still work. " + shortMessage(e));
                    analyzeButton.setEnabled(true);
                });
            }
        });
    }

    private Bitmap loadBitmap(String urlText) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(urlText).openConnection();
        c.setConnectTimeout(8000);
        c.setReadTimeout(8000);
        c.setInstanceFollowRedirects(true);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 Android RizwanMediaSaver");
        try (BufferedInputStream in = new BufferedInputStream(c.getInputStream())) {
            return BitmapFactory.decodeStream(in);
        } finally {
            c.disconnect();
        }
    }

    private String formatDuration(int totalSeconds) {
        int h = totalSeconds / 3600;
        int m = (totalSeconds % 3600) / 60;
        int s = totalSeconds % 60;
        if (h > 0) return String.format(Locale.US, "%d:%02d:%02d", h, m, s);
        return String.format(Locale.US, "%d:%02d", m, s);
    }

    private void refreshDownloads() {
        if (downloadsContainer == null || downloadsCount == null) return;
        downloadsContainer.removeAllViews();
        File outDir = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES),
                "Rizwan Media Saver");
        File[] files = outDir.listFiles((dir, name) -> name.toLowerCase(Locale.US).endsWith(".mp4"));
        if (files == null || files.length == 0) {
            downloadsCount.setText("No completed videos yet");
            LinearLayout empty = new LinearLayout(this);
            empty.setOrientation(LinearLayout.VERTICAL);
            empty.setPadding(dp(18), dp(28), dp(18), dp(28));
            empty.setGravity(Gravity.CENTER);
            empty.setBackground(roundBg(SURFACE, Color.rgb(32, 44, 57), 19));
            TextView icon = new TextView(this);
            icon.setText("↓");
            icon.setTextSize(34);
            icon.setTextColor(ACCENT);
            icon.setGravity(Gravity.CENTER);
            empty.addView(icon);
            TextView t = sectionTitle("Downloads will appear here");
            t.setGravity(Gravity.CENTER);
            t.setPadding(0, dp(8), 0, 0);
            empty.addView(t);
            TextView s = smallText("Complete a video from the Home tab.");
            s.setGravity(Gravity.CENTER);
            s.setPadding(0, dp(5), 0, 0);
            empty.addView(s);
            downloadsContainer.addView(empty, fullWrap());
            return;
        }

        Arrays.sort(files, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
        downloadsCount.setText(files.length + (files.length == 1 ? " completed video" : " completed videos"));
        SimpleDateFormat sdf = new SimpleDateFormat("dd MMM • h:mm a", Locale.getDefault());
        int show = Math.min(files.length, 30);
        for (int i = 0; i < show; i++) {
            File f = files[i];
            LinearLayout item = new LinearLayout(this);
            item.setOrientation(LinearLayout.HORIZONTAL);
            item.setGravity(Gravity.CENTER_VERTICAL);
            item.setPadding(dp(14), dp(14), dp(14), dp(14));
            item.setBackground(roundBg(SURFACE, Color.rgb(32, 44, 57), 17));
            LinearLayout.LayoutParams itemLp = fullWrap();
            if (i > 0) itemLp.topMargin = dp(9);
            downloadsContainer.addView(item, itemLp);

            TextView mark = new TextView(this);
            mark.setText("✓");
            mark.setGravity(Gravity.CENTER);
            mark.setTextSize(19);
            mark.setTextColor(Color.rgb(6, 32, 23));
            mark.setBackground(roundBg(ACCENT, ACCENT, 12));
            item.addView(mark, new LinearLayout.LayoutParams(dp(42), dp(42)));

            LinearLayout info = new LinearLayout(this);
            info.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams infoLp = new LinearLayout.LayoutParams(0,
                    LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
            infoLp.leftMargin = dp(11);
            item.addView(info, infoLp);

            TextView name = new TextView(this);
            name.setText(f.getName());
            name.setTextColor(TEXT);
            name.setTextSize(14);
            name.setMaxLines(2);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            info.addView(name);

            TextView meta = smallText(formatBytes(f.length()) + "  •  " + sdf.format(new Date(f.lastModified())));
            meta.setPadding(0, dp(4), 0, 0);
            info.addView(meta);
        }
    }

    private String formatBytes(long bytes) {
        double mb = bytes / (1024.0 * 1024.0);
        if (mb >= 1024) return String.format(Locale.US, "%.2f GB", mb / 1024.0);
        return String.format(Locale.US, "%.1f MB", mb);
    }

    private void selectQuality(int quality) {
        if (processId != null) return;
        selectedQuality = quality;
        updateQualityButtons();
        if (downloadButton != null) downloadButton.setText("Download " + quality + "p");
    }

    private void updateQualityButtons() {
        if (quality360 == null) return;
        styleQuality(quality360, selectedQuality == 360, "360p\nSD");
        styleQuality(quality720, selectedQuality == 720, "720p\nHD");
        styleQuality(quality1080, selectedQuality == 1080, "1080p\nFULL HD");
    }

    private void styleQuality(Button button, boolean selected, String text) {
        button.setText(text);
        button.setTextColor(selected ? Color.rgb(5, 29, 21) : Color.rgb(220, 228, 236));
        button.setBackground(roundBg(selected ? ACCENT : SURFACE_2,
                selected ? ACCENT : Color.rgb(44, 58, 72), 15));
    }

    private void setQualityButtonsEnabled(boolean enabled) {
        quality360.setEnabled(enabled);
        quality720.setEnabled(enabled);
        quality1080.setEnabled(enabled);
        if (analyzeButton != null) analyzeButton.setEnabled(enabled);
    }

    private void initEngine() {
        setStatus("Preparing native download engine...");
        executor.execute(() -> {
            String updateNote;
            try {
                YoutubeDL.getInstance().init(getApplicationContext());

                try {
                    FFmpeg.getInstance().init(getApplicationContext());
                } catch (Exception ignored) {
                }

                String before = YoutubeDL.getInstance().versionName(getApplicationContext());
                try {
                    runOnUiThread(() -> setStatus("Engine loaded. Checking latest YouTube support..."));
                    YoutubeDL.UpdateStatus updateStatus = YoutubeDL.getInstance().updateYoutubeDL(
                            getApplicationContext(), YoutubeDL.UpdateChannel._NIGHTLY);
                    String after = YoutubeDL.getInstance().versionName(getApplicationContext());
                    updateNote = "yt-dlp " + (after == null ? "updated" : after) + " · " +
                            (updateStatus == null ? "update checked" : updateStatus.toString());
                } catch (Exception updateError) {
                    String current = YoutubeDL.getInstance().versionName(getApplicationContext());
                    updateNote = "yt-dlp update unavailable; using " +
                            (current != null ? current : (before != null ? before : "bundled version"));
                }

                final String readyText = updateNote;
                engineReady = true;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Ready to download\n" + readyText +
                            "\nAndroid MediaMuxer ready for HD audio + video.");
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
        setStatus("Starting 360p video + audio...");

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
                    setStatus("HD stage 3/3: joining video + audio with Android MediaMuxer...");
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
            try { videoExtractor.release(); } catch (Exception ignored) { }
            try { audioExtractor.release(); } catch (Exception ignored) { }
            if (muxer != null) {
                if (muxerStarted) {
                    try { muxer.stop(); } catch (Exception ignored) { }
                }
                try { muxer.release(); } catch (Exception ignored) { }
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
        } catch (Exception ignored) { }
        return 0;
    }

    private void moveOrCopy(File source, File destination) throws Exception {
        if (source.renameTo(destination)) return;

        try (BufferedInputStream in = new BufferedInputStream(new FileInputStream(source));
             BufferedOutputStream out = new BufferedOutputStream(new FileOutputStream(destination))) {
            byte[] buf = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buf)) != -1) out.write(buf, 0, read);
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
        if (files != null) for (File f : files) f.delete();
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
        } catch (Exception ignored) { }
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
        refreshDownloads();
    }

    private void cancelDownload() {
        String id = processId;
        if (id != null) {
            try { YoutubeDL.getInstance().destroyProcessById(id); } catch (Exception ignored) { }
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
            setStatus("Storage permission is required to save videos in Movies.");
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

    private String shortMessage(Throwable t) {
        String m = safeMessage(t).replace('\n', ' ').trim();
        return m.length() > 150 ? m.substring(0, 150) + "..." : m;
    }

    private void setStatus(String text) {
        if (status != null) status.setText(text);
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
