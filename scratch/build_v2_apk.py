"""
Script to apply anti-tamper bypass, uncompressed native libs, crash logger, and build clean standalone APK.
"""
import os
import shutil
import zipfile
import re
import subprocess

JAVA = r"C:\Program Files\Java\openjdk-22_windows-x64_bin\jdk-22\bin\java.exe"
APKTOOL = r"tools\apktool.jar"
SIGNER = r"tools\uber-apk-signer.jar"
WORK_DIR = r"scratch\apk_build"
DECOMPILED = os.path.join(WORK_DIR, "orig_decompiled")
OUTPUT_DIR = r"patch\build\output"
UNSIGNED_APK = os.path.join(WORK_DIR, "kpn-tvplus-adskip-v2-unsigned.apk")

def patch_adskip_hook():
    print(">>> Patching AdSkipHook.smali with crash handler & file logger...")
    hook_dir = os.path.join(DECOMPILED, "smali_classes3", "software", "morphe", "kpn")
    os.makedirs(hook_dir, exist_ok=True)
    hook_path = os.path.join(hook_dir, "AdSkipHook.smali")
    
    # Read existing AdSkipHook.smali
    with open(r"patch\smali\software\morphe\kpn\AdSkipHook.smali", "r", encoding="utf-8") as f:
        smali = f.read()

    # Add log method if not present
    if "public static log(Ljava/lang/String;)V" not in smali:
        log_method = """
.method public static log(Ljava/lang/String;)V
    .registers 4
    .param p0, "msg"    # Ljava/lang/String;

    const-string v0, "KPN_AdSkip"
    invoke-static {v0, p0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    :try_start_0
    new-instance v0, Ljava/io/File;
    const-string v1, "/sdcard/Download/kpn_debug.log"
    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    new-instance v1, Ljava/io/FileWriter;
    const/4 v2, 0x1
    invoke-direct {v1, v0, v2}, Ljava/io/FileWriter;-><init>(Ljava/io/File;Z)V

    new-instance v0, Ljava/lang/StringBuilder;
    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V
    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, "\\n"
    invoke-virtual {v0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0

    invoke-virtual {v1, v0}, Ljava/io/Writer;->write(Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/OutputStreamWriter;->close()V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catch_0

    :catch_0
    return-void
.end method
"""
        smali += "\n" + log_method

    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(smali)
    print("Saved AdSkipHook.smali to:", hook_path)

