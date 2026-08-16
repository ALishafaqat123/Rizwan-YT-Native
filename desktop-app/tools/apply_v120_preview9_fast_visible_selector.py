from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

pattern = re.compile(
    r'    private static string ChannelSelectorScript\(\) => """.*?""";\n\n    private async Task EnsureChannelSelectorInjectedAsync',
    re.S,
)

replacement = r'''    private static string ChannelSelectorScript() => """
(() => {
  const install = () => {
    if (window.__rmsChannelSelectorInstalledV9) {
      try { window.__rmsChannelScanV9?.(); } catch {}
      return;
    }
    window.__rmsChannelSelectorInstalledV9 = true;

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

    const inScanRange = el => {
      try {
        const r = el.getBoundingClientRect();
        if (!r || r.width < 120 || r.height < 80) return false;
        // Scan the current viewport plus generous space above/below so buttons
        // are already ready when the user reaches the next rows.
        return r.bottom >= -700 && r.top <= (window.innerHeight + 1500);
      } catch { return false; }
    };

    const findCard = anchor => {
      const known = anchor.closest(cardSelector);
      if (known) return known;
      let el = anchor.parentElement;
      for (let depth = 0; el && depth < 11; depth++, el = el.parentElement) {
        const r = el.getBoundingClientRect();
        if (r.width < 170 || r.width > 760 || r.height < 110 || r.height > 1000) continue;
        if (!el.querySelector('img')) continue;
        const links = Array.from(el.querySelectorAll('a[href*="/watch"]'));
        if (!links.some(a => !!videoIdFromHref(a.getAttribute('href') || a.href || ''))) continue;
        return el;
      }
      return null;
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
      row.className = 'rms-channel-action-row-v9';
      row.dataset.videoId = id;
      Object.assign(row.style, {
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
        width: '100%', boxSizing: 'border-box', marginTop: '7px', marginBottom: '5px',
        minHeight: '34px', position: 'relative', zIndex: '60'
      });

      const button = document.createElement('button');
      button.className = 'rms-channel-select-v9';
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

    const ensureCardForAnchor = anchor => {
      const id = videoIdFromHref(anchor.getAttribute('href') || anchor.href || '');
      if (!id) return false;
      const card = findCard(anchor);
      if (!card || !card.isConnected || !inScanRange(card)) return false;

      const rows = Array.from(card.querySelectorAll('.rms-channel-action-row-v9'));
      let matching = rows.find(r => r.dataset.videoId === id) || null;
      for (const row of rows) if (row !== matching) row.remove();

      if (card.dataset.rmsVideoIdV9 && card.dataset.rmsVideoIdV9 !== id) {
        for (const row of Array.from(card.querySelectorAll('.rms-channel-action-row-v9'))) row.remove();
        matching = null;
      }
      card.dataset.rmsVideoIdV9 = id;
      if (matching && matching.isConnected) return true;

      const titleLink = titleLinkFor(card, id);
      const host = actionHost(card, titleLink);
      if (!host) return false;
      host.appendChild(makeButtonRow(card, id, titleLink));
      return true;
    };

    const scan = () => {
      if (!isChannelPage()) return 0;
      const anchors = Array.from(document.querySelectorAll('a[href*="/watch"]'));
      const seenCards = new Set();
      let candidates = 0;
      let buttons = 0;

      for (const anchor of anchors) {
        if (!videoIdFromHref(anchor.getAttribute('href') || anchor.href || '')) continue;
        const card = findCard(anchor);
        if (!card || seenCards.has(card) || !inScanRange(card)) continue;
        seenCards.add(card);
        candidates++;
        if (ensureCardForAnchor(anchor)) buttons++;
      }

      try {
        if (candidates !== window.__rmsLastFoundV9 || buttons !== window.__rmsLastButtonsV9) {
          window.__rmsLastFoundV9 = candidates;
          window.__rmsLastButtonsV9 = buttons;
          window.chrome.webview.postMessage({ type: 'rms-selector-status', count: buttons, found: candidates, path: location.pathname });
        }
      } catch {}
      return buttons;
    };

    window.__rmsChannelScanV9 = scan;

    // IMPORTANT: leading-edge rAF throttle. Do not debounce/cancel scans while
    // YouTube is continuously mutating the DOM or while the user is scrolling.
    let rafPending = false;
    const scheduleNow = () => {
      if (rafPending) return;
      rafPending = true;
      requestAnimationFrame(() => {
        rafPending = false;
        try { scan(); } catch {}
      });
    };

    const burst = () => {
      scheduleNow();
      setTimeout(scheduleNow, 80);
      setTimeout(scheduleNow, 220);
      setTimeout(scheduleNow, 500);
    };

    new MutationObserver(scheduleNow).observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['href']
    });

    window.addEventListener('scroll', scheduleNow, true);
    window.addEventListener('wheel', scheduleNow, { passive: true, capture: true });
    window.addEventListener('resize', scheduleNow, true);
    window.addEventListener('yt-navigate-finish', burst, true);
    window.addEventListener('yt-page-data-updated', burst, true);
    window.addEventListener('popstate', burst, true);

    // Slow safety pass only; normal work is event/rAF driven and immediate.
    setInterval(scheduleNow, 1200);
    burst();
  };
  install();
})();
""";

    private async Task EnsureChannelSelectorInjectedAsync'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview9 ChannelSelectorScript replacement failed: {n}')
s = s2

s = s.replace('Text = "PC v1.2 Preview 8",', 'Text = "PC v1.2 Preview 9",', 1)
s = s.replace('Browser UI v1.2 Preview 8 starting', 'Browser UI v1.2 Preview 9 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview8-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview9-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 9 fast visible channel selector')
