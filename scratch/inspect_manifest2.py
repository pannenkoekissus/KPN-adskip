import zipfile
import io
import re

def inspect_manifest_utf16():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        manifest_raw = bz.read('AndroidManifest.xml')
        # UTF-16LE decode or regex
        chars = []
        for i in range(0, len(manifest_raw) - 1, 2):
            b1 = manifest_raw[i]
            b2 = manifest_raw[i+1]
            if b2 == 0 and 32 <= b1 <= 126:
                chars.append(chr(b1))
            else:
                chars.append('\x00')
        joined = "".join(chars)
        words = re.findall(r'[a-zA-Z0-9_\.\-]{3,}', joined)
        for w in words:
            if any(k in w.lower() for k in ['kpn', 'activity', 'version', 'pca', 'package']):
                print(" ", w)

if __name__ == '__main__':
    inspect_manifest_utf16()
