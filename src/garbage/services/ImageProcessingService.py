import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from garbage.services.FileService import FileService

logger = logging.getLogger(__name__)

class ImageProcessingService:

    CROPPED_IMAGE_NAME = "1. cropped_table.png"
    EMPTY_CELL_CHARACTER = "+"
    TMP_SUBFOLDER = Path("image")

    def __init__(self, file_service: FileService, input_file):
        self.file_service = file_service
        self.input_file = input_file
        self.dir = self.file_service.temporary_directory / self.TMP_SUBFOLDER
        self.file_service.create_folder(self.dir)

    def process_waste_pdf(self):
        cropped_image = self._crop_file(self.input_file)
        redless_image = self._replace_red_black(self.dir / cropped_image)
        colorless_image = self._eliminate_colours(self.dir / redless_image)

        filled_image = self._fill_empty_cells(self.dir / colorless_image)
        header, body = self._split_table_into_header_and_body(self.dir / filled_image)

        return self.dir / header, self.dir / body

    def _crop_file(self, file_name) -> str:
        OUT_FILE = self.CROPPED_IMAGE_NAME

        # === 1. Otwórz PDF i wczytaj stronę ===
        doc = self.file_service.open_pdf(file_name)
        page = doc.load_page(0)

        # Tworzymy pixmap z wysoką rozdzielczością
        pix = page.get_pixmap(dpi=300)

        # === 2. Zamiana pixmap na numpy array ===
        # Sprawdzenie czy jest kanał alfa
        if pix.alpha:
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 4)
            # Konwersja RGBA -> RGB (usuwa alfa)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        else:
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

        # Konwersja do BGR dla OpenCV
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # === 3. Wykrywanie linii tabeli ===
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("Nie znaleziono żadnych konturów w obrazie PDF.")

        # Wybieramy największy kontur (domniemana tabela)
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)

        # === 4. Przycinanie obrazu do tabeli ===
        MARGIN = 5
        cropped_bgr = img_bgr[y-MARGIN:y+h+MARGIN, x-MARGIN:x+w+MARGIN]

        # === 5. Zapis przyciętego obrazu ===
        cv2.imwrite(self.dir / OUT_FILE, cropped_bgr)
        logger.debug(f"✅ Zapisano przyciętą tabelę do: {self.dir / OUT_FILE}")

        return OUT_FILE

    def _replace_red_black(self, file_name, sensitivity=0.5):
        """
        sensitivity – zakres 0.1–1.0
        większa wartość = większa tolerancja na różne odcienie czerwieni
        """

        import colorsys
        OUT_FILE = "2. redless.png"
        img = Image.open(file_name).convert("RGB")
        pixels = img.load()

        # ustawienia zależne od czułości
        hue_range = 0.03 + sensitivity * 0.07   # szerokość stożka czerwieni
        min_saturation = 0.2 - sensitivity * 0.15  # dopuszczalna saturacja

        for i in range(img.width):
            for j in range(img.height):
                r, g, b = pixels[i, j]
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)

                # czerwony jest przy H ≈ 0 (i ≈1), więc bierzemy oba końce skali
                if (h < hue_range or h > 1 - hue_range) and s > min_saturation:
                    pixels[i, j] = (0, 0, 0)

        img.save(self.dir / OUT_FILE)
        return OUT_FILE

    def _eliminate_colours(self, file_name):
        OUT_FILE = "3. colorless.png"

        image = cv2.imread(file_name)
        output = image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Binaryzacja do wykrycia linii
        thresh = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

        # Wykrywanie linii poziomych
        horizontal = thresh.copy()
        cols = horizontal.shape[1]
        horizontal_size = cols // 30
        horizontal_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
        horizontal = cv2.erode(horizontal, horizontal_structure)
        horizontal = cv2.dilate(horizontal, horizontal_structure)

        # Wykrywanie linii pionowych
        vertical = thresh.copy()
        rows = vertical.shape[0]
        vertical_size = rows // 30
        vertical_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
        vertical = cv2.erode(vertical, vertical_structure)
        vertical = cv2.dilate(vertical, vertical_structure)

        # Maska wszystkich linii
        mask_lines = horizontal + vertical

        # Kontury komórek
        contours, _ = cv2.findContours(mask_lines, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Konwersja do HSV do wykrywania nasyconych kolorów
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Automatyczna maska dla bardzo nasyconych kolorów (saturation i value powyżej progu)
        # Dzięki temu zostaną wykryte wszystkie intensywne kolory tła
        sat_thresh = 80   # minimalna saturacja, by uznać kolor za intensywny
        val_thresh = 180  # minimalna jasność, by nie usuwać tekstu/ciemnych linii
        mask_bright = cv2.inRange(hsv, np.array([0, sat_thresh, val_thresh]), np.array([179, 255, 255]))

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 20 or h < 20:
                continue

            cell = output[y:y+h, x:x+w]

            # --- Usuwanie koloru na podstawie średniego koloru (dynamiczne tło) ---
            mean_color = cv2.mean(cell)[:3]
            mean_color = np.array(mean_color, dtype=np.uint8)
            lower = np.clip(mean_color - 60, 0, 255)
            upper = np.clip(mean_color + 60, 0, 255)
            mask_cell = cv2.inRange(cell, lower, upper)
            cell[mask_cell > 0] = [255, 255, 255]

            # --- Usuwanie wszystkich intensywnych kolorów ---
            mask_bright_in_cell = mask_bright[y:y+h, x:x+w]
            cell[mask_bright_in_cell > 0] = [255, 255, 255]

            output[y:y+h, x:x+w] = cell

        # Zapisz wynik
        cv2.imwrite(self.dir / OUT_FILE, output)

        return OUT_FILE


    def _all_black(self, file_name):
        OUT_FILE = "2. black.png"
        img = cv2.imread(file_name)

        # 1️⃣ Zamiana na skalę szarości
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2️⃣ Wykrycie liter i ciemnych linii – maska tekstu
        # Adaptive threshold dobrze działa przy nierównym oświetleniu
        text_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                          cv2.THRESH_BINARY_INV, 15, 10)

        # Opcjonalnie poprawa maski morfologią
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, kernel)

        # 3️⃣ Tworzymy białe tło
        white_bg = np.full_like(img, 255)  # obraz w pełni biały

        # 4️⃣ Na białe tło nakładamy litery z oryginalnego obrazu
        result = white_bg.copy()
        result[text_mask > 0] = img[text_mask > 0]

        # 5️⃣ Zapis wyniku
        cv2.imwrite(self.dir / OUT_FILE, result)
        return OUT_FILE

    def _fill_empty_cells(self, file_name):
        OUT_FILE = "4. filled_image.png"
        OUT_DEBUG = "4. obraz_kontury.png"

        # Wczytaj obraz
        img = cv2.imread(file_name)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Inwersja (bo linie są ciemne)
        gray = cv2.bitwise_not(gray)

        # Binaryzacja
        _, bw = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)

        # --- 1️⃣ Wykryj linie poziome i pionowe ---
        # Kernel poziomy
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detect_horizontal = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=2)

        # Kernel pionowy
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        detect_vertical = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel, iterations=2)

        # Połącz linie poziome i pionowe
        grid = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)

        # Zamknij drobne przerwy w liniach
        grid = cv2.dilate(grid, np.ones((3, 3), np.uint8), iterations=1)

        # --- 2️⃣ Znajdź kontury (czyli komórki) ---
        contours, _ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        debug = img.copy()

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 40 or h < 20 or w > img.shape[1]*0.95:
                continue  # pomiń małe lub bardzo duże prostokąty (np. cała tabela)

            # Wytnij zawartość komórki
            roi = gray[y+3:y+h-3, x+3:x+w-3]
            if roi.size == 0:
                continue

            # Sprawdź, czy komórka pusta (większość bieli)
            white_ratio = np.sum(roi == 0) / roi.size
            if white_ratio > 0.998:
                cx, cy = x + w // 2, y + h // 2
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                text_size = cv2.getTextSize(self.EMPTY_CELL_CHARACTER, font, font_scale, thickness)[0]
                tx = int(cx - text_size[0] / 2)
                ty = int(cy + text_size[1] / 2)
                cv2.putText(img, self.EMPTY_CELL_CHARACTER, (tx, ty), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
                cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 255, 0), 2)  # zielony = pusta komórka
            else:
                cv2.rectangle(debug, (x, y), (x + w, y + h), (0, 0, 255), 1)  # czerwony = zawiera tekst

        # --- 3️⃣ Zapisz wyniki ---
        cv2.imwrite(self.dir / OUT_FILE, img)
        cv2.imwrite(self.dir / OUT_DEBUG, debug)

        return OUT_FILE

    def _split_table_into_header_and_body(self, input_path):
        """
        Dzieli obraz tabeli na:
          - nagłówek (pierwszy wiersz),
          - ciało tabeli (reszta),
        bez przycinania do ramki.
        """
        HEADER_FILE = "5. headers.png"
        BODY_FILE = "5. data.png"

        # Wczytaj obraz (w odcieniach szarości)
        img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)

        # Odwrócenie kolorów, żeby linie były białe
        inverted = cv2.bitwise_not(img)

        # Binaryzacja
        _, binary = cv2.threshold(inverted, 128, 255, cv2.THRESH_BINARY)

        # --- 1️⃣ Wykrycie poziomych linii ---
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (binary.shape[1] // 2, 2))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)

        # Uśrednienie intensywności w pionie (suma wartości pikseli dla każdego wiersza)
        y_profile = np.sum(horizontal_lines, axis=1)

        # Szukamy rzędów, gdzie występują linie (intensywność powyżej progu)
        line_positions = np.where(y_profile > y_profile.max() * 0.3)[0]

        if len(line_positions) < 2:
            raise ValueError("Nie udało się wykryć dwóch linii poziomych — sprawdź jakość obrazu.")

        # --- 2️⃣ Grupowanie zbliżonych linii w jedną ---
        grouped_lines = []
        current = [line_positions[0]]
        for y in line_positions[1:]:
            if y - current[-1] > 5:  # przerwa > 5 px => nowa linia
                grouped_lines.append(int(np.mean(current)))
                current = [y]
            else:
                current.append(y)
        grouped_lines.append(int(np.mean(current)))

        # Teraz powinniśmy mieć listę linii poziomych (od góry do dołu)
        y_top = grouped_lines[0]           # pierwsza linia (góra tabeli)
        y_header_bottom = grouped_lines[1] # linia pod nagłówkiem

        # --- 3️⃣ Podział obrazu ---
        header = img[y_top-5:y_header_bottom+5, :]
        body = img[y_header_bottom-5:, :]

        # --- 4️⃣ Zapisz wyniki ---
        header_output = self.dir / HEADER_FILE
        body_output = self.dir / BODY_FILE
        cv2.imwrite(header_output, header)
        cv2.imwrite(body_output, body)

        return header_output, body_output
