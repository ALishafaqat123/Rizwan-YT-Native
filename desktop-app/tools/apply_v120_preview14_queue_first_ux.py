from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 14 — queue-first UX.
# Goal: while one download/batch is active, a newly opened single video can be
# added immediately to a persistent queue instead of waiting for the current
# operation to finish. Keep the sequential engine for stability.

# -----------------------------------------------------------------------------
# Fields / state
# -----------------------------------------------------------------------------
old = '    private readonly Button pauseResumeButton = new();\n'
new = old + '    private readonly Button startQueueButton = new();\n'
if old not in s:
    raise SystemExit('P14 start-queue button anchor not found')
s = s.replace(old, new, 1)

old = '    private string pauseManagerId = string.Empty;\n'
new = old + '''    private readonly List<QueuedSingleDownload> queuedSingleDownloads = new();\n    private bool drainingQueuedSingles;\n'''
if old not in s:
    raise SystemExit('P14 queue state anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Downloads toolbar: add Queued filter + Start queue.
# -----------------------------------------------------------------------------
s = s.replace('foreach (var filter in new[] { "All", "Active", "Completed", "Failed" })',
              'foreach (var filter in new[] { "All", "Active", "Queued", "Completed", "Failed" })', 1)

old = '''        toolbar.Controls.Add(clearCompleted);\n\n        var openFolder = MakeWideButton("Open download folder");\n'''
new = '''        toolbar.Controls.Add(clearCompleted);\n\n        startQueueButton.Text = "Start queue";\n        ConfigureActionButton(startQueueButton, Color.FromArgb(47, 79, 103), 98);\n        startQueueButton.Margin = new Padding(4, 0, 7, 0);\n        startQueueButton.Enabled = false;\n        startQueueButton.Click += async (_, _) => await DrainQueuedSinglesAsync();\n        toolbar.Controls.Add(startQueueButton);\n\n        var openFolder = MakeWideButton("Open download folder");\n'''
if old not in s:
    raise SystemExit('P14 toolbar queue button anchor not found')
s = s.replace(old, new, 1)

# Queued is not the same thing as actively downloading.
old = '''    private static bool IsManagerActive(string status)\n        => !IsManagerCompleted(status) && !IsManagerFailed(status) && !status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase);\n'''
new = '''    private static bool IsManagerActive(string status)\n        => status.Equals("Downloading", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Analyzing", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Merging", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Processing", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Paused", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)\n        || status.StartsWith("Starting", StringComparison.OrdinalIgnoreCase);\n'''
if old not in s:
    raise SystemExit('P14 IsManagerActive anchor not found')
s = s.replace(old, new, 1)

old = '''            "Active" => IsManagerActive(item.Status),\n            "Completed" => IsManagerCompleted(item.Status),\n'''
new = '''            "Active" => IsManagerActive(item.Status),\n            "Queued" => item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase) || item.Status.Equals("Ready", StringComparison.OrdinalIgnoreCase),\n            "Completed" => IsManagerCompleted(item.Status),\n'''
if old not in s:
    raise SystemExit('P14 manager filter anchor not found')
s = s.replace(old, new, 1)

# Stable-card action shape must know queued cards have a Remove action.
s = s.replace('item.Status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase)) ? "T" : "A")',
              'item.Status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase) || item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase)) ? "T" : "A")', 1)

old = '''                    if (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase))\n'''
new = '''                    if (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase) || item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase))\n'''
if old not in s:
    raise SystemExit('P14 remove action condition anchor not found')
s = s.replace(old, new, 1)

old = '''                            downloadManagerItems.RemoveAll(x => x.Id == removeId);\n                            managerLayoutKey = string.Empty;\n                            RefreshDownloadManagerCards();\n                            SaveSessionState(force: true);\n'''
new = '''                            downloadManagerItems.RemoveAll(x => x.Id == removeId);\n                            queuedSingleDownloads.RemoveAll(x => x.ManagerId == removeId);\n                            managerLayoutKey = string.Empty;\n                            RefreshDownloadManagerCards();\n                            UpdateQueueControls();\n                            SaveSessionState(force: true);\n'''
if old not in s:
    raise SystemExit('P14 remove queued item anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Queue helpers before DownloadAsync.
# -----------------------------------------------------------------------------
anchor = '    private async Task DownloadAsync()\n'
if anchor not in s:
    raise SystemExit('P14 DownloadAsync anchor not found')
helpers = r'''    private void UpdatePrimaryDownloadAction()
    {
        var mediaReady = !string.IsNullOrWhiteSpace(currentMediaUrl) && qualityBox.Enabled && audioBox.Enabled;
        if (downloadCts != null)
        {
            downloadButton.Text = "Add to queue  +";
            downloadButton.Enabled = mediaReady;
        }
        else
        {
            downloadButton.Text = "Download  ↓";
            downloadButton.Enabled = mediaReady;
        }
    }

    private void UpdateQueueControls()
    {
        startQueueButton.Enabled = downloadCts == null && queuedSingleDownloads.Count > 0 && !drainingQueuedSingles;
    }

    private void QueueCurrentVideo(string url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out _)) return;
        if (!qualityBox.Enabled || !audioBox.Enabled || qualityBox.SelectedIndex < 0)
        {
            SetStatus("Wait for video analysis before adding to queue");
            return;
        }

        var managerId = ManagerId("single", url);
        if (string.Equals(activeDownloadManagerId, managerId, StringComparison.Ordinal) || queuedSingleDownloads.Any(x => x.ManagerId == managerId))
        {
            SetStatus("This video is already downloading or queued");
            return;
        }

        var selectedQuality = qualityBox.SelectedIndex >= 0 && qualityBox.SelectedIndex < qualityChoices.Count
            ? qualityChoices[qualityBox.SelectedIndex]
            : new QualityChoice("720p HD • Best compatibility", 720, false, false, 0, 30, "H.264");
        var selectedAudio = audioBox.SelectedIndex >= 0 && audioBox.SelectedIndex < audioChoices.Count ? audioChoices[audioBox.SelectedIndex] : null;
        var originalAudio = selectedAudio == null
            || selectedAudio.Kind == AudioKind.Default
            || selectedAudio.Label.StartsWith("Original", StringComparison.OrdinalIgnoreCase);

        var job = new QueuedSingleDownload
        {
            ManagerId = managerId,
            Url = url,
            Title = string.IsNullOrWhiteSpace(mediaTitle.Text) ? "YouTube video" : mediaTitle.Text,
            ThumbnailUrl = currentMediaThumbnailUrl,
            OutputFolder = string.IsNullOrWhiteSpace(folderBox.Text) ? DefaultFolder : folderBox.Text.Trim(),
            QualityLabel = selectedQuality.Label,
            Height = selectedQuality.Height,
            AudioOnly = selectedQuality.AudioOnly,
            BestAvailable = selectedQuality.BestAvailable,
            AudioLabel = selectedAudio?.Label ?? "Original / default",
            AudioFormatId = originalAudio ? null : selectedAudio?.FormatId
        };
        queuedSingleDownloads.Add(job);

        UpsertDownloadManagerItem(
            managerId,
            job.Url,
            job.Title,
            job.ThumbnailUrl,
            "Single-video queue",
            "Queued",
            "Waiting in queue  •  " + job.QualityLabel + "  •  " + job.AudioLabel,
            job.OutputFolder,
            preserveProgress: true);
        var manager = downloadManagerItems.FirstOrDefault(x => x.Id == managerId);
        if (manager != null)
        {
            manager.Progress = 0;
            manager.ProgressText = "0%";
        }
        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        UpdateQueueControls();
        SaveSessionState(force: true);
        SetStatus($"Added to queue • {queuedSingleDownloads.Count} waiting");
        AppendLog("Added to queue: " + job.Title);
    }

    private List<string> BuildQueuedSingleArgs(QueuedSingleDownload job, string? cookieFile)
    {
        var args = CommonArgs(job.Url, includeOutput: false);
        if (args.Count > 0 && string.Equals(args[^1], job.Url, StringComparison.Ordinal)) args.RemoveAt(args.Count - 1);
        args.Add("--no-playlist");
        if (!string.IsNullOrWhiteSpace(cookieFile))
        {
            args.Add("--cookies");
            args.Add(cookieFile!);
        }
        if (!string.IsNullOrWhiteSpace(job.AudioFormatId))
        {
            args.Add("--extractor-args");
            args.Add("youtube:player_client=default,web_embedded");
        }

        Directory.CreateDirectory(job.OutputFolder);
        args.Add("-o");
        args.Add(Path.Combine(job.OutputFolder, "%(title).180B [%(id)s].%(ext)s"));

        string format;
        if (job.AudioOnly)
        {
            format = !string.IsNullOrWhiteSpace(job.AudioFormatId) ? job.AudioFormatId! : "bestaudio[ext=m4a]/bestaudio";
        }
        else
        {
            var cap = job.BestAvailable ? string.Empty : $"[height<={Math.Max(144, job.Height)}]";
            if (!string.IsNullOrWhiteSpace(job.AudioFormatId))
                format = $"bestvideo{cap}[ext=mp4][vcodec^=avc1]+{job.AudioFormatId}/bestvideo{cap}[ext=mp4]+{job.AudioFormatId}/bestvideo{cap}+{job.AudioFormatId}";
            else
                format = $"bestvideo{cap}[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo{cap}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{cap}+bestaudio/best{cap}";
        }

        args.Add("-f");
        args.Add(format);
        if (!job.AudioOnly)
        {
            args.Add("--merge-output-format");
            args.Add("mp4");
        }
        args.Add(job.Url);
        return args;
    }

    private async Task DrainQueuedSinglesAsync()
    {
        if (drainingQueuedSingles || downloadCts != null || queuedSingleDownloads.Count == 0) return;
        drainingQueuedSingles = true;
        UpdateQueueControls();
        try
        {
            while (downloadCts == null && queuedSingleDownloads.Count > 0)
            {
                var job = queuedSingleDownloads[0];
                await DownloadQueuedSingleAsync(job);
            }
        }
        finally
        {
            drainingQueuedSingles = false;
            UpdateQueueControls();
            UpdatePrimaryDownloadAction();
        }
    }

    private async Task DownloadQueuedSingleAsync(QueuedSingleDownload job)
    {
        if (downloadCts != null) return;
        downloadCts = new CancellationTokenSource();
        cancelButton.Enabled = true;
        activeDownloadManagerId = job.ManagerId;
        lastManagerProgressRendered = -1;
        lastManagerProgressTick = 0;
        SetDownloadsHero(job.Title, job.ThumbnailUrl, job.QualityLabel + "  •  " + job.AudioLabel + "  •  queued download");
        UpdateDownloadManagerItem(job.ManagerId, "Downloading", "Started from queue", progressValue: null, progressText: null, outputFolder: job.OutputFolder);
        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        UpdatePrimaryDownloadAction();
        UpdateQueueControls();
        SaveSessionState(force: true);
        AppendLog("Queue download started: " + job.Title);

        string? cookieFile = null;
        try
        {
            var cookieSnapshot = await ExportYouTubeCookiesAsync(downloadCts.Token);
            cookieFile = cookieSnapshot.Path;
            var args = BuildQueuedSingleArgs(job, cookieFile);
            var exit = await RunStreamingPauseAwareAsync(args, downloadCts.Token, job.ManagerId);
            if (exit == 0)
            {
                UpdateDownloadManagerItem(job.ManagerId, "Completed", "Saved successfully", 100, "100%", job.OutputFolder);
                queuedSingleDownloads.Remove(job);
                SetStatus("Queued download completed");
                AppendLog("Queue download completed: " + job.Title);
                System.Media.SystemSounds.Asterisk.Play();
            }
            else
            {
                UpdateDownloadManagerItem(job.ManagerId, "Failed", "Queued download did not complete", outputFolder: job.OutputFolder);
                queuedSingleDownloads.Remove(job);
                SetStatus("Queued download failed");
                AppendLog("Queue download failed: " + job.Title + " • exit=" + exit);
            }
        }
        catch (OperationCanceledException)
        {
            UpdateDownloadManagerItem(job.ManagerId, "Cancelled", "Cancelled by user", outputFolder: job.OutputFolder);
            queuedSingleDownloads.Remove(job);
            SetStatus("Queued download cancelled");
            AppendLog("Queue download cancelled: " + job.Title);
        }
        catch (Exception ex)
        {
            UpdateDownloadManagerItem(job.ManagerId, "Failed", ex.Message, outputFolder: job.OutputFolder);
            queuedSingleDownloads.Remove(job);
            AppendLog("Queue download error: " + ex.Message);
            LogCrash(ex, "Queued single download");
        }
        finally
        {
            DeleteTempCookieFile(cookieFile);
            activeProcess = null;
            downloadCts?.Dispose();
            downloadCts = null;
            activeDownloadManagerId = string.Empty;
            cancelButton.Enabled = false;
            ResetPauseState();
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            UpdateQueueControls();
            UpdatePrimaryDownloadAction();
            SaveSessionState(force: true);
        }
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

# If another operation is active, Download button means Add to queue.
old = '''    private async Task DownloadAsync()\n    {\n        var url = !string.IsNullOrWhiteSpace(currentMediaUrl) ? currentMediaUrl : addressBox.Text.Trim();\n        if (!ValidateReady(url)) return;\n'''
new = '''    private async Task DownloadAsync()\n    {\n        var url = !string.IsNullOrWhiteSpace(currentMediaUrl) ? currentMediaUrl : addressBox.Text.Trim();\n        if (downloadCts != null)\n        {\n            QueueCurrentVideo(url);\n            return;\n        }\n        if (!ValidateReady(url)) return;\n'''
if old not in s:
    raise SystemExit('P14 DownloadAsync busy queue anchor not found')
s = s.replace(old, new, 1)

# Busy state keeps the primary action usable as Add to queue when a newly opened video is ready.
old = '''        downloadButton.Enabled = !busy;\n        if (busy) channelQueueDownloadButton.Enabled = false;\n        else UpdateChannelQueueActions();\n        SetStatus(status);\n'''
new = '''        if (busy) channelQueueDownloadButton.Enabled = false;\n        else UpdateChannelQueueActions();\n        UpdatePrimaryDownloadAction();\n        UpdateQueueControls();\n        SetStatus(status);\n'''
if old not in s:
    raise SystemExit('P14 SetBusy anchor not found')
s = s.replace(old, new, 1)

# Whenever analysis enables audio choices, refresh Download vs Add-to-queue action.
s = s.replace('            audioBox.Enabled = true;\n', '            audioBox.Enabled = true;\n            UpdatePrimaryDownloadAction();\n')

# After each normal single/playlist/channel operation exits, automatically drain queued singles.
def add_drain_after_reset(src: str, method_name: str) -> str:
    start = src.find('private async Task ' + method_name + '(')
    if start < 0:
        raise SystemExit('P14 method not found for queue drain: ' + method_name)
    end = src.find('\n    private ', start + 20)
    if end < 0: end = len(src)
    block = src[start:end]
    marker = '            ResetPauseState();\n'
    if marker not in block:
        raise SystemExit('P14 ResetPauseState not found in ' + method_name)
    replacement = marker + '''            UpdatePrimaryDownloadAction();\n            UpdateQueueControls();\n            if (queuedSingleDownloads.Count > 0) BeginInvoke(async () => await DrainQueuedSinglesAsync());\n'''
    block = block.replace(marker, replacement, 1)
    return src[:start] + block + src[end:]

s = add_drain_after_reset(s, 'DownloadAsync')
s = add_drain_after_reset(s, 'DownloadSelectedPlaylistAsync')
s = add_drain_after_reset(s, 'DownloadReadyChannelQueueAsync')

# -----------------------------------------------------------------------------
# Persist queued singles with Hotfix 2 session state.
# -----------------------------------------------------------------------------
old = '''                ManagerItems = downloadManagerItems.ToList(),\n                ChannelItems = channelQueueItems.ToList(),\n                SavedUtc = DateTime.UtcNow\n'''
new = '''                ManagerItems = downloadManagerItems.ToList(),\n                ChannelItems = channelQueueItems.ToList(),\n                QueuedSingles = queuedSingleDownloads.ToList(),\n                SavedUtc = DateTime.UtcNow\n'''
if old not in s:
    raise SystemExit('P14 session save initializer anchor not found')
s = s.replace(old, new, 1)

old = '''            currentPlaylistUrl = data.CurrentPlaylistUrl ?? string.Empty;\n'''
new = '''            queuedSingleDownloads.Clear();\n            foreach (var job in data.QueuedSingles ?? new List<QueuedSingleDownload>())\n            {\n                if (string.IsNullOrWhiteSpace(job.Url) || string.IsNullOrWhiteSpace(job.ManagerId)) continue;\n                queuedSingleDownloads.Add(job);\n                var manager = downloadManagerItems.FirstOrDefault(x => x.Id == job.ManagerId);\n                if (manager == null)\n                {\n                    manager = new DownloadManagerItem\n                    {\n                        Id = job.ManagerId, Url = job.Url, Title = job.Title, ThumbnailUrl = job.ThumbnailUrl,\n                        Source = "Single-video queue", Status = "Queued",\n                        Detail = "Restored queue • ready to start", OutputFolder = job.OutputFolder, Progress = 0, ProgressText = "0%"\n                    };\n                    downloadManagerItems.Add(manager);\n                }\n                else if (!IsManagerCompleted(manager.Status) && !IsManagerFailed(manager.Status))\n                {\n                    manager.Status = "Queued";\n                    manager.Detail = "Restored queue • ready to start/resume";\n                }\n            }\n\n            currentPlaylistUrl = data.CurrentPlaylistUrl ?? string.Empty;\n'''
if old not in s:
    raise SystemExit('P14 session restore anchor not found')
s = s.replace(old, new, 1)

old = '''            UpdateChannelQueueActions();\n            UpdatePlaylistSelectionStatus();\n            AppendLog($"Session restored • manager={downloadManagerItems.Count} • playlist={playlistItems.Count} • channel={channelQueueItems.Count}");\n'''
new = '''            UpdateChannelQueueActions();\n            UpdatePlaylistSelectionStatus();\n            UpdateQueueControls();\n            UpdatePrimaryDownloadAction();\n            AppendLog($"Session restored • manager={downloadManagerItems.Count} • playlist={playlistItems.Count} • channel={channelQueueItems.Count} • queue={queuedSingleDownloads.Count}");\n'''
if old not in s:
    raise SystemExit('P14 restored UI anchor not found')
s = s.replace(old, new, 1)

old = '''        public List<ChannelQueueItem>? ChannelItems { get; set; }\n        public DateTime SavedUtc { get; set; }\n'''
new = '''        public List<ChannelQueueItem>? ChannelItems { get; set; }\n        public List<QueuedSingleDownload>? QueuedSingles { get; set; }\n        public DateTime SavedUtc { get; set; }\n'''
if old not in s:
    raise SystemExit('P14 SessionStateData property anchor not found')
s = s.replace(old, new, 1)

# Add serializable queue job model before ManagerCardView.
anchor = '    private sealed class ManagerCardView\n'
if anchor not in s:
    raise SystemExit('P14 ManagerCardView anchor not found')
model = '''    private sealed class QueuedSingleDownload\n    {\n        public string ManagerId { get; set; } = string.Empty;\n        public string Url { get; set; } = string.Empty;\n        public string Title { get; set; } = string.Empty;\n        public string ThumbnailUrl { get; set; } = string.Empty;\n        public string OutputFolder { get; set; } = string.Empty;\n        public string QualityLabel { get; set; } = string.Empty;\n        public int Height { get; set; }\n        public bool AudioOnly { get; set; }\n        public bool BestAvailable { get; set; }\n        public string AudioLabel { get; set; } = "Original / default";\n        public string? AudioFormatId { get; set; }\n    }\n\n'''
s = s.replace(anchor, model + anchor, 1)

# Preview identity.
s = s.replace('Text = "PC v1.2 Preview 13",', 'Text = "PC v1.2 Preview 14",', 1)
s = s.replace('Browser UI v1.2 Preview 13 starting • safe Pause / Resume',
              'Browser UI v1.2 Preview 14 starting • queue-first UX + Pause / Resume', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview13-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview14-Setup', 1)
iss.write_text(i, encoding='utf-8')

# Build-time safety checks.
check = p.read_text(encoding='utf-8')
required = [
    'window.__rmsChannelSelectorInstalledV10',
    'outputTemplate = Path.Combine(targetFolder',
    'var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;',
    'managerLayoutKey == nextLayoutKey',
    'private void SaveSessionState(bool force = false)',
    'private async Task<int> RunStreamingPauseAwareAsync',
    'private readonly List<QueuedSingleDownload> queuedSingleDownloads',
    'private void QueueCurrentVideo(string url)',
    'private async Task DrainQueuedSinglesAsync()',
    'downloadButton.Text = "Add to queue  +"',
    'QueuedSingles = queuedSingleDownloads.ToList()',
    '"--continue"'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P14 sanity check failed: ' + marker)

print('Applied Preview 14: queue-first UX with persistent sequential single-video queue')
