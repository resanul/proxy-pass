from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ProjectPackageTests(unittest.TestCase):
    def test_python_source_compiles(self):
        source = ROOT / "src" / "proxypilot.py"
        compile(source.read_text(encoding="utf-8"), str(source), "exec")

    def test_required_release_files_exist(self):
        for path in (
            "README.md",
            "build.bat",
            "requirements.txt",
            "version_info.txt",
            "installer/ProxyPilot.iss",
            ".github/workflows/windows-release.yml",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

    def test_version_is_declared(self):
        source = (ROOT / "src" / "proxypilot.py").read_text(encoding="utf-8")
        self.assertIn('VERSION = "1.1.0"', source)

if __name__ == "__main__":
    unittest.main()
