from pathlib import Path
from pypdf import PdfReader


def load_pdf(file_path: str) -> list[dict]:
    """
    Extract text from a PDF while preserving page numbers.

    Returns:
        A list of dictionaries containing:
        - page number
        - page text
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    reader = PdfReader(path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):
        page_text = page.extract_text()

        if page_text:
            pages.append(
                {
                    "page": page_number,
                    "text": page_text
                }
            )

    return pages


if __name__ == "__main__":

    pdf_path = "data/raw/employee_handbook.pdf"

    pages = load_pdf(pdf_path)

    print("PDF loaded successfully.")
    print("-" * 50)

    for page in pages:

        print(f"\nPAGE {page['page']}")
        print("-" * 50)
        print(page["text"])