# Making the KPN TV+ patch work with Morphe, cross-version

Status: upstream `1ce3311` (one commit before `main`). This document records why the
Morphe route in `patch/README.md` currently fails, the command you would use once it
is fixed, and everything still needed to make it genuinely version-independent.

Scope note: the remote-button behaviour is treated as intentional — keycode **90
(⏩) → +30 s**, keycode **85 (⏯) → skip ad break**, and D-pad left/right (21/22)
passed through. Play/Pause being bound is not a defect.

---

## 1. Short answer

The Morphe/Kotlin patch is an **unfinished alternative**, not the shipping patch.
The working route in this repo is the apktool split build
(`scratch/build_patched_splits.py` / `build_armeabi_v7a.py`), which produces
`patch/build/output/kpn-tvplus-adskip-splits.apks`.

Nothing in the repo currently produces a patch bundle Morphe can load, and even if
it did, the fingerprint would not match this app.

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

## 4. Corrected CLI once a real `.mpp` exists

```bash
java -jar morphe-desktop-*-all.jar patch \
  -p patches.mpp \
  --exclusive \
  -e "KPN TV+ AdSkip & Seek Unlock" \
  --force \
  --continue-on-error \
  -r result.json \
  -o out.apks \
  "KPN TV+.apks"
```

Notes: `--exclusive -e` selects only this patch; `--force` bypasses version
verification; `--continue-on-error` lets other patch steps still report;
`-r result.json` is essential for diagnosing fingerprint misses. If the app has
multi-dex / framework-mixing issues, retry with `--bytecode-mode FULL`.

---

## 5. What is still needed for a working, cross-version Morphe patch

### 5.1 Build and bundle

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

- Implement step 3: parse `AdSkipHook.smali` into a `ClassDef` (smali parser /
  `DexBuilder`) and add it to the patch's `BytecodeContext`, or ship the hook as a
  compiled DEX and merge it into the target APK.
- Assert after patching that `Lsoftware/morphe/kpn/AdSkipHook;` exists in the DEX;
  add a build-time check so a future regression is caught.
- Generate the Java reference source from the smali (or vice versa) so the two
  copies cannot diverge.

### 5.4 Stable registration point

- `VideoPlayer.seekTo(J)V` only fires after the first seek. To register the player
  earlier, also hook a constructor or `ExoPlayer` creation path, with a fallback
  chain of fingerprints.
- Consider a generic entry point such as `Application.onCreate` for installing a
  lifecycle callback / window-callback wrapper; this is more robust across app
  versions but needs a stable fingerprint of its own.

### 5.5 Split packaging

- Do not feed the combined `.apks` into Morphe if it auto-merges splits. Extract
  `base.apk`, patch that, keep every config split byte-identical, then reassemble
  and sign all splits with **one** certificate (Android requires matching certs).
- Verify after repacking that density/locale resources such as `exo_icon_vr` are
  still present in their original splits, and smoke-test playback (no `PlayerView`
  inflate crash / black screen).
- Add this repack-and-sign step to the Morphe workflow script, not just the older
  Python build scripts.

### 5.6 Key bindings across remote variants

- Android keycodes are stable, so use literals (`90` ⏩, `85` ⏯, ignore `21`/`22`)
  rather than constants introduced at different API levels.
- Keep the D-pad early-return added in `1ce3311`.
- Log unrecognised key-down codes so a different KPN remote (e.g. one emitting
  `87`/`88` MEDIA_NEXT/PREVIOUS) can be diagnosed from `adb logcat -s KPN_AdSkip`.
  Optional aliases should be opt-in config, never the default.
- Keep Play/Pause → skip ad break as intended behaviour.

### 5.7 Testing matrix

- CI job that, for every supported KPN TV+ version: downloads the base APK, runs
  the patch with `--force --continue-on-error`, asserts from `result.json` that each
  fingerprint resolved, inspects the output DEX for `AdSkipHook`, verifies split
  integrity, and signs it.
- On-device smoke test with `adb logcat -s KPN_AdSkip`: press ⏩ during an ad and
  confirm `KEYDOWN code=90` plus a 30 s jump; press D-pad and ⏯ and confirm no
  jump and normal navigation/playback.
- Add a negative test that an unsupported app version fails with a clear message
  rather than silently producing a half-patched APK.

### 5.8 Documentation

- Replace README Method A with the current `.mpp` CLI command from §4.
- Keep Method B (`apktool`) documented and mark it as the known-good route until
  the Morphe path passes the test matrix.
- Link this file from `patch/README.md`.

---

## 6. Ordered work plan

1. Add Gradle wrapper + JDK 17 toolchain; fix Android stubs; get `./gradlew build`
   running.
2. Switch to the Morphe patch plugin so the build emits `patches.mpp`.
3. Implement real hook-class injection and remove the placeholder comment.
4. Rewrite both fingerprints for `dispatchKeyEvent` and stable ExoPlayer/Media3
   matching; make misses non-fatal.
5. Add split-safe repack + single-cert signing to the Morphe flow.
6. Publish the `.mpp` and update the README CLI instructions.
7. Add the multi-version CI matrix and on-device smoke test.

Definition of done: a clean machine can clone the repo, run one documented command,
produce `out.apks`, install it on a KPN TV+ box, and use ⏩ for +30 s across all
tested app versions without losing D-pad or Play/Pause behaviour.

---

## 7. Files involved

- `patch/build.gradle.kts`, `patch/settings.gradle.kts` — build plugin, deps, stubs,
  wrapper.
- `patch/src/main/kotlin/software/morphe/patches/kpn/KpnAdSkipPatch.kt` — hook
  injection and soft failures.
- `patch/src/main/kotlin/software/morphe/patches/kpn/fingerprints/*.kt` — version-
  tolerant fingerprints.
- `patch/src/main/java/software/morphe/kpn/AdSkipHook.java` and
  `patch/smali/software/morphe/kpn/AdSkipHook.smali` — single source of truth for
  key logic.
- `patch/README.md` — corrected CLI + known-good route.
- `scratch/build_patched_splits.py` — split/repack logic to port into the Morphe
  flow.

## 8. Non-goals / separate concerns

- The browser userscript and Chrome extension have their own unrelated key bindings.
- The root `KPN TV+.apks` is stock/unpatched; it contains no `AdSkipHook` class.
- Broader ad-skipping/overlay mechanisms are out of scope unless they block the
  remote-button patch.
