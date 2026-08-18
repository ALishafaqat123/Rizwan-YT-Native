from pathlib import Path

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 13 — safe logical Pause / Resume.
# Pause stops the current yt-dlp process WITHOUT cancelling the batch token.
# yt-dlp's existing --continue support keeps .part files reusable; Resume reruns
# the exact same arguments, so single/playlist/channel downloads continue safely.
# Preview 12 Hotfix 2 stability/session recovery remains intact.

# -----------------------------------------------------------------------------
# UI/state fields
# -----------------------------------------------------------------------------
old = '    private readonly Button cancelButton = new();\n'
new = old + '    private readonly Button pauseResumeButton = new();\n'
if old not in s:
    raise SystemExit('P13 pause button field anchor not found')
s = s.replace(old, new, 1)

old = '    private string activeDownloadManagerId = string.Empty;\n'
new = old + '''    private TaskCompletionSource<bool>? pauseGate;\n    private bool pauseRequested;\n    private string pauseManagerId = string.Empty;\n'''
if old not in s:
    raise SystemExit('P13 manager state anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Compact toolbar + Pause/Resume control
# -----------------------------------------------------------------------------
s = s.replace('            filterButton.Width = filter == "Completed" ? 96 : 78;\n',
              '            filterButton.Width = filter == "Completed" ? 88 : 68;\n', 1)
s = s.replace('        clearCompleted.Width = 120;\n', '        clearCompleted.Width = 108;\n', 1)
s = s.replace('        openFolder.Width = 155;\n', '        openFolder.Width = 132;\n', 1)

old = '''        toolbar.Controls.Add(openFolder);\n\n        cancelButton.Text = "Cancel current";\n        ConfigureActionButton(cancelButton, Color.FromArgb(118, 55, 61), 130);\n        cancelButton.Margin = new Padding(4, 0, 0, 0);\n        cancelButton.Enabled = false;\n        cancelButton.Click += (_, _) => TryCancelProcess();\n        toolbar.Controls.Add(cancelButton);\n'''
new = '''        toolbar.Controls.Add(openFolder);\n\n        pauseResumeButton.Text = "Pause current";\n        ConfigureActionButton(pauseResumeButton, Color.FromArgb(92, 76, 43), 118);\n        pauseResumeButton.Margin = new Padding(4, 0, 7, 0);\n        pauseResumeButton.Enabled = false;\n        pauseResumeButton.Click += (_, _) => TogglePauseResume();\n        toolbar.Controls.Add(pauseResumeButton);\n\n        cancelButton.Text = "Cancel current";\n        ConfigureActionButton(cancelButton, Color.FromArgb(118, 55, 61), 112);\n        cancelButton.Margin = new Padding(4, 0, 0, 0);\n        cancelButton.Enabled = false;\n        cancelButton.Click += (_, _) => TryCancelProcess();\n        toolbar.Controls.Add(cancelButton);\n'''
if old not in s:
    raise SystemExit('P13 toolbar anchor not found')
s = s.replace(old, new, 1)

# Paused should have its own warm status color.
old = '''        if (status.Equals("Analyzing", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(218, 172, 80);\n        if (status.Equals("Ready", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(128, 214, 178);\n'''
new = '''        if (status.Equals("Analyzing", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(218, 172, 80);\n        if (status.Equals("Paused", StringComparison.OrdinalIgnoreCase) || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(230, 184, 92);\n        if (status.Equals("Ready", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(128, 214, 178);\n'''
if old not in s:
    raise SystemExit('P13 status color anchor not found')
s = s.replace(old, new, 1)

# If the app closes while paused, restore it next launch as Interrupted/resume-ready.
old = '''        || status.Equals("Processing", StringComparison.OrdinalIgnoreCase)\n        || status.StartsWith("Starting", StringComparison.OrdinalIgnoreCase);\n'''
new = '''        || status.Equals("Processing", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Paused", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)\n        || status.StartsWith("Starting", StringComparison.OrdinalIgnoreCase);\n'''
if old not in s:
    raise SystemExit('P13 interrupted status anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Pause/resume engine helper. Insert before TryCancelProcess.
# -----------------------------------------------------------------------------
anchor = '    private void TryCancelProcess()\n'
if anchor not in s:
    raise SystemExit('P13 TryCancelProcess anchor not found')
helpers = r'''    private void TogglePauseResume()
    {
        if (pauseRequested) ResumeCurrentDownload();
        else PauseCurrentDownload();
    }

    private void PauseCurrentDownload()
    {
        if (downloadCts == null || pauseRequested || string.IsNullOrWhiteSpace(activeDownloadManagerId)) return;

        var process = activeProcess;
        if (process == null) return;
        try
        {
            if (process.HasExited) return;
        }
        catch { return; }

        pauseRequested = true;
        pauseManagerId = activeDownloadManagerId;
        pauseGate = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        pauseResumeButton.Text = "Resume current";
        pauseResumeButton.Enabled = true;

        UpdateDownloadManagerItem(pauseManagerId, "Pausing", "Stopping safely • partial file will be kept");
        SetStatus("Pausing…");
        managerLayoutKey = string.Empty;
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Pause requested • keeping partial file for resume.");

        try
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
        }
        catch (Exception ex)
        {
            pauseRequested = false;
            pauseGate = null;
            pauseManagerId = string.Empty;
            pauseResumeButton.Text = "Pause current";
            pauseResumeButton.Enabled = downloadCts != null;
            AppendLog("Pause note: " + ex.Message);
        }
    }

    private void ResumeCurrentDownload()
    {
        if (!pauseRequested || pauseGate == null) return;
        pauseResumeButton.Text = "Resuming…";
        pauseResumeButton.Enabled = false;
        AppendLog("Resume requested.");
        pauseGate.TrySetResult(true);
    }

    private async Task<int> RunStreamingPauseAwareAsync(List<string> args, CancellationToken token, string managerId)
    {
        pauseManagerId = managerId;
        pauseResumeButton.Text = "Pause current";
        pauseResumeButton.Enabled = true;

        while (true)
        {
            token.ThrowIfCancellationRequested();
            pauseManagerId = managerId;

            var exit = await RunStreamingAsync(args, token);
            if (!pauseRequested) return exit;

            UpdateDownloadManagerItem(managerId, "Paused", "Paused safely • click Resume current to continue");
            SetStatus("Paused");
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            SaveSessionState(force: true);
            AppendLog("Paused • partial download preserved.");

            var gate = pauseGate ??= new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            pauseResumeButton.Text = "Resume current";
            pauseResumeButton.Enabled = true;
            await gate.Task.WaitAsync(token);

            pauseGate = null;
            pauseRequested = false;
            pauseResumeButton.Text = "Pause current";
            pauseResumeButton.Enabled = true;
            UpdateDownloadManagerItem(managerId, "Downloading", "Resuming partial download…");
            SetStatus("Resuming download…");
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            SaveSessionState(force: true);

            // Rerun the exact same yt-dlp command. CommonArgs already contains --continue,
            // so an existing .part file is reused rather than starting from zero.
        }
    }

    private void ResetPauseState()
    {
        pauseRequested = false;
        try { pauseGate?.TrySetCanceled(); } catch { }
        pauseGate = null;
        pauseManagerId = string.Empty;
        pauseResumeButton.Text = "Pause current";
        pauseResumeButton.Enabled = false;
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

# Cancel must also release a paused waiter before cancelling the download token.
old = '''    private void TryCancelProcess()\n    {\n        try\n        {\n            downloadCts?.Cancel();\n'''
new = '''    private void TryCancelProcess()\n    {\n        try\n        {\n            pauseGate?.TrySetResult(true);\n            downloadCts?.Cancel();\n'''
if old not in s:
    raise SystemExit('P13 cancel anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Route single / playlist / channel streaming through pause-aware wrapper.
# -----------------------------------------------------------------------------
def replace_call_in_method(src: str, method_name: str, manager_id: str) -> str:
    start = src.find('private async Task ' + method_name + '(')
    if start < 0:
        raise SystemExit(f'P13 method not found: {method_name}')
    next_method = src.find('\n    private ', start + 20)
    if next_method < 0:
        next_method = len(src)
    block = src[start:next_method]
    old_call = 'var exit = await RunStreamingAsync(args, downloadCts.Token);'
    if old_call not in block:
        raise SystemExit(f'P13 streaming call not found in {method_name}')
    block = block.replace(old_call, f'var exit = await RunStreamingPauseAwareAsync(args, downloadCts.Token, {manager_id});', 1)
    return src[:start] + block + src[next_method:]

s = replace_call_in_method(s, 'DownloadAsync', 'managerItemId')
s = replace_call_in_method(s, 'DownloadSelectedPlaylistAsync', 'playlistManagerId')
s = replace_call_in_method(s, 'DownloadReadyChannelQueueAsync', 'channelManagerId')

# Reset pause UI/state when each operation fully exits.
# Single download finally.
method_start = s.find('private async Task DownloadAsync()')
if method_start < 0: raise SystemExit('P13 single method missing for reset')
next_method = s.find('\n    private ', method_start + 20)
block = s[method_start:next_method]
old_reset = '            activeDownloadManagerId = string.Empty;\n            RefreshDownloadManagerCards();\n'
new_reset = old_reset + '            ResetPauseState();\n'
if old_reset not in block: raise SystemExit('P13 single reset anchor missing')
block = block.replace(old_reset, new_reset, 1)
s = s[:method_start] + block + s[next_method:]

# Playlist finally.
method_start = s.find('private async Task DownloadSelectedPlaylistAsync()')
if method_start < 0: raise SystemExit('P13 playlist method missing for reset')
next_method = s.find('\n    private ', method_start + 20)
block = s[method_start:next_method]
old_reset = '            UpdatePlaylistSelectionStatus();\n'
new_reset = old_reset + '            ResetPauseState();\n'
if old_reset not in block: raise SystemExit('P13 playlist reset anchor missing')
block = block.replace(old_reset, new_reset, 1)
s = s[:method_start] + block + s[next_method:]

# Channel finally.
method_start = s.find('private async Task DownloadReadyChannelQueueAsync()')
if method_start < 0: raise SystemExit('P13 channel method missing for reset')
next_method = s.find('\n    private ', method_start + 20)
block = s[method_start:next_method]
old_reset = '            UpdateChannelQueueActions();\n'
new_reset = old_reset + '            ResetPauseState();\n'
if old_reset not in block: raise SystemExit('P13 channel reset anchor missing')
block = block.replace(old_reset, new_reset, 1)
s = s[:method_start] + block + s[next_method:]

# -----------------------------------------------------------------------------
# Identity / installer
# -----------------------------------------------------------------------------
s = s.replace('Text = "PC v1.2 Preview 12 Hotfix 2",', 'Text = "PC v1.2 Preview 13",', 1)
s = s.replace('Browser UI v1.2 Preview 12 Hotfix 2 starting', 'Browser UI v1.2 Preview 13 starting • safe Pause / Resume', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview12-Hotfix2-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview13-Setup', 1)
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
    'Pause requested • keeping partial file for resume.',
    'RunStreamingPauseAwareAsync(args, downloadCts.Token, managerItemId)',
    'RunStreamingPauseAwareAsync(args, downloadCts.Token, playlistManagerId)',
    'RunStreamingPauseAwareAsync(args, downloadCts.Token, channelManagerId)',
    '"--continue"'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P13 sanity check failed: ' + marker)

print('Applied Preview 13: safe logical Pause / Resume for single, playlist, and channel downloads')
