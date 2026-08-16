from pathlib import Path

p = Path('desktop-app/tools/apply_v120_preview4_channel_queue_ui.py')
s = p.read_text(encoding='utf-8')
old = "anchor = '    private async Task HandleBrowserNavigationAsync()\\n'"
new = "anchor = '    private async Task HandleBrowserNavigationAsync(string url)\\n'"
if old not in s:
    raise SystemExit('Preview 4 patch navigation anchor marker not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('Corrected Preview 4 navigation handler anchor')
