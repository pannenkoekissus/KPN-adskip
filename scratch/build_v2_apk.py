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

def patch_videoplayer():
    print(">>> Patching VideoPlayer.smali (registerPlayer hook)...")
    vp_path = os.path.join(DECOMPILED, "smali_classes3", "io", "flutter", "plugins", "videoplayer", "VideoPlayer.smali")
    with open(vp_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "AdSkipHook" not in content:
        target = ".method public seekTo(J)V\n    .locals 1"
        replacement = """.method public seekTo(J)V
    .locals 1

    # === KPN TV+ AdSkip Hook: register active player ===
    invoke-static {p0}, Lsoftware/morphe/kpn/AdSkipHook;->registerPlayer(Ljava/lang/Object;)V"""
        assert target in content, "Could not find seekTo in VideoPlayer.smali"
        content = content.replace(target, replacement)
        with open(vp_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Patched VideoPlayer.smali")
    else:
        print("VideoPlayer.smali already patched")

def patch_exoplayer_event_listener():
    print(">>> Patching ExoPlayerEventListener.smali to log errors...")
    ep_path = os.path.join(DECOMPILED, "smali_classes3", "io", "flutter", "plugins", "videoplayer", "ExoPlayerEventListener.smali")
    with open(ep_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "AdSkipHook" not in content:
        target = ".method public onPlayerError(LA0/C;)V\n    .locals 3"
        replacement = """.method public onPlayerError(LA0/C;)V
    .locals 3

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
        assert target in content, "Could not find onPlayerError in ExoPlayerEventListener.smali"
        content = content.replace(target, replacement)
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

    # 1. hasCorrectlyInstalled -> return true
    pattern1 = r'(:cond_6\s+const-string v0, "hasCorrectlyInstalled"[\s\S]*?:cond_7\s+)'
    sub1 = r'''\1# Security bypass: hasCorrectlyInstalled -> TRUE
    const/4 p1, 0x1
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern1, sub1, content)

    # 2. isRooted -> return false
    pattern2 = r'(:cond_0\s+const-string v0, "isRooted"[\s\S]*?if-eqz p1, :cond_c\s+)'
    sub2 = r'''\1# Security bypass: isRooted -> FALSE
    const/4 p1, 0x0
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern2, sub2, content)

    # 3. isRealDevice -> return true
    pattern3 = r'(:cond_1\s+const-string v0, "isRealDevice"[\s\S]*?if-nez p1, :cond_2\s+)'
    sub3 = r'''\1# Security bypass: isRealDevice -> TRUE
    const/4 p1, 0x1
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern3, sub3, content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched flutter_security_checker (r8.1/b.smali)")

def patch_safe_device():
    print(">>> Patching safe_device (z8.1/b.smali)...")
    path = os.path.join(DECOMPILED, "smali_classes3", "z8.1", "b.smali")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. isJailBroken -> return false
    pattern1 = r'(:cond_0\s+const-string v2, "isJailBroken"[\s\S]*?if-eqz v1, :cond_1\s+)'
    sub1 = r'''\1# SafeDevice bypass: isJailBroken -> FALSE
    const/4 p1, 0x0
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern1, sub1, content)

    # 2. isRealDevice -> return true
    pattern2 = r'(:cond_1\s+const-string v2, "isRealDevice"[\s\S]*?if-eqz v1, :cond_\w+\s+)'
    sub2 = r'''\1# SafeDevice bypass: isRealDevice -> TRUE
    const/4 p1, 0x1
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern2, sub2, content)

    # 3. isDevelopmentModeEnable -> return false
    pattern3 = r'(const-string v4, "isDevelopmentModeEnable"[\s\S]*?if-eqz v1, :cond_\w+\s+)'
    sub3 = r'''\1# SafeDevice bypass: isDevelopmentModeEnable -> FALSE
    const/4 p1, 0x0
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern3, sub3, content)

    # 4. usbDebuggingCheck -> return false
    pattern4 = r'(const-string v4, "usbDebuggingCheck"[\s\S]*?if-eqz v1, :cond_\w+\s+)'
    sub4 = r'''\1# SafeDevice bypass: usbDebuggingCheck -> FALSE
    const/4 p1, 0x0
    invoke-static {p1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object p1
    invoke-interface {p2, p1}, Lio/flutter/plugin/common/MethodChannel$Result;->success(Ljava/lang/Object;)V
    return-void

    '''
    content = re.sub(pattern4, sub4, content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched safe_device (z8.1/b.smali)")

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
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

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

    print(">>> Signing APK with uber-apk-signer...")
    cmd = [JAVA, "-jar", SIGNER, "-a", UNSIGNED_APK, "-o", OUTPUT_DIR, "--allowResign"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout[-1500:])
    if res.stderr:
        print("STDERR:", res.stderr[-1500:])
    assert res.returncode == 0, f"uber-apk-signer failed with code {res.returncode}"

    # Copy to user-friendly name
    signed_name = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-v2-unsigned-aligned-debugSigned.apk")
    final_name = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-standalone.apk")
    if os.path.exists(signed_name):
        shutil.copy2(signed_name, final_name)
        print(f"SUCCESS! Output: {final_name} ({os.path.getsize(final_name)} bytes)")

def main():
    patch_adskip_hook()
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
