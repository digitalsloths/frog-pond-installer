#!/usr/bin/env python3
"""Package compiled ESP32-S3 firmware into an ESP Web Tools release."""
from pathlib import Path
import json, hashlib, shutil
build=Path('build'); site=Path('site'); root=site/'releases'/'v21.0.0-beta'
core=Path.home()/'.arduino15/packages/esp32/hardware/esp32/3.3.10'
root.mkdir(parents=True,exist_ok=True)
def one(pattern):
    hits=list(build.glob(pattern))
    if len(hits)!=1:raise RuntimeError(f'Expected exactly one {pattern}, found {len(hits)}')
    return hits[0]
parts=[
(one('*.bootloader.bin'),'bootloader.bin',0x0000),
(one('*.partitions.bin'),'partitions.bin',0x8000),
(core/'tools/partitions/boot_app0.bin','boot_app0.bin',0xe000),
(one('*.ino.bin'),'frogpond.bin',0x10000)]
manifest={'name':'Frog Pond V21 Echo and Pocket Watch - Waveshare ESP32-S3 AMOLED 1.75','version':'v21.0.0-beta',
'new_install_prompt_erase':False,'builds':[{'chipFamily':'ESP32-S3','parts':[]}]}
sha=[]
for infile,name,offset in parts:
    if not infile.is_file(): raise RuntimeError(f'Missing {infile}')
    data=infile.read_bytes()
    if not data:raise RuntimeError(f'Empty binary {infile}')
    if name=='frogpond.bin' and data[0]!=0xe9:raise RuntimeError('Bad application ESP image header')
    (root/name).write_bytes(data)
    sha.append(hashlib.sha256(data).hexdigest()+'  '+name)
    manifest['builds'][0]['parts'].append({'path':name,'offset':offset})
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(root/'SHA256SUMS.txt').write_text('\n'.join(sha)+'\n')
(site/'latest.json').write_text(json.dumps({'version':'v21.0.0-beta','manifest':'releases/v21.0.0-beta/manifest.json'},indent=2)+'\n')
print('Validated and packaged',[(name,(root/name).stat().st_size) for _,name,_ in parts])
