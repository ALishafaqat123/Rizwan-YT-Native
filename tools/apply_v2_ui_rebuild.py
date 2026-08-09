from pathlib import Path

src_path = Path('app/src/main/java/com/rizwan/ytnativefoundation/FastSmartMainActivity.java')
dst_path = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = src_path.read_text(encoding='utf-8')


def replace_between(text, start_marker, end_marker, replacement):
    a = text.find(start_marker)
    if a < 0:
        raise SystemExit('Missing start marker: ' + start_marker)
    b = text.find(end_marker, a)
    if b < 0:
        raise SystemExit('Missing end marker: ' + end_marker)
    return text[:a] + replacement + '\n\n' + text[b:]

s = s.replace('import android.widget.Button;\n', 'import android.widget.ArrayAdapter;\nimport android.widget.Button;\n', 1)
s = s.replace('public class FastSmartMainActivity extends Activity {', 'public class V2MainActivity extends Activity {', 1)

old_colors = '''    private static final int BG = Color.rgb(249, 250, 248);\n    private static final int SURFACE = Color.WHITE;\n    private static final int SURFACE_2 = Color.rgb(244, 246, 244);\n    private static final int TEXT = Color.rgb(19, 23, 21);\n    private static final int MUTED = Color.rgb(111, 120, 115);\n    private static final int ACCENT = Color.rgb(35, 196, 132);\n    private static final int ACCENT_DARK = Color.rgb(15, 111, 76);\n    private static final int BORDER = Color.rgb(225, 230, 227);'''
new_colors = '''    private static final int BG = Color.rgb(246, 248, 247);\n    private static final int SURFACE = Color.WHITE;\n    private static final int SURFACE_2 = Color.rgb(240, 244, 242);\n    private static final int TEXT = Color.rgb(20, 25, 22);\n    private static final int MUTED = Color.rgb(101, 111, 106);\n    private static final int ACCENT = Color.rgb(18, 176, 111);\n    private static final int ACCENT_DARK = Color.rgb(10, 112, 70);\n    private static final int ACCENT_SOFT = Color.rgb(231, 248, 239);\n    private static final int DARK = Color.rgb(24, 30, 27);\n    private static final int BORDER = Color.rgb(224, 230, 227);'''
if old_colors not in s:
    raise SystemExit('Color block changed unexpectedly')
s = s.replace(old_colors, new_colors, 1)

field_anchor = '    private TextView completedSummary;\n'
field_extra = '''    private TextView completedSummary;\n    private LinearLayout statusCard;\n    private LinearLayout activeSection;\n    private LinearLayout completedSection;\n    private Button activeTab;\n    private Button completedTab;\n    private boolean downloadsShowingActive = true;\n    private volatile long lastQueueUiRefreshMs = 0L;\n'''
if field_anchor not in s:
    raise SystemExit('Field anchor missing')
s = s.replace(field_anchor, field_extra, 1)

new_build_ui = r'''    private void buildUi() {
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
    }'''
s = replace_between(s, '    private void buildUi() {', '    private LinearLayout buildHomePage() {', new_build_ui)

new_home = r'''    private LinearLayout buildHomePage() {
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
    }'''
s = replace_between(s, '    private LinearLayout buildHomePage() {', '    private LinearLayout buildDownloadsPage() {', new_home)

new_downloads = r'''    private LinearLayout buildDownloadsPage() {
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
    }'''
s = replace_between(s, '    private LinearLayout buildDownloadsPage() {', '    private void initEngine() {', new_downloads)

new_clipboard = r'''    private void showCopiedLinkPrompt(String url) {
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
    }'''
s = replace_between(s, '    private void showCopiedLinkPrompt(String url) {', '    private void pasteFromClipboard() {', new_clipboard)

new_options = r'''    private void showVideoOptionsFast(String url, boolean fromClipboard) {
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
    }'''
s = replace_between(s, '    private void showVideoOptionsFast(String url, boolean fromClipboard) {', '    private OptionRow addOption(', new_options)

new_add_option = r'''    private OptionRow addOption(LinearLayout parent, String icon, String title, String detail, Runnable action) {
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
    }'''
s = replace_between(s, '    private OptionRow addOption(', '    private void loadPlaylistFast(', new_add_option)

