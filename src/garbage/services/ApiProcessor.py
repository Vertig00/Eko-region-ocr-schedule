import logging

from bs4 import BeautifulSoup

from garbage.model.EkoRegion import City, Street, ScheduleInfo
from garbage.services.ApiService import ApiService
from garbage.services.Decorators import first_empty_element
from garbage.services.FileService import FileService


class ApiProcessor:

    api = ApiService()

    def __init__(self, file_service: FileService):
        self.file_service = file_service

    def get_selector_fields(self):
        response = self.api.get_page().text
        soup = BeautifulSoup(response, "html.parser")

        @first_empty_element
        def find_selector_values(class_element):
            selector = soup.find("select", {"class": class_element})
            return [(x.get_text(strip=True), x["value"]) for x in selector.find_all("option") if
                                   x["value"]]

        residents = find_selector_values("residents-select")
        family = find_selector_values("family-select")
        building_type = find_selector_values("high-select")
        segregating = find_selector_values("segregating-select")
        community = find_selector_values("communities-select")

        return residents, family, building_type, segregating, community

    def get_city_data(self, community_id):
        response = self.api.get_city(community_id)
        data = [City(community_id=x["CommunityID"], id=x["ID"], title=x["Title"]) for x in response.json()]
        return data

    def get_street_data(self, city_id):
        response = self.api.get_street(city_id)
        data = [Street(city_id=x["CityID"], id=x["ID"], title=x["Title"]) for x in response.json()]
        return data

    def get_schedule_data(self, community_id, city_id, street_id):
        response = self.api.get_schedule(community_id, city_id, street_id).json()
        data = ScheduleInfo(filename=response["filename"], msg=response["msg"], pdf_path=response["pdf"])
        return data

    #TODO: dodaj moze dekorator dla nauki
    def get_schedule_file(self, pdf_location, destination_path):
        try:
            response = self.api.get_schedule_file(pdf_location)
            response.raise_for_status()
            self.file_service.save_downloaded_file(destination_path, response)
        except Exception as e:
            logging.error("Błąd pobierania: {}".format(e))

    def get_file_from_url(self, url, destination_path):
        try:
            response = self.api.get_file(url)
            response.raise_for_status()
            self.file_service.save_downloaded_file(destination_path, response)
        except Exception as e:
            logging.error("Błąd pobierania: {}".format(e))
