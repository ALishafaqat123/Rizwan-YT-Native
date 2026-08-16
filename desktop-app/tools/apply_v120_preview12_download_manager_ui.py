from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# Preview 12: UI/UX-only Download Manager layer.
# Preserve the working Preview 10 channel selector, Preview 11 named folders,
# and Preview 11 Hotfix 1 original-audio behavior. Download execution remains
# sequential; this patch changes presentation/state tracking, not concurrency.
# -----------------------------------------------------------------------------

# New download-manager UI fields.
old = '    private readonly Button channelQueueDownloadButton = new();\n'
new = old + '''    private readonly FlowLayoutPanel downloadsManagerPanel = new();\n    private readonly Label downloadsSummary = new();\n'''
if old not in s:
    raise SystemExit('Preview12 UI field anchor not found')
s = s.replace(old, new, 1)

# New download-manager state.
old = '    private string currentMediaThumbnailUrl = string.Empty;\n'
new = old + '''    private readonly List<DownloadManagerItem> downloadManagerItems = new();\n    private string downloadsManagerFilter = "All";\n    private string activeDownloadManagerId = string.Empty;\n    private int lastManagerProgressRendered = -1;\n    private long lastManagerProgressTick;\n'''
if old not in s:
    raise SystemExit('Preview12 state anchor not found')
s = s.replace(old, new, 1)

