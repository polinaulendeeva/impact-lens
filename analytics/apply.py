from pathlib import Path

from sqlalchemy import text

from app.db import engine

SQL = (Path(__file__).parent / "views.sql").read_text(encoding="utf-8")


def main():
    with engine.begin() as connection:
        for statement in SQL.split(";"):
            if statement.strip():
                connection.execute(text(statement))
    print("Views created: v_current_assessment, v_portfolio_exposure")


if __name__ == "__main__":
    main()
    