[app]
title = Alarm Scheduler
package.name = alarmscheduler
package.domain = org.alarmscheduler

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp3,wav,json
source.include_patterns = alarm alert/*

version = 1.0

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

android.permissions = VIBRATE,WAKE_LOCK,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED,FOREGROUND_SERVICE

android.api = 34
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
