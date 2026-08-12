from pathlib import Path
import re

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

# Keep v1.1.3 audio/session behavior intact and add a dynamic quality model on top.
old = '    private readonly List<AudioChoice> audioChoices = new();\n'
new = old + '    private readonly List<QualityChoice> qualityChoices = new();\n'
if old not in s:
    raise SystemExit('quality field anchor not found')
s = s.replace(old, new, 1)

old = '''        ConfigurePicker(qualityBox);\n        qualityBox.Items.AddRange(new object[] { "720p HD", "1080p Full HD", "360p MP4", "Best available", "Audio only" });\n        qualityBox.SelectedIndex = 0;\n        tray.Controls.Add(MakePickerHost("QUALITY", qualityBox), 1, 0);\n'''
new = '''        ConfigurePicker(qualityBox);\n        qualityBox.Items.Add("Waiting for video…");\n        qualityBox.SelectedIndex = 0;\n        qualityBox.Enabled = false;\n        tray.Controls.Add(MakePickerHost("QUALITY", qualityBox), 1, 0);\n'''
if old not in s:
    raise SystemExit('quality picker anchor not found')
s = s.replace(old, new, 1)

old = '''        mediaMeta.Text = "Checking available audio languages";\n        audioBox.Enabled = false;\n'''
new = '''        mediaMeta.Text = "Checking available qualities and audio languages";\n        qualityBox.Enabled = false;\n        audioBox.Enabled = false;\n'''
if old not in s:
    raise SystemExit('analysis start anchor not found')
s = s.replace(old, new, 1)

old = '''            var parsedChoices = ParseAudioChoices(root);\n\n            mediaTitle.Text = title;\n'''
new = '''            var parsedChoices = ParseAudioChoices(root);\n            var parsedQualities = ParseQualityChoices(root);\n\n            mediaTitle.Text = title;\n'''
if old not in s:
    raise SystemExit('parsed choices anchor not found')
s = s.replace(old, new, 1)

old = '''            mediaMeta.Text = parts.Count == 0 ? "Ready to download" : string.Join("  •  ", parts);\n\n            audioChoices.Clear();\n'''
new = '''            mediaMeta.Text = parts.Count == 0 ? "Ready to download" : string.Join("  •  ", parts);\n\n            qualityChoices.Clear();\n            qualityChoices.AddRange(parsedQualities);\n            qualityBox.Items.Clear();\n            foreach (var choice in qualityChoices) qualityBox.Items.Add(choice.Label);\n            if (qualityChoices.Count == 0)\n            {\n                qualityChoices.Add(new QualityChoice("720p HD • Best compatibility", 720, false, false, 0, 30, "H.264"));\n                qualityChoices.Add(new QualityChoice("Audio only", 0, true, false, 0, 0, string.Empty));\n                qualityBox.Items.Add(qualityChoices[0].Label);\n                qualityBox.Items.Add(qualityChoices[1].Label);\n            }\n            var preferredQuality = qualityChoices.FindIndex(x => !x.AudioOnly && !x.BestAvailable && x.Height == 720);\n            if (preferredQuality < 0) preferredQuality = qualityChoices.FindIndex(x => !x.AudioOnly && !x.BestAvailable && x.Height == 1080);\n            if (preferredQuality < 0) preferredQuality = qualityChoices.FindIndex(x => !x.AudioOnly);\n            qualityBox.SelectedIndex = preferredQuality >= 0 ? preferredQuality : 0;\n            qualityBox.Enabled = true;\n\n            audioChoices.Clear();\n'''
if old not in s:
    raise SystemExit('quality fill anchor not found')
s = s.replace(old, new, 1)

# If metadata analysis fails, preserve a safe quality fallback rather than leaving the picker disabled.
old = '''            audioChoices.Clear();\n            audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));\n            audioBox.Items.Clear();\n'''
new = '''            qualityChoices.Clear();\n            qualityChoices.Add(new QualityChoice("720p HD • Best compatibility", 720, false, false, 0, 30, "H.264"));\n            qualityChoices.Add(new QualityChoice("360p • Small file", 360, false, false, 0, 30, "H.264"));\n            qualityChoices.Add(new QualityChoice("Best available", 0, false, true, 0, 0, string.Empty));\n            qualityChoices.Add(new QualityChoice("Audio only", 0, true, false, 0, 0, string.Empty));\n            qualityBox.Items.Clear();\n            foreach (var q in qualityChoices) qualityBox.Items.Add(q.Label);\n            qualityBox.SelectedIndex = 0;\n            qualityBox.Enabled = true;\n\n            audioChoices.Clear();\n            audioChoices.Add(new AudioChoice("Original / default", null, null, AudioKind.Default, 0, 0));\n            audioBox.Items.Clear();\n'''
# Two catch/fallback blocks can exist after v1.1.3. Updating the first safe fallback is sufficient;
# the verification-specific block returns earlier and already has valid metadata state.
if old not in s:
    raise SystemExit('analysis fallback anchor not found')
