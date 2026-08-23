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
# This patch is intentionally tolerant/idempotent because earlier preview patches
# may slightly alter whitespace or neighboring lines.

# -----------------------------------------------------------------------------
# Hide the browser bottom tray permanently after it is constructed.
# -----------------------------------------------------------------------------
if 'downloadTray.Height = 0;' not in s:
    anchor = '        downloadTray.Controls.Add(tray);\n'
    if anchor not in s:
        raise SystemExit('P19 download tray build anchor not found')
    s = s.replace(
        anchor,
        anchor
        + '        // Preview 19: keep quality/audio controls alive for analysis and queue jobs,\n'
        + '        // but do not show the large bottom tray. The in-page watch button is enough.\n'
        + '        downloadTray.Visible = false;\n'
        + '        downloadTray.Height = 0;\n',
        1,
    )

# Navigation must never re-show the old tray. Be flexible about BringToFront.
nav_pattern = re.compile(
    r'(\s*currentMediaUrl\s*=\s*url;\s*\n)'
    r'\s*downloadTray\.Visible\s*=\s*true;\s*\n'
    r'(?:\s*downloadTray\.BringToFront\(\);\s*\n)?'
)
if nav_pattern.search(s):
    s = nav_pattern.sub(lambda m: m.group(1) + '        downloadTray.Visible = false;\n', s, count=1)
elif 'currentMediaUrl = url;' in s and 'downloadTray.Visible = false;' in s:
    pass
else:
    raise SystemExit('P19 navigation tray anchor not found')

# -----------------------------------------------------------------------------
# Remove the global Downloads toolbar Open folder button; per-file folder action
# is clearer and avoids the clipped/half-visible toolbar control.
# -----------------------------------------------------------------------------
open_toolbar_pattern = re.compile(
    r'\n\s*var\s+openFolder\s*=\s*MakeSmallButton\("Open folder"\);\s*\n'
    r'.*?toolbar\.Controls\.Add\(openFolder,\s*2,\s*0\);\s*\n',
    re.S,
)
s2, n = open_toolbar_pattern.subn('\n', s, count=1)
if n == 1:
    s = s2
elif 'toolbar.Controls.Add(openFolder, 2, 0);' not in s:
    # Already removed or changed by a prior/re-run application.
    pass
else:
    raise SystemExit('P19 toolbar open-folder removal failed')

# Give completed cards enough right-side room for two obvious icons.
s = s.replace('                    var rightWidth = 118;\n', '                    var rightWidth = 168;\n', 1)

# -----------------------------------------------------------------------------
# Completed state: enabled bright check + per-file containing-folder icon.
# Replace the Preview 17 completed branch regardless of minor whitespace changes.
# -----------------------------------------------------------------------------
completed_pattern = re.compile(
    r'\s*if\s*\(IsManagerCompleted\(item\.Status\)\)\s*\{\s*'
    r'var\s+done\s*=\s*MakeCardIconButton\("✓",\s*Accent\);\s*'
    r'done\.Enabled\s*=\s*false;\s*'
    r'card\.Controls\.Add\(done\);\s*'
    r'\}\s*'
    r'(?=else\s+if\s*\(concurrentQueueActive\.Contains\(item\.Id\)\))',
    re.S,
)
completed_replacement = '''                    if (IsManagerCompleted(item.Status))
                    {
                        var done = MakeCardIconButton("✓", Accent);
                        done.Left = width - 64;
                        done.Enabled = true;
                        done.Cursor = Cursors.Default;
                        done.AccessibleName = "Download completed";
                        done.TabStop = false;
                        done.Click += (_, _) => { };
                        card.Controls.Add(done);

                        if (!string.IsNullOrWhiteSpace(item.OutputFolder))
                        {
                            var openDoneFolder = MakeCardIconButton("📂", Color.FromArgb(255, 152, 0));
                            openDoneFolder.Left = width - 118;
                            openDoneFolder.Font = new Font("Segoe UI Emoji", 13F, FontStyle.Regular);
                            openDoneFolder.AccessibleName = "Open containing folder";
                            openDoneFolder.Tag = "OpenFolder";
                            var completedFolder = item.OutputFolder;
                            openDoneFolder.Click += (_, _) => OpenManagerFolder(completedFolder);
                            card.Controls.Add(openDoneFolder);
                        }
                    }
                    '''
if 'openDoneFolder.AccessibleName = "Open containing folder"' not in s:
    s2, n = completed_pattern.subn(completed_replacement, s, count=1)
    if n != 1:
        raise SystemExit(f'P19 completed action anchor not found: {n}')
    s = s2

# Identity / installer.
s = s.replace('Text = "PC v1.2 Preview 18",', 'Text = "PC v1.2 Preview 19",', 1)
s = s.replace(
    'Browser UI v1.2 Preview 18 starting • smooth Pause/Resume + smart paused slots',
    'Browser UI v1.2 Preview 19 starting • clear completed actions + compact watch page',
    1,
)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace(
    'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview18-Setup',
    'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview19-Setup',
    1,
)
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
    'MaxConcurrentDownloads',
]
for marker in required:
    if marker not in check:
        raise SystemExit('P19 sanity check failed: ' + marker)

print('Applied Preview 19: bright completed check + per-file folder icon + hidden large watch tray')
