"""Run SQL migrations against the configured Supabase Postgres database."""

from pathlib import Path

from psycopg import connect

from backend.core.config import get_settings


def main() -> None:
    """Apply SQL files in lexical order."""
    settings = get_settings()
    if not settings.supabase_db_url:
        raise ValueError("SUPABASE_DB_URL is required to run migrations.")

    sql_dir = Path(__file__).resolve().parents[1] / "sql"
    files = sorted(sql_dir.glob("*.sql"))
    if not files:
        print("No SQL migrations found.")
        return

    with connect(settings.supabase_db_url.get_secret_value()) as connection:
        with connection.cursor() as cursor:
            for sql_file in files:
                print(f"Applying {sql_file.name}...")
                cursor.execute(sql_file.read_text(encoding="utf-8"))
        connection.commit()

    print("Migrations applied successfully.")


if __name__ == "__main__":
    main()
