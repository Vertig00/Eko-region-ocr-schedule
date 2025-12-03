from dataclasses import dataclass


@dataclass
class City:
    title: str
    community_id: str
    id: str

    def to_selector(self):
        return (self.title, self.id)

@dataclass
class ScheduleInfo:
    filename: int
    msg: str
    pdf_path: str

@dataclass
class Street:
    title: str
    city_id: str
    id: str

    def to_selector(self):
        return (self.title, self.id)