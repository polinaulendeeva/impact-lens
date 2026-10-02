import pymupdf


def extract_pages(path):
    """Return a list of (page_number, text) for every page that has text."""
    pages = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            # PDFs can contain NUL characters, which PostgreSQL cannot store
            raw = page.get_text("text").replace("\x00", " ")
            text = " ".join(raw.split())
            if text:
                pages.append((number, text))
    return pages
