#!/usr/bin/env python3
"""Assemble original Tilt-a-Tron game sources and PNG assets for native Arduino linking.

The source remains unchanged in the upstream integration tree. Separate compile units
rename only each game's global descriptor and asset table symbols, so 11 original
tat_game_t modules can link into one Frog Pond firmware without collisions.
"""
from pathlib import Path
import argparse, json, shutil, re
SLUGS=("echo","starfall","radar","maze","racer","tiltatris","star",
       "pindrop","breakout","skatergirlz","jump")
p=argparse.ArgumentParser()
p.add_argument("sketch",type=Path)
p.add_argument("--upstream",type=Path,required=True)
args=p.parse_args()
sketch=args.sketch
src=sketch/"src"
src.mkdir(parents=True,exist_ok=True)
up=args.upstream
copy=[
 ("components/tat_api/include/tat/tat_api.h","tat/tat_api.h"),
 ("components/lodepng/lodepng.h","lodepng.h"),
 ("components/lodepng/lodepng.cpp","lodepng.cpp"),
 ("components/engine/font5x7.cpp","font5x7.cpp"),
]
for origin,target in copy:
 dst=src/target
 dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(up/origin,dst)
for filename in ("pondtat_runtime.h","pondtat_runtime.cpp"):
 shutil.copyfile(Path(__file__).resolve().parents[1]/"game_ports"/"native"/filename,src/filename)
shutil.copyfile(Path(__file__).resolve().parents[1]/"game_ports"/"frogpond_pause.h",src/"frogpond_pause.h")

def data_bytes(name,data):
 text=[f"static const unsigned char {name}[{len(data)}] = {{"]
 for i in range(0,len(data),20):
  text.append("  "+",".join(str(v) for v in data[i:i+20])+",")
 text.append("};")
 return "\n".join(text)

for slug in SLUGS:
 game=up/"games"/slug
 original=(game/(slug+".c")).read_text()
 # Avoid renaming text in original source. Two narrowly scoped macro aliases
 # preserve its complete original statements and original game logic.
 pre=f'#define tat_game tat_game_{slug}\n#define tat_assets tat_assets_{slug}\n'
 (src/f"game_{slug}.c").write_text(pre+original)
 assetdir=game/"assets"
 entries=[]
 parts=['#include "tat/tat_api.h"']
 if assetdir.exists():
  for i,asset in enumerate(sorted(assetdir.rglob("*"))):
   if not asset.is_file():continue
   name=f"asset_{slug}_{i}"
   bytes_=asset.read_bytes()
   parts.append(data_bytes(name,bytes_))
   entries.append((asset.name,name))
 if not entries:
  parts.append(f'const tat_asset_t tat_assets_{slug}[1] = {{{{0,0,0}}}};')
 else:
  parts.append(f"const tat_asset_t tat_assets_{slug}[{len(entries)}] = {{")
  for filename,name in entries:
   parts.append(f'  {{"{filename}", {name}, {name}+sizeof({name})}},')
  parts.append("};")
 (src/f"assets_{slug}.c").write_text("\n".join(parts)+"\n")
 print(f"Original {slug}: {len(original)} source chars, {len(entries)} original image assets")
print("Prepared all 11 original source units and TAT host for Arduino ESP32.")