# Replace the Downloads page with a professional manager-oriented layout.
pattern = re.compile(r'    private void BuildDownloadsView\(\)\n    \{.*?\n    \}\n\n    private void BuildPlaylistView\(\)', re.S)
replacement = r'''    private void BuildDownloadsView()
    {
        downloadsView.Dock = DockStyle.Fill;
        downloadsView.BackColor = WindowBg;
        downloadsView.Padding = new Padding(26, 22, 26, 22);
        downloadsView.Visible = false;

        var title = new Label
        {
            Text = "Downloads",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 23F, FontStyle.Bold),
            Dock = DockStyle.Top,
            Height = 48
        };
        var sub = new Label
        {
            Text = "Everything in one place — queued, active, completed and failed downloads stay visible.",
            ForeColor = TextMuted,
            Font = new Font("Segoe UI", 9.7F),
            Dock = DockStyle.Top,
            Height = 30
        };

        var summaryCard = new Panel
        {
            Dock = DockStyle.Top,
            Height = 54,
            BackColor = Surface,
            Padding = new Padding(14, 8, 14, 8),
            Margin = new Padding(0, 8, 0, 8)
        };
        downloadsSummary.Text = "Total 0   •   Active 0   •   Queued 0   •   Completed 0   •   Failed 0";
        downloadsSummary.ForeColor = TextMain;
        downloadsSummary.Font = new Font("Segoe UI Semibold", 9.7F, FontStyle.Bold);
        downloadsSummary.Dock = DockStyle.Fill;
        downloadsSummary.TextAlign = ContentAlignment.MiddleLeft;
        summaryCard.Controls.Add(downloadsSummary);

        var hero = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 118,
            ColumnCount = 2,
            BackColor = Surface,
            Padding = new Padding(12),
            Margin = new Padding(0, 8, 0, 8)
        };
        hero.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 156));
        hero.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

        downloadsThumbnail.Dock = DockStyle.Fill;
        downloadsThumbnail.BackColor = Surface2;
        downloadsThumbnail.SizeMode = PictureBoxSizeMode.Zoom;
        downloadsThumbnail.Margin = new Padding(0, 0, 14, 0);
        hero.Controls.Add(downloadsThumbnail, 0, 0);

        var heroInfo = new Panel { Dock = DockStyle.Fill, BackColor = Surface, Padding = new Padding(2, 0, 0, 0) };
        downloadsTitle.Text = "Ready for your next download";
        downloadsTitle.AutoEllipsis = true;
        downloadsTitle.ForeColor = TextMain;
        downloadsTitle.Font = new Font("Segoe UI Semibold", 12.5F, FontStyle.Bold);
        downloadsTitle.Dock = DockStyle.Top;
        downloadsTitle.Height = 30;

        downloadsMeta.Text = "Open a video, playlist, or select videos from a channel.";
        downloadsMeta.AutoEllipsis = true;
        downloadsMeta.ForeColor = TextMuted;
        downloadsMeta.Font = new Font("Segoe UI", 9F);
        downloadsMeta.Dock = DockStyle.Top;
        downloadsMeta.Height = 24;

        downloadsStatus.Text = "Ready";
        downloadsStatus.ForeColor = TextMain;
        downloadsStatus.Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold);
        downloadsStatus.Dock = DockStyle.Top;
        downloadsStatus.Height = 22;

        downloadsPercent.Text = "0%";
        downloadsPercent.ForeColor = Accent;
        downloadsPercent.Font = new Font("Segoe UI Semibold", 8.8F, FontStyle.Bold);
        downloadsPercent.TextAlign = ContentAlignment.MiddleRight;
        downloadsPercent.Dock = DockStyle.Top;
        downloadsPercent.Height = 19;

        downloadsProgress.Dock = DockStyle.Top;
        downloadsProgress.Height = 9;
        downloadsProgress.Minimum = 0;
        downloadsProgress.Maximum = 100;

        heroInfo.Controls.Add(downloadsProgress);
        heroInfo.Controls.Add(downloadsPercent);
        heroInfo.Controls.Add(downloadsStatus);
        heroInfo.Controls.Add(downloadsMeta);
        heroInfo.Controls.Add(downloadsTitle);
        hero.Controls.Add(heroInfo, 1, 0);

        var toolbar = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 48,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            Padding = new Padding(0, 6, 0, 5),
            BackColor = WindowBg
        };

        foreach (var filter in new[] { "All", "Active", "Completed", "Failed" })
        {
            var filterButton = MakeSmallButton(filter);
            filterButton.Width = filter == "Completed" ? 96 : 78;
            filterButton.Margin = new Padding(0, 0, 7, 0);
            filterButton.Click += (_, _) =>
            {
                downloadsManagerFilter = filter;
                RefreshDownloadManagerCards();
            };
            toolbar.Controls.Add(filterButton);
        }

        var clearCompleted = MakeSmallButton("Clear completed");
        clearCompleted.Width = 120;
        clearCompleted.Margin = new Padding(4, 0, 7, 0);
        clearCompleted.Click += (_, _) =>
        {
            downloadManagerItems.RemoveAll(x => IsManagerCompleted(x.Status));
            RefreshDownloadManagerCards();
        };
        toolbar.Controls.Add(clearCompleted);

        var openFolder = MakeWideButton("Open download folder");
        openFolder.Width = 155;
        openFolder.Margin = new Padding(4, 0, 7, 0);
        openFolder.Click += (_, _) => OpenFolder();
        toolbar.Controls.Add(openFolder);

        cancelButton.Text = "Cancel current";
        ConfigureActionButton(cancelButton, Color.FromArgb(118, 55, 61), 130);
        cancelButton.Margin = new Padding(4, 0, 0, 0);
        cancelButton.Enabled = false;
        cancelButton.Click += (_, _) => TryCancelProcess();
        toolbar.Controls.Add(cancelButton);

        var managerHeader = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 44,
            ColumnCount = 2,
            BackColor = WindowBg,
            Padding = new Padding(0, 3, 0, 3)
        };
        managerHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        managerHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 190));
        var queueLabel = new Label
        {
            Text = "Download queue",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 11F, FontStyle.Bold),
            Dock = DockStyle.Fill,
            TextAlign = ContentAlignment.MiddleLeft
        };
        channelQueueDownloadButton.Text = "Download channel ready ↓";
        StylePrimaryButton(channelQueueDownloadButton);
        channelQueueDownloadButton.Dock = DockStyle.Fill;
        channelQueueDownloadButton.Margin = new Padding(6, 2, 0, 2);
        channelQueueDownloadButton.Enabled = false;
        channelQueueDownloadButton.Click += async (_, _) => await DownloadReadyChannelQueueAsync();
        managerHeader.Controls.Add(queueLabel, 0, 0);
        managerHeader.Controls.Add(channelQueueDownloadButton, 1, 0);

        var content = new Panel { Dock = DockStyle.Fill, BackColor = WindowBg };
        downloadsManagerPanel.Dock = DockStyle.Fill;
        downloadsManagerPanel.AutoScroll = true;
        downloadsManagerPanel.FlowDirection = FlowDirection.TopDown;
        downloadsManagerPanel.WrapContents = false;
        downloadsManagerPanel.BackColor = WindowBg;
        downloadsManagerPanel.Padding = new Padding(0, 2, 6, 6);
        downloadsManagerPanel.Resize += (_, _) => RefreshDownloadManagerCards();

        var logCard = new Panel
        {
            Dock = DockStyle.Bottom,
            Height = 42,
            BackColor = Surface,
            Padding = new Padding(12, 7, 12, 9)
        };
        var logToggle = MakeSmallButton("Show activity log");
        logToggle.Dock = DockStyle.Top;
        logToggle.Height = 27;
        logToggle.Width = 140;
        logToggle.TextAlign = ContentAlignment.MiddleLeft;
        logBox.Multiline = true;
        logBox.ReadOnly = true;
        logBox.ScrollBars = ScrollBars.Vertical;
        logBox.BorderStyle = BorderStyle.None;
        logBox.BackColor = Color.FromArgb(25, 27, 35);
        logBox.ForeColor = Color.FromArgb(203, 207, 218);
        logBox.Font = new Font("Consolas", 8.5F);
        logBox.Dock = DockStyle.Fill;
        logBox.Visible = false;
        logToggle.Click += (_, _) =>
        {
            logBox.Visible = !logBox.Visible;
            logCard.Height = logBox.Visible ? 176 : 42;
            logToggle.Text = logBox.Visible ? "Hide activity log" : "Show activity log";
            logToggle.BringToFront();
        };
        logCard.Controls.Add(logBox);
        logCard.Controls.Add(logToggle);
        logToggle.BringToFront();

        content.Controls.Add(downloadsManagerPanel);
        content.Controls.Add(logCard);
        downloadsManagerPanel.BringToFront();

        downloadsView.Controls.Add(content);
        downloadsView.Controls.Add(managerHeader);
        downloadsView.Controls.Add(toolbar);
        downloadsView.Controls.Add(hero);
        downloadsView.Controls.Add(summaryCard);
        downloadsView.Controls.Add(sub);
        downloadsView.Controls.Add(title);

        RefreshDownloadManagerCards();
    }

    private void BuildPlaylistView()'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview12 BuildDownloadsView replacement failed: {n}')
s = s2

# Replace the old hidden channel-card renderer with manager synchronization.
pattern = re.compile(r'    private void RefreshChannelQueueCards\(\)\n    \{.*?\n    \}\n\n    private void UpdateChannelQueueActions\(\)', re.S)
replacement = r'''    private void RefreshChannelQueueCards()
    {
        foreach (var item in channelQueueItems)
        {
            var status = NormalizeManagerStatus(item.Status);
            var detail = item.Meta;
            var outputFolder = string.Empty;
            if (detail.StartsWith("Saved to ", StringComparison.OrdinalIgnoreCase))
                outputFolder = detail[9..].Trim();
            UpsertDownloadManagerItem(
                ManagerId("channel", item.Url),
                item.Url,
                item.Title,
                item.ThumbnailUrl,
                string.IsNullOrWhiteSpace(item.ChannelName) ? "Channel selection" : item.ChannelName,
                status,
                detail,
                outputFolder,
                preserveProgress: true);
        }
        RefreshDownloadManagerCards();
        UpdateChannelQueueActions();
    }

    private void UpdateChannelQueueActions()'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview12 RefreshChannelQueueCards replacement failed: {n}')
