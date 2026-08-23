from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 16
# - Channel selections auto-enter the same scheduler as watch/single downloads.
# - Every queued-worker card gets its own Pause/Resume + Cancel controls.
# - Completed cards show a clear check mark.
# - Normal single-video Download also uses the scheduler, so concurrency and
#   per-card controls behave consistently from the first item onward.

# -----------------------------------------------------------------------------
# Per-item queue state
# -----------------------------------------------------------------------------
old = '''    private readonly Dictionary<string, Process> concurrentQueueProcesses = new(StringComparer.Ordinal);\n'''
new = old + '''    private readonly HashSet<string> concurrentQueuePaused = new(StringComparer.Ordinal);\n    private readonly Dictionary<string, TaskCompletionSource<bool>> concurrentQueuePauseGates = new(StringComparer.Ordinal);\n    private readonly HashSet<string> concurrentQueueCancelRequested = new(StringComparer.Ordinal);\n    private bool queueShutdownRequested;\n'''
if old not in s:
    raise SystemExit('P16 concurrent state anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Downloads header: channel items now auto-start, so remove the old manual batch
# button and give the queue title the full width.
# -----------------------------------------------------------------------------
s = s.replace('managerHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 190));',
              'managerHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 0));', 1)
old = '''        channelQueueDownloadButton.Enabled = false;\n        channelQueueDownloadButton.Click += async (_, _) => await DownloadReadyChannelQueueAsync();\n'''
new = '''        channelQueueDownloadButton.Enabled = false;\n        channelQueueDownloadButton.Visible = false;\n        channelQueueDownloadButton.Click += async (_, _) => await DownloadReadyChannelQueueAsync();\n'''
if old not in s:
    raise SystemExit('P16 channel header button anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Channel -> unified scheduler bridge.
# -----------------------------------------------------------------------------
anchor = '    private async Task ProcessChannelQueueAnalysisAsync()\n'
if anchor not in s:
    raise SystemExit('P16 channel analysis anchor not found')
helpers = r'''    private void QueueChannelItemForScheduler(ChannelQueueItem item)
    {
        if (string.IsNullOrWhiteSpace(item.Url)) return;
        var managerId = ManagerId("channel", item.Url);
        if (concurrentQueueActive.Contains(managerId) || queuedSingleDownloads.Any(x => x.ManagerId == managerId)) return;

        var existing = downloadManagerItems.FirstOrDefault(x => x.Id == managerId);
        if (existing != null && IsManagerCompleted(existing.Status))
        {
            item.Status = "Completed";
            return;
        }

        var quality = GetDefaultQualityChoice();
        var qualityLabel = quality.BestAvailable ? "Best available" : quality.Height + "p default";
        var root = string.IsNullOrWhiteSpace(folderBox.Text) ? DefaultFolder : folderBox.Text.Trim();
        var outputFolder = BuildNamedSubfolder(root, item.ChannelName, "YouTube Channel");
        Directory.CreateDirectory(outputFolder);

        var job = new QueuedSingleDownload
        {
            ManagerId = managerId,
            Url = item.Url,
            Title = string.IsNullOrWhiteSpace(item.Title) ? "YouTube video" : item.Title,
            ThumbnailUrl = item.ThumbnailUrl,
            OutputFolder = outputFolder,
            QualityLabel = qualityLabel,
            Height = quality.Height,
            AudioOnly = false,
            BestAvailable = quality.BestAvailable,
            AudioLabel = "Original / default",
            AudioFormatId = null
        };
        queuedSingleDownloads.Add(job);
        item.Status = "Queued";
        item.Meta = "Waiting in queue  •  " + qualityLabel + "  •  Original/default audio";

        UpsertDownloadManagerItem(
            managerId,
            item.Url,
            job.Title,
            item.ThumbnailUrl,
            string.IsNullOrWhiteSpace(item.ChannelName) ? "Channel selection" : item.ChannelName,
            "Queued",
            item.Meta,
            outputFolder,
            preserveProgress: true);
        var manager = downloadManagerItems.FirstOrDefault(x => x.Id == managerId);
        if (manager != null)
        {
            manager.Progress = 0;
            manager.ProgressText = "0%";
        }

        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Channel item auto-queued: " + job.Title);
        KickQueueScheduler();
    }

    private void SyncChannelItemFromManager(string managerId, string status, string detail, string? outputFolder = null)
    {
        if (!managerId.StartsWith("channel|", StringComparison.Ordinal)) return;
        var item = channelQueueItems.FirstOrDefault(x => ManagerId("channel", x.Url) == managerId);
        if (item == null) return;
        item.Status = status;
        item.Meta = IsManagerCompleted(status) && !string.IsNullOrWhiteSpace(outputFolder)
            ? "Saved to " + outputFolder
            : detail;
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

# Queue a channel video automatically as soon as its analysis becomes Ready.
method_start = s.find('private async Task ProcessChannelQueueAnalysisAsync()')
if method_start < 0:
    raise SystemExit('P16 channel analysis method missing')
method_end = s.find('\n    private ', method_start + 20)
if method_end < 0:
    method_end = len(s)
block = s[method_start:method_end]
old_ready = '                    item.Status = "Ready";\n'
new_ready = old_ready + '                    QueueChannelItemForScheduler(item);\n'
if old_ready not in block:
    raise SystemExit('P16 channel Ready anchor missing')
block = block.replace(old_ready, new_ready, 1)
s = s[:method_start] + block + s[method_end:]

# -----------------------------------------------------------------------------
# Route ALL normal single-video downloads through the scheduler. This removes the
# special first-download path and gives the first item the same concurrency and
# per-card controls as every queued item.
# -----------------------------------------------------------------------------
pattern = re.compile(r'    private async Task DownloadAsync\(\)\n    \{.*?\n    \}\n\n    private bool ValidateReady', re.S)
replacement = r'''    private Task DownloadAsync()
    {
        var url = !string.IsNullOrWhiteSpace(currentMediaUrl) ? currentMediaUrl : addressBox.Text.Trim();
        if (!ValidateReady(url)) return Task.CompletedTask;
        QueueCurrentVideo(url);
        KickQueueScheduler();
        return Task.CompletedTask;
    }

    private bool ValidateReady'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P16 DownloadAsync scheduler replacement failed: {n}')
s = s2

# -----------------------------------------------------------------------------
# Per-item Pause / Resume / Cancel for concurrent queue workers.
# -----------------------------------------------------------------------------
pattern = re.compile(
    r'    private async Task DownloadQueuedSingleConcurrentAsync\(QueuedSingleDownload job\)\n    \{.*?\n    \}\n\n(?=    private async Task<int> RunConcurrentQueueProcessAsync)',
    re.S,
)
replacement = r'''    private void ToggleConcurrentQueuePauseResume(string managerId)
    {
        if (concurrentQueuePaused.Contains(managerId)) ResumeConcurrentQueueItem(managerId);
        else PauseConcurrentQueueItem(managerId);
    }

    private void PauseConcurrentQueueItem(string managerId)
    {
        if (!concurrentQueueActive.Contains(managerId) || concurrentQueuePaused.Contains(managerId)) return;
        if (!concurrentQueueProcesses.TryGetValue(managerId, out var process)) return;
        try { if (process.HasExited) return; } catch { return; }

        concurrentQueuePaused.Add(managerId);
        concurrentQueuePauseGates[managerId] = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        UpdateDownloadManagerItem(managerId, "Pausing", "Stopping safely • partial file will be kept");
        SyncChannelItemFromManager(managerId, "Pausing", "Stopping safely • partial file will be kept");
        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Pause requested for: " + managerId);

        try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
        catch (Exception ex) { AppendLog("Per-item pause note: " + ex.Message); }
    }

    private void ResumeConcurrentQueueItem(string managerId)
    {
        if (!concurrentQueuePaused.Contains(managerId)) return;
        UpdateDownloadManagerItem(managerId, "Resuming", "Restarting partial download…");
        SyncChannelItemFromManager(managerId, "Resuming", "Restarting partial download…");
        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        if (concurrentQueuePauseGates.TryGetValue(managerId, out var gate)) gate.TrySetResult(true);
    }

    private void CancelConcurrentQueueItem(string managerId)
    {
        var job = queuedSingleDownloads.FirstOrDefault(x => x.ManagerId == managerId);
        if (job == null) return;

        if (!concurrentQueueActive.Contains(managerId))
        {
            queuedSingleDownloads.Remove(job);
            UpdateDownloadManagerItem(managerId, "Cancelled", "Removed from queue", outputFolder: job.OutputFolder);
            SyncChannelItemFromManager(managerId, "Cancelled", "Removed from queue", job.OutputFolder);
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            SaveSessionState(force: true);
            UpdateQueueControls();
            UpdatePrimaryDownloadAction();
            KickQueueScheduler();
            return;
        }

        concurrentQueueCancelRequested.Add(managerId);
        if (concurrentQueuePauseGates.TryGetValue(managerId, out var gate)) gate.TrySetResult(true);
        if (concurrentQueueTokens.TryGetValue(managerId, out var cts)) cts.Cancel();
    }

    private async Task DownloadQueuedSingleConcurrentAsync(QueuedSingleDownload job)
    {
        var cts = new CancellationTokenSource();
        concurrentQueueTokens[job.ManagerId] = cts;
        lastManagerProgressRendered = -1;
        lastManagerProgressTick = 0;
        UpdateDownloadManagerItem(job.ManagerId, "Downloading", $"Queue worker • limit {GetConcurrentDownloadLimit()}", progressValue: null, progressText: null, outputFolder: job.OutputFolder);
        SyncChannelItemFromManager(job.ManagerId, "Downloading", "Downloading", job.OutputFolder);
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

            while (true)
            {
                cts.Token.ThrowIfCancellationRequested();
                var exit = await RunConcurrentQueueProcessAsync(args, job, cts.Token);

                if (queueShutdownRequested)
                {
                    UpdateDownloadManagerItem(job.ManagerId, "Interrupted", "App closed before completion • ready to resume", outputFolder: job.OutputFolder);
                    SyncChannelItemFromManager(job.ManagerId, "Interrupted", "App closed before completion • ready to resume", job.OutputFolder);
                    break;
                }

                if (concurrentQueuePaused.Contains(job.ManagerId))
                {
                    UpdateDownloadManagerItem(job.ManagerId, "Paused", "Paused safely • click Resume on this video");
                    SyncChannelItemFromManager(job.ManagerId, "Paused", "Paused safely • click Resume on this video", job.OutputFolder);
                    managerLayoutKey = string.Empty;
                    RefreshDownloadManagerCards();
                    SaveSessionState(force: true);
                    AppendLog("Paused: " + job.Title);

                    if (!concurrentQueuePauseGates.TryGetValue(job.ManagerId, out var gate))
                    {
                        gate = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
                        concurrentQueuePauseGates[job.ManagerId] = gate;
                    }
                    await gate.Task.WaitAsync(cts.Token);
                    concurrentQueuePauseGates.Remove(job.ManagerId);
                    concurrentQueuePaused.Remove(job.ManagerId);
                    cts.Token.ThrowIfCancellationRequested();

                    UpdateDownloadManagerItem(job.ManagerId, "Downloading", "Resuming partial download…");
                    SyncChannelItemFromManager(job.ManagerId, "Downloading", "Resuming partial download…", job.OutputFolder);
                    managerLayoutKey = string.Empty;
                    RefreshDownloadManagerCards();
                    SaveSessionState(force: true);
                    AppendLog("Resumed: " + job.Title);
                    continue;
                }

                if (exit == 0)
                {
                    UpdateDownloadManagerItem(job.ManagerId, "Completed", "Saved successfully", 100, "100%", job.OutputFolder);
                    SyncChannelItemFromManager(job.ManagerId, "Completed", "Saved successfully", job.OutputFolder);
                    queuedSingleDownloads.Remove(job);
                    AppendLog("Queue download completed: " + job.Title);
                    System.Media.SystemSounds.Asterisk.Play();
                }
                else
                {
                    UpdateDownloadManagerItem(job.ManagerId, "Failed", "Download did not complete", outputFolder: job.OutputFolder);
                    SyncChannelItemFromManager(job.ManagerId, "Failed", "Download did not complete", job.OutputFolder);
                    queuedSingleDownloads.Remove(job);
                    AppendLog("Queue download failed: " + job.Title + " • exit=" + exit);
                }
                break;
            }
        }
        catch (OperationCanceledException)
        {
            if (concurrentQueueCancelRequested.Remove(job.ManagerId))
            {
                UpdateDownloadManagerItem(job.ManagerId, "Cancelled", "Cancelled by user", outputFolder: job.OutputFolder);
                SyncChannelItemFromManager(job.ManagerId, "Cancelled", "Cancelled by user", job.OutputFolder);
                queuedSingleDownloads.Remove(job);
                AppendLog("Cancelled: " + job.Title);
            }
            else
            {
                UpdateDownloadManagerItem(job.ManagerId, "Interrupted", "Stopped before completion • ready to resume", outputFolder: job.OutputFolder);
                SyncChannelItemFromManager(job.ManagerId, "Interrupted", "Stopped before completion • ready to resume", job.OutputFolder);
            }
        }
        catch (Exception ex)
        {
            UpdateDownloadManagerItem(job.ManagerId, "Failed", ex.Message, outputFolder: job.OutputFolder);
            SyncChannelItemFromManager(job.ManagerId, "Failed", ex.Message, job.OutputFolder);
            queuedSingleDownloads.Remove(job);
            AppendLog("Queue download error: " + ex.Message);
            LogCrash(ex, "Concurrent queued download");
        }
        finally
        {
            DeleteTempCookieFile(cookieFile);
            concurrentQueueProcesses.Remove(job.ManagerId);
            if (concurrentQueueTokens.Remove(job.ManagerId, out var tokenSource)) tokenSource.Dispose();
            if (concurrentQueuePauseGates.Remove(job.ManagerId, out var pauseGate))
            {
                try { pauseGate.TrySetCanceled(); } catch { }
            }
            concurrentQueuePaused.Remove(job.ManagerId);
            concurrentQueueCancelRequested.Remove(job.ManagerId);
            concurrentQueueActive.Remove(job.ManagerId);
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            SaveSessionState(force: true);
            UpdateQueueControls();
            UpdatePrimaryDownloadAction();
            UpdatePlaylistSelectionStatus();
            UpdateChannelQueueActions();
            if (!queueShutdownRequested) KickQueueScheduler();
        }
    }

'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P16 concurrent worker replacement failed: {n}')
s = s2

# Sync live channel state as the queue worker progresses.
old = '''        UpdateDownloadManagerItem(managerId, status, detail, value, pctText);\n        RefreshDownloadManagerCards();\n'''
new = '''        UpdateDownloadManagerItem(managerId, status, detail, value, pctText);\n        SyncChannelItemFromManager(managerId, status, detail);\n        RefreshDownloadManagerCards();\n'''
if old not in s:
    raise SystemExit('P16 concurrent line sync anchor not found')
s = s.replace(old, new, 1)

# Shutdown should never turn active jobs into Failed just because processes were killed.
old = '''    private void StopConcurrentQueueProcessesForShutdown()\n    {\n        foreach (var process in concurrentQueueProcesses.Values.ToList())\n'''
new = '''    private void StopConcurrentQueueProcessesForShutdown()\n    {\n        queueShutdownRequested = true;\n        foreach (var process in concurrentQueueProcesses.Values.ToList())\n'''
if old not in s:
    raise SystemExit('P16 shutdown anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Download-manager card action shapes and controls.
# -----------------------------------------------------------------------------
anchor = '    private void RefreshDownloadManagerCards()\n'
if anchor not in s:
    raise SystemExit('P16 manager renderer anchor not found')
action_helper = r'''    private static string ManagerCardActionShape(string status)
    {
        if (IsManagerCompleted(status) || IsManagerFailed(status) || status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase)) return "done";
        if (status.Equals("Paused", StringComparison.OrdinalIgnoreCase) || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase) || status.Equals("Resuming", StringComparison.OrdinalIgnoreCase)) return "paused";
        if (status.Equals("Queued", StringComparison.OrdinalIgnoreCase) || status.Equals("Ready", StringComparison.OrdinalIgnoreCase) || status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase)) return "waiting";
        return "active";
    }

