"""离线PE头检查，不能据此证明任何运行时指针或坐标有效。"""
import hashlib
import re
import struct


def inspect_pe(stream):
    def read_at(offset, count):
        if offset < 0:
            raise ValueError('PE偏移为负')
        stream.seek(offset)
        data = stream.read(count)
        if len(data) != count:
            raise ValueError('PE文件截断')
        return data
    if read_at(0, 2) != b'MZ':
        raise ValueError('不是DOS/PE文件')
    pe = struct.unpack('<I', read_at(0x3C, 4))[0]
    if read_at(pe, 4) != b'PE\0\0':
        raise ValueError('PE签名错误')
    machine, count, timestamp, _, _, optional_size, _ = struct.unpack('<HHIIIHH', read_at(pe+4, 20))
    if not 1 <= count <= 96 or optional_size < 112:
        raise ValueError('PE节数量或可选头尺寸异常')
    optional = read_at(pe+24, optional_size)
    magic = struct.unpack_from('<H',optional)[0]
    if machine != 0x8664 or magic != 0x20B:
        raise ValueError('需要AMD64 PE32+文件')
    result = {'machine': 'AMD64', 'optional_header': 'PE32+',
              'coff_timestamp_raw': timestamp,
              'image_size': struct.unpack_from('<I',optional,56)[0],
              'sections': []}
    for index in range(count):
        data = read_at(pe+24+optional_size+index*40, 40)
        name = data[:8].split(b'\0')[0].decode('ascii',errors='replace')
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from('<IIII',data,8)
        flags = struct.unpack_from('<I',data,36)[0]
        result['sections'].append({'name':name, 'rva':rva, 'virtual_size':virtual_size,
            'raw_size':raw_size, 'raw_offset':raw_offset,
            'readable':bool(flags & 0x40000000), 'writable':bool(flags & 0x80000000),
            'executable':bool(flags & 0x20000000)})
    return result


def locate_rva(pe, rva, size):
    if rva < 0 or size <= 0 or rva+size > pe['image_size']:
        return {'in_image':False, 'section':None}
    for section in pe['sections']:
        if section['rva'] <= rva and rva+size <= section['rva']+max(section['virtual_size'],section['raw_size']):
            return {'in_image':True, 'section':section['name'],
                    'readable':section['readable'], 'writable':section['writable'],
                    'executable':section['executable']}
    return {'in_image':True, 'section':None}


def inspect_build(exe_path, manifest_path, offsets):
    with exe_path.open('rb') as stream:
        digest = hashlib.file_digest(stream,'sha256').hexdigest()
        pe = inspect_pe(stream)
    # 清单可能含Steam账号，严格仅输出四个构建字段，不保存原始文件。
    manifest = manifest_path.read_text(encoding='utf-8-sig')
    steam = {key: match[1] for key in ('appid','name','buildid','LastUpdated')
             if (match := re.search(r'"'+key+r'"\s+"([^"\r\n]*)"',manifest))}
    return {'sha256':digest, 'steam':steam, 'pe':pe,
            'historical_rvas':{name: {'rva':hex(offsets[name]), **locate_rva(pe,offsets[name],size)}
                               for name,size in (('animals',8),('camera',12))},
            'runtime_access_attempted':False, 'offsets_verified':False,
            'warning':'落在可读数据节仅是必要条件；不证明字段含义或指针链有效。COFF时间戳不能直接认定为发行日期。'}
