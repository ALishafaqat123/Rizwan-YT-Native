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
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class SmartMainActivity extends Activity {
    private static final int BG = Color.rgb(248, 249, 247);
    private static final int SURFACE = Color.WHITE;
    private static final int SURFACE_2 = Color.rgb(242, 245, 243);
    private static final int TEXT = Color.rgb(18, 22, 20);
    private static final int MUTED = Color.rgb(112, 120, 116);
    private static final int ACCENT = Color.rgb(35, 196, 132);
    private static final int ACCENT_DARK = Color.rgb(13, 108, 74);
    private static final int BORDER = Color.rgb(225, 230, 227);

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ArrayList<DownloadTask> queue = new ArrayList<>();

    private EditText linkInput;
    private Button analyzeButton;
    private Button homeNav;
    private Button downloadsNav;
    private Button settingsNav;
    private TextView status;
    private TextView activeTitle;
    private TextView activeMeta;
    private TextView queueSummary;
    private TextView completedSummary;
    private ProgressBar progress;
    private LinearLayout homePage;
    private LinearLayout downloadsPage;
    private LinearLayout queueContainer;
    private LinearLayout completedContainer;

    private volatile boolean engineReady = false;
    private volatile boolean queueRunning = false;
    private volatile boolean cancelCurrent = false;
    private volatile String processId = null;
    private volatile DownloadTask currentTask = null;

    private String pendingClipboardUrl = null;
    private String lastClipboardUrl = null;

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
        nav.setPadding(dp(8), dp(5), dp(8), dp(7));
        nav.setBackgroundColor(Color.WHITE);

        homeNav = navButton("⌂", "Home");
        downloadsNav = navButton("↓", "Downloads");
        settingsNav = navButton("⚙", "Settings");

        nav.addView(homeNav, new LinearLayout.LayoutParams(0, dp(62), 1f));
        nav.addView(downloadsNav, new LinearLayout.LayoutParams(0, dp(62), 1f));
        nav.addView(settingsNav, new LinearLayout.LayoutParams(0, dp(62), 1f));

        homeNav.setOnClickListener(v -> showPage(true));
        downloadsNav.setOnClickListener(v -> showPage(false));
        settingsNav.setOnClickListener(v -> Toast.makeText(
                this, "Settings will be added after the download workflow is stable.",
                Toast.LENGTH_SHORT).show());

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

        TextView title = new TextView(this);
        title.setText("Rizwan Media Saver");
        title.setTextColor(TEXT);
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        header.addView(title, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        TextView noAds = pill("NO ADS", Color.rgb(231, 249, 240), ACCENT_DARK);
        header.addView(noAds);

        TextView sub = new TextView(this);
        sub.setText("Fast • private • simple");
        sub.setTextColor(MUTED);
        sub.setTextSize(13);
        LinearLayout.LayoutParams subLp = fullWrap();
        subLp.topMargin = dp(4);
        root.addView(sub, subLp);

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
        hero.setPadding(dp(16), dp(54), dp(16), dp(46));
        LinearLayout.LayoutParams heroLp = fullWrap();
        heroLp.topMargin = dp(16);
        root.addView(hero, heroLp);

        TextView logo = new TextView(this);
        logo.setText("↓");
        logo.setTextSize(33);
        logo.setGravity(Gravity.CENTER);
        logo.setTextColor(Color.WHITE);
        logo.setBackground(roundBg(ACCENT, ACCENT, 26));
        hero.addView(logo, new LinearLayout.LayoutParams(dp(70), dp(70)));

        TextView heroTitle = new TextView(this);
        heroTitle.setText("Paste a link. Pick a quality. Done.");
        heroTitle.setTextColor(TEXT);
        heroTitle.setTextSize(22);
        heroTitle.setTypeface(Typeface.DEFAULT_BOLD);
        heroTitle.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams htLp = fullWrap();
        htLp.topMargin = dp(18);
        hero.addView(heroTitle, htLp);

        TextView heroSub = new TextView(this);
        heroSub.setText("Copied YouTube links are detected automatically when you open the app.");
        heroSub.setTextColor(MUTED);
        heroSub.setTextSize(14);
        heroSub.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams hsLp = fullWrap();
        hsLp.topMargin = dp(7);
        hero.addView(heroSub, hsLp);

        LinearLayout searchCard = new LinearLayout(this);
        searchCard.setOrientation(LinearLayout.HORIZONTAL);
        searchCard.setGravity(Gravity.CENTER_VERTICAL);
        searchCard.setPadding(dp(8), dp(8), dp(8), dp(8));
        searchCard.setBackground(roundBg(Color.WHITE, BORDER, 22));
        LinearLayout.LayoutParams searchLp = fullWrap();
        searchLp.topMargin = dp(32);
        hero.addView(searchCard, searchLp);

        Button paste = new Button(this);
        paste.setText("↓");
        paste.setTextSize(20);
        paste.setTextColor(MUTED);
        paste.setBackground(roundBg(SURFACE_2, BORDER, 18));
        paste.setOnClickListener(v -> pasteFromClipboard());
        searchCard.addView(paste, new LinearLayout.LayoutParams(dp(52), dp(52)));

        linkInput = new EditText(this);
        linkInput.setHint("Paste YouTube link");
        linkInput.setHintTextColor(Color.rgb(154, 160, 157));
        linkInput.setTextColor(TEXT);
        linkInput.setTextSize(15);
        linkInput.setSingleLine(true);
        linkInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        linkInput.setBackgroundColor(Color.TRANSPARENT);
        linkInput.setPadding(dp(12), 0, dp(8), 0);
        searchCard.addView(linkInput, new LinearLayout.LayoutParams(
                0, dp(52), 1f));

        analyzeButton = new Button(this);
        analyzeButton.setText("Go");
        analyzeButton.setAllCaps(false);
        analyzeButton.setTextColor(Color.WHITE);
        analyzeButton.setTextSize(15);
        analyzeButton.setTypeface(Typeface.DEFAULT_BOLD);
        analyzeButton.setBackground(roundBg(ACCENT, ACCENT, 18));
        analyzeButton.setEnabled(false);
        analyzeButton.setOnClickListener(v -> analyzeCurrentLink(false));
        searchCard.addView(analyzeButton, new LinearLayout.LayoutParams(dp(68), dp(52)));

        LinearLayout statusCard = new LinearLayout(this);
        statusCard.setOrientation(LinearLayout.VERTICAL);
        statusCard.setPadding(dp(14), dp(14), dp(14), dp(14));
        statusCard.setBackground(roundBg(SURFACE, BORDER, 18));
        LinearLayout.LayoutParams scLp = fullWrap();
        scLp.topMargin = dp(20);
        root.addView(statusCard, scLp);

        activeTitle = new TextView(this);
        activeTitle.setText("Ready");
        activeTitle.setTextColor(TEXT);
        activeTitle.setTextSize(15);
        activeTitle.setTypeface(Typeface.DEFAULT_BOLD);
        statusCard.addView(activeTitle);

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        LinearLayout.LayoutParams pLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(10));
        pLp.topMargin = dp(10);
        statusCard.addView(progress, pLp);

        status = new TextView(this);
        status.setText("Preparing download engine...");
        status.setTextColor(MUTED);
        status.setTextSize(12);
        status.setPadding(0, dp(9), 0, 0);
        status.setMaxLines(4);
        status.setTextIsSelectable(true);
        statusCard.addView(status);

        activeMeta = new TextView(this);
        activeMeta.setText("");
        activeMeta.setTextColor(MUTED);
        activeMeta.setTextSize(12);
        activeMeta.setPadding(0, dp(5), 0, 0);
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
        sub.setPadding(0, dp(4), 0, dp(18));
        root.addView(sub);

        LinearLayout activeCard = new LinearLayout(this);
        activeCard.setOrientation(LinearLayout.VERTICAL);
        activeCard.setPadding(dp(14), dp(14), dp(14), dp(14));
        activeCard.setBackground(roundBg(SURFACE, BORDER, 18));
        root.addView(activeCard, fullWrap());

        TextView activeHead = sectionTitle("Active");
        activeHead.setTextSize(17);
        activeCard.addView(activeHead);

        TextView activeHint = smallText("The current item is also shown on Home with live progress.");
        activeHint.setPadding(0, dp(5), 0, 0);
        activeCard.addView(activeHint);

        Button cancel = new Button(this);
        cancel.setText("Cancel current item");
        cancel.setAllCaps(false);
        cancel.setTextColor(Color.rgb(171, 41, 41));
        cancel.setBackground(roundBg(Color.rgb(255, 244, 244), Color.rgb(245, 211, 211), 14));
        LinearLayout.LayoutParams cLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(46));
        cLp.topMargin = dp(10);
        activeCard.addView(cancel, cLp);
        cancel.setOnClickListener(v -> cancelActiveDownload());

        TextView qHead = sectionTitle("Queue");
        qHead.setPadding(0, dp(22), 0, 0);
        root.addView(qHead);
        queueSummary = smallText("No queued items");
        queueSummary.setPadding(0, dp(4), 0, dp(10));
        root.addView(queueSummary);

        queueContainer = new LinearLayout(this);
        queueContainer.setOrientation(LinearLayout.VERTICAL);
        root.addView(queueContainer, fullWrap());

        TextView doneHead = sectionTitle("Completed");
        doneHead.setPadding(0, dp(22), 0, 0);
        root.addView(doneHead);
        completedSummary = smallText("Checking saved files...");
        completedSummary.setPadding(0, dp(4), 0, dp(10));
        root.addView(completedSummary);

        completedContainer = new LinearLayout(this);
        completedContainer.setOrientation(LinearLayout.VERTICAL);
        root.addView(completedContainer, fullWrap());

        refreshQueueUi();
        refreshCompletedUi();
        return wrapScroll(scroll);
    }

    private LinearLayout wrapScroll(ScrollView scroll) {
        LinearLayout holder = new LinearLayout(this);
        holder.setOrientation(LinearLayout.VERTICAL);
        holder.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        return holder;
    }

    private Button navButton(String icon, String label) {
        Button b = new Button(this);
        b.setText(icon + "\n" + label);
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setGravity(Gravity.CENTER);
        b.setBackgroundColor(Color.TRANSPARENT);
        return b;
    }

    private Button platformButton(String name, boolean enabled) {
        Button b = new Button(this);
        b.setText(name + (enabled ? "" : "  · soon"));
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(enabled ? Color.WHITE : MUTED);
        b.setBackground(roundBg(enabled ? TEXT : SURFACE_2,
                enabled ? TEXT : BORDER, 16));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, dp(42));
        lp.rightMargin = dp(8);
        b.setLayoutParams(lp);
        if (!enabled) {
            b.setOnClickListener(v -> Toast.makeText(this,
                    name + " will be enabled after its download engine is tested.",
                    Toast.LENGTH_SHORT).show());
        }
        return b;
    }

    private void showPage(boolean home) {
        homePage.setVisibility(home ? View.VISIBLE : View.GONE);
        downloadsPage.setVisibility(home ? View.GONE : View.VISIBLE);
        styleNav(homeNav, home);
        styleNav(downloadsNav, !home);
        styleNav(settingsNav, false);
        if (!home) {
            refreshQueueUi();
            refreshCompletedUi();
        }
    }

    private void styleNav(Button button, boolean selected) {
        button.setTextColor(selected ? ACCENT_DARK : MUTED);
        button.setTypeface(selected ? Typeface.DEFAULT_BOLD : Typeface.DEFAULT);
    }

    private void initEngine() {
        setStatus("Preparing native download engine...");
        executor.execute(() -> {
            String note;
            try {
                YoutubeDL.getInstance().init(getApplicationContext());
                try { FFmpeg.getInstance().init(getApplicationContext()); } catch (Exception ignored) { }

                String before = YoutubeDL.getInstance().versionName(getApplicationContext());
                try {
                    YoutubeDL.UpdateStatus updateStatus = YoutubeDL.getInstance().updateYoutubeDL(
                            getApplicationContext(), YoutubeDL.UpdateChannel._NIGHTLY);
                    String after = YoutubeDL.getInstance().versionName(getApplicationContext());
                    note = "yt-dlp " + (after == null ? "updated" : after) + " · " +
                            (updateStatus == null ? "checked" : updateStatus.toString());
                } catch (Exception e) {
                    String current = YoutubeDL.getInstance().versionName(getApplicationContext());
                    note = "Using " + (current != null ? current :
                            (before != null ? before : "bundled yt-dlp"));
                }

                final String finalNote = note;
                engineReady = true;
                runOnUiThread(() -> {
                    analyzeButton.setEnabled(true);
                    activeTitle.setText("Ready");
                    setStatus(finalNote + "\nAndroid MediaMuxer ready for 720p/1080p.");
                    if (pendingClipboardUrl != null) {
                        String p = pendingClipboardUrl;
                        pendingClipboardUrl = null;
                        linkInput.setText(p);
                        analyzeUrl(p, true);
                    } else {
                        detectClipboardLink();
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
        if (engineReady && !queueRunning) {
            analyzeUrl(text, true);
        } else {
            pendingClipboardUrl = text;
        }
    }

    private String clipboardText() {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm == null || !cm.hasPrimaryClip()) return null;
            ClipData clip = cm.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0) return null;
            CharSequence text = clip.getItemAt(0).coerceToText(this);
            return text == null ? null : text.toString().trim();
        } catch (Exception e) {
            return null;
        }
    }

    private void pasteFromClipboard() {
        String text = clipboardText();
        if (text == null || text.isEmpty()) {
            Toast.makeText(this, "Clipboard is empty", Toast.LENGTH_SHORT).show();
            return;
        }
        linkInput.setText(text);
        linkInput.setSelection(linkInput.length());
        if (looksLikeYoutubeUrl(text) && engineReady) analyzeUrl(text, false);
    }

    private void analyzeCurrentLink(boolean fromClipboard) {
        String url = linkInput.getText().toString().trim();
        analyzeUrl(url, fromClipboard);
    }

    private void analyzeUrl(String url, boolean fromClipboard) {
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
            Toast.makeText(this, "A download queue is active. Add more items after it finishes.",
                    Toast.LENGTH_SHORT).show();
            return;
        }

        analyzeButton.setEnabled(false);
        activeTitle.setText("Analyzing link");
        setStatus("Reading title, formats, sizes and playlist information...");
        progress.setProgress(4);

        executor.execute(() -> {
            VideoInfo info = null;
            PlaylistResult playlist = null;
            Bitmap thumbnail = null;
            Exception singleError = null;

            try {
                if (hasPlaylistHint(url)) {
                    try { playlist = loadPlaylist(url); } catch (Exception ignored) { }
                }

                try {
                    info = getSingleInfo(url);
                    if (info != null && info.getThumbnail() != null) {
                        try { thumbnail = loadBitmap(info.getThumbnail()); } catch (Exception ignored) { }
                    }
                } catch (Exception e) {
                    singleError = e;
                }

                if (info == null && (playlist == null || playlist.entries.isEmpty())) {
                    throw singleError != null ? singleError : new Exception("No downloadable video information was found.");
                }

                final VideoInfo finalInfo = info;
                final PlaylistResult finalPlaylist = playlist;
                final Bitmap finalThumbnail = thumbnail;
                runOnUiThread(() -> {
                    analyzeButton.setEnabled(true);
                    progress.setProgress(0);
                    activeTitle.setText("Ready");
                    setStatus(finalPlaylist != null && !finalPlaylist.entries.isEmpty()
                            ? "Playlist detected • " + finalPlaylist.entries.size() + " videos"
                            : "Video ready • choose a download option");
                    showDownloadSheet(url, finalInfo, finalPlaylist, finalThumbnail, fromClipboard);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    analyzeButton.setEnabled(true);
                    progress.setProgress(0);
                    activeTitle.setText("Could not analyze");
                    setStatus(safeMessage(e));
                });
            }
        });
    }

    private VideoInfo getSingleInfo(String url) throws Exception {
        YoutubeDLRequest request = new YoutubeDLRequest(url);
        request.addOption("--no-playlist");
        request.addOption("--force-ipv4");
        request.addOption("--remote-components", "ejs:github");
        request.addOption("--js-runtimes", "quickjs");
        request.addOption("--extractor-args",
                "youtube:player_client=default,-android_sdkless;formats=missing_pot");
        return YoutubeDL.getInstance().getInfo(request);
    }

    private PlaylistResult loadPlaylist(String url) throws Exception {
        YoutubeDLRequest request = new YoutubeDLRequest(url);
        request.addOption("--flat-playlist");
        request.addOption("--dump-single-json");
        request.addOption("--skip-download");
        request.addOption("--yes-playlist");
        request.addOption("--force-ipv4");
        request.addOption("--remote-components", "ejs:github");
        request.addOption("--js-runtimes", "quickjs");
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
            item.url = webpage.startsWith("http") ? webpage :
                    "https://www.youtube.com/watch?v=" + id;
            result.entries.add(item);
        }
        return result;
    }

    private void showDownloadSheet(String url, VideoInfo info, PlaylistResult playlist,
                                   Bitmap thumbnail, boolean fromClipboard) {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        ScrollView sheetScroll = new ScrollView(this);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(20), dp(18), dp(20), dp(24));
        sheet.setBackground(roundBg(Color.WHITE, Color.WHITE, 24));
        sheetScroll.addView(sheet);

        TextView handle = new TextView(this);
        handle.setText("━");
        handle.setTextColor(Color.rgb(195, 199, 197));
        handle.setTextSize(26);
        handle.setGravity(Gravity.CENTER);
        sheet.addView(handle);

        TextView head = sectionTitle(fromClipboard ? "Copied link detected" : "Download options");
        head.setTextSize(21);
        sheet.addView(head);

        if (info != null) {
            LinearLayout media = new LinearLayout(this);
            media.setOrientation(LinearLayout.HORIZONTAL);
            media.setGravity(Gravity.CENTER_VERTICAL);
            LinearLayout.LayoutParams mediaLp = fullWrap();
            mediaLp.topMargin = dp(14);
            sheet.addView(media, mediaLp);

            ImageView image = new ImageView(this);
            image.setScaleType(ImageView.ScaleType.CENTER_CROP);
            image.setBackground(roundBg(SURFACE_2, BORDER, 12));
            if (thumbnail != null) image.setImageBitmap(thumbnail);
            media.addView(image, new LinearLayout.LayoutParams(dp(108), dp(68)));

            LinearLayout text = new LinearLayout(this);
            text.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams textLp = new LinearLayout.LayoutParams(
                    0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
            textLp.leftMargin = dp(12);
            media.addView(text, textLp);

            TextView t = new TextView(this);
            t.setText(info.getTitle() == null ? "YouTube video" : info.getTitle());
            t.setTextColor(TEXT);
            t.setTextSize(15);
            t.setTypeface(Typeface.DEFAULT_BOLD);
            t.setMaxLines(2);
            text.addView(t);

            TextView m = smallText(info.getDuration() > 0
                    ? formatDuration(info.getDuration()) : "YouTube");
            m.setPadding(0, dp(4), 0, 0);
            text.addView(m);
        }

        if (playlist != null && !playlist.entries.isEmpty()) {
            LinearLayout playlistCard = new LinearLayout(this);
            playlistCard.setOrientation(LinearLayout.HORIZONTAL);
            playlistCard.setGravity(Gravity.CENTER_VERTICAL);
            playlistCard.setPadding(dp(13), dp(12), dp(13), dp(12));
            playlistCard.setBackground(roundBg(Color.rgb(238, 250, 244),
                    Color.rgb(198, 233, 216), 15));
            LinearLayout.LayoutParams plLp = fullWrap();
            plLp.topMargin = dp(14);
            sheet.addView(playlistCard, plLp);

            TextView plText = new TextView(this);
            plText.setText("Playlist • " + playlist.entries.size() + " videos\n" +
                    (playlist.title == null ? "YouTube playlist" : playlist.title));
            plText.setTextColor(ACCENT_DARK);
            plText.setTextSize(14);
            plText.setTypeface(Typeface.DEFAULT_BOLD);
            playlistCard.addView(plText, new LinearLayout.LayoutParams(
                    0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

            Button all = smallActionButton("Choose videos");
            playlistCard.addView(all, new LinearLayout.LayoutParams(dp(126), dp(44)));
            all.setOnClickListener(v -> {
                dialog.dismiss();
                showPlaylistSelection(playlist);
            });
        }

        if (info != null) {
            TextView vHead = sectionTitle("Video");
            vHead.setTextSize(17);
            vHead.setPadding(0, dp(18), 0, dp(8));
            sheet.addView(vHead);

            addDownloadOption(sheet, "360p", "SD • " + estimateVideoLabel(info, 360), () -> {
                dialog.dismiss();
                enqueueSingle(url, safeTitle(info), 360, 0);
            });
            addDownloadOption(sheet, "720p", "HD • " + estimateVideoLabel(info, 720), () -> {
                dialog.dismiss();
                enqueueSingle(url, safeTitle(info), 720, 0);
            });
            addDownloadOption(sheet, "1080p", "Full HD • " + estimateVideoLabel(info, 1080), () -> {
                dialog.dismiss();
                enqueueSingle(url, safeTitle(info), 1080, 0);
            });

            TextView aHead = sectionTitle("Audio only");
            aHead.setTextSize(17);
            aHead.setPadding(0, dp(18), 0, dp(8));
            sheet.addView(aHead);

            addDownloadOption(sheet, "AAC Low", "≈ 64 kbps • " + estimateAudioLabel(info, 64), () -> {
                dialog.dismiss();
                enqueueSingle(url, safeTitle(info), 0, 64);
            });
            addDownloadOption(sheet, "AAC Standard", "≈ 128 kbps • " + estimateAudioLabel(info, 128), () -> {
                dialog.dismiss();
                enqueueSingle(url, safeTitle(info), 0, 128);
            });
            addDownloadOption(sheet, "AAC Best", "Best available M4A • " + estimateAudioLabel(info, 256), () -> {
                dialog.dismiss();
                enqueueSingle(url, safeTitle(info), 0, 999);
            });
        }

        Button close = new Button(this);
        close.setText("Close");
        close.setAllCaps(false);
        close.setTextColor(MUTED);
        close.setBackgroundColor(Color.TRANSPARENT);
        LinearLayout.LayoutParams closeLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        closeLp.topMargin = dp(10);
        sheet.addView(close, closeLp);
        close.setOnClickListener(v -> dialog.dismiss());

        dialog.setContentView(sheetScroll);
        Window w = dialog.getWindow();
        if (w != null) {
            w.setBackgroundDrawableResource(android.R.color.transparent);
            w.setGravity(Gravity.BOTTOM);
        }
        dialog.show();
        if (dialog.getWindow() != null) {
            dialog.getWindow().setLayout(WindowManager.LayoutParams.MATCH_PARENT,
                    Math.min(getResources().getDisplayMetrics().heightPixels * 4 / 5, dp(720)));
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }
    }

    private void addDownloadOption(LinearLayout parent, String title, String detail, Runnable action) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(14), dp(10), dp(10), dp(10));
        row.setBackground(roundBg(SURFACE_2, BORDER, 14));
        LinearLayout.LayoutParams lp = fullWrap();
        lp.bottomMargin = dp(8);
        parent.addView(row, lp);

        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        row.addView(text, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        TextView t = new TextView(this);
        t.setText(title);
        t.setTextColor(TEXT);
        t.setTextSize(15);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        text.addView(t);

        TextView d = smallText(detail);
        d.setPadding(0, dp(3), 0, 0);
        text.addView(d);

        Button dl = new Button(this);
        dl.setText("↓");
        dl.setTextSize(20);
        dl.setTextColor(Color.WHITE);
        dl.setBackground(roundBg(ACCENT, ACCENT, 16));
        row.addView(dl, new LinearLayout.LayoutParams(dp(50), dp(50)));
        dl.setOnClickListener(v -> action.run());
    }

    private void showPlaylistSelection(PlaylistResult playlist) {
        int n = playlist.entries.size();
        String[] labels = new String[n];
        boolean[] checked = new boolean[n];
        Arrays.fill(checked, true);
        for (int i = 0; i < n; i++) {
            labels[i] = (i + 1) + ". " + playlist.entries.get(i).title;
        }

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Choose playlist videos • " + n)
                .setMultiChoiceItems(labels, checked, (d, which, isChecked) -> checked[which] = isChecked)
                .setPositiveButton("Next", null)
                .setNegativeButton("Cancel", null)
                .setNeutralButton("Deselect all", null)
                .create();

        dialog.setOnShowListener(x -> {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                boolean anyChecked = false;
                for (boolean b : checked) if (b) { anyChecked = true; break; }
                boolean newState = !anyChecked;
                ListView list = dialog.getListView();
                for (int i = 0; i < checked.length; i++) {
                    checked[i] = newState;
                    list.setItemChecked(i, newState);
                }
                dialog.getButton(AlertDialog.BUTTON_NEUTRAL)
                        .setText(newState ? "Deselect all" : "Select all");
            });

            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                ArrayList<PlaylistEntry> selected = new ArrayList<>();
                for (int i = 0; i < checked.length; i++) {
                    if (checked[i]) selected.add(playlist.entries.get(i));
                }
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
        String[] options = {
                "360p SD",
                "720p HD",
                "1080p Full HD",
                "Audio only • Best AAC/M4A"
        };
        final int[] chosen = {1};
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Download " + selected.size() + " selected items")
                .setSingleChoiceItems(options, 1, (d, which) -> chosen[0] = which)
                .setPositiveButton("Add to queue", (d, w) -> {
                    ArrayList<DownloadTask> tasks = new ArrayList<>();
                    for (PlaylistEntry e : selected) {
                        DownloadTask task = new DownloadTask();
                        task.id = e.id;
                        task.title = e.title;
                        task.url = e.url;
                        if (chosen[0] == 3) {
                            task.audioKbps = 999;
                            task.quality = 0;
                        } else {
                            task.quality = chosen[0] == 0 ? 360 : chosen[0] == 1 ? 720 : 1080;
                            task.audioKbps = 0;
                        }
                        task.status = "WAITING";
                        tasks.add(task);
                    }
                    enqueueTasks(tasks);
                })
                .setNegativeButton("Back", (d, w) -> { })
                .create();
        dialog.show();
    }

    private void enqueueSingle(String url, String title, int quality, int audioKbps) {
        DownloadTask task = new DownloadTask();
        task.id = getYoutubeId(url);
        if (task.id == null || task.id.isEmpty()) task.id = Integer.toHexString(url.hashCode());
        task.title = title;
        task.url = url;
        task.quality = quality;
        task.audioKbps = audioKbps;
        task.status = "WAITING";
        ArrayList<DownloadTask> tasks = new ArrayList<>();
        tasks.add(task);
        enqueueTasks(tasks);
    }

    private void enqueueTasks(ArrayList<DownloadTask> tasks) {
        if (!ensureStoragePermission()) return;
        synchronized (queue) {
            queue.addAll(tasks);
        }
        refreshQueueUi();
        showPage(false);
        if (!queueRunning) {
            queueRunning = true;
            executor.execute(this::processQueue);
        }
    }

    private void processQueue() {
        while (true) {
            DownloadTask task = nextWaitingTask();
            if (task == null) break;

            currentTask = task;
            cancelCurrent = false;
            task.status = "DOWNLOADING";
            runOnUiThread(() -> {
                activeTitle.setText(task.audioKbps > 0 ? "Downloading audio" : "Downloading " + task.quality + "p");
                activeMeta.setText(task.title);
                progress.setProgress(0);
                refreshQueueUi();
            });

            try {
                downloadTaskBlocking(task);
                task.status = cancelCurrent ? "CANCELED" : "COMPLETED";
            } catch (Exception e) {
                task.error = shortMessage(e);
                task.status = cancelCurrent ? "CANCELED" : "FAILED";
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
            progress.setProgress(0);
            setStatus("All queued items have been processed. Failed items remain visible in Downloads.");
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

    private void downloadTaskBlocking(DownloadTask task) throws Exception {
        File outDir = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES),
                "Rizwan Media Saver");
        if (!outDir.exists() && !outDir.mkdirs()) {
            throw new Exception("Could not create Movies/Rizwan Media Saver folder.");
        }

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
        request.addOption("-o", new File(outDir,
                "%(title).180B [%(id)s] [360p].%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(request, pid,
                progressCallback(0, 100, "Downloading 360p video + audio"));
    }

    private void downloadAudioBlocking(DownloadTask task, File outDir) throws Exception {
        File audioDir = new File(outDir, "Audio");
        if (!audioDir.exists() && !audioDir.mkdirs()) throw new Exception("Could not create Audio folder.");

        String selector;
        String label;
        if (task.audioKbps <= 64) {
            selector = "bestaudio[ext=m4a][acodec^=mp4a][abr<=70]/worstaudio[ext=m4a][acodec^=mp4a]";
            label = "AAC Low";
        } else if (task.audioKbps <= 128) {
            selector = "bestaudio[ext=m4a][acodec^=mp4a][abr<=140]/bestaudio[ext=m4a][acodec^=mp4a]";
            label = "AAC Standard";
        } else {
            selector = "bestaudio[ext=m4a][acodec^=mp4a]/bestaudio[ext=m4a]";
            label = "AAC Best";
        }

        String pid = "rms-audio-" + UUID.randomUUID();
        processId = pid;
        YoutubeDLRequest request = commonRequest(task.url);
        request.addOption("-f", selector);
        request.addOption("-o", new File(audioDir,
                "%(title).180B [%(id)s] [audio].%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(request, pid,
                progressCallback(0, 100, "Downloading " + label));
    }

    private void downloadHdBlocking(DownloadTask task, File outDir) throws Exception {
        String safeId = sanitize(task.id == null ? Integer.toHexString(task.url.hashCode()) : task.id);
        File workRoot = new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "hd-work");
        File workDir = new File(workRoot, safeId + "-" + task.quality + "p");
        if (!workDir.exists()) workDir.mkdirs();

        File mergedTemp = new File(workDir, "merged-final.mp4");
        File finalFile = new File(outDir,
                safeFileTitle(task.title) + " [" + safeId + "] [" + task.quality + "p].mp4");

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
        if (videoFile == null || !hasVideoTrack(videoFile.getAbsolutePath())) {
            throw new Exception("HD video stream was not created correctly.");
        }

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
        if (audioFile == null || !hasAudioTrack(audioFile.getAbsolutePath())) {
            throw new Exception("AAC audio stream was not created correctly.");
        }

        runOnUiThread(() -> {
            progress.setProgress(96);
            setStatus("Joining video + audio with Android MediaMuxer...");
        });

        if (mergedTemp.exists()) mergedTemp.delete();
        muxWithAndroid(videoFile, audioFile, mergedTemp);

        if (!mergedTemp.isFile() || mergedTemp.length() <= 0 ||
                !hasVideoTrack(mergedTemp.getAbsolutePath()) ||
                !hasAudioTrack(mergedTemp.getAbsolutePath())) {
            throw new Exception("Android MediaMuxer verification failed.");
        }

        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");
        moveOrCopy(mergedTemp, finalFile);

        if (!finalFile.isFile() || !hasVideoTrack(finalFile.getAbsolutePath()) ||
                !hasAudioTrack(finalFile.getAbsolutePath())) {
            if (finalFile.exists()) finalFile.delete();
            throw new Exception("Final saved MP4 verification failed.");
        }
        deleteWorkFiles(workDir);
        runOnUiThread(() -> progress.setProgress(100));
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

    private Function3<Float, Long, String, Unit> progressCallback(int start, int end, String label) {
        return (pct, eta, line) -> {
            float raw = pct == null || pct < 0 ? 0 : Math.min(100f, pct);
            int scaled = start + Math.round((end - start) * (raw / 100f));
            String safeLine = line == null ? "" : line;
            String lower = safeLine.toLowerCase(Locale.US);
            boolean resuming = lower.contains("resuming download") ||
                    lower.contains("resume at") || lower.contains("continuing at");
            runOnUiThread(() -> {
                progress.setProgress(Math.max(start, Math.min(end, scaled)));
                String etaText = eta != null && eta >= 0 ? (" • ETA " + eta + "s") : "";
                String phase = resuming ? "Resuming previous download" : label;
                activeTitle.setText(phase);
                setStatus(Math.round(raw) + "%" + etaText + "\n" + safeLine);
            });
            return Unit.INSTANCE;
        };
    }

    private void cancelActiveDownload() {
        cancelCurrent = true;
        String id = processId;
        if (id != null) {
            try { YoutubeDL.getInstance().destroyProcessById(id); } catch (Exception ignored) { }
        }
        setStatus("Cancel requested. The next queued item will continue.");
    }

    private void refreshQueueUi() {
        if (queueContainer == null || queueSummary == null) return;
        queueContainer.removeAllViews();
        ArrayList<DownloadTask> snapshot;
        synchronized (queue) { snapshot = new ArrayList<>(queue); }

        int waiting = 0, failed = 0, active = 0;
        for (DownloadTask t : snapshot) {
            if ("WAITING".equals(t.status)) waiting++;
            else if ("FAILED".equals(t.status)) failed++;
            else if ("DOWNLOADING".equals(t.status)) active++;
        }
        queueSummary.setText(active + " active • " + waiting + " waiting • " + failed + " failed");

        int shown = 0;
        for (DownloadTask t : snapshot) {
            if ("COMPLETED".equals(t.status)) continue;
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(13), dp(12), dp(13), dp(12));
            card.setBackground(roundBg(SURFACE, BORDER, 15));
            LinearLayout.LayoutParams lp = fullWrap();
            if (shown++ > 0) lp.topMargin = dp(8);
            queueContainer.addView(card, lp);

            TextView title = new TextView(this);
            title.setText(t.title);
            title.setTextColor(TEXT);
            title.setTextSize(14);
            title.setTypeface(Typeface.DEFAULT_BOLD);
            title.setMaxLines(2);
            card.addView(title);

            String mode = t.audioKbps > 0 ? "Audio only" : t.quality + "p video";
            TextView meta = smallText(mode + " • " + t.status +
                    (t.error == null ? "" : "\n" + t.error));
            meta.setPadding(0, dp(4), 0, 0);
            card.addView(meta);
        }
        if (shown == 0) {
            TextView empty = smallText("No active or waiting items.");
            empty.setPadding(dp(4), dp(8), 0, 0);
            queueContainer.addView(empty);
        }
    }

    private void refreshCompletedUi() {
        if (completedContainer == null || completedSummary == null) return;
        completedContainer.removeAllViews();
        File outDir = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES),
                "Rizwan Media Saver");
        ArrayList<File> files = new ArrayList<>();
        collectMediaFiles(outDir, files);
        files.sort((a, b) -> Long.compare(b.lastModified(), a.lastModified()));
        completedSummary.setText(files.size() + (files.size() == 1 ? " completed file" : " completed files"));

        SimpleDateFormat sdf = new SimpleDateFormat("dd MMM • h:mm a", Locale.getDefault());
        int show = Math.min(files.size(), 50);
        for (int i = 0; i < show; i++) {
            File f = files.get(i);
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.HORIZONTAL);
            card.setGravity(Gravity.CENTER_VERTICAL);
            card.setPadding(dp(12), dp(12), dp(12), dp(12));
            card.setBackground(roundBg(SURFACE, BORDER, 15));
            LinearLayout.LayoutParams lp = fullWrap();
            if (i > 0) lp.topMargin = dp(8);
            completedContainer.addView(card, lp);

            TextView mark = new TextView(this);
            mark.setText(f.getName().toLowerCase(Locale.US).endsWith(".m4a") ? "♪" : "✓");
            mark.setGravity(Gravity.CENTER);
            mark.setTextSize(20);
            mark.setTextColor(ACCENT_DARK);
            mark.setBackground(roundBg(Color.rgb(232, 249, 241), Color.rgb(205, 235, 219), 12));
            card.addView(mark, new LinearLayout.LayoutParams(dp(44), dp(44)));

            LinearLayout text = new LinearLayout(this);
            text.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams textLp = new LinearLayout.LayoutParams(
                    0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
            textLp.leftMargin = dp(11);
            card.addView(text, textLp);

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
            TextView empty = smallText("Completed videos and audio will appear here.");
            empty.setPadding(dp(4), dp(8), 0, 0);
            completedContainer.addView(empty);
        }
    }

    private void collectMediaFiles(File dir, ArrayList<File> out) {
        if (dir == null || !dir.exists()) return;
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

    private String estimateVideoLabel(VideoInfo info, int quality) {
        long bytes = estimateVideoBytes(info, quality);
        return bytes > 0 ? "≈ " + formatBytes(bytes) : "size varies";
    }

    private String estimateAudioLabel(VideoInfo info, int kbps) {
        if (info == null || info.getDuration() <= 0) return "size varies";
        int use = kbps >= 999 ? 128 : kbps;
        long bytes = (long) info.getDuration() * use * 1000L / 8L;
        return "≈ " + formatBytes(bytes);
    }

    private long estimateVideoBytes(VideoInfo info, int quality) {
        if (info == null || info.getFormats() == null) return 0;
        List<VideoFormat> formats = info.getFormats();
        VideoFormat bestVideo = null;
        VideoFormat bestCombined = null;
        VideoFormat bestAudio = null;

        for (VideoFormat f : formats) {
            String ext = safe(f.getExt());
            String vc = safe(f.getVcodec());
            String ac = safe(f.getAcodec());
            int h = f.getHeight();

            if ("m4a".equals(ext) && !"none".equals(ac) && (bestAudio == null ||
                    sizeOf(f, info.getDuration()) > sizeOf(bestAudio, info.getDuration()))) bestAudio = f;

            if (quality <= 360 && "mp4".equals(ext) && h > 0 && h <= 360 &&
                    !"none".equals(vc) && !"none".equals(ac)) {
                if (bestCombined == null || h > bestCombined.getHeight()) bestCombined = f;
            }

            if ("mp4".equals(ext) && h > 0 && h <= quality && vc.startsWith("avc1") &&
                    ("none".equals(ac) || ac.isEmpty())) {
                if (bestVideo == null || h > bestVideo.getHeight()) bestVideo = f;
            }
        }

        if (quality <= 360 && bestCombined != null) return sizeOf(bestCombined, info.getDuration());
        long v = bestVideo == null ? 0 : sizeOf(bestVideo, info.getDuration());
        long a = bestAudio == null ? 0 : sizeOf(bestAudio, info.getDuration());
        return v > 0 ? v + a : 0;
    }

    private long sizeOf(VideoFormat f, int duration) {
        if (f.getFileSize() > 0) return f.getFileSize();
        if (f.getFileSizeApproximate() > 0) return f.getFileSizeApproximate();
        if (duration > 0 && f.getTbr() > 0) return (long) duration * f.getTbr() * 1000L / 8L;
        return 0;
    }

    private String safeTitle(VideoInfo info) {
        String t = info == null ? null : info.getTitle();
        return t == null || t.trim().isEmpty() ? "YouTube video" : t.trim();
    }

    private Bitmap loadBitmap(String urlText) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(urlText).openConnection();
        c.setConnectTimeout(8000);
        c.setReadTimeout(8000);
        c.setInstanceFollowRedirects(true);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 Android RizwanMediaSaver");
        try (BufferedInputStream in = new BufferedInputStream(c.getInputStream())) {
            return BitmapFactory.decodeStream(in);
        } finally { c.disconnect(); }
    }

    private boolean hasPlaylistHint(String value) {
        try {
            Uri uri = Uri.parse(value);
            String list = uri.getQueryParameter("list");
            return (list != null && !list.isEmpty()) || value.toLowerCase(Locale.US).contains("/playlist");
        } catch (Exception e) {
            return value.toLowerCase(Locale.US).contains("list=");
        }
    }

    private boolean looksLikeYoutubeUrl(String url) {
        if (url == null) return false;
        String s = url.toLowerCase(Locale.US);
        return (s.startsWith("http://") || s.startsWith("https://")) &&
                (s.contains("youtube.com/") || s.contains("youtu.be/"));
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
                        "embed".equals(seg.get(0)) || "live".equals(seg.get(0)))) return seg.get(1);
            }
        } catch (Exception ignored) { }
        return null;
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
            if (videoMime == null || !"video/avc".equalsIgnoreCase(videoMime))
                throw new Exception("MediaMuxer requires H.264/AVC video, got: " + videoMime);
            if (audioMime == null || !audioMime.toLowerCase(Locale.US).startsWith("audio/mp4a"))
                throw new Exception("MediaMuxer requires AAC/M4A audio, got: " + audioMime);

            if (outputFile.exists() && !outputFile.delete()) throw new Exception("Could not replace temporary MP4.");
            muxer = new MediaMuxer(outputFile.getAbsolutePath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
            if (videoFormat.containsKey(MediaFormat.KEY_ROTATION)) {
                int rotation = videoFormat.getInteger(MediaFormat.KEY_ROTATION);
                if (rotation == 90 || rotation == 180 || rotation == 270) muxer.setOrientationHint(rotation);
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
                boolean useVideo = audioTime < 0 || (videoTime >= 0 && videoTime <= audioTime);
                MediaExtractor extractor = useVideo ? videoExtractor : audioExtractor;
                int muxTrack = useVideo ? videoMuxTrack : audioMuxTrack;
                buffer.clear();
                int sampleSize = extractor.readSampleData(buffer, 0);
                if (sampleSize < 0) {
                    if (useVideo) videoTime = -1; else audioTime = -1;
                    continue;
                }
                info.set(0, sampleSize, extractor.getSampleTime(), extractor.getSampleFlags());
                muxer.writeSampleData(muxTrack, buffer, info);
                extractor.advance();
                if (useVideo) videoTime = videoExtractor.getSampleTime(); else audioTime = audioExtractor.getSampleTime();
            }
            muxer.stop();
            muxerStarted = false;
        } finally {
            try { videoExtractor.release(); } catch (Exception ignored) { }
            try { audioExtractor.release(); } catch (Exception ignored) { }
            if (muxer != null) {
                if (muxerStarted) try { muxer.stop(); } catch (Exception ignored) { }
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
            if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) return Math.max(0, format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE));
        } catch (Exception ignored) { }
        return 0;
    }

    private boolean hasAudioTrack(String path) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try { extractor.setDataSource(path); return findTrack(extractor, "audio/") >= 0; }
        finally { extractor.release(); }
    }

    private boolean hasVideoTrack(String path) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try { extractor.setDataSource(path); return findTrack(extractor, "video/") >= 0; }
        finally { extractor.release(); }
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
        if (requestCode == 701 && (grantResults.length == 0 || grantResults[0] != PackageManager.PERMISSION_GRANTED))
            setStatus("Storage permission is required to save videos and audio.");
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
        tv.setPadding(dp(10), dp(6), dp(10), dp(6));
        tv.setBackground(roundBg(fill, fill, 14));
        return tv;
    }

    private Button smallActionButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setTextColor(Color.WHITE);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(roundBg(ACCENT, ACCENT, 14));
        return b;
    }

    private LinearLayout.LayoutParams fullWrap() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private GradientDrawable roundBg(int fill, int stroke, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(dp(radiusDp));
        d.setStroke(dp(1), stroke);
        return d;
    }

    private String formatDuration(int totalSeconds) {
        int h = totalSeconds / 3600;
        int m = (totalSeconds % 3600) / 60;
        int s = totalSeconds % 60;
        if (h > 0) return String.format(Locale.US, "%d:%02d:%02d", h, m, s);
        return String.format(Locale.US, "%d:%02d", m, s);
    }

    private String formatBytes(long bytes) {
        double mb = bytes / (1024.0 * 1024.0);
        if (mb >= 1024) return String.format(Locale.US, "%.2f GB", mb / 1024.0);
        if (mb < 1) return String.format(Locale.US, "%.0f KB", bytes / 1024.0);
        return String.format(Locale.US, "%.1f MB", mb);
    }

    private String safeFileTitle(String value) {
        if (value == null || value.trim().isEmpty()) return "YouTube video";
        String s = value.replaceAll("[\\\\/:*?\"<>|]", "_").trim();
        if (s.length() > 120) s = s.substring(0, 120).trim();
        return s.isEmpty() ? "YouTube video" : s;
    }

    private String sanitize(String s) {
        if (s == null) return "video";
        return s.replaceAll("[^A-Za-z0-9_-]", "_");
    }

    private String safe(String s) { return s == null ? "" : s.toLowerCase(Locale.US); }

    private String safeMessage(Throwable t) {
        String m = t.getMessage();
        return (m == null || m.trim().isEmpty()) ? t.toString() : m;
    }

    private String shortMessage(Throwable t) {
        String m = safeMessage(t).replace('\n', ' ').trim();
        return m.length() > 180 ? m.substring(0, 180) + "..." : m;
    }

    private void setStatus(String text) { if (status != null) status.setText(text); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override
    protected void onDestroy() {
        try {
            String id = processId;
            if (id != null) YoutubeDL.getInstance().destroyProcessById(id);
        } catch (Exception ignored) { }
        executor.shutdownNow();
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
    }
}
