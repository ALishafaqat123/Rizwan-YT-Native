from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 19
# - Keep Preview 18 smart-slot/flicker behavior intact.
# - Completed cards show a clear, enabled check icon plus a per-file folder icon.
# - Hide the old large bottom download tray on watch pages; the injected small
#   YouTube Download/Add to Queue button is the primary watch-page action.
# - Remove the awkward global Open folder toolbar button from the Downloads page.

# Hide the browser bottom tray permanently after it is constructed.
old = '''        downloadTray.Controls.Add(tray);\n    }\n'''
new = '''        downloadTray.Controls.Add(tray);\n        // Preview 19: keep quality/audio controls alive for analysis and queue jobs,\n        // but do not show the large bottom tray. The in-page watch button is enough.\n        downloadTray.Visible = false;\n        downloadTray.Height = 0;\n    }\n'''
if old not in s:
    raise SystemExit('P19 download tray build anchor not found')
s = s.replace(old, new, 1)

# Navigation must never re-show the old tray.
old = '''        currentMediaUrl = url;\n        downloadTray.Visible = true;\n        downloadTray.BringToFront();\n        mediaTitle.Text = "Video detected";\n'''
new = '''        currentMediaUrl = url;\n        downloadTray.Visible = false;\n        mediaTitle.Text = "Video detected";\n'''
if old not in s:
    raise SystemExit('P19 navigation tray anchor not found')
s = s.replace(old, new, 1)

# Remove the global Downloads toolbar Open folder button; per-file folder actions
# are clearer and avoid the clipped/half-visible control.
pattern = re.compile(r'''\n        var openFolder = MakeSmallButton\("Open folder"\);\n        openFolder\.Width = 110;\n        openFolder\.Height = 32;\n        openFolder\.Anchor = AnchorStyles\.Right;\n        openFolder\.Margin = new Padding\(0, 1, 0, 0\);\n        openFolder\.Click \+= \(_, _\) => OpenFolder\(\);\n        toolbar\.Controls\.Add\(openFolder, 2, 0\);\n''')
s2, n = pattern.subn('\n', s, count=1)
if n != 1:
    raise SystemExit(f'P19 toolbar open-folder removal failed: {n}')
s = s2

# Give completed cards enough right-side room for two obvious icons.
s = s.replace('                    var rightWidth = 118;\n', '                    var rightWidth = 168;\n', 1)

# Completed state: make the check an enabled visual indicator (not disabled/dim),
# and add a folder icon next to it that opens the exact output folder.
old = '''                    if (IsManagerCompleted(item.Status))\n                    {\n                        var done = MakeCardIconButton("✓", Accent);\n                        done.Enabled = false;\n                        card.Controls.Add(done);\n                    }\n'''
new = '''                    if (IsManagerCompleted(item.Status))\n                    {\n                        var done = MakeCardIconButton("✓", Accent);\n                        done.Left = width - 64;\n                        done.Enabled = true;\n                        done.Cursor = Cursors.Default;\n                        done.AccessibleName = "Download completed";\n                        done.TabStop = false;\n                        done.Click += (_, _) => { };\n                        card.Controls.Add(done);\n\n                        if (!string.IsNullOrWhiteSpace(item.OutputFolder))\n                        {\n                            var openDoneFolder = MakeCardIconButton("📂", Color.FromArgb(255, 152, 0));\n                            openDoneFolder.Left = width - 118;\n                            openDoneFolder.Font = new Font("Segoe UI Emoji", 13F, FontStyle.Regular);\n                            openDoneFolder.AccessibleName = "Open containing folder";\n                            openDoneFolder.Tag = "OpenFolder";\n                            var completedFolder = item.OutputFolder;\n                            openDoneFolder.Click += (_, _) => OpenManagerFolder(completedFolder);\n                            card.Controls.Add(openDoneFolder);\n                        }\n                    }\n'''
if old not in s:
    raise SystemExit('P19 completed action anchor not found')
s = s.replace(old, new, 1)

# Identity / installer.
s = s.replace('Text = "PC v1.2 Preview 18",', 'Text = "PC v1.2 Preview 19",', 1)
s = s.replace('Browser UI v1.2 Preview 18 starting • smooth Pause/Resume + smart paused slots',
              'Browser UI v1.2 Preview 19 starting • clear completed actions + compact watch page', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview18-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview19-Setup', 1)
iss.write_text(i, encoding='utf-8')

check = p.read_text(encoding='utf-8')
required = [
    'downloadTray.Height = 0;',
    'openDoneFolder.AccessibleName = "Open containing folder"',
    'MakeCardIconButton("📂"',
    'done.Enabled = true;',
    'MakeCardIconButton("✓", Accent)',
    'concurrentQueueResumeRequested',
    'TryStartWaitingResumes',
    'MakeDownloadTab("Downloading", "Downloading")',
    'window.__rmsWatchDownloadInstalledV15',
    'window.__rmsChannelSelectorInstalledV10',
    'MaxConcurrentDownloads'
]
for marker in required:
    if marker not in check:
        raise SystemExit('P19 sanity check failed: ' + marker)

print('Applied Preview 19: bright completed check + per-file folder icon + hidden large watch tray')
