from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/FastSmartMainActivity.java')
s = p.read_text(encoding='utf-8')

def repl(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'Missing source pattern: {label}')
    s = s.replace(old, new, 1)

repl('TextView qh = sectionTitle("Queue");\n        qh.setTextSize(17);',
     'TextView qh = sectionTitle("Active & Queue");\n        qh.setTextSize(17);',
     'downloads heading')
repl('queueSummary = smallText("No queued items");',
     'queueSummary = smallText("No active or queued items");',
     'queue summary default')

old = '''    private void showPlaylistQualityChooser(ArrayList<PlaylistEntry> selected) {
        String[] options = {"360p SD", "720p HD", "1080p Full HD", "Audio only • Best AAC/M4A"};
        final int[] chosen = {1};
        new AlertDialog.Builder(this)
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
                            task.quality = 0;
                            task.audioKbps = 999;
                        } else {
                            task.quality = chosen[0] == 0 ? 360 : chosen[0] == 1 ? 720 : 1080;
                            task.audioKbps = 0;
                        }
                        task.status = "WAITING";
                        tasks.add(task);
                    }
                    enqueueTasks(tasks);
                })
                .setNegativeButton("Back", null)
                .show();
    }
'''
new = '''    private void showPlaylistQualityChooser(ArrayList<PlaylistEntry> selected) {
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
'''
repl(old, new, 'playlist quality chooser')

repl('''        task.status = "WAITING";
        ArrayList<DownloadTask> tasks = new ArrayList<>();''',
     '''        task.status = "WAITING";
        task.stage = "Waiting";
        task.itemProgress = 0;
        task.batchIndex = 1;
        task.batchTotal = 1;
        ArrayList<DownloadTask> tasks = new ArrayList<>();''',
     'single task defaults')

old = '''    private void processQueue() {
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
            setStatus("All queued items have been processed.");
            refreshQueueUi();
            refreshCompletedUi();
        });
    }
'''
new = '''    private void processQueue() {
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
'''
repl(old, new, 'processQueue')

old = '''    private DownloadTask nextWaitingTask() {
        synchronized (queue) {
            for (DownloadTask t : queue) if ("WAITING".equals(t.status)) return t;
        }
        return null;
    }
'''
new = '''    private DownloadTask nextWaitingTask() {
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
'''
repl(old, new, 'progress helpers')

repl('''        runOnUiThread(() -> {
            progress.setProgress(96);
            setStatus("Joining video + audio with Android MediaMuxer...");
        });''',
     '''        task.stage = "Joining video + audio";
        task.itemProgress = 96;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 96));
            activeTitle.setText(itemPrefix(task) + "Joining video + audio");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 96) :
                    "Joining video + audio with Android MediaMuxer…");
            refreshQueueUi();
        });''',
     'joining stage')

repl('''        deleteWorkFiles(workDir);
        runOnUiThread(() -> progress.setProgress(100));''',
     '''        deleteWorkFiles(workDir);
        task.stage = "Finalizing";
        task.itemProgress = 100;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 100));
            activeTitle.setText(itemPrefix(task) + "Finalizing");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) : "Final MP4 verified.");
            refreshQueueUi();
        });''',
     'finalizing stage')

old = '''    private Function3<Float, Long, String, Unit> progressCallback(int start, int end, String label) {
        return (pct, eta, line) -> {
            float raw = pct == null || pct < 0 ? 0 : Math.min(100f, pct);
            int scaled = start + Math.round((end - start) * (raw / 100f));
            String safeLine = line == null ? "" : line;
            String lower = safeLine.toLowerCase(Locale.US);
            boolean resuming = lower.contains("resuming download") || lower.contains("resume at") || lower.contains("continuing at");
            runOnUiThread(() -> {
                progress.setProgress(Math.max(start, Math.min(end, scaled)));
                String etaText = eta != null && eta >= 0 ? " • ETA " + eta + "s" : "";
                activeTitle.setText(resuming ? "Resuming previous download" : label);
                setStatus(Math.round(raw) + "%" + etaText + "\\n" + safeLine);
            });
            return Unit.INSTANCE;
        };
    }
'''
new = '''    private Function3<Float, Long, String, Unit> progressCallback(int start, int end, String label) {
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
                    setStatus(playlistStatusLine(active, itemProgress) + etaText + "\\n" + safeLine);
                } else {
                    setStatus(Math.round(raw) + "%" + etaText + "\\n" + safeLine);
                }
                refreshQueueUi();
            });
            return Unit.INSTANCE;
        };
    }
'''
repl(old, new, 'progress callback')

