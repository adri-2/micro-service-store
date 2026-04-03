import requests


class ServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get(self, endpoint: str, params=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        if response.status_code >=400:
            raise Exception(f"Error {response.status_code}: {response.text}")
        return response.json()

    def post(self, endpoint: str, data=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, json=data)
        response.raise_for_status()
        if response.status_code >=400:
            raise Exception(f"Error {response.status_code}: {response.text}")
        return response.json()

    def put(self, endpoint: str, data=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.put(url, json=data)
        response.raise_for_status()
        if response.status_code >=400:
            raise Exception(f"Error {response.status_code}: {response.text}")
        return response.json()

    def delete(self, endpoint: str):
        url = f"{self.base_url}/{endpoint}"
        response = requests.delete(url)
        response.raise_for_status()
        if response.status_code >=400:
            raise Exception(f"Error {response.status_code}: {response.text}")
        return response.json()