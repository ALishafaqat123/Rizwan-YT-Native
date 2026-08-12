from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# ---------- Fields / state ----------
old = '    private readonly Button cancelButton = new();\n'
new = old + '''    private readonly Button playlistNav = new();\n    private readonly Panel playlistView = new();\n    private readonly ListView playlistList = new();\n    private readonly Label playlistStatus = new();\n    private readonly ComboBox playlistQualityBox = new();\n    private readonly Button playlistDownloadButton = new();\n    private readonly CheckBox audioDubToggle = new();\n    private readonly ComboBox qualityDisplayModeBox = new();\n    private readonly ComboBox defaultQualityBox = new();\n'''
if old not in s: raise SystemExit('button field anchor not found')
s = s.replace(old, new, 1)

old = '    private readonly List<QualityChoice> qualityChoices = new();\n'
new = old + '''    private readonly List<PlaylistItem> playlistItems = new();\n    private CancellationTokenSource? playlistAnalysisCts;\n    private string currentPlaylistUrl = string.Empty;\n    private bool loadingSettings;\n'''
if old not in s: raise SystemExit('qualityChoices state anchor not found')
s = s.replace(old, new, 1)

# ---------- Main UI wiring ----------
old = '''        BuildBrowserView();\n        BuildDownloadsView();\n        BuildSettingsView();\n        main.Controls.Add(browserView);\n        main.Controls.Add(downloadsView);\n        main.Controls.Add(settingsView);\n'''
new = '''        BuildBrowserView();\n        BuildDownloadsView();\n        BuildPlaylistView();\n        BuildSettingsView();\n        main.Controls.Add(browserView);\n        main.Controls.Add(downloadsView);\n        main.Controls.Add(playlistView);\n        main.Controls.Add(settingsView);\n'''
if old not in s: raise SystemExit('BuildUi views anchor not found')
s = s.replace(old, new, 1)

# Slightly roomier sidebar.
s = s.replace('            Width = 138,', '            Width = 152,', 1)

old = '''        browserNav.Text = "◉   Browse";\n        downloadsNav.Text = "↓   Downloads";\n        settingsNav.Text = "⚙   Settings";\n        ConfigureSideButton(browserNav);\n        ConfigureSideButton(downloadsNav);\n        ConfigureSideButton(settingsNav);\n        browserNav.Click += (_, _) => ShowView(browserView);\n        downloadsNav.Click += (_, _) => ShowView(downloadsView);\n        settingsNav.Click += (_, _) => ShowView(settingsView);\n'''
new = '''        browserNav.Text = "◉   Browse";\n        playlistNav.Text = "☷   Playlist";\n        downloadsNav.Text = "↓   Downloads";\n        settingsNav.Text = "⚙   Settings";\n        ConfigureSideButton(browserNav);\n        ConfigureSideButton(playlistNav);\n        ConfigureSideButton(downloadsNav);\n        ConfigureSideButton(settingsNav);\n        browserNav.Click += (_, _) => ShowView(browserView);\n        playlistNav.Click += (_, _) => ShowView(playlistView);\n        downloadsNav.Click += (_, _) => ShowView(downloadsView);\n        settingsNav.Click += (_, _) => ShowView(settingsView);\n'''
if old not in s: raise SystemExit('sidebar nav anchor not found')
s = s.replace(old, new, 1)

old = '''        navStack.Controls.Add(browserNav);\n        navStack.Controls.Add(downloadsNav);\n        navStack.Controls.Add(settingsNav);\n'''
new = '''        navStack.Controls.Add(browserNav);\n        navStack.Controls.Add(playlistNav);\n        navStack.Controls.Add(downloadsNav);\n        navStack.Controls.Add(settingsNav);\n'''
if old not in s: raise SystemExit('nav stack anchor not found')
s = s.replace(old, new, 1)

# Give download tray a little more breathing room.
s = s.replace('        downloadTray.Height = 104;', '        downloadTray.Height = 112;', 1)

