import requests


class ApiService:

    BASE_URL = "https://eko-region.pl"

    def _api_caller(self, request_type: str, url, data=None) -> requests.Response:
        headers = self._set_headers()

        # TODO: obsługa błędów > 400
        response = self._make_api_call(request_type, url, headers, data)
        if response.status_code == 200:
            return response
        else:
            print(f"{response.status_code}: {response.text}")

    def _api_caller_file(self, request_type: str, url, data=None, stream=True) -> requests.Response:
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

    def get_page(self):
        return self._api_caller("GET",
                                self.BASE_URL,
                                )

    def get_city(self, community_id):
        return self._api_caller("POST",
                                f"{self.BASE_URL}/scheduler/city",
                                {"communityId": community_id}
                                )

    def get_street(self, city_id):
        return self._api_caller("POST",
                                f"{self.BASE_URL}/scheduler/street",
                                {"cityId": city_id}
                                )

    def get_schedule(self, community_id, city_id, street_id):
        return self._api_caller("POST",
                                f"{self.BASE_URL}/scheduler/get-scheduler",
                                {
                                    "cityId": city_id,
                                    "streetId": street_id,
                                    "communityId": community_id,
                                    "residentsVal": "Residents",
                                    "familyVal": "OneFamily",
                                    "highVal": "",
                                    "segregationVal": "Segregating"
                                })

    def get_schedule_file(self, pdf_location):
        return self._make_api_call(request_type="GET",
                                   url=f"{self.BASE_URL}{pdf_location}",
                                   stream=True
                                   )
