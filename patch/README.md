# KPN TV+ AdSkip & Seek Unlock - patch guide

Version-independent patch implementation for **KPN TV+** on Android TV
(`com.kpn.kpnandroidtv`, the KPN TV+ Box / smart-TV app) and on phones and
tablets (`com.kpn.epg`). It maps the remote's fast-forward key to a +30 s seek,
makes ad breaks skippable, and keeps D-pad navigation and Play/Pause working as
before.

> **Status (Morphe route):** the Kotlin patch compiles into a loadable
> `.mpp` bundle that works in both the Morphe CLI and Morphe Manager (the bundle
> carries `classes.dex` next to the JVM `.class` entries, because Manager cannot
> load `.class` files), and the split-safe builder produces
> `patch/build/output/kpn-tvplus-adskip-morphe-splits.apks`. The patch has been
> verified in the output DEX (`AdSkipHook`, `dispatchKeyEvent`, `seekTo`, the
> ExoPlayer ad-seek guard, the IMA skippable override and the Flutter security
> checks are all present). The TV build is not yet smoke-tested against
> `com.kpn.kpnandroidtv`; Method B (apktool) remains the documented known-good
> fallback. See [MORPHE.md](../MORPHE.md) for the history and the remaining test
> matrix.

### Which app should I patch?

| Device | Package | APK |
| :--- | :--- | :--- |
| Android TV / KPN TV+ Box | `com.kpn.kpnandroidtv` | split bundle (`.apks`) |
| Phone / tablet | `com.kpn.epg` | split bundle (`.apks`) |

Do not use `com.kpn.epg` for a TV: it is the mobile app, even though it shares
the `com.kpn.tvplusapp.MainActivity` entry point with the TV build.

---

## 1. How the patch works

The KPN TV+ app is a Flutter app:

- The UI and the "is fast-forward blocked / trick-play" logic live in
  `lib/*/libapp.so` (native machine code). Patching that binary breaks on every
  update, so this patch never touches it.
- Playback goes through `androidx.media3.exoplayer` and the
  `io.flutter.plugins.videoplayer.VideoPlayer` / `native_video_view` wrappers, which
  are plain DEX classes with stable shapes.

The patch therefore:

1. Merges the `software.morphe.kpn` extension classes into the app
   (`extensions/kpn.mpe`).
2. Hooks `MainActivity.dispatchKeyEvent` and forwards key events to
   `AdSkipHook.onKeyDown` (D-pad 21/22 are passed straight through).
3. Registers every `VideoPlayer`/ExoPlayer instance and tracks
   `onIsPlayingChanged` so the overlay knows when a video is playing.
4. Forces the ExoPlayer "ignore seek while an ad is playing" guard to return
   `false` (`ExoPlayerImpl` seek guard, resolved through the
   `"seekTo ignored because an ad is playing"` log string, not a class name).
5. Forces the IMA `AdData.skippable()` value to `TRUE`.
6. Answers the Flutter security plugins in-process so the sideloaded build is
   treated as a correct, non-rooted install on a real device. The checks
   (`isRooted`, `isRealDevice`, `hasCorrectlyInstalled`, `isJailBroken`,
   `isDevelopmentModeEnable`, `usbDebuggingCheck`) are found by their string
   literals, so the obfuscated plugin class names do not matter.

Discovery is deliberately tolerant: every target is found through class names,
method shapes, field types or string literals, and a miss logs a `WARNING`
instead of aborting the whole patch. `result.json` still reports whether the
patch as a whole succeeded.

---

## 2. Directory layout

```text
patch/
  build.gradle.kts                         # compiles the patch + bundles the .mpp
  settings.gradle.kts
  gradlew, gradlew.bat, gradle/wrapper/    # Gradle 8.9 wrapper
  src/main/kotlin/software/morphe/patches/kpn/
    KpnAdSkipPatch.kt                      # patch entrypoint + all hook injection
  src/main/java/software/morphe/kpn/
    AdSkipHook.java                        # older draft, NOT compiled (see build.gradle.kts)
  smali/software/morphe/kpn/               # the real hook implementation (assembled to DEX)
    AdSkipHook.smali
    AdSkipButton.smali
    AdSkipOverlayTask.smali
    AdSkipPipWatcher.smali
    AdSkipForwardGate.smali
    AdSkipAccessibilityService.smali
  diffs/                                   # reference diffs for Method B
```

