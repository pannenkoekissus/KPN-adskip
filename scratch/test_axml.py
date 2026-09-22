"""
Diagnose the binary-AXML manifest patch WITHOUT building/installing.

Extracts AndroidManifest.xml from the pristine base split, runs the same
add_accessibility_service()/verify()/validate_manifest() pipeline the build uses,
and prints a structural dump of BOTH the original and patched manifests so a
"Corrupt XML binary file" install failure can be pinned down to the exact chunk
or string that is wrong.

Usage:
    python scratch\\test_axml.py

If aapt2 is found (Android SDK build-tools), it also runs `aapt2 dump xmltree`
on the patched manifest as an independent, framework-grade sanity check.
"""
import glob
import os
import struct
import subprocess
import sys
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scratch"))
import axml  # noqa: E402

WORK_DIR = os.path.join(REPO_ROOT, "scratch", "apk_build")
PRISTINE_BASE = os.path.join(WORK_DIR, "base.apk")
BUNDLE = os.path.join(REPO_ROOT, "KPN TV+.apks")
MANIFEST_OUT = os.path.join(WORK_DIR, "patched_AndroidManifest.xml")


def find_pristine_manifest():
    if os.path.exists(PRISTINE_BASE):
        with zipfile.ZipFile(PRISTINE_BASE) as z:
            return z.read("AndroidManifest.xml"), PRISTINE_BASE
    if os.path.exists(BUNDLE):
        with zipfile.ZipFile(BUNDLE) as z:
            for name in z.namelist():
                if name.endswith(".apk") and os.path.basename(name) == "base.apk":
                    data = z.read(name)
                    with zipfile.ZipFile(__import__("io").BytesIO(data)) as inner:
                        return inner.read("AndroidManifest.xml"), BUNDLE
    raise SystemExit("Neither %s nor %s found - run the build once first." % (PRISTINE_BASE, BUNDLE))


def dump_chunks(data, title):
    pool = None
    chunks = axml.read_file(data)
    pool_off = None
    for ct, hs, cs, co in chunks:
        if ct == axml.TYPE_STRING_POOL:
            pool_off = co
    if pool_off is not None:
        pool = axml.parse_string_pool(data, pool_off)
    print("\n=== %s (%d bytes, %d chunks) ===" % (title, len(data), len(chunks)))
    if pool:
        print("  pool: utf8=%s ncount=%d scount=%d flags=0x%x stringsStart=%d stylesStart=%d"
              % (pool["utf8"], pool["ncount"], pool["scount"], pool["flags"],
                 pool["stringsStart"], pool["stylesStart"]))
        print("  first strings: %r" % pool["strings"][:12])
    for ct, hs, cs, co in chunks:
        extra = ""
        if ct == axml.TYPE_START_TAG:
            name_idx = struct.unpack_from("<I", data, co + 20)[0]
            extra = " name=%r" % (pool["strings"][name_idx] if pool and name_idx < len(pool["strings"]) else name_idx)
        print("  @%#06x type=0x%04x hdr=%#x size=%#x%s" % (co, ct, hs, cs, extra))


def find_aapt2():
    candidates = []
    env = os.environ.get("ANDROID_HOME") or os.environ.get("LOCALAPPDATA")
    if env:
        candidates += glob.glob(os.path.join(env, "Android", "Sdk", "build-tools", "*", "aapt2.exe"))
        candidates += glob.glob(os.path.join(env, "build-tools", "*", "aapt2.exe"))
    return candidates[0] if candidates else None


def main():
    orig, src = find_pristine_manifest()
    print("Pristine manifest from %s: %d bytes" % (src, len(orig)))
    dump_chunks(orig, "ORIGINAL manifest")

    patched = axml.add_accessibility_service(orig)
    ok = axml.verify(patched)
    print("\nverify() -> %s" % ok)
    try:
        axml.validate_manifest(patched, original=orig)
        print("validate_manifest() -> PASS")
    except SystemExit as e:
        print(str(e))
        print("\nVALIDATION FAILED - patched manifest is corrupt.")
        dump_chunks(patched, "PATCHED manifest (likely broken)")
        return 1

    dump_chunks(patched, "PATCHED manifest")
    with open(MANIFEST_OUT, "wb") as f:
        f.write(patched)
    print("\nWrote patched manifest to %s" % MANIFEST_OUT)

    aapt2 = find_aapt2()
    built_apk = os.path.join(WORK_DIR, "patched_base.apk")
    if aapt2:
        # Prefer the REAL built base APK: that is the exact artifact that gets
        # installed, so validating its manifest is the closest pre-install
        # simulation of the framework's ResXMLTree parse. Fall back to a
        # synthetic apk (just the manifest) if the build hasn't run yet.
        if os.path.exists(built_apk):
            target = built_apk
            note = "built patched_base.apk"
        else:
            target = os.path.join(WORK_DIR, "_check.apk")
            with zipfile.ZipFile(target, "w") as z:
                z.writestr("AndroidManifest.xml", patched)
            note = "synthetic apk (build not run yet)"
        res = subprocess.run([aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", target],
                             capture_output=True, text=True)
        if res.returncode == 0:
            print("\naapt2 dump xmltree on %s: OK (framework-grade parse succeeded)" % note)
        else:
            print("\naapt2 dump xmltree on %s: FAILED" % note)
            print(res.stdout[-2000:])
            print(res.stderr[-2000:])
            return 1
    else:
        print("\n(aapt2 not found - skipped independent aapt2 check)")
    return 0


if __name__ == "__main__":
    sys.exit(main())