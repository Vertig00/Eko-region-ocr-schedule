import logging

from bs4 import BeautifulSoup

from garbage.model.EkoRegion import City, Street, ScheduleInfo
from garbage.services.ApiService import ApiService


class ApiProcessor:

    api = ApiService()

    def get_selector_fields(self):
        response = self.api.get_page().text
        soup = BeautifulSoup(response, "html.parser")
        residents_select = soup.find("select", {"class": "residents-select"})
        family_select = soup.find("select", {"class": "family-select"})
        building_type_select = soup.find("select", {"class": "high-select"})
        segregating_select = soup.find("select", {"class": "segregating-select"})
        community_select = soup.find("select", {"class": "communities-select"})
        residents = [("", None)] + [(x.get_text(strip=True), x["value"]) for x in residents_select.find_all("option") if x["value"]]
        family = [("", None)] + [(x.get_text(strip=True), x["value"]) for x in family_select.find_all("option") if x["value"]]
        building_type = [("", None)] + [(x.get_text(strip=True), x["value"]) for x in building_type_select.find_all("option") if x["value"]]
        segregating = [("", None)] + [(x.get_text(strip=True), x["value"]) for x in segregating_select.find_all("option") if x["value"]]
        community = [("", None)] + [(x.get_text(strip=True), x["value"]) for x in community_select.find_all("option") if x["value"]]
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

    def get_schedule_file(self, pdf_location, destination_path):
        try:
            response = self.api.get_schedule_file(pdf_location)
            response.raise_for_status()
            with open(destination_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            logging.error("Błąd pobierania: {}".format(e))
