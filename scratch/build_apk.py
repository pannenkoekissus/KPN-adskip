"""
KPN TV+ AdSkip APK Build Pipeline
Extracts base.apk, decompiles with apktool, injects AdSkipHook,
patches VideoPlayer and MainActivity, reassembles, and signs.
"""
import os
import sys
import subprocess
import zipfile
import shutil
import io

JAVA = r"C:\Program Files\Java\openjdk-22_windows-x64_bin\jdk-22\bin\java.exe"
APKTOOL = r"tools\apktool.jar"
SIGNER = r"tools\uber-apk-signer.jar"
APKS_FILE = r"KPN TV+.apks"
WORK_DIR = r"scratch\apk_build"
DECOMPILED = os.path.join(WORK_DIR, "decompiled")
SMALI_HOOK = r"patch\smali\software\morphe\kpn\AdSkipHook.smali"
OUTPUT_UNSIGNED = os.path.join(WORK_DIR, "kpn-tvplus-adskip-unsigned.apk")
OUTPUT_DIR = r"patch\build\output"


def run(cmd, label=""):
    print(f"\n{'='*60}")
    print(f"[{label}] {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.stdout:
        print(result.stdout[-2000:])
    if result.stderr:
        print("STDERR:", result.stderr[-2000:])
    if result.returncode != 0:
        print(f"WARNING: {label} returned code {result.returncode}")
    return result.returncode


def step1_extract_base_apk():
    """Extract base.apk from the .apks bundle"""
    print("\n>>> STEP 1: Extracting base.apk from APKS bundle")
    os.makedirs(WORK_DIR, exist_ok=True)
    base_path = os.path.join(WORK_DIR, "base.apk")
    if os.path.exists(base_path):
        print("base.apk already extracted, skipping")
        return base_path
    with zipfile.ZipFile(APKS_FILE) as z:
        z.extract("base.apk", WORK_DIR)
    print(f"Extracted base.apk ({os.path.getsize(base_path)} bytes)")
    return base_path


def step2_decompile(base_path):
    """Decompile base.apk with apktool (no resource decoding for speed)"""
    print("\n>>> STEP 2: Decompiling base.apk with apktool")
    if os.path.exists(DECOMPILED):
        shutil.rmtree(DECOMPILED)
    return run([
        JAVA, "-jar", APKTOOL,
        "d", "-r",  # don't decode resources (faster, avoids aapt issues)
        "-f",       # force overwrite
        "-o", DECOMPILED,
        base_path
    ], "apktool decompile")


def step3_inject_hook():
    """Copy AdSkipHook.smali into the decompiled smali tree"""
    print("\n>>> STEP 3: Injecting AdSkipHook.smali")
    target_dir = os.path.join(DECOMPILED, "smali_classes3", "software", "morphe", "kpn")
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy2(SMALI_HOOK, target_dir)
    print(f"Copied {SMALI_HOOK} -> {target_dir}")


def step4_patch_videoplayer():
    """Inject registerPlayer call into VideoPlayer.seekTo"""
    print("\n>>> STEP 4: Patching VideoPlayer.smali")
    vp_path = os.path.join(DECOMPILED, "smali_classes3", "io", "flutter", "plugins", "videoplayer", "VideoPlayer.smali")

    if not os.path.exists(vp_path):
        # Try smali/ or smali_classes2/
        for prefix in ["smali", "smali_classes2", "smali_classes4"]:
            alt = os.path.join(DECOMPILED, prefix, "io", "flutter", "plugins", "videoplayer", "VideoPlayer.smali")
            if os.path.exists(alt):
                vp_path = alt
                break

    if not os.path.exists(vp_path):
        print(f"ERROR: VideoPlayer.smali not found!")
        return False

    with open(vp_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find .method public seekTo(J)V and inject after first line
    hook_line = "    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V\n"
    marker = ".method public seekTo(J)V"

    if marker not in content:
        # Try alternative signatures
        for alt_marker in [".method public final seekTo(J)V", ".method seekTo(J)V"]:
            if alt_marker in content:
                marker = alt_marker
                break

    if marker not in content:
        print(f"ERROR: seekTo method not found in {vp_path}")
        return False

    if "AdSkipHook" in content:
        print("Already patched, skipping")
        return True

    # Insert after .locals or .registers line
    lines = content.split('\n')
    patched = []
    in_seek = False
    injected = False
    for line in lines:
        patched.append(line)
        if marker in line:
            in_seek = True
        if in_seek and not injected and ('.locals' in line or '.registers' in line):
            patched.append("")
            patched.append("    # === KPN TV+ AdSkip Hook: register active player ===")
            patched.append("    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V")
            patched.append("")
            injected = True

    if not injected:
        print("ERROR: Could not find insertion point in seekTo")
        return False

    with open(vp_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(patched))
    print(f"Patched {vp_path}")
    return True


def step5_patch_mainactivity():
    """Inject onKeyDown interception into MainActivity"""
    print("\n>>> STEP 5: Patching MainActivity.smali")

    # Find MainActivity
    ma_path = None
    for prefix in ["smali", "smali_classes2", "smali_classes3", "smali_classes4"]:
        candidate = os.path.join(DECOMPILED, prefix, "com", "kpn", "tvplusapp", "MainActivity.smali")
        if os.path.exists(candidate):
            ma_path = candidate
            break

    if not ma_path:
        print("WARNING: MainActivity.smali not found, creating onKeyDown override")
        return False

    with open(ma_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "AdSkipHook" in content:
        print("Already patched, skipping")
        return True

    # Check if onKeyDown already exists
    if "onKeyDown" in content:
        # Inject at start of existing method
        lines = content.split('\n')
        patched = []
        in_keydown = False
        injected = False
        for line in lines:
            patched.append(line)
            if '.method' in line and 'onKeyDown' in line:
                in_keydown = True
            if in_keydown and not injected and ('.locals' in line or '.registers' in line):
                patched.append("")
                patched.append("    # === KPN TV+ AdSkip Key Interception ===")
                patched.append("    invoke-static {p1, p2}, Lsoftware/morphe/kpn/AdSkipHook;->onKeyDown(ILandroid/view/KeyEvent;)Z")
                patched.append("    move-result v0")
                patched.append("    if-eqz v0, :cond_adskip_passthrough")
                patched.append("    const/4 v0, 0x1")
                patched.append("    return v0")
                patched.append("    :cond_adskip_passthrough")
                patched.append("")
                injected = True

        with open(ma_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(patched))
        print(f"Patched existing onKeyDown in {ma_path}")
    else:
        # Add onKeyDown method before the final .end class or at end
        new_method = """
# === KPN TV+ AdSkip: Key event interception ===
.method public onKeyDown(ILandroid/view/KeyEvent;)Z
    .registers 4
    .param p1, "keyCode"    # I
    .param p2, "event"      # Landroid/view/KeyEvent;

    invoke-static {p1, p2}, Lsoftware/morphe/kpn/AdSkipHook;->onKeyDown(ILandroid/view/KeyEvent;)Z
    move-result v0
    if-eqz v0, :cond_default
    const/4 v0, 0x1
    return v0

    :cond_default
    invoke-super {p0, p1, p2}, Lio/flutter/embedding/android/FlutterActivity;->onKeyDown(ILandroid/view/KeyEvent;)Z
    move-result v0
    return v0
.end method
"""
        # Insert before last line (which should be empty or end of file)
        with open(ma_path, 'a', encoding='utf-8') as f:
            f.write(new_method)
        print(f"Added onKeyDown method to {ma_path}")

    return True


def step6_rebuild():
    """Reassemble the APK with apktool"""
    print("\n>>> STEP 6: Rebuilding APK with apktool")
    return run([
        JAVA, "-jar", APKTOOL,
        "b",
        "-o", OUTPUT_UNSIGNED,
        DECOMPILED
    ], "apktool build")


def step7_sign():
    """Sign the APK"""
    print("\n>>> STEP 7: Signing APK")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(SIGNER) and os.path.getsize(SIGNER) > 1000:
        return run([
            JAVA, "-jar", SIGNER,
            "-a", OUTPUT_UNSIGNED,
            "-o", OUTPUT_DIR
        ], "uber-apk-signer")
    else:
        # Fallback: use jarsigner + zipalign
        print("uber-apk-signer not available, using jarsigner fallback")
        keystore = os.path.join(WORK_DIR, "debug.keystore")

        keytool = r"C:\Program Files\Java\jre-23.0.1-full\bin\keytool.exe"

        if not os.path.exists(keystore):
            run([
                keytool,
                "-genkeypair", "-v",
                "-keystore", keystore,
                "-alias", "adskip",
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "10000",
                "-storepass", "adskip123",
                "-keypass", "adskip123",
                "-dname", "CN=KPN AdSkip,O=AdSkip,C=NL"
            ], "keytool genkey")

        jarsigner = r"C:\Program Files\Java\openjdk-22_windows-x64_bin\jdk-22\bin\jarsigner.exe"
        signed_apk = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip.apk")
        shutil.copy2(OUTPUT_UNSIGNED, signed_apk)
        run([
            jarsigner,
            "-verbose",
            "-sigalg", "SHA256withRSA",
            "-digestalg", "SHA-256",
            "-keystore", keystore,
            "-storepass", "adskip123",
            signed_apk,
            "adskip"
        ], "jarsigner")
        return 0


def main():
    print("=" * 60)
    print("  KPN TV+ AdSkip APK Build Pipeline")
    print("=" * 60)

    base_path = step1_extract_base_apk()
    step2_decompile(base_path)
    step3_inject_hook()
    step4_patch_videoplayer()
    step5_patch_mainactivity()
    step6_rebuild()
    step7_sign()

    print("\n" + "=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)
    for f in os.listdir(OUTPUT_DIR):
        fp = os.path.join(OUTPUT_DIR, f)
        print(f"  {f} ({os.path.getsize(fp)} bytes)")


if __name__ == '__main__':
    main()
