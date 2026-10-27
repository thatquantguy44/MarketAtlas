"""Local configuration loading with secret-safe diagnostics."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("configs/local.toml")


class ConfigError(ValueError):
    """Raised when local configuration is missing or invalid."""


@dataclass(frozen=True)
class UpstreamAssetConfig:
    """Optional local checkout for the MacroMedallion/EcoMedallion upstream asset."""

    local_repository_path: Path | None

    def public_summary(self) -> dict[str, object]:
        """Expose whether a local checkout was selected without disclosing its path."""
        return {"local_repository_configured": self.local_repository_path is not None}


def load_upstream_asset(path: Path = DEFAULT_CONFIG_PATH) -> UpstreamAssetConfig:
    """Load an optional local upstream checkout; no remote identity is required."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read configuration at {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML configuration at {path}: {error}") from error

    section = document.get("upstream_asset", {})
    if not isinstance(section, dict):
        raise ConfigError("upstream_asset must be a table when configured")
    configured_path = section.get("local_repository_path")
    if configured_path in (None, ""):
        return UpstreamAssetConfig(local_repository_path=None)
    if not isinstance(configured_path, str):
        raise ConfigError("upstream_asset.local_repository_path must be a string")
    repository_path = Path(configured_path).expanduser()
    if not repository_path.is_absolute():
        raise ConfigError("upstream_asset.local_repository_path must be absolute")
    if not repository_path.is_dir():
        raise ConfigError(
            "upstream_asset.local_repository_path must name an existing directory"
        )
    return UpstreamAssetConfig(local_repository_path=repository_path)


@dataclass(frozen=True)
class SourceDatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    read_only: bool = True
    role: str | None = None

    def connection_kwargs(self) -> dict[str, object]:
        """Return psycopg keyword arguments without creating a printable DSN."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.username,
            "password": self.password,
            "application_name": "marketatlas-source-discovery",
            "connect_timeout": 5,
            "options": "-c default_transaction_read_only=on -c statement_timeout=30000",
        }

    def public_summary(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": "<redacted>",
            "read_only": self.read_only,
            "role": self.role,
        }


def load_source_database(path: Path = DEFAULT_CONFIG_PATH) -> SourceDatabaseConfig:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read configuration at {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML configuration at {path}: {error}") from error

    section = document.get("source_database")
    if not isinstance(section, dict):
        raise ConfigError("configuration requires a [source_database] table")

    required = ("host", "port", "database", "username", "password")
    missing = [key for key in required if section.get(key) in (None, "")]
    if missing:
        raise ConfigError(
            f"source_database is missing required fields: {', '.join(missing)}"
        )
    if not isinstance(section["port"], int) or not 1 <= section["port"] <= 65535:
        raise ConfigError("source_database.port must be an integer from 1 to 65535")
    if section.get("read_only", True) is not True:
        raise ConfigError("source_database.read_only must be true for source access")

    return SourceDatabaseConfig(
        host=str(section["host"]),
        port=section["port"],
        database=str(section["database"]),
        username=str(section["username"]),
        password=str(section["password"]),
        read_only=True,
        role=str(section["role"]) if section.get("role") else None,
    )


@dataclass(frozen=True)
class TargetDatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    role: str = "marketatlas_writer"

    def connection_kwargs(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.username,
            "password": self.password,
            "application_name": "marketatlas-migrations",
            "connect_timeout": 5,
            "options": "-c statement_timeout=30000 -c lock_timeout=5000",
        }


def load_target_database(path: Path = DEFAULT_CONFIG_PATH) -> TargetDatabaseConfig:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read configuration at {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML configuration at {path}: {error}") from error

    section = document.get("target_database")
    if not isinstance(section, dict):
        raise ConfigError("configuration requires a [target_database] table")
    required = ("host", "port", "database", "username", "password")
    missing = [key for key in required if section.get(key) in (None, "")]
    if missing:
        raise ConfigError(
            f"target_database is missing required fields: {', '.join(missing)}"
        )
    if not isinstance(section["port"], int) or not 1 <= section["port"] <= 65535:
        raise ConfigError("target_database.port must be an integer from 1 to 65535")
    role = section.get("role", "marketatlas_writer")
    if role != "marketatlas_writer":
        raise ConfigError("target_database.role must be marketatlas_writer")
    return TargetDatabaseConfig(
        host=str(section["host"]),
        port=section["port"],
        database=str(section["database"]),
        username=str(section["username"]),
        password=str(section["password"]),
        role=role,
    )


@dataclass(frozen=True)
class MacroMedallionConfig:
    series_ids: tuple[str, ...]
    observation_start: str
    observation_end: str
    knowledge_cutoff: str
    redistribution_status: str


@dataclass(frozen=True)
class MacroContextConfig:
    """Bounded selection for current macro taxonomy, releases, and coverage."""

    series_ids: tuple[str, ...]
    release_start: str
    release_end: str
    redistribution_status: str


def load_macro_medallion(
    path: Path = Path("configs/pilot.toml"),
) -> MacroMedallionConfig:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(
            f"cannot read pilot configuration at {path}: {error}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML configuration at {path}: {error}") from error
    section = document.get("macro_medallion")
    if not isinstance(section, dict):
        raise ConfigError("configuration requires a [macro_medallion] table")
    series_ids = section.get("series_ids")
    if (
        not isinstance(series_ids, list)
        or not series_ids
        or any(not isinstance(value, str) or not value.strip() for value in series_ids)
    ):
        raise ConfigError("macro_medallion.series_ids must be a nonempty string array")
    if len(series_ids) != len(set(series_ids)):
        raise ConfigError("macro_medallion.series_ids must not contain duplicates")
    required = (
        "observation_start",
        "observation_end",
        "knowledge_cutoff",
        "redistribution_status",
    )
    missing = [
        key
        for key in required
        if not isinstance(section.get(key), str) or not section[key]
    ]
    if missing:
        raise ConfigError(
            f"macro_medallion is missing required fields: {', '.join(missing)}"
        )
    return MacroMedallionConfig(
        series_ids=tuple(series_ids),
        observation_start=section["observation_start"],
        observation_end=section["observation_end"],
        knowledge_cutoff=section["knowledge_cutoff"],
        redistribution_status=section["redistribution_status"],
    )


def load_macro_context(
    path: Path = Path("configs/context_pilot.toml"),
) -> MacroContextConfig:
    """Load bounded context-adapter inputs without connection credentials."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(
            f"cannot read context configuration at {path}: {error}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML configuration at {path}: {error}") from error
    section = document.get("macro_context")
    if not isinstance(section, dict):
        raise ConfigError("configuration requires a [macro_context] table")
    series_ids = section.get("series_ids")
    if (
        not isinstance(series_ids, list)
        or not series_ids
        or any(not isinstance(value, str) or not value.strip() for value in series_ids)
    ):
        raise ConfigError("macro_context.series_ids must be a nonempty string array")
    if len(series_ids) != len(set(series_ids)):
        raise ConfigError("macro_context.series_ids must not contain duplicates")
    required = ("release_start", "release_end", "redistribution_status")
    missing = [
        key
        for key in required
        if not isinstance(section.get(key), str) or not section[key]
    ]
    if missing:
        raise ConfigError(
            f"macro_context is missing required fields: {', '.join(missing)}"
        )
    return MacroContextConfig(
        series_ids=tuple(series_ids),
        release_start=section["release_start"],
        release_end=section["release_end"],
        redistribution_status=section["redistribution_status"],
    )