The extension is the six smali files above; they are assembled with the smali
assembler bundled in the Morphe Desktop jar and shipped inside the `.mpp` as
`extensions/kpn.mpe`.

---

## 3. Method A - Morphe patch bundle (recommended)

### 3.1 One command (build + patch + split-safe packaging)

```bash
python scratch/build_morphe_splits.py
```

The script:

1. downloads the pinned Morphe Desktop CLI
   (`morphe-desktop-2.2.0-all.jar`, cached in `patch/build/morphe/cache/`),
2. runs Gradle to build `patch/build/output/kpn-tvplus-adskip.mpp`,
3. extracts `base.apk` from the input bundle and patches **only** that file,
4. keeps the config splits untouched and re-signs **every** APK with one debug
   certificate,
5. verifies the hook classes and the security bypasses in the output DEX (the
   patch log reports each bypass, e.g. `Security bypass: isRooted -> false`),
6. writes `patch/build/output/kpn-tvplus-adskip-morphe-splits.apks`.

Any split bundle works, including the TV app's:

```bash
python scratch/build_morphe_splits.py \
  --input "KPN TV TV+.apks" \
  --output patch/build/output/kpn-tv-adskip-tv-splits.apks
```

Morphe Manager merges an `.apks` before patching, which breaks this app, so let
the script do the patching and signing instead of importing the archive into
Manager. Manager can still be used on a single `base.apk`; `--resign-only`
then combines that patched base with the original config splits:

```bash
python scratch/build_morphe_splits.py \
  --resign-only path/to/folder-with-base-and-splits \
  --output patch/build/output/kpn-tv-adskip-manager-splits.apks
```

The folder must contain `base.apk` (the patched one) and the untouched
`split_config.*.apk` files. This is what fixes
`INSTALL_FAILED_INVALID_APK: signatures are inconsistent`: Manager signs the
base with its own key, while the splits still carry the Play certificate.

Install:

```bash
adb install-multiple base.apk split_config.arm64_v8a.apk split_config.nl.apk split_config.xxhdpi.apk
# or sideload the whole bundle with Split APKs Installer (SAI)
```

### 3.2 Manual build

Morphe publishes its patcher and Gradle plugin on GitHub Packages only. Without
`read:packages` credentials this repo cannot resolve them, so the patch compiles
against the patcher bundled inside the Morphe Desktop CLI jar instead:

```bash
# build the bundle
cd patch
./gradlew bundleMpp -PmorpheDesktopJar=/path/to/morphe-desktop-2.2.0-all.jar
# -> build/output/kpn-tvplus-adskip.mpp
```

`MORPHE_DESKTOP_JAR` can be used instead of `-PmorpheDesktopJar`. The `.mpp`
declares `Patcher-Version: 2.4.0`, matching the patcher inside the CLI.

The bundle contains the compiled patch classes twice: as JVM `.class` files (used
by the CLI) and as `classes.dex` (used by Morphe Manager on Android, which
rejects a bundle without a DEX entry). `bundleMpp` runs D8 from Google's Maven
repository to produce the DEX, so the first build needs network access.

### 3.3 Manual patching (single APK)

Do **not** pass the original `.apks` bundle to the CLI: it merges the splits and
that corrupts this app's resource table (missing drawables / black screen). Patch
`base.apk` only:

```bash
java -jar morphe-desktop-2.2.0-all.jar patch \
  -p patch/build/output/kpn-tvplus-adskip.mpp \
  --exclusive \
  -e "KPN TV+ AdSkip & Seek Unlock" \
  --force \
  --continue-on-error \
  -r result.json \
  -o base-patched.apk \
  --keystore "$HOME/.android/debug.keystore" \
  --keystore-password android \
  --keystore-entry-alias androiddebugkey \
  --keystore-entry-password android \
  base.apk
```

