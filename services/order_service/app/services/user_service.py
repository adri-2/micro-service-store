import requests
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError


def _build_url(path:str) -> str:
    base = settings.ACCOUNT_SERVICE_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"

def _auth_headers(access_token:str | None) -> dict:
    if not access_token:
        return {}
    token = access_token.strip()
    if token.lower().startswith("bearer"):
        return {"Authorization":token}
    return {"Authorization":f"Bearer {token}"}

def get_user(user_id:str,access_token:str|None = None) -> dict:
    url = _build_url(f"user/me/{user_id}/")
    headers = _auth_headers(access_token)
    try:
        response = requests.get(url,timeout=5,headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("account-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("account-service n'a pas répondu à temps.") from e

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise NotFound("L'utilisateur n'existe pas.")
    if response.status_code != status.HTTP_200_OK:
        raise ValidationError("Une erreur est survenue lors de la récupération de l'utilisateur.")
    return response.json()


def get_customer(customer_id:str,access_token:str|None = None) -> dict:
    url = _build_url(f"customer/me/{customer_id}/")
    headers = _auth_headers(access_token)
    try:
        response = requests.get(url,timeout=5,headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("account-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("account-service n'a pas répondu à temps.") from e

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise NotFound("Le client n'existe pas.")
    if response.status_code != status.HTTP_200_OK:
        raise ValidationError("Une erreur est survenue lors de la récupération du client.")
    return response.json()


def get_users_bulk(user_ids:list[str], access_token:str|None = None) -> dict:
    if not user_ids:
        return {}

    url = _build_url("user/bulk/")
    headers = _auth_headers(access_token)
    try:
        response = requests.post(url, json={"ids": user_ids}, timeout=5, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("account-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("account-service n'a pas répondu à temps.") from e

    if response.status_code != status.HTTP_200_OK:
        raise ValidationError("Une erreur est survenue lors de la récupération des utilisateurs.")

    return response.json().get("results", {})


def get_customers_bulk(customer_ids:list[str], access_token:str|None = None) -> dict:
    if not customer_ids:
        return {}

    url = _build_url("customer/bulk/")
    headers = _auth_headers(access_token)
    try:
        response = requests.post(url, json={"ids": customer_ids}, timeout=5, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("account-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("account-service n'a pas répondu à temps.") from e

    if response.status_code != status.HTTP_200_OK:
        raise ValidationError("Une erreur est survenue lors de la récupération des clients.")

    return response.json().get("results", {})


    
