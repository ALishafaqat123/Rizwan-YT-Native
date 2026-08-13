from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Cache recent normal metadata results so returning to a recently-opened video is instant.
old = '    private readonly List<QualityChoice> qualityChoices = new();\n'
new = old + '    private readonly Dictionary<string, (DateTime CachedAt, string Output)> mediaProbeCache = new();\n'
if old not in s:
    raise SystemExit('qualityChoices cache anchor not found')
s = s.replace(old, new, 1)

# Playlist links attached to a watch URL must not delay the current video analysis.
old = '''        var playlistUrl = GetPlaylistUrl(url);\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\n            await AnalyzePlaylistAsync(playlistUrl);\n\n        if (IsPlaylistLandingPage(url))\n        {\n            currentMediaUrl = string.Empty;\n            downloadTray.Visible = false;\n            ShowView(playlistView);\n            return;\n        }\n'''
new = '''        var playlistUrl = GetPlaylistUrl(url);\n        if (IsPlaylistLandingPage(url))\n        {\n            currentMediaUrl = string.Empty;\n            downloadTray.Visible = false;\n            ShowView(playlistView);\n            if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\n                await AnalyzePlaylistAsync(playlistUrl);\n            return;\n        }\n        if (!string.IsNullOrWhiteSpace(playlistUrl) && !string.Equals(currentPlaylistUrl, playlistUrl, StringComparison.Ordinal))\n        {\n            // A watch URL can carry a playlist ID. Load that playlist in the background,\n            // but never make the user wait for hundreds of playlist entries before the\n            // current video's title/quality becomes ready.\n            _ = AnalyzePlaylistAsync(playlistUrl);\n        }\n'''
if old not in s:
    raise SystemExit('playlist priority anchor not found')
s = s.replace(old, new, 1)

# Make the visible status match the actual amount of work being done.
s = s.replace('        mediaMeta.Text = "Checking available qualities and audio languages";\n',
              '        mediaMeta.Text = audioDubToggle.Checked ? "Checking quality and audio languages…" : "Reading title and quality…";\n', 1)

# Use a short-lived metadata cache before starting another yt-dlp extraction.
old = '''            var normalResult = await RunMediaProbeAsync(url, token, richAudio: false);\n            if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;\n'''
new = '''            (int ExitCode, string Output, string Error, bool BrowserSignedIn) normalResult;\n            if (mediaProbeCache.TryGetValue(url, out var cached) && DateTime.UtcNow - cached.CachedAt < TimeSpan.FromMinutes(10))\n            {\n                normalResult = (0, cached.Output, string.Empty, false);\n                AppendLog("Fast analysis cache hit");\n            }\n            else\n            {\n                normalResult = await RunMediaProbeAsync(url, token, richAudio: false);\n                if (normalResult.ExitCode == 0 && !string.IsNullOrWhiteSpace(normalResult.Output))\n                {\n                    mediaProbeCache[url] = (DateTime.UtcNow, normalResult.Output);\n                    if (mediaProbeCache.Count > 20)\n                    {\n                        var oldest = mediaProbeCache.OrderBy(x => x.Value.CachedAt).First().Key;\n                        mediaProbeCache.Remove(oldest);\n                    }\n                }\n            }\n            if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;\n'''
if old not in s:
    raise SystemExit('normal probe cache anchor not found')
s = s.replace(old, new, 1)

