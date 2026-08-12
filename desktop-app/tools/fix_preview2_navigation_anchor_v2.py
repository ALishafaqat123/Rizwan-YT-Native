from pathlib import Path

p = Path('desktop-app/tools/apply_v120_preview2_playlist_ui_settings.py')
s = p.read_text(encoding='utf-8')

old_block = """old = '''        var url = browser.Source.ToString();\\n        addressBox.Text = url;\\n\\n        if (!IsDownloadableMediaPage(url))\\n'''\nnew = '''        var url = browser.Source.ToString();\\n        addressBox.Text = url;\\n\\n        var playlistUrl = GetPlaylistUrl(url);\\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\\n            await AnalyzePlaylistAsync(playlistUrl);\\n\\n        if (IsPlaylistLandingPage(url))\\n        {\\n            currentMediaUrl = string.Empty;\\n            downloadTray.Visible = false;\\n            ShowView(playlistView);\\n            return;\\n        }\\n\\n        if (!IsDownloadableMediaPage(url))\\n'''"""

new_block = """old = '''        addressBox.Text = url;\\n\\n        if (!IsDownloadableMediaPage(url))\\n'''\nnew = '''        addressBox.Text = url;\\n\\n        var playlistUrl = GetPlaylistUrl(url);\\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\\n            await AnalyzePlaylistAsync(playlistUrl);\\n\\n        if (IsPlaylistLandingPage(url))\\n        {\\n            currentMediaUrl = string.Empty;\\n            downloadTray.Visible = false;\\n            ShowView(playlistView);\\n            return;\\n        }\\n\\n        if (!IsDownloadableMediaPage(url))\\n'''"""

if old_block not in s:
    raise SystemExit('Preview 2 old navigation block still not found')
s = s.replace(old_block, new_block, 1)
p.write_text(s, encoding='utf-8')
print('Corrected Preview 2 navigation anchor for v1.1.1 handler')
