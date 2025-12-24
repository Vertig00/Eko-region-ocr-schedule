import os
from pathlib import Path

import pandas as pd
import streamlit as st

from garbage.services.ApiProcessor import ApiProcessor
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

@st.cache_data
def get_community_cached():
    return api_processor.get_community()

def get_cities_cached(community_url):
    key = f"cities_{community_url}"
    if key not in st.session_state:
        with st.spinner(f"Pobieranie listy miejscowości..."):
            st.session_state[key] = api_processor.get_city(community_url)
    return st.session_state[key]

def get_streets_cached(city_url):
    key = f"streets_{city_url}"
    if key not in st.session_state:
        with st.spinner(f"Pobieranie ulic..."):
            st.session_state[key] = api_processor.get_streets(city_url)
    return st.session_state[key]

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
    community = get_community_cached()
    with tab1:
        uploaded_file = st.file_uploader(f"Wgraj plik z harmonogramem w PDF.", type=["pdf"])

        if uploaded_file:
            file_service.save_file(INPUT_FILE_PATH, uploaded_file)
            st.session_state.step = 2
            st.success("Plik wgrany ✔️")

    with tab2:
        st.markdown("Wklej link do pliku z harmonogramem, który można znaleźć na stronie **[Eko-Region](https://eko-region.pl/harmonogram-odbioru-odpadow/)**")
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

    with (tab3):
        # --- INICJALIZACJA SESSION STATE ---
        for key in ["community_value", "city_value", "street_value", "habitant_value", "download_url", "prev_community",
                    "prev_city"]:
            if key not in st.session_state:
                st.session_state[key] = None

        st.selectbox(
            "Gmina:",
            options=list(community.keys()),
            key="community_value"
        )

        community_url = community.get(st.session_state.community_value)

        # --- RESET zależnych selectboxów przy zmianie gminy ---
        if st.session_state.get("prev_community") != st.session_state.community_value:
            st.session_state.city_value = None
            st.session_state.street_value = None
            st.session_state.habitant_value = None
            st.session_state.download_url = None
            st.session_state.prev_community = st.session_state.community_value

        # --- SELECTBOX MIASTO ---
        if community_url:
            cities = get_cities_cached(community_url)
            st.selectbox(
                "Miejscowość:",
                options=cities,
                format_func=lambda i: i.name if i else "",
                key="city_value"
            )

            city = st.session_state.city_value

            # --- RESET zależnych selectboxów przy zmianie miasta ---
            if st.session_state.get("prev_city") != city:
                st.session_state.street_value = None
                st.session_state.habitant_value = None
                st.session_state.download_url = None
                st.session_state.prev_city = city

        # --- SELECTBOX ULICA / WARTOŚĆ ZALEŻNA ---
        target_obj = None
        if st.session_state.city_value:
            if st.session_state.city_value.has_street:
                streets = get_streets_cached(st.session_state.city_value.streets_link)
                st.selectbox(
                    "Ulica:",
                    options=streets,
                    format_func=lambda i: i.name if i else "",
                    key="street_value"
                )
                target_obj = st.session_state.street_value
            else:
                target_obj = st.session_state.city_value

        # --- SELECTBOX TYP NIERUCHOMOŚCI ---
        if target_obj:
            st.selectbox(
                "Rodzaj nieruchomości:",
                ["Zamieszkałe", "Niezamieszkałe"],
                key="habitant_value"
            )

            # --- DOWNLOAD URL ---
            if st.session_state.habitant_value == "Zamieszkałe":
                st.session_state.download_url = getattr(target_obj, "inhabited", None)
            elif st.session_state.habitant_value == "Niezamieszkałe":
                st.session_state.download_url = getattr(target_obj, "uninhabited", None)
            else:
                st.session_state.download_url = None

            if st.session_state.habitant_value:
                if st.session_state.download_url:
                    st.success("Znaleziono harmonogram.")
                    st.write("URL do pobrania:", st.session_state.download_url)
                else:
                    st.error("Brak harmonogramu dla podanych parametrów.")

        # --- PRZYCISK POBIERANIA ---
        if st.session_state.download_url:
            name = st.session_state.download_url.split("/")[-1]
            if st.button(f"Pobierz: {name}"):
                try:
                    api_processor.get_file_from_url(st.session_state.download_url, INPUT_FILE_PATH)
                    st.success("Pobrano plik ✔️")
                    st.session_state.step = 2
                except Exception as e:
                    st.error(f"Błąd pobierania: {e}")

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
