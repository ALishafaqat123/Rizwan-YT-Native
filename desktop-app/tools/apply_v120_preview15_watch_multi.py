from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 15
# 1) YouTube watch-page Download / Add to Queue button inside WebView2.
# 2) Optional 1/2/3 concurrent single-video queue workers.
# Default remains 1 for maximum stability. Playlist/channel legacy batches remain
# one process each, but may share available global slots with queued single videos.

# -----------------------------------------------------------------------------
# Fields/state
# -----------------------------------------------------------------------------
old = '    private readonly ComboBox defaultQualityBox = new();\n'
new = old + '    private readonly ComboBox concurrentDownloadsBox = new();\n'
if old not in s:
    raise SystemExit('P15 concurrent settings field anchor not found')
s = s.replace(old, new, 1)

old = '''    private readonly List<QueuedSingleDownload> queuedSingleDownloads = new();\n    private bool drainingQueuedSingles;\n'''
new = '''    private readonly List<QueuedSingleDownload> queuedSingleDownloads = new();\n    private bool drainingQueuedSingles;\n    private readonly HashSet<string> concurrentQueueActive = new(StringComparer.Ordinal);\n    private readonly Dictionary<string, CancellationTokenSource> concurrentQueueTokens = new(StringComparer.Ordinal);\n    private readonly Dictionary<string, Process> concurrentQueueProcesses = new(StringComparer.Ordinal);\n'''
if old not in s:
    raise SystemExit('P15 queue state anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Settings UI: concurrent download limit (1 default, 2, 3)
# -----------------------------------------------------------------------------
s = s.replace('var preferences = new Panel { Dock = DockStyle.Top, Height = 214,',
              'var preferences = new Panel { Dock = DockStyle.Top, Height = 264,', 1)
s = s.replace('RowCount = 3, Padding = new Padding(0, 8, 0, 0)',
              'RowCount = 4, Padding = new Padding(0, 8, 0, 0)', 1)
s = s.replace('for (var r = 0; r < 3; r++) prefGrid.RowStyles.Add(new RowStyle(SizeType.Percent, 33.33F));',
              'for (var r = 0; r < 4; r++) prefGrid.RowStyles.Add(new RowStyle(SizeType.Percent, 25F));', 1)

old = '''        prefGrid.Controls.Add(defaultLabel, 0, 2);\n        prefGrid.Controls.Add(defaultQualityBox, 1, 2);\n        preferences.Controls.Add(prefGrid);\n'''
new = '''        prefGrid.Controls.Add(defaultLabel, 0, 2);\n        prefGrid.Controls.Add(defaultQualityBox, 1, 2);\n\n        var concurrentLabel = new Label { Text = "Concurrent downloads", ForeColor = TextMain, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };\n        ConfigurePicker(concurrentDownloadsBox);\n        concurrentDownloadsBox.Items.AddRange(new object[] { "1 at a time (Most stable)", "2 at a time", "3 at a time" });\n        concurrentDownloadsBox.SelectedIndex = 0;\n        concurrentDownloadsBox.SelectedIndexChanged += (_, _) =>\n        {\n            if (loadingSettings) return;\n            SaveSettings();\n            UpdateQueueControls();\n            UpdatePrimaryDownloadAction();\n            if (downloadCts != null || concurrentQueueActive.Count > 0) KickQueueScheduler();\n        };\n        prefGrid.Controls.Add(concurrentLabel, 0, 3);\n        prefGrid.Controls.Add(concurrentDownloadsBox, 1, 3);\n        preferences.Controls.Add(prefGrid);\n'''
if old not in s:
    raise SystemExit('P15 settings controls anchor not found')
s = s.replace(old, new, 1)

# Preview 4 changed the default-quality index to 1. Add concurrency default beside it.
old = '''            defaultQualityBox.SelectedIndex = 1;\n\n            if (!File.Exists(SettingsPath)) return;\n'''
new = '''            defaultQualityBox.SelectedIndex = 1;\n            concurrentDownloadsBox.SelectedIndex = 0;\n\n            if (!File.Exists(SettingsPath)) return;\n'''
if old not in s:
    raise SystemExit('P15 LoadSettings default anchor not found')
s = s.replace(old, new, 1)

old = '''            defaultQualityBox.SelectedIndex = data.DefaultQuality switch\n            {\n                "360p" => 0,\n                "1080p" => 2,\n                "Best" => 3,\n                _ => 1\n            };\n'''
new = old + '''            concurrentDownloadsBox.SelectedIndex = Math.Clamp(data.MaxConcurrentDownloads - 1, 0, 2);\n'''
if old not in s:
    raise SystemExit('P15 LoadSettings mapping anchor not found')
s = s.replace(old, new, 1)

old = '''                DefaultQuality = defaultQualityBox.SelectedIndex switch { 0 => "360p", 2 => "1080p", 3 => "Best", _ => "720p" }\n'''
new = '''                DefaultQuality = defaultQualityBox.SelectedIndex switch { 0 => "360p", 2 => "1080p", 3 => "Best", _ => "720p" },\n                MaxConcurrentDownloads = Math.Clamp(concurrentDownloadsBox.SelectedIndex + 1, 1, 3)\n'''
if old not in s:
    raise SystemExit('P15 SaveSettings mapping anchor not found')
s = s.replace(old, new, 1)

old = '''        public string DefaultQuality { get; set; } = "720p";\n    }\n'''
new = '''        public string DefaultQuality { get; set; } = "720p";\n        public int MaxConcurrentDownloads { get; set; } = 1;\n    }\n'''
if old not in s:
    raise SystemExit('P15 AppSettingsData anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Watch-page button injection
# -----------------------------------------------------------------------------
old = '            await browser.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(ChannelSelectorScript());\n'
new = old + '            await browser.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(WatchPageDownloadScript());\n'
if old not in s:
    raise SystemExit('P15 document-created script anchor not found')
s = s.replace(old, new, 1)

# Replace channel-only bridge with an async bridge handling both message types.
pattern = re.compile(
    r'    private void BrowserWebMessageReceived\(object\? sender, CoreWebView2WebMessageReceivedEventArgs e\)\n    \{.*?\n    \}\n\n    private void AddChannelQueueItem',
    re.S,
)
replacement = r'''    private async void BrowserWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson);
            var root = doc.RootElement;
            if (!root.TryGetProperty("type", out var typeEl)) return;
            var type = typeEl.GetString() ?? string.Empty;
            var url = root.TryGetProperty("url", out var urlEl) ? urlEl.GetString() ?? string.Empty : string.Empty;
            var title = root.TryGetProperty("title", out var titleEl) ? titleEl.GetString() ?? "YouTube video" : "YouTube video";
            var thumbnail = root.TryGetProperty("thumbnail", out var thumbEl) ? thumbEl.GetString() ?? string.Empty : string.Empty;

            if (string.Equals(type, "rms-channel-select", StringComparison.Ordinal))
            {
                AddChannelQueueItem(url, title, thumbnail);
                return;
            }
            if (string.Equals(type, "rms-watch-download", StringComparison.Ordinal))
            {
                await HandleWatchPageDownloadAsync(url, title, thumbnail);
                return;
            }
        }
        catch (Exception ex)
        {
            AppendLog("Browser action message ignored: " + ex.Message);
        }
    }

    private static string WatchPageDownloadScript() => """
(() => {
  if (window.__rmsWatchDownloadInstalledV15) return;
  window.__rmsWatchDownloadInstalledV15 = true;
  window.__rmsWatchModeV15 = 'download';

  const videoId = () => {
    try {
      if (location.pathname !== '/watch') return '';
      return new URL(location.href).searchParams.get('v') || '';
    } catch { return ''; }
  };

  const hostForButton = () =>
      document.querySelector('ytd-watch-metadata #top-level-buttons-computed')
      || document.querySelector('ytd-watch-metadata #actions-inner')
      || document.querySelector('ytd-watch-metadata #actions')
      || document.querySelector('#below ytd-watch-metadata');

  const labelForMode = () => window.__rmsWatchModeV15 === 'queue' ? 'Add to Queue' : 'Download';

  window.__rmsWatchSetMode = mode => {
    window.__rmsWatchModeV15 = mode === 'queue' ? 'queue' : 'download';
    const b = document.querySelector('.rms-watch-download-v15');
    if (b && !b.dataset.working) b.textContent = labelForMode();
  };

  const ensure = () => {
    const id = videoId();
    if (!id) {
      document.querySelectorAll('.rms-watch-download-v15').forEach(x => x.remove());
      return;
    }
    const host = hostForButton();
    if (!host) return;

    let button = document.querySelector('.rms-watch-download-v15');
    if (button && button.dataset.videoId !== id) {
      button.remove();
      button = null;
    }
    if (!button) {
      button = document.createElement('button');
      button.className = 'rms-watch-download-v15';
      button.type = 'button';
      button.dataset.videoId = id;
      button.title = 'Download now, or add to Rizwan Media Saver queue when another download is active';
      Object.assign(button.style, {
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        height: '36px', minWidth: '104px', padding: '0 15px', margin: '0 6px',
        border: '0', borderRadius: '18px', background: '#ff9800', color: '#fff',
        fontFamily: 'Roboto, Arial, sans-serif', fontSize: '14px', fontWeight: '700',
        cursor: 'pointer', whiteSpace: 'nowrap', boxSizing: 'border-box'
      });
      button.textContent = labelForMode();
      button.addEventListener('click', ev => {
        ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation();
        const currentId = videoId();
        if (!currentId) return;
        const url = location.origin + '/watch?v=' + encodeURIComponent(currentId);
        const title = (document.querySelector('ytd-watch-metadata h1 yt-formatted-string')?.textContent
                    || document.querySelector('h1.title yt-formatted-string')?.textContent
                    || document.title.replace(/\s*-\s*YouTube\s*$/i, '')
                    || 'YouTube video').trim();
        const thumbnail = document.querySelector('meta[property="og:image"]')?.content
                       || document.querySelector('link[itemprop="thumbnailUrl"]')?.href
                       || ('https://i.ytimg.com/vi/' + currentId + '/hqdefault.jpg');
        button.dataset.working = '1';
        button.textContent = 'Working…';
        button.disabled = true;
        window.chrome.webview.postMessage({ type: 'rms-watch-download', url, title, thumbnail });
        setTimeout(() => {
          button.disabled = false;
          delete button.dataset.working;
          button.textContent = labelForMode();
        }, 2200);
      }, true);
      host.appendChild(button);
    } else if (button.parentElement !== host) {
      host.appendChild(button);
    }
  };

  let timer = 0;
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(ensure, 120);
  };
  const startObserver = () => {
    if (!document.documentElement) { setTimeout(startObserver, 0); return; }
    new MutationObserver(schedule).observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener('popstate', schedule, true);
    window.addEventListener('yt-navigate-finish', schedule, true);
    window.addEventListener('yt-page-data-updated', schedule, true);
    schedule();
    setTimeout(ensure, 400);
    setTimeout(ensure, 1100);
  };
  startObserver();
})();
""";

    private async Task HandleWatchPageDownloadAsync(string url, string title, string thumbnail)
    {
        if (!IsDownloadableMediaPage(url)) return;
        currentMediaUrl = url;
        addressBox.Text = url;
        if (!string.IsNullOrWhiteSpace(thumbnail)) currentMediaThumbnailUrl = thumbnail;

        if (!string.Equals(lastAnalyzedUrl, url, StringComparison.Ordinal) || !qualityBox.Enabled || !audioBox.Enabled)
            await AnalyzeMediaAsync(url);

        if (!string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;
        if (string.IsNullOrWhiteSpace(mediaTitle.Text) || mediaTitle.Text.Equals("Video ready", StringComparison.OrdinalIgnoreCase))
            mediaTitle.Text = string.IsNullOrWhiteSpace(title) ? "YouTube video" : title;

        if (downloadCts != null || concurrentQueueActive.Count > 0 || queuedSingleDownloads.Count > 0)
        {
            QueueCurrentVideo(url);
            KickQueueScheduler();
        }
        else
        {
            await DownloadAsync();
        }
    }

    private void SyncWatchPageButtonMode(bool queueMode)
    {
        try
        {
            if (browser.CoreWebView2 == null) return;
            var mode = queueMode ? "queue" : "download";
            _ = browser.CoreWebView2.ExecuteScriptAsync($"window.__rmsWatchSetMode?.('{mode}');");
        }
        catch { }
    }

    private void AddChannelQueueItem'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P15 BrowserWebMessageReceived replacement failed: {n}')
s = s2

# -----------------------------------------------------------------------------
# Primary action and queue controls now know about concurrent workers.
# -----------------------------------------------------------------------------
pattern = re.compile(r'    private void UpdatePrimaryDownloadAction\(\)\n    \{.*?\n    \}\n\n    private void UpdateQueueControls\(\)', re.S)
replacement = r'''    private int GetConcurrentDownloadLimit()
    {
        return concurrentDownloadsBox.SelectedIndex switch
        {
            1 => 2,
            2 => 3,
            _ => 1
        };
    }

    private int GetAvailableQueueSlots()
    {
        var legacyActive = downloadCts != null ? 1 : 0;
        return Math.Max(0, GetConcurrentDownloadLimit() - legacyActive - concurrentQueueActive.Count);
    }

    private void UpdatePrimaryDownloadAction()
    {
        var mediaReady = !string.IsNullOrWhiteSpace(currentMediaUrl) && qualityBox.Enabled && audioBox.Enabled;
        var queueMode = downloadCts != null || concurrentQueueActive.Count > 0 || queuedSingleDownloads.Count > 0;
        if (queueMode)
        {
            downloadButton.Text = "Add to queue  +";
            downloadButton.Enabled = mediaReady;
        }
        else
        {
            downloadButton.Text = "Download  ↓";
            downloadButton.Enabled = mediaReady;
        }
        SyncWatchPageButtonMode(queueMode);
    }

    private void UpdateQueueControls()'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P15 primary action replacement failed: {n}')
s = s2

pattern = re.compile(r'    private void UpdateQueueControls\(\)\n    \{.*?\n    \}\n\n    private void QueueCurrentVideo', re.S)
replacement = r'''    private void UpdateQueueControls()
    {
        var waiting = queuedSingleDownloads.Count(x => !concurrentQueueActive.Contains(x.ManagerId));
        startQueueButton.Enabled = waiting > 0 && GetAvailableQueueSlots() > 0 && !drainingQueuedSingles;
    }

    private void QueueCurrentVideo'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P15 queue controls replacement failed: {n}')
s = s2

# Queueing a new item should immediately use any free concurrent slot.
old = '''        RefreshDownloadManagerCards();\n        UpdateQueueControls();\n        SaveSessionState(force: true);\n        SetStatus($"Added to queue • {queuedSingleDownloads.Count} waiting");\n'''
new = '''        RefreshDownloadManagerCards();\n        UpdateQueueControls();\n        SaveSessionState(force: true);\n        KickQueueScheduler();\n        SetStatus($"Added to queue • {queuedSingleDownloads.Count(x => !concurrentQueueActive.Contains(x.ManagerId))} waiting");\n'''
if old not in s:
    raise SystemExit('P15 QueueCurrentVideo tail anchor not found')
s = s.replace(old, new, 1)

# Replace Preview 14 sequential queue drain + global-CancellationToken worker with
# independent worker processes, so up to 3 queued videos may run simultaneously.
pattern = re.compile(
    r'    private async Task DrainQueuedSinglesAsync\(\)\n    \{.*?\n    \}\n\n    private async Task DownloadQueuedSingleAsync\(QueuedSingleDownload job\)\n    \{.*?\n    \}\n\n(?=    private async Task DownloadAsync\(\))',
    re.S,
)
replacement = r'''    private Task DrainQueuedSinglesAsync()
    {
        KickQueueScheduler();
        return Task.CompletedTask;
    }

    private void KickQueueScheduler()
    {
        if (IsDisposed) return;
        if (InvokeRequired)
        {
            try { BeginInvoke(KickQueueScheduler); } catch { }
            return;
        }

        var slots = GetAvailableQueueSlots();
        if (slots <= 0)
        {
            UpdateQueueControls();
            UpdatePrimaryDownloadAction();
            return;
        }

        var candidates = queuedSingleDownloads
            .Where(x => !concurrentQueueActive.Contains(x.ManagerId))
            .Where(x =>
            {
                var manager = downloadManagerItems.FirstOrDefault(m => m.Id == x.ManagerId);
                return manager == null || manager.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase) || manager.Status.Equals("Ready", StringComparison.OrdinalIgnoreCase) || manager.Status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase);
            })
            .Take(slots)
            .ToList();

        foreach (var job in candidates)
        {
            concurrentQueueActive.Add(job.ManagerId);
            _ = DownloadQueuedSingleConcurrentAsync(job);
        }

        UpdateQueueControls();
        UpdatePrimaryDownloadAction();
        UpdatePlaylistSelectionStatus();
        UpdateChannelQueueActions();
        if (concurrentQueueActive.Count > 0)
            SetStatus($"Downloading {concurrentQueueActive.Count + (downloadCts != null ? 1 : 0)} file(s)…");
    }

    private async Task DownloadQueuedSingleConcurrentAsync(QueuedSingleDownload job)
    {
        var cts = new CancellationTokenSource();
        concurrentQueueTokens[job.ManagerId] = cts;
        lastManagerProgressRendered = -1;
        lastManagerProgressTick = 0;
        UpdateDownloadManagerItem(job.ManagerId, "Downloading", $"Parallel queue • limit {GetConcurrentDownloadLimit()}", progressValue: null, progressText: null, outputFolder: job.OutputFolder);
        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Queue worker started: " + job.Title);

        string? cookieFile = null;
        try
        {
            var cookieSnapshot = await ExportYouTubeCookiesAsync(cts.Token);
            cookieFile = cookieSnapshot.Path;
            var args = BuildQueuedSingleArgs(job, cookieFile);
            var exit = await RunConcurrentQueueProcessAsync(args, job, cts.Token);
            if (exit == 0)
            {
                UpdateDownloadManagerItem(job.ManagerId, "Completed", "Saved successfully", 100, "100%", job.OutputFolder);
                queuedSingleDownloads.Remove(job);
                AppendLog("Queue download completed: " + job.Title);
                System.Media.SystemSounds.Asterisk.Play();
            }
            else
            {
                UpdateDownloadManagerItem(job.ManagerId, "Failed", "Queued download did not complete", outputFolder: job.OutputFolder);
                queuedSingleDownloads.Remove(job);
                AppendLog("Queue download failed: " + job.Title + " • exit=" + exit);
            }
        }
        catch (OperationCanceledException)
        {
            // A user-facing per-item Cancel action is intentionally deferred; shutdown
            // cancellation should leave the job restorable on next launch.
            UpdateDownloadManagerItem(job.ManagerId, "Interrupted", "Stopped before completion • ready to resume", outputFolder: job.OutputFolder);
        }
        catch (Exception ex)
        {
            UpdateDownloadManagerItem(job.ManagerId, "Failed", ex.Message, outputFolder: job.OutputFolder);
            queuedSingleDownloads.Remove(job);
            AppendLog("Queue download error: " + ex.Message);
            LogCrash(ex, "Concurrent queued single download");
        }
        finally
        {
            DeleteTempCookieFile(cookieFile);
            concurrentQueueProcesses.Remove(job.ManagerId);
            if (concurrentQueueTokens.Remove(job.ManagerId, out var tokenSource)) tokenSource.Dispose();
            concurrentQueueActive.Remove(job.ManagerId);
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            SaveSessionState(force: true);
            UpdateQueueControls();
            UpdatePrimaryDownloadAction();
            UpdatePlaylistSelectionStatus();
            UpdateChannelQueueActions();
            KickQueueScheduler();
        }
    }

    private async Task<int> RunConcurrentQueueProcessAsync(List<string> args, QueuedSingleDownload job, CancellationToken token)
    {
        var psi = MakeProcessInfo(args);
        using var process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        concurrentQueueProcesses[job.ManagerId] = process;
        process.OutputDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) HandleConcurrentQueueLine(job.ManagerId, e.Data!); };
        process.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) HandleConcurrentQueueLine(job.ManagerId, e.Data!); };
        if (!process.Start()) throw new InvalidOperationException("Could not start queued download engine.");
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        using var registration = token.Register(() =>
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch { }
        });
        await process.WaitForExitAsync(CancellationToken.None);
        if (token.IsCancellationRequested) throw new OperationCanceledException(token);
        return process.ExitCode;
    }

    private void HandleConcurrentQueueLine(string managerId, string line)
    {
        if (IsDisposed || !IsHandleCreated) return;
        if (InvokeRequired)
        {
            try { BeginInvoke(() => HandleConcurrentQueueLine(managerId, line)); } catch { }
            return;
        }

        var clean = Regex.Replace(line, "\\x1B\\[[0-9;]*[A-Za-z]", "").Trim();
        if (string.IsNullOrWhiteSpace(clean)) return;
        var status = "Downloading";
        var detail = "Downloading in parallel";
        if (clean.Contains("[Merger]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Merging formats", StringComparison.OrdinalIgnoreCase))
        {
            status = "Merging";
            detail = "Joining video + audio";
        }
        else if (clean.Contains("[ExtractAudio]", StringComparison.OrdinalIgnoreCase))
        {
            status = "Processing";
            detail = "Preparing audio";
        }

        int? value = null;
        string? pctText = null;
        var match = Regex.Match(clean, @"(?<!\d)(?<p>\d{1,3}(?:\.\d+)?)%");
        if (match.Success && double.TryParse(match.Groups["p"].Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var pct))
        {
            value = Math.Clamp((int)Math.Round(pct), 0, 100);
            pctText = pct.ToString("0.0", CultureInfo.InvariantCulture) + "%";
        }

        UpdateDownloadManagerItem(managerId, status, detail, value, pctText);
        RefreshDownloadManagerCards();
        if (!clean.StartsWith("[download]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Destination", StringComparison.OrdinalIgnoreCase) || clean.Contains("100%"))
            AppendLog(clean);
    }

    private void StopConcurrentQueueProcessesForShutdown()
    {
        foreach (var process in concurrentQueueProcesses.Values.ToList())
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch { }
        }
    }

