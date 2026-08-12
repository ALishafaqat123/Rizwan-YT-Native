from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

pattern = re.compile(r'    private async Task<\(string\? Path, bool SignedIn\)> ExportYouTubeCookiesAsync\(CancellationToken token\)\n    \{.*?\n    \}\n\n    private static void DeleteTempCookieFile', re.S)
replacement = r'''    private async Task<(string? Path, bool SignedIn)> ExportYouTubeCookiesAsync(CancellationToken token)
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

    private static void DeleteTempCookieFile'''

s2, n = pattern.subn(lambda _m: replacement, s, count=1)
if n != 1:
    raise SystemExit(f'cookie escape repair failed: {n}')

p.write_text(s2, encoding='utf-8')
print('Repaired v1.1.3 cookie bridge escapes')
