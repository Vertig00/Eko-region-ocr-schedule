import logging

from bs4 import BeautifulSoup

from garbage.model.EkoRegion import ResponseData
from garbage.services.ApiService import ApiService
from garbage.services.Decorators import first_empty_element
from garbage.services.FileService import FileService


class ApiProcessor:

    api = ApiService()

    def __init__(self, file_service: FileService):
        self.file_service = file_service

    @first_empty_element
    def get_community(self):
        response = self.api.get_community().text
        soup = BeautifulSoup(response, "html.parser")
        data = { elem.text: elem.get("href") for elem in soup.select('p.elementor-heading-title a') }
        return data

    @first_empty_element
    def get_city(self, city_url):
        api_response = self.api.get_cities(city_url).text
        soup = BeautifulSoup(api_response, "html.parser")

        for selector, processor in [
            ("div.cities_list > div", self._process_city),
            ("div.streets_list > div", self._process_streets),
        ]:
            elements = soup.select(selector)
            if elements:
                return processor(elements)

    @first_empty_element
    def get_streets(self, url):
        api_response = self.api.get_streets(url).text
        soup = BeautifulSoup(api_response, "html.parser")
        selector = soup.select("div.streets_list > div")
        return self._process_streets(selector)

    def get_file_from_url(self, url, destination_path):
        try:
            response = self.api.get_file(url)
            response.raise_for_status()
            self.file_service.save_downloaded_file(destination_path, response)
        except Exception as e:
            logging.error("Błąd pobierania: {}".format(e))

    def _process_city(self, selector):
        response = []
        for element in selector:
            city_name = element.find('strong').get_text(strip=True)

            streets = element.select_one("a.see-streets")
            if streets:
                response.append(ResponseData(name=city_name, inhabited=None, uninhabited=None, has_street=True,
                              streets_link=streets.get("href")))
            else:
                inhabited = None
                uninhabited = None
                for a in element.select('a.see-file'):
                    text = a.get_text(strip=True).lower()
                    href = a.get('href')
                    match text:
                        case t if 'niezamieszkałe' in t:
                            uninhabited = href
                        case t if 'zamieszkałe' in t:
                            inhabited = href
                response.append(ResponseData(name=city_name, inhabited=inhabited, uninhabited=uninhabited))
        return response

    def _process_streets(self, selector):
        response = []
        for element in selector:
            city_name = element.find('strong').get_text(strip=True)

            inhabited, uninhabited = None, None
            for a in element.select('a.see-file'):
                text = a.get_text(strip=True).lower()
                href = a.get('href')
                match text:
                    case t if 'niezamieszkałe' in t:
                        uninhabited = href
                    case t if 'zamieszkałe' in t:
                        inhabited = href
            response.append(ResponseData(name=city_name, inhabited=inhabited, uninhabited=uninhabited))
        return response
