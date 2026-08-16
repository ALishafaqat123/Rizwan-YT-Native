from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Preview 8: process every YouTube video card independently.
# This avoids skipping visible cards when YouTube keeps hidden/duplicate cards
# for the same video in its virtualized channel grid.
pattern = re.compile(
    r'    private static string ChannelSelectorScript\(\) => """.*?""";\n\n    private async Task EnsureChannelSelectorInjectedAsync',
    re.S,
)

replacement = r'''    private static string ChannelSelectorScript() => """
(() => {
  const install = () => {
    if (window.__rmsChannelSelectorInstalledV8) {
      try { window.__rmsChannelScanV8?.(); } catch {}
      return;
    }
    window.__rmsChannelSelectorInstalledV8 = true;

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

    const cardSelector = [
      'ytd-rich-item-renderer',
      'ytd-rich-grid-media',
      'ytd-grid-video-renderer',
      'ytd-video-renderer',
      'yt-lockup-view-model',
      '.yt-lockup-view-model-wiz',
      '[class*="GridShelfItem"]',
      '[class*="grid-shelf-item"]'
    ].join(', ');

    const scoreAnchor = a => {
      const href = a.getAttribute('href') || a.href || '';
      if (!videoIdFromHref(href)) return -1000;
      let score = 0;
      if (a.id === 'thumbnail' || a.closest('ytd-thumbnail, yt-thumbnail-view-model')) score += 20;
      if ((a.getAttribute('title') || '').trim()) score += 12;
      if ((a.textContent || '').trim().length >= 3) score += 8;
      if (a.id === 'video-title-link' || a.id === 'video-title') score += 10;
      return score;
    };

    const primaryAnchor = card => {
      const links = Array.from(card.querySelectorAll('a[href*="/watch"]'))
        .filter(a => !!videoIdFromHref(a.getAttribute('href') || a.href || ''));
      if (!links.length) return null;
      links.sort((a, b) => scoreAnchor(b) - scoreAnchor(a));
      return links[0];
    };

    const titleLinkFor = (card, id) => {
      const links = Array.from(card.querySelectorAll('a[href*="/watch"]'))
        .filter(a => videoIdFromHref(a.getAttribute('href') || a.href || '') === id);
      return links.find(a => a.id === 'video-title-link' || a.id === 'video-title')
          || links.find(a => (a.getAttribute('title') || '').trim().length > 0)
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

    const makeButtonRow = (card, id, titleLink) => {
      const row = document.createElement('div');
      row.className = 'rms-channel-action-row-v8';
      row.dataset.videoId = id;
      Object.assign(row.style, {
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
        width: '100%', boxSizing: 'border-box', marginTop: '8px', marginBottom: '5px',
        minHeight: '34px', position: 'relative', zIndex: '50'
      });

      const button = document.createElement('button');
      button.className = 'rms-channel-select-v8';
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
        } catch {
          button.textContent = 'Select failed';
        }
      }, true);

      row.appendChild(button);
      return row;
    };

    const fallbackCard = anchor => {
      let el = anchor.parentElement;
      for (let depth = 0; el && depth < 10; depth++, el = el.parentElement) {
        const r = el.getBoundingClientRect();
        if (r.width < 170 || r.width > 720 || r.height < 120 || r.height > 950) continue;
        const watchCount = Array.from(el.querySelectorAll('a[href*="/watch"]'))
          .filter(a => !!videoIdFromHref(a.getAttribute('href') || a.href || '')).length;
        if (watchCount >= 1 && el.querySelector('img') && (el.innerText || '').trim().length > 3) return el;
      }
      return null;
    };

    const ensureCard = card => {
      if (!card || !card.isConnected) return false;
      const anchor = primaryAnchor(card);
      if (!anchor) return false;
      const id = videoIdFromHref(anchor.getAttribute('href') || anchor.href || '');
      if (!id) return false;

      // Crucial V8 rule: uniqueness is per CARD, not per video-ID across the page.
      // YouTube may retain hidden duplicate cards, so a global video-ID check is wrong.
      const rows = Array.from(card.querySelectorAll(':scope .rms-channel-action-row-v8'));
      let matching = rows.find(r => r.dataset.videoId === id) || null;
      for (const row of rows) {
        if (row !== matching) row.remove();
      }

      // If YouTube recycled this DOM node, old marker/button must be rebuilt.
      if (card.dataset.rmsVideoIdV8 && card.dataset.rmsVideoIdV8 !== id) {
        for (const row of Array.from(card.querySelectorAll(':scope .rms-channel-action-row-v8'))) row.remove();
        matching = null;
      }
      card.dataset.rmsVideoIdV8 = id;

      if (matching && matching.isConnected) return true;

      const titleLink = titleLinkFor(card, id);
      const host = actionHost(card, titleLink);
      if (!host) return false;
      host.appendChild(makeButtonRow(card, id, titleLink));
      return true;
    };

    const scan = () => {
      if (!isChannelPage()) return 0;
      const cards = new Set(Array.from(document.querySelectorAll(cardSelector)));

      // Fallback for newer YouTube markup that does not expose a known card tag.
      for (const anchor of Array.from(document.querySelectorAll('a[href*="/watch"]'))) {
        if (!videoIdFromHref(anchor.getAttribute('href') || anchor.href || '')) continue;
        if (anchor.closest(cardSelector)) continue;
        const fallback = fallbackCard(anchor);
        if (fallback) cards.add(fallback);
      }

      let found = 0;
      let buttons = 0;
      for (const card of cards) {
        const anchor = primaryAnchor(card);
        if (!anchor) continue;
        found++;
        if (ensureCard(card)) buttons++;
      }

      try {
        if (found !== window.__rmsLastFoundV8 || buttons !== window.__rmsLastButtonsV8) {
          window.__rmsLastFoundV8 = found;
          window.__rmsLastButtonsV8 = buttons;
          window.chrome.webview.postMessage({ type: 'rms-selector-status', count: buttons, found, path: location.pathname });
        }
      } catch {}
      return buttons;
    };

    window.__rmsChannelScanV8 = scan;
    let timer = 0;
    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        try { scan(); } catch {}
        requestAnimationFrame(() => { try { scan(); } catch {} });
      }, 60);
    };

    new MutationObserver(schedule).observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['href', 'src', 'title']
    });
    window.addEventListener('scroll', schedule, true);
    window.addEventListener('wheel', schedule, { passive: true, capture: true });
    window.addEventListener('resize', schedule, true);
    window.addEventListener('yt-navigate-finish', schedule, true);
    window.addEventListener('yt-page-data-updated', schedule, true);
    window.addEventListener('popstate', schedule, true);
    setInterval(() => { try { scan(); } catch {} }, 300);
    scan();
  };
  install();
})();
""";

    private async Task EnsureChannelSelectorInjectedAsync'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview8 ChannelSelectorScript replacement failed: {n}')
s = s2

s = s.replace('Text = "PC v1.2 Preview 7",', 'Text = "PC v1.2 Preview 8",', 1)
s = s.replace('Browser UI v1.2 Preview 7 starting', 'Browser UI v1.2 Preview 8 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview7-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview8-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 8 per-card channel selector')
