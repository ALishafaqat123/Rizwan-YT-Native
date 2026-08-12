from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Replace the v1.1.2 probe with a browser-session-aware probe and add cookie helpers.
pattern = re.compile(r'    private async Task<\(int ExitCode, string Output\)> RunMediaProbeAsync\(string url, CancellationToken token, bool richAudio\)\n    \{.*?\n    \}\n\n    private List<AudioChoice> ParseAudioChoices', re.S)
replacement = r'''    private async Task<(int ExitCode, string Output, string Error, bool BrowserSignedIn)> RunMediaProbeAsync(string url, CancellationToken token, bool richAudio)
    {
        var cookieSnapshot = await ExportYouTubeCookiesAsync(token);
        var args = CommonArgs(url, includeOutput: false);
        if (args.Count > 0 && string.Equals(args[^1], url, StringComparison.Ordinal))
            args.RemoveAt(args.Count - 1);

        args.Add("--no-playlist");
        args.Add("--skip-download");
        args.Add("--dump-single-json");
        if (!string.IsNullOrWhiteSpace(cookieSnapshot.Path))
        {
            args.Add("--cookies");
            args.Add(cookieSnapshot.Path!);
        }
        if (richAudio)
        {
            args.Add("--extractor-args");
            args.Add("youtube:player_client=default,web_embedded");
        }
        args.Add(url);

        try
        {
            var result = await RunCaptureDetailedAsync(args, token);
            return (result.ExitCode, result.Output, result.Error, cookieSnapshot.SignedIn);
        }
        finally
        {
            DeleteTempCookieFile(cookieSnapshot.Path);
        }
    }

    private async Task<(string? Path, bool SignedIn)> ExportYouTubeCookiesAsync(CancellationToken token)
    {
        try
        {
            if (browser.CoreWebView2 == null) return (null, false);
            var cookies = await browser.CoreWebView2.CookieManager.GetCookiesAsync("");
            token.ThrowIfCancellationRequested();

            var relevant = cookies
                .Where(c =>
                {
                    var d = (c.Domain ?? string.Empty).TrimStart('.').ToLowerInvariant();
                    return d.EndsWith("youtube.com") || d.EndsWith("google.com") || d.EndsWith("googleusercontent.com");
                })
                .Where(c => !string.IsNullOrWhiteSpace(c.Name) && c.Value != null)
                .ToList();
            if (relevant.Count == 0) return (null, false);

            var signedIn = relevant.Any(c =>
                c.Name.Equals("SAPISID", StringComparison.OrdinalIgnoreCase) ||
                c.Name.Equals("__Secure-3PAPISID", StringComparison.OrdinalIgnoreCase) ||
                c.Name.Equals("__Secure-1PAPISID", StringComparison.OrdinalIgnoreCase) ||
                c.Name.Equals("LOGIN_INFO", StringComparison.OrdinalIgnoreCase));

            var tempDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Rizwan Media Saver PC", "Temp");
            Directory.CreateDirectory(tempDir);
            var path = Path.Combine(tempDir, "yt-session-" + Guid.NewGuid().ToString("N") + ".txt");
            var sb = new StringBuilder();
            sb.AppendLine("# Netscape HTTP Cookie File");
            sb.AppendLine("# Temporary file generated from the app's WebView2 YouTube session.");

            foreach (var c in relevant)
            {
                if (c.Name.IndexOfAny(new[] { '\t', '\r', '\n' }) >= 0 || c.Value.IndexOfAny(new[] { '\t', '\r', '\n' }) >= 0)
                    continue;
                var domain = string.IsNullOrWhiteSpace(c.Domain) ? ".youtube.com" : c.Domain;
                var includeSubdomains = domain.StartsWith(".") ? "TRUE" : "FALSE";
                var secure = c.IsSecure ? "TRUE" : "FALSE";
                long expires = 0;
                if (!c.IsSession)
                {
                    try { expires = new DateTimeOffset(c.Expires.ToUniversalTime()).ToUnixTimeSeconds(); }
                    catch { expires = 0; }
                }
                sb.Append(domain).Append('\t')
                  .Append(includeSubdomains).Append('\t')
                  .Append(string.IsNullOrWhiteSpace(c.Path) ? "/" : c.Path).Append('\t')
                  .Append(secure).Append('\t')
                  .Append(expires).Append('\t')
                  .Append(c.Name).Append('\t')
                  .Append(c.Value).AppendLine();
            }

            File.WriteAllText(path, sb.ToString(), new UTF8Encoding(false));
            return (path, signedIn);
        }
        catch (OperationCanceledException) { throw; }
        catch (Exception ex)
        {
            AppendLog("YouTube session bridge note: " + ex.Message);
            return (null, false);
        }
    }

    private static void DeleteTempCookieFile(string? path)
    {
        if (string.IsNullOrWhiteSpace(path)) return;
        try { if (File.Exists(path)) File.Delete(path); } catch { }
    }

    private async Task<(int ExitCode, string Output, string Error)> RunCaptureDetailedAsync(List<string> args, CancellationToken token)
    {
        var psi = MakeProcessInfo(args);
        using var process = new Process { StartInfo = psi };
        if (!process.Start()) throw new InvalidOperationException("Could not start analysis engine.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(token);
        var stderrTask = process.StandardError.ReadToEndAsync(token);
        await process.WaitForExitAsync(token);
        var output = await stdoutTask;
        var err = await stderrTask;
        if (process.ExitCode != 0 && !string.IsNullOrWhiteSpace(err)) AppendLog(err.Trim());
        return (process.ExitCode, output, err);
    }

    private List<AudioChoice> ParseAudioChoices'''
