"""
ÉTAPE 2 — Implémenter la couche de communication HTTP (services.py)
====================================================================

FICHIER À CRÉER:
    services/order_service/app/services.py


CONTEXTE:
---------
order_service doit appeler product_service de manière centralisée.
On NE MET PAS requests directement dans les views ou serializers.
On crée une couche "services.py" qui encapsule tous les appels réseau.

Avantages:
    - Code plus testable
    - Erreurs centralisées
    - Facile à changer d'URL ou de logique
    - Réutilisable depuis views, serializers, tasks, etc.


STRUCTURE DU FICHIER:
---------------------

import requests
from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError


# Utilitaire pour construire les URLs
def _build_url(path: str) -> str:
    # Récupérer CATALOGUE_SERVICE_URL depuis settings.py
    # Combiner avec le chemin fourni
    # Retourner l'URL complète
    pass


# Appel 1 : Récupérer un produit
def get_product(product_id: str) -> dict:
    # Appel HTTP: GET /products/{product_id}/
    # Retourne: dict du produit (name, price, stock, ...)
    # Erreurs:
    #   - 404: NotFound
    #   - Timeout: ValidationError
    #   - Autres: ValidationError
    pass


# Appel 2: Décrémenter le stock
def check_and_decrement_stock(product_id: str, quantity: int) -> dict:
    # Appel HTTP: POST /products/{product_id}/decrement-stock/
    # Body: {"quantity": quantity}
    # Retourne: dict du produit mis à jour
    # Erreurs:
    #   - 404: NotFound (produit inexistant)
    #   - 400: ValidationError (stock insuffisant ou quantity invalide)
    #   - Timeout: ValidationError
    #   - Autres: ValidationError
    pass


DÉTAIL DE CHAQUE FONCTION:
----------------------------

1. _build_url(path: str) -> str:
   
   Objectif: Construire une URL valide et cohérente.
   
   Entrée: path = "products/uuid/"
   Sortie: "http://product-service:8000/products/uuid/"
   
   Implémentation:
   - Récupérer settings.CATALOGUE_SERVICE_URL
   - Enlever le "/" à la fin de l'URL (s'il existe)
   - Enlever le "/" au début du path (s'il existe)
   - Combiner avec "/"
   - Retourner


2. get_product(product_id: str) -> dict:
   
   Objectif: Récupérer les infos d'un produit via HTTP.
   
   Entrée: product_id = "f47c3f5a-1234-5678-abcd-ef1234567890"
   
   Étapes:
   a) Construire l'URL: _build_url(f"products/{product_id}/")
   b) Faire un GET avec timeout=5
   c) Gérer les exceptions réseau:
      - requests.exceptions.ConnectionError → ValidationError()
      - requests.exceptions.Timeout → ValidationError()
   d) Vérifier le status_code:
      - 404 → NotFound()
      - 200 → retourner response.json()
      - Autres → ValidationError()
   
   Retour: {"id": "...", "name": "...", "price": "...", "stock": ...}


3. check_and_decrement_stock(product_id: str, quantity: int) -> dict:
   
   Objectif: Réserver le stock (appel product_service).
   
   Entrée: product_id = "uuid", quantity = 5
   
   Étapes:
   a) Construire l'URL: _build_url(f"products/{product_id}/decrement-stock/")
   b) Faire un POST avec json={"quantity": quantity} et timeout=5
   c) Gérer les exceptions réseau (identique à get_product)
   d) Vérifier le status_code:
      - 404 → NotFound()
      - 400 → ValidationError() (stock insuffisant ou qty invalide)
      - 200 → retourner response.json()
      - Autres → ValidationError()
   
   Retour: {"id": "...", "name": "...", "stock": ... (décrementé)}


GESTION DES EXCEPTIONS:
------------------------

Toutes les exceptions réseau doivent être traduites en exceptions DRF:

requests.exceptions.ConnectionError
    → raise ValidationError("catalogue-service est inaccessible.")

requests.exceptions.Timeout
    → raise ValidationError("catalogue-service n'a pas répondu à temps.")

response.status_code == 404
    → raise NotFound("Produit introuvable.")

response.status_code == 400
    → raise ValidationError(response.json())  # passer la réponse du service

response.status_code non-200
    → raise ValidationError(f"Erreur catalogue-service: {response.status_code}")


POINTS D'ATTENTION:
--------------------

⚠ TIMEOUT:
    Toujours mettre timeout=5 (ou une valeur appropriée).
    Sans timeout, si product_service ne répond pas, order_service gèle.

⚠ TRADUCTION DES ERREURS:
    Les exceptions requests doivent devenir des exceptions DRF
    (NotFound, ValidationError) pour que le serializer les capture.

⚠ JSON:
    Utiliser json={"quantity": quantity} (pas data=...).
    requests convertira automatiquement en content-type: application/json.

⚠ IDEMPOTENCE:
    check_and_decrement_stock() MODIFIE la base de product_service.
    Si on l'appelle deux fois, le stock est décrémenté deux fois.
    C'est pourquoi on l'enveloppe dans une transaction atomique en Python.


EXEMPLE COMPLET:

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
            response = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError as e:
            raise ValidationError("catalogue-service est inaccessible.") from e
        except requests.exceptions.Timeout as e:
            raise ValidationError("catalogue-service n'a pas répondu à temps.") from e
        
        if response.status_code == 404:
            raise NotFound(f"Produit {product_id} introuvable.")
        
        if response.status_code != 200:
            raise ValidationError(f"Erreur catalogue-service: {response.status_code}")
        
        return response.json()


    def check_and_decrement_stock(product_id: str, quantity: int) -> dict:
        url = _build_url(f"products/{product_id}/decrement-stock/")
        try:
            response = requests.post(
                url,
                json={"quantity": quantity},
                timeout=5
            )
        except requests.exceptions.ConnectionError as e:
            raise ValidationError("catalogue-service est inaccessible.") from e
        except requests.exceptions.Timeout as e:
            raise ValidationError("catalogue-service n'a pas répondu à temps.") from e
        
        if response.status_code == 404:
            raise NotFound(f"Produit {product_id} introuvable.")
        
        if response.status_code == 400:
            raise ValidationError(response.json())
        
        if response.status_code != 200:
            raise ValidationError(f"Erreur catalogue-service: {response.status_code}")
        
        return response.json()


TESTER DANS LE SHELL:
---------------------

Once created, test manuellement:

    python manage.py shell
    from app.services import get_product, check_and_decrement_stock
    
    # Test 1: Get
    product = get_product("uuid-du-produit")
    print(product)
    
    # Test 2: Decrement
    updated = check_and_decrement_stock("uuid-du-produit", 2)
    print(updated)
    
    # Test 3: Erreur (produit inexistant)
    try:
        get_product("invalid-uuid")
    except Exception as e:
        print(type(e), e)
"""
