from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

pattern = re.compile(
    r'    private static string ChannelSelectorScript\(\) => """.*?""";\n\n    private void BrowserWebMessageReceived',
    re.S,
)

replacement = r'''    private static string ChannelSelectorScript() => """
(() => {
  if (window.__rmsChannelSelectorInstalledV5) return;
  window.__rmsChannelSelectorInstalledV5 = true;

  const isChannelPage = () => {
    const p = location.pathname || '';
    return p.startsWith('/@') || p.startsWith('/channel/') || p.startsWith('/c/') || p.startsWith('/user/');
  };

  const normalizeVideoUrl = href => {
    try {
      const u = new URL(href, location.origin);
      if (u.pathname === '/watch' && u.searchParams.get('v')) {
        return location.origin + '/watch?v=' + encodeURIComponent(u.searchParams.get('v'));
      }
      if (u.pathname.startsWith('/shorts/')) return location.origin + u.pathname;
      return u.href;
    } catch { return href || ''; }
  };

  const findCards = () => {
    const selectors = [
      'ytd-rich-item-renderer',
      'ytd-rich-grid-media',
      'ytd-grid-video-renderer',
      'ytd-video-renderer',
      'yt-lockup-view-model',
      'yt-lockup-metadata-view-model',
      '.yt-lockup-view-model-wiz',
      '.ytGridShelfViewModelGridShelfItem'
    ];
    return [...new Set(selectors.flatMap(sel => Array.from(document.querySelectorAll(sel))))];
  };

  const findVideoLink = card => {
    const candidates = card.querySelectorAll(
      'a#thumbnail[href], a#video-title-link[href], a[href^="/watch"], a[href*="youtube.com/watch"], a[href^="/shorts/"]'
    );
    for (const a of candidates) {
      const href = a.getAttribute('href') || a.href || '';
      if (href.includes('/watch?v=') || href.startsWith('/watch?') || href.includes('youtube.com/watch?v=') || href.startsWith('/shorts/')) return a;
    }
    return null;
  };

  const chooseActionHost = card => {
    return card.querySelector(
      '#details, #meta, ytd-video-meta-block, yt-lockup-metadata-view-model, .yt-lockup-metadata-view-model-wiz__metadata, .yt-lockup-metadata-view-model-wiz__text-container'
    ) || card;
  };

  const decorate = () => {
    if (!isChannelPage()) return;

    findCards().forEach(card => {
      if (card.dataset.rmsSelectorReady === '1' || card.querySelector('.rms-channel-select-v5')) return;

      const link = findVideoLink(card);
      if (!link) return;
      const rawHref = link.getAttribute('href') || link.href || '';
      const url = normalizeVideoUrl(rawHref);
      if (!url || (!url.includes('/watch?v=') && !url.includes('/shorts/'))) return;

      const titleEl = card.querySelector('#video-title-link, #video-title, a[title], h3 a, .yt-lockup-metadata-view-model-wiz__title a');
      const img = card.querySelector('img.yt-core-image, ytd-thumbnail img, yt-thumbnail-view-model img, img');
      const host = chooseActionHost(card);
      if (!host) return;

      const row = document.createElement('div');
      row.className = 'rms-channel-action-row-v5';
      Object.assign(row.style, {
        display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
        marginTop: '10px', marginBottom: '4px', minHeight: '34px'
      });

      const button = document.createElement('button');
      button.className = 'rms-channel-select-v5';
      button.type = 'button';
      button.textContent = 'Download';
      button.title = 'Select this video for Rizwan Media Saver Downloads';
      Object.assign(button.style, {
        border: '0', borderRadius: '6px', padding: '7px 14px',
        background: '#ff9800', color: '#ffffff', fontWeight: '700',
        fontSize: '13px', lineHeight: '18px', cursor: 'pointer',
        fontFamily: 'Roboto, Arial, sans-serif', boxShadow: 'none'
      });

      button.addEventListener('mouseenter', () => { if (!button.disabled) button.style.background = '#f57c00'; });
      button.addEventListener('mouseleave', () => { if (!button.disabled) button.style.background = '#ff9800'; });

      button.addEventListener('click', ev => {
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation();

        const title = (titleEl?.getAttribute('title') || titleEl?.textContent || 'YouTube video').trim();
        const thumbnail = img?.currentSrc || img?.src || '';
        window.chrome.webview.postMessage({ type: 'rms-channel-select', url, title, thumbnail });

        button.textContent = '✓ Selected';
        button.disabled = true;
        button.style.background = '#1fc984';
        button.style.color = '#09231a';
        button.style.cursor = 'default';
      }, true);

      row.appendChild(button);
      host.appendChild(row);
      card.dataset.rmsSelectorReady = '1';
    });
  };

  let decorateTimer = 0;
  const scheduleDecorate = () => {
    clearTimeout(decorateTimer);
    decorateTimer = setTimeout(decorate, 120);
  };

  new MutationObserver(scheduleDecorate).observe(document.documentElement, { childList: true, subtree: true });
  window.addEventListener('yt-navigate-finish', scheduleDecorate, true);
  window.addEventListener('popstate', scheduleDecorate, true);
  setInterval(decorate, 1000);
  decorate();
})();
""";

    private void BrowserWebMessageReceived'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'ChannelSelectorScript replacement failed: {n}')
s = s2

s = s.replace('Text = "PC v1.2 Preview 4",', 'Text = "PC v1.2 Preview 5",', 1)
s = s.replace('Browser UI v1.2 Preview 4 starting', 'Browser UI v1.2 Preview 5 starting', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview4-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview5-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 5 robust channel selector')
