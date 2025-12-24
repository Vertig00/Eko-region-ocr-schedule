import re
from datetime import date
import fitz

import logging

logger = logging.getLogger(__name__)

class PdfService:
    def __init__(self, file):
        self.file = file

    # TODO: move to fileService
    def save_selected_page(self, page_number):
        doc = fitz.open(self.file)
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_number - 1, to_page=page_number - 1)
        new_doc.save(self.file)
        doc.close()
        new_doc.close()

    def detect_multipage(self):
        doc = fitz.open(self.file)
        num_pages = doc.page_count
        doc.close()
        return num_pages > 1, num_pages

    def detect_year(self):
        pattern = r'KALENDARZ ODBIORU ODPADÓW\s+(\d{4})'

        doc = fitz.open(self.file)
        page = doc.load_page(0)
        text = page.get_text()
        match = re.search(pattern, text, re.IGNORECASE)
        doc.close()
        if match:
            return match.group(1)
        else:
            logger.warning("Cannot recognized YEAR from PDF file, try to resolve YEAR by current date.")
            return self._define_date_if_not_reckognised

    def _define_date_if_not_reckognised(self):
        now = date.today()
        return str(now.year + 1 if now.month == 12 else now.year)
