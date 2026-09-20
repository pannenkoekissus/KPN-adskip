"""
Correct approach: KEEP the split APK architecture (do NOT merge splits).

Why the previous standalones kept crashing on playback:
  The Play Store build of KPN TV+ is installed as splits. Resources declared by
  base.apk (e.g. media3 controls) have their FILES only in the density/locale
  splits (exo_icon_vr 0x7f0800c5 lives in split_config.xxhdpi.apk). Merging the
  splits with apktool corrupts the shared resource table, so drawables turn into
  missing/null references -> PlayerView inflate crash (black screen).

Why this builds installable APKs:
  1. base.apk is the ONLY split that needs patching. We re-decompile it with
     `apktool d -r` (resources.arsc + res/* stay ORIGINAL, smali IS decoded) and
     inject AdSkipHook + the seek/key hooks + security bypasses.
  2. The config splits (arm64/xxhdpi/nl/...) are NEVER rebuilt. We keep them 100%
     byte-original and only re-sign them, so their resources stay intact and the
     runtime merges them with base exactly like the Play store does.
  3. Every split is signed with ONE debug key. Android REQUIRES all splits of an
     app to share the same certificate. Signing each split separately with a fresh
     generated keystore is the classic cause of:
         Failure [INSTALL_FAILED_INVALID_APK]   (adb error code -2)

Install with (all four must be present):
  adb install-multiple patched_base.apk split_config.arm64_v8a.apk \
      split_config.xxhdpi.apk split_config.nl.apk
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scratch"))
if os.getcwd() != REPO_ROOT:
    os.chdir(REPO_ROOT)

JAVA = r"C:\Program Files\Java\openjdk-22_windows-x64_bin\jdk-22\bin\java.exe"
APKTOOL = os.path.join(REPO_ROOT, "tools", "apktool.jar")
SIGNER = os.path.join(REPO_ROOT, "tools", "uber-apk-signer.jar")
BUNDLE = os.path.join(REPO_ROOT, "KPN TV+.apks")

WORK_DIR = os.path.join(REPO_ROOT, "scratch", "apk_build")
OUTPUT_DIR = os.path.join(REPO_ROOT, "patch", "build", "output")

# Files this script (re)generates in OUTPUT_DIR. Removed at startup so you never
# mistake a previous run's output for the current one.
REGENERATED_OUTPUTS = [
    "kpn-tvplus-adskip-splits.apks",
    "patched_base-aligned-debugSigned.apk",
    "patched_base-aligned-debugSigned.apk.idsig",
    "patched_split_config.arm64_v8a-aligned-debugSigned.apk",
    "patched_split_config.xxhdpi-aligned-debugSigned.apk",
    "patched_split_config.nl-aligned-debugSigned.apk",
    "kpn-tvplus-adskip-universal.apk",
    "kpn-tvplus-adskip-universal-signed.apk",
]

PATCH_HOOK_SRC = os.path.join(REPO_ROOT, "patch", "smali", "software", "morphe", "kpn", "AdSkipHook.smali")

PRISTINE_BASE = os.path.join(WORK_DIR, "base.apk")
BASE_DECOMPILED = os.path.join(WORK_DIR, "base_decompiled")
PATCHED_BASE_UNSIGNED = os.path.join(WORK_DIR, "patched_base.apk")

# Config splits are extracted from the .apks bundle and re-signed, never rebuilt.
CONFIG_SPLITS = [
    "split_config.arm64_v8a.apk",
    "split_config.xxhdpi.apk",
    "split_config.nl.apk",
]


def log(msg):
    print(msg, flush=True)


def extract_splits_from_bundle():
    """Pull the original splits out of KPN TV+.apks so we never work on a stale one."""
    if not os.path.exists(BUNDLE):
        raise SystemExit(f"Missing bundle: {BUNDLE}")
    extracted = []
    with zipfile.ZipFile(BUNDLE) as z:
        apk_names = sorted(
            n for n in z.namelist()
            if n.endswith(".apk") and "splits/" not in n
        ) or sorted(n for n in z.namelist() if n.endswith(".apk"))
        for name in apk_names:
            dst = os.path.join(WORK_DIR, os.path.basename(name))
            with z.open(name) as src, open(dst, "wb") as out:
                shutil.copyfileobj(src, out)
            extracted.append(dst)
    return extracted


def decompile_base():
    """Fresh decode of base.apk: -r keeps original resources, smali IS decoded."""
    if os.path.exists(BASE_DECOMPILED):
        shutil.rmtree(BASE_DECOMPILED)
    cmd = [JAVA, "-jar", APKTOOL, "d", "-r", PRISTINE_BASE, "-o", BASE_DECOMPILED]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"apktool decode failed:\n{res.stdout[-1200:]}\n{res.stderr[-1200:]}")
    for sm in ("smali", "smali_classes2", "smali_classes3"):
        log(f"  {sm}: {'OK' if os.path.isdir(os.path.join(BASE_DECOMPILED, sm)) else 'MISSING'}")


def apply_smali_patches():
    """Reuse the proven patch routines from build_v2_apk.py, pointed at the base split."""
    import build_v2_apk as v2
    v2.DECOMPILED = BASE_DECOMPILED

    log(">>> Applying AdSkipHook + hooks + security bypasses to base.apk...")
    v2.patch_adskip_hook()
    v2.patch_main_activity()
    v2.patch_videoplayer()
    v2.patch_videoplayer_lifecycle()
    v2.patch_exoplayer_state_logging()
    v2.patch_exoplayer_event_listener()
    v2.patch_exoplayer_ad_bypass()
    v2.patch_native_player()
    v2.patch_flutter_security_checker()
    v2.patch_safe_device()

    patch_remote_key_shortcuts()


def patch_remote_key_shortcuts():
    """Wire AdSkipHook.onKeyDown via dispatchKeyEvent so remote/shortcut keys work."""
    path = os.path.join(BASE_DECOMPILED, "smali_classes3", "com", "kpn", "tvplusapp", "MainActivity.smali")
    if not os.path.exists(path):
        log("  WARNING: MainActivity.smali not found, key shortcuts skipped")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "AdSkipHook;->onKeyDown" in content:
        log("  MainActivity.smali dispatchKeyEvent: already patched")
        return
    target = ".method public final dispatchKeyEvent(Landroid/view/KeyEvent;)Z\n"
    if target not in content:
        log("  WARNING: dispatchKeyEvent(Landroid/view/KeyEvent;)Z not found in MainActivity, key shortcuts skipped")
        return
    injection = target + """
    # === KPN TV+ AdSkip Hook: intercept keys via dispatchKeyEvent ===
    invoke-virtual {p1}, Landroid/view/KeyEvent;->getKeyCode()I
    move-result v0
    invoke-static {v0, p1}, Lsoftware/morphe/kpn/AdSkipHook;->onKeyDown(ILandroid/view/KeyEvent;)Z
    move-result v0
    if-eqz v0, :cond_adskip_default
    const/4 v0, 0x1
    return v0

    :cond_adskip_default

