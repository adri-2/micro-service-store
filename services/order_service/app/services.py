import requests
from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError

def _build_url(path: str) -> str:
    base = settings.CATALOGUE_SERVICE_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"

def get_product(product_id: str) -> dict:
    url = _build_url(f"products/{product_id}/")
    try:
        response = requests.get(url,timeout=5)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("catalogue-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("catalogue-service n'a pas répondu à temps.") from e

    if response.status_code == 404:
        raise NotFound("Le produit n'existe pas.")
    if response.status_code != 200:
        raise ValidationError("Une erreur est survenue lors de la récupération du produit.")

    return response.json()

def get_products() -> dict:
    url = _build_url(f"/products/")
    try:
        response = requests.get(url,timeout=5)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("catalogue-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("catalogue-service n'a pas répondu à temps.") from e

    if response.status_code == 404:
        raise NotFound("Le produit n'existe pas.")
    if response.status_code != 200:
        raise ValidationError("Une erreur est survenue lors de la récupération du produit.")

    return response.json()