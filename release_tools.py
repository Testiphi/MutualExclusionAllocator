"""九个静态文件的校验、打包和版本切换；不修改Nginx配置。"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

FILES = ('index.html', 'styles.css', 'config.js', 'app_state.js', 'api.js',
         'allocator.js', 'race_scores.js', 'gauntlet_data.json', 'cars.json')


def manifest(contents):
    files = {name: {'sha256': hashlib.sha256(contents[name]).hexdigest(), 'size': len(contents[name])}
             for name in FILES}
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:24]
    return {'version': 1, 'id': identity, 'files': files}


def pack(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('输出已存在，请使用新的压缩包路径')
    contents = {name: (source / name).read_bytes() for name in FILES}
    info = manifest(contents)
    descriptor, filename = tempfile.mkstemp(suffix='.zip', dir=output.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in contents.items():
                archive.writestr(name, content)
            archive.writestr('manifest.json', json.dumps(info, ensure_ascii=False, indent=2))
        os.replace(filename, output)
    finally:
        Path(filename).unlink(missing_ok=True)
    return info


def stage(bundle, base):
    base = Path(base)
    with zipfile.ZipFile(bundle) as archive:
        if len(archive.namelist()) != len(FILES) + 1 or set(archive.namelist()) != set(FILES) | {'manifest.json'}:
            raise ValueError('包内文件必须与九个静态文件及manifest一致')
        if any(item.file_size > 10 * 1024 * 1024 for item in archive.infolist()):
            raise ValueError('包内文件超过大小限制')
        contents = {name: archive.read(name) for name in FILES}
        info = json.loads(archive.read('manifest.json'))
    if info != manifest(contents):
        raise ValueError('发布包校验失败')
    base.mkdir(parents=True, exist_ok=True)
    target = base / info['id']
    if target.is_symlink():
        raise ValueError('版本目录不能是符号链接')
    if target.exists():
        verify(target)
        return target
    temporary = Path(tempfile.mkdtemp(prefix='.stage-', dir=base))
    try:
        temporary.chmod(0o755)
        for name, content in contents.items():
            path = temporary / name
            path.write_bytes(content)
            path.chmod(0o644)
        (temporary / 'manifest.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        os.rename(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def verify(target):
    target = Path(target)
    contents = {name: (target / name).read_bytes() for name in FILES}
    info = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
    if info != manifest(contents) or target.name != info['id']:
        raise ValueError('版本目录内容校验失败')
    return info


def activate(base, identity):
    base = Path(base).resolve()
    if len(identity) != 24 or any(char not in '0123456789abcdef' for char in identity):
        raise ValueError('无效版本ID')
    target = base / identity
    if target.is_symlink():
        raise ValueError('版本目录不能是符号链接')
    verify(target)
    current = base / 'current'
    if current.exists() and not current.is_symlink():
        raise ValueError('current已存在且不是符号链接，不会覆盖')
    previous = os.readlink(current) if current.is_symlink() else None
    descriptor, name = tempfile.mkstemp(prefix='.link-', dir=base)
    os.close(descriptor)
    temporary = Path(name)
    temporary.unlink()
    try:
        os.symlink(identity, temporary, target_is_directory=True)
        os.replace(temporary, current)
    finally:
        temporary.unlink(missing_ok=True)
    return previous
