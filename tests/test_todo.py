import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import todo  # noqa: E402


class RmCommandTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "todos.json")
        patcher = mock.patch.dict(os.environ, {"TODO_FILE": self.path})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmpdir.cleanup)

    def run_cli(self, *argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = todo.main(list(argv))
        return code, stdout.getvalue(), stderr.getvalue()

    def read_data(self):
        with open(self.path, encoding="utf-8") as file:
            return json.load(file)

    def test_rm_existing_id(self):
        self.run_cli("add", "牛乳を買う")
        self.run_cli("add", "本を返す")

        code, out, err = self.run_cli("rm", "1")

        self.assertEqual(code, 0)
        self.assertEqual(out, "Removed #1: 牛乳を買う\n")
        self.assertEqual(err, "")
        data = self.read_data()
        self.assertEqual([item["id"] for item in data["items"]], [2])
        self.assertEqual(data["next_id"], 3)

    def test_rm_done_item(self):
        self.run_cli("add", "牛乳を買う")
        self.run_cli("done", "1")

        code, out, _ = self.run_cli("rm", "1")

        self.assertEqual(code, 0)
        self.assertEqual(out, "Removed #1: 牛乳を買う\n")
        self.assertEqual(self.read_data()["items"], [])

    def test_rm_missing_id(self):
        self.run_cli("add", "牛乳を買う")
        with open(self.path, "rb") as file:
            before = file.read()

        for missing in ("99", "0", "-1"):
            with self.subTest(id=missing):
                code, out, err = self.run_cli("rm", missing)
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertEqual(err, "Error: todo #{} not found\n".format(missing))
                with open(self.path, "rb") as file:
                    self.assertEqual(file.read(), before)

    def test_rm_does_not_reuse_id(self):
        self.run_cli("add", "牛乳を買う")
        self.run_cli("add", "本を返す")
        self.run_cli("rm", "2")

        code, out, _ = self.run_cli("add", "掃除する")

        self.assertEqual(code, 0)
        self.assertEqual(out, "Added #3: 掃除する\n")
        data = self.read_data()
        self.assertEqual([item["id"] for item in data["items"]], [1, 3])
        self.assertEqual(data["next_id"], 4)

    def test_rm_removed_id_twice(self):
        self.run_cli("add", "牛乳を買う")
        self.run_cli("rm", "1")

        code, _, err = self.run_cli("rm", "1")

        self.assertEqual(code, 1)
        self.assertEqual(err, "Error: todo #1 not found\n")


if __name__ == "__main__":
    unittest.main()
