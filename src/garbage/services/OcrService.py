import logging
from pathlib import Path

import cv2
import easyocr
import numpy as np
import pandas as pd

from garbage.services.FileService import FileService

logger = logging.getLogger(__name__)

class OcrService:

    MODEL_SUBFOLDER = Path("models")
    TMP_SUBFOLDER = Path("ocr")
    LANGS = ['pl']
    TOLERANCE_Y = 25        # grupowanie wierszy
    TOLERANCE_X_GROUP = 60  # grupowanie kolumn
    CELL_VERTICAL_MERGE = 20  # odległość (px) w pionie dla łączenia tekstów w tej samej komórce

    HEADER_OUTPUT = "header_harmonogram.csv"
    DATA_OUTPUT = "data_harmonogram.csv"

    def __init__(self, file_service: FileService, headers_file, data_file) -> None:
        pd.set_option('display.max_columns', None)
        self.file_service = file_service
        self.headers_file = headers_file
        self.data_file = data_file
        self.dir = self.file_service.temporary_directory / self.TMP_SUBFOLDER
        self.file_service.create_folder(self.dir)
        self.model_path = self.file_service.base_directory / self.file_service.resources_dir / self.MODEL_SUBFOLDER
        self._check_models()


    def _check_models(self):
        if not self.file_service.path_exists(self.model_path) or not self.file_service.list_dir(self.model_path):
            logger.info("Modele EasyOCR nie istnieją, pobieram...")
            self.reader = easyocr.Reader(['en', 'pl'], model_storage_directory=self.model_path)
        else:
            logger.info("Modele EasyOCR już są, używam ich z cache")
            self.reader = easyocr.Reader(['en', 'pl'], model_storage_directory=self.model_path)

    def process(self):
        self.ocr(self.headers_file, self.HEADER_OUTPUT)
        self.ocr(self.data_file, self.DATA_OUTPUT)
        return self.dir/ self.HEADER_OUTPUT, self.dir / self.DATA_OUTPUT

    def ocr(self, file_path, output_file_path):
        # ====== Wczytanie i OCR ======
        img = cv2.imread(file_path)
        # reader = easyocr.Reader(self.LANGS)
        results = self.reader.readtext(img)

        # ====== Tworzenie listy elementów ======
        elements = []
        for bbox, text, conf in results:
            if not text:
                continue
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            cx, cy = np.mean(x_coords), np.mean(y_coords)
            elements.append({'text': text.strip(), 'x': cx, 'y': cy, 'bbox': bbox})

        # ====== Sortowanie po Y ======
        elements.sort(key=lambda e: e['y'])

        # ====== Grupowanie wierszy ======
        rows, current_row, last_y = [], [], None
        for el in elements:
            if last_y is None or abs(el['y'] - last_y) < self.TOLERANCE_Y:
                current_row.append(el)
            else:
                rows.append(current_row)
                current_row = [el]
            last_y = el['y']
        if current_row:
            rows.append(current_row)

        # ====== Wykrywanie kolumn ======
        all_x = sorted([e['x'] for e in elements])
        col_groups = []
        cur = [all_x[0]]
        for x in all_x[1:]:
            if abs(x - cur[-1]) < self.TOLERANCE_X_GROUP:
                cur.append(x)
            else:
                col_groups.append(cur)
                cur = [x]
        if cur:
            col_groups.append(cur)
        col_centers = [np.mean(g) for g in col_groups]

        # ====== Funkcja do znalezienia najbliższej kolumny ======
        def nearest_col(x):
            return np.argmin([abs(x - c) for c in col_centers])

        # ====== Grupowanie i scalanie tekstów ======
        final_rows = []
        for row in rows:
            cols = {i: [] for i in range(len(col_centers))}
            for el in sorted(row, key=lambda e: e['x']):
                col = nearest_col(el['x'])
                cols[col].append(el)
            # scalanie tekstów pionowo w obrębie komórki
            merged_row = []
            for i in range(len(col_centers)):
                cell_texts = cols[i]
                if not cell_texts:
                    merged_row.append("")
                else:
                    # sortuj pionowo w komórce
                    cell_texts = sorted(cell_texts, key=lambda e: e['y'])
                    merged_lines = []
                    current_block = [cell_texts[0]['text']]
                    last_y = cell_texts[0]['y']
                    for t in cell_texts[1:]:
                        if abs(t['y'] - last_y) < self.CELL_VERTICAL_MERGE:
                            # ta sama linia (scalamy w poziomie)
                            current_block[-1] += " " + t['text']
                        else:
                            # nowa linia w tej samej komórce
                            merged_lines.append(" ".join(current_block))
                            current_block = [t['text']]
                        last_y = t['y']
                    merged_lines.append(" ".join(current_block))
                    merged_row.append(" ".join(merged_lines))  # <-- łączenie w pionie
            final_rows.append(merged_row)

        # ====== Tworzenie DataFrame ======
        max_cols = max(len(r) for r in final_rows)
        for r in final_rows:
            while len(r) < max_cols:
                r.append("")
        df = pd.DataFrame(final_rows)

        logger.debug("\n📊 Odczytana tabela z wieloliniowymi komórkami:\n")
        print(df)

        self.file_service.save_df_to_csv(self.dir / output_file_path, df)
        logger.debug(f"\n✅ Zapisano do pliku: {output_file_path}")
