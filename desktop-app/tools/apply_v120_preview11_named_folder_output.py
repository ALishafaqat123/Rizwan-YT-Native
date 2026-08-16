from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 7 correctly creates channel/playlist folders, but CommonArgs(includeOutput:true)
# builds an absolute -o template rooted at folderBox.Text. That absolute output template
# wins over --paths, so the media file can still land in the main download folder.
# Preview 11 fixes only the batch output template; Preview 10 selector code is untouched.

sig = '    private List<string> BuildPlaylistItemDownloadArgs(string url, string? cookieFile, int height, bool bestAvailable, string? outputFolder = null)\n'
start = s.find(sig)
if start < 0:
    raise SystemExit('Preview11 BuildPlaylistItemDownloadArgs signature not found')

next_method = s.find('\n    private ', start + len(sig))
if next_method < 0:
    raise SystemExit('Preview11 next method boundary not found')

method = s[start:next_method]

needle = '        return args;\n'
if needle not in method:
    raise SystemExit('Preview11 return args anchor not found')

fix = r'''        // Force the real yt-dlp output template into the named channel/playlist folder.
        // CommonArgs creates an absolute -o path using folderBox.Text, so --paths alone
        // cannot reliably redirect it. Replace that absolute template directly.
        var targetFolder = string.IsNullOrWhiteSpace(outputFolder) ? folderBox.Text : outputFolder;
        Directory.CreateDirectory(targetFolder);
        var outputIndex = args.FindIndex(a => a.Equals("-o", StringComparison.Ordinal) || a.Equals("--output", StringComparison.Ordinal));
        var outputTemplate = Path.Combine(targetFolder, "%(title).180B [%(id)s].%(ext)s");
        if (outputIndex >= 0 && outputIndex + 1 < args.Count)
        {
            args[outputIndex + 1] = outputTemplate;
        }
        else
        {
            var urlIndex = args.FindLastIndex(a => a.Equals(url, StringComparison.Ordinal));
            if (urlIndex < 0) urlIndex = args.Count;
            args.Insert(urlIndex, "-o");
            args.Insert(urlIndex + 1, outputTemplate);
        }
        AppendLog("Batch output folder: " + targetFolder);
'''

method2 = method.replace(needle, fix + needle, 1)
if method2 == method:
    raise SystemExit('Preview11 output-template injection failed')

s = s[:start] + method2 + s[next_method:]

s = s.replace('Text = "PC v1.2 Preview 10",', 'Text = "PC v1.2 Preview 11",', 1)
s = s.replace('Browser UI v1.2 Preview 10 starting', 'Browser UI v1.2 Preview 11 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview10-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview11-Setup', 1)
iss.write_text(i, encoding='utf-8')

# Simple build-time sanity checks.
check = p.read_text(encoding='utf-8')
if 'var outputTemplate = Path.Combine(targetFolder, "%(title).180B [%(id)s].%(ext)s");' not in check:
    raise SystemExit('Preview11 sanity check failed: named output template missing')
if 'window.__rmsChannelSelectorInstalledV10' not in check:
    raise SystemExit('Preview11 sanity check failed: Preview10 selector missing')

print('Applied PC v1.2 Preview 11 named-folder direct output fix')