'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P15 queue runner replacement failed: {n}')
s = s2

# If any queue worker/queued item exists, normal Download action joins the queue.
old = '''        if (downloadCts != null)\n        {\n            QueueCurrentVideo(url);\n            return;\n        }\n'''
new = '''        if (downloadCts != null || concurrentQueueActive.Count > 0 || queuedSingleDownloads.Count > 0)\n        {\n            QueueCurrentVideo(url);\n            return;\n        }\n'''
if old not in s:
    raise SystemExit('P15 DownloadAsync queue-mode guard not found')
s = s.replace(old, new, 1)

# Playlist/channel legacy batches consume one global slot and should not exceed
# the configured limit when queue workers are already active.
def patch_method_guard(src: str, method_name: str) -> str:
    start = src.find('private async Task ' + method_name + '(')
    if start < 0:
        raise SystemExit('P15 method guard not found: ' + method_name)
    end = src.find('\n    private ', start + 20)
    if end < 0: end = len(src)
    block = src[start:end]
    old_guard = '        if (downloadCts != null) return;\n'
    if old_guard not in block:
        raise SystemExit('P15 legacy guard anchor missing: ' + method_name)
    block = block.replace(old_guard, '        if (downloadCts != null || concurrentQueueActive.Count >= GetConcurrentDownloadLimit()) return;\n', 1)
    return src[:start] + block + src[end:]

