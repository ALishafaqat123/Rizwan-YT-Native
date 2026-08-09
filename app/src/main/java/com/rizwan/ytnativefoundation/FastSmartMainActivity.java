package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
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
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.yausername.ffmpeg.FFmpeg;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import com.yausername.youtubedl_android.YoutubeDLResponse;
import com.yausername.youtubedl_android.mapper.VideoFormat;
import com.yausername.youtubedl_android.mapper.VideoInfo;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class FastSmartMainActivity extends Activity {
    private static final int BG = Color.rgb(249, 250, 248);
    private static final int SURFACE = Color.WHITE;
    private static final int SURFACE_2 = Color.rgb(244, 246, 244);
    private static final int TEXT = Color.rgb(19, 23, 21);
    private static final int MUTED = Color.rgb(111, 120, 115);
    private static final int ACCENT = Color.rgb(35, 196, 132);
    private static final int ACCENT_DARK = Color.rgb(15, 111, 76);
    private static final int BORDER = Color.rgb(225, 230, 227);

    private final ExecutorService metadataExecutor = Executors.newFixedThreadPool(2);
    private final ExecutorService downloadExecutor = Executors.newSingleThreadExecutor();
    private final ArrayList<DownloadTask> queue = new ArrayList<>();

    private EditText linkInput;
    private Button goButton;
    private Button homeNav;
    private Button downloadsNav;
    private TextView status;
    private TextView activeTitle;
    private TextView activeMeta;
    private ProgressBar progress;
    private LinearLayout homePage;
    private LinearLayout downloadsPage;
    private LinearLayout queueContainer;
    private LinearLayout completedContainer;
    private TextView queueSummary;
    private TextView completedSummary;

    private volatile boolean engineReady = false;
    private volatile boolean queueRunning = false;
    private volatile boolean cancelCurrent = false;
    private volatile String processId = null;
    private volatile DownloadTask currentTask = null;
    private String lastClipboardUrl = null;
    private String pendingClipboardUrl = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.WHITE);
        getWindow().setNavigationBarColor(Color.WHITE);
        if (Build.VERSION.SDK_INT >= 23) {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        }
        buildUi();
        ensureStoragePermission();
        initEngine();
    }

    @Override
    protected void onResume() {
        super.onResume();
        detectClipboardLink();
    }

    private void buildUi() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(BG);

        FrameLayout host = new FrameLayout(this);
        page.addView(host, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        homePage = buildHomePage();
        downloadsPage = buildDownloadsPage();
        downloadsPage.setVisibility(View.GONE);
        host.addView(homePage, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        host.addView(downloadsPage, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(8), dp(4), dp(8), dp(6));
        nav.setBackgroundColor(Color.WHITE);

        homeNav = navButton("⌂", "Home");
        downloadsNav = navButton("↓", "Downloads");
        Button settings = navButton("⚙", "Settings");
        nav.addView(homeNav, new LinearLayout.LayoutParams(0, dp(62), 1f));
        nav.addView(downloadsNav, new LinearLayout.LayoutParams(0, dp(62), 1f));
        nav.addView(settings, new LinearLayout.LayoutParams(0, dp(62), 1f));
        homeNav.setOnClickListener(v -> showPage(true));
        downloadsNav.setOnClickListener(v -> showPage(false));
        settings.setOnClickListener(v -> Toast.makeText(this,
                "Settings will be added after the download flow is fully stable.", Toast.LENGTH_SHORT).show());
        page.addView(nav, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(70)));

        setContentView(page);
        showPage(true);
    }

    private LinearLayout buildHomePage() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(22), dp(20), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(header, fullWrap());

        LinearLayout brand = new LinearLayout(this);
        brand.setOrientation(LinearLayout.VERTICAL);
        header.addView(brand, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        TextView title = new TextView(this);
        title.setText("Rizwan Media Saver");
        title.setTextColor(TEXT);
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        brand.addView(title);
        TextView sub = smallText("Fast • private • simple");
        sub.setPadding(0, dp(4), 0, 0);
        brand.addView(sub);
        header.addView(pill("NO ADS", Color.rgb(231, 249, 240), ACCENT_DARK));

        HorizontalScrollView platformScroll = new HorizontalScrollView(this);
        platformScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout platforms = new LinearLayout(this);
        platforms.setOrientation(LinearLayout.HORIZONTAL);
        platforms.setPadding(0, dp(16), 0, dp(8));
        platformScroll.addView(platforms);
        root.addView(platformScroll, fullWrap());
        platforms.addView(platformButton("YouTube", true));
        platforms.addView(platformButton("Instagram", false));
        platforms.addView(platformButton("Facebook", false));
        platforms.addView(platformButton("TikTok", false));

        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setGravity(Gravity.CENTER_HORIZONTAL);
        hero.setPadding(dp(10), dp(42), dp(10), dp(34));
        root.addView(hero, fullWrap());

        TextView logo = new TextView(this);
        logo.setText("↓");
        logo.setTextSize(34);
        logo.setGravity(Gravity.CENTER);
        logo.setTextColor(Color.WHITE);
        logo.setBackground(roundBg(ACCENT, ACCENT, 25));
        hero.addView(logo, new LinearLayout.LayoutParams(dp(70), dp(70)));

        TextView heroTitle = new TextView(this);
        heroTitle.setText("Paste a link. Pick a quality. Done.");
        heroTitle.setTextColor(TEXT);
        heroTitle.setTextSize(21);
        heroTitle.setTypeface(Typeface.DEFAULT_BOLD);
        heroTitle.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams ht = fullWrap();
        ht.topMargin = dp(17);
        hero.addView(heroTitle, ht);

        TextView heroSub = smallText("Copied YouTube links open instantly. Exact sizes load in the background.");
        heroSub.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams hs = fullWrap();
        hs.topMargin = dp(7);
        hero.addView(heroSub, hs);

        LinearLayout search = new LinearLayout(this);
        search.setOrientation(LinearLayout.HORIZONTAL);
        search.setGravity(Gravity.CENTER_VERTICAL);
        search.setPadding(dp(8), dp(8), dp(8), dp(8));
        search.setBackground(roundBg(Color.WHITE, BORDER, 22));
        LinearLayout.LayoutParams searchLp = fullWrap();
        searchLp.topMargin = dp(28);
        hero.addView(search, searchLp);

        Button paste = new Button(this);
        paste.setText("↓");
        paste.setTextSize(20);
        paste.setTextColor(MUTED);
        paste.setBackground(roundBg(SURFACE_2, BORDER, 18));
        paste.setOnClickListener(v -> pasteFromClipboard());
        search.addView(paste, new LinearLayout.LayoutParams(dp(52), dp(52)));

        linkInput = new EditText(this);
        linkInput.setHint("Paste YouTube link");
        linkInput.setHintTextColor(Color.rgb(153, 160, 156));
        linkInput.setTextColor(TEXT);
        linkInput.setTextSize(15);
        linkInput.setSingleLine(true);
        linkInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        linkInput.setBackgroundColor(Color.TRANSPARENT);
        linkInput.setPadding(dp(12), 0, dp(8), 0);
        search.addView(linkInput, new LinearLayout.LayoutParams(0, dp(52), 1f));

        goButton = new Button(this);
        goButton.setText("Go");
        goButton.setAllCaps(false);
        goButton.setTextColor(Color.WHITE);
        goButton.setTextSize(15);
        goButton.setTypeface(Typeface.DEFAULT_BOLD);
        goButton.setBackground(roundBg(ACCENT, ACCENT, 18));
        goButton.setEnabled(false);
        goButton.setOnClickListener(v -> handleLink(linkInput.getText().toString().trim(), false));
        search.addView(goButton, new LinearLayout.LayoutParams(dp(68), dp(52)));

        LinearLayout statusCard = new LinearLayout(this);
        statusCard.setOrientation(LinearLayout.VERTICAL);
        statusCard.setPadding(dp(14), dp(14), dp(14), dp(14));
        statusCard.setBackground(roundBg(SURFACE, BORDER, 18));
        LinearLayout.LayoutParams sc = fullWrap();
        sc.topMargin = dp(16);
        root.addView(statusCard, sc);
        activeTitle = sectionTitle("Preparing");
        activeTitle.setTextSize(15);
        statusCard.addView(activeTitle);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(9));
        pp.topMargin = dp(10);
        statusCard.addView(progress, pp);
        status = smallText("Preparing download engine...");
        status.setPadding(0, dp(9), 0, 0);
        status.setMaxLines(4);
        status.setTextIsSelectable(true);
        statusCard.addView(status);
        activeMeta = smallText("");
        activeMeta.setPadding(0, dp(4), 0, 0);
        statusCard.addView(activeMeta);

        return wrapScroll(scroll);
    }

    private LinearLayout buildDownloadsPage() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(24), dp(20), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        TextView title = sectionTitle("Downloads");
        title.setTextSize(25);
        root.addView(title);
        TextView sub = smallText("Active downloads, playlist queue and completed files.");
        sub.setPadding(0, dp(4), 0, dp(16));
        root.addView(sub);

        TextView qh = sectionTitle("Active & Queue");
        qh.setTextSize(17);
        root.addView(qh);
        queueSummary = smallText("No active or queued items");
        queueSummary.setPadding(0, dp(4), 0, dp(9));
        root.addView(queueSummary);
        queueContainer = new LinearLayout(this);
        queueContainer.setOrientation(LinearLayout.VERTICAL);
        root.addView(queueContainer, fullWrap());

        TextView dh = sectionTitle("Completed");
        dh.setTextSize(17);
        dh.setPadding(0, dp(22), 0, 0);
        root.addView(dh);
        completedSummary = smallText("Checking saved files...");
        completedSummary.setPadding(0, dp(4), 0, dp(9));
        root.addView(completedSummary);
        completedContainer = new LinearLayout(this);
        completedContainer.setOrientation(LinearLayout.VERTICAL);
        root.addView(completedContainer, fullWrap());

        refreshQueueUi();
        refreshCompletedUi();
        return wrapScroll(scroll);
    }

    private void initEngine() {
        activeTitle.setText("Preparing");
        metadataExecutor.execute(() -> {
            try {
                YoutubeDL.getInstance().init(getApplicationContext());
                try { FFmpeg.getInstance().init(getApplicationContext()); } catch (Exception ignored) { }
                String note;
                String before = YoutubeDL.getInstance().versionName(getApplicationContext());
                try {
                    YoutubeDL.UpdateStatus us = YoutubeDL.getInstance().updateYoutubeDL(
                            getApplicationContext(), YoutubeDL.UpdateChannel._NIGHTLY);
                    String after = YoutubeDL.getInstance().versionName(getApplicationContext());
                    note = "yt-dlp " + (after == null ? "updated" : after) + " • " +
                            (us == null ? "checked" : us.toString());
                } catch (Exception e) {
                    String current = YoutubeDL.getInstance().versionName(getApplicationContext());
                    note = "Using " + (current != null ? current : (before != null ? before : "bundled yt-dlp"));
                }
                final String n = note;
                engineReady = true;
                runOnUiThread(() -> {
                    goButton.setEnabled(true);
                    activeTitle.setText("Ready");
                    setStatus(n + "\nAndroid MediaMuxer ready for HD.");
                    if (pendingClipboardUrl != null) {
                        String p = pendingClipboardUrl;
                        pendingClipboardUrl = null;
                        showCopiedLinkPrompt(p);
                    }
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    activeTitle.setText("Engine error");
                    setStatus(safeMessage(e));
                });
            }
        });
    }

    private void detectClipboardLink() {
        String text = clipboardText();
        if (text == null || !looksLikeYoutubeUrl(text)) return;
        if (text.equals(lastClipboardUrl)) return;
        lastClipboardUrl = text;
        linkInput.setText(text);
        linkInput.setSelection(linkInput.length());
        if (engineReady && !queueRunning) showCopiedLinkPrompt(text);
        else pendingClipboardUrl = text;
    }

    private void showCopiedLinkPrompt(String url) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(18), dp(10), dp(18), dp(4));

        LinearLayout media = new LinearLayout(this);
        media.setOrientation(LinearLayout.HORIZONTAL);
        media.setGravity(Gravity.CENTER_VERTICAL);
        box.addView(media, fullWrap());

        ImageView thumb = new ImageView(this);
        thumb.setScaleType(ImageView.ScaleType.CENTER_CROP);
        thumb.setBackground(roundBg(SURFACE_2, BORDER, 10));
        media.addView(thumb, new LinearLayout.LayoutParams(dp(76), dp(52)));

        LinearLayout txt = new LinearLayout(this);
        txt.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        tlp.leftMargin = dp(11);
        media.addView(txt, tlp);
        TextView t = new TextView(this);
        t.setText(hasPlaylistHint(url) ? "Playlist link copied" : "Video link copied");
        t.setTextColor(TEXT);
        t.setTextSize(15);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        txt.addView(t);
        TextView u = smallText(ellipsize(url, 65));
        u.setPadding(0, dp(4), 0, 0);
        txt.addView(u);

        String id = getYoutubeId(url);
        if (id != null) loadThumbnailAsync("https://i.ytimg.com/vi/" + id + "/hqdefault.jpg", thumb);

        AlertDialog d = new AlertDialog.Builder(this)
                .setTitle("Download the link you copied?")
                .setView(box)
                .setPositiveButton(hasPlaylistHint(url) ? "Open" : "Download", (x, w) -> handleLink(url, true))
                .setNegativeButton("Not now", null)
                .create();
        d.show();
    }

    private void pasteFromClipboard() {
        String text = clipboardText();
        if (text == null || text.isEmpty()) {
            Toast.makeText(this, "Clipboard is empty", Toast.LENGTH_SHORT).show();
            return;
        }
        linkInput.setText(text);
        linkInput.setSelection(linkInput.length());
        if (looksLikeYoutubeUrl(text) && engineReady) handleLink(text, false);
    }

    private void handleLink(String url, boolean fromClipboard) {
        if (!looksLikeYoutubeUrl(url)) {
            linkInput.setError("Paste a YouTube video or playlist link");
            return;
        }
        if (!engineReady) {
            pendingClipboardUrl = url;
            setStatus("Engine is still preparing...");
            return;
        }
        if (queueRunning) {
            Toast.makeText(this, "A download queue is active. You can add more after it finishes.", Toast.LENGTH_SHORT).show();
            return;
        }

        if (hasPlaylistHint(url)) {
            String id = getYoutubeId(url);
            if (id != null && !id.isEmpty()) {
                new AlertDialog.Builder(this)
                        .setTitle("Playlist detected")
                        .setMessage("This link belongs to a playlist. What would you like to download?")
                        .setPositiveButton("Download playlist", (d, w) -> loadPlaylistFast(url))
                        .setNeutralButton("This video", (d, w) -> showVideoOptionsFast(canonicalVideoUrl(id), fromClipboard))
                        .setNegativeButton("Cancel", null)
                        .show();
            } else {
                loadPlaylistFast(url);
            }
        } else {
            showVideoOptionsFast(url, fromClipboard);
        }
    }

    private void showVideoOptionsFast(String url, boolean fromClipboard) {
        activeTitle.setText("Options ready");
        setStatus("Download choices opened immediately. Exact title and sizes are loading in the background.");
        progress.setProgress(0);

        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        ScrollView scroll = new ScrollView(this);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(20), dp(12), dp(20), dp(24));
        sheet.setBackground(roundBg(Color.WHITE, Color.WHITE, 24));
        scroll.addView(sheet);

        TextView handle = new TextView(this);
        handle.setText("━");
        handle.setTextColor(Color.rgb(194, 199, 196));
        handle.setTextSize(25);
        handle.setGravity(Gravity.CENTER);
        sheet.addView(handle);
        TextView head = sectionTitle(fromClipboard ? "Copied link detected" : "Download video as");
        head.setTextSize(21);
        sheet.addView(head);

        LinearLayout media = new LinearLayout(this);
        media.setOrientation(LinearLayout.HORIZONTAL);
        media.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams mlp = fullWrap();
        mlp.topMargin = dp(12);
        sheet.addView(media, mlp);
        ImageView image = new ImageView(this);
        image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        image.setBackground(roundBg(SURFACE_2, BORDER, 10));
        media.addView(image, new LinearLayout.LayoutParams(dp(108), dp(70)));
        LinearLayout textCol = new LinearLayout(this);
        textCol.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams tcp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        tcp.leftMargin = dp(12);
        media.addView(textCol, tcp);
        TextView title = new TextView(this);
        title.setText("YouTube video");
        title.setTextColor(TEXT);
        title.setTextSize(15);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setMaxLines(2);
        textCol.addView(title);
        TextView meta = smallText("Checking title and exact sizes…");
        meta.setPadding(0, dp(4), 0, 0);
        textCol.addView(meta);

        String id = getYoutubeId(url);
        if (id != null) loadThumbnailAsync("https://i.ytimg.com/vi/" + id + "/hqdefault.jpg", image);

        TextView musicHead = sectionTitle("Music");
        musicHead.setTextSize(16);
        musicHead.setTextColor(MUTED);
        musicHead.setPadding(0, dp(20), 0, dp(7));
        sheet.addView(musicHead);
        OptionRow audioFast = addOption(sheet, "♪", "Fast", "AAC • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 0, 64);
        });
        OptionRow audioBest = addOption(sheet, "♪", "Classic AAC", "Best M4A • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 0, 999);
        });

        TextView videoHead = sectionTitle("Video");
        videoHead.setTextSize(16);
        videoHead.setTextColor(MUTED);
        videoHead.setPadding(0, dp(18), 0, dp(7));
        sheet.addView(videoHead);
        OptionRow q360 = addOption(sheet, "▣", "Fast (360p)", "SD • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 360, 0);
        });
        OptionRow q720 = addOption(sheet, "▣", "High quality (720p)", "HD • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 720, 0);
        });
        OptionRow q1080 = addOption(sheet, "▣", "Full HD (1080p)", "1080p • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 1080, 0);
        });

        Button close = new Button(this);
        close.setText("Close");
        close.setAllCaps(false);
        close.setTextColor(MUTED);
        close.setBackgroundColor(Color.TRANSPARENT);
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        clp.topMargin = dp(8);
        sheet.addView(close, clp);
        close.setOnClickListener(v -> dialog.dismiss());

        dialog.setContentView(scroll);
        Window w = dialog.getWindow();
        if (w != null) {
            w.setBackgroundDrawableResource(android.R.color.transparent);
            w.setGravity(Gravity.BOTTOM);
        }
        dialog.show();
        if (dialog.getWindow() != null) {
            dialog.getWindow().setLayout(WindowManager.LayoutParams.MATCH_PARENT,
                    Math.min(getResources().getDisplayMetrics().heightPixels * 4 / 5, dp(760)));
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }

        metadataExecutor.execute(() -> {
            try {
                VideoInfo info = getSingleInfo(url);
                final String finalTitle = info.getTitle() == null || info.getTitle().trim().isEmpty()
                        ? "YouTube video" : info.getTitle();
                final String duration = info.getDuration() > 0 ? formatDuration(info.getDuration()) : "YouTube";
                final String s360 = estimateVideoLabel(info, 360);
                final String s720 = estimateVideoLabel(info, 720);
                final String s1080 = estimateVideoLabel(info, 1080);
                final String sa64 = estimateAudioLabel(info, 64);
                final String sab = estimateAudioLabel(info, 256);
                final int maxH = maxHeight(info);
                runOnUiThread(() -> {
                    if (!dialog.isShowing()) return;
                    title.setText(finalTitle);
                    meta.setText(duration + " • exact formats checked");
                    q360.detail.setText("SD • " + s360);
                    q720.detail.setText("HD • " + s720);
                    q1080.detail.setText("Full HD • " + s1080);
                    audioFast.detail.setText("AAC • " + sa64);
                    audioBest.detail.setText("Best M4A • " + sab);
                    if (maxH > 0) {
                        q720.button.setEnabled(maxH >= 720);
                        q1080.button.setEnabled(maxH >= 1080);
                        if (maxH < 720) q720.detail.setText("Not available on this video");
                        if (maxH < 1080) q1080.detail.setText("Not available on this video");
                    }
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    if (dialog.isShowing()) meta.setText("Options are ready • exact size unavailable");
                });
            }
        });
    }

    private OptionRow addOption(LinearLayout parent, String icon, String title, String detail, Runnable action) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(12), dp(8), dp(8), dp(8));
        row.setBackground(roundBg(Color.WHITE, BORDER, 13));
        LinearLayout.LayoutParams rlp = fullWrap();
        rlp.bottomMargin = dp(7);
        parent.addView(row, rlp);

        TextView mark = new TextView(this);
        mark.setText(icon);
        mark.setTextColor(MUTED);
        mark.setTextSize(20);
        mark.setGravity(Gravity.CENTER);
        row.addView(mark, new LinearLayout.LayoutParams(dp(42), dp(46)));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        row.addView(text, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextColor(TEXT);
        t.setTextSize(15);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        text.addView(t);
        TextView d = smallText(detail);
        d.setPadding(0, dp(2), 0, 0);
        text.addView(d);

        Button b = new Button(this);
        b.setText("↓");
        b.setTextSize(18);
        b.setTextColor(Color.WHITE);
        b.setBackground(roundBg(ACCENT, ACCENT, 16));
        b.setOnClickListener(v -> action.run());
        row.addView(b, new LinearLayout.LayoutParams(dp(48), dp(48)));
        return new OptionRow(d, b);
    }

    private void loadPlaylistFast(String url) {
        activeTitle.setText("Loading playlist");
        setStatus("Reading playlist titles only — no per-video format analysis.");
        progress.setProgress(6);
        metadataExecutor.execute(() -> {
            try {
                PlaylistResult result = loadPlaylist(url);
                if (result.entries.isEmpty()) throw new Exception("No playlist videos were returned.");
                runOnUiThread(() -> {
                    activeTitle.setText("Playlist ready");
                    progress.setProgress(0);
                    setStatus(result.entries.size() + " videos found • choose what you want to download");
                    showPlaylistSelection(result);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    activeTitle.setText("Playlist error");
                    progress.setProgress(0);
                    setStatus(safeMessage(e));
                });
            }
        });
    }

    private PlaylistResult loadPlaylist(String url) throws Exception {
        YoutubeDLRequest request = new YoutubeDLRequest(url);
        request.addOption("--flat-playlist");
        request.addOption("--dump-single-json");
        request.addOption("--skip-download");
        request.addOption("--yes-playlist");
        request.addOption("--force-ipv4");
        YoutubeDLResponse response = YoutubeDL.getInstance().execute(request, null, null);
        String json = response.getOut();
        int a = json == null ? -1 : json.indexOf('{');
        int b = json == null ? -1 : json.lastIndexOf('}');
        if (a < 0 || b <= a) throw new Exception("Playlist information was not returned.");
        JSONObject root = new JSONObject(json.substring(a, b + 1));
        PlaylistResult result = new PlaylistResult();
        result.title = root.optString("title", "YouTube playlist");
        JSONArray entries = root.optJSONArray("entries");
        if (entries == null) return result;
        for (int i = 0; i < entries.length(); i++) {
            JSONObject e = entries.optJSONObject(i);
            if (e == null) continue;
            String id = e.optString("id", "");
            if (id.isEmpty()) continue;
            PlaylistEntry item = new PlaylistEntry();
            item.id = id;
            item.title = e.optString("title", "Video " + (i + 1));
            item.thumbnail = e.optString("thumbnail", "");
            String webpage = e.optString("webpage_url", "");
            item.url = webpage.startsWith("http") ? webpage : "https://www.youtube.com/watch?v=" + id;
            result.entries.add(item);
        }
        return result;
    }

    private void showPlaylistSelection(PlaylistResult playlist) {
        int n = playlist.entries.size();
        String[] labels = new String[n];
        boolean[] checked = new boolean[n];
        for (int i = 0; i < n; i++) {
            checked[i] = true;
            labels[i] = (i + 1) + ". " + playlist.entries.get(i).title;
        }
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle((playlist.title == null ? "Playlist" : playlist.title) + " • " + n)
                .setMultiChoiceItems(labels, checked, (d, which, isChecked) -> checked[which] = isChecked)
                .setPositiveButton("Next", null)
                .setNeutralButton("Deselect all", null)
                .setNegativeButton("Cancel", null)
                .create();
        dialog.setOnShowListener(x -> {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                boolean any = false;
                for (boolean c : checked) if (c) { any = true; break; }
                boolean next = !any;
                ListView list = dialog.getListView();
                for (int i = 0; i < n; i++) {
                    checked[i] = next;
                    list.setItemChecked(i, next);
                }
                dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setText(next ? "Deselect all" : "Select all");
            });
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                ArrayList<PlaylistEntry> selected = new ArrayList<>();
                for (int i = 0; i < n; i++) if (checked[i]) selected.add(playlist.entries.get(i));
                if (selected.isEmpty()) {
                    Toast.makeText(this, "Select at least one video", Toast.LENGTH_SHORT).show();
                    return;
                }
                dialog.dismiss();
                showPlaylistQualityChooser(selected);
            });
        });
        dialog.show();
    }

    private void showPlaylistQualityChooser(ArrayList<PlaylistEntry> selected) {
        String[] options = {"360p SD", "720p HD", "1080p Full HD", "Audio only • Best AAC/M4A"};
        final int[] chosen = {1};
        new AlertDialog.Builder(this)
                .setTitle("Download " + selected.size() + " selected items")
                .setSingleChoiceItems(options, 1, (d, which) -> chosen[0] = which)
                .setPositiveButton("Add to queue", (d, w) -> {
                    ArrayList<DownloadTask> tasks = new ArrayList<>();
                    int total = selected.size();
                    for (int i = 0; i < selected.size(); i++) {
                        PlaylistEntry e = selected.get(i);
                        DownloadTask task = new DownloadTask();
                        task.id = e.id;
                        task.title = e.title;
                        task.url = e.url;
                        task.batchIndex = i + 1;
                        task.batchTotal = total;
                        task.playlistBatch = total > 1;
                        if (chosen[0] == 3) {
                            task.quality = 0;
                            task.audioKbps = 999;
                        } else {
                            task.quality = chosen[0] == 0 ? 360 : chosen[0] == 1 ? 720 : 1080;
                            task.audioKbps = 0;
                        }
                        task.status = "WAITING";
                        task.stage = "Waiting";
                        task.itemProgress = 0;
                        tasks.add(task);
                    }
                    enqueueTasks(tasks);
                })
                .setNegativeButton("Back", null)
                .show();
    }

    private VideoInfo getSingleInfo(String url) throws Exception {
        YoutubeDLRequest request = new YoutubeDLRequest(url);
        request.addOption("--no-playlist");
        request.addOption("--force-ipv4");
        request.addOption("--remote-components", "ejs:github");
        request.addOption("--js-runtimes", "quickjs");
        request.addOption("--extractor-args", "youtube:player_client=default,-android_sdkless;formats=missing_pot");
        return YoutubeDL.getInstance().getInfo(request);
    }

    private void enqueueSingle(String url, String title, int quality, int audioKbps) {
        DownloadTask task = new DownloadTask();
        task.id = getYoutubeId(url);
        if (task.id == null || task.id.isEmpty()) task.id = Integer.toHexString(url.hashCode());
        task.title = title == null || title.trim().isEmpty() ? "YouTube video" : title;
        task.url = url;
        task.quality = quality;
        task.audioKbps = audioKbps;
        task.status = "WAITING";
        task.stage = "Waiting";
        task.itemProgress = 0;
        task.batchIndex = 1;
        task.batchTotal = 1;
        ArrayList<DownloadTask> tasks = new ArrayList<>();
        tasks.add(task);
        enqueueTasks(tasks);
    }

    private void enqueueTasks(ArrayList<DownloadTask> tasks) {
        if (!ensureStoragePermission()) return;
        synchronized (queue) { queue.addAll(tasks); }
        refreshQueueUi();
        showPage(false);
        if (!queueRunning) {
            queueRunning = true;
            downloadExecutor.execute(this::processQueue);
        }
    }

    private void processQueue() {
        while (true) {
            DownloadTask task = nextWaitingTask();
            if (task == null) break;
            currentTask = task;
            cancelCurrent = false;
            task.status = "DOWNLOADING";
            task.stage = task.audioKbps > 0 ? "Downloading audio" :
                    (task.quality <= 360 ? "Downloading video + audio" : "Downloading video");
            task.itemProgress = 0;
            runOnUiThread(() -> {
                activeTitle.setText(itemPrefix(task) + task.stage);
                activeMeta.setText(task.title);
                progress.setProgress(overallProgress(task, 0));
                setStatus(task.playlistBatch ? playlistStatusLine(task, 0) : "Starting download…");
                refreshQueueUi();
            });
            try {
                downloadTaskBlocking(task);
                task.status = cancelCurrent ? "CANCELED" : "COMPLETED";
                task.stage = cancelCurrent ? "Canceled" : "Completed";
                task.itemProgress = cancelCurrent ? task.itemProgress : 100;
            } catch (Exception e) {
                task.error = shortMessage(e);
                task.status = cancelCurrent ? "CANCELED" : "FAILED";
                task.stage = cancelCurrent ? "Canceled" : "Failed";
            } finally {
                processId = null;
                currentTask = null;
                cancelCurrent = false;
                runOnUiThread(() -> {
                    refreshQueueUi();
                    refreshCompletedUi();
                });
            }
        }
        queueRunning = false;
        runOnUiThread(() -> {
            activeTitle.setText("Queue finished");
            activeMeta.setText("");
            progress.setProgress(100);
            setStatus("All queued items have been processed.");
            refreshQueueUi();
            refreshCompletedUi();
        });
    }

    private DownloadTask nextWaitingTask() {
        synchronized (queue) {
            for (DownloadTask t : queue) if ("WAITING".equals(t.status)) return t;
        }
        return null;
    }

    private String itemPrefix(DownloadTask task) {
        return task != null && task.batchTotal > 1
                ? "Item " + task.batchIndex + "/" + task.batchTotal + " • " : "";
    }

    private int overallProgress(DownloadTask task, int itemProgress) {
        int p = Math.max(0, Math.min(100, itemProgress));
        if (task == null || task.batchTotal <= 1) return p;
        return Math.max(0, Math.min(100,
                ((task.batchIndex - 1) * 100 + p) / task.batchTotal));
    }

    private String playlistStatusLine(DownloadTask task, int itemProgress) {
        int overall = overallProgress(task, itemProgress);
        return "Playlist " + task.batchIndex + "/" + task.batchTotal +
                " • current item " + itemProgress + "% • overall " + overall + "%";
    }

    private void downloadTaskBlocking(DownloadTask task) throws Exception {
        File outDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES),
                "Rizwan Media Saver");
        if (!outDir.exists() && !outDir.mkdirs()) throw new Exception("Could not create Movies/Rizwan Media Saver folder.");
        if (task.audioKbps > 0) downloadAudioBlocking(task, outDir);
        else if (task.quality <= 360) download360Blocking(task, outDir);
        else downloadHdBlocking(task, outDir);
    }

    private void download360Blocking(DownloadTask task, File outDir) throws Exception {
        String pid = "rms360-" + UUID.randomUUID();
        processId = pid;
        YoutubeDLRequest request = commonRequest(task.url);
        request.addOption("-f", "18/" +
                "best[height<=360][ext=mp4][vcodec^=avc1][acodec^=mp4a]/" +
                "best[height<=360][ext=mp4][vcodec!=none][acodec!=none]/" +
                "bestvideo[height<=360][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/" +
                "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/" +
                "best[height<=360][vcodec!=none][acodec!=none]/best");
        request.addOption("--merge-output-format", "mp4");
        request.addOption("-o", new File(outDir, "%(title).180B [%(id)s] [360p].%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(request, pid, progressCallback(0, 100, "Downloading 360p video + audio"));
    }

    private void downloadAudioBlocking(DownloadTask task, File outDir) throws Exception {
        File audioDir = new File(outDir, "Audio");
        if (!audioDir.exists() && !audioDir.mkdirs()) throw new Exception("Could not create Audio folder.");
        String selector;
        if (task.audioKbps <= 64) selector = "bestaudio[ext=m4a][acodec^=mp4a][abr<=70]/worstaudio[ext=m4a][acodec^=mp4a]";
        else selector = "bestaudio[ext=m4a][acodec^=mp4a]/bestaudio[ext=m4a]";
        String pid = "rms-audio-" + UUID.randomUUID();
        processId = pid;
        YoutubeDLRequest request = commonRequest(task.url);
        request.addOption("-f", selector);
        request.addOption("-o", new File(audioDir, "%(title).180B [%(id)s] [audio].%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(request, pid, progressCallback(0, 100, "Downloading audio"));
    }

    private void downloadHdBlocking(DownloadTask task, File outDir) throws Exception {
        String safeId = sanitize(task.id == null ? Integer.toHexString(task.url.hashCode()) : task.id);
        File workRoot = new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "hd-work");
        File workDir = new File(workRoot, safeId + "-" + task.quality + "p");
        if (!workDir.exists()) workDir.mkdirs();
        File mergedTemp = new File(workDir, "merged-final.mp4");
        File finalFile = new File(outDir, safeFileTitle(task.title) + " [" + safeId + "] [" + task.quality + "p].mp4");

        String videoPid = "rms-hd-video-" + safeId + "-" + task.quality;
        processId = videoPid;
        YoutubeDLRequest videoReq = commonRequest(task.url);
        videoReq.addOption("-f", "bestvideo[height<=" + task.quality + "][ext=mp4][vcodec^=avc1]");
        videoReq.addOption("-o", new File(workDir, "video.%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(videoReq, videoPid,
                progressCallback(0, 78, "Downloading " + task.quality + "p H.264 video"));
        processId = null;
        if (cancelCurrent) throw new Exception("Canceled");
        File videoFile = findCompleteFile(workDir, "video.");
        if (videoFile == null || !hasVideoTrack(videoFile.getAbsolutePath())) throw new Exception("HD video stream was not created correctly.");

        String audioPid = "rms-hd-audio-" + safeId + "-" + task.quality;
        processId = audioPid;
        YoutubeDLRequest audioReq = commonRequest(task.url);
        audioReq.addOption("-f", "bestaudio[ext=m4a][acodec^=mp4a]");
        audioReq.addOption("-o", new File(workDir, "audio.%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(audioReq, audioPid,
                progressCallback(78, 95, "Downloading AAC audio"));
        processId = null;
        if (cancelCurrent) throw new Exception("Canceled");
        File audioFile = findCompleteFile(workDir, "audio.");
        if (audioFile == null || !hasAudioTrack(audioFile.getAbsolutePath())) throw new Exception("AAC audio stream was not created correctly.");

        task.stage = "Joining video + audio";
        task.itemProgress = 96;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 96));
            activeTitle.setText(itemPrefix(task) + "Joining video + audio");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 96) :
                    "Joining video + audio with Android MediaMuxer…");
            refreshQueueUi();
        });
        if (mergedTemp.exists()) mergedTemp.delete();
        muxWithAndroid(videoFile, audioFile, mergedTemp);
        if (!mergedTemp.isFile() || mergedTemp.length() <= 0 || !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {
            throw new Exception("Android MediaMuxer verification failed.");
        }
        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");
        moveOrCopy(mergedTemp, finalFile);
        if (!finalFile.isFile() || !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
            if (finalFile.exists()) finalFile.delete();
            throw new Exception("Final saved MP4 verification failed.");
        }
        deleteWorkFiles(workDir);
        task.stage = "Finalizing";
        task.itemProgress = 100;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 100));
            activeTitle.setText(itemPrefix(task) + "Finalizing");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) : "Final MP4 verified.");
            refreshQueueUi();
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
        request.addOption("--extractor-args", "youtube:player_client=default,-android_sdkless;formats=missing_pot");
        return request;
    }

    private Function3<Float, Long, String, Unit> progressCallback(int start, int end, String label) {
        return (pct, eta, line) -> {
            float raw = pct == null || pct < 0 ? 0 : Math.min(100f, pct);
            int scaled = start + Math.round((end - start) * (raw / 100f));
            int itemProgress = Math.max(start, Math.min(end, scaled));
            String safeLine = line == null ? "" : line;
            String lower = safeLine.toLowerCase(Locale.US);
            boolean resuming = lower.contains("resuming download") || lower.contains("resume at") || lower.contains("continuing at");
            DownloadTask task = currentTask;
            if (task != null) {
                task.stage = resuming ? "Resuming previous download" : label;
                task.itemProgress = itemProgress;
            }
            runOnUiThread(() -> {
                DownloadTask active = currentTask;
                int shownProgress = active == null ? itemProgress : overallProgress(active, itemProgress);
                progress.setProgress(shownProgress);
                String etaText = eta != null && eta >= 0 ? " • ETA " + eta + "s" : "";
                String stage = resuming ? "Resuming previous download" : label;
                activeTitle.setText((active == null ? "" : itemPrefix(active)) + stage);
                if (active != null && active.playlistBatch) {
                    setStatus(playlistStatusLine(active, itemProgress) + etaText + "\n" + safeLine);
                } else {
                    setStatus(Math.round(raw) + "%" + etaText + "\n" + safeLine);
                }
                refreshQueueUi();
            });
            return Unit.INSTANCE;
        };
    }

    private void muxWithAndroid(File videoFile, File audioFile, File outputFile) throws Exception {
        MediaExtractor videoExtractor = new MediaExtractor();
        MediaExtractor audioExtractor = new MediaExtractor();
        MediaMuxer muxer = null;
        boolean started = false;
        try {
            videoExtractor.setDataSource(videoFile.getAbsolutePath());
            audioExtractor.setDataSource(audioFile.getAbsolutePath());
            int vs = findTrack(videoExtractor, "video/");
            int as = findTrack(audioExtractor, "audio/");
            if (vs < 0 || as < 0) throw new Exception("MediaMuxer input track missing.");
            MediaFormat vf = videoExtractor.getTrackFormat(vs);
            MediaFormat af = audioExtractor.getTrackFormat(as);
            String vm = vf.getString(MediaFormat.KEY_MIME);
            String am = af.getString(MediaFormat.KEY_MIME);
            if (vm == null || !"video/avc".equalsIgnoreCase(vm)) throw new Exception("MediaMuxer requires H.264 video, got " + vm);
            if (am == null || !am.toLowerCase(Locale.US).startsWith("audio/mp4a")) throw new Exception("MediaMuxer requires AAC audio, got " + am);
            if (outputFile.exists() && !outputFile.delete()) throw new Exception("Could not replace temporary MP4.");
            muxer = new MediaMuxer(outputFile.getAbsolutePath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
            if (vf.containsKey(MediaFormat.KEY_ROTATION)) {
                int r = vf.getInteger(MediaFormat.KEY_ROTATION);
                if (r == 90 || r == 180 || r == 270) muxer.setOrientationHint(r);
            }
            int vmux = muxer.addTrack(vf);
            int amux = muxer.addTrack(af);
            videoExtractor.selectTrack(vs);
            audioExtractor.selectTrack(as);
            muxer.start();
            started = true;
            int bufferSize = Math.max(8 * 1024 * 1024, Math.max(maxInputSize(vf), maxInputSize(af)) + 1024);
            ByteBuffer buffer = ByteBuffer.allocate(bufferSize);
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            long vt = videoExtractor.getSampleTime();
            long at = audioExtractor.getSampleTime();
            while (vt >= 0 || at >= 0) {
                boolean useVideo = at < 0 || (vt >= 0 && vt <= at);
                MediaExtractor ex = useVideo ? videoExtractor : audioExtractor;
                int track = useVideo ? vmux : amux;
                buffer.clear();
                int size = ex.readSampleData(buffer, 0);
                if (size < 0) {
                    if (useVideo) vt = -1; else at = -1;
                    continue;
                }
                info.set(0, size, ex.getSampleTime(), ex.getSampleFlags());
                muxer.writeSampleData(track, buffer, info);
                ex.advance();
                if (useVideo) vt = videoExtractor.getSampleTime(); else at = audioExtractor.getSampleTime();
            }
            muxer.stop();
            started = false;
        } finally {
            try { videoExtractor.release(); } catch (Exception ignored) { }
            try { audioExtractor.release(); } catch (Exception ignored) { }
            if (muxer != null) {
                if (started) try { muxer.stop(); } catch (Exception ignored) { }
                try { muxer.release(); } catch (Exception ignored) { }
            }
        }
    }

    private int findTrack(MediaExtractor extractor, String prefix) {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            MediaFormat f = extractor.getTrackFormat(i);
            String mime = f.getString(MediaFormat.KEY_MIME);
            if (mime != null && mime.startsWith(prefix)) return i;
        }
        return -1;
    }

    private int maxInputSize(MediaFormat f) {
        try { return f.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE) ? Math.max(0, f.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE)) : 0; }
        catch (Exception e) { return 0; }
    }

    private boolean hasVideoTrack(String path) throws Exception {
        MediaExtractor e = new MediaExtractor();
        try { e.setDataSource(path); return findTrack(e, "video/") >= 0; } finally { e.release(); }
    }

    private boolean hasAudioTrack(String path) throws Exception {
        MediaExtractor e = new MediaExtractor();
        try { e.setDataSource(path); return findTrack(e, "audio/") >= 0; } finally { e.release(); }
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
            if (!f.isFile() || !n.startsWith(prefix) || n.endsWith(".part") || n.endsWith(".ytdl") || f.length() <= 0) continue;
            if (best == null || f.lastModified() > best.lastModified()) best = f;
        }
        return best;
    }

    private void deleteWorkFiles(File dir) {
        File[] files = dir.listFiles();
        if (files != null) for (File f : files) f.delete();
        dir.delete();
    }

    private void refreshQueueUi() {
        if (queueContainer == null || queueSummary == null) return;
        queueContainer.removeAllViews();
        ArrayList<DownloadTask> snap;
        synchronized (queue) { snap = new ArrayList<>(queue); }
        int waiting = 0, failed = 0, active = 0, completed = 0;
        for (DownloadTask t : snap) {
            if ("WAITING".equals(t.status)) waiting++;
            else if ("FAILED".equals(t.status)) failed++;
            else if ("DOWNLOADING".equals(t.status)) active++;
            else if ("COMPLETED".equals(t.status)) completed++;
        }
        if (snap.size() > 1) {
            queueSummary.setText(completed + "/" + snap.size() + " completed • " +
                    active + " active • " + waiting + " waiting" +
                    (failed > 0 ? " • " + failed + " failed" : ""));
        } else {
            queueSummary.setText(active + " active • " + waiting + " waiting" +
                    (failed > 0 ? " • " + failed + " failed" : ""));
        }
        int shown = 0;
        for (DownloadTask t : snap) {
            if ("COMPLETED".equals(t.status)) continue;
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(13), dp(11), dp(13), dp(11));
            card.setBackground(roundBg(SURFACE, BORDER, 14));
            LinearLayout.LayoutParams lp = fullWrap();
            if (shown++ > 0) lp.topMargin = dp(7);
            queueContainer.addView(card, lp);
            TextView name = new TextView(this);
            name.setText((t.batchTotal > 1 ? t.batchIndex + "/" + t.batchTotal + "  " : "") + t.title);
            name.setTextColor(TEXT);
            name.setTextSize(14);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            name.setMaxLines(2);
            card.addView(name);
            String mode = t.audioKbps > 0 ? "Audio only" : t.quality + "p video";
            String stage = t.stage == null ? t.status : t.stage;
            TextView meta = smallText(mode + " • " + stage + (t.error == null ? "" : "\n" + t.error));
            meta.setPadding(0, dp(4), 0, 0);
            card.addView(meta);
            if ("DOWNLOADING".equals(t.status)) {
                ProgressBar itemBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
                itemBar.setMax(100);
                itemBar.setProgress(Math.max(0, Math.min(100, t.itemProgress)));
                LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, dp(8));
                bp.topMargin = dp(8);
                card.addView(itemBar, bp);
                TextView pct = smallText(t.itemProgress + "% of current item" +
                        (t.batchTotal > 1 ? " • playlist overall " + overallProgress(t, t.itemProgress) + "%" : ""));
                pct.setPadding(0, dp(4), 0, 0);
                card.addView(pct);
            }
        }
        if (shown == 0) queueContainer.addView(smallText("No active or waiting items."));
    }

    private void refreshCompletedUi() {
        if (completedContainer == null || completedSummary == null) return;
        completedContainer.removeAllViews();
        File outDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES), "Rizwan Media Saver");
        ArrayList<File> files = new ArrayList<>();
        collectMediaFiles(outDir, files);
        files.sort((a, b) -> Long.compare(b.lastModified(), a.lastModified()));
        completedSummary.setText(files.size() + (files.size() == 1 ? " completed file" : " completed files"));
        SimpleDateFormat sdf = new SimpleDateFormat("dd MMM • h:mm a", Locale.getDefault());
        int show = Math.min(files.size(), 50);
        for (int i = 0; i < show; i++) {
            File f = files.get(i);
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(13), dp(11), dp(13), dp(11));
            card.setBackground(roundBg(SURFACE, BORDER, 14));
            LinearLayout.LayoutParams lp = fullWrap();
            if (i > 0) lp.topMargin = dp(7);
            completedContainer.addView(card, lp);
            TextView name = new TextView(this);
            name.setText(f.getName());
            name.setTextColor(TEXT);
            name.setTextSize(14);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            name.setMaxLines(2);
            card.addView(name);
            TextView meta = smallText(formatBytes(f.length()) + " • " + sdf.format(new Date(f.lastModified())));
            meta.setPadding(0, dp(4), 0, 0);
            card.addView(meta);
        }
    }

    private void collectMediaFiles(File dir, ArrayList<File> out) {
        if (dir == null || !dir.isDirectory()) return;
        File[] files = dir.listFiles();
        if (files == null) return;
        for (File f : files) {
            if (f.isDirectory()) collectMediaFiles(f, out);
            else {
                String n = f.getName().toLowerCase(Locale.US);
                if (n.endsWith(".mp4") || n.endsWith(".m4a")) out.add(f);
            }
        }
    }

    private void cancelActiveDownload() {
        cancelCurrent = true;
        String id = processId;
        if (id != null) try { YoutubeDL.getInstance().destroyProcessById(id); } catch (Exception ignored) { }
        setStatus("Cancel requested. The next queued item will continue.");
    }

    private int maxHeight(VideoInfo info) {
        int max = 0;
        try {
            List<VideoFormat> formats = info.getFormats();
            if (formats != null) for (VideoFormat f : formats) if (f.getVcodec() != null && !"none".equals(f.getVcodec())) max = Math.max(max, f.getHeight());
        } catch (Exception ignored) { }
        return max;
    }

    private String estimateVideoLabel(VideoInfo info, int quality) {
        long video = 0;
        long audio = 0;
        try {
            List<VideoFormat> formats = info.getFormats();
            if (formats != null) {
                for (VideoFormat f : formats) {
                    long size = f.getFileSize() > 0 ? f.getFileSize() : f.getFileSizeApproximate();
                    if (size <= 0) continue;
                    boolean hasVideo = f.getVcodec() != null && !"none".equals(f.getVcodec());
                    boolean hasAudio = f.getAcodec() != null && !"none".equals(f.getAcodec());
                    if (hasVideo && f.getHeight() > 0 && f.getHeight() <= quality) video = Math.max(video, size);
                    if (!hasVideo && hasAudio) audio = Math.max(audio, size);
                }
            }
        } catch (Exception ignored) { }
        long total = video + audio;
        return total > 0 ? formatBytes(total) : "size varies";
    }

    private String estimateAudioLabel(VideoInfo info, int kbps) {
        if (info.getDuration() > 0) {
            long bytes = (long) info.getDuration() * kbps * 1000L / 8L;
            return "≈ " + formatBytes(bytes);
        }
        return "size varies";
    }

    private void loadThumbnailAsync(String url, ImageView image) {
        metadataExecutor.execute(() -> {
            try {
                Bitmap b = loadBitmap(url);
                if (b != null) runOnUiThread(() -> image.setImageBitmap(b));
            } catch (Exception ignored) { }
        });
    }

    private Bitmap loadBitmap(String urlText) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(urlText).openConnection();
        c.setConnectTimeout(5000);
        c.setReadTimeout(5000);
        c.setInstanceFollowRedirects(true);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 Android RizwanMediaSaver");
        try (BufferedInputStream in = new BufferedInputStream(c.getInputStream())) {
            return BitmapFactory.decodeStream(in);
        } finally { c.disconnect(); }
    }

    private boolean hasPlaylistHint(String url) {
        try {
            Uri uri = Uri.parse(url);
            String list = uri.getQueryParameter("list");
            return list != null && !list.trim().isEmpty();
        } catch (Exception e) { return false; }
    }

    private String canonicalVideoUrl(String id) {
        return "https://www.youtube.com/watch?v=" + id;
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
                if (seg.size() >= 2 && ("shorts".equals(seg.get(0)) || "embed".equals(seg.get(0)) || "live".equals(seg.get(0)))) return seg.get(1);
            }
        } catch (Exception ignored) { }
        return null;
    }

    private boolean looksLikeYoutubeUrl(String url) {
        if (url == null) return false;
        String s = url.toLowerCase(Locale.US);
        return (s.startsWith("http://") || s.startsWith("https://")) && (s.contains("youtube.com/") || s.contains("youtu.be/"));
    }

    private String clipboardText() {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm == null || !cm.hasPrimaryClip()) return null;
            ClipData clip = cm.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0) return null;
            CharSequence text = clip.getItemAt(0).coerceToText(this);
            return text == null ? null : text.toString().trim();
        } catch (Exception e) { return null; }
    }

    private boolean ensureStoragePermission() {
        if (Build.VERSION.SDK_INT >= 23 && Build.VERSION.SDK_INT <= 28) {
            if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
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
            setStatus("Storage permission is required to save videos in Movies.");
        }
    }

    private void showPage(boolean home) {
        homePage.setVisibility(home ? View.VISIBLE : View.GONE);
        downloadsPage.setVisibility(home ? View.GONE : View.VISIBLE);
        homeNav.setTextColor(home ? ACCENT_DARK : MUTED);
        downloadsNav.setTextColor(home ? MUTED : ACCENT_DARK);
        homeNav.setTypeface(home ? Typeface.DEFAULT_BOLD : Typeface.DEFAULT);
        downloadsNav.setTypeface(home ? Typeface.DEFAULT : Typeface.DEFAULT_BOLD);
        if (!home) {
            refreshQueueUi();
            refreshCompletedUi();
        }
    }

    private Button navButton(String icon, String label) {
        Button b = new Button(this);
        b.setText(icon + "\n" + label);
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setGravity(Gravity.CENTER);
        b.setTextColor(MUTED);
        b.setBackgroundColor(Color.TRANSPARENT);
        return b;
    }

    private Button platformButton(String name, boolean enabled) {
        Button b = new Button(this);
        b.setText(name + (enabled ? "" : " • soon"));
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(enabled ? Color.WHITE : MUTED);
        b.setBackground(roundBg(enabled ? TEXT : SURFACE_2, enabled ? TEXT : BORDER, 16));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(42));
        lp.rightMargin = dp(8);
        b.setLayoutParams(lp);
        if (!enabled) b.setOnClickListener(v -> Toast.makeText(this, name + " will be enabled after its engine is tested.", Toast.LENGTH_SHORT).show());
        return b;
    }

    private LinearLayout wrapScroll(ScrollView scroll) {
        LinearLayout h = new LinearLayout(this);
        h.setOrientation(LinearLayout.VERTICAL);
        h.addView(scroll, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return h;
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

    private TextView pill(String text, int fill, int textColor) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextColor(textColor);
        tv.setTextSize(11);
        tv.setTypeface(Typeface.DEFAULT_BOLD);
        tv.setGravity(Gravity.CENTER);
        tv.setPadding(dp(11), dp(7), dp(11), dp(7));
        tv.setBackground(roundBg(fill, fill, 15));
        return tv;
    }

    private GradientDrawable roundBg(int fill, int stroke, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(dp(radius));
        d.setStroke(dp(1), stroke);
        return d;
    }

    private LinearLayout.LayoutParams fullWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private void setStatus(String s) { if (status != null) status.setText(s); }

    private String formatDuration(int totalSeconds) {
        int h = totalSeconds / 3600;
        int m = (totalSeconds % 3600) / 60;
        int s = totalSeconds % 60;
        return h > 0 ? String.format(Locale.US, "%d:%02d:%02d", h, m, s) : String.format(Locale.US, "%d:%02d", m, s);
    }

    private String formatBytes(long bytes) {
        double mb = bytes / (1024.0 * 1024.0);
        return mb >= 1024 ? String.format(Locale.US, "%.2f GB", mb / 1024.0) : String.format(Locale.US, "%.1f MB", mb);
    }

    private String safeFileTitle(String title) {
        if (title == null || title.trim().isEmpty()) return "YouTube";
        String s = title.replaceAll("[\\/:*?\"<>|]", "_").trim();
        if (s.length() > 120) s = s.substring(0, 120).trim();
        return s.isEmpty() ? "YouTube" : s;
    }

    private String sanitize(String s) { return s == null ? "video" : s.replaceAll("[^A-Za-z0-9_-]", "_"); }
    private String ellipsize(String s, int max) { return s == null ? "" : (s.length() <= max ? s : s.substring(0, max - 1) + "…"); }
    private String safeMessage(Throwable t) { String m = t.getMessage(); return m == null || m.trim().isEmpty() ? t.toString() : m; }
    private String shortMessage(Throwable t) { String m = safeMessage(t).replace('\n', ' ').trim(); return m.length() > 160 ? m.substring(0, 160) + "…" : m; }

    @Override
    protected void onDestroy() {
        metadataExecutor.shutdownNow();
        downloadExecutor.shutdownNow();
        super.onDestroy();
    }

    private static class PlaylistEntry {
        String id;
        String title;
        String url;
        String thumbnail;
    }

    private static class PlaylistResult {
        String title;
        final ArrayList<PlaylistEntry> entries = new ArrayList<>();
    }

    private static class DownloadTask {
        String id;
        String title;
        String url;
        int quality;
        int audioKbps;
        String status;
        String error;
        String stage;
        int itemProgress;
        int batchIndex = 1;
        int batchTotal = 1;
        boolean playlistBatch = false;
    }

    private static class OptionRow {
        final TextView detail;
        final Button button;
        OptionRow(TextView detail, Button button) {
            this.detail = detail;
            this.button = button;
        }
    }
}
