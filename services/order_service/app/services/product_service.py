import requests
from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError

def _build_url(path: str) -> str:
    base = settings.CATALOGUE_SERVICE_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"

def _auth_headers(access_token: str | None) -> dict:
    if not access_token:
        return {}
    token = access_token.strip()
    if token.lower().startswith("bearer "):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}


def get_product(product_id: str, access_token: str | None = None) -> dict:
    url = _build_url(f"products/{product_id}/")
    headers = _auth_headers(access_token)
    try:
        response = requests.get(url, timeout=5, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("catalogue-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("catalogue-service n'a pas répondu à temps.") from e

    if response.status_code == 404:
        raise NotFound("Le produit n'existe pas.")
    if response.status_code != 200:
        raise ValidationError("Une erreur est survenue lors de la récupération du produit.")

    return response.json()

def get_products(access_token: str | None = None) -> dict:
    url = _build_url(f"/products/")
    headers = _auth_headers(access_token)
    try:
        response = requests.get(url, timeout=5, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("catalogue-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("catalogue-service n'a pas répondu à temps.") from e

    if response.status_code == 404:
        raise NotFound("Le produit n'existe pas.")
    if response.status_code != 200:
        raise ValidationError("Une erreur est survenue lors de la récupération du produit.")

    return response.json()


def get_products_bulk(product_ids, access_token=None):
    url = _build_url("products/bulk/")
    headers = _auth_headers(access_token)

    response = requests.post(
        url,
        json={"ids": product_ids},
        timeout=2,
        headers=headers
    )

    if response.status_code != 200:
        raise ValidationError("Erreur récupération produits")

    return response.json().get("results", {})