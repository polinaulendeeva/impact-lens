from sqlalchemy import select

from app.models import Chunk, Document
from ingest.embed import embed_query

TOP_K = 8


def retrieve(session, company_id, theme, k=TOP_K):
    """Return the k passages of this company's report closest in meaning to the theme."""
    query = (f"{theme.name}: {theme.definition} "
             "Revenue, sales and business segments related to this.")
    distance = Chunk.embedding.cosine_distance(embed_query(query))
    rows = session.execute(
        select(Chunk.id, Chunk.page, Chunk.text)
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.company_id == company_id)
        .order_by(distance)
        .limit(k)
    ).all()
    return [{"chunk_id": r.id, "page": r.page, "text": r.text} for r in rows]
    