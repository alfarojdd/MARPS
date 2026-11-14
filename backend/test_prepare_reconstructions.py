"""Fresh-clone metadata and download integrity, without using the network."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prepare_reconstructions import download, prepare
from reconstructions import BUNDLED_DATASET, build_catalog


class ReconstructionInstallTests(unittest.TestCase):
    def test_fresh_clone_retains_every_entry_and_anchor_without_binaries(self):
        # Copy tracked metadata only, even if binaries have already been downloaded locally.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            with patch("prepare_reconstructions.MANIFEST") as manifest:
                manifest.read_text.return_value = "[]"
                prepare(path)
            catalog = build_catalog(path)
            self.assertEqual(catalog["counts"], dict(total=244, placed=94, local=2))
            local = [s for s in catalog["scenes"] if s["renderer"] != "sketchfab"]
            self.assertTrue(all(not s["available"] for s in local))
            self.assertTrue(any("prepare_reconstructions.py" in s for s in catalog["warnings"]))
            self.assertEqual(local[1]["coordinates"], [77.444311622, 18.430825802])

    def test_check_is_offline_and_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "absent"
            with patch("prepare_reconstructions.urlopen") as network:
                with self.assertRaisesRegex(ValueError, "Files are missing"):
                    prepare(path, check=True)
                network.assert_not_called()
            self.assertFalse(path.exists())

    def test_failed_integrity_keeps_previous_file_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.spz"
            path.write_bytes(b"old")
            item = dict(path="model.spz", url="https://example.invalid/model", bytes=4,
                        sha256=hashlib.sha256(b"good").hexdigest())
            with patch("prepare_reconstructions.urlopen", return_value=io.BytesIO(b"bad!")):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    download(item, path)
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(list(path.parent.glob("*.download")), [])
            with patch("prepare_reconstructions.urlopen", return_value=io.BytesIO(b"good")):
                download(item, path)
            self.assertEqual(path.read_bytes(), b"good")


if __name__ == "__main__":
    unittest.main()
