"""
Script to create the final standalone APK combining:
1. test_smali_build.apk (uncompressed .so + patched smali_classes3)
2. Clean split-free AndroidManifest.xml from standalone_app
3. uber-apk-signer (zipalign + v1/v2/v3 signatures)
"""
import os
import zipfile
import subprocess
import shutil

JAVA = r"C:\Program Files\Java\openjdk-22_windows-x64_bin\jdk-22\bin\java.exe"
SIGNER = r"tools\uber-apk-signer.jar"
WORK_DIR = r"scratch\apk_build"
SMALI_APK = os.path.join(WORK_DIR, "test_smali_build.apk")
CLEAN_MANIFEST_APK = os.path.join(WORK_DIR, "kpn-tvplus-adskip-standalone-unsigned.apk")
COMBINED_UNSIGNED = os.path.join(WORK_DIR, "kpn-final-unsigned.apk")
OUTPUT_DIR = r"patch\build\output"
FINAL_APK = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-standalone.apk")

def main():
    print(">>> 1. Extracting clean split-free AndroidManifest.xml...")
    with zipfile.ZipFile(CLEAN_MANIFEST_APK, 'r') as z:
        clean_manifest = z.read("AndroidManifest.xml")
    print(f"Clean manifest size: {len(clean_manifest)} bytes")

    print(">>> 2. Assembling combined APK...")
    with zipfile.ZipFile(SMALI_APK, 'r') as src_zip:
        with zipfile.ZipFile(COMBINED_UNSIGNED, 'w') as dst_zip:
            for item in src_zip.infolist():
                if item.filename == "AndroidManifest.xml":
                    # Replace with clean split-free manifest
                    dst_zip.writestr(item, clean_manifest)
                    print("  Replaced AndroidManifest.xml with clean version")
                elif item.filename.startswith("META-INF/"):
                    # Skip old signatures, uber-apk-signer will generate clean ones
                    continue
                else:
                    data = src_zip.read(item.filename)
                    # Preserve original compression (stored for .so, deflated for dex/assets)
                    dst_zip.writestr(item, data)

    print(f">>> Combined unsigned APK created: {COMBINED_UNSIGNED} ({os.path.getsize(COMBINED_UNSIGNED)} bytes)")

    print(">>> 3. Signing and 4KB page-aligning APK...")
    cmd = [JAVA, "-jar", SIGNER, "-a", COMBINED_UNSIGNED, "-o", OUTPUT_DIR, "--allowResign"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout[-1500:])
    if res.stderr:
        print("STDERR:", res.stderr[-1500:])
    assert res.returncode == 0, f"Signing failed with code {res.returncode}"

    # Rename / copy output to user-friendly final path
    signed_name = os.path.join(OUTPUT_DIR, "kpn-final-unsigned-aligned-debugSigned.apk")
    if os.path.exists(signed_name):
        shutil.copy2(signed_name, FINAL_APK)
        print(f"\n==========================================")
        print(f"SUCCESS! Ready to install:")
        print(f"  {FINAL_APK} ({os.path.getsize(FINAL_APK)} bytes)")
        print(f"==========================================")

if __name__ == "__main__":
    main()
