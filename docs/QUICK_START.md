# QUICK START (DEBUTANT)

Si tu apprends encore, commence ici.

## 1) Lis seulement ces 2 fichiers

1. `docs/BEGINNER_MICROSERVICES_GUIDE.md`
2. `docs/BEGINNER_EXERCISES.md`

## 2) Fais les exercices dans l ordre

1. Exercice 1: health checks
2. Exercice 2: decrement stock
3. Exercice 3: appels HTTP entre services
4. Exercice 4: creation de commande
5. Exercice 5: routes + actions

## 3) Regle simple

Sur chaque appel HTTP inter-service, mets toujours `timeout=5`.

## 4) Si tu bloques

1. Lis le fichier `STEP_X_INSTRUCTIONS.py` de l etape correspondante.
2. Teste un endpoint a la fois avec `curl`.
3. Corrige une seule erreur, puis reteste.

## 5) Objectif final

Quand `POST /orders/` diminue le stock produit et renvoie la commande, tu as reussi.
