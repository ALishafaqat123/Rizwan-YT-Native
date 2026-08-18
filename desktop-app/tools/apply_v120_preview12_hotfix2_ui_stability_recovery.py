from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 12 Hotfix 2
# - Stop full manager-card rebuilds on every progress tick (flicker/crash risk).
# - Persist manager/channel/playlist state and restore interrupted sessions.
# - Add crash log breadcrumbs. Do not change download format/folder/channel selector logic.

old = '    private long lastManagerProgressTick;\n'
new = old + '''    private readonly Dictionary<string, ManagerCardView> managerCardViews = new();\n    private string managerLayoutKey = string.Empty;\n    private long lastSessionSaveTick;\n    private bool restoringSession;\n    private string SessionStatePath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Rizwan Media Saver PC", "session-state.json");\n    private string CrashLogPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Rizwan Media Saver PC", "crash.log");\n'''
if old not in s: raise SystemExit('HF2 state anchor not found')
s = s.replace(old, new, 1)

# Restore after controls/settings exist. Save state on graceful close too.
old = '''        BuildUi();\n        LoadSettings();\n        Shown += async (_, _) => await OnFirstShownAsync();\n'''
new = '''        BuildUi();\n        LoadSettings();\n        LoadSessionState();\n        Application.ThreadException += (_, e) => LogCrash(e.Exception, "UI thread");\n        AppDomain.CurrentDomain.UnhandledException += (_, e) =>\n        {\n            if (e.ExceptionObject is Exception ex) LogCrash(ex, "Unhandled");\n        };\n        Shown += async (_, _) => await OnFirstShownAsync();\n'''
if old not in s: raise SystemExit('HF2 constructor restore anchor not found')
s = s.replace(old, new, 1)

old = '''            SaveSettings();\n        };\n'''
new = '''            SaveSessionState(force: true);\n            SaveSettings();\n        };\n'''
# First occurrence is the FormClosing block in constructor after Preview patches.
if old not in s: raise SystemExit('HF2 close save anchor not found')
s = s.replace(old, new, 1)

# A resize is a real layout change; invalidate layout key explicitly.
old = '        downloadsManagerPanel.Resize += (_, _) => RefreshDownloadManagerCards();\n'
new = '''        downloadsManagerPanel.Resize += (_, _) =>\n        {\n            managerLayoutKey = string.Empty;\n            RefreshDownloadManagerCards();\n        };\n'''
if old not in s: raise SystemExit('HF2 manager resize anchor not found')
s = s.replace(old, new, 1)

# Filter changes are real rebuilds; progress/status changes should not be.
old = '''                downloadsManagerFilter = filter;\n                RefreshDownloadManagerCards();\n'''
new = '''                downloadsManagerFilter = filter;\n                managerLayoutKey = string.Empty;\n                RefreshDownloadManagerCards();\n'''
if old not in s: raise SystemExit('HF2 filter anchor not found')
s = s.replace(old, new, 1)

old = '''            downloadManagerItems.RemoveAll(x => IsManagerCompleted(x.Status));\n            RefreshDownloadManagerCards();\n'''
new = '''            downloadManagerItems.RemoveAll(x => IsManagerCompleted(x.Status));\n            managerLayoutKey = string.Empty;\n            RefreshDownloadManagerCards();\n            SaveSessionState(force: true);\n'''
if old not in s: raise SystemExit('HF2 clear-completed anchor not found')
s = s.replace(old, new, 1)

