from pathlib import Path

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

old = '        var audioId = selectedAudio?.FormatId;\n'
new = '''        // Original/default audio must not be locked to a transient format ID.\n        // YouTube can expose one audio format ID during metadata analysis and a\n        // different set during the real download request, which causes\n        // "Requested format is not available". Keep explicit IDs only for\n        // user-selected Auto-Dub / Alternate / Audio Description tracks.\n        var isOriginalAudio = selectedAudio == null\n            || selectedAudio.Kind == AudioKind.Default\n            || selectedAudio.Label.StartsWith("Original", StringComparison.OrdinalIgnoreCase);\n        var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;\n'''
if old not in s:
    raise SystemExit('Hotfix1 audioId anchor not found')
s = s.replace(old, new, 1)

s = s.replace('Text = "PC v1.2 Preview 11",', 'Text = "PC v1.2 Preview 11 Hotfix 1",', 1)
s = s.replace('Browser UI v1.2 Preview 11 starting', 'Browser UI v1.2 Preview 11 Hotfix 1 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview11-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview11-Hotfix1-Setup', 1)
iss.write_text(i, encoding='utf-8')

check = p.read_text(encoding='utf-8')
if 'var audioId = isOriginalAudio ? null : selectedAudio?.FormatId;' not in check:
    raise SystemExit('Hotfix1 sanity check failed')
if 'window.__rmsChannelSelectorInstalledV10' not in check:
    raise SystemExit('Hotfix1 sanity check failed: Preview10 selector missing')
if 'outputTemplate = Path.Combine(targetFolder' not in check:
    raise SystemExit('Hotfix1 sanity check failed: Preview11 folder fix missing')

print('Applied Preview 11 Hotfix 1: original/default audio no longer locks to transient format ID')
