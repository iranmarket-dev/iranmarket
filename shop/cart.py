# shop/cart.py
from decimal import Decimal
from django.conf import settings
from .models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        """
        محصول را به سبد اضافه می‌کند.
        قیمت را اینجا ذخیره نمی‌کنیم، چون می‌خواهیم همیشه از قیمت به‌روز DB استفاده کنیم.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                "quantity": 0,
            }

        if override_quantity:
            self.cart[product_id]["quantity"] = quantity
        else:
            self.cart[product_id]["quantity"] += quantity

        self.save()

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, product):
        """
        حذف کامل یک محصول از سبد خرید
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        روی آیتم‌های سبد خرید آیتریت می‌کند و:
        - محصول واقعی را از DB می‌گیرد
        - قیمت نهایی به‌روز را از product.final_price می‌گیرد
        """
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids).select_related(
            "category", "brand"
        )
        cart = self.cart.copy()

        for product in products:
            item = cart[str(product.id)]
            item["product"] = product

            # قیمت واحد به‌روز بر اساس منطق مدل (شامل تخفیف محصول + تخفیف دسته)
            unit_price = product.final_price  # این پراپرتی را در مدل Product داری

            # اگر دوست داری همه‌چیز اعشاری باشد:
            # unit_price = Decimal(product.final_price)

            item["price"] = unit_price
            item["total_price"] = unit_price * item["quantity"]

            yield item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def get_total_price(self):
        """
        جمع کل سبد خرید با قیمت‌های به‌روز
        """
        return sum(item["total_price"] for item in self)

    def clear(self):
        self.session[settings.CART_SESSION_ID] = {}
        self.session.modified = True
