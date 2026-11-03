import os
import re
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.sql.sqltypes import Unicode


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str | URL, create_database: bool = True) -> None:
        self.url = make_url(url) if isinstance(url, str) else url
        self._create_database = create_database
        self.engine = None
        self.sessions = None

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Database":
        if env_file is not None:
            _load_env_file(Path(env_file))
        elif Path(".env").is_file():
            _load_env_file(Path(".env"))

        explicit_url = os.getenv("DATABASE_URL")
        if explicit_url:
            return cls(explicit_url)

        database_name = os.getenv("SQL_SERVER_DATABASE", "ITmanager").strip()
        if not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}", database_name):
            raise ValueError("SQL_SERVER_DATABASE contains unsupported characters.")

        server = os.getenv("SQL_SERVER_HOST", "192.168.1.69").strip()
        instance = os.getenv("SQL_SERVER_INSTANCE", "").strip()
        if not server:
            raise ValueError("SQL_SERVER_HOST must not be empty.")
        if instance:
            server = f"{server}\\{instance}"

        port = os.getenv("SQL_SERVER_PORT", "1433").strip()
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ValueError("SQL_SERVER_PORT must be between 1 and 65535.")

        driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 18 for SQL Server").strip()
        if not driver:
            raise ValueError("SQL_SERVER_DRIVER must not be empty.")

        auth_mode = os.getenv("SQL_SERVER_AUTH", "windows").strip().lower()
        query = {
            "driver": driver,
            "Encrypt": "yes",
            "TrustServerCertificate": "yes",
        }
        username = password = None
        if auth_mode == "windows":
            query["Trusted_Connection"] = "yes"
        elif auth_mode == "sql":
            username = os.getenv("SQL_SERVER_USER", "")
            password = os.getenv("SQL_SERVER_PASSWORD", "")
            if not username or not password:
                raise ValueError(
                    "Set SQL_SERVER_USER and SQL_SERVER_PASSWORD when SQL_SERVER_AUTH=sql."
                )
        else:
            raise ValueError("SQL_SERVER_AUTH must be either 'windows' or 'sql'.")

        return cls(
            URL.create(
                "mssql+pyodbc",
                username=username,
                password=password,
                host=server,
                port=int(port),
                database=database_name,
                query=query,
            )
        )

    def initialize(self) -> None:
        if self.engine is not None:
            return
        if self._create_database and self.url.get_backend_name() == "mssql":
            self._ensure_sql_server_database()
        try:
            from modules import persistence

            self.engine = create_engine(
                self.url,
                pool_pre_ping=True,
                connect_args={"timeout": 10} if self.url.get_backend_name() == "mssql" else {},
            )
            if self.url.get_backend_name() == "mssql":
                _recreate_empty_legacy_schema(self.engine, persistence.Base.metadata)
            persistence.Base.metadata.create_all(self.engine)
            self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        except Exception as error:
            self.close()
            raise RuntimeError(
                f"Could not initialize database '{self.url.database}'. "
                "Check the SQL Server address, ODBC driver, authentication, and database permissions."
            ) from error

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
            self.sessions = None

    def _ensure_sql_server_database(self) -> None:
        database_name = self.url.database
        if not database_name or not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}", database_name):
            raise ValueError("A valid SQL Server database name is required.")
        master_url = self.url.set(database="master")
        master_engine = create_engine(
            master_url, pool_pre_ping=True, connect_args={"timeout": 10}
        )
        quoted_name = database_name.replace("]", "]]")
        try:
            with master_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                exists = connection.execute(
                    text("SELECT DB_ID(:database_name)"),
                    {"database_name": database_name},
                ).scalar()
                if exists is None:
                    connection.exec_driver_sql(f"CREATE DATABASE [{quoted_name}]")
        except Exception as error:
            raise RuntimeError(
                f"Could not create or inspect SQL Server database '{database_name}'. "
                "Ensure the configured login can connect to master and create databases, "
                "or create the database in SQL Server Management Studio first."
            ) from error
        finally:
            master_engine.dispose()


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _recreate_empty_legacy_schema(engine, metadata) -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    tables = [table for table in metadata.sorted_tables if table.name in existing]
    has_non_unicode_columns = False
    for table in tables:
        reflected_columns = {
            column["name"]: column["type"] for column in inspector.get_columns(table.name)
        }
        if any(
            isinstance(column.type, Unicode)
            and not reflected_columns[column.name].__class__.__name__.upper().startswith(
                ("NVARCHAR", "NCHAR")
            )
            for column in table.columns
        ):
            has_non_unicode_columns = True
            break
    if not has_non_unicode_columns:
        return

    with engine.connect() as connection:
        populated_tables = [
            table.name
            for table in tables
            if connection.scalar(select(func.count()).select_from(table))
        ]
    if populated_tables:
        names = ", ".join(sorted(populated_tables))
        raise RuntimeError(
            "The existing SQL Server schema uses non-Unicode text columns and contains data "
            f"in {names}; migrate or back up this data before changing the schema."
        )

    metadata.drop_all(engine, tables=tables, checkfirst=True)
