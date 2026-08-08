Rizwan YT Native Foundation v1.5.6 — SOURCE PACKAGE
===================================================

مقصد
-----
یہ پرانے WebView/direct-GoogleVideo/403 patches کا تسلسل نہیں ہے۔
یہ نئی native foundation ہے جو youtubedl-android 0.18.1 کے ذریعے bundled Python + yt-dlp استعمال کرتی ہے۔

پہلا test scope
---------------
- ایک public YouTube single-video URL
- 360p combined (itag 18) کو ترجیح
- اگر itag 18 نہ ہو تو best <= 360p MP4 fallback
- progress callback
- cancel
- output: Movies / Rizwan Media Saver
- system DownloadManager استعمال نہیں ہوتا
- WebView media URL replay استعمال نہیں ہوتا

ابھی شامل نہیں
--------------
- 720p/1080p video+audio merge
- FFmpeg integration
- thumbnail/history cards
- pause/resume queue
- playlist download

اہم
----
یہ native Android source foundation ہے۔ APK GitHub Actions سے compile ہوگی۔

Dependency
----------
io.github.junkfood02.youtubedl-android:library:0.18.1

Target test ABI
---------------
arm64-v8a

Version
-------
1.5.6-native-foundation / code 156
