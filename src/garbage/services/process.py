from garbage.services.CalendarService import CalendarService
from garbage.services.CsvProcessing import CsvProcessing
from garbage.services.DataProcessor import DataProcessor
from garbage.services.FileService import FileService
from garbage.services.ImageProcessingService import ImageProcessingService
from garbage.services.OcrService import OcrService
from garbage.services.PdfService import PdfService

def process_schedule(base_dir, pdf_path):
    file_service = FileService(base_dir)
    year = PdfService(pdf_path).detect_year()
    header_img, data_img = ImageProcessingService(file_service, pdf_path).process_waste_pdf()

    header, data = OcrService(file_service, header_img, data_img).process()

    schedule_csv = CsvProcessing(file_service, header, data).process()

    data_from_csv = file_service.read_csv(schedule_csv)
    schedule = DataProcessor().map_garbage_data(data_from_csv, year)
    CalendarService(file_service, schedule).prepare_calendar()

def process_schedule_to_csv(base_dir, pdf_path):
    file_service = FileService(base_dir)
    year = PdfService(pdf_path).detect_year()
    header_img, data_img = ImageProcessingService(file_service, pdf_path).process_waste_pdf()
    header, data = OcrService(file_service, header_img, data_img).process()
    CsvProcessing(file_service, header, data).process()
    return year

def process_from_csv(base_dir, csv_path, year: int):
    file_service = FileService(base_dir)
    data_from_csv = file_service.read_csv(csv_path)
    schedule = DataProcessor().map_garbage_data(data_from_csv, year)
    CalendarService(file_service, schedule).prepare_calendar()

# TODO: maybe refactor/move somewhere
def open_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        return f.read()

def detect_multipage(pdf_path):
    return PdfService(pdf_path).detect_multipage()

def save_selected_page(pdf_path, page_number):
    PdfService(pdf_path).save_selected_page(page_number)