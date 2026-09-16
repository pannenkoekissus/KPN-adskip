import os
import subprocess
import shutil
import zipfile

JDK_BIN = r"C:\Program Files\Java\openjdk-22_windows-x64_bin\jdk-22\bin"
JAVAC = os.path.join(JDK_BIN, "javac.exe")
JAR = os.path.join(JDK_BIN, "jar.exe")
ANDROID_JAR = r"C:\Users\Gebruiker\AppData\Local\Android\Sdk\platforms\android-34\android.jar"
D8 = r"C:\Users\Gebruiker\AppData\Local\Android\Sdk\build-tools\35.0.0\d8.bat"

def build_patch_jar():
    print("=== Step 1: Compiling Java Hook ===")
    out_dir = r"patch\build\classes"
    os.makedirs(out_dir, exist_ok=True)
    
    src = r"patch\src\main\java\software\morphe\kpn\AdSkipHook.java"
    cmd = [
        JAVAC,
        "-cp", ANDROID_JAR,
        "-d", out_dir,
        "-source", "8",
        "-target", "8",
        src
    ]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("javac stdout:", res.stdout)
    print("javac stderr:", res.stderr)
    if res.returncode != 0:
        raise RuntimeError("javac failed")

    print("=== Step 2: Creating Patch Bundle JAR ===")
    libs_dir = r"patch\build\libs"
    os.makedirs(libs_dir, exist_ok=True)
    jar_file = os.path.join(libs_dir, "kpn-tvplus-adskip-patch-2.1.0.jar")

    cmd = [
        JAR,
        "cf", jar_file,
        "-C", out_dir, "."
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("jar creation:", jar_file, "Result code:", res.returncode)

    print("=== Step 3: Compiling to DEX with D8 ===")
    dex_out = r"patch\build\dex"
    os.makedirs(dex_out, exist_ok=True)

    class_files = []
    for root, _, files in os.walk(out_dir):
        for f in files:
            if f.endswith(".class"):
                class_files.append(os.path.join(root, f))

    cmd = [D8, "--output", dex_out, "--lib", ANDROID_JAR] + class_files
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("d8 stdout:", res.stdout)
    print("d8 stderr:", res.stderr)
    print("DEX files in dex_out:", os.listdir(dex_out))

if __name__ == '__main__':
    build_patch_jar()
