import zipfile
import io
import re

def search_kpntv():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        for fname in bz.namelist():
            if fname.endswith('.dex'):
                data = bz.read(fname)
                matches = list(re.finditer(rb'kpntv[a-zA-Z0-9_]*', data, re.IGNORECASE))
                if matches:
                    print(f"In {fname}:")
                    for m in set([match.group(0) for match in matches]):
                        print(" ", m.decode(errors='ignore'))

if __name__ == '__main__':
    search_kpntv()
