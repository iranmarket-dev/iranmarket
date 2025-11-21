from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.db import transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q


class SiteSetting(models.Model):
    store_name = models.CharField(max_length=150, default="فروشگاه ایران مارکت")
    intro_text = models.TextField(
        blank=True,
        help_text="متن معرفی فروشگاه که در صفحه اول نمایش داده می‌شود.",
    )
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    whatsapp_link = models.URLField(blank=True)
    instagram_link = models.URLField(blank=True)
    delivery_description = models.TextField(
        blank=True,
        help_text="مثلاً: ارسال در شهر X در کمتر از ۲ ساعت.",
    )

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return self.store_name


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    icon_image = models.ImageField(
        upload_to="categories/icons/",
        blank=True,
        null=True,
        help_text="عکس گرد دسته‌بندی برای نمایش در صفحه اول و لیست دسته‌ها.",
    )

    # تخفیف دسته‌ای
    discount_percent = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="درصد تخفیف برای کل این دسته (مثلاً 10، 20، 30).",
    )
    discount_active = models.BooleanField(
        default=False,
        help_text="اگر تیک بخورد، این درصد تخفیف روی تمام محصولات فعالِ این دسته اعمال می‌شود.",
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Brand(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    logo = models.ImageField(upload_to="brands/logos/", blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "برند"
        verbose_name_plural = "برندها"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Province(models.Model):
    name = models.CharField("نام استان", max_length=50)
    slug = models.SlugField(unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Province.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ShippingZone(models.Model):
    name = models.CharField("نام زون", max_length=100)
    base_shipping_cost = models.PositiveIntegerField(
        "هزینه پایه ارسال (تومان)",
        help_text="مثلاً ۲۰۰۰۰ برای ۲۰ هزار تومان.",
    )
    free_shipping_threshold = models.PositiveIntegerField(
        "ارسال رایگان از (تومان)",
        null=True,
        blank=True,
        help_text="اگر خالی باشد، برای این زون ارسال رایگان نداریم.",
    )
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveIntegerField("ترتیب نمایش", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "زون ارسال"
        verbose_name_plural = "زون‌های ارسال"

    def __str__(self):
        return self.name


class City(models.Model):
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name="cities",
        verbose_name="استان",
    )
    name = models.CharField("نام شهر", max_length=100)
    slug = models.SlugField("اسلاگ", max_length=255, blank=True, unique=True)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    is_popular = models.BooleanField("محبوب/پرتکرار", default=False)
    delivery_available = models.BooleanField("امکان ارسال", default=True)

    shipping_zone = models.ForeignKey(
        ShippingZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cities",
        verbose_name="زون ارسال",
    )

    class Meta:
        ordering = ["province__name", "order", "name"]
        unique_together = ("province", "name")
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self):
        return f"{self.name} ({self.province.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.province.name}-{self.name}", allow_unicode=True)
            slug = base_slug
            counter = 1
            while City.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Product(models.Model):
    UNIT_CHOICES = (
        ("g", "گرم"),
        ("kg", "کیلوگرم"),
        ("ml", "میلی‌لیتر"),
        ("l", "لیتر"),
        ("pcs", "عدد"),
        ("pack", "بسته"),
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        related_name="products",
        blank=True,
        null=True,
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, db_index=True)

    # کد کالا در نرم‌افزار باران
    external_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="کد کالا در نرم‌افزار باران (برای اتصال خودکار).",
    )

    image = models.ImageField(upload_to="products/main/", blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=0)
    discount_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        blank=True,
        null=True,
        help_text="اگر خالی باشد یعنی تخفیف ندارد.",
    )

    stock = models.PositiveIntegerField(default=0, help_text="موجودی انبار")
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="pcs")
    unit_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="مثلاً 0.9 برای ۹۰۰ گرم یا 1 برای ۱ لیتر.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_best_seller = models.BooleanField(
        default=False,
        help_text="نمایش در اسلایدر پرفروش‌ترین‌ها",
        db_index=True,
    )
    show_in_special_offer = models.BooleanField(
        default=False,
        help_text="نمایش در اسلایدر پیشنهاد ویژه.",
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="میانگین امتیاز کاربران، مثلاً 4.35",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        indexes = [
            models.Index(fields=["is_active", "created_at"]),
            models.Index(fields=["is_best_seller", "is_active"]),
            models.Index(fields=["show_in_special_offer", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    # ---------- منطق تخفیف (محصول + دسته) ----------

    def _category_discount_percent(self):
        """درصد تخفیف فعال روی دسته، اگر وجود داشته باشد."""
        if (
            self.category
            and self.category.discount_active
            and self.category.discount_percent
        ):
            return self.category.discount_percent
        return 0

    @property
    def has_discount(self):
        """آیا این محصول به هر دلیلی تخفیف دارد؟ (خودش یا دسته‌اش)"""
        if self.discount_price and self.discount_price < self.price:
            return True
        return self._category_discount_percent() > 0

    @property
    def discount_percent(self):
        """درصد تخفیف نهایی روی محصول."""
        if self.discount_price and self.discount_price < self.price:
            return int(100 - (self.discount_price / self.price) * 100)

        cat_pct = self._category_discount_percent()
        if cat_pct > 0:
            return cat_pct

        return 0

    @property
    def final_price(self):
        """قیمت نهایی قابل نمایش/فروش."""
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price

        cat_pct = self._category_discount_percent()
        if cat_pct > 0:
            return int(self.price * (100 - cat_pct) / 100)

        return self.price


class Review(models.Model):
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="محصول",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_reviews",
        verbose_name="کاربر",
    )
    rating = models.PositiveSmallIntegerField(
        "امتیاز",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="عددی بین ۱ تا ۵",
    )
    title = models.CharField("عنوان نظر", max_length=100, blank=True)
    comment = models.TextField("متن نظر", blank=True)

    is_approved = models.BooleanField(
        "تایید شده",
        default=True,   # اگر می‌خوای همه اول برن تو صف تایید، بذار False
    )

    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("تاریخ بروزرسانی", auto_now=True)

    class Meta:
        verbose_name = "نظر محصول"
        verbose_name_plural = "نظرات محصولات"
        ordering = ("-created_at",)
        unique_together = ("product", "user")  # هر کاربر برای هر محصول فقط یک نظر

    def __str__(self):
        return f"{self.product.name} - {self.user} ({self.rating})"



class Banner(models.Model):
    POSITION_CHOICES = (
        ("hero", "اسلایدر بزرگ بالای صفحه"),
        ("special_offer_side", "باکس کنار پیشنهاد ویژه"),
        ("middle", "بنر وسط صفحه"),
        ("footer", "بنر پایین صفحه"),
    )

    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=250, blank=True)
    image = models.ImageField(upload_to="banners/")
    link_url = models.CharField(
        max_length=300,
        blank=True,
        help_text="می‌تواند لینک یک دسته، محصول یا صفحه خاص باشد.",
    )
    position = models.CharField(
        max_length=30,
        choices=POSITION_CHOICES,
        default="hero",
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["position", "order"]
        verbose_name = "بنر"
        verbose_name_plural = "بنرها"
        indexes = [
            models.Index(fields=["position", "order"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_position_display()})"

class Coupon(models.Model):
    code = models.CharField("کد تخفیف", max_length=50, unique=True)
    description = models.CharField("توضیح", max_length=200, blank=True)

    discount_percent = models.PositiveIntegerField(
        "درصد تخفیف",
        null=True,
        blank=True,
        help_text="مثلاً ۱۰ برای ۱۰٪ تخفیف. اگر خالی باشد، فقط مبلغ ثابت اعمال می‌شود.",
    )
    discount_amount = models.PositiveIntegerField(
        "تخفیف ثابت (تومان)",
        null=True,
        blank=True,
        help_text="مثلاً ۵۰۰۰۰ برای ۵۰هزار تومان تخفیف. اگر خالی باشد، فقط درصد تخفیف اعمال می‌شود.",
    )

    min_order_amount = models.PositiveIntegerField(
        "حداقل مبلغ سفارش (تومان)",
        default=0,
        help_text="اگر ۰ باشد، بدون محدودیت است.",
    )

    active = models.BooleanField("فعال", default=True)
    valid_from = models.DateTimeField("اعتبار از")
    valid_to = models.DateTimeField("اعتبار تا")

    for_first_order_only = models.BooleanField(
        "فقط برای اولین سفارش کاربر؟",
        default=False,
    )

    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "کوپن تخفیف"
        verbose_name_plural = "کوپن‌های تخفیف"

    def __str__(self):
        return self.code

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.discount_percent is None and self.discount_amount is None:
            raise ValidationError("حداقل یکی از درصد تخفیف یا مبلغ ثابت باید پر باشد.")
        if self.discount_percent and self.discount_percent > 100:
            raise ValidationError("درصد تخفیف نمی‌تواند بیشتر از ۱۰۰ باشد.")

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "در حال بررسی"),
        (STATUS_PROCESSING, "در حال آماده‌سازی"),
        (STATUS_SENT, "ارسال شده"),
        (STATUS_DELIVERED, "تحویل شده"),
        (STATUS_CANCELLED, "لغو شده"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        blank=True,
        null=True,
        help_text="اگر کاربر موقع ثبت سفارش لاگین بوده باشد، اینجا ذخیره می‌شود.",
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    address = models.TextField()

    # شهر انتخاب‌شده برای ارسال (براساس City)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="شهر",
    )

    # هزینه ارسال و جمع کل
    shipping_cost = models.PositiveIntegerField(
        "هزینه ارسال (تومان)",
        default=0,
    )
    total_price = models.PositiveIntegerField(
        "جمع کل با ارسال (تومان)",
        default=0,
    )

    # اطلاعات درگاه/پرداخت
    payment_ref = models.CharField(
        "شماره پیگیری پرداخت",
        max_length=100,
        blank=True,
    )
    gateway_tracking_code = models.CharField(
        "کد رهگیری درگاه",
        max_length=100,
        blank=True,
    )

    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    paid = models.BooleanField("پرداخت شده", default=False)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    stock_deducted = models.BooleanField(
            "کسر موجودی انجام شده",
            default=False,
            help_text="برای جلوگیری از کسر دوباره‌ی موجودی در صورت تأیید پرداخت تکراری.",
    )


    class Meta:
        ordering = ["-created_at"]
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"

    def __str__(self):
        return f"سفارش #{self.id}"

    @property
    def items_total(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def shipping_zone(self):
        if self.city and self.city.shipping_zone:
            return self.city.shipping_zone
        return None

        # ---- متدهای کمکی چرخه سفارش و موجودی ----

    def can_modify_stock(self):
        """
        آیا هنوز منطقی است که روی موجودی این سفارش عملیات انجام دهیم؟
        معمولاً قبل از ارسال/تحویل.
        """
        return self.status in {self.STATUS_PENDING, self.STATUS_PROCESSING}

    @transaction.atomic
    def apply_payment(self):
        """
        متد اصلی برای زمانی که پرداخت سفارش تأیید می‌شود.
        - بررسی کافی بودن موجودی
        - کسر موجودی
        - تنظیم وضعیت سفارش و فلگ‌ها
        - idempotent (اگر قبلاً موجودی کسر شده، دوباره این کار را نمی‌کند)
        """
        if self.paid and self.stock_deducted:
            # قبلاً به عنوان پرداخت‌شده پردازش شده
            return

        # اطمینان از کافی بودن موجودی تمام آیتم‌ها
        for item in self.items.select_related("product"):
            product = item.product
            if product.stock is not None and product.stock < item.quantity:
                raise ValueError(f"موجودی محصول «{product.name}» کافی نیست.")

        # کسر موجودی
        for item in self.items.select_related("product"):
            product = item.product
            if product.stock is not None:
                product.stock -= item.quantity
                if product.stock < 0:
                    product.stock = 0
                product.save(update_fields=["stock"])

        # تنظیم وضعیت سفارش
        self.paid = True
        # اگر سفارش قبلاً لغو نشده، ببریمش در حال پردازش
        if self.status != self.STATUS_CANCELLED:
            self.status = self.STATUS_PROCESSING

        self.stock_deducted = True
        self.save(update_fields=["paid", "status", "stock_deducted"])

    @transaction.atomic
    def mark_as_cancelled(self, restock=True):
        """
        لغو سفارش.
        اگر restock=True و موجودی قبلاً کسر شده باشد و سفارش هنوز در مرحله منطقی باشد،
        موجودی برگردانده می‌شود.
        """
        if self.status == self.STATUS_CANCELLED:
            return

        if restock and self.stock_deducted and self.can_modify_stock():
            for item in self.items.select_related("product"):
                product = item.product
                if product.stock is not None:
                    product.stock += item.quantity
                    product.save(update_fields=["stock"])
            self.stock_deducted = False

        self.status = self.STATUS_CANCELLED
        # اگر سیاستت این است که سفارش لغوشده را نپرداخته در نظر بگیری:
        self.paid = False
        self.save(update_fields=["status", "paid", "stock_deducted"])

    def mark_as_sent(self):
        """
        زمانی که سفارش تحویل پیک/پست می‌شود.
        """
        if self.status not in {self.STATUS_PROCESSING, self.STATUS_PENDING}:
            # اگر دوست داری سخت‌گیر باشی می‌تونی اینجا خطا raise کنی
            pass
        self.status = self.STATUS_SENT
        self.save(update_fields=["status"])

    def mark_as_delivered(self):
        """
        زمانی که سفارش تحویل مشتری می‌شود.
        """
        self.status = self.STATUS_DELIVERED
        self.save(update_fields=["status"])


class OrderStats(Order):
    """
    مدل پروکسی فقط برای نمایش داشبورد فروش در ادمین.
    هیچ جدول جدیدی در دیتابیس ساخته نمی‌شود.
    """
    class Meta:
        proxy = True
        verbose_name = "داشبورد فروش"
        verbose_name_plural = "داشبورد فروش"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name="order_items",
        on_delete=models.PROTECT,
    )
    price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity


class LoginOTP(models.Model):
    identifier = models.CharField(
        max_length=100,
        db_index=True,
        help_text="شماره موبایل یا ایمیل کاربر",
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "کد ورود"
        verbose_name_plural = "کدهای ورود"

    def __str__(self):
        return f"{self.identifier} - {self.code}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField("نام و نام خانوادگی", max_length=150, blank=True)
    phone = models.CharField("شماره موبایل", max_length=20, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    date_of_birth = models.DateField("تاریخ تولد", blank=True, null=True)

    current_city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="شهر انتخاب‌شده",
    )

    # تنظیمات اطلاع‌رسانی
    notify_order_sms = models.BooleanField(
        "پیامک وضعیت سفارش",
        default=True,
    )
    notify_promotions = models.BooleanField(
        "اطلاع‌رسانی تخفیف‌ها",
        default=False,
    )
    notify_site_notifications = models.BooleanField(
        "اعلان‌های داخل سایت",
        default=True,
    )

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل کاربران"

    def __str__(self):
        return f"پروفایل {self.user.get_username()}"


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField("برچسب", max_length=50, help_text="مثلاً خانه، محل کار")
    city = models.CharField("شهر", max_length=50)
    district = models.CharField("محله", max_length=100, blank=True)
    street = models.CharField("خیابان", max_length=150, blank=True)
    plaque = models.CharField("پلاک", max_length=20, blank=True)
    postal_code = models.CharField("کد پستی", max_length=20, blank=True)

    latitude = models.FloatField("عرض جغرافیایی", blank=True, null=True)
    longitude = models.FloatField("طول جغرافیایی", blank=True, null=True)

    is_default = models.BooleanField("آدرس پیش‌فرض", default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"

    def __str__(self):
        return f"{self.label} - {self.city}"


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "آیتم علاقه‌مندی"
        verbose_name_plural = "لیست علاقه‌مندی‌ها"
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user} → {self.product}"


class SupportTicket(models.Model):
    STATUS_CHOICES = (
        ("open", "باز"),
        ("answered", "پاسخ داده شده"),
        ("closed", "بسته شده"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    subject = models.CharField("موضوع", max_length=200)
    message = models.TextField("پیام")
    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )
    admin_reply = models.TextField("پاسخ پشتیبانی", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تیکت پشتیبانی"
        verbose_name_plural = "تیکت‌های پشتیبانی"

    def __str__(self):
        return f"{self.user} - {self.subject}"
