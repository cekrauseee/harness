"""Generated helpers stay current without deleting authored skill resources."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class DistributionTest(unittest.TestCase):
    def test_generation_preserves_resources_and_checks_drift(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for folder in ("src", "scripts", "skills/example/scripts/assets"):
                (root / folder).mkdir(parents=True)
            for file in ("src/continuity.py", "scripts/build_dist.py"):
                shutil.copyfile(source / file, root / file)
            skill = root / "skills/example"
            (skill / "SKILL.md").write_text("---\nname: example\n---\n")
            authored = skill / "scripts/custom.py"
            authored.write_text("print('keep this source')\n")
            generated = skill / "scripts/continuity.py"

            def run(*args):
                return subprocess.run([sys.executable, "-B", str(root / "scripts/build_dist.py"), *args],
                                      cwd=root, capture_output=True, text=True, timeout=20)

            self.assertEqual(run("--check").returncode, 1)
            self.assertFalse(generated.exists())
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(generated.read_bytes(), (root / "src/continuity.py").read_bytes())
            modified = generated.stat().st_mtime_ns
            self.assertEqual(run().returncode, 0)
            self.assertEqual(generated.stat().st_mtime_ns, modified)
            self.assertEqual(run("--check").returncode, 0)
            generated.write_text("outdated")
            self.assertEqual(run("--check").returncode, 1)
            self.assertEqual(authored.read_text(), "print('keep this source')\n")
            self.assertTrue((skill / "scripts/assets").is_dir())