old = '''    private void refreshQueueUi() {
        if (queueContainer == null || queueSummary == null) return;
        queueContainer.removeAllViews();
        ArrayList<DownloadTask> snap;
        synchronized (queue) { snap = new ArrayList<>(queue); }
        int waiting = 0, failed = 0, active = 0;
        for (DownloadTask t : snap) {
            if ("WAITING".equals(t.status)) waiting++;
            else if ("FAILED".equals(t.status)) failed++;
            else if ("DOWNLOADING".equals(t.status)) active++;
        }
        queueSummary.setText(active + " active • " + waiting + " waiting • " + failed + " failed");
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
            name.setText(t.title);
            name.setTextColor(TEXT);
            name.setTextSize(14);
            name.setTypeface(Typeface.DEFAULT_BOLD);
            name.setMaxLines(2);
            card.addView(name);
            String mode = t.audioKbps > 0 ? "Audio only" : t.quality + "p video";
            TextView meta = smallText(mode + " • " + t.status + (t.error == null ? "" : "\\n" + t.error));
            meta.setPadding(0, dp(4), 0, 0);
            card.addView(meta);
        }
        if (shown == 0) queueContainer.addView(smallText("No active or waiting items."));
    }
'''
new = '''    private void refreshQueueUi() {
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
            TextView meta = smallText(mode + " • " + stage + (t.error == null ? "" : "\\n" + t.error));
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
'''
repl(old, new, 'queue UI')

old = '''    private static class DownloadTask {
        String id;
        String title;
        String url;
        int quality;
        int audioKbps;
        String status;
        String error;
    }
'''
new = '''    private static class DownloadTask {
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
'''
repl(old, new, 'DownloadTask fields')

p.write_text(s, encoding='utf-8')

g = Path('app/build.gradle')
gs = g.read_text(encoding='utf-8')
if "versionCode 181" not in gs or "versionName '1.8.1-fast-analyze-playlist'" not in gs:
    raise SystemExit('Unexpected build.gradle version')
gs = gs.replace('versionCode 181', 'versionCode 182')
gs = gs.replace("versionName '1.8.1-fast-analyze-playlist'", "versionName '1.8.2-progress-polish'")
g.write_text(gs, encoding='utf-8')

w = Path('.github/workflows/build-apk.yml')
ws = w.read_text(encoding='utf-8')
ws = ws.replace('v1.8.1-aligned-unsigned.apk', 'v1.8.2-aligned-unsigned.apk')
ws = ws.replace('v1.8.1-fast.apk', 'v1.8.2-progress-polish.apk')
ws = ws.replace("versionCode='181'", "versionCode='182'")
ws = ws.replace("versionName='1.8.1-fast-analyze-playlist'", "versionName='1.8.2-progress-polish'")
ws = ws.replace('Rizwan-Media-Saver-v1.8.1-Fast-Analyze-Playlist-Verified-APK',
                'Rizwan-Media-Saver-v1.8.2-Progress-Polish-Verified-APK')
w.write_text(ws, encoding='utf-8')

for cleanup in [Path('.github/workflows/apply-v182-progress-polish.yml'), Path('tools/apply_v182_progress_polish.py')]:
    if cleanup.exists():
        cleanup.unlink()
