from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# ---------- Preview 4 fields/state ----------
old = '    private readonly Button playlistDownloadButton = new();\n'
new = old + '''    private readonly PictureBox downloadsThumbnail = new();\n    private readonly Label downloadsTitle = new();\n    private readonly Label downloadsMeta = new();\n    private readonly FlowLayoutPanel channelQueuePanel = new();\n    private readonly Button channelQueueDownloadButton = new();\n'''
if old not in s: raise SystemExit('Preview4 UI field anchor not found')
s = s.replace(old, new, 1)

old = '    private bool loadingSettings;\n'
new = old + '''    private readonly List<ChannelQueueItem> channelQueueItems = new();\n    private CancellationTokenSource? channelQueueAnalysisCts;\n    private bool channelQueueAnalysisRunning;\n    private string currentMediaThumbnailUrl = string.Empty;\n'''
if old not in s: raise SystemExit('Preview4 state anchor not found')
s = s.replace(old, new, 1)

# ---------- Prettier Downloads page with thumbnail + channel queue ----------
pattern = re.compile(r'    private void BuildDownloadsView\(\)\n    \{.*?\n    \}\n\n    private void BuildPlaylistView\(\)', re.S)
replacement = r'''    private void BuildDownloadsView()
    {
        downloadsView.Dock = DockStyle.Fill;
        downloadsView.BackColor = WindowBg;
        downloadsView.Padding = new Padding(30, 24, 30, 24);
        downloadsView.Visible = false;

        var title = new Label
        {
            Text = "Downloads",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 24F, FontStyle.Bold),
            Dock = DockStyle.Top,
            Height = 50
        };
        var sub = new Label
        {
            Text = "Selected channel videos are analyzed here — never on the channel page.",
            ForeColor = TextMuted,
            Font = new Font("Segoe UI", 10F),
            Dock = DockStyle.Top,
            Height = 34
        };

        var hero = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 150,
            ColumnCount = 2,
            BackColor = Surface,
            Padding = new Padding(14),
            Margin = new Padding(0, 10, 0, 10)
        };
        hero.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 190));
        hero.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

        downloadsThumbnail.Dock = DockStyle.Fill;
        downloadsThumbnail.BackColor = Surface2;
        downloadsThumbnail.SizeMode = PictureBoxSizeMode.Zoom;
        downloadsThumbnail.Margin = new Padding(0, 0, 16, 0);
        hero.Controls.Add(downloadsThumbnail, 0, 0);

        var heroInfo = new Panel { Dock = DockStyle.Fill, BackColor = Surface, Padding = new Padding(4, 3, 2, 2) };
        downloadsTitle.Text = "Ready for your next download";
        downloadsTitle.AutoEllipsis = true;
        downloadsTitle.ForeColor = TextMain;
        downloadsTitle.Font = new Font("Segoe UI Semibold", 13F, FontStyle.Bold);
        downloadsTitle.Dock = DockStyle.Top;
        downloadsTitle.Height = 34;

        downloadsMeta.Text = "Select videos from a YouTube channel or open a single video.";
        downloadsMeta.AutoEllipsis = true;
        downloadsMeta.ForeColor = TextMuted;
        downloadsMeta.Font = new Font("Segoe UI", 9.3F);
        downloadsMeta.Dock = DockStyle.Top;
        downloadsMeta.Height = 28;

        downloadsStatus.Text = "Ready";
        downloadsStatus.ForeColor = TextMain;
        downloadsStatus.Font = new Font("Segoe UI Semibold", 10.5F, FontStyle.Bold);
        downloadsStatus.Dock = DockStyle.Top;
        downloadsStatus.Height = 27;

        downloadsPercent.Text = "0%";
        downloadsPercent.ForeColor = Accent;
        downloadsPercent.Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold);
        downloadsPercent.TextAlign = ContentAlignment.MiddleRight;
        downloadsPercent.Dock = DockStyle.Top;
        downloadsPercent.Height = 23;

        downloadsProgress.Dock = DockStyle.Top;
        downloadsProgress.Height = 12;
        downloadsProgress.Minimum = 0;
        downloadsProgress.Maximum = 100;

        heroInfo.Controls.Add(downloadsProgress);
        heroInfo.Controls.Add(downloadsPercent);
        heroInfo.Controls.Add(downloadsStatus);
        heroInfo.Controls.Add(downloadsMeta);
        heroInfo.Controls.Add(downloadsTitle);
        hero.Controls.Add(heroInfo, 1, 0);

        var actions = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 52,
            FlowDirection = FlowDirection.LeftToRight,
            Padding = new Padding(0, 8, 0, 6),
            BackColor = WindowBg
        };
        var openFolder = MakeWideButton("Open download folder");
        openFolder.Click += (_, _) => OpenFolder();
        cancelButton.Text = "Cancel current task";
        ConfigureActionButton(cancelButton, Color.FromArgb(118, 55, 61), 160);
        cancelButton.Enabled = false;
        cancelButton.Click += (_, _) => TryCancelProcess();
        actions.Controls.Add(openFolder);
        actions.Controls.Add(cancelButton);

        var queueHeader = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 48,
            ColumnCount = 2,
            BackColor = WindowBg,
            Padding = new Padding(0, 4, 0, 4)
        };
        queueHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        queueHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 190));
        var queueLabel = new Label
        {
            Text = "Channel selections",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 11F, FontStyle.Bold),
            Dock = DockStyle.Fill,
            TextAlign = ContentAlignment.MiddleLeft
        };
        channelQueueDownloadButton.Text = "Download ready  ↓";
        StylePrimaryButton(channelQueueDownloadButton);
        channelQueueDownloadButton.Dock = DockStyle.Fill;
        channelQueueDownloadButton.Margin = new Padding(6, 2, 0, 2);
        channelQueueDownloadButton.Enabled = false;
        channelQueueDownloadButton.Click += async (_, _) => await DownloadReadyChannelQueueAsync();
        queueHeader.Controls.Add(queueLabel, 0, 0);
        queueHeader.Controls.Add(channelQueueDownloadButton, 1, 0);

        var content = new Panel { Dock = DockStyle.Fill, BackColor = WindowBg };
        channelQueuePanel.Dock = DockStyle.Fill;
        channelQueuePanel.AutoScroll = true;
        channelQueuePanel.FlowDirection = FlowDirection.TopDown;
        channelQueuePanel.WrapContents = false;
        channelQueuePanel.BackColor = WindowBg;
        channelQueuePanel.Padding = new Padding(0, 4, 6, 6);
        channelQueuePanel.Resize += (_, _) => RefreshChannelQueueCards();

        var logCard = new Panel { Dock = DockStyle.Bottom, Height = 135, BackColor = Surface, Padding = new Padding(14) };
        var logTitle = new Label { Text = "Activity", Dock = DockStyle.Top, Height = 26, ForeColor = TextMain, Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold) };
        logBox.Multiline = true;
        logBox.ReadOnly = true;
        logBox.ScrollBars = ScrollBars.Vertical;
        logBox.BorderStyle = BorderStyle.None;
        logBox.BackColor = Color.FromArgb(25, 27, 35);
        logBox.ForeColor = Color.FromArgb(203, 207, 218);
        logBox.Font = new Font("Consolas", 8.7F);
        logBox.Dock = DockStyle.Fill;
        logCard.Controls.Add(logBox);
        logCard.Controls.Add(logTitle);
        logBox.BringToFront();

        content.Controls.Add(channelQueuePanel);
        content.Controls.Add(logCard);
        channelQueuePanel.BringToFront();

        downloadsView.Controls.Add(content);
        downloadsView.Controls.Add(queueHeader);
        downloadsView.Controls.Add(actions);
        downloadsView.Controls.Add(hero);
        downloadsView.Controls.Add(sub);
        downloadsView.Controls.Add(title);
    }

    private void BuildPlaylistView()'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'BuildDownloadsView replacement failed: {n}')
s = s2

# ---------- Channel thumbnail selector bridge ----------
old = '''            await browser.EnsureCoreWebView2Async();\n            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;\n'''
new = '''            await browser.EnsureCoreWebView2Async();\n            browser.CoreWebView2.WebMessageReceived += BrowserWebMessageReceived;\n            await browser.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(ChannelSelectorScript());\n            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;\n'''
if old not in s: raise SystemExit('WebView2 init anchor not found')
s = s.replace(old, new, 1)

anchor = '    private async Task HandleBrowserNavigationAsync()\n'
channel_methods = r'''    private static string ChannelSelectorScript() => """
(() => {
  if (window.__rmsChannelSelectorInstalled) return;
  window.__rmsChannelSelectorInstalled = true;

  const isChannelPage = () => {
    const p = location.pathname || '';
    return p.startsWith('/@') || p.startsWith('/channel/') || p.startsWith('/c/') || p.startsWith('/user/');
  };

  const decorate = () => {
    if (!isChannelPage()) return;
    const cards = document.querySelectorAll('ytd-rich-item-renderer, ytd-rich-grid-media, ytd-grid-video-renderer, ytd-video-renderer');
    cards.forEach(card => {
      if (card.querySelector('.rms-channel-select')) return;
      const link = card.querySelector('a#thumbnail[href*="/watch"]') || card.querySelector('a[href*="/watch?v="]');
      if (!link || !link.href) return;
      const host = link.closest('#thumbnail') || link.parentElement || card;
      if (!host) return;
      const cs = getComputedStyle(host);
      if (cs.position === 'static') host.style.position = 'relative';

      const titleEl = card.querySelector('#video-title-link, #video-title, a[title]');
      const img = card.querySelector('img.yt-core-image, #img, img');
      const button = document.createElement('button');
      button.className = 'rms-channel-select';
      button.textContent = '↓ Select';
      button.title = 'Add to Rizwan Media Saver Downloads';
      Object.assign(button.style, {
        position: 'absolute', right: '8px', bottom: '8px', zIndex: '9999',
        border: '0', borderRadius: '8px', padding: '7px 11px',
        background: '#1fc984', color: '#09231a', fontWeight: '700',
        fontSize: '12px', cursor: 'pointer', boxShadow: '0 2px 10px rgba(0,0,0,.35)'
      });
      button.addEventListener('click', ev => {
        ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation();
        const url = new URL(link.href, location.origin).href;
        const title = (titleEl?.getAttribute('title') || titleEl?.textContent || 'YouTube video').trim();
        const thumbnail = img?.currentSrc || img?.src || '';
        window.chrome.webview.postMessage({ type: 'rms-channel-select', url, title, thumbnail });
        button.textContent = '✓ Selected';
        button.disabled = true;
        button.style.opacity = '0.82';
        button.style.cursor = 'default';
      }, true);
      host.appendChild(button);
    });
  };

  const observer = new MutationObserver(() => decorate());
  observer.observe(document.documentElement, { childList: true, subtree: true });
  setInterval(decorate, 1200);
  decorate();
})();
""";

    private void BrowserWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            using var doc = JsonDocument.Parse(e.WebMessageAsJson);
            var root = doc.RootElement;
            if (!root.TryGetProperty("type", out var typeEl) || !string.Equals(typeEl.GetString(), "rms-channel-select", StringComparison.Ordinal)) return;
            var url = root.TryGetProperty("url", out var urlEl) ? urlEl.GetString() ?? string.Empty : string.Empty;
            var title = root.TryGetProperty("title", out var titleEl) ? titleEl.GetString() ?? "YouTube video" : "YouTube video";
            var thumbnail = root.TryGetProperty("thumbnail", out var thumbEl) ? thumbEl.GetString() ?? string.Empty : string.Empty;
            AddChannelQueueItem(url, title, thumbnail);
        }
        catch (Exception ex)
        {
            AppendLog("Channel selection message ignored: " + ex.Message);
        }
    }

    private void AddChannelQueueItem(string url, string title, string thumbnail)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || !uri.Host.Contains("youtube", StringComparison.OrdinalIgnoreCase)) return;
        if (channelQueueItems.Any(x => string.Equals(x.Url, url, StringComparison.Ordinal))) return;
        if (string.IsNullOrWhiteSpace(thumbnail)) thumbnail = ThumbnailFromYouTubeUrl(url);
        channelQueueItems.Add(new ChannelQueueItem
        {
            Url = url,
            Title = string.IsNullOrWhiteSpace(title) ? "YouTube video" : title,
            ThumbnailUrl = thumbnail,
            Status = "Waiting for analysis",
            Meta = "Selected from channel"
        });
        downloadsNav.Text = $"↓   Downloads ({channelQueueItems.Count})";
        AppendLog("Channel selection added (no channel-page analysis): " + title);
        RefreshChannelQueueCards();
        _ = ProcessChannelQueueAnalysisAsync();
    }

    private async Task ProcessChannelQueueAnalysisAsync()
    {
        if (channelQueueAnalysisRunning) return;
        channelQueueAnalysisRunning = true;
        channelQueueAnalysisCts ??= new CancellationTokenSource();
        var token = channelQueueAnalysisCts.Token;
        try
        {
            while (true)
            {
                var item = channelQueueItems.FirstOrDefault(x => x.Status == "Waiting for analysis");
                if (item == null) break;
                item.Status = "Analyzing…";
                item.Meta = "Reading title and available formats in Downloads";
                RefreshChannelQueueCards();

                try
                {
                    var result = await RunMediaProbeAsync(item.Url, token, richAudio: false);
                    token.ThrowIfCancellationRequested();
                    if (result.ExitCode != 0 || string.IsNullOrWhiteSpace(result.Output))
                        throw new InvalidOperationException("Video information unavailable");
                    using var doc = JsonDocument.Parse(result.Output);
                    var root = doc.RootElement;
                    item.Title = JsonString(root, "title") ?? item.Title;
                    var thumb = JsonString(root, "thumbnail");
                    if (!string.IsNullOrWhiteSpace(thumb)) item.ThumbnailUrl = thumb!;
                    var uploader = JsonString(root, "uploader") ?? JsonString(root, "channel") ?? string.Empty;
                    var duration = JsonDouble(root, "duration");
                    var quality = GetDefaultQualityChoice();
                    var bits = new List<string>();
                    if (duration > 0) bits.Add(FormatDuration(duration));
                    if (!string.IsNullOrWhiteSpace(uploader)) bits.Add(uploader);
                    bits.Add(quality.BestAvailable ? "Best available" : quality.Height + "p default");
                    item.Meta = string.Join("  •  ", bits);
                    item.Status = "Ready";
                }
                catch (OperationCanceledException) { throw; }
                catch (Exception ex)
                {
                    item.Status = "Analysis failed";
                    item.Meta = ex.Message;
                    AppendLog("Channel queue analysis note: " + ex.Message);
                }
                RefreshChannelQueueCards();
            }
        }
        catch (OperationCanceledException) { }
        finally
        {
            channelQueueAnalysisRunning = false;
            UpdateChannelQueueActions();
        }
    }

    private void RefreshChannelQueueCards()
    {
        if (channelQueuePanel.IsDisposed) return;
        channelQueuePanel.SuspendLayout();
        try
        {
            channelQueuePanel.Controls.Clear();
            if (channelQueueItems.Count == 0)
            {
                var empty = new Label
                {
                    Text = "Open a YouTube channel and use the green Select button on any thumbnail.",
                    ForeColor = TextMuted,
                    Font = new Font("Segoe UI", 10F),
                    AutoSize = false,
                    Width = Math.Max(520, channelQueuePanel.ClientSize.Width - 24),
                    Height = 62,
                    TextAlign = ContentAlignment.MiddleCenter,
                    BackColor = Surface
                };
                channelQueuePanel.Controls.Add(empty);
                UpdateChannelQueueActions();
                return;
            }

            var width = Math.Max(560, channelQueuePanel.ClientSize.Width - 28);
            foreach (var item in channelQueueItems)
            {
                var card = new Panel { Width = width, Height = 92, BackColor = Surface, Margin = new Padding(0, 0, 0, 8), Padding = new Padding(10) };
                var pic = new PictureBox { Width = 128, Height = 72, Left = 10, Top = 10, SizeMode = PictureBoxSizeMode.Zoom, BackColor = Surface2 };
                if (!string.IsNullOrWhiteSpace(item.ThumbnailUrl))
                {
                    pic.ImageLocation = item.ThumbnailUrl;
                    try { pic.LoadAsync(); } catch { }
                }
                var title = new Label { Left = 150, Top = 10, Width = Math.Max(280, width - 165), Height = 28, Text = item.Title, AutoEllipsis = true, ForeColor = TextMain, Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold) };
                var meta = new Label { Left = 150, Top = 39, Width = Math.Max(280, width - 165), Height = 20, Text = item.Meta, AutoEllipsis = true, ForeColor = TextMuted, Font = new Font("Segoe UI", 8.7F) };
                var status = new Label { Left = 150, Top = 62, Width = Math.Max(280, width - 165), Height = 20, Text = item.Status, AutoEllipsis = true, ForeColor = item.Status == "Ready" || item.Status == "Completed" ? Accent : TextMuted, Font = new Font("Segoe UI Semibold", 8.7F, FontStyle.Bold) };
                card.Controls.Add(pic);
                card.Controls.Add(title);
                card.Controls.Add(meta);
                card.Controls.Add(status);
                channelQueuePanel.Controls.Add(card);
            }
        }
        finally
        {
            channelQueuePanel.ResumeLayout();
            UpdateChannelQueueActions();
        }
    }

    private void UpdateChannelQueueActions()
    {
        var ready = channelQueueItems.Count(x => x.Status == "Ready");
        channelQueueDownloadButton.Enabled = ready > 0 && downloadCts == null;
        if (channelQueueItems.Count == 0) downloadsNav.Text = "↓   Downloads";
        else downloadsNav.Text = $"↓   Downloads ({channelQueueItems.Count})";
    }

    private async Task DownloadReadyChannelQueueAsync()
    {
        if (downloadCts != null) return;
        var ready = channelQueueItems.Where(x => x.Status == "Ready").ToList();
        if (ready.Count == 0) return;
        if (string.IsNullOrWhiteSpace(folderBox.Text))
        {
            MessageBox.Show("Choose a download folder in Settings.", "Folder required", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        Directory.CreateDirectory(folderBox.Text);

        downloadCts = new CancellationTokenSource();
        cancelButton.Enabled = true;
        channelQueueDownloadButton.Enabled = false;
        var quality = GetDefaultQualityChoice();
        string? cookieFile = null;
        var completed = 0;
        try
        {
            var cookieSnapshot = await ExportYouTubeCookiesAsync(downloadCts.Token);
            cookieFile = cookieSnapshot.Path;
            for (var i = 0; i < ready.Count; i++)
            {
                downloadCts.Token.ThrowIfCancellationRequested();
                var item = ready[i];
                item.Status = $"Downloading {i + 1}/{ready.Count}";
                RefreshChannelQueueCards();
                SetDownloadsHero(item.Title, item.ThumbnailUrl, $"Channel selection  •  {(quality.BestAvailable ? "Best available" : quality.Height + "p")}  •  Original/default audio");
                SetProgress(0, "0%");
                SetStatus($"Downloading {i + 1}/{ready.Count}…");
                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable);
                var exit = await RunStreamingAsync(args, downloadCts.Token);
                if (exit == 0)
                {
                    completed++;
                    item.Status = "Completed";
                    item.Meta = "Saved to " + folderBox.Text;
                }
                else
                {
                    item.Status = "Failed";
                    AppendLog("Channel queue item failed: " + item.Title + " • exit=" + exit);
                }
                RefreshChannelQueueCards();
            }
            SetProgress(100, "100%");
            SetStatus($"Channel batch completed • {completed}/{ready.Count}");
            System.Media.SystemSounds.Asterisk.Play();
        }
        catch (OperationCanceledException)
        {
            SetStatus("Channel batch cancelled");
            AppendLog("Channel queue batch cancelled.");
        }
        catch (Exception ex)
        {
            SetStatus("Channel batch error");
            AppendLog("Channel queue error: " + ex.Message);
            MessageBox.Show(ex.Message, "Channel downloads", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            DeleteTempCookieFile(cookieFile);
            activeProcess = null;
            downloadCts?.Dispose();
            downloadCts = null;
            cancelButton.Enabled = false;
            downloadButton.Enabled = true;
            UpdateChannelQueueActions();
        }
    }

    private void SetDownloadsHero(string title, string thumbnailUrl, string meta)
    {
        downloadsTitle.Text = string.IsNullOrWhiteSpace(title) ? "Download" : title;
        downloadsMeta.Text = meta;
        var thumb = string.IsNullOrWhiteSpace(thumbnailUrl) ? string.Empty : thumbnailUrl;
        if (string.IsNullOrWhiteSpace(thumb))
        {
            downloadsThumbnail.ImageLocation = null;
            downloadsThumbnail.Image = null;
            return;
        }
        if (!string.Equals(downloadsThumbnail.ImageLocation, thumb, StringComparison.Ordinal))
        {
            downloadsThumbnail.ImageLocation = thumb;
            try { downloadsThumbnail.LoadAsync(); } catch { }
        }
    }

    private static string ThumbnailFromYouTubeUrl(string url)
    {
        try
        {
            if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) return string.Empty;
            string? id = null;
            if (uri.Host.Equals("youtu.be", StringComparison.OrdinalIgnoreCase)) id = uri.AbsolutePath.Trim('/');
            else
            {
                foreach (var part in uri.Query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))
                {
                    var pieces = part.Split('=', 2);
                    if (pieces.Length == 2 && pieces[0].Equals("v", StringComparison.OrdinalIgnoreCase)) { id = Uri.UnescapeDataString(pieces[1]); break; }
                }
            }
            return string.IsNullOrWhiteSpace(id) ? string.Empty : "https://i.ytimg.com/vi/" + id + "/hqdefault.jpg";
        }
        catch { return string.Empty; }
    }

