from pathlib import Path

import pandas as pd
from pandas import DataFrame

from garbage.services.FileService import FileService


class CsvProcessing:
    TMP_SUBFOLDER = Path("csv")
    OUTPUT_FILE_NAME = "harmonogram.csv"

    def __init__(self, file_service: FileService, headers_file, body_file) -> None:
        self.file_service = file_service
        self.headers_file = headers_file
        self.body_file = body_file
        self.dir = self.file_service.temporary_directory / self.TMP_SUBFOLDER
        self.file_service.create_folder(self.dir)

    def process(self):
        headers: DataFrame = self._process_headers()
        data: DataFrame = self._read_data()
        full = pd.concat([headers, data])
        full.to_csv(self.dir / self.OUTPUT_FILE_NAME, index=False, header=False, sep=";")
        return self.dir / self.OUTPUT_FILE_NAME

    def _read_data(self):
        df: DataFrame = pd.read_csv(self.body_file, header=None, dtype=str)
        return df

    def _process_headers(self):
        df = pd.read_csv(self.headers_file, header=None)
        df_filled = df.fillna("").astype(str)
        aggr = df_filled.agg(' '.join, axis=0)
        result = aggr.map(lambda x: x.strip())
        return pd.DataFrame([result])
