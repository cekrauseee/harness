"""Packaging, generated-file isolation and discoverable metadata contracts."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DistributionTest(unittest.TestCase):
    def test_generation_is_selective_idempotent_and_preserves_authored_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for folder in ('src', 'scripts', 'docs', 'skills/example/scripts/assets', 'skills/plain'):
                (root / folder).mkdir(parents=True)
            for file in ('src/harness.py', 'scripts/build_dist.py', 'docs/file-context.md'):
                shutil.copyfile(ROOT / file, root / file)
            skill = root / 'skills/example'
            (skill / 'SKILL.md').write_text('Use scripts/harness.py and references/file-context.md\n')
            (root / 'skills/plain/SKILL.md').write_text('Instruction-only skill\n')
            authored = skill / 'scripts/custom.py'
            authored.write_text("print('keep')\n")
            generated = skill / 'scripts/harness.py'

            def run(*args):
                return subprocess.run([sys.executable, '-B', str(root / 'scripts/build_dist.py'), *args],
                                      capture_output=True, text=True, timeout=20)

            self.assertEqual(run('--check').returncode, 1)
            self.assertFalse(generated.exists())
            self.assertEqual(run().returncode, 0)
            self.assertEqual(generated.read_bytes(), (root / 'src/harness.py').read_bytes())
            self.assertEqual((skill / 'references/file-context.md').read_bytes(), (root / 'docs/file-context.md').read_bytes())
            modified = generated.stat().st_mtime_ns
            self.assertEqual(run().returncode, 0)
            self.assertEqual(generated.stat().st_mtime_ns, modified)
            self.assertEqual(run('--check').returncode, 0)
            generated.write_text('outdated')
            self.assertEqual(run('--check').returncode, 1)
            self.assertEqual(authored.read_text(), "print('keep')\n")
            self.assertFalse((root / 'skills/plain/scripts').exists())

    def test_manifest_inventory_and_versions_align(self):
        codex = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())
        claude = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        names = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}
        self.assertEqual(codex['name'], 'harness')
        self.assertEqual(claude['name'], codex['name'])
        self.assertEqual(claude['version'], codex['version'])
        source = ast.parse((ROOT / 'src/harness.py').read_text())
        version = next(ast.literal_eval(n.value) for n in source.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in n.targets))
        self.assertEqual(version, codex['version'].split('+')[0])
        self.assertEqual({Path(p).name for p in claude['skills']}, names)
        self.assertEqual(len(names), 16)
        self.assertEqual(codex['skills'], './skills/')
        self.assertTrue(all(n.startswith(('environment-', 'workflows-')) for n in names))

    def test_skill_metadata_and_local_links_resolve_within_installed_skill(self):
        for entry in sorted((ROOT / 'skills').glob('*/SKILL.md')):
            with self.subTest(skill=entry.parent.name):
                content = entry.read_text()
                self.assertTrue(content.startswith('---\n'))
                frontmatter = content.split('---', 2)[1]
                name = re.search(r'^name: (.+)$', frontmatter, re.M).group(1)
                self.assertEqual(name, entry.parent.name)
                self.assertRegex(frontmatter, r'(?m)^description: .+')
                self.assertTrue((entry.parent / 'agents/openai.yaml').is_file())
                for path in entry.parent.rglob('*.md'):
                    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
                        if '://' in target or target.startswith('#'):
                            continue
                        resolved = (path.parent / target.split('#')[0]).resolve()
                        self.assertTrue(resolved.is_relative_to(entry.parent), target)
                        self.assertTrue(resolved.exists(), f'{path}: {target}')

    def test_generated_content_has_no_drift(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/build_dist.py'), '--check'],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bundled_imports_use_standard_library(self):
        source = ast.parse((ROOT / 'src/harness.py').read_text())
        modules = set()
        for node in ast.walk(source):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split('.')[0])
        stdlib = Path(sysconfig.get_path('stdlib')).resolve()
        for module in modules:
            spec = importlib.util.find_spec(module)
            self.assertIsNotNone(spec, module)
            if spec.origin not in {'built-in', 'frozen'}:
                path = Path(spec.origin).resolve()
                self.assertTrue(path.is_relative_to(stdlib), module)
                self.assertFalse({'site-packages', 'dist-packages'} & set(path.parts), module)
