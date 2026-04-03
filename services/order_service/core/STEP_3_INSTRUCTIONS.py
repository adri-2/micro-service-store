"""
ÉTAPE 3 — Configurer l'URL du service distant (settings.py)
============================================================

FICHIER À MODIFIER:
    services/order_service/core/settings.py


CONTEXTE:
---------
services.py a besoin de connaître l'URL de product_service.
On NE hardcode PAS l'URL dans le code.
On la lit depuis les variables d'environnement avec une valeur par défaut.


CE QU'IL FAUT AJOUTER:
-----------------------

En haut du fichier (où les autres imports):
    import os

À la fin du fichier (après REST_FRAMEWORK):
    CATALOGUE_SERVICE_URL = os.environ.get(
        "CATALOGUE_SERVICE_URL",
        "http://localhost:8001",
    )


EXPLICATION:
-----------

Pourquoi os.environ.get() ?
    - En développement local: récupère la valeur depuis le .env ou utilise la valeur par défaut
    - En Docker: la variable d'environnement peut pointer vers le nom du service
    - En production: la variable d'environnement peut pointer vers une URL externe

os.environ.get("CATALOGUE_SERVICE_URL", "http://localhost:8001")
    - Clé: "CATALOGUE_SERVICE_URL"
    - Valeur par défaut: "http://localhost:8001" (pour développement local)


VALEURS ATTENDUES:
-------------------

Environnement         URL
-----------           ---
Développement local   http://localhost:8001
Docker (local)        http://product-service:8000
Production            https://api.catalogue.example.com


DANS LE .env (optionnel, à créer à côté de manage.py):
------------------------------------------------------

Pour dev local, créer le fichier:
    services/order_service/.env

Avec le contenu:
    CATALOGUE_SERVICE_URL=http://localhost:8001


Pour Docker, la variable est définie dans docker-compose.yml.


COMMENT VÉRIFIER:
-----------------

Une fois ajouté, tester dans le shell:

    python manage.py shell
    from django.conf import settings
    print(settings.CATALOGUE_SERVICE_URL)
    # Doit afficher: "http://localhost:8001"


POINTS CLÉS:
-----------

✓ Ne pas mettre de "/" à la fin de l'URL
    BON: "http://localhost:8001"
    MAUVAIS: "http://localhost:8001/"

✓ os.environ.get() doit être utilisé partout pour les URLs externes
    C'est la bonne pratique microservices

✓ La valeur par défaut est pour le développement local uniquement
    En production/docker, utiliser les variables d'environnement
"""
