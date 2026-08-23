from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 17 — clean Download Manager UX inspired by familiar desktop downloaders.
# Keep Preview 16 scheduler/engine intact; this patch is primarily presentation.
# - Two primary tabs: Downloading / Downloaded
# - Cleaner cards with one obvious right-side Pause/Resume control
# - Small secondary Cancel control
# - Completed state uses a large check mark
# - Queued items remain visible in Downloading

# -----------------------------------------------------------------------------
# Filters: simplify visible filter model to Downloading / Downloaded while keeping
# internal legacy status helpers available.
# -----------------------------------------------------------------------------
old = '    private string downloadsManagerFilter = "All";\n'
new = '    private string downloadsManagerFilter = "Downloading";\n'
if old not in s:
    raise SystemExit('P17 filter state anchor not found')
s = s.replace(old, new, 1)

# ManagerMatchesFilter — Downloading includes queued/active/paused/interrupted/failed,
# Downloaded is completed only. Failed remains visible in the working list so retry
# can be added later without hiding the item from the user.
pattern = re.compile(r'    private bool ManagerMatchesFilter\(DownloadManagerItem item\)\n    \{.*?\n    \}', re.S)
replacement = r'''    private bool ManagerMatchesFilter(DownloadManagerItem item)
    {
        return downloadsManagerFilter switch
        {
            "Downloaded" => IsManagerCompleted(item.Status),
            "Downloading" => !IsManagerCompleted(item.Status),
            _ => true
        };
    }'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P17 ManagerMatchesFilter replacement failed: {n}')
s = s2

# -----------------------------------------------------------------------------
# Downloads page toolbar: replace busy filter row with a centered two-tab switch
# and a compact Open Folder action. Keep old global buttons hidden, not deleted,
# so existing logic stays harmlessly available.
# -----------------------------------------------------------------------------
pattern = re.compile(r'        var toolbar = new FlowLayoutPanel\n        \{.*?\n        var managerHeader = new TableLayoutPanel', re.S)
replacement = r'''        var toolbar = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 58,
            ColumnCount = 3,
            BackColor = WindowBg,
            Padding = new Padding(0, 8, 0, 8)
        };
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 250));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));

        var tabs = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            BackColor = Surface2,
            Padding = new Padding(4),
            Margin = new Padding(0)
        };

        Button MakeDownloadTab(string text, string filter)
        {
            var b = new Button
            {
                Text = text,
                Width = 116,
                Height = 34,
                FlatStyle = FlatStyle.Flat,
                BackColor = downloadsManagerFilter == filter ? Color.White : Surface2,
                ForeColor = downloadsManagerFilter == filter ? Color.FromArgb(32, 34, 42) : TextMain,
                Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Margin = new Padding(0)
            };
            b.FlatAppearance.BorderSize = 0;
            b.Click += (_, _) =>
            {
                downloadsManagerFilter = filter;
                managerLayoutKey = string.Empty;
                foreach (Control c in tabs.Controls)
                {
                    if (c is not Button tb) continue;
                    var selected = string.Equals(tb.Tag as string, filter, StringComparison.Ordinal);
                    tb.BackColor = selected ? Color.White : Surface2;
                    tb.ForeColor = selected ? Color.FromArgb(32, 34, 42) : TextMain;
                }
                RefreshDownloadManagerCards();
            };
            b.Tag = filter;
            return b;
        }

        tabs.Controls.Add(MakeDownloadTab("Downloading", "Downloading"));
        tabs.Controls.Add(MakeDownloadTab("Downloaded", "Downloaded"));
        toolbar.Controls.Add(tabs, 1, 0);

        var openFolder = MakeSmallButton("Open folder");
        openFolder.Width = 110;
        openFolder.Height = 32;
        openFolder.Anchor = AnchorStyles.Right;
        openFolder.Margin = new Padding(0, 1, 0, 0);
        openFolder.Click += (_, _) => OpenFolder();
        toolbar.Controls.Add(openFolder, 2, 0);

        // Legacy global controls remain instantiated for compatibility but hidden.
        pauseResumeButton.Visible = false;
        cancelButton.Visible = false;
        startQueueButton.Visible = false;

        var managerHeader = new TableLayoutPanel'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P17 toolbar replacement failed: {n}')
s = s2

# Hide heavy summary + hero presentation while preserving their state controls.
# The card list becomes the primary UI, matching the user's reference screenshot.
s = s.replace('        downloadsView.Controls.Add(summaryCard);\n', '        summaryCard.Visible = false;\n        downloadsView.Controls.Add(summaryCard);\n', 1)
s = s.replace('        downloadsView.Controls.Add(hero);\n', '        hero.Visible = false;\n        downloadsView.Controls.Add(hero);\n', 1)

# Make manager header compact and user-facing.
s = s.replace('            Text = "Download queue",', '            Text = "Downloads",', 1)
s = s.replace('            Height = 44,', '            Height = 38,', 1)

