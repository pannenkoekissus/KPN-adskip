import zipfile
import re
import sys

def scan_strings():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    keywords = [b'trickplay', b'seek', b'adbreak', b'cuepoint', b'commercial', b'restriction']
    
    with zipfile.ZipFile(base_bytes_io := __import__('io').BytesIO(base_bytes)) as bz:
        for fname in bz.namelist():
            if fname.endswith('.dex'):
                print(f"Scanning {fname}...")
                data = bz.read(fname)
                for kw in keywords:
                    matches = [m.start() for m in re.finditer(kw, data, re.IGNORECASE)]
                    print(f"  Keyword '{kw.decode()}' found {len(matches)} times")

if __name__ == '__main__':
    scan_strings()
