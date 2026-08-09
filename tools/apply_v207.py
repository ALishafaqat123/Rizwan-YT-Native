from pathlib import Path

p = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = p.read_text()
s = s.replace('status.setMaxLines(3);', 'status.setMaxLines(5);')

start = s.index('        // FAST PATH: if YouTube exposes the requested quality as one MP4 that already')
end = s.index('        String videoPid = "rms-hd-video-"', start)

new_fast = r'''        // V2.0.7 NO-WASTED-WAIT FAST PATH:
        // Never perform a network metadata probe after the user has pressed Download.
        // Use a ready-made combined MP4 only when metadata is already cached by the
        // background options sheet. Otherwise start the proven HD path immediately.
        long hdStarted = System.currentTimeMillis();
        long fastCheckStarted = System.currentTimeMillis();
        VideoFormat combined = null;
        String combinedExtractorArgs = null;
        String combinedSource = "Cached default";
        try {
            String infoKey = task.id == null || task.id.isEmpty() ? task.url : task.id;
            VideoInfo cachedInfo = infoCache.get(infoKey);
            if (cachedInfo != null) combined = findExactCombinedFormat(cachedInfo, task.quality);
            if (combined == null && task.quality == 720) {
                VideoInfo cachedAndroid = combinedAndroidInfoCache.get(infoKey);
                VideoFormat androidCombined = findExactCombinedFormat(cachedAndroid, 720);
                if (androidCombined != null) {
                    combined = androidCombined;
                    combinedExtractorArgs = "youtube:player_client=android;formats=missing_pot";
                    combinedSource = "Cached Android progressive";
                }
            }
        } catch (Exception ignored) { }
        long fastCheckMs = Math.max(0L, System.currentTimeMillis() - fastCheckStarted);

        if (combined != null && combined.getFormatId() != null && !combined.getFormatId().trim().isEmpty()) {
            if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");
            File fastPart = new File(finalFile.getAbsolutePath() + ".part");
            if (fastPart.exists()) fastPart.delete();
            String fastPid = "rms-fast-combined-" + safeId + "-" + task.quality;
            processId = fastPid;
            final String fastSource = combinedSource;
            final String fastFormatId = combined.getFormatId();
            YoutubeDLRequest fastReq = combinedExtractorArgs == null
                    ? commonRequest(task.url)
                    : commonRequest(task.url, combinedExtractorArgs);
            fastReq.addOption("-f", fastFormatId);
            fastReq.addOption("-o", finalFile.getAbsolutePath());
            try {
                long readyDownloadStarted = System.currentTimeMillis();
                YoutubeDL.getInstance().execute(fastReq, fastPid,
                        progressCallback(1, 99, "Downloading ready-made " + task.quality + "p MP4"));
                long readyDownloadMs = Math.max(0L, System.currentTimeMillis() - readyDownloadStarted);
                processId = null;
                if (cancelCurrent) throw new Exception("Canceled");
                long fastVerifyStarted = System.currentTimeMillis();
                if (!finalFile.isFile() || finalFile.length() <= 0 ||
                        !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
                    throw new Exception("Combined MP4 verification failed.");
                }
                long fastVerifyMs = Math.max(0L, System.currentTimeMillis() - fastVerifyStarted);
                long cleanupStartedFast = System.currentTimeMillis();
                deleteWorkFiles(workDir);
                long cleanupFastMs = Math.max(0L, System.currentTimeMillis() - cleanupStartedFast);
                long totalFastMs = Math.max(0L, System.currentTimeMillis() - hdStarted);
                lastFinalizeReport = fastSource + " combined • FastCheck " + formatElapsedMs(fastCheckMs) +
                        " • Download " + formatElapsedMs(readyDownloadMs) +
                        " • Mux 0 ms • Verify " + formatElapsedMs(fastVerifyMs) +
                        " • Cleanup " + formatElapsedMs(cleanupFastMs) +
                        " • Total " + formatElapsedMs(totalFastMs);
                task.stage = "Completed • no joining needed";
                task.itemProgress = 100;
                final long finalBytes = finalFile.length();
                final String fastReport = lastFinalizeReport;
                runOnUiThread(() -> {
                    progress.setProgress(overallProgress(task, 100));
                    activeTitle.setText(itemPrefix(task) + "Completed • no joining needed");
                    activeMeta.setText(task.title + " • " + formatBytes(finalBytes));
                    setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\n" + fastReport : fastReport);
                    Toast.makeText(this, "No joining needed", Toast.LENGTH_SHORT).show();
                    refreshQueueUi();
                });
                return;
            } catch (Exception fastError) {
                processId = null;
                if (cancelCurrent) throw fastError;
                if (finalFile.exists()) finalFile.delete();
                if (fastPart.exists()) fastPart.delete();
            }
        }

'''
s = s[:start] + new_fast + s[end:]

