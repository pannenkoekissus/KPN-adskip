# Release assets

All `.apks` bundles are split installs signed with the Android debug certificate.
Uninstall the Play Store build first; Android refuses to update an app whose
signing certificate changed:

```bash
adb uninstall com.kpn.epg            # phone / tablet build
adb uninstall com.kpn.kpnandroidtv   # Android TV build
```

KPN ships two different apps, and patching the wrong one produces the wrong
result:

| Device | Package | Main activity |
| :--- | :--- | :--- |
| Phone / tablet | `com.kpn.epg` | `com.kpn.tvplusapp.MainActivity` |
| Android TV / TV+ Box | `com.kpn.kpnandroidtv` | `com.kpn.tvplusapp.MainActivity` |

## Assets

| Asset | Target | Notes |
| :--- | :--- | :--- |
| `kpn-tvplus-adskip-morphe-splits.apks` | **phone / tablet** (`com.kpn.epg`) | Built by `scratch/build_morphe_splits.py` from `KPN TV+.apks`; patches only `base.apk`, keeps the config splits byte-identical, and includes the seek/ad-break hooks and the Flutter security bypasses. |
| `kpn-tvplus-adskip.mpp` | any Morphe CLI or Morphe Manager | Patch bundle for Morphe Desktop 2.2.0+ / Manager (patcher 2.4.0). Declares both `com.kpn.kpnandroidtv` (TV) and `com.kpn.epg` (mobile). Feed it the app's **base APK**, not the original `.apks` bundle (the CLI would merge the splits). |
| `kpn-tvplus-adskip-splits-new.apks` | phone / tablet (`com.kpn.epg`) | apktool fallback, includes the TV-remote patch. |
| `kpn-tvplus-adskip-splits.apks` | phone / tablet (`com.kpn.epg`) | apktool fallback, does not include the TV-remote patch. |
| `kpn-tvplus-adskip-splits-armeabiv7a.apks` | armeabi-v7a phones/tablets | apktool fallback. |
| `kpn-tvplus-adskip-splits-armeabiv7a-tv.apks` | armeabi-v7a TVs | apktool fallback. |

There is no ready-made TV split bundle yet: the repository only contains the
mobile `KPN TV+.apks`. On a TV, use the `.mpp` with the TV's own split bundle or
pull the TV APK first:

```bash
adb shell pm path com.kpn.kpnandroidtv
adb pull <each path> .
```

Install a split bundle with:

```bash
adb install-multiple base.apk split_config.arm64_v8a.apk split_config.nl.apk split_config.xxhdpi.apk
```

or open the `.apks` in Split APKs Installer (SAI).

## Importing the `.mpp`

Morphe Manager loads patches from `classes.dex` inside the bundle and refuses a
bundle without a non-empty dex entry ("Patch bundle is missing dex entries"), so
the `.mpp` must be built with `./gradlew bundleMpp` (or
`scratch/build_morphe_splits.py`), not assembled by hand from the `.class` files.
When the import succeeds, the source lists both apps; only the one matching your
device/build appears, tagged TV or not.

## Building these assets

```bash
# Recommended Morphe route (downloads the CLI, builds the .mpp, patches base.apk,
# re-signs the untouched config splits, writes the .apks)
python scratch/build_morphe_splits.py

# Any other split bundle (for example the TV app)
python scratch/build_morphe_splits.py --input "KPN TV TV+.apks" --output tv.apks

# Base already patched elsewhere (for example by Morphe Manager): only re-sign
python scratch/build_morphe_splits.py --resign-only <folder-with-base-and-splits>

# apktool fallback (known-good, does not use Morphe)
python scratch/build_patched_splits.py
```

The Morphe artifacts are:

- `patch/build/output/kpn-tvplus-adskip.mpp`
- `patch/build/output/kpn-tvplus-adskip-morphe-splits.apks`

See [MORPHE.md](MORPHE.md) for the build details and the remaining on-device test
matrix.
