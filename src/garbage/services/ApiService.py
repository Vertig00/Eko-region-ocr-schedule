import requests
from requests import Response


class ApiService:

    BASE_URL = "https://eko-region.pl"

    # TODO: czy 2 api_caller potrzebne ?
    def _api_caller(self, request_type: str, url, data=None) -> Response | None:
        headers = self._set_headers()

        # TODO: obsługa błędów > 400
        response = self._make_api_call(request_type, url, headers, data)
        if response.status_code == 200:
            return response
        else:
            print(f"{response.status_code}: {response.text}")

    def _api_caller_file(self, request_type: str, url, data=None, stream=True) -> Response | None:
        response = self._make_api_call(request_type, url, headers=None, data=data, stream=stream)
        if response.status_code == 200:
            return response
        else:
            print(f"{response.status_code}: {response.text}")

    def _make_api_call(self, request_type: str, url, headers=None, data=None, stream=False):
        match request_type:
            case "GET":
                return requests.get(url, data=data, headers=headers, stream=stream)
            case "POST":
                return requests.post(url, data=data, headers=headers)
            case "PUT":
                return requests.put(url, data=data, headers=headers)
            case "DELETE":
                return requests.delete(url, data=data, headers=headers)
            case _:
                raise Exception("Non defined request type")

    def _set_headers(self):
        return {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "pl-PL,pl;q=0.9,en-PL;q=0.8,en;q=0.7,da-PL;q=0.6,da;q=0.5,en-US;q=0.4",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",  # obligatory
            "x-requested-with": "XMLHttpRequest"  # obligatory
        }

    def make_api_call(self, request_type, url):
        return self._api_caller(request_type.upper(),
                                url,
                                )

    def get_community(self):
        return self._api_caller("GET", f"{self.BASE_URL}/harmonogram-odbioru-odpadow/")

    def get_cities(self, url):
        return self._api_caller("GET", url)

    def get_streets(self, url):
        return self._api_caller("GET", url)

    def get_file(self, url):
        return self._api_caller_file(request_type="GET",
                                   url=url,
                                   stream=True
                                   )
