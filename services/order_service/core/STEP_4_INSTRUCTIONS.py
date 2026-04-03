"""
ÉTAPE 4 — Ajouter la dépendance HTTP (requirements.txt)
========================================================

FICHIER À MODIFIER:
    services/order_service/requirements.txt


CE QU'IL FAUT AJOUTER:
-----------------------

Ajouter la ligne:
    requests>=2.31


CONTEXTE:
---------
services.py utilise requests pour faire des appels HTTP synchrones.
requests n'est pas inclus dans Django par défaut, il faut l'ajouter.


POURQUOI CETTE VERSION?
------------------------

requests>=2.31
    - 2.31 est stable et bien supportée
    - Versions antérieures peuvent avoir des bugs ou des vulnérabilités
    - >= veut dire "2.31 ou plus récent"


APRÈS LES MODIFICATIONS:
------------------------

Réinstaller les dépendances:

    # En dev local
    pip install -r requirements.txt

    # Ou si tu utilises un venv:
    cd services/order_service
    pip install -r requirements.txt

    # Vérifier que requests est installé:
    python -c "import requests; print(requests.__version__)"


AUTRES DÉPENDANCES À SAVOIR:
----------------------------

Déjà présentes:
    - Django>=4.2
    - djangorestframework>=3.14
    - psycopg2-binary (pour PostgreSQL)
    - pika (pour RabbitMQ, utilisé plus tard)
    - python-decouple (pour lire les .env)

À ajouter:
    - requests (pour HTTP synchrone)


ALTERNATIVE À REQUESTS:
-----------------------

httpx au lieu de requests (recommandé pour async):
    requests>=2.31  # Classique, synchrone
    httpx>=0.25     # Plus moderne, async-ready

Pour ce cours, requests est plus simple.
Tu pourras changer vers httpx plus tard si besoin de scaling.
"""
