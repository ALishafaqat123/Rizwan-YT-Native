from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# -------- Channel selector V7: resilient to YouTube lazy loading / recycled cards --------
pattern = re.compile(
    r'    private static string ChannelSelectorScript\(\) => """.*?""";\n\n    private async Task EnsureChannelSelectorInjectedAsync',
    re.S,
)
replacement = r'''    private static string ChannelSelectorScript() => """
(() => {
  const install = () => {
    if (window.__rmsChannelSelectorInstalledV7) {
      try { window.__rmsChannelDecorateV7?.(); } catch {}
      return;
    }
    window.__rmsChannelSelectorInstalledV7 = true;

    const isChannelPage = () => {
      const p = location.pathname || '';
      return p.startsWith('/@') || p.startsWith('/channel/') || p.startsWith('/c/') || p.startsWith('/user/');
    };

    const videoIdFromHref = href => {
      try {
        const u = new URL(href, location.origin);
        return u.pathname === '/watch' ? (u.searchParams.get('v') || '') : '';
      } catch { return ''; }
    };

    const canonicalUrl = id => location.origin + '/watch?v=' + encodeURIComponent(id);

    const findCard = (anchor, id) => {
      const preferred = anchor.closest(
        'ytd-rich-item-renderer, ytd-rich-grid-media, ytd-grid-video-renderer, ytd-video-renderer, yt-lockup-view-model, .yt-lockup-view-model-wiz, [class*="GridShelfItem"], [class*="grid-shelf-item"]'
      );
      if (preferred) return preferred;

      let el = anchor.parentElement;
      for (let depth = 0; el && depth < 10; depth++, el = el.parentElement) {
        const r = el.getBoundingClientRect();
        if (r.width < 160 || r.width > 700 || r.height < 120 || r.height > 950) continue;
        const links = Array.from(el.querySelectorAll('a[href*="/watch"]'));
        if (!links.some(a => videoIdFromHref(a.getAttribute('href') || a.href || '') === id)) continue;
        if (el.querySelector('img') && (el.innerText || '').trim().length > 3) return el;
      }
      return null;
    };

    const bestTitleLink = (card, id) => {
      const links = Array.from(card.querySelectorAll('a[href*="/watch"]'))
        .filter(a => videoIdFromHref(a.getAttribute('href') || a.href || '') === id);
      return links.find(a => (a.getAttribute('title') || '').trim().length > 0)
          || links.find(a => (a.textContent || '').trim().length >= 3)
          || links[0] || null;
    };

    const findThumbnail = card => card.querySelector('ytd-thumbnail img, yt-thumbnail-view-model img, img.yt-core-image, img');

    const actionHost = (card, titleLink) => {
      const metadata = card.querySelector(
        'yt-lockup-metadata-view-model, .yt-lockup-metadata-view-model-wiz__metadata, #details, #meta, ytd-video-meta-block, #metadata, [class*="metadata"]'
      );
      if (metadata) return metadata;
      if (titleLink) {
        const h = titleLink.closest('h3, #video-title, #video-title-link');
        if (h?.parentElement) return h.parentElement;
        if (titleLink.parentElement?.parentElement) return titleLink.parentElement.parentElement;
        if (titleLink.parentElement) return titleLink.parentElement;
      }
      return card;
    };

    const makeButton = (card, id, titleLink) => {
      const row = document.createElement('div');
      row.className = 'rms-channel-action-row-v7';
      row.dataset.videoId = id;
      Object.assign(row.style, {
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start', width: '100%',
        boxSizing: 'border-box', marginTop: '8px', marginBottom: '5px', minHeight: '34px',
        position: 'relative', zIndex: '40'
      });

      const button = document.createElement('button');
      button.className = 'rms-channel-select-v7';
      button.dataset.videoId = id;
      button.type = 'button';
      button.textContent = 'Download';
      button.title = 'Select this video for Rizwan Media Saver Downloads';
      Object.assign(button.style, {
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: '86px',
        height: '32px', border: '0', borderRadius: '6px', padding: '6px 14px',
        background: '#ff9800', color: '#ffffff', fontWeight: '700', fontSize: '13px',
        lineHeight: '18px', cursor: 'pointer', fontFamily: 'Roboto, Arial, sans-serif'
      });
      button.addEventListener('mouseenter', () => { if (!button.disabled) button.style.background = '#f57c00'; });
      button.addEventListener('mouseleave', () => { if (!button.disabled) button.style.background = '#ff9800'; });
      button.addEventListener('click', ev => {
        ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation();
        const title = (titleLink?.getAttribute('title') || titleLink?.textContent || 'YouTube video').trim();
        const img = findThumbnail(card);
        const thumbnail = img?.currentSrc || img?.src || '';
        try {
          window.chrome.webview.postMessage({ type: 'rms-channel-select', url: canonicalUrl(id), title, thumbnail });
          button.textContent = '✓ Selected';
          button.disabled = true;
          button.style.background = '#1fc984';
          button.style.color = '#09231a';
          button.style.cursor = 'default';
        } catch {
          button.textContent = 'Select failed';
        }
      }, true);
      row.appendChild(button);
      return row;
    };

    const decorate = () => {
      if (!isChannelPage()) return 0;

      const anchors = Array.from(document.querySelectorAll('a[href*="/watch"]'));
      const seenCards = new Set();
      let found = 0;
      let buttons = 0;

      for (const anchor of anchors) {
        const id = videoIdFromHref(anchor.getAttribute('href') || anchor.href || '');
        if (!id) continue;
        const card = findCard(anchor, id);
        if (!card || seenCards.has(card)) continue;
        seenCards.add(card);
        found++;

        // YouTube virtualizes the grid and recycles card DOM nodes while scrolling.
        // A button that belonged to the old video must be replaced when the card's href changes.
        const oldRows = Array.from(card.querySelectorAll('.rms-channel-action-row-v7'));
        const matching = oldRows.find(r => r.dataset.videoId === id);
        for (const r of oldRows) if (r !== matching) r.remove();

        if (matching) { buttons++; continue; }

        const titleLink = bestTitleLink(card, id);
        const host = actionHost(card, titleLink);
        if (!host) continue;
        host.appendChild(makeButton(card, id, titleLink));
        buttons++;
      }

      try {
        if (found !== window.__rmsLastFoundV7 || buttons !== window.__rmsLastButtonsV7) {
          window.__rmsLastFoundV7 = found;
          window.__rmsLastButtonsV7 = buttons;
          window.chrome.webview.postMessage({ type: 'rms-selector-status', count: buttons, found, path: location.pathname });
        }
      } catch {}
      return buttons;
    };

    window.__rmsChannelDecorateV7 = decorate;
    let timer = 0;
    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(() => { try { decorate(); } catch {} }, 80);
    };

    new MutationObserver(schedule).observe(document.documentElement, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['href', 'src']
    });
    window.addEventListener('scroll', schedule, true);
    window.addEventListener('wheel', schedule, { passive: true, capture: true });
    window.addEventListener('yt-navigate-finish', schedule, true);
    window.addEventListener('yt-page-data-updated', schedule, true);
    window.addEventListener('popstate', schedule, true);
    setInterval(() => { try { decorate(); } catch {} }, 450);
    decorate();
  };
  install();
})();
""";

    private async Task EnsureChannelSelectorInjectedAsync'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1: raise SystemExit(f'Preview7 ChannelSelectorScript replacement failed: {n}')
s = s2

# -------- Folder naming state --------
old = '    private string currentPlaylistUrl = string.Empty;\n'
new = old + '    private string currentPlaylistTitle = string.Empty;\n'
if old not in s: raise SystemExit('Preview7 currentPlaylistUrl anchor not found')
s = s.replace(old, new, 1)

# Remember the real playlist title from yt-dlp analysis.
old = '            var playlistTitle = JsonString(root, "title") ?? "YouTube playlist";\n'
new = old + '            currentPlaylistTitle = playlistTitle;\n'
if old not in s: raise SystemExit('Preview7 playlist title anchor not found')
s = s.replace(old, new, 1)

# ChannelQueueItem keeps the analyzed uploader/channel name.
old = '        public string Meta { get; set; } = string.Empty;\n'
new = old + '        public string ChannelName { get; set; } = string.Empty;\n'
if old not in s: raise SystemExit('Preview7 ChannelQueueItem Meta anchor not found')
s = s.replace(old, new, 1)

old = '                    var uploader = JsonString(root, "uploader") ?? JsonString(root, "channel") ?? string.Empty;\n'
new = old + '                    item.ChannelName = uploader;\n'
# There are multiple uploader anchors; only the queue-analysis occurrence has item in scope.
queue_pos = s.find('private async Task ProcessChannelQueueAnalysisAsync')
if queue_pos < 0: raise SystemExit('Preview7 queue analysis method not found')
uploader_pos = s.find(old, queue_pos)
if uploader_pos < 0: raise SystemExit('Preview7 queue uploader anchor not found')
s = s[:uploader_pos] + new + s[uploader_pos + len(old):]

# Named folder helper. Windows invalid/reserved names are cleaned automatically.
anchor = '    private List<string> BuildPlaylistItemDownloadArgs(string url, string? cookieFile, int height, bool bestAvailable)\n'
helpers = r'''    private static string SanitizeFolderName(string? value, string fallback)
    {
        var name = string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
        foreach (var ch in Path.GetInvalidFileNameChars()) name = name.Replace(ch, '_');
        name = Regex.Replace(name, @"\s+", " ").Trim().TrimEnd('.', ' ');
        if (string.IsNullOrWhiteSpace(name)) name = fallback;
        var reserved = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        };
        if (reserved.Contains(name)) name = "_" + name;
        if (name.Length > 100) name = name[..100].TrimEnd('.', ' ');
        return string.IsNullOrWhiteSpace(name) ? fallback : name;
    }

    private static string BuildNamedSubfolder(string root, string? name, string fallback)
        => Path.Combine(root, SanitizeFolderName(name, fallback));

