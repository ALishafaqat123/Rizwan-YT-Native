using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;

namespace RizwanMediaSaverPC;

public sealed class MainForm : Form
{
    private readonly Color Bg = Color.FromArgb(17, 22, 21);
    private readonly Color Card = Color.FromArgb(29, 36, 34);
    private readonly Color Card2 = Color.FromArgb(37, 46, 43);
    private readonly Color Accent = Color.FromArgb(10, 174, 120);
    private readonly Color TextMain = Color.FromArgb(239, 245, 242);
    private readonly Color TextMuted = Color.FromArgb(164, 177, 171);

    private readonly TextBox urlBox = new();
    private readonly ComboBox qualityBox = new();
    private readonly TextBox folderBox = new();
    private readonly CheckBox playlistCheck = new();
    private readonly Label titleValue = new();
    private readonly Label statusLabel = new();
    private readonly Label percentLabel = new();
    private readonly ProgressBar progress = new();
    private readonly TextBox logBox = new();
    private readonly Button downloadButton = new();
    private readonly Button cancelButton = new();
    private Process? activeProcess;
    private CancellationTokenSource? cts;

    private string AppDir => AppContext.BaseDirectory;
    private string ToolsDir => Path.Combine(AppDir, "tools");
    private string YtDlpPath => Path.Combine(ToolsDir, "yt-dlp.exe");
    private string FfmpegPath => Path.Combine(ToolsDir, "ffmpeg.exe");
    private string DenoPath => Path.Combine(ToolsDir, "deno.exe");

    public MainForm()
    {
        Text = "Rizwan Media Saver PC";
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(820, 690);
        Size = new Size(940, 760);
        BackColor = Bg;
        ForeColor = TextMain;
        Font = new Font("Segoe UI", 10F, FontStyle.Regular, GraphicsUnit.Point);
        AutoScaleMode = AutoScaleMode.Dpi;

        BuildUi();
        Shown += (_, _) => OnFirstShown();
        FormClosing += (_, e) =>
        {
            if (activeProcess is { HasExited: false })
            {
                var answer = MessageBox.Show("A download is still running. Exit and cancel it?", "Rizwan Media Saver PC", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (answer != DialogResult.Yes) { e.Cancel = true; return; }
                TryCancelProcess();
            }
        };
    }

    private void BuildUi()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 4,
            BackColor = Bg,
            Padding = new Padding(22),
        };
        root.RowStyles.Add(new RowStyle(SizeType.Absolute, 92));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        Controls.Add(root);