# Replace the expensive manager renderer with a stable renderer that updates existing controls in-place.
pattern = re.compile(r'    private void RefreshDownloadManagerCards\(\)\n    \{.*?\n    \}\n\n    private void UpdateDownloadsSummary\(\)', re.S)
replacement = r'''    private void RefreshDownloadManagerCards()
    {
        if (downloadsManagerPanel.IsDisposed) return;
        var visible = downloadManagerItems.Where(ManagerMatchesFilter).ToList();
        var width = Math.Max(650, downloadsManagerPanel.ClientSize.Width - 28);
        var shapeKey = string.Join(";", visible.Select(x =>
            x.Id + ":" +
            ((IsManagerCompleted(x.Status) || IsManagerFailed(x.Status) || x.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase) || x.Status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase)) ? "T" : "A") +
            (string.IsNullOrWhiteSpace(x.OutputFolder) ? "0" : "1")));
        var nextLayoutKey = downloadsManagerFilter + "|" + width.ToString(CultureInfo.InvariantCulture) + "|" + shapeKey;

        // Critical HF2 behavior: progress/status ticks update existing controls only.
        // Rebuild only when filter, item membership, card-action shape, or width actually changes.
        if (managerLayoutKey == nextLayoutKey && managerCardViews.Count == visible.Count && visible.All(x => managerCardViews.ContainsKey(x.Id)))
        {
            foreach (var item in visible) UpdateManagerCardView(item, managerCardViews[item.Id]);
            UpdateDownloadsSummary();
            UpdateDownloadsNavBadge();
            SaveSessionState();
            return;
        }

        managerLayoutKey = nextLayoutKey;
        managerCardViews.Clear();
        downloadsManagerPanel.SuspendLayout();
        try
        {
            downloadsManagerPanel.Controls.Clear();
            if (visible.Count == 0)
            {
                var empty = new Label
                {
                    Text = downloadManagerItems.Count == 0
                        ? "No downloads yet. Open a video, playlist, or select videos from a channel."
                        : "No items match this filter.",
                    ForeColor = TextMuted,
                    Font = new Font("Segoe UI", 10F),
                    AutoSize = false,
                    Width = Math.Max(560, downloadsManagerPanel.ClientSize.Width - 24),
                    Height = 68,
                    TextAlign = ContentAlignment.MiddleCenter,
                    BackColor = Surface
                };
                downloadsManagerPanel.Controls.Add(empty);
            }
            else
            {
                foreach (var item in visible)
                {
                    var card = new Panel
                    {
                        Width = width,
                        Height = 108,
                        BackColor = Surface,
                        Margin = new Padding(0, 0, 0, 8),
                        Padding = new Padding(10)
                    };
                    var pic = new PictureBox
                    {
                        Width = 132,
                        Height = 78,
                        Left = 10,
                        Top = 15,
                        SizeMode = PictureBoxSizeMode.Zoom,
                        BackColor = Surface2
                    };
                    if (!string.IsNullOrWhiteSpace(item.ThumbnailUrl))
                    {
                        pic.ImageLocation = item.ThumbnailUrl;
                        try { pic.LoadAsync(); } catch { }
                    }

                    var rightWidth = 172;
                    var middleWidth = Math.Max(270, width - 166 - rightWidth);
                    var itemTitle = new Label { Left = 154, Top = 10, Width = middleWidth, Height = 25, AutoEllipsis = true, ForeColor = TextMain, Font = new Font("Segoe UI Semibold", 9.8F, FontStyle.Bold) };
                    var source = new Label { Left = 154, Top = 36, Width = middleWidth, Height = 19, AutoEllipsis = true, ForeColor = TextMuted, Font = new Font("Segoe UI", 8.5F) };
                    var detail = new Label { Left = 154, Top = 56, Width = middleWidth, Height = 18, AutoEllipsis = true, ForeColor = TextMuted, Font = new Font("Segoe UI", 8.2F) };
                    var bar = new ProgressBar { Left = 154, Top = 82, Width = Math.Max(180, middleWidth - 58), Height = 8, Minimum = 0, Maximum = 100, Style = ProgressBarStyle.Continuous };
                    var pct = new Label { Left = 154 + Math.Max(180, middleWidth - 54), Top = 76, Width = 54, Height = 20, ForeColor = Accent, Font = new Font("Segoe UI Semibold", 8.2F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleRight };
                    var status = new Label { Left = width - rightWidth + 10, Top = 12, Width = rightWidth - 28, Height = 24, Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleRight, AutoEllipsis = true };

                    var view = new ManagerCardView(card, itemTitle, source, detail, bar, pct, status);
                    managerCardViews[item.Id] = view;
                    UpdateManagerCardView(item, view);

                    card.Controls.Add(pic);
                    card.Controls.Add(itemTitle);
                    card.Controls.Add(source);
                    card.Controls.Add(detail);
                    card.Controls.Add(bar);
                    card.Controls.Add(pct);
                    card.Controls.Add(status);

                    if (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase))
                    {
                        var remove = MakeSmallButton("Remove");
                        remove.Left = width - rightWidth + 34;
                        remove.Top = 66;
                        remove.Width = 106;
                        remove.Height = 28;
                        var removeId = item.Id;
                        remove.Click += (_, _) =>
                        {
                            downloadManagerItems.RemoveAll(x => x.Id == removeId);
                            managerLayoutKey = string.Empty;
                            RefreshDownloadManagerCards();
                            SaveSessionState(force: true);
                        };
                        card.Controls.Add(remove);
                    }

                    if (item.Status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase))
                    {
                        var restore = MakeSmallButton(item.Id.StartsWith("playlist|", StringComparison.Ordinal) ? "Open playlist" : "Resume setup");
                        restore.Left = width - rightWidth + 34;
                        restore.Top = 66;
                        restore.Width = 106;
                        restore.Height = 28;
                        var restoreUrl = item.Url;
                        var isPlaylistItem = item.Id.StartsWith("playlist|", StringComparison.Ordinal);
                        restore.Click += (_, _) =>
                        {
                            if (isPlaylistItem) ShowView(playlistView);
                            else { ShowView(browserView); Navigate(restoreUrl); }
                        };
                        card.Controls.Add(restore);
                    }

                    if (!string.IsNullOrWhiteSpace(item.OutputFolder))
                    {
                        var open = MakeSmallButton("Open folder");
                        open.Left = width - rightWidth + 34;
                        open.Top = 39;
                        open.Width = 106;
                        open.Height = 26;
                        var folder = item.OutputFolder;
                        open.Click += (_, _) => OpenManagerFolder(folder);
                        card.Controls.Add(open);
                    }

                    downloadsManagerPanel.Controls.Add(card);
                }
            }
        }
        finally
        {
            downloadsManagerPanel.ResumeLayout();
            UpdateDownloadsSummary();
            UpdateDownloadsNavBadge();
            SaveSessionState();
        }
    }

    private void UpdateManagerCardView(DownloadManagerItem item, ManagerCardView view)
    {
        if (view.Card.IsDisposed) return;
        view.Title.Text = item.Title;
        view.Source.Text = item.Source;
        view.Detail.Text = item.Detail;
        view.Progress.Value = Math.Clamp(item.Progress, 0, 100);
        view.Percent.Text = string.IsNullOrWhiteSpace(item.ProgressText) ? item.Progress + "%" : item.ProgressText;
        view.Status.Text = item.Status;
        view.Status.ForeColor = ManagerStatusColor(item.Status);
    }

    private void UpdateDownloadsSummary()'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'HF2 manager renderer replacement failed: {n}')
s = s2

# Insert persistence/recovery and crash logging before SetDownloadsHero.
anchor = '    private void SetDownloadsHero(string title, string thumbnailUrl, string meta)\n'
if anchor not in s: raise SystemExit('HF2 SetDownloadsHero anchor not found')
helpers = r'''    private static bool IsManagerInterruptedStatus(string status)
        => status.Equals("Downloading", StringComparison.OrdinalIgnoreCase)
        || status.Equals("Analyzing", StringComparison.OrdinalIgnoreCase)
        || status.Equals("Merging", StringComparison.OrdinalIgnoreCase)
        || status.Equals("Processing", StringComparison.OrdinalIgnoreCase)
        || status.StartsWith("Starting", StringComparison.OrdinalIgnoreCase);

    private void SaveSessionState(bool force = false)
    {
        if (restoringSession) return;
        var now = Environment.TickCount64;
        if (!force && now - lastSessionSaveTick < 1800) return;
        lastSessionSaveTick = now;
        try
        {
            var playlistSnapshot = new List<PlaylistSessionItem>();
            foreach (ListViewItem row in playlistList.Items)
            {
                if (row.Tag is not int itemIndex || itemIndex < 0 || itemIndex >= playlistItems.Count) continue;
                var item = playlistItems[itemIndex];
                playlistSnapshot.Add(new PlaylistSessionItem
                {
                    Index = item.Index,
                    Title = item.Title,
                    Url = item.Url,
                    Duration = item.Duration,
                    Checked = row.Checked,
                    Status = row.SubItems.Count > 3 ? row.SubItems[3].Text : "Ready"
                });
            }

            var data = new SessionStateData
            {
                CurrentPlaylistUrl = currentPlaylistUrl,
                CurrentPlaylistTitle = currentPlaylistTitle,
                PlaylistQualityIndex = playlistQualityBox.SelectedIndex,
                PlaylistItems = playlistSnapshot,
                ManagerItems = downloadManagerItems.ToList(),
                ChannelItems = channelQueueItems.ToList(),
                SavedUtc = DateTime.UtcNow
            };
            var folder = Path.GetDirectoryName(SessionStatePath)!;
            Directory.CreateDirectory(folder);
            var temp = SessionStatePath + ".tmp";
            File.WriteAllText(temp, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }));
            File.Move(temp, SessionStatePath, true);
        }
        catch (Exception ex)
        {
            LogCrash(ex, "SaveSessionState");
        }
    }

    private void LoadSessionState()
    {
        if (!File.Exists(SessionStatePath)) return;
        restoringSession = true;
        try
        {
            var data = JsonSerializer.Deserialize<SessionStateData>(File.ReadAllText(SessionStatePath));
            if (data == null) return;

            downloadManagerItems.Clear();
            foreach (var item in data.ManagerItems ?? new List<DownloadManagerItem>())
            {
                if (IsManagerInterruptedStatus(item.Status))
                {
                    item.Status = "Interrupted";
                    item.Detail = string.IsNullOrWhiteSpace(item.Detail) ? "Previous session ended before completion" : item.Detail + "  •  interrupted";
                }
                downloadManagerItems.Add(item);
            }

            channelQueueItems.Clear();
            foreach (var item in data.ChannelItems ?? new List<ChannelQueueItem>())
            {
                if (item.Status.StartsWith("Downloading", StringComparison.OrdinalIgnoreCase))
                {
                    item.Status = "Ready";
                    item.Meta = "Interrupted previously • ready to resume";
                }
                channelQueueItems.Add(item);
            }

            currentPlaylistUrl = data.CurrentPlaylistUrl ?? string.Empty;
            currentPlaylistTitle = data.CurrentPlaylistTitle ?? string.Empty;
            if (playlistQualityBox.Items.Count > 0)
                playlistQualityBox.SelectedIndex = Math.Clamp(data.PlaylistQualityIndex, 0, playlistQualityBox.Items.Count - 1);

            playlistItems.Clear();
            playlistList.Items.Clear();
            foreach (var saved in data.PlaylistItems ?? new List<PlaylistSessionItem>())
            {
                var item = new PlaylistItem(saved.Index, saved.Title ?? "YouTube video", saved.Url ?? string.Empty, saved.Duration);
                playlistItems.Add(item);
                var status = saved.Status ?? "Ready";
                if (status.StartsWith("Downloading", StringComparison.OrdinalIgnoreCase)) status = "Interrupted • ready to resume";
                var completed = status.Equals("Completed", StringComparison.OrdinalIgnoreCase);
                var row = new ListViewItem(item.Index.ToString(CultureInfo.InvariantCulture))
                {
                    Tag = playlistItems.Count - 1,
                    Checked = !completed && saved.Checked
                };
                row.SubItems.Add(item.Title);
                row.SubItems.Add(item.Duration > 0 ? FormatDuration(item.Duration) : "—");
                row.SubItems.Add(status);
                playlistList.Items.Add(row);
            }

            if (playlistItems.Count > 0)
            {
                playlistStatus.Text = (string.IsNullOrWhiteSpace(currentPlaylistTitle) ? "Restored playlist" : currentPlaylistTitle)
                    + $"  •  {playlistItems.Count} videos";
                playlistNav.Text = $"☷   Playlist ({playlistItems.Count})";
            }

            activeDownloadManagerId = string.Empty;
            managerLayoutKey = string.Empty;
            RefreshDownloadManagerCards();
            UpdateChannelQueueActions();
            UpdatePlaylistSelectionStatus();
            AppendLog($"Session restored • manager={downloadManagerItems.Count} • playlist={playlistItems.Count} • channel={channelQueueItems.Count}");
        }
        catch (Exception ex)
        {
            LogCrash(ex, "LoadSessionState");
        }
        finally
        {
            restoringSession = false;
            SaveSessionState(force: true);
        }
    }

    private void LogCrash(Exception ex, string context)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(CrashLogPath)!);
            File.AppendAllText(CrashLogPath,
                $"{DateTime.Now:yyyy-MM-dd HH:mm:ss}  {context}\r\n{ex}\r\n------------------------------\r\n");
        }
        catch { }
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

