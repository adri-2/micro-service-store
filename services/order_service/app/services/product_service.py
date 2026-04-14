import requests
import hashlib
from django.core.cache import cache
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


def _token_scope(access_token: str | None) -> str:
    if not access_token:
        return "anon"
    token = access_token.strip()
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def _cache_key(prefix: str, suffix: str, access_token: str | None = None) -> str:
    scope = _token_scope(access_token)
    return f"ext-catalogue:{prefix}:{suffix}:{scope}"


PRODUCT_CACHE_TTL = getattr(settings, "PRODUCT_SERVICE_CACHE_TTL", 60 * 5)

def get_product(product_id: str, access_token: str | None = None) -> dict:
    cache_key = _cache_key("product", str(product_id), access_token)
    
    # 1. Tentative de lecture du cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    url = _build_url(f"products/{product_id}/")
    headers = _auth_headers(access_token)
    
    try:
        response = requests.get(url, timeout=5, headers=headers)
        
        # 2. Vérification des erreurs AVANT le return
        if response.status_code == 404:
            raise NotFound(f"Produit {product_id} introuvable.")
        if response.status_code != 200:
            raise ValidationError("Erreur du service catalogue.")

        product_data = response.json()

        # 3. Mise en cache uniquement si le résultat est valide
        cache.set(cache_key, product_data, timeout=PRODUCT_CACHE_TTL)
        return product_data

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise ValidationError("Le service catalogue est injoignable ou trop lent.") from e



def get_products(access_token: str | None = None) -> dict:
    cache_key = _cache_key("products", "all", access_token)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
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

    data = response.json()
    
    cache.set(cache_key,data,timeout=PRODUCT_CACHE_TTL)
    
    return data


def get_products_bulk(product_ids, access_token=None):
    results = {}
    missing_ids = []
    unique_product_ids = sorted({str(pid) for pid in product_ids})
    
    for pid in unique_product_ids:
        cache_key = _cache_key("product", pid, access_token)
        cached = cache.get(cache_key)
        if cached is not None:
            results[pid] = cached
        else:
            missing_ids.append(pid)    

    if missing_ids:    
        url = _build_url("products/bulk/")
        headers = _auth_headers(access_token)

        try:
            response = requests.post(
                url,
                json={"ids": missing_ids},
                timeout=5,
                headers=headers
            )
        except requests.exceptions.ConnectionError as e:
            raise ValidationError("catalogue-service est inaccessible.") from e
        except requests.exceptions.Timeout as e:
            raise ValidationError("catalogue-service n'a pas répondu à temps.") from e

        if response.status_code != 200:
            raise ValidationError("Erreur récupération produits")

        data = response.json().get("results", {})
        
        for pid, product in data.items():
            cache.set(
                _cache_key("product", str(pid), access_token),
                product,
                timeout=PRODUCT_CACHE_TTL,
            )
            results[pid] = product

    return results