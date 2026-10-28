"""Optional end-to-end package fixture smoke; all inference and delivery are mocked."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


FIXTURE_ID = "offline-installed-fixture-v1"
FIXTURE_QUESTION = {
    "type": "choice",
    "instructions": "Offline installed-package fixture only.",
    "criteria": {"yes": "Controlled YES", "no": "Controlled NO"},
}
FIXTURE_BYTES = json.dumps(FIXTURE_QUESTION, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()


def _available():
    if importlib.util.find_spec("build") is None or importlib.util.find_spec("pip") is None:
        return False
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--help"],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and "--python" in result.stdout


def _run(command, *, cwd, env=None):
    # Keep installed resources at the documented 0755 directory mode in this smoke.
    result = subprocess.run(["/bin/sh", "-c", 'umask 022; exec "$@"', "package-smoke",
                             *map(str, command)], cwd=cwd, env=env,
                            capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"Command failed ({result.returncode}): {command}\n{result.stdout}\n{result.stderr}")
    return result.stdout


@unittest.skipUnless(_available(), "package/build/pip --python support is not available")
class InstalledPromptPackageTests(unittest.TestCase):
    def test_wheel_and_sdist_fixture_activate_outside_source_without_sending(self):
        repo = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix="clef-installed-package-") as temporary:
            root = Path(temporary)
            source = root / "staged-source"
            shutil.copytree(repo, source, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "dist", "build", "*.egg-info", ".venv"))
            manifest = source / "prompts" / "clef" / "manifest.json"
            manifest.write_text(json.dumps({"version": 2, "resources": [
                {"id": FIXTURE_ID, "sha256": FIXTURE_SHA256}]}), encoding="utf-8")
            artifact = source / "prompts" / "clef" / f"{FIXTURE_ID}.json"
            artifact.write_bytes(FIXTURE_BYTES)
            manifest.chmod(0o644)
            artifact.chmod(0o644)
            pyproject = source / "pyproject.toml"
            contents = pyproject.read_text(encoding="utf-8")
            old = '"share/telegram-alerts/prompts/clef" = ["prompts/clef/manifest.json"]'
            new = (f'"share/telegram-alerts/prompts/clef" = '
                   f'["prompts/clef/manifest.json", "prompts/clef/{FIXTURE_ID}.json"]')
            self.assertEqual(contents.count(old), 1)
            pyproject.write_text(contents.replace(old, new), encoding="utf-8")

            dist = root / "dist"
            dist.mkdir()
            _run([sys.executable, "-m", "build", "--no-isolation", "--wheel", "--sdist",
                  "--outdir", dist, source], cwd=source)
            wheel = next(dist.glob("*.whl"))
            sdist = next(dist.glob("*.tar.gz"))
            with zipfile.ZipFile(wheel) as package:
                names = package.namelist()
                self.assertTrue(any(name.endswith(
                    f"share/telegram-alerts/prompts/clef/{FIXTURE_ID}.json") for name in names))
                self.assertTrue(any(name.endswith(
                    "share/telegram-alerts/prompts/clef/manifest.json") for name in names))
            unpacked = root / "sdist-source"
            unpacked.mkdir()
            with tarfile.open(sdist) as package:
                members = package.getnames()
                self.assertTrue(any(name.endswith(f"prompts/clef/{FIXTURE_ID}.json") for name in members))
                self.assertTrue(any(name.endswith("prompts/clef/manifest.json") for name in members))
                if sys.version_info >= (3, 12):
                    package.extractall(unpacked, filter="data")
                else:
                    package.extractall(unpacked)
            sdist_root = next(path for path in unpacked.iterdir() if path.is_dir())
            sdist_dist = root / "sdist-wheel"
            sdist_dist.mkdir()
            _run([sys.executable, "-m", "build", "--no-isolation", "--wheel",
                  "--outdir", sdist_dist, sdist_root], cwd=sdist_root)

            elsewhere = root / "unrelated-cwd"
            elsewhere.mkdir()
            artifacts = (("wheel", wheel), ("sdist-wheel", next(sdist_dist.glob("*.whl"))))
            for label, package in artifacts:
                with self.subTest(package=label):
                    venv = root / f"venv-{label}"
                    _run([sys.executable, "-m", "venv", "--without-pip", venv], cwd=elsewhere)
                    _run([sys.executable, "-m", "pip", "--python", venv / "bin" / "python",
                          "install", "--no-index", "--no-deps", package], cwd=elsewhere)
                    home = root / f"home-{label}"
                    home.mkdir(mode=0o700)
                    key = root / f"key-{label}"
                    key.write_text("synthetic-installed-fixture-key", encoding="utf-8")
                    key.chmod(0o600)
                    environment = {name: value for name, value in os.environ.items()
                                   if name not in ("PYTHONPATH", "PYTHONHOME")}
                    environment["TELEGRAM_ALERTS_HOME"] = str(home)
                    cli = venv / "bin" / "telegram-alerts"
                    configured = json.loads(_run([
                        cli, "clef", "configure", "--endpoint", "https://clef.example.invalid",
                        "--key-file", key, "--model", "offline-package",
                        "--expected-model", "offline-response", "--prompt-resource", FIXTURE_ID,
                    ], cwd=elsewhere, env=environment))
                    self.assertTrue(configured["update_route_ready"])
                    self.assertEqual(configured["prompt_id"], FIXTURE_ID)
                    self.assertEqual(configured["prompt_hash"], FIXTURE_SHA256)
                    status = json.loads(_run([cli, "clef", "status"], cwd=elsewhere, env=environment))
                    self.assertTrue(status["update_route_ready"])

                    smoke = r'''import json, pathlib, sys
from io import StringIO
from unittest.mock import patch
import alert_selector as selector
import telegram_alerts as app
assert pathlib.Path(selector.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve())
question = {"type":"choice","instructions":"Offline installed-package fixture only.","criteria":{"yes":"Controlled YES","no":"Controlled NO"}}
def fake_request(config, payload, key):
    assert payload["questions"]["publish"] == question
    return {"model":config["expected_model"],"usage":{"input_tokens":10,"output_tokens":0},
            "answers":{"publish":{"type":"choice","choice":"no","probabilities":{"yes":0.1,"no":0.9},"confidence":0.9}}}
with patch.object(app,"credentials",return_value=("synthetic-token","synthetic-chat")), \
     patch.object(selector,"_request",side_effect=fake_request), \
     patch.object(app,"api",side_effect=AssertionError("Telegram must not be called")), \
     patch.object(app.sys,"argv",["telegram-alerts","update","--key","installed-package:fixture:v1"]), \
     patch.object(app.sys,"stdin",StringIO(json.dumps({"summary":"Offline installed fixture smoke."}))), \
     patch.object(app.sys,"stdout",StringIO()) as output:
    code = app.cli()
receipt = json.loads(output.getvalue())
assert code == 0 and receipt["state"] == "suppressed" and receipt["reason"] == "clef_no"
assert receipt["prompt_id"] == "offline-installed-fixture-v1"
'''
                    _run([venv / "bin" / "python", "-c", smoke], cwd=elsewhere, env=environment)


if __name__ == "__main__":
    unittest.main()