s = patch_method_guard(s, 'DownloadSelectedPlaylistAsync')
s = patch_method_guard(s, 'DownloadReadyChannelQueueAsync')

s = s.replace('playlistDownloadButton.Enabled = selected > 0 && downloadCts == null;',
              'playlistDownloadButton.Enabled = selected > 0 && downloadCts == null && concurrentQueueActive.Count < GetConcurrentDownloadLimit();', 1)
s = s.replace('channelQueueDownloadButton.Enabled = ready > 0 && downloadCts == null;',
              'channelQueueDownloadButton.Enabled = ready > 0 && downloadCts == null && concurrentQueueActive.Count < GetConcurrentDownloadLimit();', 1)

# Save first, then stop child queue processes on graceful close so active jobs are
# restored as queued/interrupted on next launch instead of being lost.
old = '''            SaveSessionState(force: true);\n            SaveSettings();\n'''
new = '''            SaveSessionState(force: true);\n            StopConcurrentQueueProcessesForShutdown();\n            SaveSettings();\n'''
if old not in s:
    raise SystemExit('P15 FormClosing shutdown anchor not found')
s = s.replace(old, new, 1)

# Identity / installer
s = s.replace('Text = "PC v1.2 Preview 14",', 'Text = "PC v1.2 Preview 15",', 1)
s = s.replace('Browser UI v1.2 Preview 14 starting • queue-first UX + Pause / Resume',
              'Browser UI v1.2 Preview 15 starting • watch-page action + optional multi-download queue', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview14-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview15-Setup', 1)
iss.write_text(i, encoding='utf-8')

# Safety verification
check = p.read_text(encoding='utf-8')
required = [
    'window.__rmsChannelSelectorInstalledV10',
    'window.__rmsWatchDownloadInstalledV15',
    'outputTemplate = Path.Combine(targetFolder',
    'var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;',
    'managerLayoutKey == nextLayoutKey',
    'private void SaveSessionState(bool force = false)',
    'private async Task<int> RunStreamingPauseAwareAsync',
    'private readonly List<QueuedSingleDownload> queuedSingleDownloads',
    'private void KickQueueScheduler()',
    'private async Task<int> RunConcurrentQueueProcessAsync',
    'MaxConcurrentDownloads',
    'Add to Queue',
    '"--continue"'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P15 sanity check failed: ' + marker)

print('Applied Preview 15: watch-page Download/Add-to-Queue button + optional 1/2/3 concurrent queue workers')
