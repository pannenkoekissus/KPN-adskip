# KPN TV+ AdSkip & Seek Unblocker — APK Patch Guide

This repository contains the version-independent patch implementation for **KPN TV+ (`com.kpn.epg`)** on Android / Android TV.

---

## 1. Why This Patch Works Across Multiple Versions

The KPN TV+ Android app is built with **Flutter**:
- Application UI & BLoC logic (`isFastForwardBlocked`, `isTrickPlay`) is compiled into ARM64 machine code (`lib/arm64-v8a/libapp.so`). Modifying this binary directly breaks on every update because function memory offsets shift with each compiler pass.
- Video playback is handled by standard native Android plugins: **`io.flutter.plugins.videoplayer`** using **`androidx.media3.exoplayer.ExoPlayer`** in `classes3.dex`.

By targeting the **Android Media3 / VideoPlayer DEX interface** rather than internal Flutter machine code, this patch retains compatibility across future versions.

---

## 2. Directory Structure

```text
patch/
├── build.gradle.kts                          # Morphe / ReVanced gradle build configuration
├── settings.gradle.kts
├── src/main/
│   ├── java/software/morphe/kpn/
│   │   └── AdSkipHook.java                   # Core runtime hook & ExoPlayer controller
│   └── kotlin/software/morphe/patches/kpn/
│       ├── KpnAdSkipPatch.kt                 # Morphe / ReVanced Patcher entrypoint
│       └── fingerprints/
│           ├── VideoPlayerFingerprint.kt     # Pattern-match for seekTo() in VideoPlayer
│           └── MainActivityFingerprint.kt    # Pattern-match for onKeyDown() in MainActivity
├── smali/
│   └── software/morphe/kpn/
│       └── AdSkipHook.smali                  # Ready-to-inject Dalvik bytecode
└── diffs/
    ├── VideoPlayer.smali.patch               # Exact line diff for apktool workflows
    └── MainActivity.smali.patch              # Exact line diff for key handler injection
```

---

## 3. How to Apply the Patch

### Method A: Using Morphe Patcher / ReVanced CLI (Recommended)

1. Build or package the patch bundle:
   ```bash
   ./gradlew build
   ```
2. Apply using Morphe CLI or ReVanced CLI:
   ```bash
   java -jar morphe-cli.jar patch \
     --patch-bundle build/libs/kpn-tvplus-adskip-patch-2.1.0.jar \
     --apk base.apk \
     --out kpn-tvplus-patched.apk
   ```

### Method B: Manual Smali Patching (Using Apktool)

1. **Decompile base APK:**
   ```bash
   apktool d -r base.apk -o kpn_decompiled
   ```

2. **Copy the Hook class:**
   Copy [`AdSkipHook.smali`](file:///c:/Users/Gebruiker/KPN-adskip/patch/smali/software/morphe/kpn/AdSkipHook.smali) into:
   ```text
   kpn_decompiled/smali_classes3/software/morphe/kpn/AdSkipHook.smali
   ```

3. **Apply diffs or edit the two files:**
   - In `kpn_decompiled/smali_classes3/io/flutter/plugins/videoplayer/VideoPlayer.smali`:
     Inside the `.method public seekTo(J)V` method, add at the beginning:
     ```smali
     invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V
     ```
   - In `kpn_decompiled/smali_classes3/com/kpn/tvplusapp/MainActivity.smali`:
     Inside `.method public onKeyDown(ILandroid/view/KeyEvent;)Z`, add:
     ```smali
     invoke-static {p1, p2}, Lsoftware/morphe/kpn/AdSkipHook;->onKeyDown(ILandroid/view/KeyEvent;)Z
     move-result v0
     if-eqz v0, :cond_skip_def
     const/4 v0, 0x1
     return v0
     :cond_skip_def
     ```

4. **Rebuild & Sign:**
   ```bash
   apktool b kpn_decompiled -o kpn-patched-unsigned.apk
   uber-apk-signer -a kpn-patched-unsigned.apk
   ```

---

## 4. Keybindings & Shortcuts

| Key / Button | Action |
| :--- | :--- |
| **Media Fast Forward / Next** | +30 seconds jump |
| **Media Rewind / Previous** | -15 seconds jump |
| **Key `S` or `A`** | Skip commercial ad break in 1 jump (+4:30 min) |
| **Key `Z`** | Undo last jump |
| **D-Pad Right (with Shift/Alt)** | Skip commercial ad break in 1 jump |