# ---------- Playlist page + upgraded settings page ----------
pattern = re.compile(r'    private void BuildSettingsView\(\)\n    \{.*?\n    \}\n\n    private async Task OnFirstShownAsync', re.S)
replacement = r'''    private void BuildPlaylistView()
    {
        playlistView.Dock = DockStyle.Fill;
        playlistView.BackColor = WindowBg;
        playlistView.Padding = new Padding(30, 26, 30, 26);
        playlistView.Visible = false;

        var title = new Label
        {
            Text = "Playlist",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 24F, FontStyle.Bold),
            Dock = DockStyle.Top,
            Height = 50
        };
        var sub = new Label
        {
            Text = "Open a YouTube playlist, tick the videos you want, then download them as a batch.",
            ForeColor = TextMuted,
            Dock = DockStyle.Top,
            Height = 34
        };

        var toolbar = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 56,
            ColumnCount = 5,
            Padding = new Padding(0, 8, 0, 8)
        };
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 90));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 90));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 180));

        playlistStatus.Text = "No playlist loaded";
        playlistStatus.ForeColor = TextMuted;
        playlistStatus.Dock = DockStyle.Fill;
        playlistStatus.TextAlign = ContentAlignment.MiddleLeft;

        ConfigurePicker(playlistQualityBox);
        playlistQualityBox.Items.AddRange(new object[] { "Default quality", "720p", "1080p", "Best available" });
        playlistQualityBox.SelectedIndex = 0;

        var selectAll = MakeSmallButton("Select all");
        var clear = MakeSmallButton("Clear");
        selectAll.Margin = new Padding(4);
        clear.Margin = new Padding(4);
        selectAll.Click += (_, _) =>
        {
            foreach (ListViewItem item in playlistList.Items) item.Checked = true;
            UpdatePlaylistSelectionStatus();
        };
        clear.Click += (_, _) =>
        {
            foreach (ListViewItem item in playlistList.Items) item.Checked = false;
            UpdatePlaylistSelectionStatus();
        };

        playlistDownloadButton.Text = "Download selected  ↓";
        StylePrimaryButton(playlistDownloadButton);
        playlistDownloadButton.Dock = DockStyle.Fill;
        playlistDownloadButton.Margin = new Padding(8, 4, 0, 4);
        playlistDownloadButton.Enabled = false;
        playlistDownloadButton.Click += async (_, _) => await DownloadSelectedPlaylistAsync();

        toolbar.Controls.Add(playlistStatus, 0, 0);
        toolbar.Controls.Add(playlistQualityBox, 1, 0);
        toolbar.Controls.Add(selectAll, 2, 0);
        toolbar.Controls.Add(clear, 3, 0);
        toolbar.Controls.Add(playlistDownloadButton, 4, 0);

        playlistList.Dock = DockStyle.Fill;
        playlistList.BackColor = Surface;
        playlistList.ForeColor = TextMain;
        playlistList.BorderStyle = BorderStyle.None;
        playlistList.View = View.Details;
        playlistList.FullRowSelect = true;
        playlistList.CheckBoxes = true;
        playlistList.HideSelection = false;
        playlistList.Font = new Font("Segoe UI", 9.5F);
        playlistList.Columns.Add("#", 58);
        playlistList.Columns.Add("Title", 650);
        playlistList.Columns.Add("Duration", 95);
        playlistList.Columns.Add("Status", 150);
        playlistList.ItemChecked += (_, _) => BeginInvoke(UpdatePlaylistSelectionStatus);

        var hint = new Label
        {
            Text = "Preview 2: playlist batches use Original/default audio for reliability. Audio Dub remains available for normal single-video downloads when enabled in Settings.",
            ForeColor = TextMuted,
            Dock = DockStyle.Bottom,
            Height = 34,
            Font = new Font("Segoe UI", 8.7F)
        };

        playlistView.Controls.Add(playlistList);
        playlistView.Controls.Add(hint);
        playlistView.Controls.Add(toolbar);
        playlistView.Controls.Add(sub);
        playlistView.Controls.Add(title);
        playlistList.BringToFront();
    }

    private void BuildSettingsView()
    {
        settingsView.Dock = DockStyle.Fill;
        settingsView.BackColor = WindowBg;
        settingsView.Padding = new Padding(30, 26, 30, 26);
        settingsView.Visible = false;

        var title = new Label
        {
            Text = "Settings",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 24F, FontStyle.Bold),
            Dock = DockStyle.Top,
            Height = 56
        };
        var sub = new Label
        {
            Text = "Simple defaults first. Advanced choices stay optional.",
            ForeColor = TextMuted,
            Dock = DockStyle.Top,
            Height = 36
        };

        var preferences = new Panel { Dock = DockStyle.Top, Height = 214, BackColor = Surface, Padding = new Padding(18) };
        var prefTitle = new Label { Text = "Download preferences", ForeColor = TextMain, Font = new Font("Segoe UI Semibold", 11F, FontStyle.Bold), Dock = DockStyle.Top, Height = 30 };
        var prefGrid = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 3, Padding = new Padding(0, 8, 0, 0) };
        prefGrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 55));
        prefGrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 45));
        for (var r = 0; r < 3; r++) prefGrid.RowStyles.Add(new RowStyle(SizeType.Percent, 33.33F));

        var dubLabel = new Label { Text = "Audio Dub tracks", ForeColor = TextMain, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
        audioDubToggle.Text = "Enable dubbed / alternate voices";
        audioDubToggle.ForeColor = TextMain;
        audioDubToggle.Dock = DockStyle.Fill;
        audioDubToggle.AutoSize = true;
        audioDubToggle.CheckedChanged += async (_, _) =>
        {
            if (loadingSettings) return;
            SaveSettings();
            if (!string.IsNullOrWhiteSpace(currentMediaUrl))
            {
                lastAnalyzedUrl = string.Empty;
                await AnalyzeMediaAsync(currentMediaUrl);
            }
        };

        var displayLabel = new Label { Text = "Quality display", ForeColor = TextMain, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
        ConfigurePicker(qualityDisplayModeBox);
        qualityDisplayModeBox.Items.AddRange(new object[] { "Raw details (current style)", "Simple familiar names" });
        qualityDisplayModeBox.SelectedIndex = 0;
        qualityDisplayModeBox.SelectedIndexChanged += (_, _) =>
        {
            if (loadingSettings) return;
            RefreshQualityLabels();
            SaveSettings();
        };

        var defaultLabel = new Label { Text = "Default quality", ForeColor = TextMain, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
        ConfigurePicker(defaultQualityBox);
        defaultQualityBox.Items.AddRange(new object[] { "720p (Recommended)", "1080p Full HD", "Best available" });
        defaultQualityBox.SelectedIndex = 0;
        defaultQualityBox.SelectedIndexChanged += (_, _) => { if (!loadingSettings) SaveSettings(); };

        prefGrid.Controls.Add(dubLabel, 0, 0);
        prefGrid.Controls.Add(audioDubToggle, 1, 0);
        prefGrid.Controls.Add(displayLabel, 0, 1);
        prefGrid.Controls.Add(qualityDisplayModeBox, 1, 1);
        prefGrid.Controls.Add(defaultLabel, 0, 2);
        prefGrid.Controls.Add(defaultQualityBox, 1, 2);
        preferences.Controls.Add(prefGrid);
        preferences.Controls.Add(prefTitle);

        var gap = new Panel { Dock = DockStyle.Top, Height = 14, BackColor = WindowBg };
        var folderCard = new Panel { Dock = DockStyle.Top, Height = 142, BackColor = Surface, Padding = new Padding(18) };
        var folderLabel = new Label { Text = "Download folder", ForeColor = TextMain, Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold), Dock = DockStyle.Top, Height = 28 };
        var row = new TableLayoutPanel { Dock = DockStyle.Top, Height = 45, ColumnCount = 2, Margin = new Padding(0, 8, 0, 0) };
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 140));
        folderBox.Dock = DockStyle.Fill;
        folderBox.BackColor = Surface2;
        folderBox.ForeColor = TextMain;
        folderBox.BorderStyle = BorderStyle.FixedSingle;
        folderBox.Font = new Font("Segoe UI", 10F);
        var choose = MakeSmallButton("Choose folder");
        choose.Margin = new Padding(8, 0, 0, 0);
        choose.Click += (_, _) => ChooseFolder();
        row.Controls.Add(folderBox, 0, 0);
        row.Controls.Add(choose, 1, 0);
        var hint = new Label { Text = "Audio Dub is OFF by default. Raw quality display remains the default in this preview.", ForeColor = TextMuted, Dock = DockStyle.Bottom, Height = 30, Font = new Font("Segoe UI", 8.8F) };
        folderCard.Controls.Add(hint);
        folderCard.Controls.Add(row);
        folderCard.Controls.Add(folderLabel);

        settingsView.Controls.Add(folderCard);
        settingsView.Controls.Add(gap);
        settingsView.Controls.Add(preferences);
        settingsView.Controls.Add(sub);
        settingsView.Controls.Add(title);
    }

    private async Task OnFirstShownAsync'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'BuildSettingsView replacement failed: {n}')
s = s2

# ---------- Playlist detection in browser navigation ----------
old = '''        var url = browser.Source.ToString();\n        addressBox.Text = url;\n\n        if (!IsDownloadableMediaPage(url))\n'''
new = '''        var url = browser.Source.ToString();\n        addressBox.Text = url;\n\n        var playlistUrl = GetPlaylistUrl(url);\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\n            await AnalyzePlaylistAsync(playlistUrl);\n\n        if (IsPlaylistLandingPage(url))\n        {\n            currentMediaUrl = string.Empty;\n            downloadTray.Visible = false;\n            ShowView(playlistView);\n            return;\n        }\n\n        if (!IsDownloadableMediaPage(url))\n'''
if old not in s: raise SystemExit('browser navigation anchor not found')
s = s.replace(old, new, 1)

anchor = '    private static bool IsDownloadableMediaPage(string url)\n'
helpers = r'''    private static string? GetPlaylistUrl(string url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) return null;
        if (!uri.Host.Contains("youtube.com", StringComparison.OrdinalIgnoreCase)) return null;
        var query = System.Web.HttpUtility.ParseQueryString(uri.Query);
        var list = query.Get("list");
        if (string.IsNullOrWhiteSpace(list)) return null;
        return "https://www.youtube.com/playlist?list=" + Uri.EscapeDataString(list);
    }

    private static bool IsPlaylistLandingPage(string url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) return false;
        return uri.Host.Contains("youtube.com", StringComparison.OrdinalIgnoreCase)
            && uri.AbsolutePath.Equals("/playlist", StringComparison.OrdinalIgnoreCase)
            && !string.IsNullOrWhiteSpace(GetPlaylistUrl(url));
    }

