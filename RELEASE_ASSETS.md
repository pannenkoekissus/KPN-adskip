# Release assets

All `.apks` bundles are split installs signed with the Android debug certificate.
Uninstall the Play Store build first (`adb uninstall com.kpn.epg`); Android refuses
to update an app whose signing certificate changed.

| Asset | Target device | Notes |
| :--- | :--- | :--- |
| `kpn-tvplus-adskip-morphe-splits.apks` | arm64 Android TV | **Recommended.** Built by `scratch/build_morphe_splits.py`; patches only `base.apk`, keeps the config splits byte-identical, includes the TV-remote +30 s / ad-break hooks and the Flutter security bypasses. |
| `kpn-tvplus-adskip-splits-new.apks` | arm64 | apktool fallback, includes the TV-remote patch. |
| `kpn-tvplus-adskip-splits.apks` | arm64 | apktool fallback, does not include the TV-remote patch. |
| `kpn-tvplus-adskip-splits-armeabiv7a.apks` | armeabi-v7a non-TV devices | apktool fallback. |
| `kpn-tvplus-adskip-splits-armeabiv7a-tv.apks` | armeabi-v7a TVs | apktool fallback. |
| `kpn-tvplus-adskip.mpp` | any Morphe CLI | Patch bundle for Morphe Desktop 2.2.0+ (patcher 2.4.0). Feed it `base.apk` only, not the original `.apks` bundle (the CLI would merge the splits). |

Install a split bundle with:

```bash
adb install-multiple base.apk split_config.arm64_v8a.apk split_config.nl.apk split_config.xxhdpi.apk
```

or open the `.apks` in Split APKs Installer (SAI).

## Building these assets

```bash
# Recommended Morphe route (downloads the CLI, builds the .mpp, patches base.apk,
# re-signs the untouched config splits, writes the .apks)
python scratch/build_morphe_splits.py

# apktool fallback (known-good, does not use Morphe)
python scratch/build_patched_splits.py
```

The Morphe artifacts are:

- `patch/build/output/kpn-tvplus-adskip.mpp`
- `patch/build/output/kpn-tvplus-adskip-morphe-splits.apks`

See [MORPHE.md](MORPHE.md) for the build details and the remaining on-device test
matrix.
