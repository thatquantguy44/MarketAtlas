import contextlib
import io
import json
import unittest

from market_atlas.cli import main


class CliTests(unittest.TestCase):
    def test_fixture_inspect_exercises_the_documented_cutoff_workflow(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(
                ["fixture", "inspect", "--knowledge-cutoff", "2024-02-10T00:00:00Z"]
            )
        self.assertEqual(0, status)
        view = json.loads(output.getvalue())
        self.assertEqual("2024-02-10T00:00:00Z", view["knowledge_cutoff"])
        self.assertTrue(view["synthetic"])


if __name__ == "__main__":
    unittest.main()
