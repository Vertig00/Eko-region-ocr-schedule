import logging
import re
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
    TOLERANCE_Y = 25          # grupowanie wierszy
    TOLERANCE_X_GROUP = 60    # grupowanie kolumn
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
        else:
            logger.info("Modele EasyOCR już są, używam ich z cache")
        self.reader = easyocr.Reader(self.LANGS, gpu=False, model_storage_directory=self.model_path)

    def process(self):
        self.ocr(self.headers_file, self.HEADER_OUTPUT)
        self.process_table_image(self.data_file, self.DATA_OUTPUT, 35, 80, 25)
        return self.dir/ self.HEADER_OUTPUT, self.dir / self.DATA_OUTPUT

    def ocr(self, file_path, output_file_path):
        # ====== Wczytanie i OCR ======
        img = cv2.imread(file_path)
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

    def _fix_ocr_text(self, t: str) -> str:
        """
        Naprawia typowe błędy OCR w tabeli:
          - ' j ' -> ' i '
          - '9 1 23' -> '9 i 23'
          - '141 28' -> '14 i 28'
          - '111 25' -> '11 i 25'
        Zasada: tylko rozdzielamy ostatnią cyfrę '1' z lewego tokena jeśli
        po rozdziale zakładamy sensowne dni (1-31) i po prawej też jest liczba 1-31.
        """
        if not t:
            return t

        # normalizacja
        s = t.strip()
        s = s.replace(' j ', ' i ')
        s = re.sub(r'\s+', ' ', s)

        tokens = s.split(' ')
        out = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]

            # jeżeli token to dokładnie 'i' -> zostaw
            if tok == 'i':
                # unikamy powtórzeń 'i i'
                if not (out and out[-1] == 'i'):
                    out.append('i')
                i += 1
                continue

            # jeśli mamy pojedyncze '1' pomiędzy liczbami -> separator 'i'
            if tok == '1' and i - 1 >= 0 and i + 1 < len(tokens):
                if tokens[i - 1].isdigit() and tokens[i + 1].isdigit():
                    # zamień '1' będące separatorem na 'i'
                    if not (out and out[-1] == 'i'):
                        out.append('i')
                    i += 1
                    continue

            # jeśli token jest cyfrowy i kończy się na '1' oraz istnieje nast. token cyfrowy,
            # spróbuj rozdzielić ostatnią '1' jako 'i' -> left + 'i' + next
            if tok.isdigit() and tok.endswith('1') and len(tok) >= 2 and (i + 1) < len(tokens) and tokens[
                i + 1].isdigit():
                left = tok[:-1]
                # walidacja: left i next muszą być plausybilne dni 1-31
                try:
                    if 1 <= int(left) <= 31 and 1 <= int(tokens[i + 1]) <= 31:
                        # dodaj left i separator 'i' (unikaj powtórzeń)
                        if not (out and out[-1] == left):
                            out.append(left)
                        if not (out and out[-1] == 'i'):
                            out.append('i')
                        # nie konsumujemy next tutaj — zostanie dodany w kolejnym kroku
                        i += 1
                        continue
                except ValueError:
                    pass  # jeśli nie da się zamienić, traktujemy normalnie

            # default: dodaj token (ale unikaj duplikatów spacji / i i)
            out.append(tok)
            i += 1

        # finalna normalizacja: usuń powtórne 'i' lub spacje
        res = ' '.join(out)
        res = re.sub(r'\s+', ' ', res).strip()
        # czasami powstały "i i" — zamień wielokrotne na jedno
        res = re.sub(r'(?:\bi\b[\s]*){2,}', 'i ', res).strip()
        return res

    def process_table_image(self, file_path, output_file_path, TOL_Y, TOL_X_GROUP, CELL_MERGE):
        img = cv2.imread(file_path)
        results = self.reader.readtext(img, contrast_ths=0.10, adjust_contrast=1.3)

        # --- Tworzenie elementów ---
        elements = []
        for bbox, text, conf in results:
            if not text:
                continue

            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]

            center_x = np.mean(x_coords)
            baseline_y = max(y_coords)  # kluczowe!

            elements.append({
                'text': self._fix_ocr_text(text.strip()),
                'x': center_x,
                'y': baseline_y,
                'bbox': bbox
            })

        # --- Sortowanie po Y (wiersze) ---
        elements.sort(key=lambda e: (round(e['y'] / 5), e['x']))

        rows, current_row, last_y = [], [], None
        for el in elements:
            if last_y is None or abs(el['y'] - last_y) < TOL_Y:
                current_row.append(el)
            else:
                rows.append(current_row)
                current_row = [el]
            last_y = el['y']
        if current_row:
            rows.append(current_row)

        # --- Wykrywanie kolumn ---
        all_x = sorted([e['x'] for e in elements])
        col_groups = []
        cur = [all_x[0]]
        for x in all_x[1:]:
            if abs(x - cur[-1]) < TOL_X_GROUP:
                cur.append(x)
            else:
                col_groups.append(cur)
                cur = [x]
        if cur:
            col_groups.append(cur)

        col_centers = [np.mean(g) for g in col_groups]

        def nearest_col(x):
            return np.argmin([abs(x - c) for c in col_centers])

        # --- Grupowanie i scalanie tekstów ---
        final_rows = []
        for row in rows:
            cols = {i: [] for i in range(len(col_centers))}
            for el in row:
                col = nearest_col(el['x'])
                cols[col].append(el)

            merged_row = []
            for i in range(len(col_centers)):
                items = cols[i]
                if not items:
                    merged_row.append("")
                    continue

                # lepsze sortowanie: najpierw Y, potem X
                items = sorted(items, key=lambda e: (e['y'], e['x']))

                merged = []
                line = [items[0]['text']]
                last_y = items[0]['y']

                for t in items[1:]:
                    if abs(t['y'] - last_y) < CELL_MERGE:
                        line.append(t['text'])
                    else:
                        merged.append(" ".join(line))
                        line = [t['text']]
                    last_y = t['y']

                merged.append(" ".join(line))

                # finalny tekst komórki
                merged_row.append(" ".join(merged))

            final_rows.append(merged_row)

        # ujednolicenie długości wierszy
        width = max(len(r) for r in final_rows)
        for r in final_rows:
            while len(r) < width:
                r.append("")

        df = pd.DataFrame(final_rows)

        logger.debug("\n📊 Odczytana tabela z wieloliniowymi komórkami:\n")
        print(df)

        self.file_service.save_df_to_csv(self.dir / output_file_path, df)
        logger.debug(f"\n✅ Zapisano do pliku: {output_file_path}")
