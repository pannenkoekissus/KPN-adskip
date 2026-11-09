import os, shutil, subprocess, sys, zipfile, glob
sys.path.insert(0, "/root/projects/kpn-adskip/scratch")
import build_v2_linux as v2

WORK = "/root/projects/kpn-adskip/scratch/apk_build"
DECOMPILED = "/root/projects/kpn-adskip/scratch/apk_build/base_decompiled"
UNSIGNED_APK = "/root/projects/kpn-adskip/scratch/apk_build/kpn-tvplus-adskip-armv7a-unsigned.apk"

def run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout: print("STDOUT:", res.stdout[-1500:])
    if res.stderr: print("STDERR:", res.stderr[-1500:])
    if res.returncode != 0:
        raise SystemExit(f"CMD FAILED: {' '.join(cmd)}\n{res.stdout[-800:]}\n{res.stderr[-800:]}")

v2.WORK_DIR = WORK
v2.DECOMPILED = DECOMPILED
v2.OUTPUT_DIR = "/root/projects/kpn-adskip/patch/build/output"
v2.UNSIGNED_APK = UNSIGNED_APK

print(">>> merge resources")
v2.merge_resources()
print(">>> patch manifest")
v2.patch_manifest()
print(">>> rebuild")
run(["/usr/bin/java", "-jar", v2.APKTOOL, "b", DECOMPILED, "-o", UNSIGNED_APK])

import axml
with zipfile.ZipFile(os.path.join(WORK, "base.apk")) as zin:
    orig_manifest = zin.read("AndroidManifest.xml")
patched_manifest = axml.add_accessibility_service(orig_manifest)
if not axml.verify(patched_manifest):
    raise SystemExit("FATAL: accessibility service injection failed.")
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
print("manifest swapped ok")

print(">>> signing")
res = subprocess.run(["/usr/bin/java", "-jar", "/root/projects/kpn-adskip/tools/uber-apk-signer.jar", "-a", UNSIGNED_APK, "-o", "/tmp/opencode/signout3", "--allowResign", "--skipZipAlign"], capture_output=True, text=True)
print(res.stdout[-3000:])
if res.stderr: print("SIGNER STDERR:", res.stderr[-3000:])
if res.returncode != 0: raise SystemExit("Signing failed")
final = "/tmp/opencode/signout3/kpn-tvplus-adskip-armv7a-debugSigned.apk"
print("SIGNED:", final, os.path.getsize(final))
