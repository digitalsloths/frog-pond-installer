# Frog Pond ESP32-S3 1.75-inch Browser Installer

**Installer:** https://digitalsloths.github.io/frog-pond-installer/

**Cloud build:** https://github.com/digitalsloths/frog-pond-installer/actions

This repository builds the Frog Pond firmware with GitHub Actions and publishes a browser-based USB installer using ESP Web Tools. Chrome or Edge on a desktop and a USB-C data cable are required. This is for the **standard Waveshare ESP32-S3 Touch AMOLED 1.75-inch**, not the 1.43-inch or 1.75C.

## V10 beta status

The cloud workflow now applies `tools/patch_v10.py` after the V6–V9 patches. It adds drifting particles to the pond, restores the home step counter, and corrects the hop sequence. The V9 hat-selection UI and verified persistent Save logic are retained. **The complete new 32×32 animated hat sprite sheets from the separate V10 source bundle have not yet been added to this repository.** Do not assume those sprite fixes have been deployed.

GitHub Actions must show a green build and successful Pages deployment before the V10 beta is flashable; a code commit by itself does not update the live firmware.

## How to flash

1. Check that the latest workflow in **Actions** succeeded.
2. Open the installer URL above in desktop Chrome or Edge.
3. Connect the ESP32-S3 by USB-C data cable, choose **Connect & install** and select the board's serial port.
4. After flashing, press RESET.

The user-provided V10 source ZIP remains separate until its assets are imported; firmware is not physically hardware-tested.

## V14 appearance update
The cloud-built installer now includes the shorter Personalize title, an unboxed footprint step counter, brighter floating pond particles, and a transparent frog preview. Built firmware must pass GitHub Actions before publishing.
