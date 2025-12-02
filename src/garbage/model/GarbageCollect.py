from datetime import datetime

from garbage.model.Garbage import Garbage


class GarbageCollect:
    def __init__(self, garbage_type, date, additional_info):
        self.garbage_type: Garbage = garbage_type
        self.date: datetime = date
        self.additional_info = additional_info

    def __str__(self):
        return f"{self.garbage_type.name} {self.date} {self.additional_info}"