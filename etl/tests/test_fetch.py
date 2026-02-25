import json
import unittest
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dwarfboard_etl.fetch import fetch_snapshot


class _FakeResponse:
    def __init__(self, body: bytes, status: int, content_type: str) -> None:
        self._body = body
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["ETag"] = '"abc123"'
        self.headers["Last-Modified"] = "Wed, 25 Feb 2026 18:00:00 GMT"

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FetchTests(unittest.TestCase):
    @patch("dwarfboard_etl.fetch.urlopen")
    def test_fetch_snapshot_writes_body_metadata_and_latest(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = _FakeResponse(
            body=b"rank,team\n1,foo\n",
            status=200,
            content_type="text/csv",
        )

        with TemporaryDirectory() as tmp:
            result = fetch_snapshot("https://example.com/lb.csv", Path(tmp))
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.body_path.exists())
            self.assertTrue(result.metadata_path.exists())

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["url"], "https://example.com/lb.csv")
            self.assertEqual(metadata["status_code"], 200)
            self.assertEqual(metadata["content_type"], "text/csv")

            latest = json.loads((Path(tmp) / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["sha256"], metadata["sha256"])
            self.assertEqual(latest["body_file"], metadata["body_file"])


if __name__ == "__main__":
    unittest.main()
