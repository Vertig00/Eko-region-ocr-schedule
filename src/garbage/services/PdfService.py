import re
from datetime import date

import fitz
import logging

logger = logging.getLogger(__name__)

class PdfService:
    def __init__(self, file):
        self.file = file

    def detect_year(self):
        pattern = r'KALENDARZ ODBIORU ODPADÓW\s+(\d{4})'

        doc = fitz.open(self.file)
        page = doc.load_page(0)
        text = page.get_text()
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        else:
            logger.warning("Cannot recognized YEAR from PDF file, try to resolve YEAR by current date.")
            return self._define_date_if_not_reckognised

    def _define_date_if_not_reckognised(self):
        now = date.today()
        return now.year + 1 if now.month == 12 else now.year
