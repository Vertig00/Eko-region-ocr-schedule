import argparse
import logging
from pathlib import Path
import logging.config

import yaml

from garbage.services.process import process_from_csv

logger = logging.getLogger(__name__)

def setup_logging():
    config_path = Path(__file__).parents[1] / "logging.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)


def main():
    setup_logging()
    from garbage.services.process import process_schedule
    BASE_DIR = Path(__file__).resolve().parents[1]  # przejście: main.py → garbage → src → projekt
    parser = argparse.ArgumentParser(description="Eko-region harmonogram")

    # standard czyli bez parametrów -> weź plik z resources
    sub = parser.add_subparsers(dest="command", required=False)

    # podaj własną ścieżkę pliku
    parser_own_file = sub.add_parser("file", help="Uruchom skrypt z własnym plikiem")
    parser_own_file.add_argument("--path", required=True, dest="Ścieżka do pliku z harmonogramem (.pdf).")

    # poprawienie CSV
    parser_csv = sub.add_parser("csv", help="Uruchom skrypt z poprawioną tabelą harmonogramu")
    parser_csv.add_argument("--path", required=True, dest="Ścieżka do pliku z CSV harmonogramu.")
    parser_csv.add_argument("--year", required=True, dest="Rok dla którego jest harmonogram.")

    args = parser.parse_args()

    if args.command == "file":
        process_schedule(BASE_DIR, args.path)
    if args.command == "csv":
        process_from_csv(BASE_DIR, args.path, args.year)
    else:
        # pdf_path = BASE_DIR / "resources" / "Pabianice-Gmina-7.pdf"
        pdf_path = BASE_DIR / "resources" / "brzeznio_10.pdf"
        # pdf_path = BASE_DIR / "resources" / "pabianice.pdf"
        process_schedule(BASE_DIR, pdf_path)


#TODO: add debug mode
#TODO: move this to subfile -> here only invoke 1 method
if __name__ == '__main__':
    main()