def patch_main_activity():
    print(">>> Patching MainActivity.smali (guaranteed startup AdSkipHook hook)...")
    path = os.path.join(DECOMPILED, "smali_classes3", "com", "kpn", "tvplusapp", "MainActivity.smali")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "AdSkipHook" in content:
        print("MainActivity.smali already patched")
        return

    target = ".method public final onCreate(Landroid/os/Bundle;)V\n    .locals 4"
    assert target in content, "Could not find onCreate in MainActivity.smali"

    injection = target + """

    # === KPN TV+ AdSkip Hook: load at startup + register this Activity ===
    const-string v0, "MainActivity.onCreate"
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V
    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerActivity(Landroid/app/Activity;)V"""

    content = content.replace(target, injection, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched MainActivity.smali")

def patch_videoplayer():
    print(">>> Patching VideoPlayer.smali (registerPlayer hook)...")
    vp_path = os.path.join(DECOMPILED, "smali_classes3", "io", "flutter", "plugins", "videoplayer", "VideoPlayer.smali")
    with open(vp_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "AdSkipHook" not in content:
        target = ".method public seekTo(J)V\n    .locals 1"
        replacement = """.method public seekTo(J)V
    .locals 1

    # === KPN TV+ AdSkip Hook: register active player + log seek target ===
    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V
    invoke-static {p1, p2}, Lsoftware/morphe/kpn/AdSkipHook;->registerSeek(J)V"""
        assert target in content, "Could not find seekTo in VideoPlayer.smali"
        content = content.replace(target, replacement)
        with open(vp_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched VideoPlayer.smali")
    elif "registerSeek" not in content:
        # Upgrade an older AdSkipHook patch so seek targets are logged too
        content = content.replace(
            "invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V",
            "invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V\n"
            "    invoke-static {p1, p2}, Lsoftware/morphe/kpn/AdSkipHook;->registerSeek(J)V",
            1,
        )
        with open(vp_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Upgraded existing VideoPlayer.smali patch with registerSeek")
    else:
        print("VideoPlayer.smali already patched")

def patch_exoplayer_event_listener():
    print(">>> Patching ExoPlayerEventListener.smali to log errors...")
    ep_path = os.path.join(DECOMPILED, "smali_classes3", "io", "flutter", "plugins", "videoplayer", "ExoPlayerEventListener.smali")
    with open(ep_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "AdSkipHook" not in content:
        # The error parameter type (e.g. LA0/C;) changes per app build, so
        # locate onPlayerError by method name instead of hardcoding the type.
        import re as _re
        m = _re.search(r'\.method public onPlayerError\(L([^;]+;)V', content)
        if not m:
            print("WARNING: onPlayerError(L...) not found in ExoPlayerEventListener.smali, skipping")
            return

        target = ".method public onPlayerError(L%s)V" % m.group(1)

        # Find the .locals / .registers line that follows the method header
        reg_m = _re.search(_re.escape(target) + r'\n(\s*(\.locals|\.registers) (\d+))', content)
        if not reg_m:
            print("WARNING: could not find locals/registers line after onPlayerError, skipping")
            return

        old_line, kind, count = reg_m.group(1), reg_m.group(2), int(reg_m.group(3))

        # The injected block uses v0..v2 (3 locals). For .registers, `this` +
        # the error param take 2 register slots.
        injected_locals = 3
        new_count = max(count, injected_locals if kind == ".locals" else injected_locals + 2)
        new_line = ".%s %d" % (kind, new_count)

        injection = """
    # Log error to /sdcard/Download/kpn_debug.log
    invoke-static {p1}, Ljava/lang/String;->valueOf(Ljava/lang/Object;)Ljava/lang/String;
    move-result-object v0
    new-instance v1, Ljava/lang/StringBuilder;
    const-string v2, "EXOPLAYER_ERROR: "
    invoke-direct {v1, v2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V
    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v0}, Lsoftware/morphe/kpn/AdSkipHook;->log(Ljava/lang/String;)V"""

        content = content.replace(target + "\n" + old_line, target + "\n" + new_line + injection, 1)
        with open(ep_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched ExoPlayerEventListener.smali")
    else:
        print("ExoPlayerEventListener.smali already patched")
def patch_flutter_security_checker():
    print(">>> Patching flutter_security_checker (r8.1/b.smali)...")
    path = os.path.join(DECOMPILED, "smali_classes3", "r8.1", "b.smali")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    patched = []
    targets = (
        ("Security bypass: hasCorrectlyInstalled -> TRUE",
         r'(:cond_6\s+(?:\.line \d+\s+)*const-string v0, "hasCorrectlyInstalled"[\s\S]*?:cond_7\s+)',
         "const/4 p1, 0x1"),
        ("Security bypass: isRooted -> FALSE",
         r'(:cond_0\s+(?:\.line \d+\s+)*const-string v0, "isRooted"[\s\S]*?if-eqz p1, :cond_c\s+)',
         "const/4 p1, 0x0"),
        ("Security bypass: isRealDevice -> TRUE",
         r'(:cond_1\s+(?:\.line \d+\s+)*const-string v0, "isRealDevice"[\s\S]*?if-nez p1, :cond_2\s+)',
         "const/4 p1, 0x1"),
    )
    for marker, pattern, value in targets:
        if marker in content:
            continue
        sub = r'''\1# %s
    %s
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    ''' % (marker, value)
        new_content = re.sub(pattern, sub, content)
        if new_content == content:
            print("  WARNING: pattern not matched for %s" % marker)
        else:
            content = new_content
            patched.append(marker)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched flutter_security_checker (r8.1/b.smali): %s" % (", ".join(patched) if patched else "already up to date"))

def patch_safe_device():
    print(">>> Patching safe_device (z8.1/b.smali)...")
    path = os.path.join(DECOMPILED, "smali_classes3", "z8.1", "b.smali")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Tolerant matching: in the decompiled smali there can be an intervening
    # `.line N` marker / iget-object between the `:cond_X` label and the
    # const-string, so anchor on the const-string and the handler's start
    # condition rather than the label. The `\1` capture preserves the original
    # matched block; the bypass is inserted right after the handler condition
    # (e.g. `if-eqz v1, :cond_1`) so other dispatches stay intact.
    patched = []
    targets = (
        ("SafeDevice bypass: isJailBroken -> FALSE",
         r'(const-string v2, "isJailBroken"[\s\S]*?if-eqz v1, :cond_1\s+)',
         "const/4 p1, 0x0"),
        ("SafeDevice bypass: isRealDevice -> TRUE",
         r'(const-string v2, "isRealDevice"[\s\S]*?if-eqz v1, :cond_a\s+)',
         "const/4 p1, 0x1"),
        ("SafeDevice bypass: isDevelopmentModeEnable -> FALSE",
         r'(const-string v4, "isDevelopmentModeEnable"[\s\S]*?if-eqz v1, :cond_\w+\s+)',
         "const/4 p1, 0x0"),
        ("SafeDevice bypass: usbDebuggingCheck -> FALSE",
         r'(const-string v4, "usbDebuggingCheck"[\s\S]*?if-eqz v1, :cond_\w+\s+)',
         "const/4 p1, 0x0"),
    )
    for marker, pattern, value in targets:
        if marker in content:
            print("  SKIP (already present): %s" % marker)
            continue
        sub = r'''\1# %s
    %s
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    ''' % (marker, value)
        new_content = re.sub(pattern, sub, content)
        if new_content == content:
            print("  WARNING: pattern not matched for %s" % marker)
        else:
            content = new_content
            patched.append(marker)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched safe_device (z8.1/b.smali): %s" % (", ".join(patched) if patched else "already up to date"))

def inject_native_libs_and_config():
    print(">>> Injecting native libraries & configuring apktool.yml...")
    lib_target = os.path.join(DECOMPILED, "lib", "arm64-v8a")
    os.makedirs(lib_target, exist_ok=True)
    
    with zipfile.ZipFile("KPN TV+.apks") as apks:
        with apks.open("split_config.arm64_v8a.apk") as split_arm:
            with zipfile.ZipFile(split_arm) as z_arm:
                for item in z_arm.namelist():
                    if item.startswith("lib/arm64-v8a/") and item.endswith(".so"):
                        fname = os.path.basename(item)
                        out_path = os.path.join(lib_target, fname)
                        with open(out_path, "wb") as out_f:
                            out_f.write(z_arm.read(item))
                        print(f"  Injected {fname}")

    # Configure apktool.yml to NOT compress .so files (STORED, compress_type=0)
    yml_path = os.path.join(DECOMPILED, "apktool.yml")
    with open(yml_path, "r", encoding="utf-8") as f:
        yml_content = f.read()

    if "- so" not in yml_content:
        yml_content = yml_content.replace("doNotCompress:\n", "doNotCompress:\n- so\n")
        with open(yml_path, "w", encoding="utf-8") as f:
            f.write(yml_content)
        print("Configured doNotCompress in apktool.yml to include .so")

def merge_resources():
    print(">>> Merging resources (values-nl & xxhdpi drawables)...")
    # Dutch strings from nl_decompiled
    nl_res = os.path.join(WORK_DIR, "nl_decompiled", "res", "values-nl")
    target_nl = os.path.join(DECOMPILED, "res", "values-nl")
    if os.path.exists(nl_res):
        if os.path.exists(target_nl):
            shutil.rmtree(target_nl)
        shutil.copytree(nl_res, target_nl)
        print("  Copied values-nl")

    # xxhdpi drawables
    xxhdpi_res = os.path.join(WORK_DIR, "xxhdpi_decompiled", "res")
    target_res = os.path.join(DECOMPILED, "res")
    for item in os.listdir(xxhdpi_res):
        if item.startswith("drawable-"):
            src_d = os.path.join(xxhdpi_res, item)
            dst_d = os.path.join(target_res, item)
            os.makedirs(dst_d, exist_ok=True)
            for f in os.listdir(src_d):
                shutil.copy2(os.path.join(src_d, f), dst_d)
            print(f"  Merged {item}")

def patch_manifest():
    print(">>> Patching AndroidManifest.xml...")
    manifest_path = os.path.join(DECOMPILED, "AndroidManifest.xml")

    # A previous apktool b may have overwritten the text manifest with binary
    # AXML. Detect and re-decode from base.apk if so.
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Verify it's actual XML (not binary)
        if not content.lstrip().startswith("<?xml") and not content.lstrip().startswith("<"):
            raise UnicodeDecodeError("not xml", b"", 0, 1, "")
    except (UnicodeDecodeError, UnicodeError):
        print("  Manifest is binary AXML (from prior apktool b). Re-decoding...")
        tmp_decode = os.path.join(WORK_DIR, "_manifest_tmp")
        if os.path.exists(tmp_decode):
            shutil.rmtree(tmp_decode)
        base_apk = os.path.join(WORK_DIR, "base.apk")
        cmd = [JAVA, "-jar", APKTOOL, "d", base_apk, "-o", tmp_decode, "-f", "-s"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print("  WARNING: apktool decode failed, using nl_decompiled manifest as fallback")
            fallback = os.path.join(WORK_DIR, "nl_decompiled", "AndroidManifest.xml")
            shutil.copy2(fallback, manifest_path)
        else:
            shutil.copy2(os.path.join(tmp_decode, "AndroidManifest.xml"), manifest_path)
            shutil.rmtree(tmp_decode)
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()
        print("  Restored text manifest from base.apk")

    content = re.sub(r'\s*android:requiredSplitTypes="[^"]*"', '', content)
    content = re.sub(r'\s*android:splitTypes="[^"]*"', '', content)
    content = re.sub(r'android:extractNativeLibs="false"', 'android:extractNativeLibs="true"', content)
    content = re.sub(r'\s*android:isFeatureSplit="[^"]*"', '', content)

    lines = [line for line in content.splitlines(True) if "com.android.vending.splits" not in line]
    content = "".join(lines)

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Manifest patched.")

def rebuild_and_sign():
    print(">>> Rebuilding APK with apktool...")
    # Clean previous build cache if exists
    build_dir = os.path.join(DECOMPILED, "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    cmd = [JAVA, "-jar", APKTOOL, "b", DECOMPILED, "-o", UNSIGNED_APK]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout[-1500:])
    if res.stderr:
        print("STDERR:", res.stderr[-1500:])
    assert res.returncode == 0, f"apktool failed with code {res.returncode}"
    print(f"Built unsigned APK ({os.path.getsize(UNSIGNED_APK)} bytes)")

    print(">>> Applying known-good manifest & signing (uber-apk-signer)...")
    # apktool's re-encoded AndroidManifest.xml is unparseable by both uber-apk-signer
    # ("malformed binary resource") and the device (INSTALL_FAILED_INVALID_APK).
    # Swap in a known-good binary manifest from an earlier verified build.
    good_manifest = None
    candidates = [
        os.path.join(WORK_DIR, "kpn-tvplus-adskip-standalone-unsigned.apk"),
        os.path.join(WORK_DIR, "test_smali_build.apk"),
        os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-standalone-aligned-debugSigned.apk"),
        os.path.join(WORK_DIR, "kpn-tvplus-adskip-standalone.apk"),
    ]
    for cand in candidates:
        if not os.path.exists(cand):
            continue
        try:
            with zipfile.ZipFile(cand) as z:
                data = z.read("AndroidManifest.xml")
            if data and not data.lstrip().startswith(b"<"):
                good_manifest = data
                print(f"  Using known-good manifest from {os.path.basename(cand)}")
                break
        except Exception:
            continue
    assert good_manifest is not None, "No known-good binary manifest found!"

    # Rebuild unsigned APK with the good manifest (drop any old META-INF)
    tmp_apk = UNSIGNED_APK + ".reman"
    with zipfile.ZipFile(UNSIGNED_APK, "r") as zin:
        with zipfile.ZipFile(tmp_apk, "w") as zout:
            for item in zin.infolist():
                if item.filename.startswith("META-INF/"):
                    continue
                data = zin.read(item.filename)
                if item.filename == "AndroidManifest.xml":
                    data = good_manifest
                zout.writestr(item, data)
    os.replace(tmp_apk, UNSIGNED_APK)
    print(f"  Swapped AndroidManifest.xml ({len(good_manifest)} bytes)")

    jarsigner = os.path.join(os.path.dirname(JAVA), "jarsigner.exe")
    keytool = os.path.join(os.path.dirname(JAVA), "keytool.exe")
    debug_ks = os.path.expanduser(r"~\.android\debug.keystore")
    if not os.path.exists(debug_ks):
        ks_dir = os.path.dirname(debug_ks)
        os.makedirs(ks_dir, exist_ok=True)
        subprocess.run([keytool, "-genkeypair", "-v",
            "-keystore", debug_ks, "-storepass", "android",
            "-alias", "androiddebugkey", "-keypass", "android",
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-dname", "CN=Android Debug,O=Android,C=US"],
            capture_output=True)

    # Sign with uber-apk-signer (v1+v2+v3 + zipalign) - the recipe that worked
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cmd = [JAVA, "-jar", SIGNER, "-a", UNSIGNED_APK, "-o", OUTPUT_DIR, "--allowResign"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout[-1500:])
    if res.stderr:
        print("STDERR:", res.stderr[-1500:])

    final_name = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-standalone.apk")
    signed_name = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-v2-aligned-debugSigned.apk")
    backup_name = os.path.join(WORK_DIR, "kpn-tvplus-adskip-standalone.apk")
    uber_ok = res.returncode == 0 and os.path.exists(signed_name)

    if uber_ok:
        shutil.copy2(signed_name, final_name)
        print("  Signed with uber-apk-signer (v1+v2+v3, zipaligned)")
    else:
        print("  uber-apk-signer failed, falling back to jarsigner (v1)...")
        signed_jar = UNSIGNED_APK.replace("-unsigned.apk", "-signed.jar")
        shutil.copy2(UNSIGNED_APK, signed_jar)
        res = subprocess.run([jarsigner, "-sigalg", "SHA256withRSA",
            "-digestalg", "SHA-256", "-keystore", debug_ks,
            "-storepass", "android", "-keypass", "android",
            signed_jar, "androiddebugkey"],
            capture_output=True, text=True)
        if res.stderr:
            print("jarsigner:", res.stderr[-500:])
        assert res.returncode == 0, f"jarsigner failed: {res.stderr[-300:]}"
        shutil.copy2(signed_jar, final_name)
        os.remove(signed_jar)
        print("  Signed with jarsigner (v1)")

    shutil.copy2(final_name, backup_name)
    if os.path.exists(final_name):
        print(f"SUCCESS! Output: {final_name} ({os.path.getsize(final_name)} bytes)")
        print(f"Backup copy: {backup_name} ({os.path.getsize(backup_name)} bytes)")
        bad_entry = None
        try:
            with zipfile.ZipFile(final_name) as z:
                bad_entry = z.testzip()
            if bad_entry is None:
                print("  zip integrity: OK")
            else:
                print(f"  zip integrity: CORRUPT at {bad_entry}")
        except Exception as e:
            print(f"  zip integrity: FAILED ({e})")
        res = subprocess.run([jarsigner, "-verify", final_name], capture_output=True, text=True)
        output_check = (res.stdout + res.stderr).lower()
        if res.returncode == 0 and "jar verified" in output_check:
            print("  signature: VALID")
        else:
            print("  signature: (v2/v3 scheme - not checked by jarsigner)")
    else:
        print(f"ERROR: signed APK missing at {final_name} - check antivirus quarantine")

def main():
    patch_adskip_hook()
    patch_main_activity()
    patch_videoplayer()
    patch_exoplayer_event_listener()
    patch_flutter_security_checker()
    patch_safe_device()
    inject_native_libs_and_config()
    merge_resources()
    patch_manifest()
    rebuild_and_sign()

if __name__ == "__main__":
    main()
