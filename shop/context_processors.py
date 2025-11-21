# shop/context_processors.py
from .models import SiteSetting, Category, City, Province
from .cart import Cart 


def city_context(request):
    """
    تعیین current_city برای تمام templateها:
    - اول از session (selected_city_id)
    - اگر نبود و کاربر لاگین بود → از UserProfile.current_city (یا profile.current_city)
    """
    city = None
    city_id = request.session.get("selected_city_id")

    if city_id:
        try:
            city = City.objects.select_related("province", "shipping_zone").get(
                id=city_id,
                is_active=True,
            )
        except City.DoesNotExist:
            city = None

    # اگر از سشن شهر نداشتیم، از پروفایل کاربر لاگین‌شده برداریم
    if not city and request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and profile.current_city and profile.current_city.is_active:
            city = profile.current_city

    return {"current_city": city}


def global_store_context(request):
    """
    کانتکست کلی فروشگاه:
    - تنظیمات سایت (SiteSetting)
    - دسته‌بندی‌ها
    - شیء سبد خرید (Cart)
    - لیست استان‌ها برای مودال انتخاب شهر
    - current_city (از city_context)
    """
    site_setting = SiteSetting.objects.first()

    categories = Category.objects.filter(is_active=True).order_by("order", "name")

    provinces = (
        Province.objects.filter(is_active=True)
        .prefetch_related("cities")
        .order_by("name")
    )

    cart = Cart(request)

    # از city_context استفاده می‌کنیم تا current_city را هم اضافه کنیم
    city_ctx = city_context(request)

    context = {
        "global_settings": site_setting,   # این همونیه که فوتر و هدر استفاده می‌کنن
        "site_setting": site_setting,      # اگر جایی اسم دیگه لازم داشتیم
        "categories": categories,
        "province_list": provinces,
        "cart": cart,
    }
    context.update(city_ctx)
    return context
