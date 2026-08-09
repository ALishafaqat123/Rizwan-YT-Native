from pathlib import Path

src_path = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
gradle_path = Path('app/build.gradle')

src = src_path.read_text(encoding='utf-8')
gradle = gradle_path.read_text(encoding='utf-8')

# Imports
needle = 'import android.media.MediaMuxer;\n'
replacement = '''import android.media.MediaMuxer;\nimport androidx.media3.common.Format;\nimport androidx.media3.common.MimeTypes;\nimport androidx.media3.muxer.Mp4Muxer;\n'''
if needle not in src:
    raise SystemExit('MediaMuxer import anchor not found')
src = src.replace(needle, replacement, 1)

# Ensure FileOutputStream import already exists; this project has it.

old_mux = '''        long muxStarted = System.currentTimeMillis();\n        muxWithAndroid(videoFile, audioFile, mergedTemp);\n        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);\n'''
new_mux = '''        long muxStarted = System.currentTimeMillis();\n        String muxEngine = "Media3 batched";\n        try {\n            muxWithMedia3Batched(videoFile, audioFile, mergedTemp);\n        } catch (Exception batchedError) {\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxEngine = "Android fallback";\n            muxWithAndroid(videoFile, audioFile, mergedTemp);\n        }\n        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);\n'''
if old_mux not in src:
    raise SystemExit('mux timing block not found')
src = src.replace(old_mux, new_mux, 1)

old_report = '''        lastFinalizeReport = "Android MediaMuxer • Mux " + formatElapsedMs(muxMs) +\n                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n'''
new_report = '''        lastFinalizeReport = muxEngine + " • Mux " + formatElapsedMs(muxMs) +\n                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +\n'''
if old_report not in src:
    raise SystemExit('final report block not found')
src = src.replace(old_report, new_report, 1)

method_anchor = '''    private void muxWithAndroid(File videoFile, File audioFile, File outputFile) throws Exception {\n'''
if method_anchor not in src:
    raise SystemExit('muxWithAndroid anchor not found')

media3_method = r'''    private void muxWithMedia3Batched(File videoFile, File audioFile, File outputFile) throws Exception {
        MediaExtractor videoExtractor = new MediaExtractor();
        MediaExtractor audioExtractor = new MediaExtractor();
        Mp4Muxer muxer = null;
        try {
            videoExtractor.setDataSource(videoFile.getAbsolutePath());
            audioExtractor.setDataSource(audioFile.getAbsolutePath());
            int vs = findTrack(videoExtractor, "video/");
            int as = findTrack(audioExtractor, "audio/");
            if (vs < 0 || as < 0) throw new Exception("Media3 input track missing.");

            MediaFormat vf = videoExtractor.getTrackFormat(vs);
            MediaFormat af = audioExtractor.getTrackFormat(as);
            String vm = vf.getString(MediaFormat.KEY_MIME);
            String am = af.getString(MediaFormat.KEY_MIME);
            if (vm == null || !"video/avc".equalsIgnoreCase(vm))
                throw new Exception("Media3 batched mux requires H.264 video, got " + vm);
            if (am == null || !am.toLowerCase(Locale.US).startsWith("audio/mp4a"))
                throw new Exception("Media3 batched mux requires AAC audio, got " + am);

            if (outputFile.exists() && !outputFile.delete())
                throw new Exception("Could not replace Media3 output MP4.");

            muxer = new Mp4Muxer.Builder(new FileOutputStream(outputFile))
                    .setSampleBatchingEnabled(true)
                    .setSampleCopyingEnabled(true)
                    .build();

            Format videoFormat = media3VideoFormat(vf);
            Format audioFormat = media3AudioFormat(af);
            int vmux = muxer.addTrack(videoFormat);
            int amux = muxer.addTrack(audioFormat);

            videoExtractor.selectTrack(vs);
            audioExtractor.selectTrack(as);
            int bufferSize = Math.max(8 * 1024 * 1024,
                    Math.max(maxInputSize(vf), maxInputSize(af)) + 1024);
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
                if (useVideo) vt = videoExtractor.getSampleTime();
                else at = audioExtractor.getSampleTime();
            }
            muxer.close();
            muxer = null;
        } finally {
            try { videoExtractor.release(); } catch (Exception ignored) { }
            try { audioExtractor.release(); } catch (Exception ignored) { }
            if (muxer != null) try { muxer.close(); } catch (Exception ignored) { }
        }
    }

    private Format media3VideoFormat(MediaFormat f) throws Exception {
        ArrayList<byte[]> init = media3InitData(f);
        Format.Builder b = new Format.Builder()
                .setSampleMimeType(MimeTypes.VIDEO_H264)
                .setWidth(f.getInteger(MediaFormat.KEY_WIDTH))
                .setHeight(f.getInteger(MediaFormat.KEY_HEIGHT))
                .setInitializationData(init);
        try {
            if (f.containsKey(MediaFormat.KEY_FRAME_RATE)) b.setFrameRate(f.getFloat(MediaFormat.KEY_FRAME_RATE));
        } catch (Exception ignored) { }
        return b.build();
    }

    private Format media3AudioFormat(MediaFormat f) throws Exception {
        ArrayList<byte[]> init = media3InitData(f);
        return new Format.Builder()
                .setSampleMimeType(MimeTypes.AUDIO_AAC)
                .setChannelCount(f.getInteger(MediaFormat.KEY_CHANNEL_COUNT))
                .setSampleRate(f.getInteger(MediaFormat.KEY_SAMPLE_RATE))
                .setInitializationData(init)
                .build();
    }

    private ArrayList<byte[]> media3InitData(MediaFormat f) {
        ArrayList<byte[]> init = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            try {
                ByteBuffer csd = f.getByteBuffer("csd-" + i);
                if (csd == null) continue;
                ByteBuffer copy = csd.duplicate();
                copy.position(0);
                byte[] bytes = new byte[copy.remaining()];
                copy.get(bytes);
                if (bytes.length > 0) init.add(bytes);
            } catch (Exception ignored) { }
        }
        return init;
    }

'''
src = src.replace(method_anchor, media3_method + method_anchor, 1)

# Version/dependency
if "versionCode 204" not in gradle or "versionName '2.0.4-crash-safe-timing-preview'" not in gradle:
    raise SystemExit('Expected V2.0.4 Gradle version not found')
gradle = gradle.replace('versionCode 204', 'versionCode 205', 1)
gradle = gradle.replace("versionName '2.0.4-crash-safe-timing-preview'", "versionName '2.0.5-media3-batched-preview'", 1)
if "implementation 'androidx.media3:media3-muxer:1.9.1'" not in gradle:
    gradle = gradle.replace("implementation 'io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1'\n",
                            "implementation 'io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1'\n    implementation 'androidx.media3:media3-muxer:1.9.1'\n", 1)

src_path.write_text(src, encoding='utf-8')
gradle_path.write_text(gradle, encoding='utf-8')
print('V2.0.5 Media3 batched mux patch applied')