'''
if anchor not in s: raise SystemExit('HandleBrowserNavigationAsync anchor not found')
s = s.replace(anchor, channel_methods + anchor, 1)

# ---------- Capture thumbnail from normal video analysis ----------
old = '''            var duration = JsonDouble(root, "duration");\n            var parsedChoices = ParseAudioChoices(root);\n'''
new = '''            var duration = JsonDouble(root, "duration");\n            currentMediaThumbnailUrl = JsonString(root, "thumbnail") ?? ThumbnailFromYouTubeUrl(url);\n            var parsedChoices = ParseAudioChoices(root);\n'''
if old not in s: raise SystemExit('single video thumbnail anchor not found')
s = s.replace(old, new, 1)

# Show thumbnail/title as soon as a normal single download starts.
old = '''        downloadCts = new CancellationTokenSource();\n        SetProgress(0, "0%");\n'''
new = '''        SetDownloadsHero(mediaTitle.Text, currentMediaThumbnailUrl, (qualityBox.SelectedItem ?? "Default quality") + "  •  " + (audioBox.SelectedItem ?? "Original/default"));\n        downloadCts = new CancellationTokenSource();\n        SetProgress(0, "0%");\n'''
if old not in s: raise SystemExit('DownloadAsync hero anchor not found')
s = s.replace(old, new, 1)

# Show a thumbnail for playlist items too (derived from the YouTube video id).
old = '''                var item = playlistItems[itemIndex];\n                row.SubItems[3].Text = $"Downloading {i + 1}/{selectedRows.Count}";\n'''
new = '''                var item = playlistItems[itemIndex];\n                SetDownloadsHero(item.Title, ThumbnailFromYouTubeUrl(item.Url), $"Playlist {i + 1}/{selectedRows.Count}  •  Original/default audio");\n                row.SubItems[3].Text = $"Downloading {i + 1}/{selectedRows.Count}";\n'''
if old not in s: raise SystemExit('playlist hero anchor not found')
s = s.replace(old, new, 1)

# ---------- Add 360p to Default Quality settings ----------
old = '''        defaultQualityBox.Items.AddRange(new object[] { "720p (Recommended)", "1080p Full HD", "Best available" });\n        defaultQualityBox.SelectedIndex = 0;\n'''
new = '''        defaultQualityBox.Items.AddRange(new object[] { "360p", "720p (Recommended)", "1080p Full HD", "Best available" });\n        defaultQualityBox.SelectedIndex = 1;\n'''
if old not in s: raise SystemExit('default quality UI anchor not found')
s = s.replace(old, new, 1)

old = '''            defaultQualityBox.SelectedIndex = 0;\n\n            if (!File.Exists(SettingsPath)) return;\n'''
new = '''            defaultQualityBox.SelectedIndex = 1;\n\n            if (!File.Exists(SettingsPath)) return;\n'''
if old not in s: raise SystemExit('default quality load initial anchor not found')
s = s.replace(old, new, 1)

old = '''            defaultQualityBox.SelectedIndex = data.DefaultQuality switch\n            {\n                "1080p" => 1,\n                "Best" => 2,\n                _ => 0\n            };\n'''
new = '''            defaultQualityBox.SelectedIndex = data.DefaultQuality switch\n            {\n                "360p" => 0,\n                "1080p" => 2,\n                "Best" => 3,\n                _ => 1\n            };\n'''
if old not in s: raise SystemExit('default quality load mapping anchor not found')
s = s.replace(old, new, 1)

old = '''                DefaultQuality = defaultQualityBox.SelectedIndex switch { 1 => "1080p", 2 => "Best", _ => "720p" }\n'''
new = '''                DefaultQuality = defaultQualityBox.SelectedIndex switch { 0 => "360p", 2 => "1080p", 3 => "Best", _ => "720p" }\n'''
if old not in s: raise SystemExit('default quality save mapping anchor not found')
s = s.replace(old, new, 1)

# Update preferred quality selection for 360/720/1080/Best.
pattern = re.compile(r'    private int FindPreferredQualityIndex\(\)\n    \{.*?\n    \}\n\n    private static string CodecFamily', re.S)
replacement = r'''    private int FindPreferredQualityIndex()
    {
        if (qualityChoices.Count == 0) return -1;
        if (defaultQualityBox.SelectedIndex == 3)
        {
            var best = qualityChoices.FindIndex(x => x.BestAvailable);
            if (best >= 0) return best;
        }
        var target = defaultQualityBox.SelectedIndex switch
        {
            0 => 360,
            2 => 1080,
            _ => 720
        };
        var candidates = qualityChoices
            .Select((q, i) => (q, i))
            .Where(x => !x.q.AudioOnly && !x.q.BestAvailable && x.q.Height > 0)
            .OrderBy(x => Math.Abs(x.q.Height - target))
            .ThenByDescending(x => x.q.Height)
            .ToList();
        if (candidates.Count > 0) return candidates[0].i;
        return qualityChoices.FindIndex(x => !x.AudioOnly);
    }

    private static string CodecFamily'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'FindPreferredQualityIndex replacement failed: {n}')
