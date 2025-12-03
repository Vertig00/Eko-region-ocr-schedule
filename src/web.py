import os
from pathlib import Path

import pandas as pd
import streamlit as st

from garbage.services.ApiProcessor import ApiProcessor
from garbage.services.CsvProcessing import CsvProcessing
from garbage.services.FileService import FileService
from garbage.services.ImageProcessingService import ImageProcessingService
from garbage.services.helpers import prepare_selector_from_api_response
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
file_service.create_folder(INPUT_FILE_DIR)
target_filename = "Harmonogram.pdf"
INPUT_FILE_PATH = Path(INPUT_FILE_DIR).joinpath(target_filename)

tab1, tab2, tab3 = st.tabs([
    "📁 Wgraj plik",
    "🔗 Link",
    "📋 Wyszukiwarka"
])
if st.session_state.step == 1:
    api_processor = ApiProcessor(file_service)
    with tab1:
        uploaded_file = st.file_uploader(f"Wgraj plik z harmonogramem w PDF.", type=["pdf"])

        if uploaded_file:
            file_service.save_file(INPUT_FILE_PATH, uploaded_file)
            st.session_state.step = 2
            st.success("Plik wgrany ✔️")

    with tab2:
        url = st.text_input("Link:", value="")
        if st.button("📥 Pobierz plik"):
            if not url:
                st.error("Podaj link")
                st.stop()

            try:
                api_processor.get_file_from_url(url, INPUT_FILE_PATH)
                st.success(f"Pobrano plik ✔️")
                st.session_state.step = 2
            except Exception as e:
                st.error(f"Błąd pobierania: {e}")

    with tab3:
        residents, family, building_type, segregating, community = api_processor.get_selector_fields()

        for key in ["residents_value", "family_value", "segregating_value", "building_type_value", "community_value",
                    "city_value", "street_value", "schedule_data"]:
            if key not in st.session_state:
                st.session_state[key] = ""

        col1, col2, col3, col4 = st.columns(4)

        # TODO: dodaj opcje do requestu
        # TODO: pokazywanie opcji w zależności od opcji
        with col1:
            _, st.session_state.residents_value = st.selectbox("Obszar zabudowy:", residents, format_func=lambda i: i[0])
            st.write("Value:", st.session_state.residents_value)

        with col2:
            _, st.session_state.family_value = st.selectbox("Rodzaj zabudowy:", family, format_func=lambda i: i[0])
            st.write("Value:", st.session_state.family_value)

        with col3:
            _, st.session_state.segregating_value = st.selectbox("Segregacja:", segregating, format_func=lambda i: i[0])
            st.write("Value:", st.session_state.segregating_value)

        with col4:
            _, st.session_state.building_type_value = st.selectbox("Typ zabudowy:", building_type,
                                                                   format_func=lambda i: i[0])
            st.write("Value:", st.session_state.building_type_value)

        with col1:
            _, st.session_state.community_value = st.selectbox("Gmina:", community, format_func=lambda i: i[0])
            st.write("Value:", st.session_state.community_value)

        with col2:
            if st.session_state.community_value:
                cities = api_processor.get_city_data(st.session_state.community_value)
                # _, st.session_state.city_value = st.selectbox("Miejscowość:", [("", None)] + [x.to_selector() for x in cities], format_func=lambda i: i[0])
                _, st.session_state.city_value = st.selectbox("Miejscowość:", prepare_selector_from_api_response(cities), format_func=lambda i: i[0])
                st.write("Value:", st.session_state.city_value)

        with col3:
            if st.session_state.community_value and st.session_state.city_value:
                streets = api_processor.get_street_data(st.session_state.city_value)
                # _, st.session_state.street_value = st.selectbox("Ulica:", [("", None)] + [x.to_selector() for x in streets],
                _, st.session_state.street_value = st.selectbox("Ulica:", prepare_selector_from_api_response(streets),
                                               format_func=lambda i: i[0])
                st.write("Value:", st.session_state.street_value)

        # TODO: bład jak nie ma
        if st.session_state.community_value and st.session_state.city_value:
            if st.button("Szukaj"):
                st.session_state.schedule_data = api_processor.get_schedule_data(st.session_state.community_value, st.session_state.city_value, st.session_state.street_value)
                if st.session_state.schedule_data.filename:
                    st.success(f"{st.session_state.schedule_data.msg}: {st.session_state.schedule_data.filename}")
                    api_processor.get_schedule_file(st.session_state.schedule_data.pdf_path, INPUT_FILE_PATH)
                    st.success(f"Pobrano harmonogram")
                    st.session_state.step = 2
                else:
                    st.error(st.session_state.schedule_data.msg)

        #TODO: przycisk do pobierania


# ============================================================
# KROK 2 – przetwarzanie
# ============================================================
if st.session_state.step == 2 and file_service.file_exists(INPUT_FILE_PATH):
    if st.button("Rozpocznij OCR"):
        st.info("⏳ Przetwarzanie w toku...")

        year = process_schedule_to_csv(BASE_DIR, INPUT_FILE_DIR / target_filename)
        print(f"YEAR: {year}")

        st.success("Przetwarzanie zakończone!")
        st.session_state.step = 3
        st.rerun()  # odśwież ekran, aby wykryć nowy plik

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
    #TODO: inna ścieżka do trzymania .ics
    ICS_PATH = BASE_DIR / "src"
    ics_file = file_service.find_by_pattern(ICS_PATH, "*.ics")[0].name  # TODO: co jak nie ma ?

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


#TODO: wyczyść pliki tymczasowe

# ============================================================
# Inne Elementy
# ============================================================
if st.button("Do początku"):
    st.session_state.step = 1
    st.rerun()