'''
s = s.replace(anchor, action_helper + anchor, 1)

# Make layout-key changes track control shape, not every progress/status tick.
pattern = re.compile(r'        var shapeKey = string.Join\(";", visible.Select\(x =>\n.*?\)\);', re.S)
replacement = '''        var shapeKey = string.Join(";", visible.Select(x =>\n            x.Id + ":" + ManagerCardActionShape(x.Status) +\n            (string.IsNullOrWhiteSpace(x.OutputFolder) ? "0" : "1")));'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P16 manager shape-key replacement failed: {n}')
s = s2

# Give per-card actions more room.
s = s.replace('                    var rightWidth = 172;\n', '                    var rightWidth = 220;\n', 1)

# Insert Pause/Resume + Cancel immediately after the standard card controls exist.
old = '''                    card.Controls.Add(status);\n\n                    if (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase) || item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase))\n'''
new = '''                    card.Controls.Add(status);\n\n                    if (concurrentQueueActive.Contains(item.Id))\n                    {\n                        var perPause = MakeSmallButton(concurrentQueuePaused.Contains(item.Id) ? "Resume" : "Pause");\n                        perPause.Left = width - rightWidth + 18;\n                        perPause.Top = 42;\n                        perPause.Width = 88;\n                        perPause.Height = 27;\n                        var pauseId = item.Id;\n                        perPause.Click += (_, _) => ToggleConcurrentQueuePauseResume(pauseId);\n                        card.Controls.Add(perPause);\n\n                        var perCancel = MakeSmallButton("Cancel");\n                        perCancel.Left = width - rightWidth + 116;\n                        perCancel.Top = 42;\n                        perCancel.Width = 78;\n                        perCancel.Height = 27;\n                        var cancelId = item.Id;\n                        perCancel.Click += (_, _) => CancelConcurrentQueueItem(cancelId);\n                        card.Controls.Add(perCancel);\n                    }\n\n                    if (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase) || item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase))\n'''
if old not in s:
    raise SystemExit('P16 per-card controls anchor not found')