s = s.replace(old, new, 1)

# Add quality parsing immediately before the existing audio parser.
anchor = '    private List<AudioChoice> ParseAudioChoices(JsonElement root)\n'
if anchor not in s:
    raise SystemExit('ParseAudioChoices anchor not found')
quality_parser = r'''    private List<QualityChoice> ParseQualityChoices(JsonElement root)
    {
        var result = new List<QualityChoice>();
        if (!root.TryGetProperty("formats", out var formats) || formats.ValueKind != JsonValueKind.Array)
            return result;

        var candidates = new List<(int Height, double Fps, string Codec, string Ext, double Bytes)>();
        foreach (var f in formats.EnumerateArray())
        {
            var vcodec = JsonString(f, "vcodec") ?? string.Empty;
            if (string.IsNullOrWhiteSpace(vcodec) || vcodec.Equals("none", StringComparison.OrdinalIgnoreCase)) continue;
            var height = (int)Math.Round(JsonDouble(f, "height"));
            if (height <= 0) continue;
            var fps = JsonDouble(f, "fps");
            var ext = JsonString(f, "ext") ?? string.Empty;
            var bytes = JsonDouble(f, "filesize");
            if (bytes <= 0) bytes = JsonDouble(f, "filesize_approx");
            candidates.Add((height, fps, CodecFamily(vcodec), ext, bytes));
        }

        foreach (var g in candidates.GroupBy(x => x.Height).OrderByDescending(g => g.Key))
        {
            var best = g.OrderByDescending(x => x.Codec == "H.264")
                        .ThenByDescending(x => x.Ext.Equals("mp4", StringComparison.OrdinalIgnoreCase))
                        .ThenByDescending(x => x.Fps)
                        .ThenByDescending(x => x.Bytes)
                        .First();
            var fps = g.Max(x => x.Fps);
            var bytes = g.Max(x => x.Bytes);
            var estimated = bytes > 0 ? bytes * 1.08 : 0; // small allowance for merged audio/container overhead
            var label = QualityLabel(g.Key, fps, best.Codec, estimated);
            result.Add(new QualityChoice(label, g.Key, false, false, estimated, fps, best.Codec));
        }

        if (result.Count > 0)
            result.Add(new QualityChoice("Best available • Highest quality", 0, false, true, 0, 0, string.Empty));
        result.Add(new QualityChoice("Audio only", 0, true, false, 0, 0, string.Empty));
        return result;
    }

    private static string QualityLabel(int height, double fps, string codec, double estimatedBytes)
    {
        var parts = new List<string> { height + "p" };
        if (height >= 2160) parts.Add("4K");
        else if (height >= 1440) parts.Add("2K");
        else if (height >= 1080) parts.Add("Full HD");
        else if (height >= 720) parts.Add("HD");
        if (fps >= 50) parts.Add(((int)Math.Round(fps)) + "fps");
        if (codec == "H.264") parts.Add("Best compatibility");
        else if (!string.IsNullOrWhiteSpace(codec)) parts.Add(codec);
        if (estimatedBytes > 0) parts.Add("≈" + FormatBytes(estimatedBytes));
        return string.Join(" • ", parts);
    }

    private static string CodecFamily(string codec)
    {
        if (codec.StartsWith("avc1", StringComparison.OrdinalIgnoreCase) || codec.Contains("h264", StringComparison.OrdinalIgnoreCase)) return "H.264";
        if (codec.StartsWith("vp09", StringComparison.OrdinalIgnoreCase) || codec.Contains("vp9", StringComparison.OrdinalIgnoreCase)) return "VP9";
        if (codec.StartsWith("av01", StringComparison.OrdinalIgnoreCase) || codec.Contains("av1", StringComparison.OrdinalIgnoreCase)) return "AV1";
        return string.Empty;
    }

    private static string FormatBytes(double bytes)
    {
        if (bytes >= 1024d * 1024 * 1024) return (bytes / (1024d * 1024 * 1024)).ToString("0.0", CultureInfo.InvariantCulture) + " GB";
        return Math.Max(1, bytes / (1024d * 1024)).ToString("0", CultureInfo.InvariantCulture) + " MB";
    }

'''
s = s.replace(anchor, quality_parser + anchor, 1)

