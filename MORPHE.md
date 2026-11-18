# Making the KPN TV+ patch work with Morphe, cross-version

Status: upstream `1ce3311` (one commit before `main`). This document records why the
Morphe route in `patch/README.md` currently fails, the command you would use once it
is fixed, and everything still needed to make it genuinely version-independent.

Scope note: the remote-button behaviour is treated as intentional — keycode **90
(⏩) → +30 s**, keycode **85 (⏯) → skip ad break**, and D-pad left/right (21/22)
passed through. Play/Pause being bound is not a defect.

---

## 0. Implementation status

Done and verified in this repository:

- `patch/` has a Gradle 8.9 wrapper and a build that emits
  `patch/build/output/kpn-tvplus-adskip.mpp` (a loadable Morphe bundle with the
  smali extension packaged as `extensions/kpn.mpe`).
- The GitHub Packages registry (401 without `read:packages` credentials) is worked
  around by compiling against the patcher bundled inside the Morphe Desktop CLI jar
  (`-PmorpheDesktopJar=...` / `MORPHE_DESKTOP_JAR`).
- `KpnAdSkipPatch.kt` implements all hooks with tolerant discovery (class names,
  method shapes, field types and string literals) and warns instead of aborting on
  a miss: `dispatchKeyEvent`, `onCreate`, PiP callback, `VideoPlayer.seekTo` /
  `<init>` / lifecycle, ExoPlayer field registrations, `onIsPlayingChanged`, the
  ExoPlayer ad-seek guard, IMA `skippable()` and the Flutter security checks
  (`isRooted`, `isRealDevice`, `hasCorrectlyInstalled`, `isJailBroken`,
  `isDevelopmentModeEnable`, `usbDebuggingCheck`). The security bypasses answer
  `MethodChannel.Result` directly, matching the known-good apktool patch.
  The patch declares both KPN packages: `com.kpn.kpnandroidtv` as the TV app and
  `com.kpn.epg` as the mobile app. Only the mobile APK (`KPN TV+.apks`) is
  currently in the repository and covered by the static checks.
- `scratch/build_morphe_splits.py` implements section 5.5: patch `base.apk` only,
  keep the config splits' payload byte-identical, sign all splits with one
  certificate and write
  `patch/build/output/kpn-tvplus-adskip-morphe-splits.apks`.
- The output DEX was inspected: `AdSkipHook` + the five other extension classes,
  the `dispatchKeyEvent` hook, `seekTo` hook, `ExoPlayerImpl.h()Z → false`,
  `AutoValue_AdData.skippable() → TRUE` and all seven security-check early
  returns are present, and `resources.arsc` in the patched base is unchanged.
  The final `.apks` keeps every config-split payload byte-identical (only the
  Play `stamp-cert-sha256` and the signatures differ) and all four APKs share one
  debug certificate.
- Both artifacts are published on the `v1.0.0` release:
  `kpn-tvplus-adskip.mpp` and `kpn-tvplus-adskip-morphe-splits.apks`. The release
  notes mark the Morphe bundle as recommended for arm64 Android TV and keep the
  apktool bundles as fallbacks.

The Manager import path is fixed and confirmed: the bundle now carries
`classes.dex`, and importing it into Morphe Manager 2.6.0 on an API 35 emulator
adds the source without a warning and lists both `KPN TV+ (mobile)` and
`KPN TV+ Android TV`. Before the DEX entry was added, Manager logged
`Unable to open .../patches.dm` and showed neither app.

Still open: the on-device smoke test (section 5.7) and the multi-version CI
matrix. No `com.kpn.kpnandroidtv` APK is in the repository yet, so the TV build
is not verified against the real TV app.

Until that passes, the apktool route (`scratch/build_patched_splits.py`) remains the
known-good fallback.

---

## 1. Short answer