# Persist playlist state on analysis/selection changes.
old = '            AppendLog($"Playlist analyzed: {playlistTitle} • items={playlistItems.Count}");\n'
new = old + '            SaveSessionState(force: true);\n'
if old not in s: raise SystemExit('HF2 playlist analyzed save anchor not found')
s = s.replace(old, new, 1)

# UpdatePlaylistSelectionStatus is called after checkbox changes and batch completion.
pattern = re.compile(r'(    private void UpdatePlaylistSelectionStatus\(\)\n    \{.*?playlistStatus\.Text = baseText \+ \$"  •  selected \{selected\}";)(\n    \})', re.S)
m = pattern.search(s)
if not m: raise SystemExit('HF2 playlist selection method anchor not found')
s = s[:m.start()] + m.group(1) + '\n        SaveSessionState();' + m.group(2) + s[m.end():]

# Persist after channel/manager synchronization even when no progress is active.
old = '''        RefreshDownloadManagerCards();\n        UpdateChannelQueueActions();\n    }\n\n    private void UpdateChannelQueueActions()'''
new = '''        RefreshDownloadManagerCards();\n        UpdateChannelQueueActions();\n        SaveSessionState();\n    }\n\n    private void UpdateChannelQueueActions()'''
if old not in s: raise SystemExit('HF2 channel sync save anchor not found')
s = s.replace(old, new, 1)

