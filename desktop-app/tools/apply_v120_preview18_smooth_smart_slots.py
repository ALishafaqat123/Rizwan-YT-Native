from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 18 — smooth Pause/Resume + smart concurrency slots.
# 1) Pause/Resume must update an existing card in-place, never rebuild it.
# 2) A paused worker does NOT consume a concurrency slot.
# 3) If Resume is requested while all slots are occupied, show Waiting to resume
#    and automatically resume that item as soon as a slot becomes free.

# -----------------------------------------------------------------------------
# Runtime resume-wait state.
# -----------------------------------------------------------------------------
old = '''    private readonly HashSet<string> concurrentQueueCancelRequested = new(StringComparer.Ordinal);\n    private bool queueShutdownRequested;\n'''
new = '''    private readonly HashSet<string> concurrentQueueCancelRequested = new(StringComparer.Ordinal);\n    private readonly HashSet<string> concurrentQueueResumeRequested = new(StringComparer.Ordinal);\n    private readonly HashSet<string> concurrentQueueResumeStarting = new(StringComparer.Ordinal);\n    private bool queueShutdownRequested;\n'''
if old not in s:
    raise SystemExit('P18 resume state anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Paused downloads free their slot. ResumeStarting reserves a slot while the
# waiting worker is waking up, preventing a queued item from stealing it.
# -----------------------------------------------------------------------------
pattern = re.compile(r'''    private int GetAvailableQueueSlots\(\)\n    \{.*?\n    \}''', re.S)
replacement = r'''    private int GetAvailableQueueSlots()
    {
        var legacyActive = downloadCts != null ? 1 : 0;
        var runningQueueWorkers = concurrentQueueActive.Count(id =>
            !concurrentQueuePaused.Contains(id) || concurrentQueueResumeStarting.Contains(id));
        return Math.Max(0, GetConcurrentDownloadLimit() - legacyActive - runningQueueWorkers);
    }'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P18 GetAvailableQueueSlots replacement failed: {n}')
s = s2

# -----------------------------------------------------------------------------
# Treat active/paused/resuming/waiting-to-resume as ONE visual card shape.
# This is the key flicker fix: progress/status ticks and Pause/Resume no longer
# cause Controls.Clear() + thumbnail/progress recreation.
# -----------------------------------------------------------------------------
pattern = re.compile(r'''    private static string ManagerCardActionShape\(string status\)\n    \{.*?\n    \}''', re.S)
replacement = r'''    private static string ManagerCardActionShape(string status)
    {
        if (IsManagerCompleted(status) || IsManagerFailed(status) || status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase)) return "done";
        if (status.Equals("Queued", StringComparison.OrdinalIgnoreCase) || status.Equals("Ready", StringComparison.OrdinalIgnoreCase) || status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase)) return "waiting";
        return "running";
    }'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P18 ManagerCardActionShape replacement failed: {n}')
s = s2