old_video = '''        YoutubeDL.getInstance().execute(videoReq, videoPid,\n                progressCallback(2, 78, "Downloading " + task.quality + "p H.264 video"));\n        processId = null;'''
new_video = '''        long videoDownloadStarted = System.currentTimeMillis();\n        YoutubeDL.getInstance().execute(videoReq, videoPid,\n                progressCallback(2, 78, "Downloading " + task.quality + "p H.264 video"));\n        long videoDownloadMs = Math.max(0L, System.currentTimeMillis() - videoDownloadStarted);\n        processId = null;'''
if old_video not in s:
    raise SystemExit('video execute block not found')
s = s.replace(old_video, new_video, 1)

old_audio = '''        YoutubeDL.getInstance().execute(audioReq, audioPid,\n                progressCallback(78, 94, "Downloading AAC audio"));\n        processId = null;'''
new_audio = '''        long audioDownloadStarted = System.currentTimeMillis();\n        YoutubeDL.getInstance().execute(audioReq, audioPid,\n                progressCallback(78, 94, "Downloading AAC audio"));\n        long audioDownloadMs = Math.max(0L, System.currentTimeMillis() - audioDownloadStarted);\n        processId = null;'''
if old_audio not in s:
    raise SystemExit('audio execute block not found')
s = s.replace(old_audio, new_audio, 1)

old_report = '''        long cleanupMs = Math.max(0L, System.currentTimeMillis() - cleanupStarted);\n        long finalizeMs = Math.max(0L, System.currentTimeMillis() - finalizeStarted);\n\n        lastFinalizeReport = muxEngine + " • Mux " + formatElapsedMs(muxMs) +\n                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n                " • Save " + formatElapsedMs(saveMs) +\n                " • Cleanup " + formatElapsedMs(cleanupMs) +\n                " • Total " + formatElapsedMs(finalizeMs);\n\n        task.stage = "Finalize " + formatElapsedMs(finalizeMs);'''
new_report = '''        long cleanupMs = Math.max(0L, System.currentTimeMillis() - cleanupStarted);\n        long finalizeMs = Math.max(0L, System.currentTimeMillis() - finalizeStarted);\n        long totalHdMs = Math.max(0L, System.currentTimeMillis() - hdStarted);\n\n        lastFinalizeReport = "FastCheck " + formatElapsedMs(fastCheckMs) +\n                " • Video " + formatElapsedMs(videoDownloadMs) +\n                " • Audio " + formatElapsedMs(audioDownloadMs) + "\\n" +\n                muxEngine + " • Mux " + formatElapsedMs(muxMs) +\n                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n                " • Save " + formatElapsedMs(saveMs) +\n                " • Cleanup " + formatElapsedMs(cleanupMs) +\n                " • Total " + formatElapsedMs(totalHdMs);\n\n        task.stage = "Finalize " + formatElapsedMs(finalizeMs);'''
if old_report not in s:
    raise SystemExit('final report block not found')
s = s.replace(old_report, new_report, 1)
p.write_text(s)

g = Path('app/build.gradle')
b = g.read_text()
b = b.replace('versionCode 206', 'versionCode 207')
b = b.replace("versionName '2.0.6-no-mux-hd-preview'", "versionName '2.0.7-no-wasted-wait-timing-preview'")
g.write_text(b)

print('V2.0.7 patch applied')
