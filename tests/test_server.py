from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from almadar_fabric.server import Handler


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        status, payload = response.status, response.read()
        connection.close()
        return status, payload

    def test_browser_assets_and_api(self):
        for path in ["/", "/style.css", "/app.js", "/almadar-logo.png", "/api/scenarios"]:
            self.assertEqual(self.request("GET", path)[0], 200)
        status, payload = self.request(
            "POST",
            "/api/run",
            '{"scenario":"transport-fault"}',
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["status"], "restored")

    def test_invalid_input_is_rejected(self):
        for payload in [
            '{"scenario":"not-real"}',
            "[]",
            '{"incident":null}',
            "{",
            '{"extra":true}',
        ]:
            self.assertEqual(
                self.request(
                    "POST", "/api/run", payload, {"Content-Type": "application/json"}
                )[0],
                400,
            )

    def test_cross_origin_is_rejected(self):
        self.assertEqual(
            self.request(
                "POST",
                "/api/run",
                "{}",
                {"Content-Type": "application/json", "Origin": "https://example.com"},
            )[0],
            403,
        )

    def test_source_and_path_traversal_are_not_served(self):
        for path in ["/runtime.py", "/../README.md", "/%2e%2e/README.md"]:
            self.assertEqual(self.request("GET", path)[0], 404)


if __name__ == "__main__":
    unittest.main()
