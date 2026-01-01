import logging
import re
from itertools import islice

import dateparser

from garbage.model.Garbage import GarbageRegistry
from garbage.model.GarbageCollect import GarbageCollect

logger = logging.getLogger(__name__)

class DataProcessor:

    def map_garbage_data(self, data: list[dict[str, str]], year) -> list[GarbageCollect]:
        garbage = []
        for row in data:
            month = row["Miesiąc"]
            for key in islice(row, 1, None):
                garbage_type = self._create_garbage_by_type(key)
                days = row[key]
                splited_cell = self._split_row(days)
                if splited_cell:
                    day_list, additional_info = self._map_days(splited_cell)
                    if day_list:
                        for day in day_list:
                            date = f"{day} {month} {year}"
                            result_additional_info = self._resolve_additional_info(day, additional_info)
                            parsed_date = self._parse_date(date)
                            if parsed_date is None:
                                logger.warning(f"nie można sparsować {date} do daty, pomiń ten wpis.")
                                continue
                            event = GarbageCollect(garbage_type, self._parse_date(date), result_additional_info)
                            garbage.append(event)
                            logger.info(f"EVENT -> {event}")
        return garbage

    def _parse_date(self, date: str):
        return dateparser.parse(date)

    def _split_row(self, row: str) -> list[str] | None:
        false_i = " 1 "
        if row:
            if false_i in row:
                row = row.replace(false_i, " i ")
            pattern = r"[,\s]+"
            return re.split(pattern, row.strip())
        return None

    def _map_days(self, days: list[str]):
        single_split_letter = ["i", "j", "|"]
        data = []
        additional_info = []
        for day in days:
            logger.debug(f"({day})")
            match day:
                case int():
                    logger.debug(f"({day}) -> liczba")
                    # jeśli liczba z zakresu kalendarza
                    if self._day_calendar_boundries(day):
                        logger.debug(f"({day}) -> liczba z kalendarza")
                        data.append(day)
                    else:
                        # jeśli większa, sprawdź fałszywe 1
                        result = self._resolve_numbers(day)
                        data += result
                        logger.debug(f"({day}) -> po detekcji {result}")
                case str():
                    # jeśli to znak separacji
                    if day in single_split_letter:
                        logger.debug(f"({day}) -> znak podziału")
                        continue
                    # jeśli string posiada cyfrę
                    if re.search(r"\d", day):
                        logger.debug(f"({day}) -> posiada cyfrę")
                        # jeśli w stringu jest * -> prawdopodobnie data z komentarzem
                        if re.search(r"\*", day):
                            logger.debug(f"({day}) -> posiada *")
                            only_number = re.sub(r"[^\W\d_]|[*]", "", day)
                            data.append(only_number)
                            additional_info.append(day)
                        else:
                            logger.debug(f"({day}) -> cyfra ze stringiem")
                            number = re.sub(r"[^\W\d_]|[*]", "", day)
                            result = self._resolve_numbers(number)
                            data += result
                            logger.debug(f"({day}) -> detekcja {result} dla {number}")
                    else:
                        # sam tekst to dodatkowe info
                        logger.debug(f"({day}) -> komentarz")
                        additional_info.append(day)

        return data, additional_info

    def _resolve_additional_info(self, day: int, additional_info: list[str] | None):
        text = ""
        if additional_info:
            for entry in additional_info:
                if "*" in entry:
                    if day.__str__() in entry:
                        text += f"* -> możliwa zmiana daty\n"
                else:
                    text += entry

        return text if text else None



    def _resolve_numbers(self, number: str | int):
        number = int(number)
        if self._day_calendar_boundries(number):
            logger.debug(f"RESOLVE ({number}) -> liczba z kalendarza")
            return [number]
        else:
            list_of_single = [int(ch) for ch in number.__str__()]
            possible_ok = []
            for idx, value in enumerate(list_of_single[1:], start=1):
                logger.debug(f"RESOLVE ({number}) -> IDX:{idx}, VALUE:{value}")
                if value == 1:
                    temp = list_of_single.copy()
                    temp[idx] = "i"
                    check_value = "".join(x.__str__() for x in temp).split("i")
                    check_value = [int(x) for x in check_value if x]
                    logger.debug(f"RESOLVE ({number}) -> {check_value}")
                    is_consecutive = all(a < b for a, b in zip(check_value, check_value[1:]))
                    if is_consecutive:
                        logger.debug(f"RESOLVE ({number})({check_value}) -> w kolejności")
                        is_min_week_difference = all(a+7 < b for a, b in zip(check_value, check_value[1:]))
                        if is_min_week_difference:
                            logger.debug(f"RESOLVE ({number})({check_value}) -> różnica tygodnia")
                            possible_ok = check_value
            return possible_ok


    def _day_calendar_boundries(self, number) -> bool:
        return 1 <= number <= 31

    def _create_garbage_by_type(self, garbage_type: str):
        garbage_type = garbage_type.lower().strip()

        for cls in GarbageRegistry.registry:
            patterns = getattr(cls, "match_patterns", [])

            if any(p.lower() in garbage_type for p in patterns):
                return cls()

        raise ValueError(f"Unknown garbage type: {garbage_type!r}")
