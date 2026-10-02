import csv
import hashlib
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Chunk, Company, Document
from ingest.chunk import chunk_pages
from ingest.embed import embed_passages
from ingest.parse import extract_pages

RAW_DIR = Path("data/raw")
SOURCES = Path("data/sources.csv")


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    with open(SOURCES, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    loaded = skipped = problems = 0
    for row in rows:
        name, path = row["company"], RAW_DIR / row["filename"]
        if not path.exists():
            print(f"MISSING  {name}: {path} not found")
            problems += 1
            continue

        sha = file_sha256(path)
        with SessionLocal() as session:
            if session.scalar(select(Document.id).where(Document.sha256 == sha)):
                print(f"SKIP     {name}: already loaded")
                skipped += 1
                continue

            company_id = session.scalar(select(Company.id).where(Company.name == name))
            if company_id is None:
                print(f"UNKNOWN  {name}: not in companies table (check spelling vs seed.py)")
                problems += 1
                continue

            pages = extract_pages(path)
            chunks = chunk_pages(pages)
            if not chunks:
                print(f"NO TEXT  {name}: no extractable text (scanned PDF?)")
                problems += 1
                continue

            print(f"EMBED    {name}: {len(pages)} pages, {len(chunks)} chunks ...")
            vectors = embed_passages([c["text"] for c in chunks])

            document = Document(
                company_id=company_id,
                title=row["title"] or row["filename"],
                year=int(row["year"]),
                source_url=row["url"] or None,
                sha256=sha,
            )
            session.add(document)
            session.flush()  # gives the document its id
            session.add_all([
                Chunk(document_id=document.id, page=c["page"], text=c["text"], embedding=v)
                for c, v in zip(chunks, vectors)
            ])
            session.commit()  # document and its chunks are saved together, or not at all
            loaded += 1
            print(f"LOADED   {name}")

    print(f"\nDone: {loaded} loaded, {skipped} skipped, {problems} problems")


if __name__ == "__main__":
    main()