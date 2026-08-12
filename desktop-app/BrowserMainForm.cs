using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace RizwanMediaSaverPC;

public sealed class BrowserMainForm : Form
{
    private readonly Color WindowBg = Color.FromArgb(17, 18, 24);
    private readonly Color SidebarBg = Color.FromArgb(24, 25, 33);
    private readonly Color Surface = Color.FromArgb(31, 33, 42);
    private readonly Color Surface2 = Color.FromArgb(40, 42, 53);
    private readonly Color Border = Color.FromArgb(57, 60, 73);
    private readonly Color Accent = Color.FromArgb(31, 201, 132);
    private readonly Color AccentDark = Color.FromArgb(25, 164, 108);
    private readonly Color TextMain = Color.FromArgb(245, 246, 249);
    private readonly Color TextMuted = Color.FromArgb(166, 170, 184);

    private readonly WebView2 browser = new();
    private readonly TextBox addressBox = new();
    private readonly ComboBox qualityBox = new();
    private readonly ComboBox audioBox = new();
    private readonly TextBox folderBox = new();
    private readonly Label mediaTitle = new();
    private readonly Label mediaMeta = new();
    private readonly Label statusLabel = new();
    private readonly Label percentLabel = new();
    private readonly ProgressBar progress = new();
    private readonly Label downloadsStatus = new();
    private readonly Label downloadsPercent = new();
    private readonly ProgressBar downloadsProgress = new();
    private readonly TextBox logBox = new();
    private readonly Panel browserView = new();
    private readonly Panel downloadsView = new();
    private readonly Panel settingsView = new();
    private readonly Panel downloadTray = new();
    private readonly Button browserNav = new();
    private readonly Button downloadsNav = new();
    private readonly Button settingsNav = new();
    private readonly Button downloadButton = new();
    private readonly Button cancelButton = new();

    private Process? activeProcess;
    private CancellationTokenSource? downloadCts;
    private CancellationTokenSource? analysisCts;
    private string currentMediaUrl = string.Empty;
    private string lastAnalyzedUrl = string.Empty;
    private readonly List<AudioChoice> audioChoices = new();

