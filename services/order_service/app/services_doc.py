"""
GUIDE — services.py pour order_service
=======================================

Ce fichier est un guide d'implémentation.
Une fois implémenté, crée le vrai fichier :
    order_service/app/services.py


POURQUOI CE FICHIER ?
---------------------
order_service doit appeler catalogue-service pour :
  1. Vérifier qu'un produit existe (GET /products/{id}/)
  2. Vérifier que le stock est suffisant
  3. Décrémenter le stock après la création d'une commande

C'est une COMMUNICATION SYNCHRONE entre services.
Ce fichier isole tout le code réseau dans une couche séparée des views et serializers.

Principe : les views ne connaissent pas les URL de catalogue-service.
Elles appellent des fonctions de services.py qui savent comment communiquer.


QUEL OUTIL HTTP UTILISER ?
--------------------------
Deux options :

Option A : requests (synchrone, simple)
    pip install requests
    (mais requests est bloquant — chaque appel bloque le thread Django)

Option B : httpx (recommandé, supporte async)
    pip install httpx
    (meilleure option pour les microservices modernes)

Pour commencer, utilise requests. C'est plus simple à apprendre.
Tu pourras migrer vers httpx plus tard.

Ajoute dans order_service/requirements.txt :
    requests>=2.31


CONFIGURATION
-------------
L'URL de base du catalogue-service doit être dans les settings,
pas hardcodée dans le code.

Dans order_service/core/settings.py, ajoute :

    import os
    CATALOGUE_SERVICE_URL = os.environ.get(
        'CATALOGUE_SERVICE_URL',
        'http://catalogue-service:8000'   # valeur par défaut pour Docker
    )

Et dans order_service/.env (à créer à l'étape 2 des next-steps) :

    CATALOGUE_SERVICE_URL=http://catalogue-service:8000


==============================================================================
STRUCTURE DU FICHIER services.py
==============================================================================

    import requests
    from django.conf import settings
    from rest_framework.exceptions import ValidationError, NotFound


    # URL de base lue depuis settings.py
    BASE_URL = settings.CATALOGUE_SERVICE_URL


    def get_product(product_id: str) -> dict:
        \"""
        Appelle catalogue-service pour récupérer les informations d'un produit.

        Retourne un dict avec : id, name, price, stock, ...
        Lève NotFound si le produit n'existe pas (404).
        Lève une exception si le service est indisponible.
        \"""
        # TODO: construire l'URL : f"{BASE_URL}/products/{product_id}/"
        # TODO: faire la requête GET avec requests.get(url, timeout=5)
        # TODO: si response.status_code == 404 → lever NotFound("Produit introuvable")
        # TODO: si response.status_code != 200 → lever une exception générique
        # TODO: retourner response.json()
        pass


    def check_and_decrement_stock(product_id: str, quantity: int) -> dict:
        \"""
        Appelle catalogue-service pour décrémenter le stock d'un produit.

        Retourne les données du produit mis à jour.
        Lève ValidationError si le stock est insuffisant.
        Lève NotFound si le produit n'existe pas.

        Note : cet endpoint n'existe pas encore dans catalogue-service.
        Il faudra l'ajouter dans product_service/app/views.py
        (voir les TODO dans ce fichier).
        \"""
        # TODO: construire l'URL : f"{BASE_URL}/products/{product_id}/decrement-stock/"
        # TODO: faire la requête POST avec requests.post(url, json={"quantity": quantity}, timeout=5)
        # TODO: si response.status_code == 400 → lever ValidationError(response.json())
        # TODO: si response.status_code == 404 → lever NotFound("Produit introuvable")
        # TODO: retourner response.json()
        pass


==============================================================================
EXEMPLE COMPLET DE get_product()
==============================================================================

    def get_product(product_id: str) -> dict:
        url = f"{BASE_URL}/products/{product_id}/"
        try:
            response = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError:
            raise ValidationError(
                f"catalogue-service est inaccessible. URL: {url}"
            )
        except requests.exceptions.Timeout:
            raise ValidationError("catalogue-service n'a pas répondu à temps.")

        if response.status_code == 404:
            raise NotFound(f"Produit {product_id} introuvable dans le catalogue.")

        if response.status_code != 200:
            raise ValidationError(
                f"Erreur catalogue-service: {response.status_code}"
            )

        return response.json()

Pourquoi timeout=5 ?
→ Sans timeout, si catalogue-service ne répond pas,
  ton thread Django attend indéfiniment et ton service est bloqué.
  Toujours mettre un timeout sur les appels réseau inter-services.


==============================================================================
OÙ APPELER CES FONCTIONS ?
==============================================================================

Ces fonctions sont appelées dans OrderSerializer.create() :

    # Dans order_service/app/serializers.py

    from app.services import get_product, check_and_decrement_stock

    def create(self, validated_data):
        items_data = validated_data.pop('items_input')
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product_id = str(item_data['product_id'])
            quantity = item_data['quantity']

            # Appel inter-service
            product = get_product(product_id)
            check_and_decrement_stock(product_id, quantity)

            OrderItem.objects.create(
                order=order,
                product_id=product_id,
                product_name=product['name'],
                unit_price=product['price'],
                quantity=quantity,
                subtotal=0,   # recalculé dans OrderItem.save()
            )

        return order


==============================================================================
ORDRE D'IMPLÉMENTATION RECOMMANDÉ
==============================================================================

1. D'abord ajouter l'endpoint dans catalogue-service :
   product_service/app/views.py → ajouter decrement_stock action

2. Tester cet endpoint manuellement avec curl ou api.http :
   POST http://catalogue.local/products/{id}/decrement-stock/
   { "quantity": 2 }

3. Ensuite implémenter get_product() dans services.py

4. Tester get_product() dans le shell Django :
   python manage.py shell
   from app.services import get_product
   get_product("uuid-du-produit")

5. Implémenter check_and_decrement_stock()

6. Câbler dans OrderSerializer.create()


==============================================================================
CHECKLIST
==============================================================================

[ ] requests ajouté dans requirements.txt
[ ] CATALOGUE_SERVICE_URL dans settings.py (lu depuis env)
[ ] order_service/app/services.py créé
[ ] get_product() implémenté et testé
[ ] check_and_decrement_stock() implémenté et testé
[ ] Appels intégrés dans OrderSerializer.create()
[ ] Endpoint /products/{id}/decrement-stock/ créé dans catalogue-service


==============================================================================
PROCHAINE ÉTAPE
==============================================================================

→ Ouvre order_service/app/views_doc.py
  pour implémenter les views et l'endpoint /health/.
"""
