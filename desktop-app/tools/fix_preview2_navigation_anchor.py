from pathlib import Path

p = Path('desktop-app/tools/apply_v120_preview2_playlist_ui_settings.py')
s = p.read_text(encoding='utf-8')

old = '''old = \"\"\"        var url = browser.Source.ToString();\\n        addressBox.Text = url;\\n\\n        if (!IsDownloadableMediaPage(url))\\n\"\"\"\nnew = \"\"\"        var url = browser.Source.ToString();\\n        addressBox.Text = url;\\n\\n        var playlistUrl = GetPlaylistUrl(url);\\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\\n            await AnalyzePlaylistAsync(playlistUrl);\\n\\n        if (IsPlaylistLandingPage(url))\\n        {\\n            currentMediaUrl = string.Empty;\\n            downloadTray.Visible = false;\\n            ShowView(playlistView);\\n            return;\\n        }\\n\\n        if (!IsDownloadableMediaPage(url))\\n\"\"\"'''

replacement = '''old = \"\"\"        addressBox.Text = url;\\n\\n        if (!IsDownloadableMediaPage(url))\\n\"\"\"\nnew = \"\"\"        addressBox.Text = url;\\n\\n        var playlistUrl = GetPlaylistUrl(url);\\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\\n            await AnalyzePlaylistAsync(playlistUrl);\\n\\n        if (IsPlaylistLandingPage(url))\\n        {\\n            currentMediaUrl = string.Empty;\\n            downloadTray.Visible = false;\\n            ShowView(playlistView);\\n            return;\\n        }\\n\\n        if (!IsDownloadableMediaPage(url))\\n\"\"\"'''

if old not in s:
    raise SystemExit('preview2 navigation source block not found')
s = s.replace(old, replacement, 1)
p.write_text(s, encoding='utf-8')
print('Fixed Preview 2 navigation anchor')
