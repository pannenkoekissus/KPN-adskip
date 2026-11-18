"""
Split-safe Morphe packaging for KPN TV+ (see MORPHE.md, section 5.5).

Morphe Manager and the Morphe CLI auto-merge an `.apks` bundle before patching.
KPN TV+ must keep its splits: the density/locale splits own resource files that
base.apk references (merging them corrupts the shared resource table -> PlayerView
inflate crash). This script therefore:

  1. downloads the Morphe Desktop CLI jar (pinned) and builds the patch bundle
     `patch/build/output/kpn-tvplus-adskip.mpp` with Gradle,
  2. extracts `base.apk` from the input bundle and patches ONLY that file,
  3. keeps every config split untouched (same entries, same bytes per entry) and
     re-signs every APK with one debug certificate,
  4. bundles the result as an installable `.apks`.

Usage:
    python scratch/build_morphe_splits.py [OPTIONS]

    --input PATH        Split bundle to patch (default: KPN TV+.apks). Accepts
                        any .apks/.apkm/.xapk/zip that has base.apk + splits.
    --output PATH       Where to write the signed bundle
                        (default: patch/build/output/kpn-tvplus-adskip-morphe-splits.apks).
    --skip-build        Reuse patch/build/output/kpn-tvplus-adskip.mpp.
    --mpp PATH          Use an existing patch bundle instead of building one.
    --resign-only DIR   Do not patch. Take base.apk + split_config.*.apk from DIR,
                        which is useful when Manager already patched the base, and
                        only re-sign and repackage them.

Examples:
    python scratch/build_morphe_splits.py --input "KPN TV+.apks"
    python scratch/build_morphe_splits.py --input "KPN TV TV+.apks" --output tv.apks
    python scratch/build_morphe_splits.py --resign-only scratch/manager-output

Requirements: JDK 17+ on PATH (or JAVA set), Android SDK build-tools for
verification, network access for the first run (Morphe CLI + Gradle/Kotlin
dependencies).
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.getcwd() != REPO_ROOT:
    os.chdir(REPO_ROOT)

JAVA = os.environ.get("JAVA") or shutil.which("java") or "java"
PATCH_DIR = os.path.join(REPO_ROOT, "patch")
GRADLEW = os.path.join(PATCH_DIR, "gradlew.bat" if os.name == "nt" else "gradlew")
BUNDLE = os.path.join(REPO_ROOT, "KPN TV+.apks")
OUTPUT_DIR = os.path.join(PATCH_DIR, "build", "output")
WORK_DIR = os.path.join(PATCH_DIR, "build", "morphe")
CACHE_DIR = os.path.join(WORK_DIR, "cache")
DEFAULT_MPP = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip.mpp")
FINAL_APKS = os.path.join(OUTPUT_DIR, "kpn-tvplus-adskip-morphe-splits.apks")

MORPHE_VERSION = "2.2.0"
MORPHE_JAR_NAME = "morphe-desktop-%s-all.jar" % MORPHE_VERSION
MORPHE_JAR_URL = (
    "https://github.com/MorpheApp/morphe-desktop/releases/download/v%s/%s"
    % (MORPHE_VERSION, MORPHE_JAR_NAME)
)

PATCH_NAME = "KPN TV+ AdSkip & Seek Unlock"
SIGNER = os.path.join(REPO_ROOT, "tools", "uber-apk-signer.jar")

# Classes the patch must add to the output DEX. Cheap sanity check: every DEX
# string pool stores type descriptors verbatim.
REQUIRED_DEX_STRINGS = [
    b"Lsoftware/morphe/kpn/AdSkipHook;",
    b"Lsoftware/morphe/kpn/AdSkipButton;",
]

CONFIG_SPLIT_PREFIX = "split_config."


def log(message):
    print(">>> " + message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_morphe_jar():
    os.makedirs(CACHE_DIR, exist_ok=True)
    jar = os.path.join(CACHE_DIR, MORPHE_JAR_NAME)
    if os.path.exists(jar) and os.path.getsize(jar) > 10 * 1024 * 1024:
        return jar
    log("Downloading %s" % MORPHE_JAR_NAME)
    tmp = jar + ".part"
    urllib.request.urlretrieve(MORPHE_JAR_URL, tmp)
    os.replace(tmp, jar)
    return jar


def build_mpp(morphe_jar):
    log("Building patch bundle with Gradle")
    env = dict(os.environ)
    env["MORPHE_DESKTOP_JAR"] = morphe_jar
    result = subprocess.run(
        [GRADLEW, "bundleMpp", "--console=plain", "-PmorpheDesktopJar=%s" % morphe_jar],
        cwd=PATCH_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stdout or "")[-2500:] + (result.stderr or "")[-2500:]
        raise SystemExit("Gradle build failed:\n" + tail)
    if not os.path.exists(DEFAULT_MPP):
        raise SystemExit("Gradle did not produce %s" % DEFAULT_MPP)
    log("Built %s (%d bytes)" % (os.path.basename(DEFAULT_MPP), os.path.getsize(DEFAULT_MPP)))
    return DEFAULT_MPP


def verify_mpp(mpp):
    """A bundle has to satisfy both loaders: the CLI reads .class files, Manager
    reads a DEX and rejects the bundle when there is no non-empty .dex entry."""
    log("Verifying patch bundle")
    with zipfile.ZipFile(mpp) as bundle:
        entries = bundle.infolist()
        dex_entries = [entry for entry in entries if entry.filename.lower().endswith(".dex")]
        if not dex_entries:
            raise SystemExit("patch bundle has no DEX entry; Morphe Manager cannot load it")
        empty = [entry.filename for entry in dex_entries if entry.file_size <= 0]
        if empty:
            raise SystemExit("patch bundle has empty DEX entries: %s" % ", ".join(empty))
        class_entries = [entry.filename for entry in entries if entry.filename.endswith(".class")]
        if not class_entries:
            raise SystemExit("patch bundle has no JVM classes; the Morphe CLI cannot load it")
        extensions = [
            entry.filename
            for entry in entries
            if entry.filename.startswith("extensions/") and entry.filename.endswith(".mpe")
        ]
        if not extensions:
            raise SystemExit("patch bundle has no extension under extensions/")
    log(
        "Patch bundle carries %d DEX entry, %d classes and %d extension(s)"
        % (len(dex_entries), len(class_entries), len(extensions))
    )


def extract_bundle(bundle_path, work_dir):
    log("Extracting splits from %s" % os.path.basename(bundle_path))
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)
    with zipfile.ZipFile(bundle_path) as bundle:
        names = [n for n in bundle.namelist() if n.endswith(".apk")]
        if "base.apk" not in names:
            raise SystemExit(
                "base.apk not found in %s (found: %s)"
                % (bundle_path, ", ".join(names) or "no .apk entries")
            )
        for name in names:
            bundle.extract(name, work_dir)
    base = os.path.join(work_dir, "base.apk")
    configs = sorted(
        os.path.join(work_dir, name)
        for name in os.listdir(work_dir)
        if name.startswith(CONFIG_SPLIT_PREFIX) and name.endswith(".apk")
    )
    if not configs:
        raise SystemExit("no config splits found in %s" % bundle_path)
    log("Found base.apk + %d config split(s)" % len(configs))
    return base, configs


def collect_apks(directory):
    directory = os.path.abspath(directory)
    log("Collecting APKs from %s" % directory)
    if not os.path.isdir(directory):
        raise SystemExit("not a directory: %s" % directory)
    names = sorted(
        name for name in os.listdir(directory)
        if name.endswith(".apk") and os.path.isfile(os.path.join(directory, name))
    )
    if "base.apk" not in names:
        raise SystemExit(
            "base.apk not found in %s (found: %s)"
            % (directory, ", ".join(names) or "no .apk files")
        )
    configs = [
        os.path.join(directory, name)
        for name in names
        if name.startswith(CONFIG_SPLIT_PREFIX)
    ]
    if not configs:
        raise SystemExit("no split_config.*.apk files found in %s" % directory)
    log("Found base.apk + %d config split(s)" % len(configs))
    return os.path.join(directory, "base.apk"), configs


def ensure_debug_keystore():
    keystore = os.path.expanduser(r"~\.android\debug.keystore")
    if os.path.exists(keystore):
        return keystore
    os.makedirs(os.path.dirname(keystore), exist_ok=True)
    log("Creating %s" % keystore)
    subprocess.run(
        [
            "keytool", "-genkeypair", "-v",
            "-keystore", keystore, "-storepass", "android",
            "-alias", "androiddebugkey", "-keypass", "android",
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-dname", "CN=Android Debug,O=Android,C=US",
        ],
        check=True,
        capture_output=True,
    )
    return keystore


def patch_base(morphe_jar, mpp, base, work_dir, keystore):
    log("Patching base.apk with Morphe (splits are not merged)")
    patched = os.path.join(work_dir, "base-patched.apk")
    if os.path.exists(patched):
        os.remove(patched)
    result_json = os.path.join(work_dir, "result.json")
    cmd = [
        JAVA, "-jar", morphe_jar, "patch",
        "-p", mpp,
        "--exclusive",
        "-e", PATCH_NAME,
        "--continue-on-error",
        "-f",
        "-r", result_json,
        "-o", patched,
        "--keystore", keystore,
        "--keystore-password", "android",
        "--keystore-entry-alias", "androiddebugkey",
        "--keystore-entry-password", "android",
        base,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 or not os.path.exists(patched):
        raise SystemExit("Morphe patching failed:\n" + output[-4000:])
    for line in output.splitlines():
        if "[KPN AdSkip]" in line or "INFO: Applied" in line:
            print("    " + line.strip())
    if os.path.exists(result_json):
        with open(result_json, "r", encoding="utf-8") as handle:
            payload = handle.read()
        if '"success":false' in payload:
            raise SystemExit("Morphe reported a failed patch:\n" + payload)
    log("Patched base APK: %s" % patched)
    return patched


def verify_base_apk(patched_base, original_base):
    log("Verifying patched base APK")
    found = set()
    with zipfile.ZipFile(patched_base) as dex_zip:
        for name in dex_zip.namelist():
            if not (name.startswith("classes") and name.endswith(".dex")):
                continue
            data = dex_zip.read(name)
            for needle in REQUIRED_DEX_STRINGS:
                if needle in data:
                    found.add(needle)
    missing = [n.decode() for n in REQUIRED_DEX_STRINGS if n not in found]
    if missing:
        raise SystemExit("patch classes missing from output DEX: %s" % ", ".join(missing))

    with zipfile.ZipFile(original_base) as original, zipfile.ZipFile(patched_base) as patched:
        if hashlib.sha256(original.read("resources.arsc")).digest() != hashlib.sha256(
            patched.read("resources.arsc")
        ).digest():
            raise SystemExit("resources.arsc changed in base.apk; refusing to ship")
    log("AdSkipHook classes present, resources.arsc unchanged")


def sign_apk(apk_path, out_dir):
    result = subprocess.run(
        [JAVA, "-jar", SIGNER, "-a", apk_path, "-o", out_dir, "--allowResign"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stdout or "")[-1500:] + (result.stderr or "")[-1500:]
        raise SystemExit("Signing failed for %s:\n%s" % (apk_path, tail))
    stem = os.path.basename(apk_path).rsplit(".apk", 1)[0]
    candidates = [
        os.path.join(out_dir, name)
        for name in os.listdir(out_dir)
        if name.startswith(stem) and name.endswith(".apk")
    ]
    if not candidates:
        raise SystemExit("Signer produced no APK for %s" % apk_path)
    return max(candidates, key=os.path.getmtime)


def assert_split_entries_unchanged(original, signed):
    """Config splits must keep the exact same payload; only signatures may differ.

    `stamp-cert-sha256` is the Play signing-certificate stamp; the signer strips it
    because the split is now signed by the debug key.
    """
    ignored = ("META-INF/", "stamp-cert-sha256")
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(signed) as after:
        before_entries = {
            info.filename: hashlib.sha256(before.read(info.filename)).hexdigest()
            for info in before.infolist()
            if not info.is_dir() and not info.filename.startswith(ignored)
        }
        after_entries = {
            info.filename: hashlib.sha256(after.read(info.filename)).hexdigest()
            for info in after.infolist()
            if not info.is_dir() and not info.filename.startswith(ignored)
        }
    added = sorted(set(after_entries) - set(before_entries))
    removed = sorted(set(before_entries) - set(after_entries))
    changed = sorted(
        name for name in set(before_entries) & set(after_entries)
        if before_entries[name] != after_entries[name]
    )
    if added or removed or changed:
        raise SystemExit(
            "config split payload changed (%s): added=%s removed=%s changed=%s"
            % (os.path.basename(signed), added, removed, changed)
        )


def verify_common_certificate(apk_paths, sdk_dir=None):
    sdk_dir = sdk_dir or os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "build-tools"
    )
    apksigner = None
    if os.path.isdir(sdk_dir):
        versions = sorted(os.listdir(sdk_dir), reverse=True)
        for version in versions:
            candidate = os.path.join(sdk_dir, version, "apksigner.bat")
            if os.path.exists(candidate):
                apksigner = candidate
                break
    if not apksigner:
        log("apksigner not found; skipping certificate comparison")
        return
    digests = set()
    for apk in apk_paths:
        result = subprocess.run(
            [apksigner, "verify", "--print-certs", apk],
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        digest = next(
            (line.split(":", 1)[1].strip() for line in output.splitlines()
             if "SHA-256 digest" in line),
            None,
        )
        if not digest:
            raise SystemExit("could not read certificate of %s:\n%s" % (apk, output[-800:]))
        digests.add(digest)
    if len(digests) != 1:
        raise SystemExit("splits are signed by different certificates: %s" % digests)
    log("All splits share certificate %s" % next(iter(digests))[:16] + "...")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=BUNDLE,
                        help="Split bundle to patch (default: %s)" % os.path.basename(BUNDLE))
    parser.add_argument("--output", default=FINAL_APKS,
                        help="Where to write the signed bundle")
    parser.add_argument("--skip-build", action="store_true",
                        help="Reuse patch/build/output/kpn-tvplus-adskip.mpp")
    parser.add_argument("--mpp", help="Path to an existing .mpp bundle")
    parser.add_argument("--resign-only", metavar="DIR",
                        help="Skip Morphe and only re-sign base.apk + split_config.*.apk in DIR")
    args = parser.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.resign_only:
        base, configs = collect_apks(args.resign_only)
        base_to_sign = base
    else:
        morphe_jar = ensure_morphe_jar()
        mpp = args.mpp or (DEFAULT_MPP if args.skip_build else build_mpp(morphe_jar))
        if not os.path.exists(mpp):
            raise SystemExit("patch bundle not found: %s" % mpp)
        verify_mpp(mpp)

        keystore = ensure_debug_keystore()
        base, configs = extract_bundle(args.input, os.path.join(WORK_DIR, "bundle"))
        base_to_sign = patch_base(morphe_jar, mpp, base, WORK_DIR, keystore)
        verify_base_apk(base_to_sign, base)

    log("Signing every split with one certificate")
    signed_dir = os.path.join(WORK_DIR, "signed")
    if os.path.exists(signed_dir):
        shutil.rmtree(signed_dir)
    os.makedirs(signed_dir)

    staged_dir = os.path.join(WORK_DIR, "staged")
    if os.path.exists(staged_dir):
        shutil.rmtree(staged_dir)
    os.makedirs(staged_dir)

    staged = []
    for apk in [base_to_sign] + configs:
        signed = sign_apk(apk, signed_dir)
        if apk in configs:
            assert_split_entries_unchanged(apk, signed)
        # Keep the canonical split names inside the bundle.
        target_name = "base.apk" if apk == base_to_sign else os.path.basename(apk)
        target = os.path.join(staged_dir, target_name)
        shutil.copy2(signed, target)
        staged.append(target)
        log("  %s -> %s" % (os.path.basename(apk), target_name))

    verify_common_certificate(staged)

    output = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    log("Bundling %s" % os.path.basename(output))
    if os.path.exists(output):
        os.remove(output)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for apk in staged:
            bundle.write(apk, arcname=os.path.basename(apk))
    log("Done: %s (%d bytes)" % (output, os.path.getsize(output)))
    log(
        "Install with: adb install-multiple "
        + " ".join(os.path.basename(apk) for apk in staged)
    )


if __name__ == "__main__":
    main()
