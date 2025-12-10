from dataclasses import dataclass

#TODO: to_selector interface
@dataclass(frozen=True)
class City:
    title: str
    community_id: str
    id: str

    def to_selector(self):
        return (self.title, self.id)

@dataclass(frozen=True)
class Street:
    title: str
    city_id: str
    id: str

    def to_selector(self):
        return (self.title, self.id)

@dataclass(frozen=True)
class ScheduleInfo:
    filename: str
    msg: str
    pdf_path: str