        var header = new Panel { Dock = DockStyle.Fill, BackColor = Bg };
        var appTitle = new Label
        {
            AutoSize = true,
            Text = "Rizwan Media Saver PC",
            ForeColor = TextMain,
            Font = new Font("Segoe UI Semibold", 24F, FontStyle.Bold),
            Location = new Point(0, 4)
        };
        var sub = new Label
        {
            AutoSize = true,
            Text = "Ad-free • Windows desktop • Fast FFmpeg remux",
            ForeColor = TextMuted,
            Font = new Font("Segoe UI", 10.5F),
            Location = new Point(2, 52)
        };
        var version = new Label
        {
            AutoSize = true,
            Text = "PC v1.0.0",
            ForeColor = Accent,
            Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold),
            Anchor = AnchorStyles.Top | AnchorStyles.Right
        };
        header.Controls.Add(appTitle);
        header.Controls.Add(sub);
        header.Controls.Add(version);
        header.Resize += (_, _) => version.Location = new Point(header.ClientSize.Width - version.Width, 16);
        root.Controls.Add(header, 0, 0);

        var inputCard = MakeCard();
        inputCard.Padding = new Padding(18);
        inputCard.Margin = new Padding(0, 0, 0, 14);
        inputCard.AutoSize = true;
        var inputLayout = new TableLayoutPanel { Dock = DockStyle.Top, AutoSize = true, ColumnCount = 4, RowCount = 4 };
        inputLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        inputLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 130));
        inputLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 130));
        inputLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 130));

        var urlLabel = MakeLabel("Video / Playlist link", true);
        inputLayout.Controls.Add(urlLabel, 0, 0);
        inputLayout.SetColumnSpan(urlLabel, 4);

        ConfigureTextBox(urlBox, "Paste YouTube / supported link here...");
        urlBox.Margin = new Padding(0, 8, 8, 12);
        inputLayout.Controls.Add(urlBox, 0, 1);

        var pasteBtn = MakeButton("Paste Link", Card2);
        pasteBtn.Click += (_, _) => PasteClipboard();
        pasteBtn.Margin = new Padding(0, 8, 8, 12);
        inputLayout.Controls.Add(pasteBtn, 1, 1);

        var analyzeBtn = MakeButton("Analyze", Card2);
        analyzeBtn.Click += async (_, _) => await AnalyzeAsync();
        analyzeBtn.Margin = new Padding(0, 8, 8, 12);
        inputLayout.Controls.Add(analyzeBtn, 2, 1);

        var clearBtn = MakeButton("Clear", Card2);
        clearBtn.Click += (_, _) => { urlBox.Clear(); titleValue.Text = "—"; progress.Value = 0; percentLabel.Text = "0%"; };
        clearBtn.Margin = new Padding(0, 8, 0, 12);
        inputLayout.Controls.Add(clearBtn, 3, 1);

        var metaLayout = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 2 };
        metaLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 92));
        metaLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        metaLayout.Controls.Add(MakeLabel("Title", false), 0, 0);
        titleValue.Text = "—";
        titleValue.ForeColor = TextMain;
        titleValue.AutoEllipsis = true;
        titleValue.Dock = DockStyle.Fill;
        titleValue.Padding = new Padding(0, 3, 0, 0);
        metaLayout.Controls.Add(titleValue, 1, 0);
        inputLayout.Controls.Add(metaLayout, 0, 2);
        inputLayout.SetColumnSpan(metaLayout, 4);

        var settings = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 4, Margin = new Padding(0, 14, 0, 0) };
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 170));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 150));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 145));

        qualityBox.DropDownStyle = ComboBoxStyle.DropDownList;
        qualityBox.FlatStyle = FlatStyle.Flat;
        qualityBox.BackColor = Card2;
        qualityBox.ForeColor = TextMain;
        qualityBox.Items.AddRange(new object[] { "360p MP4", "720p HD", "1080p Full HD", "Best available", "Audio M4A" });
        qualityBox.SelectedIndex = 1;
        qualityBox.Dock = DockStyle.Fill;
        qualityBox.Height = 38;
        settings.Controls.Add(qualityBox, 0, 0);

        ConfigureTextBox(folderBox, "Output folder");
        folderBox.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyVideos), "Rizwan Media Saver");
        folderBox.Margin = new Padding(10, 0, 8, 0);
        settings.Controls.Add(folderBox, 1, 0);

        var browseBtn = MakeButton("Choose Folder", Card2);
        browseBtn.Click += (_, _) => ChooseFolder();
        browseBtn.Margin = new Padding(0, 0, 8, 0);
        settings.Controls.Add(browseBtn, 2, 0);

        playlistCheck.Text = "Download playlist";
        playlistCheck.ForeColor = TextMain;
        playlistCheck.AutoSize = true;
        playlistCheck.Dock = DockStyle.Fill;
        playlistCheck.Padding = new Padding(4, 7, 0, 0);
        settings.Controls.Add(playlistCheck, 3, 0);

        inputLayout.Controls.Add(settings, 0, 3);
        inputLayout.SetColumnSpan(settings, 4);
        inputCard.Controls.Add(inputLayout);
        root.Controls.Add(inputCard, 0, 1);

        var actionCard = MakeCard();
        actionCard.Padding = new Padding(18);
        actionCard.Margin = new Padding(0, 0, 0, 14);
        actionCard.Height = 148;
        var action = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 4, RowCount = 3 };
        action.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        action.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 160));
        action.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 140));
        action.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 140));
        action.RowStyles.Add(new RowStyle(SizeType.Absolute, 36));
        action.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
        action.RowStyles.Add(new RowStyle(SizeType.Absolute, 56));

        statusLabel.Text = "Ready";
        statusLabel.ForeColor = TextMain;
        statusLabel.Font = new Font("Segoe UI Semibold", 12F, FontStyle.Bold);
        statusLabel.Dock = DockStyle.Fill;
        action.Controls.Add(statusLabel, 0, 0);
        action.SetColumnSpan(statusLabel, 3);

        percentLabel.Text = "0%";
        percentLabel.TextAlign = ContentAlignment.MiddleRight;
        percentLabel.ForeColor = Accent;
        percentLabel.Font = new Font("Segoe UI Semibold", 12F, FontStyle.Bold);
        percentLabel.Dock = DockStyle.Fill;
        action.Controls.Add(percentLabel, 3, 0);

        progress.Dock = DockStyle.Fill;
        progress.Minimum = 0;
        progress.Maximum = 100;
        progress.Style = ProgressBarStyle.Continuous;
        action.Controls.Add(progress, 0, 1);
        action.SetColumnSpan(progress, 4);

        downloadButton.Text = "Download Now";
        StyleButton(downloadButton, Accent);
        downloadButton.Font = new Font("Segoe UI Semibold", 11F, FontStyle.Bold);
        downloadButton.Click += async (_, _) => await DownloadAsync();
        downloadButton.Margin = new Padding(0, 10, 8, 0);
        action.Controls.Add(downloadButton, 1, 2);

        cancelButton.Text = "Cancel";
        StyleButton(cancelButton, Color.FromArgb(114, 54, 54));
        cancelButton.Enabled = false;
        cancelButton.Click += (_, _) => TryCancelProcess();
        cancelButton.Margin = new Padding(0, 10, 8, 0);
        action.Controls.Add(cancelButton, 2, 2);

        var openBtn = MakeButton("Open Folder", Card2);
        openBtn.Click += (_, _) => OpenFolder();
        openBtn.Margin = new Padding(0, 10, 0, 0);
        action.Controls.Add(openBtn, 3, 2);
        actionCard.Controls.Add(action);
        root.Controls.Add(actionCard, 0, 2);

        var logCard = MakeCard();
        logCard.Padding = new Padding(16);
        logCard.Margin = new Padding(0);
        var logHeader = MakeLabel("Activity", true);
        logHeader.Dock = DockStyle.Top;
        logHeader.Height = 28;
        logCard.Controls.Add(logHeader);

        logBox.Multiline = true;
        logBox.ReadOnly = true;
        logBox.ScrollBars = ScrollBars.Vertical;
        logBox.BackColor = Color.FromArgb(22, 28, 26);
        logBox.ForeColor = Color.FromArgb(198, 211, 205);
        logBox.BorderStyle = BorderStyle.None;
        logBox.Font = new Font("Consolas", 9F);
        logBox.Dock = DockStyle.Fill;
        logBox.Margin = new Padding(0, 10, 0, 0);
        logCard.Controls.Add(logBox);
        logBox.BringToFront();
        root.Controls.Add(logCard, 0, 3);
    }

    private Panel MakeCard() => new() { Dock = DockStyle.Fill, BackColor = Card };

    private Label MakeLabel(string text, bool bold)
    {
        return new Label
        {
            Text = text,
            AutoSize = true,
            ForeColor = bold ? TextMain : TextMuted,
            Font = new Font("Segoe UI", 10F, bold ? FontStyle.Bold : FontStyle.Regular)
        };
    }

    private void ConfigureTextBox(TextBox box, string placeholder)
    {
        box.Dock = DockStyle.Fill;
        box.BackColor = Card2;
        box.ForeColor = TextMain;
        box.BorderStyle = BorderStyle.FixedSingle;
        box.Font = new Font("Segoe UI", 10.5F);
        box.PlaceholderText = placeholder;
    }

    private Button MakeButton(string text, Color color)
    {
        var b = new Button { Text = text, Dock = DockStyle.Fill };
        StyleButton(b, color);
        return b;
    }

    private void StyleButton(Button b, Color color)
    {
        b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderSize = 0;
        b.BackColor = color;
        b.ForeColor = Color.White;
        b.Cursor = Cursors.Hand;
        b.UseVisualStyleBackColor = false;
    }

    private void OnFirstShown()
    {
        PasteClipboard(silent: true);
        var missing = new List<string>();
        if (!File.Exists(YtDlpPath)) missing.Add("yt-dlp.exe");
        if (!File.Exists(FfmpegPath)) missing.Add("ffmpeg.exe");
        if (!File.Exists(DenoPath)) missing.Add("deno.exe");
        if (missing.Count > 0)
        {
            AppendLog("Missing engine files: " + string.Join(", ", missing));
            MessageBox.Show("The installer is missing required engine files. Please reinstall Rizwan Media Saver PC.", "Engine files missing", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        else
        {
            AppendLog("Engine ready: yt-dlp + FFmpeg + Deno");
            AppendLog("Default folder: " + folderBox.Text);
        }
    }

    private void PasteClipboard(bool silent = false)
    {
        try
        {
            if (!Clipboard.ContainsText()) return;
            var text = Clipboard.GetText().Trim();
            if (Uri.TryCreate(text, UriKind.Absolute, out var uri) && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps))
            {
                urlBox.Text = text;
                if (!silent) AppendLog("Link pasted from clipboard.");
            }
            else if (!silent)
            {
                MessageBox.Show("Clipboard does not contain a web link.", "Paste Link", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        }
        catch { }
    }

    private void ChooseFolder()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Choose where downloaded files will be saved",
            UseDescriptionForTitle = true,
            SelectedPath = Directory.Exists(folderBox.Text) ? folderBox.Text : Environment.GetFolderPath(Environment.SpecialFolder.MyVideos)
        };
        if (dialog.ShowDialog(this) == DialogResult.OK) folderBox.Text = dialog.SelectedPath;
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

    private async Task AnalyzeAsync()
    {
        var url = urlBox.Text.Trim();
        if (!ValidateReady(url)) return;

        SetBusy(true, "Analyzing link...");
        titleValue.Text = "Analyzing...";
        try
        {
            var args = CommonArgs(url, includeOutput: false);
            args.Add("--skip-download");
            args.Add("--playlist-items");
            args.Add("1");
            args.Add("--print");
            args.Add("%(title)s");
            var result = await RunCaptureAsync(args, CancellationToken.None);
            var title = result.Output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries).LastOrDefault();
            titleValue.Text = string.IsNullOrWhiteSpace(title) ? "Could not read title" : title.Trim();
            AppendLog("Analyze complete: " + titleValue.Text);
        }
        catch (Exception ex)
        {
            titleValue.Text = "Analyze failed";
            AppendLog("Analyze error: " + ex.Message);
        }
        finally { SetBusy(false, "Ready"); }
    }

    private async Task DownloadAsync()
    {
        var url = urlBox.Text.Trim();
        if (!ValidateReady(url)) return;

        try { Directory.CreateDirectory(folderBox.Text); }
        catch (Exception ex)
        {
            MessageBox.Show("Cannot create output folder:\n" + ex.Message, "Folder error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        cts = new CancellationTokenSource();
        progress.Value = 0;
        percentLabel.Text = "0%";
        SetBusy(true, "Starting download...");
        cancelButton.Enabled = true;
        AppendLog("────────────────────────────────────────");
        AppendLog("Download started • " + qualityBox.SelectedItem);

        try
        {
            var args = BuildDownloadArgs(url);
            var exit = await RunStreamingAsync(args, cts.Token);
            if (exit == 0)
            {
                progress.Value = 100;
                percentLabel.Text = "100%";
                statusLabel.Text = "Completed";
                AppendLog("Completed successfully.");
                System.Media.SystemSounds.Asterisk.Play();
            }
            else
            {
                statusLabel.Text = "Download failed";
                AppendLog("yt-dlp exited with code " + exit);
                MessageBox.Show("Download did not complete. See Activity for details.", "Download failed", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
        catch (OperationCanceledException)
        {
            statusLabel.Text = "Cancelled";
            AppendLog("Download cancelled.");
        }
        catch (Exception ex)
        {
            statusLabel.Text = "Error";
            AppendLog("Error: " + ex.Message);
            MessageBox.Show(ex.Message, "Rizwan Media Saver PC", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            activeProcess = null;
            cts?.Dispose();
            cts = null;
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
            MessageBox.Show("Please paste a valid video link first.", "Link required", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return false;
        }
        if (string.IsNullOrWhiteSpace(folderBox.Text))
        {
            MessageBox.Show("Please choose an output folder.", "Folder required", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return false;
        }
        return true;
    }

    private List<string> BuildDownloadArgs(string url)
    {
        var args = CommonArgs(url, includeOutput: true);
        if (playlistCheck.Checked) args.Add("--yes-playlist"); else args.Add("--no-playlist");

        var format = qualityBox.SelectedIndex switch
        {
            0 => "18/best[height<=360][ext=mp4][vcodec^=avc1][acodec^=mp4a]/best[height<=360][ext=mp4][vcodec!=none][acodec!=none]/bestvideo[height<=360][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
            1 => "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
            2 => "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
            3 => "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            4 => "bestaudio[ext=m4a]/bestaudio",
            _ => "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]"
        };

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
        var output = new StringBuilder();
        if (!process.Start()) throw new InvalidOperationException("Could not start analysis engine.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(token);
        var stderrTask = process.StandardError.ReadToEndAsync(token);
        await process.WaitForExitAsync(token);
        output.Append(await stdoutTask);
        var err = await stderrTask;
        if (process.ExitCode != 0 && !string.IsNullOrWhiteSpace(err)) AppendLog(err.Trim());
        return (process.ExitCode, output.ToString());
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
            statusLabel.Text = "Joining video + audio...";
        else if (clean.Contains("[ExtractAudio]", StringComparison.OrdinalIgnoreCase))
            statusLabel.Text = "Preparing audio...";
        else if (clean.Contains("[download]", StringComparison.OrdinalIgnoreCase))
            statusLabel.Text = "Downloading...";

        var match = Regex.Match(clean, @"(?<!\d)(?<p>\d{1,3}(?:\.\d+)?)%");
        if (match.Success && double.TryParse(match.Groups["p"].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var pct))
        {
            var value = Math.Clamp((int)Math.Round(pct), 0, 100);
            progress.Value = value;
            percentLabel.Text = pct.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture) + "%";
        }

        if (!clean.StartsWith("[download]", StringComparison.OrdinalIgnoreCase) || clean.Contains("Destination", StringComparison.OrdinalIgnoreCase) || clean.Contains("100%"))
            AppendLog(clean);
    }

    private void TryCancelProcess()
    {
        try
        {
            cts?.Cancel();
            if (activeProcess is { HasExited: false }) activeProcess.Kill(entireProcessTree: true);
        }
        catch { }
    }

    private void SetBusy(bool busy, string status)
    {
        if (InvokeRequired) { BeginInvoke(() => SetBusy(busy, status)); return; }
        downloadButton.Enabled = !busy;
        statusLabel.Text = status;
    }

    private void AppendLog(string message)
    {
        if (InvokeRequired) { BeginInvoke(() => AppendLog(message)); return; }
        var line = DateTime.Now.ToString("HH:mm:ss") + "  " + message;
        logBox.AppendText(line + Environment.NewLine);
        logBox.SelectionStart = logBox.TextLength;
        logBox.ScrollToCaret();
    }
}
