"""Wire-level curl_cffi regression test using a local server, never Sofascore."""
import json
import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from scouting import sofascore_recovery as r


def check_headers_on_wire():
    class Echo(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(dict(self.headers)).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = HTTPServer(('127.0.0.1', 0), Echo)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = r.HttpTransport()
    try:
        response = client._request(f'http://127.0.0.1:{server.server_port}/')
        headers = {k.lower(): v for k, v in json.loads(response['body']).items()}
        assert response['status'] == 200
        assert 'Chrome/150.' in headers['user-agent']
        assert '"150"' in headers['sec-ch-ua']
        assert ('Macintosh' in headers['user-agent']) == (headers['sec-ch-ua-platform'] == '"macOS"')
        assert headers['sec-fetch-mode'] == 'cors'
        assert headers['sec-fetch-dest'] == 'empty'
        assert headers['sec-fetch-site'] == 'same-origin'
        assert 'sec-fetch-user' not in headers
        assert 'x-requested-with' not in headers
        assert 'cookie' not in headers
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@unittest.skipUnless(importlib.util.find_spec('curl_cffi'), 'curl_cffi is installed in the worker image')
class HeaderWireTest(unittest.TestCase):
    def test_curl_profile_and_api_headers_are_consistent_on_wire(self):
        check_headers_on_wire()


if __name__ == '__main__':
    unittest.main()
