import http.server
import importlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def load(home, host="127.0.0.1:1"):
    os.environ["POLTERGEIST_HOME"] = home
    os.environ["OLLAMA_HOST"] = host
    os.environ["POLTERGEIST_TIMEOUT"] = "2"
    import poltergeist
    return importlib.reload(poltergeist)


class Stub(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.seen.append(body)
        out = json.dumps({"message": {"content": '"The candles shiver." Extra. Sentences. Here.'}}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pg = load(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_falls_back_to_omens_without_a_model(self):
        msg = self.pg.whisper("rm -rf build", 0, always=True)
        self.assertIn(msg, self.pg.OMENS["rm"])
        self.assertIn(self.pg.whisper("make", 2, always=True), self.pg.FAILED)

    def test_secrets_are_never_recorded(self):
        self.assertFalse(self.pg.record("export API_KEY=abc"))
        self.assertFalse(self.pg.record("curl -H 'Authorization: x' host"))
        self.assertTrue(self.pg.record("ls"))
        self.assertEqual([h["cmd"] for h in self.pg.load()], ["ls"])

    def test_refuses_remote_model_hosts(self):
        pg = load(self.tmp.name, "http://example.com:11434")
        self.assertIn("refusing non-local", pg.whisper("ls", 0, always=True))

    def test_talks_to_ollama_and_trims_reply(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        pg = load(self.tmp.name, f"127.0.0.1:{srv.server_port}")
        pg.record("git push")
        msg = pg.whisper("git push", 0, always=True)
        srv.shutdown()
        self.assertEqual(msg, "The candles shiver. Extra.")
        sent = Stub.seen[-1]
        self.assertIn("Times seen before: 1", sent["messages"][1]["content"])
        self.assertEqual(sent["stream"], False)

    def test_ofrenda_lists_only_long_silent_favourites(self):
        day = 86400
        now = time.time()
        hist = [{"t": now - 90 * day, "cmd": "svn up", "status": 0}] * 4
        hist += [{"t": now - 2 * day, "cmd": "git status", "status": 0}] * 5
        hist += [{"t": now - 90 * day, "cmd": "once", "status": 0}]
        got = self.pg.ofrenda(30, 3, history=hist)
        self.assertEqual([k for k, _ in got], ["svn"])
        self.assertIn("svn up", self.pg.render_ofrenda(got, 30))

    def test_hook_snippets_render(self):
        for sh in ("bash", "zsh"):
            self.assertIn("poltergeist.py", self.pg.haunt(sh))
            self.assertNotIn("%(py)s", self.pg.haunt(sh))


if __name__ == "__main__":
    unittest.main()
