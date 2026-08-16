from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Replace ChannelSelectorScript with a generic anchor-driven scanner.
pattern = re.compile(
    r'    private static string ChannelSelectorScript\(\) => """.*?""";\n\n    private void BrowserWebMessageReceived',
    re.S,
)

replacement = r'''    private static string ChannelSelectorScript() => """
(() => {
  const install = () => {
    if (window.__rmsChannelSelectorInstalledV6) {
      try { window.__rmsChannelDecorateV6?.(); } catch {}
      return;
    }
    window.__rmsChannelSelectorInstalledV6 = true;

    const isChannelPage = () => {
      const p = location.pathname || '';
      return p.startsWith('/@') || p.startsWith('/channel/') || p.startsWith('/c/') || p.startsWith('/user/');
    };

    const videoIdFromHref = href => {
      try {
        const u = new URL(href, location.origin);
        if (u.pathname === '/watch') return u.searchParams.get('v') || '';
        return '';
      } catch { return ''; }
    };

    const canonicalUrl = id => location.origin + '/watch?v=' + encodeURIComponent(id);

    const allWatchAnchors = () => Array.from(document.querySelectorAll('a[href*="/watch"]'))
      .filter(a => !!videoIdFromHref(a.getAttribute('href') || a.href || ''));

    const findCard = (anchor, id) => {
      const preferred = anchor.closest(
        'ytd-rich-item-renderer, ytd-rich-grid-media, ytd-grid-video-renderer, ytd-video-renderer, yt-lockup-view-model, .yt-lockup-view-model-wiz, [class*="GridShelfItem"], [class*="grid-shelf-item"]'
      );
      if (preferred) return preferred;

      let el = anchor.parentElement;
      for (let depth = 0; el && depth < 9; depth++, el = el.parentElement) {
        const sameLinks = Array.from(el.querySelectorAll('a[href*="/watch"]'))
          .filter(a => videoIdFromHref(a.getAttribute('href') || a.href || '') === id);
        const img = el.querySelector('img');
        const text = (el.innerText || '').trim();
        const r = el.getBoundingClientRect();
        if (sameLinks.length >= 1 && img && text.length > 4 && r.width >= 180 && r.width <= 650 && r.height >= 140 && r.height <= 900)
          return el;
      }
      return null;
    };

    const bestTitleLink = (card, id) => {
      const links = Array.from(card.querySelectorAll('a[href*="/watch"]'))
        .filter(a => videoIdFromHref(a.getAttribute('href') || a.href || '') === id);
      const named = links.find(a => (a.getAttribute('title') || '').trim().length > 0);
      if (named) return named;
      const textual = links.find(a => (a.textContent || '').trim().length >= 3);
      return textual || links[0] || null;
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

    const decorate = () => {
      if (!isChannelPage()) return 0;

      const byId = new Map();
      for (const a of allWatchAnchors()) {
        const id = videoIdFromHref(a.getAttribute('href') || a.href || '');
        if (id && !byId.has(id)) byId.set(id, a);
      }

      let added = 0;
      for (const [id, anchor] of byId.entries()) {
        if (document.querySelector(`.rms-channel-select-v6[data-video-id="${CSS.escape(id)}"]`)) continue;

        const card = findCard(anchor, id);
        if (!card) continue;
        const titleLink = bestTitleLink(card, id);
        const host = actionHost(card, titleLink);
        if (!host) continue;

        const row = document.createElement('div');
        row.className = 'rms-channel-action-row-v6';
        row.dataset.videoId = id;
        Object.assign(row.style, {
          display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
          width: '100%', boxSizing: 'border-box', marginTop: '9px', marginBottom: '5px',
          minHeight: '34px', position: 'relative', zIndex: '30'
        });

        const button = document.createElement('button');
        button.className = 'rms-channel-select-v6';
        button.dataset.videoId = id;
        button.type = 'button';
        button.textContent = 'Download';
        button.title = 'Select this video for Rizwan Media Saver Downloads';
        Object.assign(button.style, {
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          minWidth: '86px', height: '32px', border: '0', borderRadius: '6px',
          padding: '6px 14px', background: '#ff9800', color: '#ffffff',
          fontWeight: '700', fontSize: '13px', lineHeight: '18px', cursor: 'pointer',
          fontFamily: 'Roboto, Arial, sans-serif', boxShadow: 'none'
        });

        button.addEventListener('mouseenter', () => { if (!button.disabled) button.style.background = '#f57c00'; });
        button.addEventListener('mouseleave', () => { if (!button.disabled) button.style.background = '#ff9800'; });
        button.addEventListener('click', ev => {
          ev.preventDefault();
          ev.stopPropagation();
          ev.stopImmediatePropagation();

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
          } catch (err) {
            button.textContent = 'Select failed';
          }
        }, true);

        row.appendChild(button);
        host.appendChild(row);
        added++;
      }

      try {
        const visible = document.querySelectorAll('.rms-channel-select-v6').length;
        if (visible !== window.__rmsLastSelectorCountV6) {
          window.__rmsLastSelectorCountV6 = visible;
          window.chrome.webview.postMessage({ type: 'rms-selector-status', count: visible, found: byId.size, path: location.pathname });
        }
      } catch {}

      return added;
    };

    window.__rmsChannelDecorateV6 = decorate;
    let timer = 0;
    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(() => { try { decorate(); } catch {} }, 120);
    };
    new MutationObserver(schedule).observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener('yt-navigate-finish', schedule, true);
    window.addEventListener('yt-page-data-updated', schedule, true);
    window.addEventListener('popstate', schedule, true);
    setInterval(() => { try { decorate(); } catch {} }, 900);
    decorate();
  };

  install();
})();
""";

    private async Task EnsureChannelSelectorInjectedAsync()
    {
        try
        {
            if (browser.CoreWebView2 == null || browser.Source == null) return;
            var url = browser.Source.ToString();
            if (!url.Contains("youtube.com", StringComparison.OrdinalIgnoreCase)) return;
            await browser.CoreWebView2.ExecuteScriptAsync(ChannelSelectorScript());
        }
        catch (Exception ex)
        {
            AppendLog("Channel selector injection error: " + ex.Message);
        }
    }

    private void BrowserWebMessageReceived'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview6 ChannelSelectorScript replacement failed: {n}')
s = s2

# Log selector detection messages and leave selection message behavior untouched.
old = '''            using var doc = JsonDocument.Parse(e.WebMessageAsJson);\n            var root = doc.RootElement;\n            if (!root.TryGetProperty("type", out var typeEl) || !string.Equals(typeEl.GetString(), "rms-channel-select", StringComparison.Ordinal)) return;\n            var url = root.TryGetProperty("url", out var urlEl) ? urlEl.GetString() ?? string.Empty : string.Empty;\n'''
new = '''            using var doc = JsonDocument.Parse(e.WebMessageAsJson);\n            var root = doc.RootElement;\n            if (!root.TryGetProperty("type", out var typeEl)) return;\n            var messageType = typeEl.GetString() ?? string.Empty;\n            if (string.Equals(messageType, "rms-selector-status", StringComparison.Ordinal))\n            {\n                var count = root.TryGetProperty("count", out var countEl) && countEl.TryGetInt32(out var c) ? c : 0;\n                var found = root.TryGetProperty("found", out var foundEl) && foundEl.TryGetInt32(out var f) ? f : 0;\n                AppendLog($"Channel selector: watch links={found}, buttons={count}");\n                return;\n            }\n            if (!string.Equals(messageType, "rms-channel-select", StringComparison.Ordinal)) return;\n            var url = root.TryGetProperty("url", out var urlEl) ? urlEl.GetString() ?? string.Empty : string.Empty;\n'''
if old not in s:
    raise SystemExit('Preview6 BrowserWebMessageReceived anchor not found')
s = s.replace(old, new, 1)

# Force runtime injection on every completed navigation before normal media handling.
old = '''        browser.NavigationCompleted += async (_, _) =>\n        {\n            if (browser.Source != null) await HandleBrowserNavigationAsync(browser.Source.ToString());\n        };\n'''
new = '''        browser.NavigationCompleted += async (_, _) =>\n        {\n            await EnsureChannelSelectorInjectedAsync();\n            if (browser.Source != null) await HandleBrowserNavigationAsync(browser.Source.ToString());\n        };\n'''
if old not in s:
    raise SystemExit('Preview6 NavigationCompleted anchor not found')
s = s.replace(old, new, 1)

# Also run after YouTube SPA SourceChanged, which is often the only navigation event.
old = '''        browser.SourceChanged += async (_, _) =>\n        {\n            if (browser.Source == null) return;\n            var sourceUrl = browser.Source.ToString();\n            addressBox.Text = sourceUrl;\n            // YouTube is a single-page app: clicking another video often changes the URL\n            // without a full NavigationCompleted event. Analyze immediately on SourceChanged.\n            await HandleBrowserNavigationAsync(sourceUrl);\n        };\n'''
new = '''        browser.SourceChanged += async (_, _) =>\n        {\n            if (browser.Source == null) return;\n            var sourceUrl = browser.Source.ToString();\n            addressBox.Text = sourceUrl;\n            await EnsureChannelSelectorInjectedAsync();\n            // YouTube is a single-page app: clicking another video often changes the URL\n            // without a full NavigationCompleted event. Analyze immediately on SourceChanged.\n            await HandleBrowserNavigationAsync(sourceUrl);\n        };\n'''
if old not in s:
    raise SystemExit('Preview6 SourceChanged anchor not found')
s = s.replace(old, new, 1)

s = s.replace('Text = "PC v1.2 Preview 5",', 'Text = "PC v1.2 Preview 6",', 1)
s = s.replace('Browser UI v1.2 Preview 5 starting', 'Browser UI v1.2 Preview 6 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview5-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview6-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 6 runtime generic channel injection')