s = s.replace(old, new, 1)

# Avoid overlapping Open Folder with active per-card controls.
old = '''                    if (!string.IsNullOrWhiteSpace(item.OutputFolder))\n                    {\n'''
new = '''                    if (!string.IsNullOrWhiteSpace(item.OutputFolder) &&\n                        (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase)))\n                    {\n'''
if old not in s:
    raise SystemExit('P16 Open Folder condition anchor not found')
s = s.replace(old, new, 1)

# Clear completed state at a glance with a check mark.
old = '        view.Status.Text = item.Status;\n'
new = '        view.Status.Text = IsManagerCompleted(item.Status) ? "✓ Completed" : item.Status;\n'
if old not in s:
    raise SystemExit('P16 completed tick anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Queue/channel status normalization: Ready should be treated/displayed as Queued.
# -----------------------------------------------------------------------------
old = '''        if (status.Equals("Ready", StringComparison.OrdinalIgnoreCase)) return "Ready";\n'''
new = '''        if (status.Equals("Ready", StringComparison.OrdinalIgnoreCase)) return "Queued";\n'''
if old not in s:
    raise SystemExit('P16 Ready normalization anchor not found')
s = s.replace(old, new, 1)

# Identity / installer.
s = s.replace('Text = "PC v1.2 Preview 15",', 'Text = "PC v1.2 Preview 16",', 1)
s = s.replace('Browser UI v1.2 Preview 15 starting • watch-page action + optional multi-download queue',
              'Browser UI v1.2 Preview 16 starting • auto queue + per-card Pause/Resume/Cancel', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview15-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview16-Setup', 1)
iss.write_text(i, encoding='utf-8')

# Safety checks after Preview 16.
check = p.read_text(encoding='utf-8')
required = [
    'window.__rmsChannelSelectorInstalledV10',
    'window.__rmsWatchDownloadInstalledV15',
    'private void QueueChannelItemForScheduler(ChannelQueueItem item)',
    'private void ToggleConcurrentQueuePauseResume(string managerId)',
    'private void CancelConcurrentQueueItem(string managerId)',
    'ManagerCardActionShape',
    '✓ Completed',
    'MaxConcurrentDownloads',
    'outputTemplate = Path.Combine(targetFolder',
    'var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;',
    '"--continue"'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P16 sanity check failed: ' + marker)

print('Applied Preview 16: channel auto-queue + per-card Pause/Resume/Cancel + completed check mark')
