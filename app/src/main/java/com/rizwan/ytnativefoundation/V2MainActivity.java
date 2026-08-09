package com.rizwan.ytnativefoundation;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.SharedPreferences;
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
import android.util.LruCache;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.widget.ArrayAdapter;
import android.widget.BaseAdapter;
import android.widget.CheckBox;
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

import com.arthenica.ffmpegkit.FFmpegKit;
import com.arthenica.ffmpegkit.FFmpegSession;
import com.arthenica.ffmpegkit.ReturnCode;

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
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class V2MainActivity extends Activity {
    private static final int BG = Color.rgb(246, 248, 247);
    private static final int SURFACE = Color.WHITE;
    private static final int SURFACE_2 = Color.rgb(240, 244, 242);
    private static final int TEXT = Color.rgb(20, 25, 22);
    private static final int MUTED = Color.rgb(101, 111, 106);
    private static final int ACCENT = Color.rgb(18, 176, 111);
    private static final int ACCENT_DARK = Color.rgb(10, 112, 70);
    private static final int ACCENT_SOFT = Color.rgb(231, 248, 239);
    private static final int DARK = Color.rgb(24, 30, 27);
    private static final int BORDER = Color.rgb(224, 230, 227);

    private static final long YTDLP_UPDATE_INTERVAL_MS = 24L * 60L * 60L * 1000L;
    private final ExecutorService metadataExecutor = Executors.newFixedThreadPool(2);
    private final ExecutorService imageExecutor = Executors.newFixedThreadPool(3);
    private final ExecutorService downloadExecutor = Executors.newSingleThreadExecutor();
    private final ArrayList<DownloadTask> queue = new ArrayList<>();
    private final LruCache<String, Bitmap> thumbnailCache = new LruCache<>(36);
    private final ConcurrentHashMap<String, VideoInfo> infoCache = new ConcurrentHashMap<>();

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
    private LinearLayout statusCard;
    private LinearLayout activeSection;
    private LinearLayout completedSection;
    private Button activeTab;
    private Button completedTab;
    private boolean downloadsShowingActive = true;
    private volatile long lastQueueUiRefreshMs = 0L;

    private volatile boolean engineReady = false;
    private volatile boolean queueRunning = false;
    private volatile boolean cancelCurrent = false;
    private volatile String processId = null;
    private volatile DownloadTask currentTask = null;
    private volatile String lastFinalizeReport = null;
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
        nav.setPadding(dp(10), dp(5), dp(10), dp(7));
        nav.setBackgroundColor(Color.WHITE);
        if (Build.VERSION.SDK_INT >= 21) nav.setElevation(dp(8));

        homeNav = navButton("⌂", "Home");
        downloadsNav = navButton("↓", "Downloads");
        Button settings = navButton("⚙", "Settings");
        nav.addView(homeNav, new LinearLayout.LayoutParams(0, dp(58), 1f));
        nav.addView(downloadsNav, new LinearLayout.LayoutParams(0, dp(58), 1f));
        nav.addView(settings, new LinearLayout.LayoutParams(0, dp(58), 1f));
        homeNav.setOnClickListener(v -> showPage(true));
        downloadsNav.setOnClickListener(v -> showPage(false));
        settings.setOnClickListener(v -> Toast.makeText(this,
                "Settings are coming in the next V2 pass.", Toast.LENGTH_SHORT).show());
        page.addView(nav, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(68)));

        setContentView(page);
        showPage(true);
    }

    private LinearLayout buildHomePage() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(30));
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
        title.setTextSize(23);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        brand.addView(title);
        TextView sub = smallText("Simple downloads. No ads. No clutter.");
        sub.setPadding(0, dp(3), 0, 0);
        brand.addView(sub);
        header.addView(pill("V2", ACCENT_SOFT, ACCENT_DARK));

        HorizontalScrollView platformScroll = new HorizontalScrollView(this);
        platformScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout platforms = new LinearLayout(this);
        platforms.setOrientation(LinearLayout.HORIZONTAL);
        platforms.setPadding(0, dp(16), 0, dp(12));
        platformScroll.addView(platforms);
        root.addView(platformScroll, fullWrap());
        platforms.addView(platformButton("YouTube", true));
        platforms.addView(platformButton("Instagram", false));
        platforms.addView(platformButton("Facebook", false));
        platforms.addView(platformButton("TikTok", false));

        LinearLayout hero = new LinearLayout(this);
        hero.setOrientation(LinearLayout.VERTICAL);
        hero.setPadding(dp(18), dp(18), dp(18), dp(18));
        hero.setBackground(roundBg(ACCENT_SOFT, ACCENT_SOFT, 28));
        if (Build.VERSION.SDK_INT >= 21) hero.setElevation(dp(1));
        root.addView(hero, fullWrap());

        LinearLayout heroTop = new LinearLayout(this);
        heroTop.setOrientation(LinearLayout.HORIZONTAL);
        heroTop.setGravity(Gravity.CENTER_VERTICAL);
        hero.addView(heroTop, fullWrap());
        TextView logo = new TextView(this);
        logo.setText("↓");
        logo.setTextSize(27);
        logo.setGravity(Gravity.CENTER);
        logo.setTextColor(Color.WHITE);
        logo.setBackground(roundBg(ACCENT, ACCENT, 20));
        heroTop.addView(logo, new LinearLayout.LayoutParams(dp(58), dp(58)));

        LinearLayout heroText = new LinearLayout(this);
        heroText.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams htp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        htp.leftMargin = dp(13);
        heroTop.addView(heroText, htp);
        TextView heroTitle = new TextView(this);
        heroTitle.setText("Download a video or playlist");
        heroTitle.setTextColor(TEXT);
        heroTitle.setTextSize(19);
        heroTitle.setTypeface(Typeface.DEFAULT_BOLD);
        heroText.addView(heroTitle);
        TextView heroSub = smallText("Paste a link, or copy one before opening the app.");
        heroSub.setPadding(0, dp(4), 0, 0);
        heroText.addView(heroSub);

        LinearLayout search = new LinearLayout(this);
        search.setOrientation(LinearLayout.HORIZONTAL);
        search.setGravity(Gravity.CENTER_VERTICAL);
        search.setPadding(dp(6), dp(6), dp(6), dp(6));
        search.setBackground(roundBg(Color.WHITE, Color.WHITE, 20));
        if (Build.VERSION.SDK_INT >= 21) search.setElevation(dp(2));
        LinearLayout.LayoutParams searchLp = fullWrap();
        searchLp.topMargin = dp(18);
        hero.addView(search, searchLp);

        Button paste = new Button(this);
        paste.setText("Paste");
        paste.setAllCaps(false);
        paste.setTextSize(12);
        paste.setTypeface(Typeface.DEFAULT_BOLD);
        paste.setTextColor(ACCENT_DARK);
        paste.setBackground(roundBg(ACCENT_SOFT, ACCENT_SOFT, 16));
        paste.setOnClickListener(v -> pasteFromClipboard());
        search.addView(paste, new LinearLayout.LayoutParams(dp(68), dp(50)));

        linkInput = new EditText(this);
        linkInput.setHint("YouTube link");
        linkInput.setHintTextColor(Color.rgb(145, 153, 149));
        linkInput.setTextColor(TEXT);
        linkInput.setTextSize(14);
        linkInput.setSingleLine(true);
        linkInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        linkInput.setBackgroundColor(Color.TRANSPARENT);
        linkInput.setPadding(dp(10), 0, dp(6), 0);
        search.addView(linkInput, new LinearLayout.LayoutParams(0, dp(50), 1f));

        goButton = new Button(this);
        goButton.setText("Go");
        goButton.setAllCaps(false);
        goButton.setTextColor(Color.WHITE);
        goButton.setTextSize(14);
        goButton.setTypeface(Typeface.DEFAULT_BOLD);
        goButton.setBackground(roundBg(ACCENT, ACCENT, 16));
        goButton.setEnabled(false);
        goButton.setOnClickListener(v -> handleLink(linkInput.getText().toString().trim(), false));
        search.addView(goButton, new LinearLayout.LayoutParams(dp(58), dp(50)));

        LinearLayout capabilities = new LinearLayout(this);
        capabilities.setOrientation(LinearLayout.HORIZONTAL);
        capabilities.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams cp = fullWrap();
        cp.topMargin = dp(12);
        hero.addView(capabilities, cp);
        capabilities.addView(pill("VIDEO", Color.WHITE, ACCENT_DARK));
        LinearLayout.LayoutParams gap = new LinearLayout.LayoutParams(dp(7), dp(1));
        TextView spacer1 = new TextView(this);
        capabilities.addView(spacer1, gap);
        capabilities.addView(pill("AUDIO", Color.WHITE, ACCENT_DARK));
        TextView spacer2 = new TextView(this);
        capabilities.addView(spacer2, new LinearLayout.LayoutParams(dp(7), dp(1)));
        capabilities.addView(pill("PLAYLIST", Color.WHITE, ACCENT_DARK));

        statusCard = new LinearLayout(this);
        statusCard.setOrientation(LinearLayout.VERTICAL);
        statusCard.setPadding(dp(15), dp(14), dp(15), dp(14));
        statusCard.setBackground(roundBg(SURFACE, BORDER, 18));
        if (Build.VERSION.SDK_INT >= 21) statusCard.setElevation(dp(1));
        LinearLayout.LayoutParams sc = fullWrap();
        sc.topMargin = dp(14);
        root.addView(statusCard, sc);
        LinearLayout statusHead = new LinearLayout(this);
        statusHead.setOrientation(LinearLayout.HORIZONTAL);
        statusHead.setGravity(Gravity.CENTER_VERTICAL);
        statusCard.addView(statusHead, fullWrap());
        activeTitle = sectionTitle("Preparing download engine");
        activeTitle.setTextSize(14);
        statusHead.addView(activeTitle, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        statusHead.addView(pill("NO ADS", ACCENT_SOFT, ACCENT_DARK));
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(7));
        pp.topMargin = dp(10);
        statusCard.addView(progress, pp);
        status = smallText("Getting things ready…");
        status.setPadding(0, dp(8), 0, 0);
        status.setMaxLines(3);
        status.setTextIsSelectable(true);
        statusCard.addView(status);
        activeMeta = smallText("");
        activeMeta.setPadding(0, dp(3), 0, 0);
        statusCard.addView(activeMeta);

        return wrapScroll(scroll);
    }

    private LinearLayout buildDownloadsPage() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(20), dp(18), dp(30));
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        root.addView(head, fullWrap());
        LinearLayout headText = new LinearLayout(this);
        headText.setOrientation(LinearLayout.VERTICAL);
        head.addView(headText, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        TextView title = sectionTitle("Downloads");
        title.setTextSize(24);
        headText.addView(title);
        TextView sub = smallText("Queue, progress and saved files");
        sub.setPadding(0, dp(3), 0, 0);
        headText.addView(sub);
        head.addView(pill("LIVE", ACCENT_SOFT, ACCENT_DARK));

        LinearLayout summaryCard = new LinearLayout(this);
        summaryCard.setOrientation(LinearLayout.VERTICAL);
        summaryCard.setPadding(dp(15), dp(13), dp(15), dp(13));
        summaryCard.setBackground(roundBg(DARK, DARK, 18));
        if (Build.VERSION.SDK_INT >= 21) summaryCard.setElevation(dp(2));
        LinearLayout.LayoutParams sp = fullWrap();
        sp.topMargin = dp(16);
        root.addView(summaryCard, sp);
        TextView summaryTitle = new TextView(this);
        summaryTitle.setText("Download activity");
        summaryTitle.setTextColor(Color.WHITE);
        summaryTitle.setTextSize(14);
        summaryTitle.setTypeface(Typeface.DEFAULT_BOLD);
        summaryCard.addView(summaryTitle);
        queueSummary = new TextView(this);
        queueSummary.setText("No active or queued items");
        queueSummary.setTextColor(Color.rgb(205, 214, 209));
        queueSummary.setTextSize(12);
        queueSummary.setPadding(0, dp(5), 0, 0);
        summaryCard.addView(queueSummary);

        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setPadding(dp(4), dp(4), dp(4), dp(4));
        tabs.setBackground(roundBg(SURFACE_2, SURFACE_2, 17));
        LinearLayout.LayoutParams tp = fullWrap();
        tp.topMargin = dp(14);
        root.addView(tabs, tp);
        activeTab = segmentButton("Active & Queue", true);
        completedTab = segmentButton("Completed", false);
        tabs.addView(activeTab, new LinearLayout.LayoutParams(0, dp(46), 1f));
        tabs.addView(completedTab, new LinearLayout.LayoutParams(0, dp(46), 1f));

        activeSection = new LinearLayout(this);
        activeSection.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams asp = fullWrap();
        asp.topMargin = dp(14);
        root.addView(activeSection, asp);
        queueContainer = new LinearLayout(this);
        queueContainer.setOrientation(LinearLayout.VERTICAL);
        activeSection.addView(queueContainer, fullWrap());

        completedSection = new LinearLayout(this);
        completedSection.setOrientation(LinearLayout.VERTICAL);
        completedSection.setVisibility(View.GONE);
        LinearLayout.LayoutParams csp = fullWrap();
        csp.topMargin = dp(14);
        root.addView(completedSection, csp);
        completedSummary = smallText("Saved files");
        completedSummary.setPadding(0, 0, 0, dp(9));
        completedSection.addView(completedSummary);
        completedContainer = new LinearLayout(this);
        completedContainer.setOrientation(LinearLayout.VERTICAL);
        completedSection.addView(completedContainer, fullWrap());

        activeTab.setOnClickListener(v -> showDownloadsMode(true));
        completedTab.setOnClickListener(v -> showDownloadsMode(false));
        refreshQueueUi();
        return wrapScroll(scroll);
    }

    private Button segmentButton(String text, boolean selected) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setTextColor(selected ? Color.WHITE : MUTED);
        b.setBackground(roundBg(selected ? DARK : Color.TRANSPARENT,
                selected ? DARK : Color.TRANSPARENT, 14));
        return b;
    }

    private void showDownloadsMode(boolean active) {
        downloadsShowingActive = active;
        if (activeSection != null) activeSection.setVisibility(active ? View.VISIBLE : View.GONE);
        if (completedSection != null) completedSection.setVisibility(active ? View.GONE : View.VISIBLE);
        if (activeTab != null) {
            activeTab.setTextColor(active ? Color.WHITE : MUTED);
            activeTab.setBackground(roundBg(active ? DARK : Color.TRANSPARENT,
                    active ? DARK : Color.TRANSPARENT, 14));
        }
        if (completedTab != null) {
            completedTab.setTextColor(active ? MUTED : Color.WHITE);
            completedTab.setBackground(roundBg(active ? Color.TRANSPARENT : DARK,
                    active ? Color.TRANSPARENT : DARK, 14));
        }
        if (active) refreshQueueUi(); else refreshCompletedUi();
        View target = active ? activeSection : completedSection;
        if (target != null) {
            target.setAlpha(0.65f);
            target.setTranslationY(dp(8));
            target.animate().alpha(1f).translationY(0f).setDuration(150).start();
        }
    }

    private void initEngine() {
        activeTitle.setText("Preparing");
        metadataExecutor.execute(() -> {
            try {
                YoutubeDL.getInstance().init(getApplicationContext());
                try { FFmpeg.getInstance().init(getApplicationContext()); } catch (Exception ignored) { }

                SharedPreferences prefs = getSharedPreferences("rms_v2_engine", MODE_PRIVATE);
                long now = System.currentTimeMillis();
                long lastUpdate = prefs.getLong("last_yt_dlp_update", 0L);
                String before = YoutubeDL.getInstance().versionName(getApplicationContext());
                String note;

                if (lastUpdate <= 0L || now - lastUpdate >= YTDLP_UPDATE_INTERVAL_MS) {
                    try {
                        YoutubeDL.UpdateStatus us = YoutubeDL.getInstance().updateYoutubeDL(
                                getApplicationContext(), YoutubeDL.UpdateChannel._NIGHTLY);
                        String after = YoutubeDL.getInstance().versionName(getApplicationContext());
                        note = "yt-dlp " + (after == null ? "updated" : after) + " • " +
                                (us == null ? "checked" : us.toString());
                        prefs.edit().putLong("last_yt_dlp_update", now).apply();
                    } catch (Exception e) {
                        String current = YoutubeDL.getInstance().versionName(getApplicationContext());
                        note = "Using " + (current != null ? current : (before != null ? before : "bundled yt-dlp"));
                    }
                } else {
                    String current = YoutubeDL.getInstance().versionName(getApplicationContext());
                    note = "yt-dlp " + (current != null ? current : "ready") + " • cached startup";
                }

                final String n = note;
                engineReady = true;
                runOnUiThread(() -> {
                    goButton.setEnabled(true);
                    activeTitle.setText("Ready");
                    setStatus(n + "\nFast V2 engine • Android MediaMuxer ready.");
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
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(18), dp(10), dp(18), dp(20));
        sheet.setBackground(roundBg(Color.WHITE, Color.WHITE, 26));

        TextView handle = new TextView(this);
        handle.setText("━");
        handle.setTextColor(Color.rgb(190, 197, 193));
        handle.setTextSize(24);
        handle.setGravity(Gravity.CENTER);
        sheet.addView(handle);

        TextView head = sectionTitle(hasPlaylistHint(url) ? "Playlist copied" : "Link copied");
        head.setTextSize(20);
        sheet.addView(head);
        TextView helper = smallText(hasPlaylistHint(url)
                ? "Choose whether to download the playlist or only this video."
                : "Your download options are one tap away.");
        helper.setPadding(0, dp(4), 0, dp(14));
        sheet.addView(helper);

        LinearLayout media = new LinearLayout(this);
        media.setOrientation(LinearLayout.HORIZONTAL);
        media.setGravity(Gravity.CENTER_VERTICAL);
        media.setPadding(dp(10), dp(10), dp(10), dp(10));
        media.setBackground(roundBg(SURFACE_2, BORDER, 16));
        sheet.addView(media, fullWrap());
        ImageView thumb = new ImageView(this);
        thumb.setScaleType(ImageView.ScaleType.CENTER_CROP);
        thumb.setBackground(roundBg(Color.rgb(229, 234, 231), Color.rgb(229, 234, 231), 10));
        media.addView(thumb, new LinearLayout.LayoutParams(dp(92), dp(58)));
        LinearLayout txt = new LinearLayout(this);
        txt.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        tlp.leftMargin = dp(11);
        media.addView(txt, tlp);
        TextView type = new TextView(this);
        type.setText(hasPlaylistHint(url) ? "YouTube playlist" : "YouTube video");
        type.setTextColor(TEXT);
        type.setTextSize(14);
        type.setTypeface(Typeface.DEFAULT_BOLD);
        txt.addView(type);
        TextView u = smallText(ellipsize(url, 62));
        u.setPadding(0, dp(3), 0, 0);
        txt.addView(u);

        String id = getYoutubeId(url);
        if (id != null) loadThumbnailAsync("https://i.ytimg.com/vi/" + id + "/hqdefault.jpg", thumb);

        Button primary = new Button(this);
        primary.setAllCaps(false);
        primary.setTextColor(Color.WHITE);
        primary.setTextSize(14);
        primary.setTypeface(Typeface.DEFAULT_BOLD);
        primary.setText(hasPlaylistHint(url) ? "Download playlist" : "Choose quality");
        primary.setBackground(roundBg(ACCENT, ACCENT, 16));
        LinearLayout.LayoutParams pp = fullWrap();
        pp.height = dp(52);
        pp.topMargin = dp(14);
        sheet.addView(primary, pp);
        primary.setOnClickListener(v -> {
            dialog.dismiss();
            if (hasPlaylistHint(url)) loadPlaylistFast(url); else showVideoOptionsFast(url, true);
        });

        if (hasPlaylistHint(url) && id != null && !id.isEmpty()) {
            Button one = new Button(this);
            one.setText("Only this video");
            one.setAllCaps(false);
            one.setTextColor(TEXT);
            one.setTextSize(14);
            one.setBackground(roundBg(SURFACE_2, BORDER, 16));
            LinearLayout.LayoutParams op = fullWrap();
            op.height = dp(50);
            op.topMargin = dp(8);
            sheet.addView(one, op);
            one.setOnClickListener(v -> {
                dialog.dismiss();
                showVideoOptionsFast(canonicalVideoUrl(id), true);
            });
        }

        Button close = new Button(this);
        close.setText("Not now");
        close.setAllCaps(false);
        close.setTextColor(MUTED);
        close.setBackgroundColor(Color.TRANSPARENT);
        sheet.addView(close, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(44)));
        close.setOnClickListener(v -> dialog.dismiss());

        dialog.setContentView(sheet);
        Window w = dialog.getWindow();
        if (w != null) {
            w.setBackgroundDrawableResource(android.R.color.transparent);
            w.setGravity(Gravity.BOTTOM);
        }
        dialog.show();
        if (dialog.getWindow() != null) {
            dialog.getWindow().setLayout(WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.WRAP_CONTENT);
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }
        sheet.setTranslationY(dp(30));
        sheet.setAlpha(0f);
        sheet.animate().translationY(0f).alpha(1f).setDuration(180).start();
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
        setStatus("Choose now — title and exact sizes are loading in the background.");
        progress.setProgress(0);

        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        ScrollView scroll = new ScrollView(this);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(18), dp(10), dp(18), dp(22));
        sheet.setBackground(roundBg(Color.WHITE, Color.WHITE, 26));
        scroll.addView(sheet);

        TextView handle = new TextView(this);
        handle.setText("━");
        handle.setTextColor(Color.rgb(190, 197, 193));
        handle.setTextSize(24);
        handle.setGravity(Gravity.CENTER);
        sheet.addView(handle);
        TextView head = sectionTitle(fromClipboard ? "Ready to download" : "Choose a format");
        head.setTextSize(20);
        sheet.addView(head);

        LinearLayout media = new LinearLayout(this);
        media.setOrientation(LinearLayout.HORIZONTAL);
        media.setGravity(Gravity.CENTER_VERTICAL);
        media.setPadding(0, dp(12), 0, dp(12));
        sheet.addView(media, fullWrap());
        ImageView image = new ImageView(this);
        image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        image.setBackground(roundBg(SURFACE_2, BORDER, 11));
        media.addView(image, new LinearLayout.LayoutParams(dp(112), dp(70)));
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
        TextView meta = smallText("Sizes are checking in the background…");
        meta.setPadding(0, dp(4), 0, 0);
        textCol.addView(meta);

        String id = getYoutubeId(url);
        if (id != null) loadThumbnailAsync("https://i.ytimg.com/vi/" + id + "/hqdefault.jpg", image);

        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setPadding(dp(4), dp(4), dp(4), dp(4));
        tabs.setBackground(roundBg(SURFACE_2, SURFACE_2, 17));
        sheet.addView(tabs, fullWrap());
        Button videoTab = segmentButton("Video", true);
        Button audioTab = segmentButton("Audio", false);
        tabs.addView(videoTab, new LinearLayout.LayoutParams(0, dp(44), 1f));
        tabs.addView(audioTab, new LinearLayout.LayoutParams(0, dp(44), 1f));

        LinearLayout videoBox = new LinearLayout(this);
        videoBox.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams vbp = fullWrap();
        vbp.topMargin = dp(12);
        sheet.addView(videoBox, vbp);
        LinearLayout audioBox = new LinearLayout(this);
        audioBox.setOrientation(LinearLayout.VERTICAL);
        audioBox.setVisibility(View.GONE);
        LinearLayout.LayoutParams abp = fullWrap();
        abp.topMargin = dp(12);
        sheet.addView(audioBox, abp);

        OptionRow q360 = addOption(videoBox, "360", "360p • Fast", "SD • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 360, 0);
        });
        OptionRow q720 = addOption(videoBox, "720", "720p • HD", "H.264 + AAC • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 720, 0);
        });
        OptionRow q1080 = addOption(videoBox, "1080", "1080p • Full HD", "H.264 + AAC • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 1080, 0);
        });
        OptionRow audioFast = addOption(audioBox, "♪", "AAC • Small", "Fast audio • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 0, 64);
        });
        OptionRow audioBest = addOption(audioBox, "♪", "M4A • Best", "Best AAC audio • size checking…", () -> {
            dialog.dismiss(); enqueueSingle(url, title.getText().toString(), 0, 999);
        });

        videoTab.setOnClickListener(v -> {
            videoBox.setVisibility(View.VISIBLE);
            audioBox.setVisibility(View.GONE);
            videoTab.setTextColor(Color.WHITE);
            videoTab.setBackground(roundBg(DARK, DARK, 14));
            audioTab.setTextColor(MUTED);
            audioTab.setBackground(roundBg(Color.TRANSPARENT, Color.TRANSPARENT, 14));
        });
        audioTab.setOnClickListener(v -> {
            videoBox.setVisibility(View.GONE);
            audioBox.setVisibility(View.VISIBLE);
            audioTab.setTextColor(Color.WHITE);
            audioTab.setBackground(roundBg(DARK, DARK, 14));
            videoTab.setTextColor(MUTED);
            videoTab.setBackground(roundBg(Color.TRANSPARENT, Color.TRANSPARENT, 14));
        });

        Button close = new Button(this);
        close.setText("Close");
        close.setAllCaps(false);
        close.setTextColor(MUTED);
        close.setBackgroundColor(Color.TRANSPARENT);
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(44));
        clp.topMargin = dp(3);
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
                    Math.min(getResources().getDisplayMetrics().heightPixels * 84 / 100, dp(780)));
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }
        sheet.setTranslationY(dp(34));
        sheet.setAlpha(0f);
        sheet.animate().translationY(0f).alpha(1f).setDuration(180).start();

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
                    meta.setText(duration + " • formats checked");
                    q360.detail.setText("SD • " + s360);
                    q720.detail.setText("H.264 + AAC • " + s720);
                    q1080.detail.setText("H.264 + AAC • " + s1080);
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
                    if (dialog.isShowing()) meta.setText("Options are ready • exact sizes unavailable");
                });
            }
        });
    }

    private OptionRow addOption(LinearLayout parent, String icon, String title, String detail, Runnable action) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(10), dp(9), dp(8), dp(9));
        row.setBackground(roundBg(Color.WHITE, BORDER, 15));
        if (Build.VERSION.SDK_INT >= 21) row.setElevation(dp(1));
        LinearLayout.LayoutParams rlp = fullWrap();
        rlp.bottomMargin = dp(8);
        parent.addView(row, rlp);

        TextView mark = new TextView(this);
        mark.setText(icon);
        mark.setTextColor(ACCENT_DARK);
        mark.setTextSize(icon.length() > 2 ? 12 : 19);
        mark.setTypeface(Typeface.DEFAULT_BOLD);
        mark.setGravity(Gravity.CENTER);
        mark.setBackground(roundBg(ACCENT_SOFT, ACCENT_SOFT, 13));
        row.addView(mark, new LinearLayout.LayoutParams(dp(48), dp(48)));

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams txp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        txp.leftMargin = dp(10);
        row.addView(text, txp);
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextColor(TEXT);
        t.setTextSize(14);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        text.addView(t);
        TextView d = smallText(detail);
        d.setPadding(0, dp(3), 0, 0);
        text.addView(d);

        Button b = new Button(this);
        b.setText("↓");
        b.setTextSize(17);
        b.setTextColor(Color.WHITE);
        b.setBackground(roundBg(ACCENT, ACCENT, 15));
        b.setOnClickListener(v -> action.run());
        row.addView(b, new LinearLayout.LayoutParams(dp(46), dp(46)));
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
        request.addOption("--extractor-args", "youtubetab:skip=webpage");
        YoutubeDLResponse response = YoutubeDL.getInstance().execute(request, null, null);
        String json = response.getOut();
        int a = json == null ? -1 : json.indexOf('{');
        int b = json == null ? -1 : json.lastIndexOf('}');
        if (a < 0 || b <= a) throw new Exception("Playlist information was not returned.");
        JSONObject root = new JSONObject(json.substring(a, b + 1));
        PlaylistResult result = new PlaylistResult();
        result.title = root.optString("title", "YouTube playlist");
        result.thumbnail = root.optString("thumbnail", "");
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
            item.duration = e.optInt("duration", 0);
            String webpage = e.optString("webpage_url", "");
            item.url = webpage.startsWith("http") ? webpage : "https://www.youtube.com/watch?v=" + id;
            result.entries.add(item);
        }
        return result;
    }

    private void showPlaylistSelection(PlaylistResult playlist) {
        int n = playlist.entries.size();
        boolean[] checked = new boolean[n];
        for (int i = 0; i < n; i++) checked[i] = true;

        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(18), dp(10), dp(18), dp(18));
        sheet.setBackground(roundBg(Color.WHITE, Color.WHITE, 26));

        TextView handle = new TextView(this);
        handle.setText("━");
        handle.setTextColor(Color.rgb(190, 197, 193));
        handle.setTextSize(24);
        handle.setGravity(Gravity.CENTER);
        sheet.addView(handle);

        LinearLayout playlistHead = new LinearLayout(this);
        playlistHead.setOrientation(LinearLayout.HORIZONTAL);
        playlistHead.setGravity(Gravity.CENTER_VERTICAL);
        playlistHead.setPadding(0, dp(4), 0, dp(12));
        sheet.addView(playlistHead, fullWrap());

        ImageView cover = new ImageView(this);
        cover.setScaleType(ImageView.ScaleType.CENTER_CROP);
        cover.setBackground(roundBg(SURFACE_2, BORDER, 12));
        playlistHead.addView(cover, new LinearLayout.LayoutParams(dp(106), dp(66)));

        LinearLayout headText = new LinearLayout(this);
        headText.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams htp = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        htp.leftMargin = dp(12);
        playlistHead.addView(headText, htp);

        TextView title = sectionTitle(playlist.title == null || playlist.title.trim().isEmpty()
                ? "YouTube playlist" : playlist.title);
        title.setTextSize(18);
        title.setMaxLines(2);
        headText.addView(title);
        TextView selectedText = smallText(n + " of " + n + " videos selected");
        selectedText.setPadding(0, dp(5), 0, 0);
        headText.addView(selectedText);

        String playlistCover = playlist.thumbnail;
        if ((playlistCover == null || !playlistCover.startsWith("http")) && !playlist.entries.isEmpty()) {
            PlaylistEntry first = playlist.entries.get(0);
            playlistCover = first.thumbnail != null && first.thumbnail.startsWith("http")
                    ? first.thumbnail : "https://i.ytimg.com/vi/" + first.id + "/mqdefault.jpg";
        }
        if (playlistCover != null && playlistCover.startsWith("http")) loadThumbnailAsync(playlistCover, cover);

        ListView list = new ListView(this);
        list.setDividerHeight(0);
        list.setClipToPadding(false);
        list.setPadding(0, 0, 0, dp(4));
        sheet.addView(list, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout tools = new LinearLayout(this);
        tools.setOrientation(LinearLayout.HORIZONTAL);
        tools.setGravity(Gravity.CENTER_VERTICAL);
        tools.setPadding(0, dp(8), 0, 0);
        sheet.addView(tools, fullWrap());

        Button all = new Button(this);
        all.setText("Clear all");
        all.setAllCaps(false);
        all.setTextColor(TEXT);
        all.setTypeface(Typeface.DEFAULT_BOLD);
        all.setBackground(roundBg(SURFACE_2, BORDER, 14));
        tools.addView(all, new LinearLayout.LayoutParams(0, dp(48), 1f));

        Button next = new Button(this);
        next.setText("Continue • " + n);
        next.setAllCaps(false);
        next.setTextColor(Color.WHITE);
        next.setTypeface(Typeface.DEFAULT_BOLD);
        next.setBackground(roundBg(ACCENT, ACCENT, 14));
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(0, dp(48), 1f);
        np.leftMargin = dp(8);
        tools.addView(next, np);

        Runnable update = () -> {
            int c = 0;
            for (boolean value : checked) if (value) c++;
            selectedText.setText(c + " of " + n + " videos selected");
            next.setText("Continue • " + c);
            next.setEnabled(c > 0);
            all.setText(c == n ? "Clear all" : "Select all");
        };

        PlaylistAdapter adapter = new PlaylistAdapter(playlist.entries, checked, update);
        list.setAdapter(adapter);

        all.setOnClickListener(v -> {
            int c = 0;
            for (boolean value : checked) if (value) c++;
            boolean select = c != n;
            for (int i = 0; i < n; i++) checked[i] = select;
            adapter.notifyDataSetChanged();
            update.run();
        });

        next.setOnClickListener(v -> {
            ArrayList<PlaylistEntry> selected = new ArrayList<>();
            for (int i = 0; i < n; i++) if (checked[i]) selected.add(playlist.entries.get(i));
            if (selected.isEmpty()) return;
            dialog.dismiss();
            showPlaylistQualityChooser(selected);
        });

        dialog.setContentView(sheet);
        Window w = dialog.getWindow();
        if (w != null) {
            w.setBackgroundDrawableResource(android.R.color.transparent);
            w.setGravity(Gravity.BOTTOM);
        }
        dialog.show();
        if (dialog.getWindow() != null) {
            dialog.getWindow().setLayout(WindowManager.LayoutParams.MATCH_PARENT,
                    Math.min(getResources().getDisplayMetrics().heightPixels * 90 / 100, dp(850)));
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }
        sheet.setTranslationY(dp(30));
        sheet.setAlpha(0f);
        sheet.animate().translationY(0f).alpha(1f).setDuration(170).start();
    }

    private void showPlaylistQualityChooser(ArrayList<PlaylistEntry> selected) {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(18), dp(10), dp(18), dp(20));
        sheet.setBackground(roundBg(Color.WHITE, Color.WHITE, 26));
        TextView handle = new TextView(this);
        handle.setText("━");
        handle.setTextColor(Color.rgb(190, 197, 193));
        handle.setTextSize(24);
        handle.setGravity(Gravity.CENTER);
        sheet.addView(handle);
        TextView title = sectionTitle("Download " + selected.size() + " videos");
        title.setTextSize(20);
        sheet.addView(title);
        TextView sub = smallText("One quality will be used for the selected playlist items.");
        sub.setPadding(0, dp(4), 0, dp(12));
        sheet.addView(sub);

        addOption(sheet, "360", "360p • Fast", "Smaller files", () -> {
            dialog.dismiss(); enqueuePlaylistTasks(selected, 360, 0);
        });
        addOption(sheet, "720", "720p • HD", "H.264 video + AAC audio", () -> {
            dialog.dismiss(); enqueuePlaylistTasks(selected, 720, 0);
        });
        addOption(sheet, "1080", "1080p • Full HD", "H.264 video + AAC audio", () -> {
            dialog.dismiss(); enqueuePlaylistTasks(selected, 1080, 0);
        });
        addOption(sheet, "♪", "Audio only", "Best AAC / M4A", () -> {
            dialog.dismiss(); enqueuePlaylistTasks(selected, 0, 999);
        });

        dialog.setContentView(sheet);
        Window w = dialog.getWindow();
        if (w != null) {
            w.setBackgroundDrawableResource(android.R.color.transparent);
            w.setGravity(Gravity.BOTTOM);
        }
        dialog.show();
        if (dialog.getWindow() != null) {
            dialog.getWindow().setLayout(WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.WRAP_CONTENT);
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }
    }

    private void enqueuePlaylistTasks(ArrayList<PlaylistEntry> selected, int quality, int audioKbps) {
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
            task.quality = quality;
            task.audioKbps = audioKbps;
            task.status = "WAITING";
            task.stage = "Waiting";
            task.itemProgress = 0;
            tasks.add(task);
        }
        enqueueTasks(tasks);
    }

    private VideoInfo getSingleInfo(String url) throws Exception {
        String id = getYoutubeId(url);
        String key = id == null || id.isEmpty() ? url : id;
        VideoInfo cached = infoCache.get(key);
        if (cached != null) return cached;

        YoutubeDLRequest request = new YoutubeDLRequest(url);
        request.addOption("--no-playlist");
        request.addOption("--force-ipv4");
        request.addOption("--remote-components", "ejs:github");
        request.addOption("--js-runtimes", "quickjs");
        request.addOption("--extractor-args", "youtube:player_client=default,-android_sdkless;formats=missing_pot");
        VideoInfo info = YoutubeDL.getInstance().getInfo(request);
        if (info != null) infoCache.put(key, info);
        return info;
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
        final String finishReport = lastFinalizeReport;
        runOnUiThread(() -> {
            activeTitle.setText("Queue finished");
            activeMeta.setText(finishReport == null ? "" : finishReport);
            progress.setProgress(100);
            setStatus(finishReport == null
                    ? "All queued items have been processed."
                    : "All queued items have been processed.\nLast finalize: " + finishReport);
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
        File finalFile = new File(outDir, safeFileTitle(task.title) + " [" + safeId + "] [" + task.quality + "p].mp4");

        // FAST PATH: if YouTube exposes the requested quality as one MP4 that already
        // contains H.264 video + AAC audio, download that exact format and skip muxing.
        // This is intentionally exact-height only; we never silently downgrade 720p to 360p.
        VideoFormat combined = null;
        try {
            task.stage = "Checking fast " + task.quality + "p stream";
            task.itemProgress = 1;
            runOnUiThread(() -> {
                activeTitle.setText(itemPrefix(task) + "Checking fast " + task.quality + "p stream");
                setStatus(task.playlistBatch ? playlistStatusLine(task, 1) :
                        "Looking for a ready-made MP4 with video + audio…");
                refreshQueueUi();
            });
            VideoInfo info = getSingleInfo(task.url);
            combined = findExactCombinedFormat(info, task.quality);
        } catch (Exception ignored) { }

        if (combined != null && combined.getFormatId() != null && !combined.getFormatId().trim().isEmpty()) {
            if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");
            File fastPart = new File(finalFile.getAbsolutePath() + ".part");
            if (fastPart.exists()) fastPart.delete();
            String fastPid = "rms-fast-combined-" + safeId + "-" + task.quality;
            processId = fastPid;
            YoutubeDLRequest fastReq = commonRequest(task.url);
            fastReq.addOption("-f", combined.getFormatId());
            fastReq.addOption("-o", finalFile.getAbsolutePath());
            try {
                YoutubeDL.getInstance().execute(fastReq, fastPid,
                        progressCallback(1, 99, "Downloading ready-made " + task.quality + "p MP4"));
                processId = null;
                if (cancelCurrent) throw new Exception("Canceled");
                if (!finalFile.isFile() || finalFile.length() <= 0 ||
                        !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
                    throw new Exception("Combined MP4 verification failed.");
                }
                deleteWorkFiles(workDir);
                task.stage = "Completed • no joining needed";
                task.itemProgress = 100;
                final long finalBytes = finalFile.length();
                runOnUiThread(() -> {
                    progress.setProgress(overallProgress(task, 100));
                    activeTitle.setText(itemPrefix(task) + "Completed • no joining needed");
                    activeMeta.setText(task.title + " • " + formatBytes(finalBytes));
                    setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\nNo joining needed." :
                            "Ready-made video+audio MP4 used • no joining needed.");
                    refreshQueueUi();
                });
                return;
            } catch (Exception fastError) {
                processId = null;
                if (cancelCurrent) throw fastError;
                if (finalFile.exists()) finalFile.delete();
                if (fastPart.exists()) fastPart.delete();
                // Continue with the proven separate-stream path below.
            }
        }

        String videoPid = "rms-hd-video-" + safeId + "-" + task.quality;
        processId = videoPid;
        YoutubeDLRequest videoReq = commonRequest(task.url);
        videoReq.addOption("-f", "bestvideo[height<=" + task.quality + "][ext=mp4][vcodec^=avc1]");
        videoReq.addOption("-o", new File(workDir, "video.%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(videoReq, videoPid,
                progressCallback(2, 78, "Downloading " + task.quality + "p H.264 video"));
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
                progressCallback(78, 94, "Downloading AAC audio"));
        processId = null;
        if (cancelCurrent) throw new Exception("Canceled");
        File audioFile = findCompleteFile(workDir, "audio.");
        if (audioFile == null || !hasAudioTrack(audioFile.getAbsolutePath())) throw new Exception("AAC audio stream was not created correctly.");

        task.stage = "Native joining video + audio";
        task.itemProgress = 95;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 95));
            activeTitle.setText(itemPrefix(task) + "Native joining video + audio");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 95) :
                    "Joining without re-encoding using the native MP4 engine…");
            refreshQueueUi();
        });

        File mergedTemp = new File(workDir, "merged-native.mp4");
        if (mergedTemp.exists() && !mergedTemp.delete()) throw new Exception("Could not replace temporary merged MP4.");
        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");

        long finalizeStarted = System.currentTimeMillis();
        long muxStarted = System.currentTimeMillis();
        String muxName = "Native FFmpeg";
        Exception nativeError = null;
        try {
            muxWithNativeFfmpeg(videoFile, audioFile, mergedTemp);
            if (!mergedTemp.isFile() || mergedTemp.length() <= 0 ||
                    !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {
                throw new Exception("Native FFmpeg mux verification failed.");
            }
        } catch (Exception nativeMuxError) {
            nativeError = nativeMuxError;
            if (mergedTemp.exists()) mergedTemp.delete();
            muxName = "Android fallback";
            try {
                muxWithAndroid(videoFile, audioFile, mergedTemp);
                if (!mergedTemp.isFile() || mergedTemp.length() <= 0 ||
                        !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {
                    throw new Exception("Android fallback verification failed.");
                }
            } catch (Exception fallbackError) {
                if (mergedTemp.exists()) mergedTemp.delete();
                throw new Exception("Native and Android mux both failed. Native: " + shortMessage(nativeError), fallbackError);
            }
        }
        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);

        task.stage = "Saving final MP4";
        task.itemProgress = 99;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 99));
            activeTitle.setText(itemPrefix(task) + "Saving final MP4");
            setStatus("Join finished in " + formatElapsedMs(muxMs) + " • publishing file…");
            refreshQueueUi();
        });

        long publishStarted = System.currentTimeMillis();
        moveOrCopy(mergedTemp, finalFile);
        long publishMs = Math.max(0L, System.currentTimeMillis() - publishStarted);
        if (!finalFile.isFile() || finalFile.length() <= 0 ||
                !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
            if (finalFile.exists()) finalFile.delete();
            throw new Exception("Final saved MP4 verification failed.");
        }
        long finalizeMs = Math.max(0L, System.currentTimeMillis() - finalizeStarted);

        String muxTime = formatElapsedMs(muxMs);
        String publishTime = formatElapsedMs(publishMs);
        String totalTime = formatElapsedMs(finalizeMs);
        lastFinalizeReport = muxName + " • Join " + muxTime + " • Save " + publishTime + " • Total " + totalTime;

        deleteWorkFiles(workDir);
        task.stage = "Finalize " + totalTime;
        task.itemProgress = 100;
        final long finalBytes = finalFile.length();
        final String report = lastFinalizeReport;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 100));
            activeTitle.setText(itemPrefix(task) + "Completed");
            activeMeta.setText(task.title + " • " + formatBytes(finalBytes));
            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\n" + report : report);
            Toast.makeText(this, report, Toast.LENGTH_LONG).show();
            refreshQueueUi();
        });
    }

    private VideoFormat findExactCombinedFormat(VideoInfo info, int quality) {
        if (info == null || info.getFormats() == null) return null;
        VideoFormat best = null;
        for (VideoFormat f : info.getFormats()) {
            if (f == null || f.getHeight() != quality) continue;
            String ext = f.getExt();
            String vc = f.getVcodec();
            String ac = f.getAcodec();
            String id = f.getFormatId();
            if (id == null || id.trim().isEmpty()) continue;
            if (ext == null || !"mp4".equalsIgnoreCase(ext)) continue;
            if (vc == null || !vc.toLowerCase(Locale.US).startsWith("avc1")) continue;
            if (ac == null || !ac.toLowerCase(Locale.US).startsWith("mp4a")) continue;
            if (best == null || f.getTbr() > best.getTbr()) best = f;
        }
        return best;
    }

    private YoutubeDLRequest commonRequest(String url) {
        YoutubeDLRequest request = new YoutubeDLRequest(url);
        request.addOption("--no-playlist");
        request.addOption("--no-mtime");
        request.addOption("--newline");
        request.addOption("--progress");
        request.addOption("--continue");
        request.addOption("--concurrent-fragments", "4");
        request.addOption("--http-chunk-size", "10M");
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
                refreshQueueUiThrottled();
            });
            return Unit.INSTANCE;
        };
    }


    private void muxWithNativeFfmpeg(File videoFile, File audioFile, File outputFile) throws Exception {
        if (outputFile.exists() && !outputFile.delete()) throw new Exception("Could not replace native mux output.");
        String command = "-hide_banner -loglevel error -y " +
                "-i " + ffmpegQuote(videoFile.getAbsolutePath()) + " " +
                "-i " + ffmpegQuote(audioFile.getAbsolutePath()) + " " +
                "-map 0:v:0 -map 1:a:0 -c copy -movflags +faststart " +
                ffmpegQuote(outputFile.getAbsolutePath());
        FFmpegSession session = FFmpegKit.execute(command);
        if (session == null || !ReturnCode.isSuccess(session.getReturnCode())) {
            String code = session == null || session.getReturnCode() == null ? "unknown" : session.getReturnCode().toString();
            throw new Exception("Native FFmpeg remux failed (code " + code + ").");
        }
    }

    private String ffmpegQuote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
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
            ByteBuffer buffer = ByteBuffer.allocateDirect(bufferSize);
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

    private void refreshQueueUiThrottled() {
        long now = System.currentTimeMillis();
        if (now - lastQueueUiRefreshMs < 350L) return;
        lastQueueUiRefreshMs = now;
        refreshQueueUi();
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
        if (snap.isEmpty()) {
            queueSummary.setText("Nothing is downloading right now");
        } else {
            queueSummary.setText(completed + "/" + snap.size() + " completed • " +
                    active + " active • " + waiting + " waiting" +
                    (failed > 0 ? " • " + failed + " failed" : ""));
        }

        int shown = 0;
        int hidden = 0;
        final int visibleLimit = 12;
        for (DownloadTask t : snap) {
            if ("COMPLETED".equals(t.status)) continue;
            if (shown >= visibleLimit) { hidden++; continue; }
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(13), dp(12), dp(13), dp(12));
            card.setBackground(roundBg(SURFACE, BORDER, 16));
            if (Build.VERSION.SDK_INT >= 21) card.setElevation(dp(1));
            LinearLayout.LayoutParams lp = fullWrap();
            if (shown++ > 0) lp.topMargin = dp(8);
            queueContainer.addView(card, lp);

            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            card.addView(row, fullWrap());
            TextView name = new TextView(this);
            name.setText((t.batchTotal > 1 ? t.batchIndex + "/" + t.batchTotal + "  " : "") + t.title);
            name.setTextColor(TEXT);
            name.setTextSize(14);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            name.setMaxLines(2);
            row.addView(name, new LinearLayout.LayoutParams(0,
                    LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
            String stage = t.stage == null ? t.status : t.stage;
            int badgeFill = "FAILED".equals(t.status) ? Color.rgb(255, 236, 236) :
                    ("DOWNLOADING".equals(t.status) ? ACCENT_SOFT : SURFACE_2);
            int badgeText = "FAILED".equals(t.status) ? Color.rgb(177, 46, 46) :
                    ("DOWNLOADING".equals(t.status) ? ACCENT_DARK : MUTED);
            row.addView(pill(stage.length() > 18 ? t.status : stage, badgeFill, badgeText));

            String mode = t.audioKbps > 0 ? "Audio only" : t.quality + "p video";
            TextView meta = smallText(mode + (t.error == null ? "" : " • " + t.error));
            meta.setPadding(0, dp(5), 0, 0);
            card.addView(meta);
            if ("DOWNLOADING".equals(t.status)) {
                ProgressBar itemBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
                itemBar.setMax(100);
                itemBar.setProgress(Math.max(0, Math.min(100, t.itemProgress)));
                LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, dp(7));
                bp.topMargin = dp(9);
                card.addView(itemBar, bp);
                TextView pct = smallText(t.itemProgress + "% current item" +
                        (t.batchTotal > 1 ? " • " + overallProgress(t, t.itemProgress) + "% playlist" : ""));
                pct.setPadding(0, dp(4), 0, 0);
                card.addView(pct);
            }
        }
        if (shown == 0) {
            LinearLayout empty = new LinearLayout(this);
            empty.setOrientation(LinearLayout.VERTICAL);
            empty.setGravity(Gravity.CENTER);
            empty.setPadding(dp(18), dp(28), dp(18), dp(28));
            empty.setBackground(roundBg(SURFACE, BORDER, 18));
            TextView icon = new TextView(this);
            icon.setText("✓");
            icon.setTextColor(ACCENT_DARK);
            icon.setTextSize(26);
            icon.setGravity(Gravity.CENTER);
            empty.addView(icon);
            TextView t = sectionTitle("Queue is clear");
            t.setTextSize(15);
            t.setGravity(Gravity.CENTER);
            empty.addView(t);
            TextView m = smallText("New downloads will appear here.");
            m.setGravity(Gravity.CENTER);
            m.setPadding(0, dp(4), 0, 0);
            empty.addView(m);
            queueContainer.addView(empty, fullWrap());
        } else if (hidden > 0) {
            TextView more = smallText("+ " + hidden + " more queued items");
            more.setGravity(Gravity.CENTER);
            more.setPadding(0, dp(12), 0, dp(4));
            queueContainer.addView(more, fullWrap());
        }
    }

    private void refreshCompletedUi() {
        if (completedContainer == null || completedSummary == null) return;
        completedContainer.removeAllViews();
        File outDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES), "Rizwan Media Saver");
        ArrayList<File> files = new ArrayList<>();
        collectMediaFiles(outDir, files);
        files.sort((a, b) -> Long.compare(b.lastModified(), a.lastModified()));
        completedSummary.setText(files.size() + (files.size() == 1 ? " saved file" : " saved files"));
        SimpleDateFormat sdf = new SimpleDateFormat("dd MMM • h:mm a", Locale.getDefault());
        int show = Math.min(files.size(), 40);
        for (int i = 0; i < show; i++) {
            File f = files.get(i);
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.HORIZONTAL);
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(dp(11), dp(11), dp(11), dp(11));
            card.setBackground(roundBg(SURFACE, BORDER, 16));
            if (Build.VERSION.SDK_INT >= 21) card.setElevation(dp(1));
            LinearLayout.LayoutParams lp = fullWrap();
            if (i > 0) lp.topMargin = dp(8);
            completedContainer.addView(card, lp);
            TextView icon = new TextView(this);
            icon.setText(f.getName().toLowerCase(Locale.US).endsWith(".m4a") ? "♪" : "▶");
            icon.setTextColor(ACCENT_DARK);
            icon.setTextSize(18);
            icon.setGravity(Gravity.CENTER);
            icon.setBackground(roundBg(ACCENT_SOFT, ACCENT_SOFT, 13));
            card.addView(icon, new LinearLayout.LayoutParams(dp(48), dp(48)));
            LinearLayout text = new LinearLayout(this);
            text.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams tx = new LinearLayout.LayoutParams(0,
                    LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
            tx.leftMargin = dp(10);
            card.addView(text, tx);
            TextView name = new TextView(this);
            name.setText(f.getName());
            name.setTextColor(TEXT);
            name.setTextSize(13);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            name.setMaxLines(2);
            text.addView(name);
            TextView meta = smallText(formatBytes(f.length()) + " • " + sdf.format(new Date(f.lastModified())));
            meta.setPadding(0, dp(4), 0, 0);
            text.addView(meta);
        }
        if (files.isEmpty()) {
            TextView empty = smallText("Completed downloads will appear here.");
            empty.setGravity(Gravity.CENTER);
            empty.setPadding(0, dp(30), 0, dp(30));
            completedContainer.addView(empty, fullWrap());
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
        if (url == null || url.trim().isEmpty() || image == null) return;
        Bitmap cached = thumbnailCache.get(url);
        image.setTag(url);
        if (cached != null) {
            image.setImageBitmap(cached);
            return;
        }
        imageExecutor.execute(() -> {
            try {
                Bitmap b = loadBitmap(url);
                if (b != null) {
                    thumbnailCache.put(url, b);
                    runOnUiThread(() -> {
                        Object tag = image.getTag();
                        if (tag != null && url.equals(tag.toString())) image.setImageBitmap(b);
                    });
                }
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
        View incoming = home ? homePage : downloadsPage;
        View outgoing = home ? downloadsPage : homePage;
        outgoing.setVisibility(View.GONE);
        incoming.setVisibility(View.VISIBLE);
        incoming.setAlpha(0.72f);
        incoming.setTranslationY(dp(7));
        incoming.animate().alpha(1f).translationY(0f).setDuration(150).start();
        homeNav.setTextColor(home ? ACCENT_DARK : MUTED);
        downloadsNav.setTextColor(home ? MUTED : ACCENT_DARK);
        homeNav.setTypeface(home ? Typeface.DEFAULT_BOLD : Typeface.DEFAULT);
        downloadsNav.setTypeface(home ? Typeface.DEFAULT : Typeface.DEFAULT_BOLD);
        homeNav.setBackground(roundBg(home ? ACCENT_SOFT : Color.TRANSPARENT,
                home ? ACCENT_SOFT : Color.TRANSPARENT, 14));
        downloadsNav.setBackground(roundBg(home ? Color.TRANSPARENT : ACCENT_SOFT,
                home ? Color.TRANSPARENT : ACCENT_SOFT, 14));
        if (!home) {
            if (downloadsShowingActive) refreshQueueUi(); else refreshCompletedUi();
        }
    }

    private Button navButton(String icon, String label) {
        Button b = new Button(this);
        b.setText(icon + "\n" + label);
        b.setAllCaps(false);
        b.setTextSize(11);
        b.setGravity(Gravity.CENTER);
        b.setTextColor(MUTED);
        b.setBackground(roundBg(Color.TRANSPARENT, Color.TRANSPARENT, 14));
        return b;
    }

    private Button platformButton(String name, boolean enabled) {
        Button b = new Button(this);
        b.setText(name + (enabled ? "" : "  soon"));
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setTextColor(enabled ? Color.WHITE : MUTED);
        b.setBackground(roundBg(enabled ? DARK : SURFACE_2, enabled ? DARK : BORDER, 15));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(40));
        lp.rightMargin = dp(7);
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

    private String formatElapsedMs(long ms) {
        if (ms < 1000L) return ms + " ms";
        return String.format(Locale.US, "%.1f s", ms / 1000.0);
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
        imageExecutor.shutdownNow();
        downloadExecutor.shutdownNow();
        super.onDestroy();
    }

    private class PlaylistAdapter extends BaseAdapter {
        private final ArrayList<PlaylistEntry> items;
        private final boolean[] checked;
        private final Runnable changed;

        PlaylistAdapter(ArrayList<PlaylistEntry> items, boolean[] checked, Runnable changed) {
            this.items = items;
            this.checked = checked;
            this.changed = changed;
        }

        @Override public int getCount() { return items.size(); }
        @Override public Object getItem(int position) { return items.get(position); }
        @Override public long getItemId(int position) { return position; }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            PlaylistRowHolder h;
            if (convertView == null) {
                LinearLayout row = new LinearLayout(V2MainActivity.this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);
                row.setPadding(dp(8), dp(8), dp(8), dp(8));
                row.setBackground(roundBg(Color.WHITE, BORDER, 14));
                if (Build.VERSION.SDK_INT >= 21) row.setElevation(dp(1));

                ImageView thumb = new ImageView(V2MainActivity.this);
                thumb.setScaleType(ImageView.ScaleType.CENTER_CROP);
                thumb.setBackground(roundBg(SURFACE_2, BORDER, 10));
                row.addView(thumb, new LinearLayout.LayoutParams(dp(96), dp(60)));

                LinearLayout text = new LinearLayout(V2MainActivity.this);
                text.setOrientation(LinearLayout.VERTICAL);
                LinearLayout.LayoutParams tx = new LinearLayout.LayoutParams(0,
                        LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
                tx.leftMargin = dp(11);
                row.addView(text, tx);

                TextView title = new TextView(V2MainActivity.this);
                title.setTextColor(TEXT);
                title.setTextSize(14);
                title.setTypeface(Typeface.DEFAULT_BOLD);
                title.setMaxLines(2);
                text.addView(title);

                TextView meta = smallText("");
                meta.setPadding(0, dp(4), 0, 0);
                text.addView(meta);

                CheckBox check = new CheckBox(V2MainActivity.this);
                check.setClickable(false);
                check.setFocusable(false);
                row.addView(check, new LinearLayout.LayoutParams(dp(48), dp(48)));

                h = new PlaylistRowHolder(thumb, title, meta, check);
                row.setTag(h);
                convertView = row;
            } else {
                h = (PlaylistRowHolder) convertView.getTag();
            }

            PlaylistEntry e = items.get(position);
            h.title.setText(e.title == null || e.title.trim().isEmpty() ? "YouTube video" : e.title);
            h.meta.setText((position + 1) + " of " + items.size() +
                    (e.duration > 0 ? " • " + formatDuration(e.duration) : " • YouTube"));
            h.check.setChecked(checked[position]);

            String thumbnail = e.thumbnail;
            if (thumbnail == null || !thumbnail.startsWith("http")) {
                thumbnail = "https://i.ytimg.com/vi/" + e.id + "/mqdefault.jpg";
            }
            h.thumb.setImageDrawable(null);
            loadThumbnailAsync(thumbnail, h.thumb);

            final int itemPosition = position;
            convertView.setOnClickListener(v -> {
                checked[itemPosition] = !checked[itemPosition];
                notifyDataSetChanged();
                if (changed != null) changed.run();
            });

            return convertView;
        }
    }

    private static class PlaylistRowHolder {
        final ImageView thumb;
        final TextView title;
        final TextView meta;
        final CheckBox check;
        PlaylistRowHolder(ImageView thumb, TextView title, TextView meta, CheckBox check) {
            this.thumb = thumb;
            this.title = title;
            this.meta = meta;
            this.check = check;
        }
    }

    private static class PlaylistEntry {
        String id;
        String title;
        String url;
        String thumbnail;
        int duration;
    }

    private static class PlaylistResult {
        String title;
        String thumbnail;
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