The Morphe/Kotlin patch is now the maintained route: `python
scratch/build_morphe_splits.py` builds the `.mpp`, patches only `base.apk`, and
produces `patch/build/output/kpn-tvplus-adskip-morphe-splits.apks`. The earlier
version of this document described an unfinished alternative; sections 2 and 3 are
kept as the record of why it did not work before the rewrite.

The apktool split build (`scratch/build_patched_splits.py` /
`build_armeabi_v7a.py`, producing `patch/build/output/kpn-tvplus-adskip-splits.apks`)
stays documented as the known-good fallback until the Morphe output passes the
on-device smoke test in section 5.7.

---

## 2. What `patch/README.md` tells you to do, and why it fails

```bash
./gradlew build
java -jar morphe-cli.jar patch \
  --patch-bundle build/libs/kpn-tvplus-adskip-patch-2.1.0.jar \
  --apk base.apk \
  --out kpn-tvplus-patched.apk
```

| Step | Problem |
|---|---|
| `./gradlew build` | No `gradlew` / `gradlew.bat` exists in the repo. |
| Build config | Plain `kotlin("jvm")` produces a normal JAR, not a Morphe `.mpp` patch bundle. |
| Dependencies | `com.google.android:android:4.1.1.4` is API 16; `AdSkipHook.java` uses `KEYCODE_MEDIA_SKIP_FORWARD` and `MediaStore.Downloads`, which do not exist there, so compilation fails. |
| `--patch-bundle ...jar` | The prebuilt `kpn-tvplus-adskip-patch-2.1.0.jar` contains **only** `software/morphe/kpn/AdSkipHook.class` — no patch class and no DEX. It is not loadable. |
| `--apk / --out` flags | Obsolete Morphe CLI syntax. Current CLI uses `patch -p <bundle.mpp> -o <out> <input.apks>`. |

---

## 3. Verified blockers in the current source

1. **`MainActivityFingerprint.kt` targets a method that does not exist.** It looks for
   `onKeyDown(I, Landroid/view/KeyEvent;)Z` in a class whose name contains
   `MainActivity` or `FlutterActivity`. The real class,
   `com.kpn.tvplusapp.MainActivity`, only defines
   `dispatchKeyEvent(Landroid/view/KeyEvent;)Z` (confirmed by decompiling the stock
   base APK). The fingerprint never resolves.
2. **The key hook is silently skipped.** `KpnAdSkipPatch.kt:44-58` is wrapped in
   `if (mainActivityResult != null)`, so a fingerprint miss means no key hook at
   all, with only a nullable result and no error.
3. **The hook class is never injected.** `KpnAdSkipPatch.kt:60-62` is a comment:
   `// In Morphe/ReVanced builds, AdSkipHook class is packaged alongside the patch`.
   No `ClassDef` is added to the `BytecodeContext`. Even a resolved fingerprint would
   produce `NoClassDefFoundError` at runtime.
4. **The other fingerprint is brittle.** `VideoPlayerFingerprint` requires
   `definingClass.contains("VideoPlayer"|"videoplayer")` plus an exact three-opcode
   sequence (`IGET_OBJECT, IF_EQZ, INVOKE_INTERFACE`). Any rename, inlining or R8
   change breaks it.
5. **`AdSkipHook.smali` and `AdSkipHook.java` are two hand-maintained copies** that
   can drift (they already disagree on key bindings in older revisions).
6. **Morphe auto-merges `.apks`.** This app must keep splits unmerged: the repo's
   own build notes record that merging corrupts the shared resource table, causing
   missing drawables and a `PlayerView` inflate crash (black screen).

---

## 4. CLI used by the build script

The CLI auto-merges a passed `.apks` bundle, which this app cannot tolerate, so the
input is the extracted `base.apk` and the split-safe packaging happens afterwards:

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

Notes: `--exclusive -e` selects only this patch; `--force` bypasses version
verification; `--continue-on-error` lets the tolerant hooks report misses without
aborting; `-r result.json` records the result. Pass the same `--keystore` arguments
to the CLI that `scratch/build_morphe_splits.py` uses (the Android debug keystore)
so the base and the re-signed config splits share one certificate. If the app has
multi-dex / framework-mixing issues, retry with `--bytecode-mode FULL`.

