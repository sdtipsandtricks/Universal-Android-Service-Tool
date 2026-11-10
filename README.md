# Universal Android Service Tool (Windows)

## Supported brands
- OPPO
- vivo
- OnePlus
- Samsung

## Features in this build
- USB ADB device detection and authorization status
- Auto-detection of manufacturer/brand
- Device model, codename, product, build ID, fingerprint, Android SDK/version, security patch, boot-state and CPU ABI
- Full kernel release and page-size scan
- Read-only FASTBOOT device detection
- Exact-match temporary-root profile lookup (brand + model + codename + build ID + full kernel)
- Existing `su -c id` root verification
- Open upstream guide for a selected verified profile
- JSON diagnostic report export
- Windows GUI with operation panel and live log

## Deliberate safety limits
This tool does NOT provide:
- Bootloader unlocking or relocking
- FRP removal or account-lock bypass
- Factory reset / demo removal
- Exploit payload execution
- Boot image patching or flashing
- Partition erase/write commands

The bootloader remains locked. Temporary root is not the same as temporary bootloader unlock. A normal retail ADB shell cannot become root unless the device already has a supported root mechanism. Exact model, build ID and complete kernel release must match a maintained upstream hardware-tested profile.

## Install prerequisites
1. Windows 10 or 11.
2. Android SDK Platform-Tools (adb.exe and fastboot.exe).
3. Add the Platform-Tools folder to Windows PATH.
4. Python 3.10+ (only required to build the EXE).
5. Enable Developer options > USB debugging on the phone and accept the USB debugging RSA prompt.

## Build EXE
1. Extract the ZIP.
2. Double-click `BUILD_EXE_ON_WINDOWS.bat`.
3. The executable is created at `dist\Universal_Android_Service_Tool.exe`.
4. Copy/keep `profiles.json` beside the EXE.

## Profile database
The supplied profile list is intentionally empty. This prevents false compatibility claims. Add an entry only after confirming the exact model, device codename, build ID, full kernel release, upstream loader and published hardware-test evidence. `status` must be exactly `verified` for the application to display a verified match.

Example schema (illustrative only; not a real supported device):
{
  "brand": "OPPO",
  "model": "EXACT MODEL STRING",
  "device": "EXACT CODENAME",
  "build_id": "EXACT BUILD ID",
  "kernel_release": "EXACT FULL uname -r OUTPUT",
  "status": "verified",
  "loader": "Upstream project name",
  "method": "Documented method",
  "upstream_url": "https://github.com/OWNER/PROJECT"
}

Do not copy a profile for a similar model or firmware. Verify upstream release authenticity and read the device-specific recovery notes first.
