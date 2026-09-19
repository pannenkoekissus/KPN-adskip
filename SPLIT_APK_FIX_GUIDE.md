# KPN TV+ APK Black Screen Playback Issue - ROOT CAUSE & FIX

## Problem Analysis

### What's Happening
Your patched APK shows a **black screen during playback** with this error:
```
Resources$NotFoundException: Drawable (missing name) with resource ID #0x7f0800c5
```

The resource ID `0x7f0800c5` maps to `exo_icon_vr`, a media3 control UI drawable.

### Root Cause: Split APK Architecture Issue

The **pristine (working) KPN TV+ app is shipped as split APKs**:
- `base.apk` — Core app logic
- `split_config.xxhdpi.apk` — High-density screen resources  
- `split_config.nl.apk` — Dutch localization

**Media3 drawables live in the xxhdpi split**, not in base.apk.

Your current build process attempts to **merge all splits into one standalone APK**. This breaks because:
1. apktool decompiles/recompiles each APK independently
2. When merging resources from multiple APKs, the resource table (resources.arsc) becomes corrupted
3. Resource IDs that existed in splits are lost in the merged version
4. Android can't find drawable 0x7f0800c5 at runtime → black screen

### Evidence from Logs

**Pristine log (line 9963 - WORKS):**
```
No package ID 6b found for resource ID 0x6b0b0013
```
→ This is a *config-split* package reference. The pristine app *expects* this because splits are separate.

**Your merged log (line 13026 - FAILS):**
```
Resources$NotFoundException: Drawable (missing name) with resource ID #0x7f0800c5
```
→ Resource disappeared after merge. It was in xxhdpi split, but not properly merged into standalone.

---

## Solution: Keep Split Architecture (Recommended)

**Don't merge splits into standalone.** Instead, patch each split individually and keep them split.

### Why This Works
- Resources stay in their proper locations (xxhdpi drawables in xxhdpi split)
- No resource table corruption
- Matches how the pristine app is actually shipped
- Easier to maintain and patch

### Implementation

I've created `build_patched_splits.py` which:

1. **Decompiles** each pristine split individually
2. **Applies patches** (AdSkipHook, etc.) to base.apk
3. **Rebuilds** each split separately
4. **Packages** as:
   - Option A: Individual signed splits (for ADB multi-install)
   - Option B: Universal APK (single file, all splits merged correctly)

### How to Use

```bash
# Navigate to workspace
cd c:\Users\Gebruiker\KPN-adskip

# Run the patched split builder
python scratch\build_patched_splits.py

# Output will be in patch\build\output\
# Results:
#   - base.apk (signed)
#   - split_config.nl.apk (signed)
#   - split_config.xxhdpi.apk (signed)
#   - kpn-tvplus-adskip-universal-signed.apk (combined, single file)
```

### Installation

**Option A: Multiple APKs (Recommended for device)**
```bash
adb install-multiple patch\build\output\base.apk \
    patch\build\output\split_config.nl.apk \
    patch\build\output\split_config.xxhdpi.apk
```

**Option B: Universal APK (Easier, single file)**
```bash
adb install patch\build\output\kpn-tvplus-adskip-universal-signed.apk
```

---

## Alternative: Fix Standalone Merge (Complex, Not Recommended)

If you absolutely need one file and must use standalone approach:

### Option 1: Use bundletool (Google's official tool)
```bash
# Build the Android App Bundle first
gradle bundle

# Generate universal APK with proper resource merging
bundletool build-apks --bundle=app.aab --output=app.apks --mode=universal
```

### Option 2: Use Android Build Tools
Use `aapt2` with proper resource overlays to merge splits before building.

Both options are complex. **Keeping splits is simpler and correct.**

---

## Why Splitting is Actually Better

| Aspect | Split | Standalone |
|--------|-------|-----------|
| Resource Integrity | ✓ Perfect | ✗ Corrupted during merge |
| Installation Size | ✓ Minimal (only needed resources) | ✗ Bloated (all resources in one file) |
| Maintenance | ✓ Each split decompiles cleanly | ✗ Merge issues, resource conflicts |
| Distribution | ✓ How Google Play ships apps | ✗ Workaround only |
| Compatibility | ✓ Works with all Android versions that support splits (Android 5.0+) | Standard, but forces unnecessary bloat |

---

## Next Steps

1. **Run the recommended script:**
   ```bash
   python scratch\build_patched_splits.py
   ```

2. **Test the universal APK:**
   ```bash
   adb install patch\build\output\kpn-tvplus-adskip-universal-signed.apk
   ```

3. **Verify playback works** (resources should load properly now)

4. **If playback still fails:**
   - We may need to patch additional files (Android manifest, resource overlay configurations)
   - Share the new error log for further debugging

---

## Technical Details

### Resource ID Breakdown
- `0x7f0800c5` = Resource ID
  - `7f` = Package ID (app resources)
  - `08` = Type ID (drawable type)
  - `00c5` = Resource entry ID

### What Was in xxhdpi Split
From `scratch/apk_build/xxhdpi_decompiled/res/values/public.xml`:
- `exo_icon_vr` with ID `0x7f0800c5` ← This was missing!
- Other media3 UI drawables: `exo_ic_play`, `exo_ic_pause`, player controls, etc.

When apktool merged, this entry was lost, causing NotFoundException at runtime.

---

## Questions?

If playback still doesn't work after applying the fix:
1. Check logcat for new errors: `adb logcat | grep -i "exception\|error\|resource"`
2. Share the crash log
3. We can then debug specific resource/manifest issues