# Replace the v1.1.3 probe: public/no-cookie probe first, browser cookies only as fallback.
pattern = re.compile(r'    private async Task<\(int ExitCode, string Output, string Error, bool BrowserSignedIn\)> RunMediaProbeAsync\(string url, CancellationToken token, bool richAudio\)\n    \{.*?\n    \}\n\n    private async Task<\(string\? Path, bool SignedIn\)> ExportYouTubeCookiesAsync', re.S)
replacement = r'''    private async Task<(int ExitCode, string Output, string Error, bool BrowserSignedIn)> RunMediaProbeAsync(string url, CancellationToken token, bool richAudio)
    {
        List<string> BuildProbeArgs(string? cookieFile, bool rich)
        {
            var args = CommonArgs(url, includeOutput: false);
            if (args.Count > 0 && string.Equals(args[^1], url, StringComparison.Ordinal))
                args.RemoveAt(args.Count - 1);
            args.Add("--no-playlist");
            args.Add("--skip-download");
            args.Add("--dump-single-json");
            if (!string.IsNullOrWhiteSpace(cookieFile))
            {
                args.Add("--cookies");
                args.Add(cookieFile!);
            }
            if (rich)
            {
                args.Add("--extractor-args");
                args.Add("youtube:player_client=default,web_embedded");
            }
            args.Add(url);
            return args;
        }

        // Most public YouTube videos do not need the browser session at all. Avoiding
        // a WebView2 cookie export here removes work from every normal analysis.
        if (!richAudio)
        {
            var fastResult = await RunCaptureDetailedAsync(BuildProbeArgs(null, false), token);
            if (fastResult.ExitCode == 0 && !string.IsNullOrWhiteSpace(fastResult.Output))
                return (fastResult.ExitCode, fastResult.Output, fastResult.Error, false);

            // Only fall back to the live browser session when the public probe fails
            // (login/age/verification/session-restricted videos).
            var fallbackCookies = await ExportYouTubeCookiesAsync(token);
            if (string.IsNullOrWhiteSpace(fallbackCookies.Path))
                return (fastResult.ExitCode, fastResult.Output, fastResult.Error, fallbackCookies.SignedIn);
            try
            {
                AppendLog("Fast public probe needed browser-session fallback");
                var sessionResult = await RunCaptureDetailedAsync(BuildProbeArgs(fallbackCookies.Path, false), token);
                return (sessionResult.ExitCode, sessionResult.Output, sessionResult.Error, fallbackCookies.SignedIn);
            }
            finally
            {
                DeleteTempCookieFile(fallbackCookies.Path);
            }
        }

        // Rich Audio is explicitly requested by the user, so use the live browser
        // session from the start to preserve the working Auto-Dub behavior.
        var cookieSnapshot = await ExportYouTubeCookiesAsync(token);
        try
        {
            var result = await RunCaptureDetailedAsync(BuildProbeArgs(cookieSnapshot.Path, true), token);
            return (result.ExitCode, result.Output, result.Error, cookieSnapshot.SignedIn);
        }
        finally
        {
            DeleteTempCookieFile(cookieSnapshot.Path);
        }
    }

    private async Task<(string? Path, bool SignedIn)> ExportYouTubeCookiesAsync'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'RunMediaProbeAsync fast replacement failed: {n}')
s = s2

# Turning Dub OFF should be instant. Turning it ON still re-runs analysis to discover tracks.
old = '''        audioDubToggle.CheckedChanged += async (_, _) =>\n        {\n            if (loadingSettings) return;\n            SaveSettings();\n            if (!string.IsNullOrWhiteSpace(currentMediaUrl))\n            {\n                lastAnalyzedUrl = string.Empty;\n                await AnalyzeMediaAsync(currentMediaUrl);\n            }\n        };\n'''
new = '''        audioDubToggle.CheckedChanged += async (_, _) =>\n        {\n            if (loadingSettings) return;\n            SaveSettings();\n            if (!audioDubToggle.Checked)\n            {\n                var originalOnly = audioChoices.FirstOrDefault(x => x.Kind is AudioKind.Original or AudioKind.Alternate or AudioKind.Default)\n                    ?? new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0);\n                audioChoices.Clear();\n                audioChoices.Add(originalOnly);\n                audioBox.Items.Clear();\n                audioBox.Items.Add(originalOnly.Label);\n                audioBox.SelectedIndex = 0;\n                audioBox.Enabled = true;\n                return;\n            }\n            if (!string.IsNullOrWhiteSpace(currentMediaUrl))\n            {\n                lastAnalyzedUrl = string.Empty;\n                await AnalyzeMediaAsync(currentMediaUrl);\n            }\n        };\n'''
if old not in s:
    raise SystemExit('dub toggle speed anchor not found')
s = s.replace(old, new, 1)

s = s.replace('Text = "PC v1.2 Preview 2",', 'Text = "PC v1.2 Preview 3",', 1)
s = s.replace('Browser UI v1.2 Preview 2', 'Browser UI v1.2 Preview 3', 1)

p.write_text(s, encoding='utf-8')

iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview2-Setup',
              'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview3-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 3 fast-analysis optimization')
