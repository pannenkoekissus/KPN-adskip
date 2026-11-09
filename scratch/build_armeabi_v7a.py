"""Build a patched KPN Android TV / KPN TV+ binary for the armeabi-v7a architecture."""
import os
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, "/root/projects/kpn-adskip/scratch")
import build_v2_linux as v2

WORK = "/root/projects/kpn-adskip/scratch/apk_build"
DECOMPILED = "/root/projects/kpn-adskip/scratch/apk_build/base_decompiled"
UNSIGNED_APK = "/root/projects/kpn-adskip/scratch/apk_build/kpn-tvplus-adskip-armv7a-unsigned.apk"
OUTPUT_APK = "/root/projects/kpn-adskip/patch/build/output/kpn-tvplus-adskip-armv7a-aligned-debugSigned.apk"

ABI = "armeabi-v7a"
SPLIT_NAME = "split_config.armeabi_v7a.apk"

def run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout: print("STDOUT:", res.stdout[-2000:])
    if res.stderr: print("STDERR:", res.stderr[-2000:])
    if res.returncode != 0:
        raise SystemExit(f"CMD FAILED: {' '.join(cmd)}\n{res.stdout[-1500:]}\n{res.stderr[-1500:]}")
    return res

def main():
    print(">>> [1/6] Fresh decompile of base.apk (resources kept original, -r)...")
    if os.path.exists(DECOMPILED):
        shutil.rmtree(DECOMPILED)
    run(["/usr/bin/java", "-jar", v2.APKTOOL, "d", "-r", os.path.join(WORK, "base.apk"), "-o", DECOMPILED])

    v2.WORK_DIR = WORK
    v2.DECOMPILED = DECOMPILED
    v2.OUTPUT_DIR = "/root/projects/kpn-adskip/patch/build/output"
    v2.UNSIGNED_APK = UNSIGNED_APK

    print(">>> [2/6] Applying AdSkip patches...")
    v2.patch_adskip_hook()
    v2.patch_main_activity()
    v2.patch_videoplayer()
    v2.patch_videoplayer_lifecycle()
    v2.patch_exoplayer_state_logging()
    v2.patch_exoplayer_event_listener()
    v2.patch_exoplayer_ad_bypass()
    v2.patch_native_player()

    for mod, fn in (
        ("flutter_security_checker", v2.patch_flutter_security_checker),
        ("safe_device", v2.patch_safe_device),
    ):
        try:
            fn()
        except Exception as e:
            print(f"  SKIP (optional patch target changed in this app version): {mod}: {e}")

    main_vp = os.path.join(DECOMPILED, "smali_classes3", "com", "kpn", "tvplusapp", "MainActivity.smali")
    if os.path.exists(main_vp):
        with open(main_vp, "r", encoding="utf-8") as f:
            content = f.read()
        if "AdSkipHook;->onKeyDown" in content:
            print("  MainActivity.smali dispatchKeyEvent: already patched")
        else:
            target = ".method public final dispatchKeyEvent(Landroid/view/KeyEvent;)Z\n"
            if target not in content:
                print("  WARNING: dispatchKeyEvent not found, remote key shortcuts skipped")
            else:
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
                with open(main_vp, "w", encoding="utf-8") as f:
                    f.write(content)
                print("  MainActivity.smali dispatchKeyEvent: patched (remote key shortcuts enabled)")

    print(">>> [3/6] Injecting armeabi-v7a native libs from split_config.%s.apk..." % ABI)
    lib_dir = os.path.join(DECOMPILED, "lib", ABI)
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(WORK, SPLIT_NAME), "rb") as fsplit:
        with zipfile.ZipFile(fsplit) as z:
            for item in z.infolist():
                if item.filename.startswith("lib/%s/" % ABI) and item.filename.endswith(".so"):
                    fname = os.path.basename(item.filename)
                    out_path = os.path.join(lib_dir, fname)
                    data = z.read(item.filename)
                    with open(out_path, "wb") as f:
                        f.write(data)
                    print("    injected", item.filename, len(data))

    print(">>> [4/6] Configuring apktool doNotCompress for .so ...")
    yml_path = os.path.join(DECOMPILED, "apktool.yml")
    with open(yml_path, "r", encoding="utf-8") as f:
        yml_content = f.read()
    if "- so" not in yml_content:
        yml_content = yml_content.replace("doNotCompress:\n", "doNotCompress:\n- so\n")
        with open(yml_path, "w", encoding="utf-8") as f:
            f.write(yml_content)
        print("    added - so to doNotCompress")

    print(">>> [5/6] Merging nl resources (if present) ...")
    try:
        v2.merge_resources()
    except Exception as e:
        print("  SKIP merge_resources:", e)

    print(">>> [6/6] Patching + rebuilding + signing ...")
    v2.patch_manifest()
    run(["/usr/bin/java", "-jar", v2.APKTOOL, "b", DECOMPILED, "-o", UNSIGNED_APK])

    import axml
    with zipfile.ZipFile(os.path.join(WORK, "base.apk")) as zin:
        orig_manifest = zin.read("AndroidManifest.xml")
    patched_manifest = axml.add_accessibility_service(orig_manifest)
    if not axml.verify(patched_manifest):
        raise SystemExit("FATAL: injected accessibility <service> not found in rebuilt AndroidManifest.xml - Aborting.")
    tmp = UNSIGNED_APK + ".reman"
    with zipfile.ZipFile(UNSIGNED_APK) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            if item.filename.startswith("META-INF/"):
                continue
            data = zin.read(item.filename)
            if item.filename == "AndroidManifest.xml":
                data = patched_manifest
            zout.writestr(item, data)
    os.replace(tmp, UNSIGNED_APK)

    print(">>> Signing with uber-apk-signer...")
    os.makedirs("/root/projects/kpn-adskip/patch/build/output", exist_ok=True)
    res = subprocess.run(["/usr/bin/java", "-jar", v2.SIGNER, "-a", UNSIGNED_APK, "-o", "/root/projects/kpn-adskip/patch/build/output", "--allowResign"], capture_output=True, text=True)
    print(res.stdout[-3000:])
    if res.stderr: print("SIGNER STDERR:", res.stderr[-3000:])
    if res.returncode != 0:
        raise SystemExit("Signing failed")

    final = "/root/projects/kpn-adskip/patch/build/output/kpn-tvplus-adskip-armv7a-aligned-debugSigned.apk"
    if os.path.exists(final):
        shutil.copy2(final, OUTPUT_APK)
    print("DONE ->", OUTPUT_APK, os.path.getsize(OUTPUT_APK) if os.path.exists(OUTPUT_APK) else -1)

if __name__ == "__main__":
    main()
