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
    if (window.__rmsChannelSelectorInstalledV10) {
      try { window.__rmsChannelRescanV10?.(); } catch {}
      return;
    }
    window.__rmsChannelSelectorInstalledV10 = true;

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

    const isWatchAnchor = el => !!(el && el.matches && el.matches('a[href*="/watch"]') && videoIdFromHref(el.getAttribute('href') || el.href || ''));

    const findCard = anchor => {
      const known = anchor.closest(cardSelector);
      if (known) return known;
      let el = anchor.parentElement;
      for (let depth = 0; el && depth < 11; depth++, el = el.parentElement) {
        if (!el.querySelector('img')) continue;
        const links = Array.from(el.querySelectorAll('a[href*="/watch"]'));
        if (!links.some(a => !!videoIdFromHref(a.getAttribute('href') || a.href || ''))) continue;
        const r = el.getBoundingClientRect();
        if (r.width >= 160 && r.width <= 800 && r.height >= 90 && r.height <= 1100) return el;
      }
      return null;
    };

    const chooseAnchor = card => {
      const links = Array.from(card.querySelectorAll('a[href*="/watch"]'))
        .filter(a => !!videoIdFromHref(a.getAttribute('href') || a.href || ''));
      if (!links.length) return null;
      return links.find(a => a.id === 'video-title-link' || a.id === 'video-title')
          || links.find(a => (a.getAttribute('title') || '').trim().length > 0)
          || links.find(a => (a.textContent || '').trim().length >= 3)
          || links[0];
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
      row.className = 'rms-channel-action-row-v10';
      row.dataset.videoId = id;
      Object.assign(row.style, {
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
        width: '100%', boxSizing: 'border-box', marginTop: '7px', marginBottom: '5px',
        minHeight: '34px', position: 'relative', zIndex: '60'
      });

      const button = document.createElement('button');
      button.className = 'rms-channel-select-v10';
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

    let injected = 0;
    let mutationBatches = 0;
    let hrefChanges = 0;
    let lastStatusAt = 0;

    const report = force => {
      const now = Date.now();
      if (!force && now - lastStatusAt < 900) return;
      lastStatusAt = now;
      try {
        const count = document.querySelectorAll('.rms-channel-select-v10').length;
        window.chrome.webview.postMessage({
          type: 'rms-selector-status', count, found: injected,
          mutations: mutationBatches, hrefChanges, path: location.pathname
        });
      } catch {}
    };

    const ensureCard = (card, preferredAnchor = null) => {
      if (!isChannelPage() || !card || !card.isConnected) return false;
      const anchor = preferredAnchor && card.contains(preferredAnchor) && isWatchAnchor(preferredAnchor)
        ? preferredAnchor : chooseAnchor(card);
      if (!anchor) return false;
      const id = videoIdFromHref(anchor.getAttribute('href') || anchor.href || '');
      if (!id) return false;

      const rows = Array.from(card.querySelectorAll('.rms-channel-action-row-v10'));
      let matching = rows.find(r => r.dataset.videoId === id) || null;
      for (const row of rows) if (row !== matching) row.remove();

      if (card.dataset.rmsVideoIdV10 && card.dataset.rmsVideoIdV10 !== id) {
        for (const row of Array.from(card.querySelectorAll('.rms-channel-action-row-v10'))) row.remove();
        matching = null;
      }
      card.dataset.rmsVideoIdV10 = id;
      if (matching && matching.isConnected) return true;

      const titleLink = titleLinkFor(card, id);
      const host = actionHost(card, titleLink);
      if (!host) return false;
      host.appendChild(makeButtonRow(card, id, titleLink));
      injected++;
      report(false);
      return true;
    };

    const processAnchor = anchor => {
      if (!isChannelPage() || !isWatchAnchor(anchor)) return false;
      const card = findCard(anchor);
      return card ? ensureCard(card, anchor) : false;
    };

    const processSubtree = node => {
      if (!isChannelPage() || !node || node.nodeType !== 1) return;
      const el = node;
      if (el.classList?.contains('rms-channel-action-row-v10') || el.classList?.contains('rms-channel-select-v10')) return;

      if (isWatchAnchor(el)) processAnchor(el);
      if (el.matches?.(cardSelector)) ensureCard(el);

      const anchors = el.querySelectorAll?.('a[href*="/watch"]');
      if (anchors) for (const a of anchors) processAnchor(a);
    };

    const rescanExisting = () => {
      if (!isChannelPage()) return;
      const anchors = document.querySelectorAll('a[href*="/watch"]');
      for (const a of anchors) processAnchor(a);
      report(true);
    };

    window.__rmsChannelRescanV10 = rescanExisting;

    const observer = new MutationObserver(mutations => {
      if (!isChannelPage()) return;
      mutationBatches++;
      for (const m of mutations) {
        if (m.type === 'attributes') {
          if (m.target && m.target.matches?.('a[href*="/watch"]')) {
            hrefChanges++;
            processAnchor(m.target);
          }
          continue;
        }

        if (m.type === 'childList') {
          const targetCard = m.target?.closest?.(cardSelector);
          if (targetCard) ensureCard(targetCard);
          for (const n of m.addedNodes) processSubtree(n);
        }
      }
      report(false);
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['href']
    });

    const routeRefresh = () => {
      setTimeout(rescanExisting, 0);
      setTimeout(rescanExisting, 80);
      setTimeout(rescanExisting, 250);
    };
    window.addEventListener('yt-navigate-finish', routeRefresh, true);
    window.addEventListener('yt-page-data-updated', routeRefresh, true);
    window.addEventListener('popstate', routeRefresh, true);

    // Initial pass only. After this, new/recycled cards are handled by mutations.
    rescanExisting();
  };
  install();
})();
""";

    private async Task EnsureChannelSelectorInjectedAsync'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Preview10 ChannelSelectorScript replacement failed: {n}')
s = s2

# Install selector at document creation so it observes YouTube cards from the moment
# they are created, instead of waiting for NavigationCompleted/SourceChanged.
old = '''            await browser.EnsureCoreWebView2Async();\n            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;\n'''
new = '''            await browser.EnsureCoreWebView2Async();\n            await browser.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(ChannelSelectorScript());\n            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;\n'''
if old not in s:
    raise SystemExit('Preview10 document-created injection anchor not found')
s = s.replace(old, new, 1)

s = s.replace('Text = "PC v1.2 Preview 9",', 'Text = "PC v1.2 Preview 10",', 1)
s = s.replace('Browser UI v1.2 Preview 9 starting', 'Browser UI v1.2 Preview 10 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview9-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview10-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 10 event-driven document-created channel selector')
