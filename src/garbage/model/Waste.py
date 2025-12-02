class Waste:
    def __init__(self, garbage_type, date, additional_info):
        self.garbage_type = garbage_type
        self.date = date
        self.additional_info = additional_info

    def __str__(self):
        return f" {self.garbage_type} {self.date} {self.additional_info}"