# Add persistence models near DownloadManagerItem/QualityChoice records.
record_anchor = '    private sealed record QualityChoice(string Label, int Height, bool AudioOnly, bool BestAvailable, double EstimatedBytes, double Fps, string Codec);\n'
if record_anchor not in s: raise SystemExit('HF2 record anchor not found')
models = '''    private sealed class ManagerCardView\n    {\n        public Panel Card { get; }\n        public Label Title { get; }\n        public Label Source { get; }\n        public Label Detail { get; }\n        public ProgressBar Progress { get; }\n        public Label Percent { get; }\n        public Label Status { get; }\n        public ManagerCardView(Panel card, Label title, Label source, Label detail, ProgressBar progress, Label percent, Label status)\n            => (Card, Title, Source, Detail, Progress, Percent, Status) = (card, title, source, detail, progress, percent, status);\n    }\n\n    private sealed class PlaylistSessionItem\n    {\n        public int Index { get; set; }\n        public string? Title { get; set; }\n        public string? Url { get; set; }\n        public double Duration { get; set; }\n        public bool Checked { get; set; }\n        public string? Status { get; set; }\n    }\n\n    private sealed class SessionStateData\n    {\n        public string? CurrentPlaylistUrl { get; set; }\n        public string? CurrentPlaylistTitle { get; set; }\n        public int PlaylistQualityIndex { get; set; }\n        public List<PlaylistSessionItem>? PlaylistItems { get; set; }\n        public List<DownloadManagerItem>? ManagerItems { get; set; }\n        public List<ChannelQueueItem>? ChannelItems { get; set; }\n        public DateTime SavedUtc { get; set; }\n    }\n\n'''
s = s.replace(record_anchor, models + record_anchor, 1)

# Identity only. Download engine behavior stays the same.
s = s.replace('Text = "PC v1.2 Preview 12",', 'Text = "PC v1.2 Preview 12 Hotfix 2",', 1)
s = s.replace('Browser UI v1.2 Preview 12 starting', 'Browser UI v1.2 Preview 12 Hotfix 2 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview12-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview12-Hotfix2-Setup', 1)
iss.write_text(i, encoding='utf-8')

check = p.read_text(encoding='utf-8')
required = [
    'window.__rmsChannelSelectorInstalledV10',
    'outputTemplate = Path.Combine(targetFolder',
    'var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;',
    'managerLayoutKey == nextLayoutKey',
    'private void SaveSessionState(bool force = false)',
    'private void LoadSessionState()',
    'Session restored • manager=',
    'private sealed class ManagerCardView'
]
for marker in required:
    if marker not in check:
        raise SystemExit('HF2 sanity check failed: ' + marker)

print('Applied Preview 12 Hotfix 2: stable manager rendering + crash/session recovery')
