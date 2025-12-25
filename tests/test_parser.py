from unittest.mock import MagicMock, patch
import io
from app.services.parser import extract_text_from_pdf


def test_extract_text_success():
    """
    Test successful text extraction.
    """
    mock_file_stream = io.BytesIO(b"fake pdf content")

    with patch("app.services.parser.PdfReader") as MockPdfReader:
        mock_instance = MockPdfReader.return_value

        page1 = MagicMock()
        page1.extract_text.return_value = "Hello "

        page2 = MagicMock()
        page2.extract_text.return_value = "World!"

        mock_instance.pages = [page1, page2]

        result = extract_text_from_pdf(mock_file_stream)

        assert result == "Hello \nWorld!\n"


def test_extract_text_error_handling():
    """
    Test error handling logic.
    If the file is corrupted, the function should log the error
    and return an empty string (instead of crashing).
    """
    mock_file_stream = io.BytesIO(b"corrupted content")

    with patch("app.services.parser.PdfReader") as MockPdfReader:
        MockPdfReader.side_effect = Exception("File is corrupted")

        result = extract_text_from_pdf(mock_file_stream)

        assert result == ""
