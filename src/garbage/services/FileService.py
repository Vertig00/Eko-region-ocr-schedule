import csv
import glob
import os.path
import shutil
from pathlib import Path

import fitz
from PIL import Image
from icalendar import Calendar

class FileService:

    _temp_directory = Path("resources/tmp")

    def __init__(self, base_directory: Path):
        self.base_directory = base_directory
        self.temporary_directory = base_directory / self._temp_directory
        self.create_folder(self.temporary_directory)

    def __del__(self):
        #TODO: disable in debug mode
        if False:
            if self.temporary_directory.exists():
                shutil.rmtree(self.temporary_directory)


    def create_folder(self, folder_path: str | Path):
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)

    def save_ics(self, file_name, calendar: Calendar):
        with open(file_name, "wb") as ics:
            ics.write(calendar.to_ical())

    def save_csv(self, header, body, output_filename):
        with open(output_filename, mode='w', encoding="utf-8", newline='') as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(header)
            for row in body:
                writer.writerow(row.split(";"))

    def read_csv(self, filename):
        with open(filename, encoding="utf-8", newline='') as file:
            reader = csv.DictReader(file, delimiter=";")
            data = [row for row in reader]
            return data

    def open_pdf(self, filename):
        return fitz.open(filename)

    def open_image(self, filename):
        return Image.open(filename)

    def save_image(self, filename, image: Image):
        image.save(filename)

    def save_df_to_csv(self, filename, df, index=False, header=False):
        df.to_csv(filename, index=index, header=header)

    def save_file(self, path, data):
        with open(path, "wb") as f:
            f.write(data.getbuffer())

    def save_downloaded_file(self, path, data):
        with open(path, "wb") as f:
            for chunk in data.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    # TODO: obsługa błędów itp
    def find_by_pattern(self, folder, pattern):
        # if os.path.exists(folder):
        files = list(Path(folder).glob(pattern))
        return files

    def file_exists(self, filename):
        return Path(filename).exists()