s = s2

# Central default quality helper and playlist default mapping.
pattern = re.compile(r'    private \(int Height, bool BestAvailable\) GetPlaylistQualityChoice\(\)\n    \{.*?\n    \}\n\n    private List<string> BuildPlaylistItemDownloadArgs', re.S)
replacement = r'''    private (int Height, bool BestAvailable) GetDefaultQualityChoice()
    {
        return defaultQualityBox.SelectedIndex switch
        {
            0 => (360, false),
            2 => (1080, false),
            3 => (0, true),
            _ => (720, false)
        };
    }

    private (int Height, bool BestAvailable) GetPlaylistQualityChoice()
    {
        return playlistQualityBox.SelectedIndex switch
        {
            1 => (720, false),
            2 => (1080, false),
            3 => (0, true),
            _ => GetDefaultQualityChoice()
        };
    }

    private List<string> BuildPlaylistItemDownloadArgs'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'GetPlaylistQualityChoice replacement failed: {n}')
s = s2

# Busy state also controls channel batch action.
old = '''        downloadButton.Enabled = !busy;\n        SetStatus(status);\n'''
new = '''        downloadButton.Enabled = !busy;\n        if (busy) channelQueueDownloadButton.Enabled = false;\n        else UpdateChannelQueueActions();\n        SetStatus(status);\n'''
if old not in s: raise SystemExit('SetBusy anchor not found')
s = s.replace(old, new, 1)

# ---------- Preview identity ----------
s = s.replace('PC v1.2 Preview 3', 'PC v1.2 Preview 4')
s = s.replace('Browser UI v1.2 Preview 3', 'Browser UI v1.2 Preview 4')

# ---------- Mutable queue model ----------
record_anchor = '    private sealed record QualityChoice(string Label, int Height, bool AudioOnly, bool BestAvailable, double EstimatedBytes, double Fps, string Codec);\n'
if record_anchor not in s: raise SystemExit('QualityChoice record anchor not found')
queue_model = '''    private sealed class ChannelQueueItem\n    {\n        public string Url { get; set; } = string.Empty;\n        public string Title { get; set; } = string.Empty;\n        public string ThumbnailUrl { get; set; } = string.Empty;\n        public string Status { get; set; } = string.Empty;\n        public string Meta { get; set; } = string.Empty;\n    }\n\n'''
s = s.replace(record_anchor, queue_model + record_anchor, 1)

p.write_text(s, encoding='utf-8')

# Installer identity.
iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview3-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview4-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 4 channel queue + 360p default + download thumbnail UI')