new_playlist_select = r'''    private void showPlaylistSelection(PlaylistResult playlist) {
        int n = playlist.entries.size();
        String[] labels = new String[n];
        for (int i = 0; i < n; i++) labels[i] = (i + 1) + ".  " + playlist.entries.get(i).title;

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
        TextView title = sectionTitle(playlist.title == null ? "Playlist" : playlist.title);
        title.setTextSize(19);
        title.setMaxLines(2);
        sheet.addView(title);
        TextView selectedText = smallText(n + " of " + n + " videos selected");
        selectedText.setPadding(0, dp(4), 0, dp(9));
        sheet.addView(selectedText);

        ListView list = new ListView(this);
        list.setChoiceMode(ListView.CHOICE_MODE_MULTIPLE);
        list.setDividerHeight(0);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_list_item_multiple_choice, labels);
        list.setAdapter(adapter);
        for (int i = 0; i < n; i++) list.setItemChecked(i, true);
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
        all.setBackground(roundBg(SURFACE_2, BORDER, 14));
        tools.addView(all, new LinearLayout.LayoutParams(0, dp(46), 1f));
        Button next = new Button(this);
        next.setText("Continue • " + n);
        next.setAllCaps(false);
        next.setTextColor(Color.WHITE);
        next.setTypeface(Typeface.DEFAULT_BOLD);
        next.setBackground(roundBg(ACCENT, ACCENT, 14));
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(0, dp(46), 1f);
        np.leftMargin = dp(8);
        tools.addView(next, np);

        Runnable update = () -> {
            int c = 0;
            for (int i = 0; i < n; i++) if (list.isItemChecked(i)) c++;
            selectedText.setText(c + " of " + n + " videos selected");
            next.setText("Continue • " + c);
            next.setEnabled(c > 0);
            all.setText(c == n ? "Clear all" : "Select all");
        };
        list.setOnItemClickListener((p, v, position, id) -> update.run());
        all.setOnClickListener(v -> {
            int c = 0;
            for (int i = 0; i < n; i++) if (list.isItemChecked(i)) c++;
            boolean select = c != n;
            for (int i = 0; i < n; i++) list.setItemChecked(i, select);
            update.run();
        });
        next.setOnClickListener(v -> {
            ArrayList<PlaylistEntry> selected = new ArrayList<>();
            for (int i = 0; i < n; i++) if (list.isItemChecked(i)) selected.add(playlist.entries.get(i));
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
                    Math.min(getResources().getDisplayMetrics().heightPixels * 88 / 100, dp(820)));
            dialog.getWindow().setGravity(Gravity.BOTTOM);
        }
        sheet.setTranslationY(dp(30));
        sheet.setAlpha(0f);
        sheet.animate().translationY(0f).alpha(1f).setDuration(180).start();
    }'''
s = replace_between(s, '    private void showPlaylistSelection(PlaylistResult playlist) {', '    private void showPlaylistQualityChooser(', new_playlist_select)

new_playlist_quality = r'''    private void showPlaylistQualityChooser(ArrayList<PlaylistEntry> selected) {
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
    }'''
s = replace_between(s, '    private void showPlaylistQualityChooser(ArrayList<PlaylistEntry> selected) {', '    private VideoInfo getSingleInfo(', new_playlist_quality)

# Throttle expensive queue-card rebuilds during progress callbacks.
s = s.replace('                refreshQueueUi();\n            });\n            return Unit.INSTANCE;\n        };\n    }',
              '                refreshQueueUiThrottled();\n            });\n            return Unit.INSTANCE;\n        };\n    }', 1)

new_queue = r'''    private void refreshQueueUiThrottled() {
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
    }'''
s = replace_between(s, '    private void refreshQueueUi() {', '    private void refreshCompletedUi() {', new_queue)

new_completed = r'''    private void refreshCompletedUi() {
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
    }'''
s = replace_between(s, '    private void refreshCompletedUi() {', '    private void collectMediaFiles(', new_completed)

new_show_page = r'''    private void showPage(boolean home) {
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
    }'''
s = replace_between(s, '    private void showPage(boolean home) {', '    private Button navButton(', new_show_page)

new_nav = r'''    private Button navButton(String icon, String label) {
        Button b = new Button(this);
        b.setText(icon + "\n" + label);
        b.setAllCaps(false);
        b.setTextSize(11);
        b.setGravity(Gravity.CENTER);
        b.setTextColor(MUTED);
        b.setBackground(roundBg(Color.TRANSPARENT, Color.TRANSPARENT, 14));
        return b;
    }'''
s = replace_between(s, '    private Button navButton(', '    private Button platformButton(', new_nav)

new_platform = r'''    private Button platformButton(String name, boolean enabled) {
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
    }'''
s = replace_between(s, '    private Button platformButton(', '    private LinearLayout wrapScroll(', new_platform)

# Write V2 activity, leave v1.8.2 activity untouched.
dst_path.write_text(s, encoding='utf-8')

manifest = Path('app/src/main/AndroidManifest.xml')
ms = manifest.read_text(encoding='utf-8')
if '.FastSmartMainActivity' not in ms:
    raise SystemExit('Unexpected launcher in manifest')
ms = ms.replace('.FastSmartMainActivity', '.V2MainActivity', 1)
manifest.write_text(ms, encoding='utf-8')

gradle = Path('app/build.gradle')
gs = gradle.read_text(encoding='utf-8')
if 'versionCode 182' not in gs:
    raise SystemExit('Unexpected versionCode')
gs = gs.replace('versionCode 182', 'versionCode 200', 1)
gs = gs.replace("versionName '1.8.2-progress-polish'", "versionName '2.0.0-ui-rebuild-preview'", 1)
gradle.write_text(gs, encoding='utf-8')

print('V2 UI rebuild source generated successfully')
