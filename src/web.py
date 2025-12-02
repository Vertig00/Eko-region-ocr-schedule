import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from garbage.services.CsvProcessing import CsvProcessing
from garbage.services.FileService import FileService
from garbage.services.ImageProcessingService import ImageProcessingService
from garbage.services.process import process_schedule_to_csv, process_from_csv

BASE_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = BASE_DIR / "resources"
RESOURCES_TMP_DIR = RESOURCES_DIR / "tmp"

file_service = FileService(BASE_DIR)

processing_status = "start"

st.title("OCR Harmonogramu Eko-Region")
st.set_page_config(layout="wide")

year = ""

# --- inicjalizacja stanu ---
if "step" not in st.session_state:
    st.session_state.step = 1


# ============================================================
# KROK 1 – wgrywanie pliku
# ============================================================
INPUT_FILE_DIR = RESOURCES_TMP_DIR / "input"
os.makedirs(INPUT_FILE_DIR, exist_ok=True)
target_filename = "Harmonogram.pdf"

if st.session_state.step == 1:
    uploaded_file = st.file_uploader(f"Wgraj plik z harmonogramem w PDF.", type=["pdf"])
    st.markdown("Harmonogram dostępny na stronie https://eko-region.pl/")
    save_path = os.path.join(INPUT_FILE_DIR, target_filename)

    if uploaded_file:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.step = 2
        st.success("Plik wgrany ✔️")

    st.text("Albo wklej link do pliku harmonogramu.")
    url = st.text_input("Link:", value="")
    if st.button("📥 Pobierz plik"):
        if not url:
            st.error("Podaj link")
            st.stop()

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            st.success(f"Pobrano plik ✔️")
            st.session_state.step = 2
        except Exception as e:
            st.error(f"Błąd pobierania: {e}")


# ============================================================
# KROK 2 – przetwarzanie
# ============================================================
if st.session_state.step == 2:
    if st.button("Rozpocznij OCR"):
        st.info("⏳ Przetwarzanie w toku...")

        year = process_schedule_to_csv(BASE_DIR, INPUT_FILE_DIR / target_filename)
        print(f"YEAR: {year}")

        st.success("Przetwarzanie zakończone!")
        st.session_state.step = 3
        st.rerun()   # odśwież ekran, aby wykryć nowy plik


# ============================================================
# KROK 3 – porównywanie i edycja
# ============================================================
if st.session_state.step == 3:
    CSV_PATH = RESOURCES_TMP_DIR / CsvProcessing.TMP_SUBFOLDER / "harmonogram.csv"
    IMAGE_PATH = RESOURCES_TMP_DIR / ImageProcessingService.TMP_SUBFOLDER
    st.text(
        """
            Porównaj dane z tabeli wejściowej z odczytaną tabelą przez program. 
            Program może się pomylić dlatego ważne by skorygować wszelkie błędy.
            Sprawdź dane w tabeli i popraw tak, by odpowiadała plikowi wejściowemu.
            Nie zmieniaj nazw kolumn, ich inna nazwa to zamierzony efekt.
        """
    )
    if os.path.exists(CSV_PATH):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Źródło")
            st.image(IMAGE_PATH / ImageProcessingService.CROPPED_IMAGE_NAME)

        with col2:
            st.subheader("📊 Wynik przetwarzania")
            df = pd.read_csv(CSV_PATH, delimiter=";", dtype=str)
            ROW_HEIGHT = 34
            HEADER_HEIGHT = 60
            table_height = 12 * ROW_HEIGHT + HEADER_HEIGHT

            df = df.rename(columns={
                "Metale tworzywa sztuczne": "Plastik",
                "Zmieszane odpady komunalne": "Zmieszane"
            })
            edited_df = st.data_editor(df, num_rows="fixed", height=table_height, width="stretch", hide_index=True)

        if st.button("💾 Zapisz zmiany i procesuj dalej"):
            edited_df.to_csv(CSV_PATH, sep=";", index=False)
            process_from_csv(BASE_DIR, CSV_PATH, year)
            st.success("Przetwarzanie zakończone!")
            st.session_state.step = 4
            st.rerun()

# ============================================================
# KROK 4 – generowanie i pobieranie pliku ICS
# ============================================================
if st.session_state.step == 4:
    ICS_PATH = BASE_DIR / "src"
    ics_file = file_service.find_by_pattern(ICS_PATH, "*.ics")[0].name # TODO: co jak nie ma ?

    if os.path.exists(ics_file):
        st.success(f"Plik `{ics_file}` jest gotowy do pobrania!")
        with open(ICS_PATH / ics_file, "rb") as f:
            ics_bytes = f.read()

        st.download_button(
            label=f"⬇️ Pobierz {ics_file}",
            data=ics_bytes,
            file_name=ics_file,
            mime="text/calendar"
        )
        st.session_state.step = 1

# ============================================================
# Inne Elementy
# ============================================================
if st.button("Do początku"):
    st.session_state.step = 1
    st.rerun()
