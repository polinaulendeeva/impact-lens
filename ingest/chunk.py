CHUNK_WORDS = 300    # the embedding model reads ~512 tokens, about 380 words
OVERLAP_WORDS = 50   # so a sentence cut at a boundary appears in both chunks
MIN_WORDS = 30       # skip near-empty fragments such as cover pages


def chunk_pages(pages):
    """Split each page into overlapping chunks, keeping the page number."""
    chunks = []
    step = CHUNK_WORDS - OVERLAP_WORDS
    for page_number, text in pages:
        words = text.split()
        for start in range(0, len(words), step):
            piece = words[start:start + CHUNK_WORDS]
            if len(piece) >= MIN_WORDS:
                chunks.append({"page": page_number, "text": " ".join(piece)})
            if start + CHUNK_WORDS >= len(words):
                break
    return chunks
