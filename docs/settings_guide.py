"""
GUIDE — Corriger les settings.py (étape 1 et 2 des next-steps)
===============================================================

Ce fichier s'applique aux 3 services :
  - product_service/core/settings.py
  - order_service/core/settings.py
  - account_service/core/settings.py

Travaille service par service. Commence par product_service
car c'est le seul qui a déjà une API fonctionnelle.


==============================================================================
PROBLÈME ACTUEL
==============================================================================

Tous les settings.py ont ces deux problèmes critiques :

Problème 1 — SQLite au lieu de PostgreSQL :

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",  # ← mauvais moteur
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

Problème 2 — Variables d'environnement ignorées :

    SECRET_KEY = "django-insecure-ga(rs0r%)..."  # ← hardcodé dans le code
    DEBUG = True                                  # ← hardcodé
    ALLOWED_HOSTS = ["*"]                         # ← hardcodé et non sécurisé


==============================================================================
SOLUTION : utiliser python-decouple
==============================================================================

python-decouple est déjà dans les requirements.txt des 3 services.
Il lit les variables depuis :
  1. Le fichier .env (prioritaire)
  2. Les variables d'environnement du système
  3. Une valeur par défaut si fournie

Import à ajouter en haut de chaque settings.py :

    from decouple import config, Csv


REMPLACEMENT DE SECRET_KEY
--------------------------

Avant :
    SECRET_KEY = "django-insecure-ga(rs0r%)..."

Après :
    SECRET_KEY = config('SECRET_KEY')

Dans le .env du service :
    SECRET_KEY=genere-une-vraie-cle-ici

Comment générer une nouvelle clé ?
Ouvre un terminal dans le dossier du service et lance :

    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

Copie la valeur générée dans SECRET_KEY= du .env.
Génère une clé DIFFÉRENTE pour chaque service.


REMPLACEMENT DE DEBUG
---------------------

Avant :
    DEBUG = True

Après :
    DEBUG = config('DEBUG', default=True, cast=bool)

    # cast=bool → convertit la string "True"/"False" en booléen Python
    # default=True → si DEBUG n'est pas dans .env, vaut True

Dans le .env :
    DEBUG=True


REMPLACEMENT DE ALLOWED_HOSTS
------------------------------

Avant :
    ALLOWED_HOSTS = ["*"]     # product_service
    ALLOWED_HOSTS = []        # order et account service

Après :
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

    # Csv() → convertit "catalogue.local,localhost" en ['catalogue.local', 'localhost']
    # C'est l'import Csv de python-decouple

Dans le .env de chaque service :
    # product_service/.env
    ALLOWED_HOSTS=catalogue.local,localhost

    # order_service/.env
    ALLOWED_HOSTS=orders.local,localhost

    # account_service/.env
    ALLOWED_HOSTS=account.local,localhost


==============================================================================
REMPLACEMENT DU BLOC DATABASES
==============================================================================

Avant (dans les 3 services) :

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

Après :

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME":     config('DB_NAME'),
            "USER":     config('DB_USER'),
            "PASSWORD": config('DB_PASSWORD'),
            "HOST":     config('DB_HOST', default='localhost'),
            "PORT":     config('DB_PORT', default='5432'),
        }
    }

Dans le .env de chaque service (exemples) :

    # product_service/.env
    DB_NAME=catalogue_db
    DB_USER=catalogue_user
    DB_PASSWORD=catalogue_pass
    DB_HOST=catalogue-db
    DB_PORT=5432

    # order_service/.env
    DB_NAME=orders_db
    DB_USER=orders_user
    DB_PASSWORD=orders_pass
    DB_HOST=orders-db
    DB_PORT=5432

    # account_service/.env
    DB_NAME=account_db
    DB_USER=account_user
    DB_PASSWORD=account_pass
    DB_HOST=account-db
    DB_PORT=5432

Ces valeurs correspondent exactement à ce qui est déjà dans les docker-compose.


==============================================================================
REMPLACEMENT DE RABBITMQ_URL (order_service et product_service)
==============================================================================

Ajouter dans les settings.py concernés :

    RABBITMQ_URL = config('RABBITMQ_URL', default='amqp://guest:guest@localhost:5672/')

Dans le .env :
    RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672/


==============================================================================
SETTINGS.PY FINAL — résultat attendu pour product_service
==============================================================================

    from pathlib import Path
    from decouple import config, Csv

    BASE_DIR = Path(__file__).resolve().parent.parent

    SECRET_KEY = config('SECRET_KEY')
    DEBUG = config('DEBUG', default=True, cast=bool)
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

    INSTALLED_APPS = [
        # "django.contrib.admin",   ← rester commenté pour les services API
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.staticfiles",
        'rest_framework',
        'app',
    ]

    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]

    ROOT_URLCONF = "core.urls"
    WSGI_APPLICATION = "core.wsgi.application"

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME":     config('DB_NAME'),
            "USER":     config('DB_USER'),
            "PASSWORD": config('DB_PASSWORD'),
            "HOST":     config('DB_HOST', default='localhost'),
            "PORT":     config('DB_PORT', default='5432'),
        }
    }

    RABBITMQ_URL = config('RABBITMQ_URL', default='amqp://guest:guest@localhost:5672/')

    LANGUAGE_CODE = "fr-fr"
    TIME_ZONE = "Europe/Paris"
    USE_I18N = True
    USE_TZ = True

    STATIC_URL = "static/"
    DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

    REST_FRAMEWORK = {
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.AllowAny',
        ],
    }


==============================================================================
CRÉER LES FICHIERS .env
==============================================================================

Crée un .env dans chaque dossier de service.
Exemple pour product_service/.env :

    SECRET_KEY=<valeur générée avec get_random_secret_key()>
    DEBUG=True
    ALLOWED_HOSTS=catalogue.local,localhost
    DB_NAME=catalogue_db
    DB_USER=catalogue_user
    DB_PASSWORD=catalogue_pass
    DB_HOST=catalogue-db
    DB_PORT=5432
    RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672/


==============================================================================
AJOUTER .env AU .gitignore
==============================================================================

À la racine du projet, vérifie que .gitignore contient :

    .env
    *.env
    .env.*
    db.sqlite3

Si le fichier .gitignore n'existe pas, crée-le à la racine du projet.

ATTENTION : si des .env ont déjà été commités dans git,
il faut les retirer avec :
    git rm --cached product_service/.env
    git rm --cached order_service/.env
    git rm --cached account_service/.env


==============================================================================
MODIFIER LES DOCKER-COMPOSE
==============================================================================

Chaque docker-compose doit référencer le .env plutôt que de hardcoder les valeurs.

Avant (dans catalogue-service) :
    environment:
      DB_NAME: catalogue_db
      DB_USER: catalogue_user
      DB_PASSWORD: catalogue_pass
      DB_HOST: catalogue-db
      DB_PORT: 5432

Après :
    env_file:
      - .env

Avec cette syntaxe, Docker lit toutes les variables du .env automatiquement.
Tu n'as plus besoin de lister les variables une par une dans docker-compose.


==============================================================================
CRÉER LES FICHIERS .env.example
==============================================================================

Pour chaque service, crée aussi un .env.example avec les noms de variables
mais SANS les valeurs sensibles. Ce fichier PEUT être commité dans git.

Exemple product_service/.env.example :

    SECRET_KEY=
    DEBUG=True
    ALLOWED_HOSTS=catalogue.local,localhost
    DB_NAME=catalogue_db
    DB_USER=catalogue_user
    DB_PASSWORD=
    DB_HOST=catalogue-db
    DB_PORT=5432
    RABBITMQ_URL=


==============================================================================
ORDRE D'APPLICATION
==============================================================================

1. Commencer par product_service (service le plus avancé)
2. Corriger settings.py de product_service
3. Créer product_service/.env
4. Tester : docker-compose -f docker-compose.catalogue.yml up
5. Vérifier que GET /health/ et GET /products/ fonctionnent
6. Répéter pour order_service
7. Répéter pour account_service


==============================================================================
CHECKLIST
==============================================================================

product_service :
[ ] Import decouple ajouté
[ ] SECRET_KEY lu depuis .env
[ ] DEBUG lu depuis .env
[ ] ALLOWED_HOSTS lu depuis .env
[ ] DATABASES utilise PostgreSQL avec variables d'env
[ ] RABBITMQ_URL ajouté
[ ] .env créé avec les vraies valeurs
[ ] .env.example créé (sans valeurs sensibles)
[ ] docker-compose.catalogue.yml utilise env_file

order_service :
[ ] Même corrections que product_service
[ ] CATALOGUE_SERVICE_URL ajouté (pour services.py)

account_service :
[ ] Même corrections que product_service

Global :
[ ] .env dans .gitignore
[ ] Aucun secret hardcodé dans les settings.py ni docker-compose
"""
