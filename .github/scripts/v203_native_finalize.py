from pathlib import Path
import re

JAVA = Path('app/src/main/java/com/rizwan/ytnativefoundation/V2MainActivity.java')
GRADLE = Path('app/build.gradle')
WORKFLOW = Path('.github/workflows/build-apk.yml')

s = JAVA.read_text(encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'Missing expected block: {label}')
    return text.replace(old, new, 1)

# Native FFmpegKit imports. Keep the existing youtubedl-android FFmpeg import because
# that dependency is still part of the proven downloader engine.
s = replace_once(
    s,
    'import com.yausername.ffmpeg.FFmpeg;\n',
    'import com.arthenica.ffmpegkit.FFmpegKit;\nimport com.arthenica.ffmpegkit.FFmpegSession;\nimport com.arthenica.ffmpegkit.ReturnCode;\n\nimport com.yausername.ffmpeg.FFmpeg;\n',
    'FFmpegKit imports'
)

# MediaMuxerCompat did not materially improve finalize time on the real Android 8.1 test.
s = s.replace('import androidx.media3.muxer.MediaMuxerCompat;\n', '')

s = replace_once(
    s,
    '    private volatile DownloadTask currentTask = null;\n',
    '    private volatile DownloadTask currentTask = null;\n    private volatile String lastFinalizeReport = null;\n',
    'last finalize report field'
)

old_queue_finish = '''        queueRunning = false;\n        runOnUiThread(() -> {\n            activeTitle.setText("Queue finished");\n            activeMeta.setText("");\n            progress.setProgress(100);\n            setStatus("All queued items have been processed.");\n            refreshQueueUi();\n            refreshCompletedUi();\n        });\n'''
new_queue_finish = '''        queueRunning = false;\n        final String finishReport = lastFinalizeReport;\n        runOnUiThread(() -> {\n            activeTitle.setText("Queue finished");\n            activeMeta.setText(finishReport == null ? "" : finishReport);\n            progress.setProgress(100);\n            setStatus(finishReport == null\n                    ? "All queued items have been processed."\n                    : "All queued items have been processed.\\nLast finalize: " + finishReport);\n            refreshQueueUi();\n            refreshCompletedUi();\n        });\n'''
s = replace_once(s, old_queue_finish, new_queue_finish, 'queue finish report')

