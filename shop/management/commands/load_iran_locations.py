import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Province, City


class Command(BaseCommand):
    help = "Load Iran provinces and cities from JSON file into Province/City models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="shop/data/iran_locations.json",
            help="Path to JSON file containing provinces and cities.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing provinces and cities before loading.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.stdout.write(self.style.NOTICE(f"Loading locations from {file_path}..."))

        with transaction.atomic():
            if options["reset"]:
                self.stdout.write("Deleting existing provinces and cities...")
                City.objects.all().delete()
                Province.objects.all().delete()

            for prov_data in data:
                prov_name = prov_data.get("name")
                prov_slug = prov_data.get("slug") or None
                prov_order = prov_data.get("order", 0)
                is_active = prov_data.get("is_active", True)

                province, _ = Province.objects.get_or_create(
                    name=prov_name,
                    defaults={
                        "slug": prov_slug or "",
                        "order": prov_order,
                        "is_active": is_active,
                    },
                )
                # اگر از قبل بوده، آپدیت کن
                province.order = prov_order
                province.is_active = is_active
                if prov_slug:
                    province.slug = prov_slug
                province.save()

                cities = prov_data.get("cities", [])
                for city_data in cities:
                    city_name = city_data.get("name")
                    city_slug = city_data.get("slug") or ""
                    city_order = city_data.get("order", 0)
                    city_is_active = city_data.get("is_active", True)
                    is_popular = city_data.get("is_popular", False)
                    delivery_available = city_data.get("delivery_available", True)

                    city, _ = City.objects.get_or_create(
                        province=province,
                        name=city_name,
                        defaults={
                            "slug": city_slug,
                            "order": city_order,
                            "is_active": city_is_active,
                            "is_popular": is_popular,
                            "delivery_available": delivery_available,
                        },
                    )
                    city.slug = city_slug or city.slug
                    city.order = city_order
                    city.is_active = city_is_active
                    city.is_popular = is_popular
                    city.delivery_available = delivery_available
                    city.save()

        self.stdout.write(self.style.SUCCESS("Locations loaded successfully."))
