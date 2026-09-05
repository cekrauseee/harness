from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from harness_runtime import integration
from harness_runtime.core import HarnessError


class HostIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'state'
        self.file = self.root / 'host' / 'AGENTS.md'
        self.runtime = self.root / 'installed skill' / 'scripts' / 'harness.py'
        self.runtime.parent.mkdir(parents=True)
        self.runtime.write_text('# fixture runtime\n')
        self.data = {'file': str(self.file), 'runtime': str(self.runtime)}

    def call(self, op, **data):
        return integration.execute('integration.' + op, self.data | data, self.home)

    def test_preview_install_reinstall_remove_preserve_user_bytes(self):
        self.file.parent.mkdir()
        original = 'My preferences: café; no trailing newline'.encode()
        self.file.write_bytes(original)
        preview = self.call('preview')
        self.assertEqual(self.file.read_bytes(), original)
        self.assertFalse(self.home.exists())
        result = self.call('install', expected_sha256=preview['expected_sha256'])
        self.assertTrue(result['changed'])
        self.assertEqual(self.call('status')['runtime'], str(self.runtime.resolve()))
        current = self.file.read_bytes()
        self.assertFalse(self.call('install', expected_sha256=result['sha256'])['changed'])
        self.assertEqual(current, self.file.read_bytes())
        self.call('remove', expected_sha256=result['sha256'])
        self.assertEqual(original, self.file.read_bytes())
        self.assertFalse(self.call('remove', expected_sha256=hashlib.sha256(original).hexdigest())['changed'])

    def test_edits_and_races_are_rejected(self):
        preview = self.call('preview')
        self.file.parent.mkdir()
        self.file.write_text('New user preference\n')
        with self.assertRaises(HarnessError) as conflict:
            self.call('install', expected_sha256=preview['expected_sha256'])
        self.assertEqual(conflict.exception.code, 'instructions_changed')
        result = self.call('install', expected_sha256=self.call('preview')['expected_sha256'])
        self.file.write_text(self.file.read_text().replace('generic question', 'user question'))
        edited = self.file.read_bytes()
        for op in ('install', 'remove', 'status'):
            with self.assertRaises(HarnessError):
                self.call(op, expected_sha256=result['sha256'])
        self.assertEqual(self.file.read_bytes(), edited)

    def test_duplicate_and_symlink_rejected_and_missing_runtime_visible(self):
        block = integration.rule(self.runtime)
        self.file.parent.mkdir()
        self.file.write_text(block + block)
        with self.assertRaises(HarnessError):
            self.call('preview')
        self.file.write_text(block)
        self.runtime.unlink()
        self.assertFalse(self.call('status')['runtime_available'])
        with self.assertRaises(HarnessError):
            self.call('preview')
        link = self.root / 'instructions-link'
        link.symlink_to(self.file)
        with self.assertRaises(HarnessError):
            self.call('status', file=str(link))

    def test_file_mode_preserved(self):
        self.file.parent.mkdir()
        self.file.write_text('Preferences\n')
        self.file.chmod(0o640)
        self.call('install', expected_sha256=self.call('preview')['expected_sha256'])
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o640)


if __name__ == '__main__':
    unittest.main()
