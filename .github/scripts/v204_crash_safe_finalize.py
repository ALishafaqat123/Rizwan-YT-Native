from pathlib import Path

src_path = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
gradle_path = Path('app/build.gradle')

src = src_path.read_text(encoding='utf-8')

for imp in [
    'import com.arthenica.ffmpegkit.FFmpegKit;\n',
    'import com.arthenica.ffmpegkit.FFmpegSession;\n',
    'import com.arthenica.ffmpegkit.ReturnCode;\n',
]:
    src = src.replace(imp, '')

start = src.index('        task.stage = "Native joining video + audio";')
end = src.index('    private VideoFormat findExactCombinedFormat', start)

replacement = r'''        task.stage = "Joining video + audio";
        task.itemProgress = 95;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 95));
            activeTitle.setText(itemPrefix(task) + "Joining video + audio");
            setStatus(task.playlistBatch ? playlistStatusLine(task, 95) :
                    "Safe finalize • measuring mux, verify, save and cleanup separately…");
            refreshQueueUi();
        });

        File mergedTemp = new File(workDir, "merged-android.mp4");
        if (mergedTemp.exists() && !mergedTemp.delete()) throw new Exception("Could not replace temporary merged MP4.");
        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");

        long finalizeStarted = System.currentTimeMillis();

        long muxStarted = System.currentTimeMillis();
        muxWithAndroid(videoFile, audioFile, mergedTemp);
        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);

        task.stage = "Verifying merged MP4";
        task.itemProgress = 97;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 97));
            activeTitle.setText(itemPrefix(task) + "Verifying merged MP4");
            setStatus("Mux " + formatElapsedMs(muxMs) + " • checking video + audio tracks…");
            refreshQueueUi();
        });

        long verifyStarted = System.currentTimeMillis();
        if (!mergedTemp.isFile() || mergedTemp.length() <= 0 ||
                !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {
            if (mergedTemp.exists()) mergedTemp.delete();
            throw new Exception("Safe Android mux verification failed.");
        }
        long verifyMs = Math.max(0L, System.currentTimeMillis() - verifyStarted);

        task.stage = "Saving final MP4";
        task.itemProgress = 99;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 99));
            activeTitle.setText(itemPrefix(task) + "Saving final MP4");
            setStatus("Mux " + formatElapsedMs(muxMs) + " • Verify " + formatElapsedMs(verifyMs) + " • saving…");
            refreshQueueUi();
        });

        long saveStarted = System.currentTimeMillis();
        moveOrCopy(mergedTemp, finalFile);
        long saveMs = Math.max(0L, System.currentTimeMillis() - saveStarted);

        long finalVerifyStarted = System.currentTimeMillis();
        if (!finalFile.isFile() || finalFile.length() <= 0 ||
                !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {
            if (finalFile.exists()) finalFile.delete();
            throw new Exception("Final saved MP4 verification failed.");
        }
        long finalVerifyMs = Math.max(0L, System.currentTimeMillis() - finalVerifyStarted);

        long cleanupStarted = System.currentTimeMillis();
        deleteWorkFiles(workDir);
        long cleanupMs = Math.max(0L, System.currentTimeMillis() - cleanupStarted);
        long finalizeMs = Math.max(0L, System.currentTimeMillis() - finalizeStarted);

        lastFinalizeReport = "Android MediaMuxer • Mux " + formatElapsedMs(muxMs) +
                " • Verify " + formatElapsedMs(verifyMs + finalVerifyMs) +
                " • Save " + formatElapsedMs(saveMs) +
                " • Cleanup " + formatElapsedMs(cleanupMs) +
                " • Total " + formatElapsedMs(finalizeMs);

        task.stage = "Finalize " + formatElapsedMs(finalizeMs);
        task.itemProgress = 100;
        final long finalBytes = finalFile.length();
        final String report = lastFinalizeReport;
        runOnUiThread(() -> {
            progress.setProgress(overallProgress(task, 100));
            activeTitle.setText(itemPrefix(task) + "Completed");
            activeMeta.setText(task.title + " • " + formatBytes(finalBytes));
            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\n" + report : report);
            Toast.makeText(this, report, Toast.LENGTH_LONG).show();
            refreshQueueUi();
        });
    }

'''
src = src[:start] + replacement + src[end:]

native_start = src.find('    private void muxWithNativeFfmpeg(')
if native_start != -1:
    android_start = src.index('    private void muxWithAndroid(', native_start)
    src = src[:native_start] + src[android_start:]

src_path.write_text(src, encoding='utf-8')

gradle = gradle_path.read_text(encoding='utf-8')
gradle = gradle.replace("versionCode 203", "versionCode 204")
gradle = gradle.replace("versionName '2.0.3-native-finalize-preview'", "versionName '2.0.4-crash-safe-timing-preview'")
gradle = gradle.replace("    implementation 'dev.ffmpegkit-maintained:ffmpeg-kit-min:8.1.7'\n", "")
gradle_path.write_text(gradle, encoding='utf-8')

print('V2.0.4 crash-safe finalize patch applied')