    private string AppDir => AppContext.BaseDirectory;
    private string ToolsDir => Path.Combine(AppDir, "tools");
    private string YtDlpPath => Path.Combine(ToolsDir, "yt-dlp.exe");
    private string FfmpegPath => Path.Combine(ToolsDir, "ffmpeg.exe");
    private string DenoPath => Path.Combine(ToolsDir, "deno.exe");
    private string DefaultFolder => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyVideos), "Rizwan Media Saver");
    private string SettingsPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Rizwan Media Saver PC", "settings.txt");

    public BrowserMainForm()
    {
        Text = "Rizwan Media Saver PC";
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(1000, 680);
        Size = new Size(1320, 820);
        BackColor = WindowBg;
        ForeColor = TextMain;
        Font = new Font("Segoe UI", 10F, FontStyle.Regular, GraphicsUnit.Point);
        AutoScaleMode = AutoScaleMode.Dpi;
        DoubleBuffered = true;

        BuildUi();
        LoadSettings();
        Shown += async (_, _) => await OnFirstShownAsync();
        FormClosing += (_, e) =>
        {
            if (activeProcess is { HasExited: false })
            {
                var answer = MessageBox.Show("A download is still running. Exit and cancel it?", "Rizwan Media Saver PC", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (answer != DialogResult.Yes) { e.Cancel = true; return; }
                TryCancelProcess();
            }
            SaveSettings();
        };
    }

    private void BuildUi()
    {
        var shell = new Panel { Dock = DockStyle.Fill, BackColor = WindowBg };
        Controls.Add(shell);

        var sidebar = BuildSidebar();
        shell.Controls.Add(sidebar);

        var main = new Panel { Dock = DockStyle.Fill, BackColor = WindowBg };
        shell.Controls.Add(main);
        main.BringToFront();

        var topBar = BuildTopBar();
        main.Controls.Add(topBar);

        BuildBrowserView();
        BuildDownloadsView();
        BuildSettingsView();
        main.Controls.Add(browserView);
        main.Controls.Add(downloadsView);
        main.Controls.Add(settingsView);
        browserView.BringToFront();
        topBar.BringToFront();

        ShowView(browserView);
    }

    private Panel BuildSidebar()
    {
        var sidebar = new Panel
        {
            Dock = DockStyle.Left,
            Width = 138,
            BackColor = SidebarBg,
            Padding = new Padding(10, 16, 10, 12)
        };

        var logo = new Label
        {
            Text = "RMS",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 18F, FontStyle.Bold),
            TextAlign = ContentAlignment.MiddleCenter,
            Dock = DockStyle.Top,
            Height = 52
        };
        var product = new Label
        {
            Text = "Media Saver",
            ForeColor = TextMuted,
            Font = new Font("Segoe UI", 8.5F),
            TextAlign = ContentAlignment.TopCenter,
            Dock = DockStyle.Top,
            Height = 34
        };

        browserNav.Text = "◉   Browse";
        downloadsNav.Text = "↓   Downloads";
        settingsNav.Text = "⚙   Settings";
        ConfigureSideButton(browserNav);
        ConfigureSideButton(downloadsNav);
        ConfigureSideButton(settingsNav);
        browserNav.Click += (_, _) => ShowView(browserView);
        downloadsNav.Click += (_, _) => ShowView(downloadsView);
        settingsNav.Click += (_, _) => ShowView(settingsView);

        var version = new Label
        {
            Text = "PC v1.1",
            ForeColor = TextMuted,
            Font = new Font("Segoe UI", 8F),
            TextAlign = ContentAlignment.MiddleCenter,
            Dock = DockStyle.Bottom,
            Height = 34
        };

        var navStack = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            Padding = new Padding(0, 12, 0, 0)
        };
        navStack.Controls.Add(browserNav);
        navStack.Controls.Add(downloadsNav);
        navStack.Controls.Add(settingsNav);

        sidebar.Controls.Add(version);
        sidebar.Controls.Add(navStack);
        sidebar.Controls.Add(product);
        sidebar.Controls.Add(logo);
        return sidebar;
    }

    private Panel BuildTopBar()
    {
        var top = new Panel
        {
            Dock = DockStyle.Top,
            Height = 62,
            BackColor = SidebarBg,
            Padding = new Padding(12, 10, 14, 10)
        };

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 6,
            RowCount = 1,
            Margin = Padding.Empty,
            Padding = Padding.Empty
        };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 42));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 42));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 42));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 86));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 42));

        var back = MakeIconButton("←");
        var forward = MakeIconButton("→");
        var refresh = MakeIconButton("↻");
        var paste = MakeSmallButton("Paste");
        var home = MakeIconButton("⌂");
        back.Click += (_, _) => { if (browser.CanGoBack) browser.GoBack(); };
        forward.Click += (_, _) => { if (browser.CanGoForward) browser.GoForward(); };
        refresh.Click += (_, _) => browser.Reload();
        home.Click += (_, _) => Navigate("https://www.youtube.com/");
        paste.Click += (_, _) => PasteAndNavigate();

        addressBox.Dock = DockStyle.Fill;
        addressBox.BackColor = Surface;
        addressBox.ForeColor = TextMain;
        addressBox.BorderStyle = BorderStyle.FixedSingle;
        addressBox.Font = new Font("Segoe UI", 10.5F);
        addressBox.PlaceholderText = "Search YouTube or paste a video link";
        addressBox.Margin = new Padding(6, 1, 8, 1);
        addressBox.KeyDown += (_, e) =>
        {
            if (e.KeyCode == Keys.Enter)
            {
                e.SuppressKeyPress = true;
                NavigateFromAddress();
            }
        };

        layout.Controls.Add(back, 0, 0);
        layout.Controls.Add(forward, 1, 0);
        layout.Controls.Add(refresh, 2, 0);
        layout.Controls.Add(addressBox, 3, 0);
        layout.Controls.Add(paste, 4, 0);
        layout.Controls.Add(home, 5, 0);
        top.Controls.Add(layout);
        return top;
    }

    private void BuildBrowserView()
    {
        browserView.Dock = DockStyle.Fill;
        browserView.BackColor = WindowBg;
        browserView.Padding = Padding.Empty;

        browser.Dock = DockStyle.Fill;
        browser.DefaultBackgroundColor = WindowBg;
        browser.CreationProperties = new CoreWebView2CreationProperties
        {
            UserDataFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Rizwan Media Saver PC", "Browser")
        };
        browser.NavigationStarting += (_, _) => mediaMeta.Text = "Loading…";
        browser.SourceChanged += (_, _) =>
        {
            if (browser.Source != null) addressBox.Text = browser.Source.ToString();
        };
        browser.NavigationCompleted += async (_, _) => await HandleBrowserNavigationAsync();

        BuildDownloadTray();
        browserView.Controls.Add(browser);
        browserView.Controls.Add(downloadTray);
        browser.BringToFront();
        downloadTray.BringToFront();
    }

    private void BuildDownloadTray()
    {
        downloadTray.Dock = DockStyle.Bottom;
        downloadTray.Height = 104;
        downloadTray.BackColor = Surface;
        downloadTray.Padding = new Padding(18, 12, 18, 10);
        downloadTray.Visible = false;

        var tray = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 4,
            RowCount = 2,
            Margin = Padding.Empty,
            Padding = Padding.Empty
        };
        tray.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        tray.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 160));
        tray.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 235));
        tray.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 145));
        tray.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        tray.RowStyles.Add(new RowStyle(SizeType.Absolute, 12));

        var info = new Panel { Dock = DockStyle.Fill, BackColor = Surface, Padding = new Padding(0, 0, 16, 0) };
        mediaTitle.Text = "Video detected";
        mediaTitle.AutoEllipsis = true;
        mediaTitle.ForeColor = TextMain;
        mediaTitle.Font = new Font("Segoe UI Semibold", 11.5F, FontStyle.Bold);
        mediaTitle.Dock = DockStyle.Top;
        mediaTitle.Height = 30;
        mediaMeta.Text = "Reading quality and audio tracks…";
        mediaMeta.AutoEllipsis = true;
        mediaMeta.ForeColor = TextMuted;
        mediaMeta.Font = new Font("Segoe UI", 9F);
        mediaMeta.Dock = DockStyle.Top;
        mediaMeta.Height = 28;
        info.Controls.Add(mediaMeta);
        info.Controls.Add(mediaTitle);
        tray.Controls.Add(info, 0, 0);

        ConfigurePicker(qualityBox);
        qualityBox.Items.AddRange(new object[] { "720p HD", "1080p Full HD", "360p MP4", "Best available", "Audio only" });
        qualityBox.SelectedIndex = 0;
        tray.Controls.Add(MakePickerHost("QUALITY", qualityBox), 1, 0);

        ConfigurePicker(audioBox);
        audioBox.Items.Add("Original / default");
        audioBox.SelectedIndex = 0;
        tray.Controls.Add(MakePickerHost("AUDIO", audioBox), 2, 0);

        downloadButton.Text = "Download  ↓";
        StylePrimaryButton(downloadButton);
        downloadButton.Dock = DockStyle.Fill;
        downloadButton.Margin = new Padding(8, 12, 0, 4);
        downloadButton.Click += async (_, _) => await DownloadAsync();
        tray.Controls.Add(downloadButton, 3, 0);

        progress.Dock = DockStyle.Fill;
        progress.Minimum = 0;
        progress.Maximum = 100;
        progress.Style = ProgressBarStyle.Continuous;
        progress.Margin = new Padding(0, 5, 10, 0);
        tray.Controls.Add(progress, 0, 1);
        tray.SetColumnSpan(progress, 3);

        percentLabel.Text = "";
        percentLabel.ForeColor = Accent;
        percentLabel.Font = new Font("Segoe UI Semibold", 8F, FontStyle.Bold);
        percentLabel.TextAlign = ContentAlignment.MiddleRight;
        percentLabel.Dock = DockStyle.Fill;
        tray.Controls.Add(percentLabel, 3, 1);

        downloadTray.Controls.Add(tray);
    }

    private void BuildDownloadsView()
    {
        downloadsView.Dock = DockStyle.Fill;
        downloadsView.BackColor = WindowBg;
        downloadsView.Padding = new Padding(30, 26, 30, 26);
        downloadsView.Visible = false;

        var title = new Label
        {
            Text = "Downloads",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 24F, FontStyle.Bold),
            Dock = DockStyle.Top,
            Height = 52
        };
        var sub = new Label
        {
            Text = "Current task and activity",
            ForeColor = TextMuted,
            Font = new Font("Segoe UI", 10F),
            Dock = DockStyle.Top,
            Height = 36
        };

        var card = new Panel { Dock = DockStyle.Top, Height = 120, BackColor = Surface, Padding = new Padding(18), Margin = new Padding(0, 12, 0, 12) };
        downloadsStatus.Text = "Ready";
        downloadsStatus.ForeColor = TextMain;
        downloadsStatus.Font = new Font("Segoe UI Semibold", 12F, FontStyle.Bold);
        downloadsStatus.Dock = DockStyle.Top;
        downloadsStatus.Height = 32;
        downloadsPercent.Text = "0%";
        downloadsPercent.ForeColor = Accent;
        downloadsPercent.Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold);
        downloadsPercent.TextAlign = ContentAlignment.MiddleRight;
        downloadsPercent.Dock = DockStyle.Top;
        downloadsPercent.Height = 24;
        downloadsProgress.Dock = DockStyle.Top;
        downloadsProgress.Height = 14;
        downloadsProgress.Minimum = 0;
        downloadsProgress.Maximum = 100;
        card.Controls.Add(downloadsProgress);
        card.Controls.Add(downloadsPercent);
        card.Controls.Add(downloadsStatus);

        var actions = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 58, FlowDirection = FlowDirection.LeftToRight, Padding = new Padding(0, 10, 0, 0) };
        var openFolder = MakeWideButton("Open download folder");
        openFolder.Click += (_, _) => OpenFolder();
        cancelButton.Text = "Cancel current task";
        ConfigureActionButton(cancelButton, Color.FromArgb(118, 55, 61), 160);
        cancelButton.Enabled = false;
        cancelButton.Click += (_, _) => TryCancelProcess();
        actions.Controls.Add(openFolder);
        actions.Controls.Add(cancelButton);

        var logCard = new Panel { Dock = DockStyle.Fill, BackColor = Surface, Padding = new Padding(16) };
        var logTitle = new Label { Text = "Activity", Dock = DockStyle.Top, Height = 30, ForeColor = TextMain, Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold) };
        logBox.Multiline = true;
        logBox.ReadOnly = true;
        logBox.ScrollBars = ScrollBars.Vertical;
        logBox.BorderStyle = BorderStyle.None;
        logBox.BackColor = Color.FromArgb(25, 27, 35);
        logBox.ForeColor = Color.FromArgb(203, 207, 218);
        logBox.Font = new Font("Consolas", 9F);
        logBox.Dock = DockStyle.Fill;
        logCard.Controls.Add(logBox);
        logCard.Controls.Add(logTitle);
        logBox.BringToFront();

        downloadsView.Controls.Add(logCard);
        downloadsView.Controls.Add(actions);
        downloadsView.Controls.Add(card);
        downloadsView.Controls.Add(sub);
        downloadsView.Controls.Add(title);
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
            Text = "Keep the interface simple. Change only what you need.",
            ForeColor = TextMuted,
            Dock = DockStyle.Top,
            Height = 38
        };

        var card = new Panel { Dock = DockStyle.Top, Height = 152, BackColor = Surface, Padding = new Padding(18) };
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
        var hint = new Label { Text = "Downloads are saved here. Your browser history stays inside this app's local profile.", ForeColor = TextMuted, Dock = DockStyle.Bottom, Height = 30, Font = new Font("Segoe UI", 8.8F) };
        card.Controls.Add(hint);
        card.Controls.Add(row);
        card.Controls.Add(folderLabel);

        settingsView.Controls.Add(card);
        settingsView.Controls.Add(sub);
        settingsView.Controls.Add(title);
    }

    private async Task OnFirstShownAsync()
    {
        var missing = new List<string>();
        if (!File.Exists(YtDlpPath)) missing.Add("yt-dlp.exe");
        if (!File.Exists(FfmpegPath)) missing.Add("ffmpeg.exe");
        if (!File.Exists(DenoPath)) missing.Add("deno.exe");
        if (missing.Count > 0)
        {
            AppendLog("Missing engine files: " + string.Join(", ", missing));
            MessageBox.Show("Required engine files are missing. Please reinstall Rizwan Media Saver PC.", "Engine files missing", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        AppendLog("Engine ready: yt-dlp + FFmpeg + Deno");
        AppendLog("Browser UI v1.1 starting.");
        try
        {
            await browser.EnsureCoreWebView2Async();
            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;
            browser.CoreWebView2.Settings.AreDevToolsEnabled = false;
            browser.CoreWebView2.Settings.AreDefaultContextMenusEnabled = true;
            browser.CoreWebView2.Settings.IsZoomControlEnabled = true;
            browser.CoreWebView2.NewWindowRequested += (_, e) =>
            {
                e.Handled = true;
                Navigate(e.Uri);
            };
            Navigate("https://www.youtube.com/");
        }
        catch (Exception ex)
        {
            AppendLog("WebView2 error: " + ex.Message);
            MessageBox.Show("The embedded browser could not start. Microsoft Edge WebView2 Runtime may be missing or damaged. Update Microsoft Edge and reopen the app.\n\n" + ex.Message, "Browser unavailable", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    private void NavigateFromAddress()
    {
        var text = addressBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(text)) return;
        if (Uri.TryCreate(text, UriKind.Absolute, out var uri) && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps))
        {
            Navigate(uri.ToString());
            return;
        }
        Navigate("https://www.youtube.com/results?search_query=" + Uri.EscapeDataString(text));
    }

    private void Navigate(string url)
    {
        try
        {
            if (browser.CoreWebView2 != null) browser.CoreWebView2.Navigate(url);
            else browser.Source = new Uri(url);
        }
        catch (Exception ex) { AppendLog("Navigation error: " + ex.Message); }
    }

    private void PasteAndNavigate()
    {
        try
        {
            if (!Clipboard.ContainsText()) return;
            var text = Clipboard.GetText().Trim();
            addressBox.Text = text;
            NavigateFromAddress();
        }
        catch { }
    }

    private async Task HandleBrowserNavigationAsync()
    {
        if (browser.Source == null) return;
        var url = browser.Source.ToString();
        addressBox.Text = url;

        if (!IsDownloadableMediaPage(url))
        {
            currentMediaUrl = string.Empty;
            downloadTray.Visible = false;
            return;
        }

        currentMediaUrl = url;
        downloadTray.Visible = true;
        downloadTray.BringToFront();
        mediaTitle.Text = "Video detected";
        mediaMeta.Text = "Reading title, quality and audio tracks…";
        if (!string.Equals(lastAnalyzedUrl, url, StringComparison.Ordinal))
            await AnalyzeMediaAsync(url);
    }

    private static bool IsDownloadableMediaPage(string url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) return false;
        var host = uri.Host.ToLowerInvariant();
        if (host.Contains("youtube.com"))
            return uri.AbsolutePath.Equals("/watch", StringComparison.OrdinalIgnoreCase) || uri.AbsolutePath.StartsWith("/shorts/", StringComparison.OrdinalIgnoreCase);
        if (host.Equals("youtu.be", StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    private async Task AnalyzeMediaAsync(string url)
    {
        analysisCts?.Cancel();
        analysisCts?.Dispose();
        analysisCts = new CancellationTokenSource();
        var token = analysisCts.Token;
        lastAnalyzedUrl = url;
        mediaTitle.Text = "Analyzing video…";
        mediaMeta.Text = "Checking available audio languages";
        audioBox.Enabled = false;

        try
        {
            var args = CommonArgs(url, includeOutput: false);
            args.Add("--no-playlist");
            args.Add("--skip-download");
            args.Add("--dump-single-json");
            var result = await RunCaptureAsync(args, token);
            if (token.IsCancellationRequested) return;
            if (result.ExitCode != 0 || string.IsNullOrWhiteSpace(result.Output)) throw new InvalidOperationException("Could not read video information.");

            using var doc = JsonDocument.Parse(result.Output);
            var root = doc.RootElement;
            var title = JsonString(root, "title") ?? "YouTube video";
            var uploader = JsonString(root, "uploader") ?? JsonString(root, "channel") ?? string.Empty;
            var duration = JsonDouble(root, "duration");
            var parsedChoices = ParseAudioChoices(root);

            mediaTitle.Text = title;
            var parts = new List<string>();
            if (duration > 0) parts.Add(FormatDuration(duration));
            if (!string.IsNullOrWhiteSpace(uploader)) parts.Add(uploader);
            var dubCount = parsedChoices.Count(x => x.Kind == AudioKind.Dubbed);
            if (dubCount > 0) parts.Add(dubCount + " Auto-Dub " + (dubCount == 1 ? "voice" : "voices"));
            mediaMeta.Text = parts.Count == 0 ? "Ready to download" : string.Join("  •  ", parts);

            audioChoices.Clear();
            audioChoices.AddRange(parsedChoices);
            audioBox.Items.Clear();
            foreach (var choice in audioChoices) audioBox.Items.Add(choice.Label);
            if (audioBox.Items.Count == 0)
            {
                audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));
                audioBox.Items.Add("Original / default");
            }
            audioBox.SelectedIndex = 0;
            audioBox.Enabled = true;
            AppendLog("Analyze complete: " + title + (dubCount > 0 ? $" • Auto-Dub tracks={dubCount}" : string.Empty));
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            if (token.IsCancellationRequested) return;
            mediaTitle.Text = "Video ready";
            mediaMeta.Text = "Audio language details unavailable — default audio will be used";
            audioChoices.Clear();
            audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));
            audioBox.Items.Clear();
            audioBox.Items.Add("Original / default");
            audioBox.SelectedIndex = 0;
            audioBox.Enabled = true;
            AppendLog("Analyze note: " + ex.Message);
        }
    }

    private List<AudioChoice> ParseAudioChoices(JsonElement root)
    {
        var candidates = new List<AudioChoice>();
        if (!root.TryGetProperty("formats", out var formats) || formats.ValueKind != JsonValueKind.Array)
            return new List<AudioChoice> { new("Original / default", null, null, AudioKind.Default, 0, 0) };

        foreach (var f in formats.EnumerateArray())
        {
            var vcodec = JsonString(f, "vcodec") ?? string.Empty;
            var acodec = JsonString(f, "acodec") ?? string.Empty;
            if (!vcodec.Equals("none", StringComparison.OrdinalIgnoreCase) || string.IsNullOrWhiteSpace(acodec) || acodec.Equals("none", StringComparison.OrdinalIgnoreCase)) continue;

            var language = JsonString(f, "language");
            var formatId = JsonString(f, "format_id");
            if (string.IsNullOrWhiteSpace(language) || string.IsNullOrWhiteSpace(formatId)) continue;

            var note = string.Join(" ", JsonString(f, "format_note"), JsonString(f, "format"), JsonString(f, "language"));
            var kind = AudioKind.Alternate;
            if (note.Contains("dubbed", StringComparison.OrdinalIgnoreCase)) kind = AudioKind.Dubbed;
            else if (note.Contains("audio description", StringComparison.OrdinalIgnoreCase) || note.Contains("descriptive", StringComparison.OrdinalIgnoreCase)) kind = AudioKind.Description;
            else if (note.Contains("original", StringComparison.OrdinalIgnoreCase)) kind = AudioKind.Original;

            var ext = JsonString(f, "ext") ?? string.Empty;
            var abr = JsonDouble(f, "abr");
            var tbr = JsonDouble(f, "tbr");
            var langPref = JsonDouble(f, "language_preference");
            var score = (ext.Equals("m4a", StringComparison.OrdinalIgnoreCase) ? 5000 : 0)
                        + (acodec.StartsWith("mp4a", StringComparison.OrdinalIgnoreCase) ? 3000 : 0)
                        + Math.Max(abr, tbr);
            candidates.Add(new AudioChoice(string.Empty, formatId, language, kind, score, langPref));
        }

        if (candidates.Count == 0)
            return new List<AudioChoice> { new("Original / default", null, null, AudioKind.Default, 0, 0) };

        var grouped = candidates
            .GroupBy(x => (Language: x.Language ?? string.Empty, x.Kind))
            .Select(g => g.OrderByDescending(x => x.Score).First())
            .ToList();

        var original = grouped
            .Where(x => x.Kind is AudioKind.Original or AudioKind.Alternate)
            .OrderByDescending(x => x.Kind == AudioKind.Original)
            .ThenByDescending(x => x.LanguagePreference)
            .ThenByDescending(x => x.Score)
            .FirstOrDefault();

        var final = new List<AudioChoice>();
        if (original != null)
        {
            final.Add(original with { Label = "Original — " + FriendlyLanguage(original.Language) });
        }
        else
        {
            final.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));
        }

        foreach (var item in grouped
                     .Where(x => original == null || x.FormatId != original.FormatId)
                     .OrderBy(x => x.Kind == AudioKind.Dubbed ? 0 : x.Kind == AudioKind.Description ? 2 : 1)
                     .ThenBy(x => FriendlyLanguage(x.Language)))
        {
            var prefix = item.Kind switch
            {
                AudioKind.Dubbed => "Auto Dub",
                AudioKind.Description => "Audio Description",
                _ => "Alternate"
            };
            final.Add(item with { Label = prefix + " — " + FriendlyLanguage(item.Language) });
        }
        return final;
    }

    private async Task DownloadAsync()
    {
        var url = !string.IsNullOrWhiteSpace(currentMediaUrl) ? currentMediaUrl : addressBox.Text.Trim();
        if (!ValidateReady(url)) return;
        try { Directory.CreateDirectory(folderBox.Text); }
        catch (Exception ex)
        {
            MessageBox.Show("Cannot create output folder:\n" + ex.Message, "Folder error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        downloadCts = new CancellationTokenSource();
        SetProgress(0, "0%");
        SetBusy(true, "Starting download…");
        cancelButton.Enabled = true;
        AppendLog("────────────────────────────────────────");
        AppendLog("Download started • " + qualityBox.SelectedItem + " • " + (audioBox.SelectedItem ?? "Original"));

        try
        {
            var args = BuildDownloadArgs(url);
            var exit = await RunStreamingAsync(args, downloadCts.Token);
            if (exit == 0)
            {
                SetProgress(100, "100%");
                SetStatus("Completed");
                AppendLog("Completed successfully.");
                System.Media.SystemSounds.Asterisk.Play();
            }
            else
            {
                SetStatus("Download failed");
                AppendLog("yt-dlp exited with code " + exit);
                MessageBox.Show("Download did not complete. Open Downloads to see the activity log.", "Download failed", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
        catch (OperationCanceledException)
        {
            SetStatus("Cancelled");
            AppendLog("Download cancelled.");
        }
        catch (Exception ex)
        {
            SetStatus("Error");
            AppendLog("Error: " + ex.Message);
            MessageBox.Show(ex.Message, "Rizwan Media Saver PC", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            activeProcess = null;
            downloadCts?.Dispose();
            downloadCts = null;
            cancelButton.Enabled = false;
            downloadButton.Enabled = true;
        }
    }

    private bool ValidateReady(string url)
    {
        if (!File.Exists(YtDlpPath) || !File.Exists(FfmpegPath) || !File.Exists(DenoPath))
        {
            MessageBox.Show("Required engine files are missing. Please reinstall the software.", "Engine error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return false;
        }
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
        {
            MessageBox.Show("Open a YouTube video first.", "Video required", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return false;
        }
        if (string.IsNullOrWhiteSpace(folderBox.Text))
        {
            MessageBox.Show("Choose a download folder in Settings.", "Folder required", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return false;
        }
        return true;
    }

    private List<string> BuildDownloadArgs(string url)
    {
        var args = CommonArgs(url, includeOutput: true);
        args.Add("--no-playlist");

        var selectedAudio = audioBox.SelectedIndex >= 0 && audioBox.SelectedIndex < audioChoices.Count ? audioChoices[audioBox.SelectedIndex] : null;
        var audioId = selectedAudio?.FormatId;
        string format;

        if (!string.IsNullOrWhiteSpace(audioId))
        {
            format = qualityBox.SelectedIndex switch
            {
                0 => $"bestvideo[height<=720][ext=mp4][vcodec^=avc1]+{audioId}/bestvideo[height<=720][ext=mp4]+{audioId}",
                1 => $"bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+{audioId}/bestvideo[height<=1080][ext=mp4]+{audioId}",
                2 => $"bestvideo[height<=360][ext=mp4][vcodec^=avc1]+{audioId}/bestvideo[height<=360][ext=mp4]+{audioId}",
                3 => $"bestvideo[ext=mp4]+{audioId}/bestvideo+{audioId}",
                4 => audioId,
                _ => $"bestvideo[height<=720][ext=mp4]+{audioId}"
            };
        }
        else
        {
            format = qualityBox.SelectedIndex switch
            {
                0 => "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
                1 => "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
                2 => "18/best[height<=360][ext=mp4][vcodec^=avc1][acodec^=mp4a]/bestvideo[height<=360][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/best[height<=360]",
                3 => "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                4 => "bestaudio[ext=m4a]/bestaudio",
                _ => "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]"
            };
        }

        args.Add("-f");
        args.Add(format);
        if (qualityBox.SelectedIndex != 4)
        {
            args.Add("--merge-output-format");
            args.Add("mp4");
        }
        return args;
    }

    private List<string> CommonArgs(string url, bool includeOutput)
    {
        var args = new List<string>
        {
            "--newline",
            "--progress",
            "--continue",
            "--no-mtime",
            "--windows-filenames",
            "--concurrent-fragments", "4",
            "--ffmpeg-location", ToolsDir,
            "--js-runtimes", "deno:" + DenoPath,
            "--remote-components", "ejs:github",
            "--force-ipv4"
        };
        if (includeOutput)
        {
            args.Add("-o");
            args.Add(Path.Combine(folderBox.Text, "%(title).180B [%(id)s].%(ext)s"));
        }
        args.Add(url);
        return args;
    }

    private async Task<int> RunStreamingAsync(List<string> args, CancellationToken token)
    {
        var psi = MakeProcessInfo(args);
        using var process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        activeProcess = process;
        process.OutputDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) HandleEngineLine(e.Data!); };
        process.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) HandleEngineLine(e.Data!); };
        if (!process.Start()) throw new InvalidOperationException("Could not start download engine.");
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

    private async Task<(int ExitCode, string Output)> RunCaptureAsync(List<string> args, CancellationToken token)
    {
        var psi = MakeProcessInfo(args);
        using var process = new Process { StartInfo = psi };
        if (!process.Start()) throw new InvalidOperationException("Could not start analysis engine.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(token);
        var stderrTask = process.StandardError.ReadToEndAsync(token);
        await process.WaitForExitAsync(token);
        var output = await stdoutTask;
        var err = await stderrTask;
        if (process.ExitCode != 0 && !string.IsNullOrWhiteSpace(err)) AppendLog(err.Trim());
        return (process.ExitCode, output);
    }

    private ProcessStartInfo MakeProcessInfo(List<string> args)
    {
        var psi = new ProcessStartInfo
        {
            FileName = YtDlpPath,
            WorkingDirectory = AppDir,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        foreach (var arg in args) psi.ArgumentList.Add(arg);
        return psi;
    }

    private void HandleEngineLine(string line)
    {
        if (InvokeRequired) { BeginInvoke(() => HandleEngineLine(line)); return; }
        var clean = Regex.Replace(line, "\\x1B\\[[0-9;]*[A-Za-z]", "").Trim();
        if (string.IsNullOrWhiteSpace(clean)) return;

        if (clean.Contains("[Merger]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Merging formats", StringComparison.OrdinalIgnoreCase))
            SetStatus("Joining video + audio…");
        else if (clean.Contains("[ExtractAudio]", StringComparison.OrdinalIgnoreCase))
            SetStatus("Preparing audio…");
        else if (clean.Contains("[download]", StringComparison.OrdinalIgnoreCase))
            SetStatus("Downloading…");

        var match = Regex.Match(clean, @"(?<!\d)(?<p>\d{1,3}(?:\.\d+)?)%");
        if (match.Success && double.TryParse(match.Groups["p"].Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var pct))
        {
            var value = Math.Clamp((int)Math.Round(pct), 0, 100);
            SetProgress(value, pct.ToString("0.0", CultureInfo.InvariantCulture) + "%");
        }

        if (!clean.StartsWith("[download]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Destination", StringComparison.OrdinalIgnoreCase) || clean.Contains("100%"))
            AppendLog(clean);
    }

    private void SetBusy(bool busy, string status)
    {
        if (InvokeRequired) { BeginInvoke(() => SetBusy(busy, status)); return; }
        downloadButton.Enabled = !busy;
        SetStatus(status);
    }

    private void SetStatus(string status)
    {
        if (InvokeRequired) { BeginInvoke(() => SetStatus(status)); return; }
        statusLabel.Text = status;
        downloadsStatus.Text = status;
        if (downloadTray.Visible) mediaMeta.Text = status;
    }

    private void SetProgress(int value, string text)
    {
        if (InvokeRequired) { BeginInvoke(() => SetProgress(value, text)); return; }
        value = Math.Clamp(value, 0, 100);
        progress.Value = value;
        downloadsProgress.Value = value;
        percentLabel.Text = text;
        downloadsPercent.Text = text;
    }

    private void TryCancelProcess()
    {
        try
        {
            downloadCts?.Cancel();
            if (activeProcess is { HasExited: false }) activeProcess.Kill(entireProcessTree: true);
        }
        catch { }
    }

    private void AppendLog(string message)
    {
        if (InvokeRequired) { BeginInvoke(() => AppendLog(message)); return; }
        var line = DateTime.Now.ToString("HH:mm:ss") + "  " + message;
        logBox.AppendText(line + Environment.NewLine);
        logBox.SelectionStart = logBox.TextLength;
        logBox.ScrollToCaret();
    }

    private void ChooseFolder()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Choose where downloaded files will be saved",
            UseDescriptionForTitle = true,
            SelectedPath = Directory.Exists(folderBox.Text) ? folderBox.Text : Environment.GetFolderPath(Environment.SpecialFolder.MyVideos)
        };
        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            folderBox.Text = dialog.SelectedPath;
            SaveSettings();
        }
    }

    private void OpenFolder()
    {
        try
        {
            Directory.CreateDirectory(folderBox.Text);
            Process.Start(new ProcessStartInfo("explorer.exe", folderBox.Text) { UseShellExecute = true });
        }
        catch (Exception ex) { MessageBox.Show(ex.Message, "Open Folder", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }

    private void LoadSettings()
    {
        folderBox.Text = DefaultFolder;
        try
        {
            if (File.Exists(SettingsPath))
            {
                var saved = File.ReadAllText(SettingsPath).Trim();
                if (!string.IsNullOrWhiteSpace(saved)) folderBox.Text = saved;
            }
        }
        catch { }
    }

    private void SaveSettings()
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath)!);
            File.WriteAllText(SettingsPath, folderBox.Text.Trim());
        }
        catch { }
    }

    private void ShowView(Panel target)
    {
        browserView.Visible = target == browserView;
        downloadsView.Visible = target == downloadsView;
        settingsView.Visible = target == settingsView;
        target.BringToFront();
        UpdateNavStyle(browserNav, target == browserView);
        UpdateNavStyle(downloadsNav, target == downloadsView);
        UpdateNavStyle(settingsNav, target == settingsView);
    }

    private void ConfigureSideButton(Button button)
    {
        button.Width = 116;
        button.Height = 46;
        button.Margin = new Padding(0, 4, 0, 4);
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderSize = 0;
        button.BackColor = SidebarBg;
        button.ForeColor = TextMuted;
        button.TextAlign = ContentAlignment.MiddleLeft;
        button.Padding = new Padding(10, 0, 0, 0);
        button.Cursor = Cursors.Hand;
        button.Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold);
    }

    private void UpdateNavStyle(Button button, bool active)
    {
        button.BackColor = active ? Surface2 : SidebarBg;
        button.ForeColor = active ? TextMain : TextMuted;
        button.FlatAppearance.BorderColor = active ? Accent : SidebarBg;
    }

    private Button MakeIconButton(string text)
    {
        var b = new Button
        {
            Text = text,
            Dock = DockStyle.Fill,
            Margin = new Padding(2),
            FlatStyle = FlatStyle.Flat,
            BackColor = SidebarBg,
            ForeColor = TextMain,
            Font = new Font("Segoe UI Symbol", 13F, FontStyle.Regular),
            Cursor = Cursors.Hand
        };
        b.FlatAppearance.BorderSize = 0;
        b.FlatAppearance.MouseOverBackColor = Surface2;
        return b;
    }

    private Button MakeSmallButton(string text)
    {
        var b = new Button { Text = text, Dock = DockStyle.Fill, FlatStyle = FlatStyle.Flat, BackColor = Surface2, ForeColor = TextMain, Cursor = Cursors.Hand, Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold) };
        b.FlatAppearance.BorderSize = 0;
        b.FlatAppearance.MouseOverBackColor = Border;
        return b;
    }

    private Button MakeWideButton(string text)
    {
        var b = new Button { Text = text };
        ConfigureActionButton(b, Surface2, 170);
        return b;
    }

    private void ConfigureActionButton(Button b, Color color, int width)
    {
        b.Width = width;
        b.Height = 38;
        b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderSize = 0;
        b.BackColor = color;
        b.ForeColor = TextMain;
        b.Cursor = Cursors.Hand;
        b.Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold);
        b.Margin = new Padding(0, 0, 8, 0);
    }

    private void StylePrimaryButton(Button b)
    {
        b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderSize = 0;
        b.BackColor = Accent;
        b.ForeColor = Color.FromArgb(9, 35, 26);
        b.Cursor = Cursors.Hand;
        b.Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold);
        b.FlatAppearance.MouseOverBackColor = AccentDark;
    }

    private void ConfigurePicker(ComboBox box)
    {
        box.Dock = DockStyle.Fill;
        box.DropDownStyle = ComboBoxStyle.DropDownList;
        box.FlatStyle = FlatStyle.Flat;
        box.BackColor = Surface2;
        box.ForeColor = TextMain;
        box.Font = new Font("Segoe UI", 9.2F);
        box.Margin = new Padding(0, 4, 8, 4);
    }

    private Panel MakePickerHost(string label, ComboBox box)
    {
        var p = new Panel { Dock = DockStyle.Fill, BackColor = Surface, Padding = new Padding(4, 0, 4, 0) };
        var l = new Label { Text = label, Dock = DockStyle.Top, Height = 18, ForeColor = TextMuted, Font = new Font("Segoe UI Semibold", 7.5F, FontStyle.Bold) };
        box.Dock = DockStyle.Top;
        box.Height = 34;
        p.Controls.Add(box);
        p.Controls.Add(l);
        return p;
    }

    private static string? JsonString(JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var value)) return null;
        return value.ValueKind == JsonValueKind.String ? value.GetString() : value.ToString();
    }

    private static double JsonDouble(JsonElement element, string name)
    {
        if (!element.TryGetProperty(name, out var value)) return 0;
        if (value.ValueKind == JsonValueKind.Number && value.TryGetDouble(out var n)) return n;
        if (value.ValueKind == JsonValueKind.String && double.TryParse(value.GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var s)) return s;
        return 0;
    }

    private static string FormatDuration(double seconds)
    {
        var span = TimeSpan.FromSeconds(Math.Max(0, seconds));
        return span.TotalHours >= 1 ? $"{(int)span.TotalHours}:{span.Minutes:00}:{span.Seconds:00}" : $"{span.Minutes}:{span.Seconds:00}";
    }

    private static string FriendlyLanguage(string? code)
    {
        if (string.IsNullOrWhiteSpace(code)) return "Unknown";
        try
        {
            var normalized = code.Replace('_', '-');
            var culture = CultureInfo.GetCultureInfo(normalized);
            return culture.EnglishName;
        }
        catch { return code; }
    }

    private enum AudioKind { Default, Original, Dubbed, Alternate, Description }

    private sealed record AudioChoice(string Label, string? FormatId, string? Language, AudioKind Kind, double Score, double LanguagePreference);
}
