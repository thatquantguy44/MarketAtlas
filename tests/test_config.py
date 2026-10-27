import tempfile
import unittest
from pathlib import Path

from market_atlas.config import (
    ConfigError,
    load_macro_context,
    load_macro_medallion,
    load_source_database,
    load_target_database,
    load_upstream_asset,
)


class ConfigTests(unittest.TestCase):
    def test_loads_source_database_and_redacts_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.toml"
            path.write_text(
                """[source_database]
host = "localhost"
port = 55432
database = "example"
username = "reader"
password = "secret"
read_only = true
""",
                encoding="utf-8",
            )
            config = load_source_database(path)
            self.assertEqual("secret", config.connection_kwargs()["password"])
            self.assertEqual("<redacted>", config.public_summary()["password"])

    def test_rejects_write_enabled_source_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.toml"
            path.write_text(
                """[source_database]
host = "localhost"
port = 55432
database = "example"
username = "reader"
password = "secret"
read_only = false
""",
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_source_database(path)

    def test_loads_bounded_macro_medallion_pilot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.toml"
            path.write_text(
                """[macro_medallion]
series_ids = ["GDP", "UNRATE"]
observation_start = "2024-01-01"
observation_end = "2024-12-31"
knowledge_cutoff = "2025-01-31"
redistribution_status = "unresolved"
""",
                encoding="utf-8",
            )
            config = load_macro_medallion(path)
            self.assertEqual(("GDP", "UNRATE"), config.series_ids)

    def test_loads_bounded_macro_context_pilot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "context.toml"
            path.write_text(
                """[macro_context]
series_ids = ["GDP", "UNRATE"]
release_start = "2026-10-01"
release_end = "2026-12-31"
redistribution_status = "unresolved"
""",
                encoding="utf-8",
            )
            config = load_macro_context(path)
            self.assertEqual(("GDP", "UNRATE"), config.series_ids)
            self.assertEqual("2026-12-31", config.release_end)

    def test_loads_separate_target_database_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.toml"
            path.write_text(
                """[target_database]
host = "localhost"
port = 55432
database = "example"
username = "writer"
password = "secret"
role = "marketatlas_writer"
""",
                encoding="utf-8",
            )
            config = load_target_database(path)
            self.assertEqual("marketatlas_writer", config.role)

    def test_loads_optional_local_upstream_asset_without_exposing_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "local.toml"
            config_path.write_text(
                f'[upstream_asset]\nlocal_repository_path = "{root}"\n',
                encoding="utf-8",
            )
            config = load_upstream_asset(config_path)
            self.assertEqual(root, config.local_repository_path)
            self.assertEqual(
                {"local_repository_configured": True}, config.public_summary()
            )


if __name__ == "__main__":
    unittest.main()