old_finalize = '''        task.stage = "Fast joining video + audio";\n        task.itemProgress = 95;\n        runOnUiThread(() -> {\n            progress.setProgress(overallProgress(task, 95));\n            activeTitle.setText(itemPrefix(task) + "Fast joining video + audio");\n            setStatus(task.playlistBatch ? playlistStatusLine(task, 95) :\n                    "Joining with the fast MP4 muxer…");\n            refreshQueueUi();\n        });\n\n        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");\n        long muxStarted = System.currentTimeMillis();\n        boolean media3Used = false;\n        Exception media3Error = null;\n        try {\n            muxWithMedia3Compat(videoFile, audioFile, finalFile);\n            if (!finalFile.isFile() || finalFile.length() <= 0 ||\n                    !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {\n                throw new Exception("Media3 fast mux verification failed.");\n            }\n            media3Used = true;\n        } catch (Exception fastMuxError) {\n            media3Error = fastMuxError;\n            if (finalFile.exists()) finalFile.delete();\n            muxWithAndroid(videoFile, audioFile, finalFile);\n            if (!finalFile.isFile() || finalFile.length() <= 0 ||\n                    !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {\n                if (finalFile.exists()) finalFile.delete();\n                throw new Exception("Final saved MP4 verification failed after fallback.", fastMuxError);\n            }\n        }\n        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);\n        String muxName = media3Used ? "Media3 fast mux" : "Android fallback mux";\n        String muxTime = formatElapsedMs(muxMs);\n\n        deleteWorkFiles(workDir);\n        task.stage = "Joined in " + muxTime;\n        task.itemProgress = 100;\n        final long finalBytes = finalFile.length();\n        final String finalMuxName = muxName;\n        final String finalMuxTime = muxTime;\n        runOnUiThread(() -> {\n            progress.setProgress(overallProgress(task, 100));\n            activeTitle.setText(itemPrefix(task) + "Completed");\n            activeMeta.setText(task.title + " • " + formatBytes(finalBytes));\n            String joinText = finalMuxName + " • joined in " + finalMuxTime;\n            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\\n" + joinText : joinText);\n            refreshQueueUi();\n        });\n'''
new_finalize = '''        task.stage = "Native joining video + audio";\n        task.itemProgress = 95;\n        runOnUiThread(() -> {\n            progress.setProgress(overallProgress(task, 95));\n            activeTitle.setText(itemPrefix(task) + "Native joining video + audio");\n            setStatus(task.playlistBatch ? playlistStatusLine(task, 95) :\n                    "Joining without re-encoding using the native MP4 engine…");\n            refreshQueueUi();\n        });\n\n        File mergedTemp = new File(workDir, "merged-native.mp4");\n        if (mergedTemp.exists() && !mergedTemp.delete()) throw new Exception("Could not replace temporary merged MP4.");\n        if (finalFile.exists() && !finalFile.delete()) throw new Exception("Could not replace old final file.");\n\n        long finalizeStarted = System.currentTimeMillis();\n        long muxStarted = System.currentTimeMillis();\n        String muxName = "Native FFmpeg";\n        Exception nativeError = null;\n        try {\n            muxWithNativeFfmpeg(videoFile, audioFile, mergedTemp);\n            if (!mergedTemp.isFile() || mergedTemp.length() <= 0 ||\n                    !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {\n                throw new Exception("Native FFmpeg mux verification failed.");\n            }\n        } catch (Exception nativeMuxError) {\n            nativeError = nativeMuxError;\n            if (mergedTemp.exists()) mergedTemp.delete();\n            muxName = "Android fallback";\n            try {\n                muxWithAndroid(videoFile, audioFile, mergedTemp);\n                if (!mergedTemp.isFile() || mergedTemp.length() <= 0 ||\n                        !hasVideoTrack(mergedTemp.getAbsolutePath()) || !hasAudioTrack(mergedTemp.getAbsolutePath())) {\n                    throw new Exception("Android fallback verification failed.");\n                }\n            } catch (Exception fallbackError) {\n                if (mergedTemp.exists()) mergedTemp.delete();\n                throw new Exception("Native and Android mux both failed. Native: " + shortMessage(nativeError), fallbackError);\n            }\n        }\n        long muxMs = Math.max(0L, System.currentTimeMillis() - muxStarted);\n\n        task.stage = "Saving final MP4";\n        task.itemProgress = 99;\n        runOnUiThread(() -> {\n            progress.setProgress(overallProgress(task, 99));\n            activeTitle.setText(itemPrefix(task) + "Saving final MP4");\n            setStatus("Join finished in " + formatElapsedMs(muxMs) + " • publishing file…");\n            refreshQueueUi();\n        });\n\n        long publishStarted = System.currentTimeMillis();\n        moveOrCopy(mergedTemp, finalFile);\n        long publishMs = Math.max(0L, System.currentTimeMillis() - publishStarted);\n        if (!finalFile.isFile() || finalFile.length() <= 0 ||\n                !hasVideoTrack(finalFile.getAbsolutePath()) || !hasAudioTrack(finalFile.getAbsolutePath())) {\n            if (finalFile.exists()) finalFile.delete();\n            throw new Exception("Final saved MP4 verification failed.");\n        }\n        long finalizeMs = Math.max(0L, System.currentTimeMillis() - finalizeStarted);\n\n        String muxTime = formatElapsedMs(muxMs);\n        String publishTime = formatElapsedMs(publishMs);\n        String totalTime = formatElapsedMs(finalizeMs);\n        lastFinalizeReport = muxName + " • Join " + muxTime + " • Save " + publishTime + " • Total " + totalTime;\n\n        deleteWorkFiles(workDir);\n        task.stage = "Finalize " + totalTime;\n        task.itemProgress = 100;\n        final long finalBytes = finalFile.length();\n        final String report = lastFinalizeReport;\n        runOnUiThread(() -> {\n            progress.setProgress(overallProgress(task, 100));\n            activeTitle.setText(itemPrefix(task) + "Completed");\n            activeMeta.setText(task.title + " • " + formatBytes(finalBytes));\n            setStatus(task.playlistBatch ? playlistStatusLine(task, 100) + "\\n" + report : report);\n            Toast.makeText(this, report, Toast.LENGTH_LONG).show();\n            refreshQueueUi();\n        });\n'''
s = replace_once(s, old_finalize, new_finalize, 'HD finalize block')