---

## 5. What was needed for a working, cross-version Morphe patch

Each subsection records the requirement and its current status.

### 5.1 Build and bundle

**Status: done, with one workaround.** A Gradle 8.9 wrapper is committed and
`./gradlew bundleMpp` emits `kpn-tvplus-adskip.mpp`. Morphe's own patch-build
plugin and patcher live on GitHub Packages, which returns 401 without
`read:packages` credentials, so the build compiles against the patcher bundled in
`morphe-desktop-2.2.0-all.jar` (patcher 2.4.0) and packages the bundle itself. The
obsolete Java draft in `src/main/java` is excluded from compilation; the smali
extension is the single source of truth for the hook logic.

The bundle ships the patch classes twice: as JVM `.class` entries for the CLI and
as `classes.dex` for Morphe Manager. Manager's `PatchBundle.Loader` rejects a
bundle with no non-empty `.dex` entry with "Patch bundle is missing dex entries",
which shows up as an import warning and an empty app list. D8 (R8 on Google's
Maven repository) produces the DEX in `dexPatches`; the split builder refuses a
bundle without both entry kinds.

- Install JDK 17+ (or 21) and Gradle, or commit a Gradle wrapper so `./gradlew build`
  works on a clean machine.
- Replace the plain `kotlin("jvm")` plugin with Morphe's patch-build plugin (the one
  used by `MorpheApp/morphe-patches`) so the output is `patches.mpp`, not a plain JAR.
- Align the patcher dependency with the Morphe CLI version you ship against
  (`app.revanced:patcher` / Morphe fork). A patch compiled against a mismatched
  patcher API will fail to load.
- Replace API-16 stubs with API 33+ Android stubs. Better still, remove the two
  problematic references: use the literal `90` instead of
  `KEYCODE_MEDIA_SKIP_FORWARD`, and provide a legacy fallback for
  `MediaStore.Downloads` (it was added in API 29).
- Publish the `.mpp` as a release asset so users do not have to build it.

### 5.2 Fingerprints that survive new app versions

**Status: done.** The brittle `MethodFingerprint` objects were replaced by
tolerant discovery inside `KpnAdSkipPatch.kt` (no `app.revanced` imports). Every
target is resolved through a preferred name plus shape/type/string hints, and a miss
logs `[KPN AdSkip] WARNING: ...` instead of failing the patch.

- Rewrite `MainActivityFingerprint` for
  `dispatchKeyEvent(Landroid/view/KeyEvent;)Z`. Do **not** require the class name to
  contain `MainActivity`: find any class extending `android.app.Activity` /
  `androidx.fragment.app.FragmentActivity` / `io.flutter.embedding.android.FlutterActivity`
  that overrides `dispatchKeyEvent`. Keep the class-name check as a *preferred hint*,
  not a hard requirement.
- Inside that hook, call
  `AdSkipHook.onKeyDown(event.getKeyCode(), event)` and consume when it returns
  `true`; this keeps the existing single source of key logic.
- Rewrite `VideoPlayerFingerprint` to match on stable semantics rather than class
  names and exact opcode order: method name `seekTo`, return `V`, single `J`
  parameter, and accept both `io.flutter.plugins.videoplayer.VideoPlayer` and
  Media3 `androidx.media3.exoplayer.ExoPlayer` implementations. Use opcodes/strings
  only as soft hints.
- Provide multiple candidate fingerprints and treat a miss as a **warning**, not a
  hard failure: a new app version should degrade gracefully (no key hook) rather
  than abort patching.
- Log every fingerprint resolution into `result.json` and add a `--dry-run`-style
  self-test that reports which fingerprints matched before writing any APK.
- Avoid `definingClass.contains(...)` as the sole discriminator; R8/ProGuard can
  rename classes between releases.

### 5.3 Actually inject the hook class

