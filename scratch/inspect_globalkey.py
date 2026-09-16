import zipfile
import io
import re

def inspect_globalkeyreceiver():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        data = bz.read('classes3.dex')

    for term in [b'GlobalKeyReceiver', b'tvplusapp/MainActivity']:
        for m in re.finditer(term, data):
            start = max(0, m.start() - 100)
            end = min(len(data), m.end() + 200)
            chunk = data[start:end]
            words = re.findall(rb'[a-zA-Z0-9_\.\-\:\/\$]{3,}', chunk)
            print(f"Context for {term.decode()}:")
            print("  " + " ".join([w.decode(errors='ignore') for w in words]))

if __name__ == '__main__':
    inspect_globalkeyreceiver()
