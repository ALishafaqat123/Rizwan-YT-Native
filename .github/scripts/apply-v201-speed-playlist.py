from pathlib import Path
import re

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text(encoding='utf-8')


def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'MISSING PATTERN: {label}')
    s = s.replace(old, new, 1)

# Imports for V2 performance/cache/custom playlist rows.
once('import android.content.Context;\n', 'import android.content.Context;\nimport android.content.SharedPreferences;\n', 'SharedPreferences import')
once('import android.text.InputType;\n', 'import android.text.InputType;\nimport android.util.LruCache;\n', 'LruCache import')
once('import android.view.View;\n', 'import android.view.View;\nimport android.view.ViewGroup;\n', 'ViewGroup import')
once('import android.widget.ArrayAdapter;\n', 'import android.widget.ArrayAdapter;\nimport android.widget.BaseAdapter;\nimport android.widget.CheckBox;\n', 'adapter imports')
once('import java.util.concurrent.ExecutorService;\n', 'import java.util.concurrent.ConcurrentHashMap;\nimport java.util.concurrent.ExecutorService;\n', 'ConcurrentHashMap import')

# Separate thumbnails from heavy yt-dlp metadata and cache both in memory.
once(
'''    private final ExecutorService metadataExecutor = Executors.newFixedThreadPool(2);\n    private final ExecutorService downloadExecutor = Executors.newSingleThreadExecutor();\n    private final ArrayList<DownloadTask> queue = new ArrayList<>();\n''',
'''    private static final long YTDLP_UPDATE_INTERVAL_MS = 24L * 60L * 60L * 1000L;\n    private final ExecutorService metadataExecutor = Executors.newFixedThreadPool(2);\n    private final ExecutorService imageExecutor = Executors.newFixedThreadPool(3);\n    private final ExecutorService downloadExecutor = Executors.newSingleThreadExecutor();\n    private final ArrayList<DownloadTask> queue = new ArrayList<>();\n    private final LruCache<String, Bitmap> thumbnailCache = new LruCache<>(36);\n    private final ConcurrentHashMap<String, VideoInfo> infoCache = new ConcurrentHashMap<>();\n''',
'performance fields')

# Avoid a network self-update on every launch. First run still checks; later launches use the cached engine for 24h.
pattern = re.compile(r'    private void initEngine\(\) \{.*?\n    \}\n\n    private void detectClipboardLink\(\) \{', re.S)
replacement = r'''    private void initEngine() {
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

    private void detectClipboardLink() {'''
s, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit('FAILED initEngine replacement')

# Playlist flat extraction: keep it lightweight, but retain the useful metadata that is returned.
once('''        request.addOption("--force-ipv4");\n        YoutubeDLResponse response = YoutubeDL.getInstance().execute(request, null, null);\n''',
'''        request.addOption("--force-ipv4");\n        request.addOption("--extractor-args", "youtubetab:skip=webpage");\n        YoutubeDLResponse response = YoutubeDL.getInstance().execute(request, null, null);\n''',
'playlist lightweight extractor args')
once('''        PlaylistResult result = new PlaylistResult();\n        result.title = root.optString("title", "YouTube playlist");\n''',
'''        PlaylistResult result = new PlaylistResult();\n        result.title = root.optString("title", "YouTube playlist");\n        result.thumbnail = root.optString("thumbnail", "");\n''',
'playlist root thumbnail')
once('''            item.thumbnail = e.optString("thumbnail", "");\n            String webpage = e.optString("webpage_url", "");\n''',
'''            item.thumbnail = e.optString("thumbnail", "");\n            item.duration = e.optInt("duration", 0);\n            String webpage = e.optString("webpage_url", "");\n''',
'playlist duration')

# Replace the stock Android multiple-choice rows (which can render blank on older themes)
# with explicit V2 cards: thumbnail, black title, duration/index and a checkbox.
pattern = re.compile(r'    private void showPlaylistSelection\(PlaylistResult playlist\) \{.*?\n    \}\n\n    private void showPlaylistQualityChooser', re.S)
replacement = r'''    private void showPlaylistSelection(PlaylistResult playlist) {
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

    private void showPlaylistQualityChooser'''
s, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit('FAILED playlist selection replacement')