s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'RunMediaProbeAsync replacement failed: {n}')
s = s2

# Improve normal-probe failure handling: identify YouTube anti-bot verification instead of collapsing to a generic audio error.
old = '''            if (normalResult.ExitCode != 0 || string.IsNullOrWhiteSpace(normalResult.Output))
                throw new InvalidOperationException("Could not read video information.");
'''
new = '''            if (normalResult.ExitCode != 0 || string.IsNullOrWhiteSpace(normalResult.Output))
            {
                if (normalResult.Error.Contains("Sign in to confirm", StringComparison.OrdinalIgnoreCase) ||
                    normalResult.Error.Contains("not a bot", StringComparison.OrdinalIgnoreCase))
                {
                    mediaTitle.Text = "YouTube verification needed";
                    mediaMeta.Text = normalResult.BrowserSignedIn
                        ? "YouTube blocked this extractor request. Refresh the page and try again."
                        : "Sign in to YouTube above, then reopen this video to unlock audio tracks.";
                    audioChoices.Clear();
                    audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));
                    audioBox.Items.Clear();
                    audioBox.Items.Add("Original / default");
                    audioBox.SelectedIndex = 0;
                    audioBox.Enabled = true;
                    AppendLog("YouTube verification blocked metadata extraction • browserSignedIn=" + normalResult.BrowserSignedIn);
                    return;
                }
                throw new InvalidOperationException("Could not read video information.");
            }
'''
if old not in s:
    raise SystemExit('normal probe failure anchor not found')
s = s.replace(old, new, 1)

