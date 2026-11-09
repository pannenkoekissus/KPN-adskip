import os, shutil, subprocess, zipfile

SIGNER = "/root/projects/kpn-adskip/tools/uber-apk-signer.jar"
PKG = "/tmp/opencode/pkg"
OUT = "/tmp/opencode/pkgout"
DEST = "/root/projects/kpn-adskip/patch/build/output/kpn-tvplus-adskip-armv7a-splits.apks"
WORK = "/root/projects/kpn-adskip/scratch/apk_build"

items = [
    ("patched_base.apk", "/root/projects/kpn-adskip/scratch/apk_build/kpn-tvplus-adskip-armv7a-unsigned.apk"),
    ("split_config.arm64_v8a.apk", "/root/projects/kpn-adskip/scratch/apk_build/split_config.arm64_v8a.apk"),
    ("split_config.armeabi_v7a.apk", "/root/projects/kpn-adskip/scratch/apk_build/split_config.armeabi_v7a.apk"),
    ("split_config.xxhdpi.apk", "/root/projects/kpn-adskip/scratch/apk_build/split_config.xxhdpi.apk"),
    ("split_config.nl.apk", "/root/projects/kpn-adskip/scratch/apk_build/split_config.nl.apk"),
]

signed = {}
for src_name, src_path in items:
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    res = subprocess.run(["/usr/bin/java", "-jar", SIGNER, "-a", src_path, "-o", OUT, "--allowResign", "--skipZipAlign"], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"sign failed for {src_path}: {res.stdout[-1500:]} {res.stderr[-1500:]}")
    produced = [f for f in os.listdir(OUT) if f.endswith(".apk")]
    if len(produced) != 1:
        raise SystemExit(f"expected 1 output for {src_path}, got {produced}")
    signed[src_name] = os.path.join(OUT, produced[0])

os.makedirs("/tmp/opencode/pkgfinal", exist_ok=True)
for f in os.listdir("/tmp/opencode/pkgfinal"):
    os.remove(os.path.join("/tmp/opencode/pkgfinal", f))
with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED) as z:
    for name, path in signed.items():
        z.write(path, arcname=name)
        print("wrote", name, os.path.getsize(path))
print("DEST:", DEST, os.path.getsize(DEST))