# Cache format metadata so reopening the same video is instant.
pattern = re.compile(r'    private VideoInfo getSingleInfo\(String url\) throws Exception \{.*?\n    \}\n\n    private void enqueueSingle', re.S)
replacement = r'''    private VideoInfo getSingleInfo(String url) throws Exception {
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

    private void enqueueSingle'''
s, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit('FAILED metadata cache replacement')

# V2-only transfer experiment. Concurrent fragments is ignored for normal non-fragmented HTTP.
# Chunked HTTP is experimental and lives only in the side-by-side V2 preview for A/B testing.
once('''        request.addOption("--continue");\n        request.addOption("--force-ipv4");\n''',
'''        request.addOption("--continue");\n        request.addOption("--concurrent-fragments", "4");\n        request.addOption("--http-chunk-size", "10M");\n        request.addOption("--force-ipv4");\n''',
'download speed options')

# Remove the second full-file disk pass: mux directly into the public final MP4.
once('''        File mergedTemp = new File(workDir, "merged-final.mp4");\n        File finalFile = new File(outDir, safeFileTitle(task.title) + " [" + safeId + "] [" + task.quality + "p].mp4");\n''',
'''        File finalFile = new File(outDir, safeFileTitle(task.title) + " [" + safeId + "] [" + task.quality + "p].mp4");\n''',
'remove merged temp file')
once('''            setStatus(task.playlistBatch ? playlistStatusLine(task, 96) :\n                    "Joining video + audio with Android MediaMuxer…");\n''',
'''            setStatus(task.playlistBatch ? playlistStatusLine(task, 96) :\n                    "Joining directly to final MP4…");\n''',
'join status')
once('''        if (mergedTemp.exists()) mergedTemp.delete();\n        muxWithAndroid(videoFile, audioFile, mergedTemp);\n        if (!mergedTemp.isFile() || mergedTemp.length() <= 0 || !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {\n            throw new Exception("Android MediaMuxer verification failed.");\n        }\n        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");\n        moveOrCopy(mergedTemp, finalFile);\n        if (!finalFile.isFile() || !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {\n            if (finalFile.exists()) finalFile.delete();\n            throw new Exception("Final saved MP4 verification failed.");\n        }\n''',
'''        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");\n        try {\n            muxWithAndroid(videoFile, audioFile, finalFile);\n            if (!finalFile.isFile() || finalFile.length() <= 0 ||\n                    !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {\n                throw new Exception("Final saved MP4 verification failed.");\n            }\n        } catch (Exception muxError) {\n            if (finalFile.exists()) finalFile.delete();\n            throw muxError;\n        }\n''',
'direct final mux')
once('ByteBuffer buffer = ByteBuffer.allocate(bufferSize);',
     'ByteBuffer buffer = ByteBuffer.allocateDirect(bufferSize);',
     'direct mux buffer')

# Thumbnail requests no longer wait behind yt-dlp; recycled playlist rows are protected by a URL tag.
pattern = re.compile(r'    private void loadThumbnailAsync\(String url, ImageView image\) \{.*?\n    \}\n\n    private Bitmap loadBitmap', re.S)
replacement = r'''    private void loadThumbnailAsync(String url, ImageView image) {
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

    private Bitmap loadBitmap'''
s, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit('FAILED thumbnail loader replacement')

# Shut down the dedicated image pool too.
once('''        metadataExecutor.shutdownNow();\n        downloadExecutor.shutdownNow();\n''',
'''        metadataExecutor.shutdownNow();\n        imageExecutor.shutdownNow();\n        downloadExecutor.shutdownNow();\n''',
'onDestroy image executor')

# Add the custom playlist adapter before the model classes.
marker = '    private static class PlaylistEntry {\n'
if marker not in s:
    raise SystemExit('MISSING PlaylistEntry marker')
adapter_code = r'''    private class PlaylistAdapter extends BaseAdapter {
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

            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
            lp.bottomMargin = dp(7);
            convertView.setLayoutParams(lp);
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

'''
s = s.replace(marker, adapter_code + marker, 1)

# Extend playlist models.
once('''        String thumbnail;\n    }\n\n    private static class PlaylistResult {\n        String title;\n''',
'''        String thumbnail;\n        int duration;\n    }\n\n    private static class PlaylistResult {\n        String title;\n        String thumbnail;\n''',
'playlist model fields')

p.write_text(s, encoding='utf-8')
print('V2.0.1 speed + playlist patch applied successfully')