# -----------------------------------------------------------------------------
# Card styling: taller clean cards, roomy right action column, accent border via
# a narrow left stripe, and obvious per-item action icons.
# -----------------------------------------------------------------------------
s = s.replace('                        Height = 108,', '                        Height = 112,', 1)
s = s.replace('                    var rightWidth = 220;\n', '                    var rightWidth = 118;\n', 1)

# Add a subtle state stripe to each card after card creation.
old = '''                    var pic = new PictureBox
                    {
'''
new = '''                    var stripe = new Panel
                    {
                        Left = 0,
                        Top = 0,
                        Width = 3,
                        Height = 112,
                        BackColor = IsManagerCompleted(item.Status)
                            ? Accent
                            : (item.Status.Equals("Paused", StringComparison.OrdinalIgnoreCase) ? Color.FromArgb(255, 152, 0) : Color.FromArgb(90, 169, 255))
                    };
                    card.Controls.Add(stripe);

                    var pic = new PictureBox
                    {
'''
if old not in s:
    raise SystemExit('P17 card stripe anchor not found')
s = s.replace(old, new, 1)

# Move status into compact line under title; free right column for the large icon.
s = s.replace('var status = new Label { Left = width - rightWidth + 10, Top = 12, Width = rightWidth - 28, Height = 24, Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleRight, AutoEllipsis = true };',
              'var status = new Label { Left = 154, Top = 58, Width = Math.Max(230, middleWidth), Height = 20, Font = new Font("Segoe UI Semibold", 8.7F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft, AutoEllipsis = true };', 1)

# Progress sits below status/details in a simpler arrangement.
s = s.replace('var detail = new Label { Left = 154, Top = 56, Width = middleWidth, Height = 18, AutoEllipsis = true, ForeColor = TextMuted, Font = new Font("Segoe UI", 8.2F) };',
              'var detail = new Label { Left = 154, Top = 39, Width = middleWidth, Height = 18, AutoEllipsis = true, ForeColor = TextMuted, Font = new Font("Segoe UI", 8.2F) };', 1)
s = s.replace('var bar = new ProgressBar { Left = 154, Top = 82, Width = Math.Max(180, middleWidth - 58), Height = 8, Minimum = 0, Maximum = 100, Style = ProgressBarStyle.Continuous };',
              'var bar = new ProgressBar { Left = 154, Top = 86, Width = Math.Max(180, middleWidth - 58), Height = 7, Minimum = 0, Maximum = 100, Style = ProgressBarStyle.Continuous };', 1)
s = s.replace('var pct = new Label { Left = 154 + Math.Max(180, middleWidth - 54), Top = 76, Width = 54, Height = 20, ForeColor = Accent, Font = new Font("Segoe UI Semibold", 8.2F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleRight };',
              'var pct = new Label { Left = 154 + Math.Max(180, middleWidth - 54), Top = 79, Width = 54, Height = 20, ForeColor = Accent, Font = new Font("Segoe UI Semibold", 8.2F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleRight };', 1)

