from pathlib import Path

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

old = '''        browser.NavigationStarting += (_, _) => mediaMeta.Text = "Loading…";\n        browser.SourceChanged += (_, _) =>\n        {\n            if (browser.Source != null) addressBox.Text = browser.Source.ToString();\n        };\n        browser.NavigationCompleted += async (_, _) => await HandleBrowserNavigationAsync();\n'''
new = '''        browser.NavigationStarting += (_, e) =>\n        {\n            if (!string.IsNullOrWhiteSpace(e.Uri) && IsDownloadableMediaPage(e.Uri))\n                ResetMediaTrayForIncomingVideo(e.Uri);\n        };\n        browser.SourceChanged += async (_, _) =>\n        {\n            if (browser.Source == null) return;\n            var sourceUrl = browser.Source.ToString();\n            addressBox.Text = sourceUrl;\n            // YouTube is a single-page app: clicking another video often changes the URL\n            // without a full NavigationCompleted event. Analyze immediately on SourceChanged.\n            await HandleBrowserNavigationAsync(sourceUrl);\n        };\n        browser.NavigationCompleted += async (_, _) =>\n        {\n            if (browser.Source != null) await HandleBrowserNavigationAsync(browser.Source.ToString());\n        };\n'''
if old not in s:
    raise SystemExit('browser navigation event anchor not found')
s = s.replace(old, new, 1)

old_handler = '''    private async Task HandleBrowserNavigationAsync()\n    {\n        if (browser.Source == null) return;\n        var url = browser.Source.ToString();\n        addressBox.Text = url;\n\n        if (!IsDownloadableMediaPage(url))\n        {\n            currentMediaUrl = string.Empty;\n            downloadTray.Visible = false;\n            return;\n        }\n\n        currentMediaUrl = url;\n        downloadTray.Visible = true;\n        downloadTray.BringToFront();\n        mediaTitle.Text = "Video detected";\n        mediaMeta.Text = "Reading title, quality and audio tracks…";\n        if (!string.Equals(lastAnalyzedUrl, url, StringComparison.Ordinal))\n            await AnalyzeMediaAsync(url);\n    }\n'''
new_handler = '''    private async Task HandleBrowserNavigationAsync(string url)\n    {\n        addressBox.Text = url;\n\n        if (!IsDownloadableMediaPage(url))\n        {\n            analysisCts?.Cancel();\n            currentMediaUrl = string.Empty;\n            lastAnalyzedUrl = string.Empty;\n            downloadTray.Visible = false;\n            return;\n        }\n\n        var changedVideo = !string.Equals(currentMediaUrl, url, StringComparison.Ordinal);\n        currentMediaUrl = url;\n        downloadTray.Visible = true;\n        downloadTray.BringToFront();\n\n        if (changedVideo)\n            ResetMediaTrayForIncomingVideo(url);\n\n        if (!string.Equals(lastAnalyzedUrl, url, StringComparison.Ordinal))\n            await AnalyzeMediaAsync(url);\n    }\n\n    private void ResetMediaTrayForIncomingVideo(string url)\n    {\n        // Cancel stale metadata immediately so the previous video's title/audio can never\n        // remain visible while the newly opened YouTube video is loading.\n        analysisCts?.Cancel();\n        currentMediaUrl = url;\n        lastAnalyzedUrl = string.Empty;\n        downloadTray.Visible = true;\n        downloadTray.BringToFront();\n        mediaTitle.Text = "Analyzing new video…";\n        mediaMeta.Text = "Reading title, quality and audio tracks…";\n        audioChoices.Clear();\n        audioBox.Items.Clear();\n        audioBox.Items.Add("Loading audio…");\n        audioBox.SelectedIndex = 0;\n        audioBox.Enabled = false;\n    }\n'''
if old_handler not in s:
    raise SystemExit('HandleBrowserNavigationAsync anchor not found')
s = s.replace(old_handler, new_handler, 1)

# Guard every completed analysis against a late result from a previously-opened video.
old_guard = '''            var result = await RunCaptureAsync(args, token);\n            if (token.IsCancellationRequested) return;\n            if (result.ExitCode != 0 || string.IsNullOrWhiteSpace(result.Output)) throw new InvalidOperationException("Could not read video information.");\n'''
new_guard = '''            var result = await RunCaptureAsync(args, token);\n            if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;\n            if (result.ExitCode != 0 || string.IsNullOrWhiteSpace(result.Output)) throw new InvalidOperationException("Could not read video information.");\n'''
if old_guard not in s:
    raise SystemExit('analysis result guard anchor not found')
s = s.replace(old_guard, new_guard, 1)

# Guard the fallback UI too; a failed old request must not overwrite a newer video.
old_catch = '''        catch (Exception ex)\n        {\n            if (token.IsCancellationRequested) return;\n            mediaTitle.Text = "Video ready";\n'''
new_catch = '''        catch (Exception ex)\n        {\n            if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;\n            mediaTitle.Text = "Video ready";\n'''
if old_catch not in s:
    raise SystemExit('analysis catch guard anchor not found')
s = s.replace(old_catch, new_catch, 1)

s = s.replace('Text = "PC v1.1",', 'Text = "PC v1.1.1",', 1)
s = s.replace('AppendLog("Browser UI v1.1 starting.");', 'AppendLog("Browser UI v1.1.1 starting • instant SPA video analysis.");', 1)

p.write_text(s, encoding='utf-8')
print('Applied PC v1.1.1 instant navigation analysis fix')