"""
    content = content.replace(target, injection, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    log("  MainActivity.smali dispatchKeyEvent: patched (remote key shortcuts enabled)")


def rebuild_base():
    log(">>> Rebuilding base.apk with apktool...")
    build_dir = os.path.join(BASE_DECOMPILED, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    cmd = [JAVA, "-jar", APKTOOL, "b", BASE_DECOMPILED, "-o", PATCHED_BASE_UNSIGNED]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"apktool build failed:\n{res.stdout[-1500:]}\n{res.stderr[-1500:]}")
    log(f"  Built {PATCHED_BASE_UNSIGNED} ({os.path.getsize(PATCHED_BASE_UNSIGNED)} bytes)")

    # apktool re-encodes AndroidManifest.xml from text. That re-encode has been
    # observed to produce a malformed manifest on this app -> INSTALL_FAILED_INVALID_APK.
    # Swap in the ORIGINAL binary manifest from the pristine base.apk instead
    # (it carries the correct resource-ID references for the unmodified arsc).
    with zipfile.ZipFile(PRISTINE_BASE) as zin:
        orig_manifest = zin.read("AndroidManifest.xml")
    tmp = PATCHED_BASE_UNSIGNED + ".reman"
    with zipfile.ZipFile(PATCHED_BASE_UNSIGNED) as zin:
        with zipfile.ZipFile(tmp, "w") as zout:
            for item in zin.infolist():
                if item.filename.startswith("META-INF/"):
                    continue
                data = zin.read(item.filename)
                if item.filename == "AndroidManifest.xml":
                    data = orig_manifest
                zout.writestr(item, data)
    os.replace(tmp, PATCHED_BASE_UNSIGNED)
    log(f"  Swapped in original binary AndroidManifest.xml ({len(orig_manifest)} bytes)")

    verify_patches_present()


def verify_patches_present():
    """Fail loudly if the rebuild lost the injected hook.

    A silent regression once shipped a "patched" base.apk that contained NONE of
    the smali edits (the hook call was simply missing), which is indistinguishable
    from stock at runtime. Scan the rebuilt dex payload for the hook's class
    descriptor so that can never happen unnoticed again.
    """
    markers = {
        b"Lsoftware/morphe/kpn/AdSkipHook;": "AdSkipHook class",
        b"Lsoftware/morphe/kpn/AdSkipButton;": "AdSkipButton overlay",
        b"Lsoftware/morphe/kpn/AdSkipOverlayTask;": "AdSkipOverlayTask delay",
        b"Lsoftware/morphe/kpn/AdSkipPipWatcher;": "AdSkipPipWatcher PiP polling",
        b"onKeyDown": "MainActivity key routing",
    }
    dex_blob = b""
    with zipfile.ZipFile(PATCHED_BASE_UNSIGNED) as z:
        for name in z.namelist():
            if name.startswith("classes") and name.endswith(".dex"):
                dex_blob += z.read(name)
    missing = [label for marker, label in markers.items() if marker not in dex_blob]
    if missing:
        raise SystemExit(
            "FATAL: rebuilt base.apk is missing patch(es): "
            + ", ".join(missing)
            + " - smali patches were not applied. Aborting before signing a stock build."
        )
    log("  Verified: AdSkipHook + key routing present in rebuilt dex")


def ensure_debug_keystore():
    keystore = os.path.expanduser(r"~\.android\debug.keystore")
    if os.path.exists(keystore):
        return keystore
    ks_dir = os.path.dirname(keystore)
    os.makedirs(ks_dir, exist_ok=True)
    keytool = os.path.join(os.path.dirname(JAVA), "keytool.exe")
    subprocess.run([
        keytool, "-genkeypair", "-v",
        "-keystore", keystore, "-storepass", "android",
        "-alias", "androiddebugkey", "-keypass", "android",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
        "-dname", "CN=Android Debug,O=Android,C=US",
    ], check=True)
    return keystore


def sign_apk(apk_path, out_dir, keystore):
    """Sign one APK with V1+V2+V3 signatures.

    IMPORTANT: Do NOT pass --ks/--ksalias... to uber-apk-signer here. When those
    options are supplied it exits 0 but writes NO output (observed). Instead we
    rely on uber's default behaviour: it uses ~/.android/debug.keystore when it
    exists (ensure_debug_keystore() creates it first), i.e. the SAME certificate
    for every split. Android only installs split sets where all splits share one
    signing certificate, so this consistency is mandatory.
    """
    cmd = [JAVA, "-jar", SIGNER, "-a", apk_path, "-o", out_dir, "--allowResign"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"Signing failed for {apk_path}:\n{(res.stdout or '')[-1200:]}\n{(res.stderr or '')[-1200:]}")
    stem = os.path.basename(apk_path).rsplit(".apk", 1)[0]
    signed = [f for f in glob.glob(os.path.join(out_dir, "*.apk")) if stem in os.path.basename(f)]
    if not signed and os.path.exists(apk_path + ".reman"):
        signed = [apk_path + ".reman"]
    if not signed:
        tail = (res.stdout or "")[-1500:]
        raise SystemExit(f"No signed APK produced for {apk_path}.\nSigner output:\n{tail}")
    fresh = max(signed, key=os.path.getmtime)
    log(f"    signer wrote: {os.path.basename(fresh)}")
    return fresh


def package_apks(final_apks):
    """Bundle the signed splits into a single SAI-compatible .apks archive.

    A .apks is a plain zip that lists the split APK files at its root, which is
    exactly what Split APKs Installer (SAI) / split-installer apps accept, and it
    can be sideloaded as one file instead of passing four APKs to
    `adb install-multiple`.
    """
    out_apks = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-splits.apks")
    if os.path.exists(out_apks):
        os.remove(out_apks)
    with zipfile.ZipFile(out_apks, "w", zipfile.ZIP_DEFLATED) as z:
        for p in final_apks:
            z.write(p, arcname=os.path.basename(p))
    return out_apks


def main():
    log("=" * 70)
    log("KPN TV+ AdSkip - Patched SPLITS build (resources stay in config splits)")
    log("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    keystore = ensure_debug_keystore()
    log(f"Using keystore: {keystore}")

    # Scrub stale output so `patch\\build\\output` only contains fresh builds.
    # Best-effort: a file locked by another process (Explorer preview, etc.) must
    # not abort the whole build - we keep going and warn instead.
    for stale in REGENERATED_OUTPUTS:
        p = os.path.join(OUTPUT_DIR, stale)
        if os.path.exists(p):
            try:
                os.remove(p)
                log(f"removed stale {stale}")
            except OSError as e:
                log(f"  WARNING: could not remove stale {stale} (locked?) - {e}")

    extracted = extract_splits_from_bundle()
    log(f"Extracted splits from bundle: {[os.path.basename(p) for p in extracted]}")

    config_apks = []
    for wanted in CONFIG_SPLITS:
        p = os.path.join(WORK_DIR, wanted)
        if not os.path.exists(p):
            raise SystemExit(f"Config split {wanted} missing from {WORK_DIR} (is it in the .apks bundle?)")

    decompile_base()
    apply_smali_patches()
    rebuild_base()

    log(">>> Signing EVERY split with the SAME key (required for install-multiple)...")
    final = {}
    final["base"] = sign_apk(PATCHED_BASE_UNSIGNED, OUTPUT_DIR, keystore)
    log(f"  signed base   -> {os.path.basename(final['base'])}")
    for name in CONFIG_SPLITS:
        src = os.path.join(WORK_DIR, name)
        signed = sign_apk(src, OUTPUT_DIR, keystore)
        final[name] = signed
        log(f"  signed config -> {os.path.basename(signed)} (original resources, re-signed only)")

    log("")
    apks_path = package_apks([final["base"]] + [final[n] for n in CONFIG_SPLITS if n in final])
    log("=" * 70)
    log("SUCCESS. Single-file bundle (SAI / Split APKs Installer compatible):")
    log("  " + apks_path)
    log("")
    log("Or install via adb (from inside the output folder):")
    cmd_parts = ["adb", "install-multiple", os.path.basename(final["base"])] + [os.path.basename(final[n]) for n in CONFIG_SPLITS if n in final]
    log("  " + " \\\n      ".join(cmd_parts))
    log("")
    log("Output folder:")
    log("  " + OUTPUT_DIR)
    log("=" * 70)


if __name__ == "__main__":
    main()