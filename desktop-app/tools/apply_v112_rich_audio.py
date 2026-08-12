from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

pattern = re.compile(r'    private async Task AnalyzeMediaAsync\(string url\)\n    \{.*?\n    \}\n\n    private List<AudioChoice> ParseAudioChoices', re.S)
replacement = r'''    private async Task AnalyzeMediaAsync(string url)
    {
        analysisCts?.Cancel();
        analysisCts?.Dispose();
        analysisCts = new CancellationTokenSource();
        var token = analysisCts.Token;
        lastAnalyzedUrl = url;
        mediaTitle.Text = "Analyzing video…";
        mediaMeta.Text = "Checking available audio languages";
        audioBox.Enabled = false;

        try
        {
            var normalResult = await RunMediaProbeAsync(url, token, richAudio: false);
            if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;
            if (normalResult.ExitCode != 0 || string.IsNullOrWhiteSpace(normalResult.Output))
                throw new InvalidOperationException("Could not read video information.");

            var chosenOutput = normalResult.Output;
            var usedRichScan = false;
            List<AudioChoice> normalChoices;
            using (var normalDoc = JsonDocument.Parse(normalResult.Output))
                normalChoices = ParseAudioChoices(normalDoc.RootElement);

            var normalDubCount = normalChoices.Count(x => x.Kind == AudioKind.Dubbed);
            var normalLanguages = normalChoices.Where(x => !string.IsNullOrWhiteSpace(x.Language))
                                               .Select(x => x.Language!)
                                               .Distinct(StringComparer.OrdinalIgnoreCase)
                                               .Count();

            // Current logged-out YouTube defaults often expose only the original language.
            // When that happens, retry once with the yt-dlp-maintainer-recommended
            // web_embedded + default player-client combination to discover dubbed tracks.
            if (normalDubCount == 0 && normalLanguages <= 1)
            {
                mediaMeta.Text = "Checking YouTube Auto-Dub voices…";
                AppendLog("Only original audio found • starting Rich Audio Scan");
                var richResult = await RunMediaProbeAsync(url, token, richAudio: true);
                if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;

                if (richResult.ExitCode == 0 && !string.IsNullOrWhiteSpace(richResult.Output))
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
            }

            using var doc = JsonDocument.Parse(chosenOutput);
            var root = doc.RootElement;
            var title = JsonString(root, "title") ?? "YouTube video";
            var uploader = JsonString(root, "uploader") ?? JsonString(root, "channel") ?? string.Empty;
            var duration = JsonDouble(root, "duration");
            var parsedChoices = ParseAudioChoices(root);

            mediaTitle.Text = title;
            var parts = new List<string>();
            if (duration > 0) parts.Add(FormatDuration(duration));
            if (!string.IsNullOrWhiteSpace(uploader)) parts.Add(uploader);
            var dubCount = parsedChoices.Count(x => x.Kind == AudioKind.Dubbed);
            if (dubCount > 0) parts.Add(dubCount + " Auto-Dub " + (dubCount == 1 ? "voice" : "voices"));
            else if (usedRichScan) parts.Add("Rich audio scan");
            mediaMeta.Text = parts.Count == 0 ? "Ready to download" : string.Join("  •  ", parts);

            audioChoices.Clear();
            audioChoices.AddRange(parsedChoices);
            audioBox.Items.Clear();
            foreach (var choice in audioChoices) audioBox.Items.Add(choice.Label);
            if (audioBox.Items.Count == 0)
            {
                audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));
                audioBox.Items.Add("Original / default");
            }
            audioBox.SelectedIndex = 0;
            audioBox.Enabled = true;
            AppendLog("Analyze complete: " + title + (dubCount > 0 ? $" • Auto-Dub tracks={dubCount}" : string.Empty));
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            if (token.IsCancellationRequested || !string.Equals(currentMediaUrl, url, StringComparison.Ordinal)) return;
            mediaTitle.Text = "Video ready";
            mediaMeta.Text = "Audio language details unavailable — default audio will be used";
            audioChoices.Clear();
            audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));
            audioBox.Items.Clear();
            audioBox.Items.Add("Original / default");
            audioBox.SelectedIndex = 0;
            audioBox.Enabled = true;
            AppendLog("Analyze note: " + ex.Message);
        }
    }

    private async Task<(int ExitCode, string Output)> RunMediaProbeAsync(string url, CancellationToken token, bool richAudio)
    {
        var args = CommonArgs(url, includeOutput: false);
        if (args.Count > 0 && string.Equals(args[^1], url, StringComparison.Ordinal))
            args.RemoveAt(args.Count - 1);

        args.Add("--no-playlist");
        args.Add("--skip-download");
        args.Add("--dump-single-json");
        if (richAudio)
        {
            args.Add("--extractor-args");
            args.Add("youtube:player_client=web_embedded,default");
        }
        args.Add(url);
        return await RunCaptureAsync(args, token);
    }

    private List<AudioChoice> ParseAudioChoices'''

s2, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'AnalyzeMediaAsync replacement failed: {n}')
s = s2

old = '''        var selectedAudio = audioBox.SelectedIndex >= 0 && audioBox.SelectedIndex < audioChoices.Count ? audioChoices[audioBox.SelectedIndex] : null;\n        var audioId = selectedAudio?.FormatId;\n        string format;\n'''
new = '''        var selectedAudio = audioBox.SelectedIndex >= 0 && audioBox.SelectedIndex < audioChoices.Count ? audioChoices[audioBox.SelectedIndex] : null;\n        var audioId = selectedAudio?.FormatId;\n\n        // A format ID discovered by Rich Audio Scan must be extracted with the same\n        // player-client set; `default` remains included as the compatibility fallback.\n        if (!string.IsNullOrWhiteSpace(audioId) && IsDownloadableMediaPage(url))\n        {\n            var insertAt = args.FindLastIndex(x => string.Equals(x, url, StringComparison.Ordinal));\n            if (insertAt < 0) insertAt = args.Count;\n            args.Insert(insertAt, "--extractor-args");\n            args.Insert(insertAt + 1, "youtube:player_client=web_embedded,default");\n        }\n\n        string format;\n'''
if old not in s:
    raise SystemExit('BuildDownloadArgs audio anchor not found')
s = s.replace(old, new, 1)

s = s.replace('Text = "PC v1.1.1",', 'Text = "PC v1.1.2",', 1)
s = s.replace('AppendLog("Browser UI v1.1.1 starting • instant SPA video analysis.");',
              'AppendLog("Browser UI v1.1.2 starting • instant SPA analysis + Rich Audio Scan.");', 1)

p.write_text(s, encoding='utf-8')
print('Applied PC v1.1.2 Rich Audio Scan')
