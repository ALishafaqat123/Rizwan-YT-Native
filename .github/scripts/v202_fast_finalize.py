from pathlib import Path

path = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
s = path.read_text(encoding='utf-8')

# 1) Media3 fast mux import
needle = 'import android.media.MediaMuxer;\n'
if 'import androidx.media3.muxer.MediaMuxerCompat;' not in s:
    assert needle in s
    s = s.replace(needle, needle + 'import androidx.media3.muxer.MediaMuxerCompat;\n', 1)

# 2) Replace the HD download path with a progressive-fast-path + timed mux fallback.
start = s.index('    private void downloadHdBlocking(DownloadTask task, File outDir) throws Exception {')
end = s.index('    private YoutubeDLRequest commonRequest(String url) {', start)
new_hd = r'''    private void downloadHdBlocking(DownloadTask task, File outDir) throws Exception {
        String safeId = sanitize(task.id == null ? Integer.toHexString(task.url.hashCode()) : task.id);
        File workRoot = new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "hd-work");
        File workDir = new File(workRoot, safeId + "-" + task.quality + "p");
        if (!workDir.exists()) workDir.mkdirs();
        File finalFile = new File(outDir, safeFileTitle(task.title) + " [" + safeId + "] [" + task.quality + "p].mp4");

        // FAST PATH: if YouTube exposes the requested quality as one MP4 that already
        // contains H.264 video + AAC audio, download that exact format and skip muxing.
        // This is intentionally exact-height only; we never silently downgrade 720p to 360p.
        VideoFormat combined = null;
        try {
            task.stage = "Checking fast " + task.quality + "p stream";
            task.itemProgress = 1;
            runOnUiThread(() -> {
                activeTitle.setText(itemPrefix(task) + "Checking fast " + task.quality + "p stream");
                setStatus(task.playlistBatch ? playlistStatusLine(task, 1) :
                        "Looking for a ready-made MP4 with video + audio…");
                refreshQueueUi();
            });
            VideoInfo info = getSingleInfo(task.url);
            combined = findExactCombinedFormat(info, task.quality);
        } catch (Exception ignored) { }

        if (combined != null && combined.getFormatId() != null && !combined.getFormatId().trim().isEmpty()) {
            if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");
            File fastPart = new File(finalFile.getAbsolutePath() + ".part");
            if (fastPart.exists()) fastPart.delete();
            String fastPid = "rms-fast-combined-" + safeId + "-" + task.quality;
            processId = fastPid;
            YoutubeDLRequest fastReq = commonRequest(task.url);
            fastReq.addOption("-f", combined.getFormatId());
            fastReq.addOption("-o", finalFile.getAbsolutePath());
            try {
                YoutubeDL.getInstance().execute(fastReq, fastPid,
                        progressCallback(1, 99, "Downloading ready-made " + task.quality + "p MP4"));
                processId = null;
                if (cancelCurrent) throw new Exception("Canceled");
                if (!finalFile.isFile() || finalFile.length() <= 0 ||
                        !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
                    throw new Exception("Combined MP4 verification failed.");
                }
                deleteWorkFiles(workDir);
                task.stage = "Completed • no joining needed";
                task.itemProgress = 100;
                final long finalBytes = finalFile.length();
                runOnUiThread(() -> {
                    progress.setProgress(overallProgress(task, 100));
                    activeTitle.setText(itemPrefix(task) + "Completed • no joining needed");
                    activeMeta.setText(task.title + " • " + formatBytes(finalBytes));
                    setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\nNo joining needed." :
                            "Ready-made video+audio MP4 used • no joining needed.");
                    refreshQueueUi();
                });
                return;
            } catch (Exception fastError) {
                processId = null;
                if (cancelCurrent) throw fastError;
                if (finalFile.exists()) finalFile.delete();
                if (fastPart.exists()) fastPart.delete();
                // Continue with the proven separate-stream path below.
            }
        }

        String videoPid = "rms-hd-video-" + safeId + "-" + task.quality;
        processId = videoPid;
        YoutubeDLRequest videoReq = commonRequest(task.url);
        videoReq.addOption("-f", "bestvideo[height<=" + task.quality + "][ext=mp4][vcodec^=avc1]");
        videoReq.addOption("-o", new File(workDir, "video.%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(videoReq, videoPid,
                progressCallback(2, 78, "Downloading " + task.quality + "p H.264 video"));
        processId = null;
        if (cancelCurrent) throw new Exception("Canceled");
        File videoFile = findCompleteFile(workDir, "video.");
        if (videoFile == null || !hasVideoTrack(videoFile.getAbsolutePath())) throw new Exception("HD video stream was not created correctly.");

        String audioPid = "rms-hd-audio-" + safeId + "-" + task.quality;
        processId = audioPid;
        YoutubeDLRequest audioReq = commonRequest(task.url);
        audioReq.addOption("-f", "bestaudio[ext=m4a][acodec^=mp4a]");
        audioReq.addOption("-o", new File(workDir, "audio.%(ext)s").getAbsolutePath());
        YoutubeDL.getInstance().execute(audioReq, audioPid,
                progressCallback(78, 94, "Downloading AAC audio"));
        processId = null;
        if (cancelCurrent) throw new Exception("Canceled");
        File audioFile = findCompleteFile(workDir, "audio.");
        if (audioFile == null || !hasAudioTrack(audioFile.getAbsolutePath())) throw new Exception("AAC audio stream was not created correctly.");

        task.stage = "Fast joining video + audio";
        task.itemProgress = 95;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 95));
            activeTitle.setText(itemPrefix(task) + "Fast joining video + audio");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 95) :
                    "Joining with the fast MP4 muxer…");
            refreshQueueUi();
        });

        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");
        long muxStarted = System.currentTimeMillis();
        boolean media3Used = false;
        Exception media3Error = null;
        try {
            muxWithMedia3Compat(videoFile, audioFile, finalFile);
            if (!finalFile.isFile() || finalFile.length() <= 0 ||
                    !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
                throw new Exception("Media3 fast mux verification failed.");
            }
            media3Used = true;
        } catch (Exception fastMuxError) {
            media3Error = fastMuxError;
            if (finalFile.exists()) finalFile.delete();
            muxWithAndroid(videoFile, audioFile, finalFile);
            if (!finalFile.isFile() || finalFile.length() <= 0 ||
                    !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
                if (finalFile.exists()) finalFile.delete();
                throw new Exception("Final saved MP4 verification failed after fallback.", fastMuxError);
            }
        }
        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);
        String muxName = media3Used ? "Media3 fast mux" : "Android fallback mux";
        String muxTime = formatElapsedMs(muxMs);

        deleteWorkFiles(workDir);
        task.stage = "Joined in " + muxTime;
        task.itemProgress = 100;
        final long finalBytes = finalFile.length();
        final String finalMuxName = muxName;
        final String finalMuxTime = muxTime;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 100));
            activeTitle.setText(itemPrefix(task) + "Completed");
            activeMeta.setText(task.title + " • " + formatBytes(finalBytes));
            String joinText = finalMuxName + " • joined in " + finalMuxTime;
            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\n" + joinText : joinText);
            refreshQueueUi();
        });
    }

    private VideoFormat findExactCombinedFormat(VideoInfo info, int quality) {
        if (info == null || info.getFormats() == null) return null;
        VideoFormat best = null;
        for (VideoFormat f : info.getFormats()) {
            if (f == null || f.getHeight() != quality) continue;
            String ext = f.getExt();
            String vc = f.getVcodec();
            String ac = f.getAcodec();
            String id = f.getFormatId();
            if (id == null || id.trim().isEmpty()) continue;
            if (ext == null || !"mp4".equalsIgnoreCase(ext)) continue;
            if (vc == null || !vc.toLowerCase(Locale.US).startsWith("avc1")) continue;
            if (ac == null || !ac.toLowerCase(Locale.US).startsWith("mp4a")) continue;
            if (best == null || f.getTbr() > best.getTbr()) best = f;
        }
        return best;
    }

'''
s = s[:start] + new_hd + s[end:]

