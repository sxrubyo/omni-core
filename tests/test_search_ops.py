import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from search_ops import brave_search, summarize_brave_results  # noqa: E402


class SearchOpsTests(unittest.TestCase):
    def test_summarize_brave_results_flattens_titles_urls_and_descriptions(self) -> None:
        lines = summarize_brave_results(
            {
                "web": {
                    "results": [
                        {
                            "title": "Ubuntu OpenSSH",
                            "url": "https://example.com/ubuntu-ssh",
                            "description": "How to enable password auth safely.",
                        }
                    ]
                }
            }
        )
        self.assertIn("Ubuntu OpenSSH", lines)
        self.assertIn("https://example.com/ubuntu-ssh", lines)
        self.assertIn("How to enable password auth safely.", lines)

    def test_brave_search_sends_expected_headers(self) -> None:
        payload = json.dumps({"web": {"results": []}}).encode("utf-8")

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return payload

        with mock.patch("search_ops.urllib.request.urlopen", return_value=FakeResponse()) as urlopen_mock:
            result = brave_search("ubuntu ssh", "brave-secret")

        self.assertEqual(result["status"], 200)
        request = urlopen_mock.call_args.args[0]
        self.assertIn("q=ubuntu%20ssh", request.full_url)
        self.assertEqual(request.headers["X-subscription-token"], "brave-secret")


if __name__ == "__main__":
    unittest.main()
