import requests


class ApiService:

    def _api_caller(self, request_type: str, url, data=None) -> requests.Response:
        headers = self._set_headers()

        response = self._make_api_call(request_type, url, headers, data)




        pass

    def _make_api_call(self, request_type: str, url, headers, data=None):
        match request_type:
            case "GET":
                return requests.get(url, data=data, headers=headers)
            case "POST":
                return requests.post(url, data=data, headers=headers)
            case "PUT":
                return requests.put(url, data=data, headers=headers)
            case "DELETE":
                return requests.delete(url, data=data, headers=headers)
            case _:
                raise Exception("Non defined request type")

    def _set_headers(self):
        pass