# Remove the Media3 compatibility implementation now that the real-device test showed
# little practical gain. The proven framework muxer remains as the safety fallback.
pattern = r'\n    private void muxWithMedia3Compat\(File videoFile, File audioFile, File outputFile\) throws Exception \{.*?\n    \}\n\n    private void muxWithAndroid'
s2, count = re.subn(pattern, '\n    private void muxWithAndroid', s, count=1, flags=re.S)
if count != 1:
    raise SystemExit('Could not remove MediaMuxerCompat method')
s = s2

native_method = r'''
    private void muxWithNativeFfmpeg(File videoFile, File audioFile, File outputFile) throws Exception {
        if (outputFile.exists() && !outputFile.delete()) throw new Exception("Could not replace native mux output.");
        String command = "-hide_banner -loglevel error -y " +
                "-i " + ffmpegQuote(videoFile.getAbsolutePath()) + " " +
                "-i " + ffmpegQuote(audioFile.getAbsolutePath()) + " " +
                "-map 0:v:0 -map 1:a:0 -c copy -movflags +faststart " +
                ffmpegQuote(outputFile.getAbsolutePath());
        FFmpegSession session = FFmpegKit.execute(command);
        if (session == null || !ReturnCode.isSuccess(session.getReturnCode())) {
            String code = session == null || session.getReturnCode() == null ? "unknown" : session.getReturnCode().toString();
            throw new Exception("Native FFmpeg remux failed (code " + code + ").");
        }
    }

    private String ffmpegQuote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

'''
marker = '    private void muxWithAndroid(File videoFile, File audioFile, File outputFile) throws Exception {'
if marker not in s:
    raise SystemExit('Missing Android mux marker')
s = s.replace(marker, native_method + marker, 1)

JAVA.write_text(s, encoding='utf-8')

# Build config: add maintained JNI FFmpegKit min package for a pure stream-copy remux.
g = GRADLE.read_text(encoding='utf-8')
g = replace_once(g, "versionCode 202", "versionCode 203", 'versionCode')
g = replace_once(g, "versionName '2.0.2-fast-finalize-preview'", "versionName '2.0.3-native-finalize-preview'", 'versionName')
g = g.replace("    implementation 'androidx.media3:media3-muxer:1.9.1'\n", '')
if "dev.ffmpegkit-maintained:ffmpeg-kit-min:8.1.7" not in g:
    g = g.replace(
        "    implementation 'io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1'\n",
        "    implementation 'io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1'\n    implementation 'dev.ffmpegkit-maintained:ffmpeg-kit-min:8.1.7'\n"
    )
GRADLE.write_text(g, encoding='utf-8')

# Build artifact naming/verification.
w = WORKFLOW.read_text(encoding='utf-8')
w = w.replace('V2.0.2', 'V2.0.3')
w = w.replace('v2.0.2', 'v2.0.3')
w = w.replace('Fast-Finalize', 'Native-Fast-Finalize')
w = w.replace("versionCode='202'", "versionCode='203'")
w = w.replace("versionName='2.0.2-fast-finalize-preview'", "versionName='2.0.3-native-finalize-preview'")
WORKFLOW.write_text(w, encoding='utf-8')

print('V2.0.3 native finalize patch applied')
