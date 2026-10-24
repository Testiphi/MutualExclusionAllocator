from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from data_tools import ROOT
from release_tools import FILES, pack, stage, verify, activate


class ReleaseTests(unittest.TestCase):
    def fixture(self, directory, change=False):
        source = directory / ('source2' if change else 'source')
        source.mkdir()
        for name in FILES:
            (source / name).write_text(name + (' new' if change else ''), encoding='utf-8')
        return source

    def test_full_package_stage_and_repeat_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = self.fixture(directory)
            info = pack(source, directory / 'release.zip')
            target = stage(directory / 'release.zip', directory / 'versions')
            self.assertEqual(verify(target), info)
            self.assertEqual(stage(directory / 'release.zip', directory / 'versions'), target)
            self.assertFalse((directory / 'versions/current').exists())
            with self.assertRaises(ValueError):
                pack(source, directory / 'release.zip')

    def test_checksum_corruption_and_extra_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pack(self.fixture(directory), directory / 'release.zip')
            with zipfile.ZipFile(directory / 'release.zip') as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            for mode in ('corrupt', 'extra'):
                bad = dict(files)
                if mode == 'corrupt':
                    bad['index.html'] = b'corrupted'
                else:
                    bad['../escape'] = b'bad'
                with zipfile.ZipFile(directory / 'bad.zip', 'w') as archive:
                    for name, content in bad.items():
                        archive.writestr(name, content)
                with self.assertRaises(ValueError):
                    stage(directory / 'bad.zip', directory / 'versions')
            self.assertFalse((directory / 'versions').exists())

    def test_changed_staged_files_cannot_be_activated(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pack(self.fixture(directory), directory / 'release.zip')
            target = stage(directory / 'release.zip', directory / 'versions')
            (target / 'index.html').write_text('corrupted')
            with patch('release_tools.os.symlink') as link:
                with self.assertRaises(ValueError):
                    activate(directory / 'versions', target.name)
                link.assert_not_called()

    def test_activation_verifies_before_replacing_current(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pack(self.fixture(directory), directory / 'release.zip')
            target = stage(directory / 'release.zip', directory / 'versions')
            with patch('release_tools.os.symlink') as link, patch('release_tools.os.replace') as replace:
                self.assertIsNone(activate(directory / 'versions', target.name))
                link.assert_called_once()
                replace.assert_called_once()
                self.assertEqual(replace.call_args.args[1], (directory / 'versions/current').resolve())

    @unittest.skipIf(os.name == 'nt', 'Linux服务器的真实目录链接切换，Windows测试仅验证接线')
    def test_real_switch_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pack(self.fixture(directory), directory / 'one.zip')
            one = stage(directory / 'one.zip', directory / 'versions')
            pack(self.fixture(directory, True), directory / 'two.zip')
            two = stage(directory / 'two.zip', directory / 'versions')
            activate(directory / 'versions', one.name)
            self.assertEqual(activate(directory / 'versions', two.name), one.name)
            self.assertEqual((directory / 'versions/current').resolve(), two)
            activate(directory / 'versions', one.name)
            self.assertEqual((directory / 'versions/current').resolve(), one)

    def test_actual_source_cli_package_and_stage_only(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            build = subprocess.run([sys.executable, '-B', str(ROOT / 'build_release.py'),
                                    '--output', str(directory / 'release.zip')], capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            deploy = subprocess.run([sys.executable, '-B', str(ROOT / 'deploy_release.py'),
                                     '--bundle', str(directory / 'release.zip'), '--base', str(directory / 'versions')],
                                    capture_output=True)
            self.assertEqual(deploy.returncode, 0, deploy.stderr)
            self.assertFalse((directory / 'versions/current').exists())


if __name__ == '__main__':
    unittest.main()