# Replace fixed-index quality selection with the dynamic quality model.
pattern = re.compile(r'''        var selectedAudio = audioBox\.SelectedIndex >= 0 && audioBox\.SelectedIndex < audioChoices\.Count \? audioChoices\[audioBox\.SelectedIndex\] : null;\n        var audioId = selectedAudio\?\.FormatId;\n(?P<middle>.*?)        args\.Add\("-f"\);''', re.S)
m = pattern.search(s)
if not m:
    raise SystemExit('BuildDownloadArgs dynamic quality block not found')
middle = m.group('middle')
# Preserve the v1.1.2/v1.1.3 Rich Audio extractor-args insertion that lives between audioId and string format.
preserve = ''
marker = '        string format;\n'
if marker in middle:
    preserve = middle.split(marker, 1)[0]
replacement = '''        var selectedAudio = audioBox.SelectedIndex >= 0 && audioBox.SelectedIndex < audioChoices.Count ? audioChoices[audioBox.SelectedIndex] : null;\n        var audioId = selectedAudio?.FormatId;\n''' + preserve + '''        var selectedQuality = qualityBox.SelectedIndex >= 0 && qualityBox.SelectedIndex < qualityChoices.Count\n            ? qualityChoices[qualityBox.SelectedIndex]\n            : new QualityChoice("720p HD • Best compatibility", 720, false, false, 0, 30, "H.264");\n\n        string format;\n        if (selectedQuality.AudioOnly)\n        {\n            format = !string.IsNullOrWhiteSpace(audioId) ? audioId : "bestaudio[ext=m4a]/bestaudio";\n        }\n        else\n        {\n            var cap = selectedQuality.BestAvailable ? string.Empty : $"[height<={Math.Max(144, selectedQuality.Height)}]";\n            if (!string.IsNullOrWhiteSpace(audioId))\n            {\n                format = $"bestvideo{cap}[ext=mp4][vcodec^=avc1]+{audioId}/bestvideo{cap}[ext=mp4]+{audioId}/bestvideo{cap}+{audioId}";\n            }\n            else\n            {\n                format = $"bestvideo{cap}[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/bestvideo{cap}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{cap}+bestaudio/best{cap}";\n            }\n        }\n\n        args.Add("-f");'''
s = s[:m.start()] + replacement + s[m.end():]

# Merge to MP4 for video modes only; index no longer represents Audio only.
s = s.replace('        if (qualityBox.SelectedIndex != 4)\n', '        if (!(qualityBox.SelectedIndex >= 0 && qualityBox.SelectedIndex < qualityChoices.Count && qualityChoices[qualityBox.SelectedIndex].AudioOnly))\n', 1)

# Preview identity; stable v1.1.3 remains untouched on v2-ui-rebuild.
s = s.replace('Text = "PC v1.1.3",', 'Text = "PC v1.2 Preview 1",', 1)
s = s.replace('AppendLog("Browser UI v1.1.3 starting • WebView YouTube session bridge + Rich Audio Scan.");',
              'AppendLog("Browser UI v1.2 Preview 1 starting • Smart Quality + v1.1.3 audio/session foundation.");', 1)

record_anchor = '    private sealed record AudioChoice(string Label, string? FormatId, string? Language, AudioKind Kind, double Score, double LanguagePreference);\n'
if record_anchor not in s:
    raise SystemExit('AudioChoice record anchor not found')
s = s.replace(record_anchor, '    private sealed record QualityChoice(string Label, int Height, bool AudioOnly, bool BestAvailable, double EstimatedBytes, double Fps, string Codec);\n\n' + record_anchor, 1)

p.write_text(s, encoding='utf-8')

# Give the preview installer its own identity so it cannot be mistaken for the stable setup file.
iss = Path('desktop-app/installer.iss')
i = iss.read_text(encoding='utf-8')
i = i.replace('#define MyAppVersion "1.1.3"', '#define MyAppVersion "1.2.0"', 1)
i = i.replace('OutputBaseFilename=Rizwan-Media-Saver-PC-v1.1.3-Setup', 'OutputBaseFilename=Rizwan-Media-Saver-PC-v1.2.0-Preview1-Setup', 1)
iss.write_text(i, encoding='utf-8')

print('Applied PC v1.2 Preview 1 Smart Quality foundation')
