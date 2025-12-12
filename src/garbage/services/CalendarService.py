import datetime
import uuid
from datetime import timedelta

from icalendar import Calendar, Event

from garbage.model.GarbageCollect import GarbageCollect
from garbage.services.FileService import FileService


class CalendarService:

    _output_file_template = "Eko-Region-%s.ics"

    def __init__(self, file_service: FileService, schedule: list[GarbageCollect]):
        self.file_service: FileService = file_service
        self.calendar = Calendar()
        self.schedule = schedule

    def prepare_calendar(self):
        self._define_calendar_base_info()

        for entry in self.schedule:
            event = self._create_event(entry)
            self.calendar.add_component(event)

        year = self.schedule[0].date.year
        calendar_file_name = self._output_file_template % year
        self.file_service.save_ics(calendar_file_name, self.calendar)


    def _define_calendar_base_info(self):
        self.calendar.add("PRODID", "-//Vertig0//Harmonogram wywozu śmieci//PL")
        self.calendar.add("VERSION", "2.0")
        self.calendar.add("CALSCALE", "GREGORIAN")
        self.calendar.add("NAME", "Śmieci")
        self.calendar.add("DESCRIPTION", "Harmonogram wywozu śmieci")

    def _create_event(self, entry: GarbageCollect) -> Event:
        event = Event()
        event.add("UID", uuid.uuid4())
        event.add("SUMMARY", f"Śmieci {entry.garbage_type.name}")
        event.add("DESCRIPTION", entry.garbage_type.hash_id)
        event.add("DTSTART", entry.date.date())
        event.add("DTSTAMP", datetime.datetime.now())
        event.add("DTEND", (entry.date + timedelta(days=1)).date())
        event.add("COMMENT", entry.additional_info)
        event.add("COLOR", entry.garbage_type.color)
        event.add("TRANSP", "TRANSPARENT")
        event.add("STATUS", "CONFIRMED")
        return event
