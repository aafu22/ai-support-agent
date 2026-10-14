from app.services.ingestion.chunker import chunk_pages
from app.services.ingestion.cleaner import clean_pages, clean_text


def test_clean_text_rejoins_hyphenation_and_strips_page_numbers():
    out = clean_text("The refund pol-\nicy applies.\n\n12\n\nPage 3 of 10\nNext   line")
    assert "policy applies." in out
    assert "\n12\n" not in f"\n{out}\n"
    assert "Page 3" not in out
    assert "Next line" in out


def test_clean_pages_removes_repeated_headers():
    pages = [(i, f"ACME Corp Confidential\nContent number {i}") for i in range(1, 5)]
    cleaned = clean_pages(pages)
    assert all("Confidential" not in t for _, t in cleaned)
    assert cleaned[0][1] == "Content number 1"


def test_chunks_respect_size_and_keep_page_numbers():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(20))
    chunks = chunk_pages([(7, text)], size=500, overlap=60)
    assert len(chunks) > 3
    assert all(len(c.text) <= 500 + 60 for c in chunks)
    assert all(c.page == 7 for c in chunks)


def test_oversized_paragraph_is_split():
    chunks = chunk_pages([(None, "A sentence here. " * 200)], size=300, overlap=0)
    assert len(chunks) > 5 and all(len(c.text) <= 300 for c in chunks)


def test_overlap_repeats_text_between_chunks():
    text = "\n\n".join(f"Unique{i} " + "filler " * 25 for i in range(6))
    chunks = chunk_pages([(None, text)], size=300, overlap=80)
    assert chunks[0].text.split()[-1] in chunks[1].text


def test_empty_input_gives_no_chunks():
    assert chunk_pages([(None, "")]) == []
