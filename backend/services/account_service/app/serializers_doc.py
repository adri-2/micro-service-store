"""
GUIDE — serializers.py pour account_service
============================================

Ce fichier est un guide d'implémentation.
Une fois que tu as compris et implémenté, crée le vrai fichier :
    account_service/app/serializers.py

Tu peux t'appuyer sur le fichier existant comme référence :
    product_service/app/serializers.py


POURQUOI DES SERIALIZERS ?
--------------------------
Un serializer DRF fait deux choses :
  1. Validation   → transforme et valide les données reçues (JSON → Python)
  2. Sérialisation → transforme les objets Python en JSON pour la réponse

Sans serializer, tu ne peux pas construire d'API REST avec DRF.


RÈGLE GÉNÉRALE POUR CE SERVICE
-------------------------------
account_service gère deux modèles indépendants :
  - User  → credentials (email, username, password)
  - Client → profil client (nom, prénom, adresse, téléphone)

Ces deux modèles ne doivent PAS se connaître dans les serializers.
Chaque serializer gère un seul modèle.


ÉTAPE 1 — Créer le fichier
--------------------------
Crée le fichier : account_service/app/serializers.py

Commence par l'import :

    from rest_framework import serializers
    from .models import User, Client


==============================================================================
SERIALIZER 1 : UserSerializer
==============================================================================

Pourquoi un UserSerializer ?
- Exposer les informations de base d'un utilisateur (email, username)
- Ne PAS exposer le mot de passe en lecture
- Permettre la création d'un utilisateur en écriture

Modèle concerné (account_service/app/models.py) :

    class User(AbstractBaseUser, BaseModel):
        id       = UUIDField (primary_key)
        email    = EmailField (unique)
        username = CharField
        # hérité de AbstractBaseUser :
        # password (haché, jamais exposé en lecture)

Structure à implémenter :

    class UserSerializer(serializers.ModelSerializer):

        # Conseil : déclarer le champ password explicitement
        # pour contrôler qu'il est write_only
        # (ne jamais renvoyer le hash du mot de passe dans les réponses)
        password = serializers.CharField(
            ???,          # TODO: rendre le champ en écriture seule
            ???,          # TODO: ne pas l'afficher dans les réponses GET
        )

        class Meta:
            model = ???     # TODO: quel modèle ?
            fields = ???    # TODO: quels champs exposer ?
                            # Suggestion : ['id', 'email', 'username', 'password']

        def create(self, validated_data):
            # IMPORTANT : ne pas faire User.objects.create(**validated_data)
            # car le mot de passe serait stocké en clair.
            # AbstractBaseUser fournit set_password() pour hacher le mot de passe.
            #
            # TODO: extraire le password de validated_data avec .pop()
            # TODO: créer l'utilisateur sans le password
            # TODO: appeler user.set_password(password)
            # TODO: sauvegarder l'utilisateur avec user.save()
            # TODO: retourner l'utilisateur
            pass


# EXEMPLE de bonne pratique pour create() :
#
#   def create(self, validated_data):
#       password = validated_data.pop('password')
#       user = User(**validated_data)
#       user.set_password(password)
#       user.save()
#       return user
#
# Pourquoi pop() et pas get() ?
#   pop() retire le champ de validated_data pour éviter de le passer
#   deux fois (une fois dans **validated_data et une fois dans set_password)


==============================================================================
SERIALIZER 2 : ClientSerializer
==============================================================================

Pourquoi un ClientSerializer ?
- Exposer et valider le profil complet d'un client
- Ce serializer est plus simple : pas de mot de passe, pas de relation ManyToMany

Modèle concerné (account_service/app/models.py) :

    class Client(BaseModel):
        id           = UUIDField (primary_key)
        first_name   = CharField
        last_name    = CharField
        email        = EmailField (unique)
        phone_number = CharField (blank)
        address      = TextField (blank)

Structure à implémenter :

    class ClientSerializer(serializers.ModelSerializer):

        class Meta:
            model = ???     # TODO: quel modèle ?
            fields = ???    # TODO: 'id', 'first_name', 'last_name', 'email',
                            #       'phone_number', 'address', 'created_at'
            read_only_fields = ???  # TODO: quels champs ne doivent pas être
                                    #       modifiables par l'API ?
                                    # Réponse : 'id' et 'created_at'

        def validate_email(self, value):
            # TODO: vérifier que l'email n'est pas déjà utilisé par un autre client
            # Attention : lors d'un UPDATE, exclure le client en cours de modification !
            #
            # Aide : utilise self.instance pour accéder à l'objet en cours de modification
            # Si self.instance est None → c'est une création (POST)
            # Si self.instance est défini → c'est une mise à jour (PUT/PATCH)
            #
            # La validation équivalente existe déjà dans le modèle (clean()),
            # mais il est préférable de la faire ici aussi pour avoir
            # une erreur JSON propre dans la réponse API.
            pass

        def validate_phone_number(self, value):
            # TODO: si une valeur est fournie, vérifier qu'elle ne contient
            #       que des chiffres, +, -, espaces
            # Optionnel mais bon exercice de validation
            pass


# RAPPEL : différence entre validate_<field> et validate()
#
#   validate_email(self, value)
#     → validé pour UN champ spécifique
#     → appelé automatiquement par DRF si le champ s'appelle 'email'
#
#   validate(self, data)
#     → validé sur TOUS les champs ensemble (validation croisée)
#     → utile quand une règle dépend de deux champs en même temps
#
# Exemple de validate() croisée :
#
#   def validate(self, data):
#       if data.get('first_name') == data.get('last_name'):
#           raise serializers.ValidationError("Prénom et nom ne peuvent pas être identiques.")
#       return data


==============================================================================
CHECKLIST AVANT DE PASSER AUX VIEWS
==============================================================================

Avant de créer views.py, vérifie que :

[ ] Le fichier serializers.py est créé dans account_service/app/
[ ] UserSerializer gère la création avec set_password()
[ ] password est déclaré write_only=True
[ ] ClientSerializer a read_only_fields pour id et created_at
[ ] ClientSerializer.validate_email() vérifie l'unicité
[ ] Tu as testé manuellement :
      from app.serializers import UserSerializer, ClientSerializer
      (dans le shell Django : python manage.py shell)


==============================================================================
PROCHAINE ÉTAPE
==============================================================================

Une fois ce fichier implémenté comme serializers.py :
→ Ouvre account_service/app/views_doc.py pour implémenter les views
"""