'''
# Avoid System.Web dependency by replacing parser immediately with manual query parsing.
helpers = helpers.replace('''        var query = System.Web.HttpUtility.ParseQueryString(uri.Query);\n        var list = query.Get("list");\n''', '''        string? list = null;\n        foreach (var part in uri.Query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))\n        {\n            var pieces = part.Split('=', 2);\n            if (pieces.Length == 2 && pieces[0].Equals("list", StringComparison.OrdinalIgnoreCase))\n            {\n                list = Uri.UnescapeDataString(pieces[1]);\n                break;\n            }\n        }\n''')
if anchor not in s: raise SystemExit('IsDownloadableMediaPage anchor not found')
s = s.replace(anchor, helpers + anchor, 1)

# ---------- Playlist analysis/download methods ----------
anchor = '    private async Task AnalyzeMediaAsync(string url)\n'
playlist_methods = r'''    private async Task AnalyzePlaylistAsync(string playlistUrl)
    {
        playlistAnalysisCts?.Cancel();
        playlistAnalysisCts?.Dispose();
        playlistAnalysisCts = new CancellationTokenSource();
        var token = playlistAnalysisCts.Token;
        currentPlaylistUrl = playlistUrl;
        playlistStatus.Text = "Reading playlist…";
        playlistDownloadButton.Enabled = false;
        playlistItems.Clear();
        playlistList.Items.Clear();

        string? cookieFile = null;
        try
        {
            var cookieSnapshot = await ExportYouTubeCookiesAsync(token);
            cookieFile = cookieSnapshot.Path;
            var args = CommonArgs(playlistUrl, includeOutput: false);
            if (args.Count > 0 && string.Equals(args[^1], playlistUrl, StringComparison.Ordinal)) args.RemoveAt(args.Count - 1);
            args.Add("--flat-playlist");
            args.Add("--skip-download");
            args.Add("--dump-single-json");
            args.Add("--yes-playlist");
            if (!string.IsNullOrWhiteSpace(cookieFile))
            {
                args.Add("--cookies");
                args.Add(cookieFile!);
            }
            args.Add(playlistUrl);

            var result = await RunCaptureDetailedAsync(args, token);
            if (token.IsCancellationRequested) return;
            if (result.ExitCode != 0 || string.IsNullOrWhiteSpace(result.Output))
                throw new InvalidOperationException("Could not read this playlist.");

            using var doc = JsonDocument.Parse(result.Output);
            var root = doc.RootElement;
            var playlistTitle = JsonString(root, "title") ?? "YouTube playlist";
            if (!root.TryGetProperty("entries", out var entries) || entries.ValueKind != JsonValueKind.Array)
                throw new InvalidOperationException("No playlist videos were returned.");

            var index = 0;
            foreach (var entry in entries.EnumerateArray())
            {
                if (index >= 500) break;
                var id = JsonString(entry, "id") ?? string.Empty;
                var title = JsonString(entry, "title") ?? ("Video " + (index + 1));
                var entryUrl = JsonString(entry, "webpage_url") ?? JsonString(entry, "url") ?? string.Empty;
                if (!entryUrl.StartsWith("http", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(id))
                    entryUrl = "https://www.youtube.com/watch?v=" + id;
                if (string.IsNullOrWhiteSpace(entryUrl)) continue;
                var duration = JsonDouble(entry, "duration");
                var item = new PlaylistItem(index + 1, title, entryUrl, duration);
                playlistItems.Add(item);

                var row = new ListViewItem(item.Index.ToString(CultureInfo.InvariantCulture)) { Tag = playlistItems.Count - 1, Checked = true };
                row.SubItems.Add(item.Title);
                row.SubItems.Add(duration > 0 ? FormatDuration(duration) : "—");
                row.SubItems.Add("Ready");
                playlistList.Items.Add(row);
                index++;
            }

            playlistStatus.Text = playlistItems.Count == 0 ? "Playlist is empty" : $"{playlistTitle}  •  {playlistItems.Count} videos";
            playlistDownloadButton.Enabled = playlistItems.Count > 0;
            playlistNav.Text = playlistItems.Count > 0 ? $"☷   Playlist ({playlistItems.Count})" : "☷   Playlist";
            AppendLog($"Playlist analyzed: {playlistTitle} • items={playlistItems.Count}");
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            if (token.IsCancellationRequested) return;
            playlistStatus.Text = "Playlist unavailable";
            playlistDownloadButton.Enabled = false;
            AppendLog("Playlist analysis note: " + ex.Message);
        }
        finally
        {
            DeleteTempCookieFile(cookieFile);
        }
    }

    private void UpdatePlaylistSelectionStatus()
    {
        if (playlistItems.Count == 0) return;
        var selected = playlistList.CheckedItems.Count;
        playlistDownloadButton.Enabled = selected > 0 && downloadCts == null;
        var baseText = playlistStatus.Text;
        var marker = baseText.IndexOf("  •  selected ", StringComparison.Ordinal);
        if (marker >= 0) baseText = baseText[..marker];
        playlistStatus.Text = baseText + $"  •  selected {selected}";
    }

    private async Task DownloadSelectedPlaylistAsync()
    {
        if (downloadCts != null) return;
        var selectedRows = playlistList.CheckedItems.Cast<ListViewItem>().ToList();
        if (selectedRows.Count == 0)
        {
            MessageBox.Show("Select at least one playlist video.", "Playlist", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        if (string.IsNullOrWhiteSpace(folderBox.Text))
        {
            MessageBox.Show("Choose a download folder in Settings.", "Folder required", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        Directory.CreateDirectory(folderBox.Text);

        downloadCts = new CancellationTokenSource();
        cancelButton.Enabled = true;
        playlistDownloadButton.Enabled = false;
        SetProgress(0, "0%");
        SetBusy(true, "Starting playlist batch…");
        AppendLog("────────────────────────────────────────");
        AppendLog($"Playlist batch started • selected={selectedRows.Count} • Original/default audio");

        string? cookieFile = null;
        var completed = 0;
        try
        {
            var cookieSnapshot = await ExportYouTubeCookiesAsync(downloadCts.Token);
            cookieFile = cookieSnapshot.Path;
            var quality = GetPlaylistQualityChoice();

            for (var i = 0; i < selectedRows.Count; i++)
            {
                downloadCts.Token.ThrowIfCancellationRequested();
                var row = selectedRows[i];
                if (row.Tag is not int itemIndex || itemIndex < 0 || itemIndex >= playlistItems.Count) continue;
                var item = playlistItems[itemIndex];
                row.SubItems[3].Text = $"Downloading {i + 1}/{selectedRows.Count}";
                playlistStatus.Text = $"Downloading {i + 1}/{selectedRows.Count}  •  {item.Title}";
                SetProgress(0, "0%");
                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable);
                var exit = await RunStreamingAsync(args, downloadCts.Token);
                if (exit == 0)
                {
                    completed++;
                    row.SubItems[3].Text = "Completed";
                }
                else
                {
                    row.SubItems[3].Text = "Failed";
                    AppendLog($"Playlist item failed: {item.Title} • exit={exit}");
                }
            }

            SetProgress(100, "100%");
            SetStatus("Playlist completed");
            playlistStatus.Text = $"Batch finished  •  {completed}/{selectedRows.Count} completed";
            AppendLog($"Playlist batch finished • completed={completed}/{selectedRows.Count}");
            System.Media.SystemSounds.Asterisk.Play();
        }
        catch (OperationCanceledException)
        {
            SetStatus("Playlist cancelled");
            playlistStatus.Text = $"Batch cancelled  •  {completed}/{selectedRows.Count} completed";
            AppendLog("Playlist batch cancelled.");
        }
        catch (Exception ex)
        {
            SetStatus("Playlist error");
            playlistStatus.Text = "Playlist download error";
            AppendLog("Playlist error: " + ex.Message);
            MessageBox.Show(ex.Message, "Playlist download", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            DeleteTempCookieFile(cookieFile);
            activeProcess = null;
            downloadCts?.Dispose();
            downloadCts = null;
            cancelButton.Enabled = false;
            downloadButton.Enabled = true;
            UpdatePlaylistSelectionStatus();
        }
    }

    private (int Height, bool BestAvailable) GetPlaylistQualityChoice()
    {
        return playlistQualityBox.SelectedIndex switch
        {
            1 => (720, false),
            2 => (1080, false),
            3 => (0, true),
            _ => defaultQualityBox.SelectedIndex switch
            {
                1 => (1080, false),
                2 => (0, true),
                _ => (720, false)
            }
        };
    }

    private List<string> BuildPlaylistItemDownloadArgs(string url, string? cookieFile, int height, bool bestAvailable)
    {
        var args = CommonArgs(url, includeOutput: true);
        var insertAt = args.FindLastIndex(x => string.Equals(x, url, StringComparison.Ordinal));
        if (insertAt < 0) insertAt = args.Count;
        var injected = new List<string> { "--no-playlist" };
        if (!string.IsNullOrWhiteSpace(cookieFile))
        {
            injected.Add("--cookies");
            injected.Add(cookieFile!);
        }
        var cap = bestAvailable ? string.Empty : $"[height<={Math.Max(144, height)}]";
        var format = $"bestvideo{cap}[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo{cap}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{cap}+bestaudio/best{cap}";
        injected.Add("-f");
        injected.Add(format);
        injected.Add("--merge-output-format");
        injected.Add("mp4");
        args.InsertRange(insertAt, injected);
        return args;
    }

'''
if anchor not in s: raise SystemExit('AnalyzeMediaAsync anchor not found')
s = s.replace(anchor, playlist_methods + anchor, 1)

# ---------- Audio Dub setting: OFF means no Rich Audio scan and only original/default choice ----------
s = s.replace('            if (normalDubCount == 0 && normalLanguages <= 1)\n', '            if (audioDubToggle.Checked && normalDubCount == 0 && normalLanguages <= 1)\n', 1)

old = '''            var parsedChoices = ParseAudioChoices(root);\n            var parsedQualities = ParseQualityChoices(root);\n\n            mediaTitle.Text = title;\n'''
new = '''            var parsedChoices = ParseAudioChoices(root);\n            var parsedQualities = ParseQualityChoices(root);\n            if (!audioDubToggle.Checked)\n            {\n                var originalOnly = parsedChoices.FirstOrDefault(x => x.Kind is AudioKind.Original or AudioKind.Alternate or AudioKind.Default);\n                parsedChoices = new List<AudioChoice>\n                {\n                    originalOnly ?? new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0)\n                };\n            }\n\n            mediaTitle.Text = title;\n'''
if old not in s: raise SystemExit('parsed audio/quality anchor not found')
s = s.replace(old, new, 1)

# ---------- Default quality preference ----------
old = '''            var preferredQuality = qualityChoices.FindIndex(x => !x.AudioOnly && !x.BestAvailable && x.Height == 720);\n            if (preferredQuality < 0) preferredQuality = qualityChoices.FindIndex(x => !x.AudioOnly && !x.BestAvailable && x.Height == 1080);\n            if (preferredQuality < 0) preferredQuality = qualityChoices.FindIndex(x => !x.AudioOnly);\n            qualityBox.SelectedIndex = preferredQuality >= 0 ? preferredQuality : 0;\n'''
new = '''            var preferredQuality = FindPreferredQualityIndex();\n            qualityBox.SelectedIndex = preferredQuality >= 0 ? preferredQuality : 0;\n'''
if old not in s: raise SystemExit('preferred quality block not found')
s = s.replace(old, new, 1)

# ---------- Raw/Simple quality labels ----------
pattern = re.compile(r'    private static string QualityLabel\(int height, double fps, string codec, double estimatedBytes\)\n    \{.*?\n    \}\n\n    private static string CodecFamily', re.S)
replacement = r'''    private string QualityLabel(int height, double fps, string codec, double estimatedBytes)
    {
        var parts = new List<string>();
        if (qualityDisplayModeBox.SelectedIndex == 1)
        {
            parts.Add(SimpleQualityName(height));
        }
        else
        {
            parts.Add(height + "p");
            if (height >= 1900) parts.Add("4K");
            else if (height >= 1280) parts.Add("2K");
            else if (height >= 900) parts.Add("Full HD");
            else if (height >= 600) parts.Add("HD");
        }
        if (fps >= 50) parts.Add(((int)Math.Round(fps)) + "fps");
        if (codec == "H.264") parts.Add("Best compatibility");
        else if (!string.IsNullOrWhiteSpace(codec)) parts.Add(codec);
        if (estimatedBytes > 0) parts.Add("≈" + FormatBytes(estimatedBytes));
        return string.Join(" • ", parts);
    }

    private static string SimpleQualityName(int height)
    {
        if (height >= 1900) return "2160p / 4K";
        if (height >= 1250) return "1440p / 2K";
        if (height >= 900) return "1080p Full HD";
        if (height >= 600) return "720p HD";
        if (height >= 400) return "480p";
        if (height >= 300) return "360p";
        if (height >= 190) return "240p";
        return "144p";
    }

    private void RefreshQualityLabels()
    {
        if (qualityChoices.Count == 0) return;
        for (var i = 0; i < qualityChoices.Count; i++)
        {
            var q = qualityChoices[i];
            if (q.AudioOnly || q.BestAvailable) continue;
            var updated = q with { Label = QualityLabel(q.Height, q.Fps, q.Codec, q.EstimatedBytes) };
            qualityChoices[i] = updated;
            if (i < qualityBox.Items.Count) qualityBox.Items[i] = updated.Label;
        }
    }

    private int FindPreferredQualityIndex()
    {
        if (qualityChoices.Count == 0) return -1;
        if (defaultQualityBox.SelectedIndex == 2)
        {
            var best = qualityChoices.FindIndex(x => x.BestAvailable);
            if (best >= 0) return best;
        }
        var target = defaultQualityBox.SelectedIndex == 1 ? 1080 : 720;
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
if n != 1: raise SystemExit(f'QualityLabel replacement failed: {n}')
s = s2

# ---------- Persistent settings: JSON with migration from old folder-only text ----------
pattern = re.compile(r'    private void LoadSettings\(\)\n    \{.*?\n    \}\n\n    private void SaveSettings\(\)\n    \{.*?\n    \}', re.S)
replacement = r'''    private void LoadSettings()
    {
        loadingSettings = true;
        try
        {
            folderBox.Text = DefaultFolder;
            audioDubToggle.Checked = false;
            qualityDisplayModeBox.SelectedIndex = 0;
            defaultQualityBox.SelectedIndex = 0;

            if (!File.Exists(SettingsPath)) return;
            var saved = File.ReadAllText(SettingsPath).Trim();
            if (string.IsNullOrWhiteSpace(saved)) return;
            if (!saved.StartsWith("{", StringComparison.Ordinal))
            {
                // Migration from v1.1.x / Preview 1 where settings.txt contained only the folder path.
                folderBox.Text = saved;
                return;
            }

            var data = JsonSerializer.Deserialize<AppSettingsData>(saved);
            if (data == null) return;
            if (!string.IsNullOrWhiteSpace(data.DownloadFolder)) folderBox.Text = data.DownloadFolder;
            audioDubToggle.Checked = data.AudioDubs;
            qualityDisplayModeBox.SelectedIndex = data.SimpleQualityDisplay ? 1 : 0;
            defaultQualityBox.SelectedIndex = data.DefaultQuality switch
            {
                "1080p" => 1,
                "Best" => 2,
                _ => 0
            };
        }
        catch { }
        finally
        {
            loadingSettings = false;
        }
    }

    private void SaveSettings()
    {
        if (loadingSettings) return;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath)!);
            var data = new AppSettingsData
            {
                DownloadFolder = folderBox.Text.Trim(),
                AudioDubs = audioDubToggle.Checked,
                SimpleQualityDisplay = qualityDisplayModeBox.SelectedIndex == 1,
                DefaultQuality = defaultQualityBox.SelectedIndex switch { 1 => "1080p", 2 => "Best", _ => "720p" }
            };
            File.WriteAllText(SettingsPath, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { }
    }'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'Load/Save settings replacement failed: {n}')
s = s2

# ---------- View switching ----------
old = '''        browserView.Visible = target == browserView;\n        downloadsView.Visible = target == downloadsView;\n        settingsView.Visible = target == settingsView;\n        target.BringToFront();\n        UpdateNavStyle(browserNav, target == browserView);\n        UpdateNavStyle(downloadsNav, target == downloadsView);\n        UpdateNavStyle(settingsNav, target == settingsView);\n'''
new = '''        browserView.Visible = target == browserView;\n        playlistView.Visible = target == playlistView;\n        downloadsView.Visible = target == downloadsView;\n        settingsView.Visible = target == settingsView;\n        target.BringToFront();\n        UpdateNavStyle(browserNav, target == browserView);\n        UpdateNavStyle(playlistNav, target == playlistView);\n        UpdateNavStyle(downloadsNav, target == downloadsView);\n        UpdateNavStyle(settingsNav, target == settingsView);\n'''
if old not in s: raise SystemExit('ShowView anchor not found')
s = s.replace(old, new, 1)

# Preview identity/log.
s = s.replace('Text = "PC v1.2 Preview 1",', 'Text = "PC v1.2 Preview 2",', 1)
s = s.replace('AppendLog("Browser UI v1.2 Preview 1 starting • Smart Quality + v1.1.3 audio/session foundation.");',
              'AppendLog("Browser UI v1.2 Preview 2 starting • Playlist + settings + Smart Quality.");', 1)

# Records/classes near the bottom.
record_anchor = '    private sealed record QualityChoice(string Label, int Height, bool AudioOnly, bool BestAvailable, double EstimatedBytes, double Fps, string Codec);\n'
if record_anchor not in s: raise SystemExit('QualityChoice record anchor not found')
records = '''    private sealed class AppSettingsData\n    {\n        public string DownloadFolder { get; set; } = string.Empty;\n        public bool AudioDubs { get; set; }\n        public bool SimpleQualityDisplay { get; set; }\n        public string DefaultQuality { get; set; } = "720p";\n    }\n\n    private sealed record PlaylistItem(int Index, string Title, string Url, double Duration);\n\n'''
s = s.replace(record_anchor, records + record_anchor, 1)

p.write_text(s, encoding='utf-8')

# Preview 2 installer filename; keep isolated Preview AppId/install folder from Preview 1.
iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview1-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview2-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 2 playlist + UI + settings')
