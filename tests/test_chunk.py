from ingest.chunk import CHUNK_WORDS, OVERLAP_WORDS, chunk_pages


def test_very_short_pages_are_skipped():
    assert chunk_pages([(1, "Annual Report 2025")]) == []


def test_chunks_keep_their_page_number():
    chunks = chunk_pages([(7, " ".join(["word"] * 100))])
    assert len(chunks) == 1
    assert chunks[0]["page"] == 7


def test_long_page_is_split_with_overlap():
    words = [f"w{i}" for i in range(700)]
    chunks = chunk_pages([(3, " ".join(words))])

    assert len(chunks) == 3
    assert all(len(c["text"].split()) <= CHUNK_WORDS for c in chunks)
    first, second = chunks[0]["text"].split(), chunks[1]["text"].split()
    assert first[-OVERLAP_WORDS:] == second[:OVERLAP_WORDS]
    assert chunks[-1]["text"].split()[-1] == "w699"   # nothing lost at the end
    