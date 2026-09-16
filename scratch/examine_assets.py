import zipfile
import json
import zlib
import io

def examine_assets():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        manifest_data = bz.read('assets/flutter_assets/AssetManifest.json')
        manifest = json.loads(manifest_data.decode('utf-8'))
        print("Asset keys count:", len(manifest))
        packages = set()
        for k in manifest.keys():
            if k.startswith('packages/'):
                pkg = k.split('/')[1]
                packages.add(pkg)
        print("Packages in AssetManifest:", sorted(list(packages)))

        # Also let's check NOTICES.Z
        try:
            notices_compressed = bz.read('assets/flutter_assets/NOTICES.Z')
            notices = zlib.decompress(notices_compressed).decode('utf-8', errors='ignore')
            print("NOTICES length:", len(notices))
            # Find lines like "Package: xyz" or copyright notices
            lines = notices.split('\n')
            pkg_headers = [l for l in lines if l.startswith('---') or 'package' in l.lower()]
            print("Notice sample lines:", pkg_headers[:20])
        except Exception as e:
            print("Error reading NOTICES:", e)

if __name__ == '__main__':
    examine_assets()
