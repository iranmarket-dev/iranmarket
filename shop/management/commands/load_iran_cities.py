# shop/management/commands/load_iran_cities.py
from django.core.management.base import BaseCommand
from pathlib import Path
import json

from shop.models import Province, City


class Command(BaseCommand):
    help = "Load Iran provinces and cities from iran_cities.json into DB"

    def handle(self, *args, **options):
        # iran_cities.json در همین پوشه‌ی فعلی
        data_path = Path(__file__).with_name("iran_cities.json")

        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {data_path}"))
            return

        with data_path.open(encoding="utf-8") as f:
            data = json.load(f)

        created_provinces = 0
        created_cities = 0

        for item in data:
            province_name = item["province"].strip()
            cities = item.get("cities", [])

            province, p_created = Province.objects.get_or_create(name=province_name)
            if p_created:
                created_provinces += 1

            for city_name in cities:
                city_name = city_name.strip()
                _, c_created = City.objects.get_or_create(
                    province=province,
                    name=city_name,
                )
                if c_created:
                    created_cities += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Provinces created: {created_provinces}, cities created: {created_cities}"
        ))
