import zipfile
import io
import re

def inspect_manifest():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        manifest_raw = bz.read('AndroidManifest.xml')
        # Android binary xml string extraction
        strings = re.findall(rb'[\x20-\x7e]{3,}', manifest_raw)
        print("Manifest strings sample:")
        for s in strings:
            s_dec = s.decode(errors='ignore')
            if any(k in s_dec.lower() for k in ['kpn', 'package', 'activity', 'version']):
                print(" ", s_dec)

if __name__ == '__main__':
    inspect_manifest()
