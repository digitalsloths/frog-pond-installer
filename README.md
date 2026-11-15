# Frog Pond ESP32-S3 USB installer

Firmware and browser installer for the **standard Waveshare ESP32-S3 Touch AMOLED 1.75-inch**. Not compatible with the 1.43-inch or 1.75C variants.

## Install
Once GitHub Pages is enabled and the workflow has succeeded, open **https://digitalsloths.github.io/frog-pond-installer/** in desktop Chrome/Edge with a USB-C data cable and click **Connect & install**. The website uses ESP Web Tools 10.1.0 and Web Serial to flash precompiled ESP32-S3 firmware. It does not compile firmware in the browser.

## Automated releases
The workflow under `.github/workflows/build-site.yml` downloads the existing **V5 source** archive, applies `tools/patch_v6.py`, fetches Waveshare Arduino libraries, installs Arduino ESP32 3.3.10, compiles using 16 MB flash and OPI PSRAM, validates the required binaries and packages a versioned manifest. On success it deploys the exact contents of `site/` via GitHub Pages. Failed builds do not publish.

**V6 is currently beta and must be tested on physical hardware.** The external V5 source archive and upstream Waveshare repository are build dependencies. A more reproducible follow-up is to check source and pinned library versions into this repository. Physical step counting still requires calibration.

## GitHub Pages (one-time setup)
Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**. Then inspect the workflow under **Actions**, or use **Run workflow**. The installer page won't show **Connect & install** until compilation and deployment complete successfully.

## V6 changes
Navigation swipe fix (Home left = Personalize; Home right = Games / Settings), touchscreen release debounce, hat touch targets, Save feedback and persistent values, and removal of Personalize's Back button. The original MOST startup image remains.

## Flash manifest
ESP32-S3; bootloader `0x0`, partitions `0x8000`, boot_app0 `0xe000`, application `0x10000`. The website checks files before activating the flash control.
