from sqlalchemy import text

from app.db import SessionLocal

CHECKS = {
    "Companies with no document": """
        select c.name from companies c
        left join documents d on d.company_id = c.id
        where d.id is null order by 1""",
    "Documents with fewer than 20 chunks (scanned or very short?)": """
        select c.name, d.title, count(ch.id) as chunks
        from documents d join companies c on c.id = d.company_id
        left join chunks ch on ch.document_id = d.id
        group by c.name, d.title having count(ch.id) < 20""",
    "Chunks with no embedding": """
        select count(*) from chunks where embedding is null having count(*) > 0""",
    "Repeated chunk text within a document (headers, footers?)": """
        select c.name, count(*) - count(distinct md5(ch.text)) as repeats
        from chunks ch join documents d on d.id = ch.document_id
        join companies c on c.id = d.company_id
        group by c.name having count(*) > count(distinct md5(ch.text))""",
    "Documents older than 2024": """
        select c.name, d.year from documents d
        join companies c on c.id = d.company_id where d.year < 2024""",
    "Portfolio weights not summing to 100": """
        select portfolio, as_of, sum(weight) from holdings
        group by portfolio, as_of having sum(weight) <> 100""",
}


def main():
    with SessionLocal() as session:
        docs = session.scalar(text("select count(*) from documents"))
        chunks = session.scalar(text("select count(*) from chunks"))
        print(f"Documents: {docs}   Chunks: {chunks}\n")
        for name, sql in CHECKS.items():
            rows = session.execute(text(sql)).all()
            if rows:
                print(f"ISSUE  {name}")
                for r in rows:
                    print(f"         {tuple(r)}")
            else:
                print(f"OK     {name}")


if __name__ == "__main__":
    main()
    