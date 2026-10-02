import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Chunk, Company, Document
from ingest.embed import embed_query


def main(company, question, k=5):
    query_vector = embed_query(question)
    distance = Chunk.embedding.cosine_distance(query_vector)
    with SessionLocal() as session:
        results = session.execute(
            select(Chunk.page, Chunk.text, distance.label("distance"))
            .join(Document, Document.id == Chunk.document_id)
            .join(Company, Company.id == Document.company_id)
            .where(Company.name == company)
            .order_by(distance)
            .limit(k)
        ).all()
    for page, passage, dist in results:
        print(f"--- page {page}  (similarity {1 - dist:.2f})")
        print(passage[:500], "...\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    