s = s2

# Replace action updater so the Downloads badge reflects the whole manager, not only channel selections.
pattern = re.compile(r'    private void UpdateChannelQueueActions\(\)\n    \{.*?\n    \}\n\n    private async Task DownloadReadyChannelQueueAsync', re.S)
replacement = r'''    private void UpdateChannelQueueActions()
    {
        var ready = channelQueueItems.Count(x => x.Status == "Ready");
        channelQueueDownloadButton.Enabled = ready > 0 && downloadCts == null;
        UpdateDownloadsNavBadge();
    }

    private async Task DownloadReadyChannelQueueAsync'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview12 UpdateChannelQueueActions replacement failed: {n}')
s = s2

# Insert manager helpers before SetDownloadsHero.
anchor = '    private void SetDownloadsHero(string title, string thumbnailUrl, string meta)\n'
if anchor not in s:
    raise SystemExit('Preview12 SetDownloadsHero anchor not found')
helpers = r'''    private static string ManagerId(string kind, string url) => kind + "|" + url;

    private void UpsertDownloadManagerItem(
        string id,
        string url,
        string title,
        string thumbnailUrl,
        string source,
        string status,
        string detail,
        string outputFolder,
        bool preserveProgress = false)
    {
        var item = downloadManagerItems.FirstOrDefault(x => x.Id == id);
        if (item == null)
        {
            item = new DownloadManagerItem { Id = id, Url = url };
            downloadManagerItems.Add(item);
        }
        item.Title = string.IsNullOrWhiteSpace(title) ? "YouTube video" : title;
        if (!string.IsNullOrWhiteSpace(thumbnailUrl)) item.ThumbnailUrl = thumbnailUrl;
        item.Source = string.IsNullOrWhiteSpace(source) ? "YouTube" : source;
        if (!string.IsNullOrWhiteSpace(status)) item.Status = status;
        if (!string.IsNullOrWhiteSpace(detail)) item.Detail = detail;
        if (!string.IsNullOrWhiteSpace(outputFolder)) item.OutputFolder = outputFolder;
        if (!preserveProgress && !IsManagerCompleted(item.Status))
        {
            item.Progress = 0;
            item.ProgressText = "0%";
        }
    }

    private void UpdateDownloadManagerItem(string id, string status, string? detail = null, int? progressValue = null, string? progressText = null, string? outputFolder = null)
    {
        var item = downloadManagerItems.FirstOrDefault(x => x.Id == id);
        if (item == null) return;
        if (!string.IsNullOrWhiteSpace(status)) item.Status = status;
        if (detail != null) item.Detail = detail;
        if (progressValue.HasValue) item.Progress = Math.Clamp(progressValue.Value, 0, 100);
        if (progressText != null) item.ProgressText = progressText;
        if (!string.IsNullOrWhiteSpace(outputFolder)) item.OutputFolder = outputFolder;
    }

    private static string NormalizeManagerStatus(string status)
    {
        if (string.IsNullOrWhiteSpace(status)) return "Queued";
        if (status.StartsWith("Downloading", StringComparison.OrdinalIgnoreCase)) return "Downloading";
        if (status.StartsWith("Analyzing", StringComparison.OrdinalIgnoreCase)) return "Analyzing";
        if (status.Contains("Waiting", StringComparison.OrdinalIgnoreCase)) return "Queued";
        if (status.Contains("Analysis failed", StringComparison.OrdinalIgnoreCase)) return "Failed";
        if (status.Contains("Failed", StringComparison.OrdinalIgnoreCase) || status.Contains("Error", StringComparison.OrdinalIgnoreCase)) return "Failed";
        if (status.Contains("Completed", StringComparison.OrdinalIgnoreCase)) return "Completed";
        if (status.Contains("Cancelled", StringComparison.OrdinalIgnoreCase)) return "Cancelled";
        if (status.Equals("Ready", StringComparison.OrdinalIgnoreCase)) return "Ready";
        return status;
    }

    private static bool IsManagerCompleted(string status)
        => status.Equals("Completed", StringComparison.OrdinalIgnoreCase);

    private static bool IsManagerFailed(string status)
        => status.Contains("Failed", StringComparison.OrdinalIgnoreCase) || status.Contains("Error", StringComparison.OrdinalIgnoreCase);

    private static bool IsManagerActive(string status)
        => !IsManagerCompleted(status) && !IsManagerFailed(status) && !status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase);

    private bool ManagerMatchesFilter(DownloadManagerItem item)
    {
        return downloadsManagerFilter switch
        {
            "Active" => IsManagerActive(item.Status),
            "Completed" => IsManagerCompleted(item.Status),
            "Failed" => IsManagerFailed(item.Status),
            _ => true
        };
    }

    private Color ManagerStatusColor(string status)
    {
        if (IsManagerCompleted(status)) return Accent;
        if (IsManagerFailed(status)) return Color.FromArgb(238, 104, 116);
        if (status.Equals("Downloading", StringComparison.OrdinalIgnoreCase) || status.Equals("Merging", StringComparison.OrdinalIgnoreCase))
            return Color.FromArgb(90, 169, 255);
        if (status.Equals("Analyzing", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(218, 172, 80);
        if (status.Equals("Ready", StringComparison.OrdinalIgnoreCase)) return Color.FromArgb(128, 214, 178);
        return TextMuted;
    }

    private void RefreshDownloadManagerCards()
    {
        if (downloadsManagerPanel.IsDisposed) return;
        downloadsManagerPanel.SuspendLayout();
        try
        {
            downloadsManagerPanel.Controls.Clear();
            var visible = downloadManagerItems.Where(ManagerMatchesFilter).ToList();
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
                var width = Math.Max(650, downloadsManagerPanel.ClientSize.Width - 28);
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
                    var itemTitle = new Label
                    {
                        Left = 154,
                        Top = 10,
                        Width = middleWidth,
                        Height = 25,
                        Text = item.Title,
                        AutoEllipsis = true,
                        ForeColor = TextMain,
                        Font = new Font("Segoe UI Semibold", 9.8F, FontStyle.Bold)
                    };
                    var source = new Label
                    {
                        Left = 154,
                        Top = 36,
                        Width = middleWidth,
                        Height = 19,
                        Text = item.Source,
                        AutoEllipsis = true,
                        ForeColor = TextMuted,
                        Font = new Font("Segoe UI", 8.5F)
                    };
                    var detail = new Label
                    {
                        Left = 154,
                        Top = 56,
                        Width = middleWidth,
                        Height = 18,
                        Text = item.Detail,
                        AutoEllipsis = true,
                        ForeColor = TextMuted,
                        Font = new Font("Segoe UI", 8.2F)
                    };
                    var bar = new ProgressBar
                    {
                        Left = 154,
                        Top = 82,
                        Width = Math.Max(180, middleWidth - 58),
                        Height = 8,
                        Minimum = 0,
                        Maximum = 100,
                        Value = Math.Clamp(item.Progress, 0, 100),
                        Style = ProgressBarStyle.Continuous
                    };
                    var pct = new Label
                    {
                        Left = 154 + Math.Max(180, middleWidth - 54),
                        Top = 76,
                        Width = 54,
                        Height = 20,
                        Text = string.IsNullOrWhiteSpace(item.ProgressText) ? item.Progress + "%" : item.ProgressText,
                        ForeColor = Accent,
                        Font = new Font("Segoe UI Semibold", 8.2F, FontStyle.Bold),
                        TextAlign = ContentAlignment.MiddleRight
                    };
                    var status = new Label
                    {
                        Left = width - rightWidth + 10,
                        Top = 12,
                        Width = rightWidth - 28,
                        Height = 24,
                        Text = item.Status,
                        ForeColor = ManagerStatusColor(item.Status),
                        Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold),
                        TextAlign = ContentAlignment.MiddleRight,
                        AutoEllipsis = true
                    };

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
                            RefreshDownloadManagerCards();
                        };
                        card.Controls.Add(remove);
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
        }
    }

    private void UpdateDownloadsSummary()
    {
        var total = downloadManagerItems.Count;
        var completed = downloadManagerItems.Count(x => IsManagerCompleted(x.Status));
        var failed = downloadManagerItems.Count(x => IsManagerFailed(x.Status));
        var queued = downloadManagerItems.Count(x => x.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase) || x.Status.Equals("Ready", StringComparison.OrdinalIgnoreCase));
        var active = Math.Max(0, total - completed - failed - queued - downloadManagerItems.Count(x => x.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase)));
        downloadsSummary.Text = $"Total {total}   •   Active {active}   •   Queued {queued}   •   Completed {completed}   •   Failed {failed}";
    }

    private void UpdateDownloadsNavBadge()
    {
        var pending = downloadManagerItems.Count(x => !IsManagerCompleted(x.Status) && !x.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase));
        downloadsNav.Text = pending > 0 ? $"↓   Downloads ({pending})" : "↓   Downloads";
    }

    private void OpenManagerFolder(string folder)
    {
        try
        {
            var target = string.IsNullOrWhiteSpace(folder) ? folderBox.Text : folder;
            if (!Directory.Exists(target)) Directory.CreateDirectory(target);
            Process.Start(new ProcessStartInfo("explorer.exe", target) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            AppendLog("Open folder note: " + ex.Message);
        }
    }

    private void SetActiveManagerStatus(string status)
    {
        if (string.IsNullOrWhiteSpace(activeDownloadManagerId)) return;
        var item = downloadManagerItems.FirstOrDefault(x => x.Id == activeDownloadManagerId);
        if (item == null) return;
        var normalized = status.Contains("Joining", StringComparison.OrdinalIgnoreCase) || status.Contains("Merging", StringComparison.OrdinalIgnoreCase)
            ? "Merging"
            : status.Contains("Downloading", StringComparison.OrdinalIgnoreCase)
                ? "Downloading"
                : status.Contains("Preparing", StringComparison.OrdinalIgnoreCase)
                    ? "Processing"
                    : status;
        if (!string.Equals(item.Status, normalized, StringComparison.Ordinal))
        {
            item.Status = normalized;
            RefreshDownloadManagerCards();
        }
    }

    private void UpdateActiveManagerEngineDetail(string clean)
    {
        if (string.IsNullOrWhiteSpace(activeDownloadManagerId)) return;
        var item = downloadManagerItems.FirstOrDefault(x => x.Id == activeDownloadManagerId);
        if (item == null) return;
        var speed = Regex.Match(clean, @"\bat\s+(?<v>[^\s]+/s)", RegexOptions.IgnoreCase);
        var eta = Regex.Match(clean, @"\bETA\s+(?<v>[0-9:]+)", RegexOptions.IgnoreCase);
        if (!speed.Success && !eta.Success) return;
        var bits = new List<string>();
        if (speed.Success) bits.Add(speed.Groups["v"].Value);
        if (eta.Success) bits.Add("ETA " + eta.Groups["v"].Value);
        if (bits.Count > 0) item.Detail = string.Join("  •  ", bits);
    }

'''
s = s.replace(anchor, helpers + anchor, 1)

# Single-video download: create/update one manager item and keep it visible after completion/failure.
old = '        AppendLog("Download started • " + qualityBox.SelectedItem + " • " + (audioBox.SelectedItem ?? "Original"));\n'
new = old + '''        var managerItemId = ManagerId("single", url);\n        UpsertDownloadManagerItem(\n            managerItemId,\n            url,\n            mediaTitle.Text,\n            currentMediaThumbnailUrl,\n            "Single video",\n            "Downloading",\n            (qualityBox.SelectedItem ?? "Default quality") + "  •  " + (audioBox.SelectedItem ?? "Original/default"),\n            folderBox.Text);\n        activeDownloadManagerId = managerItemId;\n        lastManagerProgressRendered = -1;\n        lastManagerProgressTick = 0;\n        RefreshDownloadManagerCards();\n'''
if old not in s:
    raise SystemExit('Preview12 single download start anchor not found')
s = s.replace(old, new, 1)

old = '                AppendLog("Completed successfully.");\n'
new = '''                AppendLog("Completed successfully.");\n                UpdateDownloadManagerItem(managerItemId, "Completed", "Saved successfully", 100, "100%", folderBox.Text);\n                RefreshDownloadManagerCards();\n'''
if old not in s:
    raise SystemExit('Preview12 single completed anchor not found')
s = s.replace(old, new, 1)

old = '                AppendLog("yt-dlp exited with code " + exit);\n'
new = '''                AppendLog("yt-dlp exited with code " + exit);\n                UpdateDownloadManagerItem(managerItemId, "Failed", "Download did not complete");\n                RefreshDownloadManagerCards();\n'''
if old not in s:
    raise SystemExit('Preview12 single failed anchor not found')
s = s.replace(old, new, 1)

old = '            AppendLog("Download cancelled.");\n'
new = '''            AppendLog("Download cancelled.");\n            UpdateDownloadManagerItem(managerItemId, "Cancelled", "Cancelled by user");\n            RefreshDownloadManagerCards();\n'''
if old not in s:
    raise SystemExit('Preview12 single cancelled anchor not found')
s = s.replace(old, new, 1)

old = '            AppendLog("Error: " + ex.Message);\n'
new = '''            AppendLog("Error: " + ex.Message);\n            UpdateDownloadManagerItem(managerItemId, "Failed", ex.Message);\n            RefreshDownloadManagerCards();\n'''
if old not in s:
    raise SystemExit('Preview12 single exception anchor not found')
s = s.replace(old, new, 1)

# Clear active manager pointer in the single-download finally block.
method_start = s.find('private async Task DownloadAsync()')
if method_start < 0:
    raise SystemExit('Preview12 DownloadAsync method not found')
finally_anchor = '            downloadButton.Enabled = true;\n'
finally_pos = s.find(finally_anchor, method_start)
if finally_pos < 0:
    raise SystemExit('Preview12 DownloadAsync finally anchor not found')
s = s[:finally_pos + len(finally_anchor)] + '            activeDownloadManagerId = string.Empty;\n            RefreshDownloadManagerCards();\n' + s[finally_pos + len(finally_anchor):]

# Playlist batch: register every selected video in the manager before the batch starts.
playlist_start = s.find('private async Task DownloadSelectedPlaylistAsync()')
if playlist_start < 0:
    raise SystemExit('Preview12 playlist download method not found')
anchor_text = '        AppendLog($"Playlist batch started • selected={selectedRows.Count} • Original/default audio");\n'
pos = s.find(anchor_text, playlist_start)
if pos < 0:
    raise SystemExit('Preview12 playlist batch start anchor not found')
insert = r'''        foreach (var selectedRow in selectedRows)
        {
            if (selectedRow.Tag is not int selectedIndex || selectedIndex < 0 || selectedIndex >= playlistItems.Count) continue;
            var selectedItem = playlistItems[selectedIndex];
            UpsertDownloadManagerItem(
                ManagerId("playlist", selectedItem.Url),
                selectedItem.Url,
                selectedItem.Title,
                ThumbnailFromYouTubeUrl(selectedItem.Url),
                string.IsNullOrWhiteSpace(currentPlaylistTitle) ? "Playlist" : currentPlaylistTitle,
                "Queued",
                "Waiting in playlist batch",
                playlistFolder);
        }
        RefreshDownloadManagerCards();
'''
s = s[:pos + len(anchor_text)] + insert + s[pos + len(anchor_text):]

# Playlist item loop: activate/update each manager card.
old = '                var item = playlistItems[itemIndex];\n                SetDownloadsHero(item.Title, ThumbnailFromYouTubeUrl(item.Url), $"Playlist {i + 1}/{selectedRows.Count}  •  Original/default audio");\n'
new = '''                var item = playlistItems[itemIndex];\n                var playlistManagerId = ManagerId("playlist", item.Url);\n                activeDownloadManagerId = playlistManagerId;\n                lastManagerProgressRendered = -1;\n                lastManagerProgressTick = 0;\n                UpdateDownloadManagerItem(playlistManagerId, "Downloading", $"Playlist {i + 1}/{selectedRows.Count}  •  Original/default audio", 0, "0%", playlistFolder);\n                RefreshDownloadManagerCards();\n                SetDownloadsHero(item.Title, ThumbnailFromYouTubeUrl(item.Url), $"Playlist {i + 1}/{selectedRows.Count}  •  Original/default audio");\n'''
if old not in s:
    raise SystemExit('Preview12 playlist loop anchor not found')
s = s.replace(old, new, 1)

old = '                    row.SubItems[3].Text = "Completed";\n'
new = '''                    row.SubItems[3].Text = "Completed";\n                    UpdateDownloadManagerItem(playlistManagerId, "Completed", "Saved to " + playlistFolder, 100, "100%", playlistFolder);\n'''
# First occurrence after playlist method only.
pos = s.find(old, playlist_start)
if pos < 0:
    raise SystemExit('Preview12 playlist completed anchor not found')
s = s[:pos] + new + s[pos + len(old):]

old = '                    row.SubItems[3].Text = "Failed";\n'
new = '''                    row.SubItems[3].Text = "Failed";\n                    UpdateDownloadManagerItem(playlistManagerId, "Failed", "Playlist item failed", outputFolder: playlistFolder);\n'''
pos = s.find(old, playlist_start)
if pos < 0:
    raise SystemExit('Preview12 playlist failed anchor not found')
s = s[:pos] + new + s[pos + len(old):]

# Clear active pointer after each playlist item.
old = '                RefreshChannelQueueCards();\n'
# Do not use this generic anchor for playlist; instead insert immediately after the playlist failure/success if block.
loop_exit_anchor = '                    AppendLog($"Playlist item failed: {item.Title} • exit={exit}");\n                }\n'
pos = s.find(loop_exit_anchor, playlist_start)
if pos < 0:
    raise SystemExit('Preview12 playlist loop exit anchor not found')
s = s[:pos + len(loop_exit_anchor)] + '                activeDownloadManagerId = string.Empty;\n                RefreshDownloadManagerCards();\n' + s[pos + len(loop_exit_anchor):]

# Channel batch: set the active manager card and exact named output folder.
channel_start = s.find('private async Task DownloadReadyChannelQueueAsync()')
if channel_start < 0:
    raise SystemExit('Preview12 channel batch method not found')
old = '''                var channelFolder = BuildNamedSubfolder(folderBox.Text, item.ChannelName, "YouTube Channel");\n                Directory.CreateDirectory(channelFolder);\n                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable, channelFolder);\n'''
new = '''                var channelFolder = BuildNamedSubfolder(folderBox.Text, item.ChannelName, "YouTube Channel");\n                Directory.CreateDirectory(channelFolder);\n                var channelManagerId = ManagerId("channel", item.Url);\n                activeDownloadManagerId = channelManagerId;\n                lastManagerProgressRendered = -1;\n                lastManagerProgressTick = 0;\n                UpdateDownloadManagerItem(channelManagerId, "Downloading", $"Channel {i + 1}/{ready.Count}  •  Original/default audio", 0, "0%", channelFolder);\n                RefreshDownloadManagerCards();\n                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable, channelFolder);\n'''
if old not in s:
    raise SystemExit('Preview12 channel folder/args anchor not found')
s = s.replace(old, new, 1)

old = '                    item.Meta = "Saved to " + channelFolder;\n'
new = '''                    item.Meta = "Saved to " + channelFolder;\n                    UpdateDownloadManagerItem(channelManagerId, "Completed", item.Meta, 100, "100%", channelFolder);\n'''
if old not in s:
    raise SystemExit('Preview12 channel completed anchor not found')
s = s.replace(old, new, 1)

old = '                    item.Status = "Failed";\n                    AppendLog("Channel queue item failed: " + item.Title + " • exit=" + exit);\n'
new = '''                    item.Status = "Failed";\n                    UpdateDownloadManagerItem(channelManagerId, "Failed", "Channel item failed", outputFolder: channelFolder);\n                    AppendLog("Channel queue item failed: " + item.Title + " • exit=" + exit);\n'''
if old not in s:
    raise SystemExit('Preview12 channel failed anchor not found')
s = s.replace(old, new, 1)

old = '                RefreshChannelQueueCards();\n            }\n            SetProgress(100, "100%");\n'
new = '''                activeDownloadManagerId = string.Empty;\n                RefreshChannelQueueCards();\n            }\n            SetProgress(100, "100%");\n'''
if old not in s:
    raise SystemExit('Preview12 channel loop exit anchor not found')
s = s.replace(old, new, 1)

# SetStatus now also drives the active card's high-level state.
old = '''        statusLabel.Text = status;\n        downloadsStatus.Text = status;\n        if (downloadTray.Visible) mediaMeta.Text = status;\n'''
new = '''        statusLabel.Text = status;\n        downloadsStatus.Text = status;\n        if (downloadTray.Visible) mediaMeta.Text = status;\n        SetActiveManagerStatus(status);\n'''
if old not in s:
    raise SystemExit('Preview12 SetStatus anchor not found')
s = s.replace(old, new, 1)

# SetProgress updates only the active manager item and throttles card rebuilds.
old = '''        percentLabel.Text = text;\n        downloadsPercent.Text = text;\n'''
new = '''        percentLabel.Text = text;\n        downloadsPercent.Text = text;\n        if (!string.IsNullOrWhiteSpace(activeDownloadManagerId))\n        {\n            var item = downloadManagerItems.FirstOrDefault(x => x.Id == activeDownloadManagerId);\n            if (item != null)\n            {\n                item.Progress = value;\n                item.ProgressText = text;\n                var now = Environment.TickCount64;\n                if (value == 100 || Math.Abs(value - lastManagerProgressRendered) >= 1 || now - lastManagerProgressTick >= 250)\n                {\n                    lastManagerProgressRendered = value;\n                    lastManagerProgressTick = now;\n                    RefreshDownloadManagerCards();\n                }\n            }\n        }\n'''
if old not in s:
    raise SystemExit('Preview12 SetProgress anchor not found')
s = s.replace(old, new, 1)

# Capture speed/ETA from yt-dlp lines for the active card.
old = '''        if (!clean.StartsWith("[download]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Destination", StringComparison.OrdinalIgnoreCase) || clean.Contains("100%"))\n            AppendLog(clean);\n'''
new = '''        UpdateActiveManagerEngineDetail(clean);\n        if (!clean.StartsWith("[download]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Destination", StringComparison.OrdinalIgnoreCase) || clean.Contains("100%"))\n            AppendLog(clean);\n'''
if old not in s:
    raise SystemExit('Preview12 HandleEngineLine anchor not found')
s = s.replace(old, new, 1)

# Add the manager model near the existing mutable ChannelQueueItem model.
record_anchor = '    private sealed record QualityChoice(string Label, int Height, bool AudioOnly, bool BestAvailable, double EstimatedBytes, double Fps, string Codec);\n'
if record_anchor not in s:
    raise SystemExit('Preview12 record anchor not found')
model = '''    private sealed class DownloadManagerItem\n    {\n        public string Id { get; set; } = string.Empty;\n        public string Url { get; set; } = string.Empty;\n        public string Title { get; set; } = string.Empty;\n        public string ThumbnailUrl { get; set; } = string.Empty;\n        public string Source { get; set; } = string.Empty;\n        public string Status { get; set; } = "Queued";\n        public string Detail { get; set; } = string.Empty;\n        public string OutputFolder { get; set; } = string.Empty;\n        public int Progress { get; set; }\n        public string ProgressText { get; set; } = "0%";\n    }\n\n'''
s = s.replace(record_anchor, model + record_anchor, 1)

# Preview identity.
s = s.replace('Text = "PC v1.2 Preview 11 Hotfix 1",', 'Text = "PC v1.2 Preview 12",', 1)
s = s.replace('Browser UI v1.2 Preview 11 Hotfix 1 starting', 'Browser UI v1.2 Preview 12 starting', 1)

p.write_text(s, encoding='utf-8')

# Installer identity.
iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview11-Hotfix1-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview12-Setup', 1)
iss.write_text(i, encoding='utf-8')

# Build-time sanity checks: preserve all known-working layers.
check = p.read_text(encoding='utf-8')
required = [
    'window.__rmsChannelSelectorInstalledV10',
    'outputTemplate = Path.Combine(targetFolder',
    'var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;',
    'private sealed class DownloadManagerItem',
    'Everything in one place — queued, active, completed and failed downloads stay visible.',
    'UpdateActiveManagerEngineDetail(clean);'
]
for marker in required:
    if marker not in check:
        raise SystemExit('Preview12 sanity check failed: ' + marker)

print('Applied PC v1.2 Preview 12 professional Download Manager UI/UX')
