[app]
title = CarApp
package.name = carapp
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.0
requirements = python3,kivy==2.3.0,kivymd==1.1.1
orientation = portrait
fullscreen = 0

[app@android]
permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[android]
api = 31
minapi = 24
arch = arm64-v8a
allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