# 3) Add Media3 muxer implementation before the proven Android framework fallback.
marker = '    private void muxWithAndroid(File videoFile, File audioFile, File outputFile) throws Exception {'
assert marker in s
if 'private void muxWithMedia3Compat(' not in s:
    media3_method = r'''    private void muxWithMedia3Compat(File videoFile, File audioFile, File outputFile) throws Exception {
        MediaExtractor videoExtractor = new MediaExtractor();
        MediaExtractor audioExtractor = new MediaExtractor();
        MediaMuxerCompat muxer = null;
        boolean started = false;
        try {
            videoExtractor.setDataSource(videoFile.getAbsolutePath());
            audioExtractor.setDataSource(audioFile.getAbsolutePath());
            int vs = findTrack(videoExtractor, "video/");
            int as = findTrack(audioExtractor, "audio/");
            if (vs < 0 || as < 0) throw new Exception("Media3 mux input track missing.");
            MediaFormat vf = videoExtractor.getTrackFormat(vs);
            MediaFormat af = audioExtractor.getTrackFormat(as);
            String vm = vf.getString(MediaFormat.KEY_MIME);
            String am = af.getString(MediaFormat.KEY_MIME);
            if (vm == null || !"video/avc".equalsIgnoreCase(vm)) throw new Exception("Fast mux requires H.264 video, got " + vm);
            if (am == null || !am.toLowerCase(Locale.US).startsWith("audio/mp4a")) throw new Exception("Fast mux requires AAC audio, got " + am);
            if (outputFile.exists() && !outputFile.delete()) throw new Exception("Could not replace output MP4.");
            muxer = new MediaMuxerCompat(outputFile.getAbsolutePath(), MediaMuxerCompat.OUTPUT_FORMAT_MP4);
            if (vf.containsKey(MediaFormat.KEY_ROTATION)) {
                int r = vf.getInteger(MediaFormat.KEY_ROTATION);
                if (r == 90 || r == 180 || r == 270) muxer.setOrientationHint(r);
            }
            int vmux = muxer.addTrack(vf);
            int amux = muxer.addTrack(af);
            videoExtractor.selectTrack(vs);
            audioExtractor.selectTrack(as);
            muxer.start();
            started = true;
            int bufferSize = Math.max(8 * 1024 * 1024, Math.max(maxInputSize(vf), maxInputSize(af)) + 1024);
            ByteBuffer buffer = ByteBuffer.allocateDirect(bufferSize);
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            long vt = videoExtractor.getSampleTime();
            long at = audioExtractor.getSampleTime();
            while (vt >= 0 || at >= 0) {
                boolean useVideo = at < 0 || (vt >= 0 && vt <= at);
                MediaExtractor ex = useVideo ? videoExtractor : audioExtractor;
                int track = useVideo ? vmux : amux;
                buffer.clear();
                int size = ex.readSampleData(buffer, 0);
                if (size < 0) {
                    if (useVideo) vt = -1; else at = -1;
                    continue;
                }
                info.set(0, size, ex.getSampleTime(), ex.getSampleFlags());
                muxer.writeSampleData(track, buffer, info);
                ex.advance();
                if (useVideo) vt = videoExtractor.getSampleTime(); else at = audioExtractor.getSampleTime();
            }
            muxer.stop();
            started = false;
        } finally {
            try { videoExtractor.release(); } catch (Exception ignored) { }
            try { audioExtractor.release(); } catch (Exception ignored) { }
            if (muxer != null) {
                if (started) try { muxer.stop(); } catch (Exception ignored) { }
                try { muxer.release(); } catch (Exception ignored) { }
            }
        }
    }

'''
    s = s.replace(marker, media3_method + marker, 1)

# 4) Small timing formatter.
fmt_marker = '    private String formatBytes(long bytes) {'
assert fmt_marker in s
if 'private String formatElapsedMs(' not in s:
    timing = r'''    private String formatElapsedMs(long ms) {
        if (ms < 1000L) return ms + " ms";
        return String.format(Locale.US, "%.1f s", ms / 1000.0);
    }

'''
    s = s.replace(fmt_marker, timing + fmt_marker, 1)

path.write_text(s, encoding='utf-8')
print('V2.0.2 fast finalize patch applied')
