"""
GUIDE RAPIDE — Si tu es perdu
==============================

Tu as de nombreuses instructions ? Voici le chemin court.

LIRE D'ABORD (5 min)
---------------------

1. docs/MICROSERVICES_SYNC_GUIDE.md
   → Comprendre le flux global

2. docs/MICROSERVICES_WORK_PLAN.md
   → Voir l'ordre d'implémentation + tests

FAIRE EN ORDRE (7 étapes)
--------------------------

[1] ÉTAPE 1 — product_service/app/views.py
    Lire: services/product_service/app/STEP_1_INSTRUCTIONS.py
    Ajouter: @action pour decrement_stock

[2] ÉTAPE 2 — order_service/app/services.py
    Lire: services/order_service/app/STEP_2_INSTRUCTIONS.py
    Créer: nouveau fichier avec get_product() + check_and_decrement_stock()

[3] ÉTAPE 3 — order_service/core/settings.py
    Lire: services/order_service/core/STEP_3_INSTRUCTIONS.py
    Ajouter: CATALOGUE_SERVICE_URL

[4] ÉTAPE 4 — order_service/requirements.txt
    Lire: services/order_service/core/STEP_4_INSTRUCTIONS.py
    Ajouter: requests>=2.31

[5] ÉTAPE 5 — order_service/app/serializers.py
    Lire: services/order_service/app/STEP_5_INSTRUCTIONS.py
    Créer: nouveau fichier avec 3 serializers

[6] ÉTAPE 6 — order_service/app/views.py + urls.py
    Lire: services/order_service/app/STEP_6_INSTRUCTIONS.py
    Modifier: views.py (health + OrderViewSet)
    Modifier: urls.py (routeur)

[7] TEST
    Lire: docs/MICROSERVICES_WORK_PLAN.md (section Tests)
    Lancer: curl pour chaque test

ARCHITECTURE EN 1 IMAGE
------------------------

    Client API
        |
        | POST /orders/
        v
    order_service (serializers.create)
        |
        +--- SYNC GET product ------- product_service /products/{id}/
        |   (get_product)                   |
        |                                  Response: {name, price}
        |
        +--- SYNC POST stock ----- product_service /products/{id}/decrement-stock/
        |   (check_and_decrement_stock)     |
        |                                  Response: Updated {stock: x}
        |
        +--- Creer Order + Items en base
        |
        v
    Response: {"id": "...", "items": [...], "status": "Pending"}

POINTS À RETENIR
-----------------

1. SYNCHRONE = order_service ATTEND la réponse de product_service
   Si product_service ne répond pas → order_service lève une erreur

2. TIMEOUT obligatoire = 5s par défaut
   Pas de timeout = gèle indéfiniment en cas d'erreur distant

3. SNAPSHOT de données = product_name + unit_price copiés au moment de la création
   Si prix change après, l'ordre garde l'ancien prix

4. TRANSACTION ATOMIQUE = tout ou rien
   Si OrderItem échoue → Order est rollback automatiquement

5. SÉPARATION responsabilités:
   - product_service = produits + stock
   - order_service = commandes + orchestration

SI TU BLOQUES
--------------

❌ "Je comprends pas un truc"
→ Relis la section du STEP_X_INSTRUCTIONS.py correspondant
→ Les commentaires expliquent chaque ligne

❌ "Mon code ne marche pas"
→ Vérifier les 3 points:

   1. CATALOGUE_SERVICE_URL correctement configurée ?
   2. Timeout mis sur les requests ?
   3. Exceptions traduites en DRF (NotFound, ValidationError) ?

❌ "Erreur import"
→ Vérifier que le fichier est create (pas juste comments)
→ pip install -r requirements.txt exécuté ?

❌ "Produit service ne répond pas"
→ Lancer product_service d'abord
→ Tester endpoint /health/ avec curl

COMMANDES UTILES
-----------------

# Voir la structure

tree /services/product_service/
tree /services/order_service/

# Vérifier imports

python manage.py shell

# Tester un endpoint

curl <http://localhost:8001/health/>
curl <http://localhost:8002/health/>

# Voir les erreurs

python manage.py runserver 0.0.0.0:8002

FICHIERS À LIRE (dans l'ordre)
------------------------------

1. docs/MICROSERVICES_SYNC_GUIDE.md (5 min)
2. docs/MICROSERVICES_WORK_PLAN.md (10 min)
3. services/product_service/app/STEP_1_INSTRUCTIONS.py (5 min)
   → implémenter
4. services/order_service/app/STEP_2_INSTRUCTIONS.py (10 min)
   → implémenter
5. services/order_service/core/STEP_3_INSTRUCTIONS.py (2 min)
   → implémenter
6. services/order_service/core/STEP_4_INSTRUCTIONS.py (1 min)
   → implémenter
7. services/order_service/app/STEP_5_INSTRUCTIONS.py (15 min)
   → implémenter
8. services/order_service/app/STEP_6_INSTRUCTIONS.py (10 min)
   → implémenter
9. docs/MICROSERVICES_WORK_PLAN.md (section Tests, 10 min)
   → tester

TOTAL ATTENDU
--------------

Temps de lecture: ~40 min
Temps d'implémentation: ~1-2 heures
Temps de test: ~30 min

TOTAL: ~3 heures pour maîtriser complètement

C'est normal si c'est long la première fois.
Tu apprendras les patterns.
Après microservices = second nature.
"""
