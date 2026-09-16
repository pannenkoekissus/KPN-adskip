import zipfile
import io
import struct

def parse_class():
    with zipfile.ZipFile('KPN TV+.apks') as z:
        base_bytes = z.read('base.apk')

    with zipfile.ZipFile(io.BytesIO(base_bytes)) as bz:
        data = bz.read('classes3.dex')

    string_ids_size, string_ids_off = struct.unpack_from('<II', data, 0x38)
    type_ids_size, type_ids_off = struct.unpack_from('<II', data, 0x40)
    method_ids_size, method_ids_off = struct.unpack_from('<II', data, 0x58)
    class_defs_size, class_defs_off = struct.unpack_from('<II', data, 0x60)

    def get_str(idx):
        off = struct.unpack_from('<I', data, string_ids_off + idx * 4)[0]
        pos = off
        length, shift = 0, 0
        while True:
            b = data[pos]
            pos += 1
            length |= (b & 0x7f) << shift
            if not (b & 0x80): break
            shift += 7
        end = data.find(b'\x00', pos)
        return data[pos:end].decode('utf-8', errors='ignore')

    def get_type(idx):
        descriptor_idx = struct.unpack_from('<I', data, type_ids_off + idx * 4)[0]
        return get_str(descriptor_idx)

    def get_method(idx):
        class_idx, proto_idx, name_idx = struct.unpack_from('<HHI', data, method_ids_off + idx * 8)
        return get_type(class_idx), get_str(name_idx)

    # find class_def for VideoPlayer
    for c in range(class_defs_size):
        class_idx = struct.unpack_from('<I', data, class_defs_off + c * 32)[0]
        cname = get_type(class_idx)
        if cname == 'Lio/flutter/plugins/videoplayer/VideoPlayer;':
            print("Found class def:", cname)
            class_data_off = struct.unpack_from('<I', data, class_defs_off + c * 32 + 24)[0]
            print("class_data_off:", hex(class_data_off))
            break

if __name__ == '__main__':
    parse_class()
