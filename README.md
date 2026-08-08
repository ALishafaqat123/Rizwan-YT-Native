# Rizwan YT Native

Native Android foundation for **Rizwan Media Saver**.

## v1.5.6 test goal

- Android 8.1 compatible test target
- yt-dlp through `youtubedl-android`
- one public YouTube video at up to 360p
- native in-app progress and cancel
- output folder: `Movies/Rizwan Media Saver`
- no WebView media URL replay
- no Android DownloadManager

The APK is built automatically by GitHub Actions from `.github/workflows/build-apk.yml`.

This foundation intentionally starts with a small test scope. Higher resolutions and FFmpeg audio/video merging come after the first native download is proven on-device.