# Rich scan must never destroy a valid normal result if the secondary client fails or returns malformed JSON.
old = '''                if (richResult.ExitCode == 0 && !string.IsNullOrWhiteSpace(richResult.Output))
                {
                    using var richDoc = JsonDocument.Parse(richResult.Output);
                    var richChoices = ParseAudioChoices(richDoc.RootElement);
                    var richDubCount = richChoices.Count(x => x.Kind == AudioKind.Dubbed);
                    var richLanguages = richChoices.Where(x => !string.IsNullOrWhiteSpace(x.Language))
                                                   .Select(x => x.Language!)
                                                   .Distinct(StringComparer.OrdinalIgnoreCase)
                                                   .Count();

                    var normalScore = normalDubCount * 1000 + normalLanguages * 100 + normalChoices.Count;
                    var richScore = richDubCount * 1000 + richLanguages * 100 + richChoices.Count;
                    if (richScore > normalScore)
                    {
                        chosenOutput = richResult.Output;
                        usedRichScan = true;
                        AppendLog($"Rich Audio Scan found more tracks • languages={richLanguages} • Auto-Dub={richDubCount}");
                    }
                    else
                    {
                        AppendLog("Rich Audio Scan completed • no additional downloadable voices exposed");
                    }
                }
'''
new = '''                if (richResult.ExitCode == 0 && !string.IsNullOrWhiteSpace(richResult.Output))
                {
                    try
                    {
                        using var richDoc = JsonDocument.Parse(richResult.Output);
                        var richChoices = ParseAudioChoices(richDoc.RootElement);
                        var richDubCount = richChoices.Count(x => x.Kind == AudioKind.Dubbed);
                        var richLanguages = richChoices.Where(x => !string.IsNullOrWhiteSpace(x.Language))
                                                       .Select(x => x.Language!)
                                                       .Distinct(StringComparer.OrdinalIgnoreCase)
                                                       .Count();

                        var normalScore = normalDubCount * 1000 + normalLanguages * 100 + normalChoices.Count;
                        var richScore = richDubCount * 1000 + richLanguages * 100 + richChoices.Count;
                        if (richScore > normalScore)
                        {
                            chosenOutput = richResult.Output;
                            usedRichScan = true;
                            AppendLog($"Rich Audio Scan found more tracks • languages={richLanguages} • Auto-Dub={richDubCount}");
                        }
                        else
                        {
                            AppendLog("Rich Audio Scan completed • no additional downloadable voices exposed");
                        }
                    }
                    catch (Exception ex)
                    {
                        AppendLog("Rich Audio Scan parse note: " + ex.Message);
                    }
                }
                else if (!string.IsNullOrWhiteSpace(richResult.Error))
                {
                    AppendLog("Rich Audio Scan unavailable; keeping normal audio result.");
                }
'''
if old not in s:
    raise SystemExit('rich scan block anchor not found')
s = s.replace(old, new, 1)

# Pass the same live WebView2 session to the actual download process.
old = '''        try
        {
            var args = BuildDownloadArgs(url);
            var exit = await RunStreamingAsync(args, downloadCts.Token);
'''
new = '''        string? downloadCookieFile = null;
        try
        {
            var cookieSnapshot = await ExportYouTubeCookiesAsync(downloadCts.Token);
            downloadCookieFile = cookieSnapshot.Path;
            var args = BuildDownloadArgs(url, downloadCookieFile);
            var exit = await RunStreamingAsync(args, downloadCts.Token);
'''
if old not in s:
    raise SystemExit('DownloadAsync build args anchor not found')
s = s.replace(old, new, 1)

old = '''        finally
        {
            activeProcess = null;
            downloadCts?.Dispose();
'''
new = '''        finally
        {
            DeleteTempCookieFile(downloadCookieFile);
            activeProcess = null;
            downloadCts?.Dispose();
'''
if old not in s:
    raise SystemExit('DownloadAsync finally anchor not found')
s = s.replace(old, new, 1)

s = s.replace('private List<string> BuildDownloadArgs(string url)', 'private List<string> BuildDownloadArgs(string url, string? cookieFile = null)', 1)
old = '''        var args = CommonArgs(url, includeOutput: true);
        args.Add("--no-playlist");

        var selectedAudio ='''
new = '''        var args = CommonArgs(url, includeOutput: true);
        args.Add("--no-playlist");
        if (!string.IsNullOrWhiteSpace(cookieFile))
        {
            var cookieInsertAt = args.FindLastIndex(x => string.Equals(x, url, StringComparison.Ordinal));
            if (cookieInsertAt < 0) cookieInsertAt = args.Count;
            args.Insert(cookieInsertAt, "--cookies");
            args.Insert(cookieInsertAt + 1, cookieFile!);
        }

        var selectedAudio ='''
if old not in s:
    raise SystemExit('BuildDownloadArgs cookie anchor not found')
s = s.replace(old, new, 1)

s = s.replace('Text = "PC v1.1.2",', 'Text = "PC v1.1.3",', 1)
s = s.replace('AppendLog("Browser UI v1.1.2 starting • instant SPA analysis + Rich Audio Scan.");',
              'AppendLog("Browser UI v1.1.3 starting • WebView YouTube session bridge + Rich Audio Scan.");', 1)

p.write_text(s, encoding='utf-8')
print('Applied PC v1.1.3 WebView YouTube session bridge')
