from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import Category, Product, Supplier


class Command(BaseCommand):
    help = "Peuple la base avec des catégories, fournisseurs et produits de démonstration."

    categories = [
        {
            "name": "Boissons",
            "description": "Articles pour le café, le thé et les boissons du quotidien.",
        },
        {
            "name": "Électronique",
            "description": "Produits techniques et accessoires numériques.",
        },
        {
            "name": "Maison",
            "description": "Objets utiles pour l'intérieur et l'organisation.",
        },
        {
            "name": "Accessoires",
            "description": "Petits articles pratiques pour compléter l'offre.",
        },
    ]

    suppliers = [
        {
            "name": "Atlas Supply",
            "contact_name": "Nadia Diop",
            "email": "contact@atlassupply.example",
            "phone_number": "+221770000001",
            "address": "Dakar, Sénégal",
        },
        {
            "name": "Nord Distribution",
            "contact_name": "Moussa Kane",
            "email": "hello@norddistribution.example",
            "phone_number": "+221770000002",
            "address": "Thiès, Sénégal",
        },
        {
            "name": "Maison Pro",
            "contact_name": "Awa Fall",
            "email": "contact@maisonpro.example",
            "phone_number": "+221770000003",
            "address": "Mbour, Sénégal",
        },
        {
            "name": "Tech Source",
            "contact_name": "Ibrahima Ba",
            "email": "team@techsource.example",
            "phone_number": "+221770000004",
            "address": "Saint-Louis, Sénégal",
        },
    ]

    products = [
        {
            "name": "Coffee Machine Plus",
            "description": "Machine à café automatique simple et fiable.",
            "price": Decimal("229.00"),
            "stock": 20,
            "reserved_stock": 2,
            "category": "Boissons",
            "supplier": "Atlas Supply",
        },
        {
            "name": "Wireless Keyboard",
            "description": "Clavier sans fil compact pour poste de travail.",
            "price": Decimal("49.90"),
            "stock": 34,
            "reserved_stock": 3,
            "category": "Électronique",
            "supplier": "Tech Source",
        },
        {
            "name": "Desk Lamp",
            "description": "Lampe de bureau LED à lumière douce.",
            "price": Decimal("29.50"),
            "stock": 14,
            "reserved_stock": 1,
            "category": "Maison",
            "supplier": "Maison Pro",
        },
        {
            "name": "Water Bottle",
            "description": "Bouteille réutilisable légère et pratique.",
            "price": Decimal("12.00"),
            "stock": 58,
            "reserved_stock": 0,
            "category": "Accessoires",
            "supplier": "Nord Distribution",
        },
        {
            "name": "USB-C Hub",
            "description": "Hub multifonction pour ordinateur portable.",
            "price": Decimal("39.00"),
            "stock": 8,
            "reserved_stock": 4,
            "category": "Électronique",
            "supplier": "Tech Source",
        },
        {
            "name": "Tea Box",
            "description": "Boîte de thé assortiment pour boutique ou bureau.",
            "price": Decimal("16.75"),
            "stock": 10,
            "reserved_stock": 1,
            "category": "Boissons",
            "supplier": "Atlas Supply",
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les données de démonstration existantes avant de recreer le jeu de données.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les actions sans écrire en base.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Mode dry-run : aucune écriture en base."))

        with transaction.atomic():
            if reset and not dry_run:
                deleted_products = Product.objects.all().delete()[0]
                deleted_categories = Category.objects.all().delete()[0]
                deleted_suppliers = Supplier.objects.all().delete()[0]
                self.stdout.write(
                    self.style.WARNING(
                        f"Nettoyage effectué: {deleted_products} produits, "
                        f"{deleted_categories} catégories, {deleted_suppliers} fournisseurs supprimés."
                    )
                )

            categories = self._seed_categories(dry_run=dry_run)
            suppliers = self._seed_suppliers(dry_run=dry_run)
            products = self._seed_products(categories, suppliers, dry_run=dry_run)

        self.stdout.write(
            self.style.SUCCESS(
                f"Peuplement terminé: {len(categories)} catégories, {len(suppliers)} fournisseurs, "
                f"{len(products)} produits."
            )
        )

    def _seed_categories(self, dry_run=False):
        categories = {}
        for item in self.categories:
            if dry_run:
                categories[item["name"]] = None
                self.stdout.write(f"[DRY-RUN] Catégorie: {item['name']}")
                continue

            obj, created = Category.objects.update_or_create(
                name=item["name"],
                defaults={"description": item["description"]},
            )
            categories[obj.name] = obj
            action = "créée" if created else "mise à jour"
            self.stdout.write(f"Catégorie {action}: {obj.name}")
        return categories

    def _seed_suppliers(self, dry_run=False):
        suppliers = {}
        for item in self.suppliers:
            if dry_run:
                suppliers[item["name"]] = None
                self.stdout.write(f"[DRY-RUN] Fournisseur: {item['name']}")
                continue

            obj, created = Supplier.objects.update_or_create(
                name=item["name"],
                defaults={
                    "contact_name": item["contact_name"],
                    "email": item["email"],
                    "phone_number": item["phone_number"],
                    "address": item["address"],
                },
            )
            suppliers[obj.name] = obj
            action = "créé" if created else "mis à jour"
            self.stdout.write(f"Fournisseur {action}: {obj.name}")
        return suppliers

    def _seed_products(self, categories, suppliers, dry_run=False):
        products = []
        for item in self.products:
            if dry_run:
                products.append(item["name"])
                self.stdout.write(f"[DRY-RUN] Produit: {item['name']}")
                continue

            obj, created = Product.objects.update_or_create(
                name=item["name"],
                defaults={
                    "description": item["description"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "reserved_stock": item["reserved_stock"],
                    "category": categories[item["category"]],
                    "suppliers": suppliers[item["supplier"]],
                },
            )
            products.append(obj.name)
            action = "créé" if created else "mis à jour"
            self.stdout.write(f"Produit {action}: {obj.name}")
        return products
