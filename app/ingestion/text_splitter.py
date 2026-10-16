import re


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text.
    """

    # Replace multiple whitespace characters
    # with a single space.
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def split_text(
    text: str,
    chunk_size: int = 300,
    overlap: int = 50
) -> list[str]:
    """
    Split text into chunks without cutting
    sentences in the middle.

    Sentences are grouped until the chunk
    reaches approximately chunk_size characters.
    """

    sentences = split_into_sentences(text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:

        # If adding this sentence would make the
        # chunk too large, save the current chunk.
        if (
            current_chunk
            and len(current_chunk) + len(sentence) + 1
            > chunk_size
        ):

            chunks.append(
                current_chunk.strip()
            )

            # Keep a small amount of overlap
            # using the end of the previous chunk.
            overlap_text = current_chunk[-overlap:]

            current_chunk = (
                overlap_text
                + " "
                + sentence
            )

        else:

            if current_chunk:

                current_chunk += " " + sentence

            else:

                current_chunk = sentence

    # Add the final chunk.
    if current_chunk.strip():

        chunks.append(
            current_chunk.strip()
        )

    return chunks


def process_pages(
    pages: list[dict],
    chunk_size: int = 300,
    overlap: int = 50
) -> list[dict]:
    """
    Process every PDF page while preserving
    page numbers.
    """

    processed_chunks = []

    for page in pages:

        page_number = page["page"]

        cleaned_text = clean_text(
            page["text"]
        )

        chunks = split_text(
            cleaned_text,
            chunk_size,
            overlap
        )

        for chunk_number, chunk in enumerate(
            chunks,
            start=1
        ):

            processed_chunks.append(
                {
                    "page": page_number,
                    "chunk": chunk,
                    "chunk_number": chunk_number
                }
            )

    return processed_chunks