**Status: done.** The six smali classes are assembled into `extensions/kpn.mpe`
and merged by `extendWith("extensions/kpn.mpe")`. The patch aborts with a clear
error if `Lsoftware/morphe/kpn/AdSkipHook;` is missing after the merge, and
`build_morphe_splits.py` re-checks the output DEX before signing.

- Implement step 3: parse `AdSkipHook.smali` into a `ClassDef` (smali parser /
  `DexBuilder`) and add it to the patch's `BytecodeContext`, or ship the hook as a
  compiled DEX and merge it into the target APK.
- Assert after patching that `Lsoftware/morphe/kpn/AdSkipHook;` exists in the DEX;
  add a build-time check so a future regression is caught.
- Generate the Java reference source from the smali (or vice versa) so the two
  copies cannot diverge.

### 5.4 Stable registration point

**Status: done.** `MainActivity.onCreate` calls `registerActivity`, the
`VideoPlayer` constructor registers the wrapper right after the super call, and
every assignment to a player-typed field (both
`androidx/media3/exoplayer/ExoPlayer` and the obfuscated
`androidx/media3/exoplayer/c`) registers the concrete ExoPlayer. `seekTo(J)V` and
the lifecycle methods stay hooked as a fallback chain.

- `VideoPlayer.seekTo(J)V` only fires after the first seek. To register the player
  earlier, also hook a constructor or `ExoPlayer` creation path, with a fallback
  chain of fingerprints.
- Consider a generic entry point such as `Application.onCreate` for installing a
  lifecycle callback / window-callback wrapper; this is more robust across app
  versions but needs a stable fingerprint of its own.

### 5.5 Split packaging

**Status: done.** `scratch/build_morphe_splits.py` implements this end to end:
extract `base.apk`, patch only that file, re-sign the untouched config splits with
the same debug certificate, verify that every non-`META-INF` entry of each config
split is byte-identical (only the Play `stamp-cert-sha256` is dropped when
re-signing), verify that all four APKs share one certificate, and write
`kpn-tvplus-adskip-morphe-splits.apks`. It also checks that `resources.arsc` in the
patched base is unchanged.

- Do not feed the combined `.apks` into Morphe if it auto-merges splits. Extract
  `base.apk`, patch that, keep every config split byte-identical, then reassemble
  and sign all splits with **one** certificate (Android requires matching certs).
- Verify after repacking that density/locale resources such as `exo_icon_vr` are
  still present in their original splits, and smoke-test playback (no `PlayerView`
  inflate crash / black screen).
- Add this repack-and-sign step to the Morphe workflow script, not just the older
  Python build scripts.

### 5.6 Key bindings across remote variants

**Status: done.** The hook uses numeric literals, keeps the D-pad early return in
`dispatchKeyEvent`, logs unrecognised key-downs, and keeps Play/Pause → skip ad
break.

- Android keycodes are stable, so use literals (`90` ⏩, `85` ⏯, ignore `21`/`22`)
  rather than constants introduced at different API levels.
- Keep the D-pad early-return added in `1ce3311`.
- Log unrecognised key-down codes so a different KPN remote (e.g. one emitting
  `87`/`88` MEDIA_NEXT/PREVIOUS) can be diagnosed from `adb logcat -s KPN_AdSkip`.
  Optional aliases should be opt-in config, never the default.
- Keep Play/Pause → skip ad break as intended behaviour.

### 5.7 Testing matrix

**Status: partially done.** The static checks (output DEX contents,
`resources.arsc` integrity, split payloads, certificate match) are implemented in
`build_morphe_splits.py`, and the Morphe Manager import was verified on an
emulator. The on-device smoke test and the multi-version CI matrix still have to
be run.

- CI job that, for every supported KPN TV+ version: downloads the base APK, runs
  the patch with `--force --continue-on-error`, asserts from `result.json` that each
  fingerprint resolved, inspects the output DEX for `AdSkipHook`, verifies split
  integrity, and signs it.
