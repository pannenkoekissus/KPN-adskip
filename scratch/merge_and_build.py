"""
Pipeline to merge split APKs into a monolithic, standalone APK with AdSkipHook injected.
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
TARGET_DIR = os.path.join(WORK_DIR, "standalone_app")
OUTPUT_DIR = r"patch\build\output"
UNSIGNED_APK = os.path.join(WORK_DIR, "kpn-tvplus-adskip-standalone-unsigned.apk")

def step1_prepare_base():
    print(">>> 1. Preparing base directory from manifest_test...")
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    shutil.copytree(os.path.join(WORK_DIR, "manifest_test"), TARGET_DIR)
    
    # Remove any old build artifacts inside TARGET_DIR
    build_cache = os.path.join(TARGET_DIR, "build")
    if os.path.exists(build_cache):
        shutil.rmtree(build_cache)
    print("Prepared target dir:", TARGET_DIR)

def step2_inject_patched_dex():
    print(">>> 2. Injecting patched classes3.dex containing AdSkipHook...")
    src_unsigned = os.path.join(WORK_DIR, "kpn-tvplus-adskip-unsigned.apk")
    with zipfile.ZipFile(src_unsigned, 'r') as z:
        c3_data = z.read("classes3.dex")
    
    assert b"AdSkipHook" in c3_data, "AdSkipHook not found in classes3.dex!"
    
    dest_c3 = os.path.join(TARGET_DIR, "classes3.dex")
    with open(dest_c3, "wb") as f:
        f.write(c3_data)
    print("Injected patched classes3.dex (size:", len(c3_data), "bytes)")

def step3_inject_native_libs():
    print(">>> 3. Extracting and injecting arm64-v8a native libraries...")
    apks_file = "KPN TV+.apks"
    lib_target = os.path.join(TARGET_DIR, "lib", "arm64-v8a")
    os.makedirs(lib_target, exist_ok=True)
    
    with zipfile.ZipFile(apks_file) as apks:
        with apks.open("split_config.arm64_v8a.apk") as split_arm:
            with zipfile.ZipFile(split_arm) as z_arm:
                for item in z_arm.namelist():
                    if item.startswith("lib/arm64-v8a/") and item.endswith(".so"):
                        fname = os.path.basename(item)
                        so_data = z_arm.read(item)
                        out_path = os.path.join(lib_target, fname)
                        with open(out_path, "wb") as out_f:
                            out_f.write(so_data)
                        print(f"  Extracted {fname} ({len(so_data)} bytes)")

def step4_merge_resources():
    print(">>> 4. Merging Dutch strings and xxhdpi drawables...")
    # Dutch strings
    nl_res = os.path.join(WORK_DIR, "nl_decompiled", "res", "values-nl")
    target_nl = os.path.join(TARGET_DIR, "res", "values-nl")
    if os.path.exists(nl_res):
        if os.path.exists(target_nl):
            shutil.rmtree(target_nl)
        shutil.copytree(nl_res, target_nl)
        print("  Copied values-nl")
        
    # xxhdpi drawables
    xxhdpi_res = os.path.join(WORK_DIR, "xxhdpi_decompiled", "res")
    target_res = os.path.join(TARGET_DIR, "res")
    for item in os.listdir(xxhdpi_res):
        if item.startswith("drawable-"):
            src_d = os.path.join(xxhdpi_res, item)
            dst_d = os.path.join(target_res, item)
            os.makedirs(dst_d, exist_ok=True)
            for f in os.listdir(src_d):
                shutil.copy2(os.path.join(src_d, f), dst_d)
            print(f"  Merged {item}")

def step5_patch_manifest():
    print(">>> 5. Patching AndroidManifest.xml for standalone installation...")
    manifest_path = os.path.join(TARGET_DIR, "AndroidManifest.xml")
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove requiredSplitTypes and splitTypes from <manifest>
    content = re.sub(r'\s*android:requiredSplitTypes="[^"]*"', '', content)
    content = re.sub(r'\s*android:splitTypes="[^"]*"', '', content)

    # 2. Change extractNativeLibs to true
    content = re.sub(r'android:extractNativeLibs="false"', 'android:extractNativeLibs="true"', content)

    # 3. Remove isFeatureSplit if present
    content = re.sub(r'\s*android:isFeatureSplit="[^"]*"', '', content)

    # 4. Remove all split meta-data lines
    lines = [line for line in content.splitlines(True) if "com.android.vending.splits" not in line]
    content = "".join(lines)

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # Remove splits0.xml resource if exists
    splits_xml = os.path.join(TARGET_DIR, "res", "xml", "splits0.xml")
    if os.path.exists(splits_xml):
        os.remove(splits_xml)
    print("Manifest successfully modified and split metadata purged.")

def step6_rebuild():
    print(">>> 6. Rebuilding monolithic APK with apktool...")
    cmd = [JAVA, "-jar", APKTOOL, "b", TARGET_DIR, "-o", UNSIGNED_APK]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout[-1000:])
    if res.stderr:
        print("STDERR:", res.stderr[-1000:])
    assert res.returncode == 0, f"apktool failed with code {res.returncode}"
    print(f"Built unsigned APK: {UNSIGNED_APK} ({os.path.getsize(UNSIGNED_APK)} bytes)")

def step7_sign():
    print(">>> 7. Signing APK with uber-apk-signer...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cmd = [JAVA, "-jar", SIGNER, "-a", UNSIGNED_APK, "-o", OUTPUT_DIR, "--allowResign"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout[-1500:])
    if res.stderr:
        print("STDERR:", res.stderr[-1500:])
    assert res.returncode == 0, f"Signer failed with code {res.returncode}"
    print("Signing complete!")

def main():
    step1_prepare_base()
    step2_inject_patched_dex()
    step3_inject_native_libs()
    step4_merge_resources()
    step5_patch_manifest()
    step6_rebuild()
    step7_sign()
    print("\nSUCCESS! Final APK files in", OUTPUT_DIR)
    for f in os.listdir(OUTPUT_DIR):
        fp = os.path.join(OUTPUT_DIR, f)
        print(f"  - {f} ({os.path.getsize(fp)} bytes)")

if __name__ == "__main__":
    main()