Then sign every split with the same certificate and repack the `.apks` - the
`build_morphe_splits.py` script already does this (see section 5.5 of
[MORPHE.md](../MORPHE.md)).

### 3.4 Publishing the bundle

`patch/build/output/kpn-tvplus-adskip.mpp` is the release asset users need. Keep
the generated `.apks` as the ready-to-install artifact.

---

## 4. Method B - apktool (known-good fallback)

```bash
python scratch/build_patched_splits.py
# -> patch/build/output/kpn-tvplus-adskip-splits.apks
```

Manual outline:

1. `apktool d -r base.apk -o kpn_decompiled` (keep the original `resources.arsc`).
2. Copy all six files from `patch/smali/software/morphe/kpn/` into
   `kpn_decompiled/smali_classes3/software/morphe/kpn/`.
3. Inject the hooks (see `patch/diffs/*.patch`):
   - `VideoPlayer.seekTo(J)V`: call `registerPlayer` + `registerSeek` first.
   - `MainActivity.dispatchKeyEvent(Landroid/view/KeyEvent;)Z`: forward the key
     code to `AdSkipHook.onKeyDown` and return `true` when it handles the event.
     Note: the real class has **no** `onKeyDown` override, so patching
     `dispatchKeyEvent` is required.
4. `apktool b kpn_decompiled -o patched-unsigned.apk`, then sign each split with
   the same key (uber-apk-signer does v1+v2+v3 and zipalign).

---

## 5. Key bindings

| Key / button | Keycode | Action |
| :--- | :--- | :--- |
| Media fast-forward (or next) | 90 / 87 / 34 | +30 seconds |
| Media rewind (or previous) | 89 / 88 / 46 | -15 seconds |
| Play/Pause | 85 / 47 / 29 | Skip the current ad break (+4:30) |
| `Z` | 54 | Undo the last jump |
| D-pad left/right | 21 / 22 | Passed through unchanged |

`adb logcat -s KPN_AdSkip` plus `/sdcard/Download/kpn_debug.log` show the key
codes the hook actually receives, which is the fastest way to diagnose a remote
that emits different codes.

---

## 6. Troubleshooting

- **Morphe imports the `.mpp` with a warning but the KPN app never appears.**
  The bundle has no `classes.dex` entry. Morphe Manager cannot load JVM `.class`
  files and rejects the whole source. Rebuild with `./gradlew bundleMpp` or
  `scratch/build_morphe_splits.py`; both now dex the patch classes and refuse a
  bundle without the dex entry.
- **The app list shows KPN but not the app you have installed.** KPN ships
  `com.kpn.kpnandroidtv` for Android TV and `com.kpn.epg` for phones/tablets. Pick
  the APK that matches the package, not the device form factor.
- **Patch log says a target was skipped.** The `[KPN AdSkip] WARNING: ...` lines
  name the missing class/method; the rest of the hooks still apply. Run with
  `--force --continue-on-error` and check `result.json`.
- **`+30 s` does nothing during an ad.** The ExoPlayer ad-seek guard was not
  resolved. Confirm the patch log mentions `ad seek bypass`; if not, the log
  string changed in that app version.
- **App installs but shows a black player.** The splits were merged. Rebuild with
  `scratch/build_morphe_splits.py`, which never merges them.
- **App refuses to play or reports an integrity problem.** The Flutter security
  checks were not bypassed. The patch log should contain seven
  `Security bypass: ...` lines; if it does not, the plugin's string literals
  changed in that app version and `SECURITY_CHECKS` in `KpnAdSkipPatch.kt` needs
  updating.
- **`INSTALL_FAILED_INVALID_APK: signatures are inconsistent`.** Not all splits
  are signed with the same certificate. This happens when Manager patched
  `base.apk` (its own key) and you combined it with the Play-signed config splits.
  Run the script with `--resign-only <folder>` to re-sign every APK with one
  certificate, or patch the original bundle with `--input` so the script patches
  and signs the whole set.
- **GitHub Packages 401 while building.** Expected on machines without
  `read:packages`; the local-jar build path in section 3.2 avoids the registry.
