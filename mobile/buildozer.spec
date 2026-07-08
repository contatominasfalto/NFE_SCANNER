[app]
title = NFE Scanner
package.name = nfescanner
package.domain = br.com.nfescanner
icon.filename = assets/app_icon.png

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,json
source.exclude_dirs = tests,__pycache__,.git

version = 0.1.9
android.numeric_version = 10
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

android.archs = arm64-v8a
android.allow_backup = True
android.add_manifest_application_arguments = android:usesCleartextTraffic="true"
android.gradle_dependencies = com.google.android.gms:play-services-code-scanner:16.1.0
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
