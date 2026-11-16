#!/usr/bin/env python3
"""Build an optional localhost Web Serial installer for experimental native TAT firmware.

Never publish this as the repository's latest.json or deploy to GitHub Pages.
"""
from pathlib import Path
import json, shutil
root=Path("test-site")
root.mkdir(exist_ok=True)
build=Path("build")
core=Path.home()/".arduino15/packages/esp32/hardware/esp32/3.3.10"
def unique(glob):
 matches=list(build.glob(glob))
 if len(matches)!=1:raise RuntimeError(f"Expected one {glob}: {matches}")
 return matches[0]
parts=[
 (unique("*.bootloader.bin"),"bootloader.bin",0x0000),
 (unique("*.partitions.bin"),"partitions.bin",0x8000),
 (core/"tools/partitions/boot_app0.bin","boot_app0.bin",0xe000),
 (unique("*.ino.bin"),"frogpond-native.bin",0x10000)
]
out=[]
for source,dest,offset in parts:
 if not source.is_file():raise RuntimeError("Missing "+str(source))
 shutil.copyfile(source,root/dest)
 out.append({"path":dest,"offset":offset})
manifest={
 "name":"Frog Pond v22 ORIGINAL GAMES — EXPERIMENTAL; hardware unverified",
 "version":"v22-native-test",
 "new_install_prompt_erase":False,
 "builds":[{"chipFamily":"ESP32-S3","parts":out}]
}
(root/"manifest.json").write_text(json.dumps(manifest,indent=2))
(root/"index.html").write_text("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Frog Pond Original Games — Experimental USB Installer</title>
<style>body{font-family:system-ui,sans-serif;background:#102b30;color:#f5f7f5;max-width:640px;margin:40px auto;padding:20px;line-height:1.5}
main{padding:25px;border-radius:18px;background:#173b40}h1{font-size:1.5rem}a{color:#80ead0}
.note{background:#442b18;padding:14px;border-radius:12px;margin:18px 0}button{padding:12px}</style></head>
<body><main><h1>Frog Pond — Original Tilt-a-Tron Games</h1>
<p><strong>ESP32-S3 Touch AMOLED 1.75-inch · Experimental v22</strong></p>
<div class="note"><strong>UNTESTED HARDWARE BUILD</strong> — Contains all eleven original game sources and a new TAT API host.
Graphics, touch, tilt, audio, and pause controls need physical validation. Do not use this build if you cannot reflash V21 to recover.</div>
<p>Plug your board into USB, open in Chrome or Edge on localhost, and select Install.</p>
<esp-web-install-button manifest="manifest.json"></esp-web-install-button>
<p>Don't choose an erase option unless you intend to reset local saves.</p>
<p><a href="https://digitalsloths.github.io/frog-pond-installer/">Return to stable V21 flasher</a> |
<a href="https://github.com/digitalsloths/frog-pond-installer/pull/1">Integration source and status</a></p>
<p>Package includes original Tilt-a-Tron content under the MIT license (c) PartiallyFrozen.</p>
</main><script type="module" src="https://unpkg.com/esp-web-tools@10/dist/web/install-button.js"></script></body></html>
""")
(root/"HOW_TO_RUN.txt").write_text("""Frog Pond experimental original Tilt-a-Tron games (ESP32-S3 AMOLED 1.75-inch)

1. Download the 'experimental-native-tat-web-flasher' artifact from the GitHub Actions build.
2. Extract the archive to a folder on your Windows PC.
3. In that folder open PowerShell and run: py -m http.server 8000
   (or: python -m http.server 8000)
4. Open Chrome or Edge at http://localhost:8000
5. Connect the board by USB, press Install and select the ESP32-S3 serial port.
6. For recovery, use your stable installer:
   https://digitalsloths.github.io/frog-pond-installer/

Experimental, not yet confirmed on physical device; only flash if comfortable recovering.
""")
print("Packaged local-only experimental Web Serial installer:",root)