'''
if anchor not in s: raise SystemExit('Preview7 BuildPlaylistItemDownloadArgs anchor not found')
s = s.replace(anchor, helpers + '    private List<string> BuildPlaylistItemDownloadArgs(string url, string? cookieFile, int height, bool bestAvailable, string? outputFolder = null)\n', 1)

# Let batch callers override the root -P/--paths from CommonArgs with a named subfolder.
old = '        var injected = new List<string> { "--no-playlist" };\n'
new = '''        var injected = new List<string> { "--no-playlist" };\n        if (!string.IsNullOrWhiteSpace(outputFolder))\n        {\n            Directory.CreateDirectory(outputFolder);\n            injected.Add("--paths");\n            injected.Add(outputFolder);\n        }\n'''
# Restrict to the playlist item arg builder.
builder_pos = s.find('private List<string> BuildPlaylistItemDownloadArgs')
inject_pos = s.find(old, builder_pos)
if builder_pos < 0 or inject_pos < 0: raise SystemExit('Preview7 injected args anchor not found')
s = s[:inject_pos] + new + s[inject_pos + len(old):]

# Playlist batch: create/use a playlist-named folder once for the whole batch.
method_start = s.find('private async Task DownloadSelectedPlaylistAsync()')
if method_start < 0: raise SystemExit('Preview7 playlist download method not found')
dir_anchor = '        Directory.CreateDirectory(folderBox.Text);\n'
dir_pos = s.find(dir_anchor, method_start)
if dir_pos < 0: raise SystemExit('Preview7 playlist Directory anchor not found')
dir_new = dir_anchor + '''        var playlistFolder = BuildNamedSubfolder(folderBox.Text, currentPlaylistTitle, "YouTube Playlist");\n        Directory.CreateDirectory(playlistFolder);\n        AppendLog("Playlist folder: " + playlistFolder);\n'''
s = s[:dir_pos] + dir_new + s[dir_pos + len(dir_anchor):]

call_old = '                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable);\n'
call_pos = s.find(call_old, method_start)
if call_pos < 0: raise SystemExit('Preview7 playlist builder call not found')
call_new = '                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable, playlistFolder);\n'
s = s[:call_pos] + call_new + s[call_pos + len(call_old):]

# Channel queue: each analyzed channel gets its own folder. Selections from multiple channels still route correctly.
queue_download_start = s.find('private async Task DownloadReadyChannelQueueAsync()')
if queue_download_start < 0: raise SystemExit('Preview7 channel download method not found')
call_pos = s.find(call_old, queue_download_start)
if call_pos < 0: raise SystemExit('Preview7 channel builder call not found')
channel_new = '''                var channelFolder = BuildNamedSubfolder(folderBox.Text, item.ChannelName, "YouTube Channel");\n                Directory.CreateDirectory(channelFolder);\n                var args = BuildPlaylistItemDownloadArgs(item.Url, cookieFile, quality.Height, quality.BestAvailable, channelFolder);\n'''
s = s[:call_pos] + channel_new + s[call_pos + len(call_old):]

# The completed-card text should report the real named folder.
meta_old = '                    item.Meta = "Saved to " + folderBox.Text;\n'
meta_pos = s.find(meta_old, queue_download_start)
if meta_pos >= 0:
    s = s[:meta_pos] + '                    item.Meta = "Saved to " + channelFolder;\n' + s[meta_pos + len(meta_old):]

s = s.replace('Text = "PC v1.2 Preview 6",', 'Text = "PC v1.2 Preview 7",', 1)
s = s.replace('Browser UI v1.2 Preview 6 starting', 'Browser UI v1.2 Preview 7 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview6-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview7-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 7 scroll-safe selector + channel/playlist folders')
