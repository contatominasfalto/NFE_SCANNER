[app]
title = NFE Scanner
package.name = nfescanner
package.domain = br.com.nfescanner

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,json
source.exclude_dirs = tests,__pycache__,.git

version = 0.1.0
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