# Replace Preview 16 small Pause/Cancel text buttons with one very obvious icon
# action plus a small secondary X. Queued shows a neutral queue glyph; completed
# shows a large check; failed shows !.
pattern = re.compile(r'''                    if \(concurrentQueueActive\.Contains\(item\.Id\)\)\n                    \{.*?\n                    \}\n\n                    if \(IsManagerCompleted\(item\.Status\) \|\| IsManagerFailed\(item\.Status\) \|\| item\.Status\.Equals\("Cancelled", StringComparison\.OrdinalIgnoreCase\) \|\| item\.Status\.Equals\("Queued", StringComparison\.OrdinalIgnoreCase\)\)''', re.S)
replacement = r'''                    var actionX = width - 74;
                    var actionY = 26;
                    Button MakeCardIconButton(string text, Color borderColor)
                    {
                        var b = new Button
                        {
                            Text = text,
                            Left = actionX,
                            Top = actionY,
                            Width = 44,
                            Height = 44,
                            FlatStyle = FlatStyle.Flat,
                            BackColor = Surface,
                            ForeColor = borderColor,
                            Font = new Font("Segoe UI Symbol", text == "❚❚" ? 12F : 16F, FontStyle.Bold),
                            Cursor = Cursors.Hand,
                            TabStop = false
                        };
                        b.FlatAppearance.BorderColor = borderColor;
                        b.FlatAppearance.BorderSize = 2;
                        b.FlatAppearance.MouseOverBackColor = Surface2;
                        b.FlatAppearance.MouseDownBackColor = Color.FromArgb(42, 44, 54);
                        return b;
                    }

                    if (IsManagerCompleted(item.Status))
                    {
                        var done = MakeCardIconButton("✓", Accent);
                        done.Enabled = false;
                        card.Controls.Add(done);
                    }
                    else if (concurrentQueueActive.Contains(item.Id))
                    {
                        var paused = concurrentQueuePaused.Contains(item.Id)
                            || item.Status.Equals("Paused", StringComparison.OrdinalIgnoreCase)
                            || item.Status.Equals("Pausing", StringComparison.OrdinalIgnoreCase);
                        var perPause = MakeCardIconButton(paused ? "▶" : "❚❚", Color.FromArgb(255, 152, 0));
                        perPause.AccessibleName = paused ? "Resume this download" : "Pause this download";
                        perPause.Tag = paused ? "Resume" : "Pause";
                        var pauseId = item.Id;
                        perPause.Click += (_, _) => ToggleConcurrentQueuePauseResume(pauseId);
                        card.Controls.Add(perPause);

                        var perCancel = new Button
                        {
                            Text = "×",
                            Left = width - 31,
                            Top = 6,
                            Width = 22,
                            Height = 22,
                            FlatStyle = FlatStyle.Flat,
                            BackColor = Surface,
                            ForeColor = TextMuted,
                            Font = new Font("Segoe UI", 10F, FontStyle.Bold),
                            Cursor = Cursors.Hand,
                            TabStop = false
                        };
                        perCancel.FlatAppearance.BorderSize = 0;
                        var cancelId = item.Id;
                        perCancel.Click += (_, _) => CancelConcurrentQueueItem(cancelId);
                        card.Controls.Add(perCancel);
                    }
                    else if (item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase)
                          || item.Status.Equals("Ready", StringComparison.OrdinalIgnoreCase)
                          || item.Status.Equals("Interrupted", StringComparison.OrdinalIgnoreCase))
                    {
                        var queued = MakeCardIconButton("…", TextMuted);
                        queued.Enabled = false;
                        card.Controls.Add(queued);

                        var perCancel = new Button
                        {
                            Text = "×",
                            Left = width - 31,
                            Top = 6,
                            Width = 22,
                            Height = 22,
                            FlatStyle = FlatStyle.Flat,
                            BackColor = Surface,
                            ForeColor = TextMuted,
                            Font = new Font("Segoe UI", 10F, FontStyle.Bold),
                            Cursor = Cursors.Hand,
                            TabStop = false
                        };
                        perCancel.FlatAppearance.BorderSize = 0;
                        var cancelId = item.Id;
                        perCancel.Click += (_, _) => CancelConcurrentQueueItem(cancelId);
                        card.Controls.Add(perCancel);
                    }
                    else if (IsManagerFailed(item.Status))
                    {
                        var failed = MakeCardIconButton("!", Color.FromArgb(238, 104, 116));
                        failed.Enabled = false;
                        card.Controls.Add(failed);
                    }

                    if (IsManagerCompleted(item.Status) || IsManagerFailed(item.Status) || item.Status.Equals("Cancelled", StringComparison.OrdinalIgnoreCase) || item.Status.Equals("Queued", StringComparison.OrdinalIgnoreCase))'''
s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'P17 card action replacement failed: {n}')
s = s2

# Don't show Remove/Open-folder buttons inside the main card action area; keep the
# visual language clean. Completed items can be opened from folder toolbar for now.
pattern = re.compile(r'''                    if \(IsManagerCompleted\(item\.Status\) \|\| IsManagerFailed\(item\.Status\) \|\| item\.Status\.Equals\("Cancelled", StringComparison\.OrdinalIgnoreCase\) \|\| item\.Status\.Equals\("Queued", StringComparison\.OrdinalIgnoreCase\)\)\n                    \{.*?\n                    \}\n\n                    if \(!string\.IsNullOrWhiteSpace\(item\.OutputFolder\).*?\n                    \{.*?\n                    \}\n''', re.S)
s2, n = pattern.subn(lambda _m: '', s, count=1)
if n != 1:
    raise SystemExit(f'P17 old card secondary actions removal failed: {n}')
s = s2

# Update summary text to match simplified mental model even though summary is hidden.
pattern = re.compile(r'        downloadsSummary\.Text = .*?;\n')
s = pattern.sub('        downloadsSummary.Text = "Downloading 0   •   Downloaded 0";\n', s, count=1)

# Identity / installer.
s = s.replace('Text = "PC v1.2 Preview 16",', 'Text = "PC v1.2 Preview 17",', 1)
s = s.replace('Browser UI v1.2 Preview 16 starting • auto queue + per-card Pause/Resume/Cancel',
              'Browser UI v1.2 Preview 17 starting • clean Downloading/Downloaded UI + icon actions', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview16-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview17-Setup', 1)
iss.write_text(i, encoding='utf-8')

check = p.read_text(encoding='utf-8')
required = [
    '"Downloading" => !IsManagerCompleted(item.Status)',
    'MakeDownloadTab("Downloading", "Downloading")',
    'MakeDownloadTab("Downloaded", "Downloaded")',
    'MakeCardIconButton(paused ? "▶" : "❚❚"',
    'MakeCardIconButton("✓", Accent)',
    'ToggleConcurrentQueuePauseResume(pauseId)',
    'CancelConcurrentQueueItem(cancelId)',
    'window.__rmsWatchDownloadInstalledV15',
    'private void QueueChannelItemForScheduler(ChannelQueueItem item)',
    'MaxConcurrentDownloads'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P17 sanity check failed: ' + marker)

print('Applied Preview 17 clean Downloading/Downloaded UI with prominent per-card icon actions')
