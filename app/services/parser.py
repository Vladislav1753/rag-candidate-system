from pypdf import PdfReader
import logging

logger = logging.getLogger("parser")


def extract_text_from_pdf(file_stream) -> str:
    """Extracts raw text from a PDF file stream."""
    try:
        reader = PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return ""