- Import the `.mpp` into Morphe Manager and confirm both KPN apps appear in the
  source's app list. **Verified** with Manager 2.6.0 on an API 35 emulator: no
  import warning and both apps are listed. Manager reads `classes.dex` from the
  bundle and rejects the whole source when that entry is missing.
- Pull `com.kpn.kpnandroidtv` from a TV or the TV+ Box
  (`adb shell pm path com.kpn.kpnandroidtv`, then `adb pull` each path) and run the
  same static checks. The two apps share the `com.kpn.tvplusapp.MainActivity` entry
  point, but the TV build's obfuscation and version differ, so the hint-based
  discovery still needs to be verified against it.
- On-device smoke test with `adb logcat -s KPN_AdSkip`: press ⏩ during an ad and
  confirm `KEYDOWN code=90` plus a 30 s jump; press D-pad and ⏯ and confirm no
  jump and normal navigation/playback.
- Add a negative test that an unsupported app version fails with a clear message
  rather than silently producing a half-patched APK.

### 5.8 Documentation

**Status: done.** `patch/README.md` now documents the `.mpp` CLI, the one-command
split-safe build, and Method B as the known-good fallback, and links back to this
file.

- Replace README Method A with the current `.mpp` CLI command from §4.
- Keep Method B (`apktool`) documented and mark it as the known-good route until
  the Morphe path passes the test matrix.
- Link this file from `patch/README.md`.

---

## 6. Ordered work plan

1. ✅ Add Gradle wrapper + JDK 17 toolchain; fix Android stubs; get `./gradlew build`
   running.
2. ✅ Switch to the Morphe patch plugin so the build emits `patches.mpp`. (Worked
   around: no GitHub Packages credentials, so the bundle is assembled against the
   patcher inside the Morphe Desktop CLI jar.)
3. ✅ Implement real hook-class injection and remove the placeholder comment.
4. ✅ Rewrite both fingerprints for `dispatchKeyEvent` and stable ExoPlayer/Media3
   matching; make misses non-fatal.
5. ✅ Add split-safe repack + single-cert signing to the Morphe flow
   (`scratch/build_morphe_splits.py`).
6. ✅ Publish the `.mpp` and update the README CLI instructions. (The `.mpp` is
   built at `patch/build/output/kpn-tvplus-adskip.mpp` and attached to the
   `v1.0.0` release together with the split-safe `.apks`.)
7. ⬜ Add the multi-version CI matrix and on-device smoke test.

Definition of done: a clean machine can clone the repo, run one documented command,
produce `out.apks`, install it on a KPN TV+ box, and use ⏩ for +30 s across all
tested app versions without losing D-pad or Play/Pause behaviour.

---

## 7. Files involved

- `patch/build.gradle.kts`, `patch/settings.gradle.kts` — local-jar build, extension
  assembly and `.mpp` packaging; Gradle 8.9 wrapper in `patch/gradle/`.
- `patch/src/main/kotlin/software/morphe/patches/kpn/KpnAdSkipPatch.kt` — tolerant
  discovery, hook injection, soft failures.
- `patch/smali/software/morphe/kpn/*.smali` — the hook implementation packaged as
  `extensions/kpn.mpe` (six classes).
- `patch/src/main/java/software/morphe/kpn/AdSkipHook.java` — older draft, excluded
  from compilation; do not use it as the reference.
- `patch/README.md` — current `.mpp` CLI, one-command build, known-good fallback.
- `scratch/build_morphe_splits.py` — download CLI, build `.mpp`, patch `base.apk`,
  verify, sign all splits, repack the `.apks`.
- `scratch/build_patched_splits.py` — apktool fallback (known-good until the
  on-device test passes).

## 8. Non-goals / separate concerns

- The browser userscript and Chrome extension have their own unrelated key bindings.
- The root `KPN TV+.apks` is stock/unpatched; it contains no `AdSkipHook` class.
- Broader ad-skipping/overlay mechanisms are out of scope unless they block the
  remote-button patch.