# -----------------------------------------------------------------------------
# Replace per-item pause/resume methods with smart-slot behavior.
# -----------------------------------------------------------------------------
pattern = re.compile(r'''    private void PauseConcurrentQueueItem\(string managerId\)\n    \{.*?\n    \}\n\n    private void ResumeConcurrentQueueItem\(string managerId\)\n    \{.*?\n    \}\n\n(?=    private void CancelConcurrentQueueItem)''', re.S)
replacement = r'''    private void PauseConcurrentQueueItem(string managerId)
    {
        if (!concurrentQueueActive.Contains(managerId) || concurrentQueuePaused.Contains(managerId)) return;
        if (!concurrentQueueProcesses.TryGetValue(managerId, out var process)) return;
        try { if (process.HasExited) return; } catch { return; }

        concurrentQueuePaused.Add(managerId);
        concurrentQueueResumeRequested.Remove(managerId);
        concurrentQueueResumeStarting.Remove(managerId);
        concurrentQueuePauseGates[managerId] = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        UpdateDownloadManagerItem(managerId, "Pausing", "Stopping safely • this slot is now available for another download");
        SyncChannelItemFromManager(managerId, "Pausing", "Stopping safely • this slot is now available for another download");
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Pause requested for: " + managerId + " • slot released");

        try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
        catch (Exception ex) { AppendLog("Per-item pause note: " + ex.Message); }

        // A paused item no longer consumes a concurrency slot. Immediately allow
        // the next queued item to use that slot, even when the setting is 1-at-a-time.
        UpdateQueueControls();
        UpdatePrimaryDownloadAction();
        KickQueueScheduler();
    }

    private void BeginResumeInAvailableSlot(string managerId)
    {
        if (!concurrentQueuePaused.Contains(managerId)) return;
        if (!concurrentQueuePauseGates.TryGetValue(managerId, out var gate)) return;
        if (GetAvailableQueueSlots() <= 0) return;

        concurrentQueueResumeRequested.Remove(managerId);
        // Reserve the slot immediately while the async worker wakes up.
        concurrentQueueResumeStarting.Add(managerId);
        UpdateDownloadManagerItem(managerId, "Resuming", "Resuming partial download…");
        SyncChannelItemFromManager(managerId, "Resuming", "Resuming partial download…");
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Resume slot granted for: " + managerId);
        gate.TrySetResult(true);
    }

    private void ResumeConcurrentQueueItem(string managerId)
    {
        if (!concurrentQueuePaused.Contains(managerId)) return;
        if (concurrentQueueResumeStarting.Contains(managerId) || concurrentQueueResumeRequested.Contains(managerId)) return;

        if (GetAvailableQueueSlots() > 0)
        {
            BeginResumeInAvailableSlot(managerId);
            return;
        }

        // Respect the user's concurrency limit. A paused item may request Resume,
        // but if another file is currently using the only slot it waits visibly
        // and is given priority when that slot becomes free.
        concurrentQueueResumeRequested.Add(managerId);
        UpdateDownloadManagerItem(managerId, "Waiting to resume", "Another download is using the available slot • will resume automatically");
        SyncChannelItemFromManager(managerId, "Waiting to resume", "Another download is using the available slot • will resume automatically");
        RefreshDownloadManagerCards();
        SaveSessionState(force: true);
        AppendLog("Resume waiting for free slot: " + managerId);
    }

    private void TryStartWaitingResumes()
    {
        if (GetAvailableQueueSlots() <= 0 || concurrentQueueResumeRequested.Count == 0) return;

        // Preserve download-list order when more than one paused item is waiting.
        var waiting = queuedSingleDownloads
            .Where(x => concurrentQueueResumeRequested.Contains(x.ManagerId))
            .Select(x => x.ManagerId)
            .ToList();

        foreach (var managerId in waiting)
        {
            if (GetAvailableQueueSlots() <= 0) break;
            BeginResumeInAvailableSlot(managerId);
        }
    }

'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P18 pause/resume replacement failed: {n}')
s = s2

# Waiting resume requests get first claim on free slots before new queued jobs.
method_start = s.find('    private void KickQueueScheduler()')
if method_start < 0:
    raise SystemExit('P18 KickQueueScheduler method missing')
method_end = s.find('\n    private ', method_start + 20)
if method_end < 0:
    method_end = len(s)
block = s[method_start:method_end]
old = '        var slots = GetAvailableQueueSlots();\n'
new = '        TryStartWaitingResumes();\n        var slots = GetAvailableQueueSlots();\n'
if old not in block:
    raise SystemExit('P18 scheduler slot anchor missing')
block = block.replace(old, new, 1)
s = s[:method_start] + block + s[method_end:]

# When the paused worker wakes, clear reservation/wait flags before it reruns.
old = '''                    concurrentQueuePauseGates.Remove(job.ManagerId);\n                    concurrentQueuePaused.Remove(job.ManagerId);\n                    cts.Token.ThrowIfCancellationRequested();\n'''
new = '''                    concurrentQueuePauseGates.Remove(job.ManagerId);\n                    concurrentQueuePaused.Remove(job.ManagerId);\n                    concurrentQueueResumeRequested.Remove(job.ManagerId);\n                    concurrentQueueResumeStarting.Remove(job.ManagerId);\n                    cts.Token.ThrowIfCancellationRequested();\n'''
if old not in s:
    raise SystemExit('P18 worker wake anchor not found')
s = s.replace(old, new, 1)

# Pause and resume are transient state changes; do NOT force a layout rebuild.
# Remove only the two worker-branch invalidations around Paused -> Downloading.
old = '''                    managerLayoutKey = string.Empty;\n                    RefreshDownloadManagerCards();\n                    SaveSessionState(force: true);\n                    AppendLog("Paused: " + job.Title);\n'''
new = '''                    RefreshDownloadManagerCards();\n                    SaveSessionState(force: true);\n                    AppendLog("Paused: " + job.Title);\n'''
if old not in s:
    raise SystemExit('P18 paused worker flicker anchor missing')
s = s.replace(old, new, 1)

old = '''                    managerLayoutKey = string.Empty;\n                    RefreshDownloadManagerCards();\n                    SaveSessionState(force: true);\n                    AppendLog("Resumed: " + job.Title);\n'''
new = '''                    RefreshDownloadManagerCards();\n                    SaveSessionState(force: true);\n                    AppendLog("Resumed: " + job.Title);\n'''
if old not in s:
    raise SystemExit('P18 resumed worker flicker anchor missing')
s = s.replace(old, new, 1)

# Always clean the new runtime flags when a worker ends/cancels.
old = '''            concurrentQueuePaused.Remove(job.ManagerId);\n            concurrentQueueCancelRequested.Remove(job.ManagerId);\n            concurrentQueueActive.Remove(job.ManagerId);\n'''
new = '''            concurrentQueuePaused.Remove(job.ManagerId);\n            concurrentQueueCancelRequested.Remove(job.ManagerId);\n            concurrentQueueResumeRequested.Remove(job.ManagerId);\n            concurrentQueueResumeStarting.Remove(job.ManagerId);\n            concurrentQueueActive.Remove(job.ManagerId);\n'''
if old not in s:
    raise SystemExit('P18 worker cleanup anchor not found')
s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# In-place visual updates. The Preview 17 Pause/Resume icon is created once.
# On status transitions, update that existing Button + stripe instead of rebuilding
# the entire card/progress bar.
# -----------------------------------------------------------------------------
old = '''        view.Status.Text = IsManagerCompleted(item.Status) ? "✓ Completed" : item.Status;\n        view.Status.ForeColor = ManagerStatusColor(item.Status);\n    }\n'''
new = '''        view.Status.Text = IsManagerCompleted(item.Status) ? "✓ Completed" : item.Status;\n        view.Status.ForeColor = ManagerStatusColor(item.Status);\n\n        var isPaused = concurrentQueuePaused.Contains(item.Id)\n            || item.Status.Equals("Paused", StringComparison.OrdinalIgnoreCase)\n            || item.Status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)\n            || item.Status.Equals("Waiting to resume", StringComparison.OrdinalIgnoreCase);\n        var resumeWaiting = concurrentQueueResumeRequested.Contains(item.Id);\n        var resumeStarting = concurrentQueueResumeStarting.Contains(item.Id);\n\n        foreach (var button in view.Card.Controls.OfType<Button>())\n        {\n            if (button.Tag as string is not ("Pause" or "Resume" or "Waiting")) continue;\n            if (resumeWaiting || resumeStarting)\n            {\n                button.Text = "…";\n                button.Tag = "Waiting";\n                button.AccessibleName = resumeWaiting ? "Waiting for a free download slot" : "Resuming this download";\n                button.Enabled = false;\n            }\n            else if (isPaused)\n            {\n                button.Text = "▶";\n                button.Tag = "Resume";\n                button.AccessibleName = "Resume this download";\n                button.Enabled = true;\n            }\n            else\n            {\n                button.Text = "❚❚";\n                button.Tag = "Pause";\n                button.AccessibleName = "Pause this download";\n                button.Enabled = concurrentQueueActive.Contains(item.Id);\n            }\n        }\n\n        var stripe = view.Card.Controls.OfType<Panel>().FirstOrDefault(x => x.Left == 0 && x.Width == 3);\n        if (stripe != null)\n        {\n            stripe.BackColor = IsManagerCompleted(item.Status)\n                ? Accent\n                : (isPaused ? Color.FromArgb(255, 152, 0) : Color.FromArgb(90, 169, 255));\n        }\n    }\n'''
if old not in s:
    raise SystemExit('P18 UpdateManagerCardView anchor not found')
s = s.replace(old, new, 1)

# Status color for the new waiting state.
old = '''        if (status.Equals("Paused", StringComparison.OrdinalIgnoreCase) || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(230, 184, 92);\n'''
new = '''        if (status.Equals("Paused", StringComparison.OrdinalIgnoreCase) || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase) || status.Equals("Waiting to resume", StringComparison.OrdinalIgnoreCase) || status.Equals("Resuming", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(230, 184, 92);\n'''
if old not in s:
    raise SystemExit('P18 status color anchor not found')
s = s.replace(old, new, 1)

# If the app closes while waiting to resume, recovery should treat it as interrupted.
old = '''        || status.Equals("Paused", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)\n        || status.StartsWith("Starting", StringComparison.OrdinalIgnoreCase);\n'''
new = '''        || status.Equals("Paused", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Pausing", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Waiting to resume", StringComparison.OrdinalIgnoreCase)\n        || status.Equals("Resuming", StringComparison.OrdinalIgnoreCase)\n        || status.StartsWith("Starting", StringComparison.OrdinalIgnoreCase);\n'''
if old not in s:
    raise SystemExit('P18 interrupted recovery anchor not found')
s = s.replace(old, new, 1)

# Identity / installer.
s = s.replace('Text = "PC v1.2 Preview 17",', 'Text = "PC v1.2 Preview 18",', 1)
s = s.replace('Browser UI v1.2 Preview 17 starting • clean Downloading/Downloaded UI + icon actions',
              'Browser UI v1.2 Preview 18 starting • smooth Pause/Resume + smart paused slots', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview17-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview18-Setup', 1)
iss.write_text(i, encoding='utf-8')

# Build-time sanity markers.
check = p.read_text(encoding='utf-8')
required = [
    'concurrentQueueResumeRequested',
    'concurrentQueueResumeStarting',
    'runningQueueWorkers = concurrentQueueActive.Count',
    'private void TryStartWaitingResumes()',
    '"Waiting to resume"',
    'return "running";',
    'button.Text = "▶";',
    'button.Text = "❚❚";',
    'MakeDownloadTab("Downloading", "Downloading")',
    'MakeCardIconButton(paused ? "▶" : "❚❚"',
    'private void QueueChannelItemForScheduler(ChannelQueueItem item)',
    'MaxConcurrentDownloads',
    'window.__rmsWatchDownloadInstalledV15',
    'window.__rmsChannelSelectorInstalledV10',
    '"--continue"'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P18 sanity check failed: ' + marker)

print('Applied Preview 18: flicker-free Pause/Resume + paused slots free concurrency capacity + auto resume waiting')
