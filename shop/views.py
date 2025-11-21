import random
from datetime import timedelta
from django.core.paginator import Paginator
from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.db.models import Q, Sum, Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
import uuid
from django.views.decorators.http import require_POST
from .cart import Cart
from .forms import CheckoutForm, ReviewForm
from . import notifications
from django.http import JsonResponse
from .models import (
    Banner,
    Brand,
    Category,
    LoginOTP,
    OrderItem,
    Product,
    UserProfile,
    Address,
    WishlistItem,
    SupportTicket,
    Province,
    City,
    Order,
    ShippingZone,
    Coupon,
    Review,
)

User = get_user_model()
MAX_OTP_ATTEMPTS = 5


# ============ کمک‌کننده پروفایل ============

def _get_or_create_profile(user):
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "phone": user.username,
            "email": user.email or "",
        },
    )
    return profile

def _get_querystring_without_page(request):
    """
    همه پارامترهای GET فعلی را برمی‌گرداند به جز page
    تا در pagination بتوانیم فیلترها و sort را حفظ کنیم.
    """
    params = request.GET.copy()

    # پارامتر page را حذف می‌کنیم
    params.pop("page", None)

    # پارامترهای خالی را حذف کن تا URL تمیزتر شود
    clean_params = {k: v for k, v in params.items() if v}

    return urlencode(clean_params)


# ============ صفحه اصلی ============

def home(request):
    base_products = (
        Product.objects.filter(is_active=True)
        .select_related("category", "brand")
    )

    categories = Category.objects.filter(is_active=True).order_by("order", "name")
    hero_banners = Banner.objects.filter(position="hero", is_active=True).order_by("order")
    special_products = base_products.filter(show_in_special_offer=True)[:12]
    best_sellers = base_products.filter(is_best_seller=True)[:12]
    new_products = base_products.order_by("-created_at")[:12]
    discounted_products = (
        base_products.filter(
            Q(discount_price__isnull=False)
            | Q(category__discount_active=True, category__discount_percent__isnull=False)
        )
        .distinct()[:12]
    )
    middle_banners = Banner.objects.filter(position="middle", is_active=True).order_by("order")

    context = {
        "categories": categories,
        "hero_banners": hero_banners,
        "special_products": special_products,
        "best_sellers": best_sellers,
        "new_products": new_products,
        "discounted_products": discounted_products,
        "middle_banners": middle_banners,
    }
    return render(request, "shop/home.html", context)


# ============ دسته‌ها و محصول ============

def category_list(request):
    categories = Category.objects.filter(is_active=True).order_by("order", "name")
    return render(request, "shop/category_list.html", {"categories": categories})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # پایه: فقط محصولات فعال همین دسته، به همراه category و brand (برای کاهش کوئری)
    products_qs = (
        category.products.filter(is_active=True)
        .select_related("category", "brand")
    )

    # ------------ فیلترها ------------

    # فیلتر برند
    brand_id = request.GET.get("brand") or ""
    if brand_id:
        products_qs = products_qs.filter(brand_id=brand_id)

    # فقط محصولات دارای تخفیف
    only_discount = request.GET.get("only_discount")
    if only_discount == "1":
        products_qs = products_qs.filter(
            Q(discount_price__isnull=False)
            | Q(
                category__discount_active=True,
                category__discount_percent__isnull=False,
            )
        ).distinct()

    # فقط موجود (stock > 0)
    in_stock = request.GET.get("in_stock")
    if in_stock == "1":
        products_qs = products_qs.filter(stock__gt=0)

    # فیلتر بازه قیمت
    min_price = request.GET.get("min_price") or ""
    max_price = request.GET.get("max_price") or ""

    try:
        if min_price:
            products_qs = products_qs.filter(price__gte=int(min_price))
    except ValueError:
        min_price = ""

    try:
        if max_price:
            products_qs = products_qs.filter(price__lte=int(max_price))
    except ValueError:
        max_price = ""

    # ------------ مرتب‌سازی ------------

    sort = request.GET.get("sort", "")

    if sort == "price_asc":
        products_qs = products_qs.order_by("price")
    elif sort == "price_desc":
        products_qs = products_qs.order_by("-price")
    elif sort == "new":
        products_qs = products_qs.order_by("-created_at")
    elif sort == "bestseller":
        # روی فیلد is_best_seller که در Product داریم
        products_qs = products_qs.order_by("-is_best_seller", "-created_at")
    else:
        # پیش‌فرض: جدیدترین‌ها
        products_qs = products_qs.order_by("-created_at")

    # ------------ pagination ------------

    paginator = Paginator(products_qs, 24)  # ۲۴ محصول در هر صفحه
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    products = page_obj.object_list  # برای اینکه template فعلی که از products استفاده می‌کند، نشکند

    # برندها برای فیلتر سمت چپ/بالا
    brands = (
        Brand.objects.filter(products__category=category, products__is_active=True)
        .distinct()
        .order_by("name")
    )

    current_querystring = _get_querystring_without_page(request)

    seo_title = f"خرید {category.name} | ایران مارکت"
    seo_description = (
        f"خرید آنلاین {category.name} با ارسال سریع و قیمت مناسب از ایران مارکت. "
        f"جدیدترین، پرفروش‌ترین و پیشنهادهای ویژه {category.name} را ببینید."
    )

    return render(
        request,
        "shop/category_detail.html",
        {
            "category": category,
            "products": products,           # لیست صفحه فعلی
            "page_obj": page_obj,           # برای کنترل‌های pagination
            "sort": sort,
            "brands": brands,
            "selected_brand_id": brand_id,
            "only_discount": only_discount,
            "in_stock": in_stock,
            "min_price": min_price,
            "max_price": max_price,
            "current_querystring": current_querystring,
            "seo_title": seo_title,
            "seo_description": seo_description,
        },
    )



def product_detail(request, slug):
    """
    صفحه جزئیات محصول + امتیاز و نظرات:
    - annotate برای میانگین امتیاز و تعداد
    - لیست نظرات تاییدشده
    - فرم ثبت/ویرایش نظر کاربر
    """
    product_qs = (
        Product.objects.select_related("category", "brand")
        .annotate(
            rating_average=Avg(
                "reviews__rating",
                filter=Q(reviews__is_approved=True),
            ),
            rating_count=Count(
                "reviews",
                filter=Q(reviews__is_approved=True),
            ),
        )
    )

    product = get_object_or_404(
        product_qs,
        slug=slug,
        is_active=True,
    )

    # قیمت نهایی
    if hasattr(product, "final_price"):
        final_price = product.final_price
    else:
        final_price = product.discount_price or product.price

    # موجودی
    in_stock = True
    if hasattr(product, "stock") and product.stock is not None:
        in_stock = product.stock > 0

    # توضیح سئویی
    base_desc = getattr(product, "short_description", "") or ""
    if not base_desc and getattr(product, "description", ""):
        base_desc = product.description[:150]

    if base_desc:
        seo_description = f"{base_desc} خرید آنلاین «{product.name}» با ارسال سریع از ایران مارکت."
    else:
        seo_description = f"خرید آنلاین «{product.name}» با قیمت مناسب و ارسال سریع از ایران مارکت."

    seo_title = f"{product.name} | خرید آنلاین | ایران مارکت"
    canonical_url = request.build_absolute_uri()
    og_image_url = None
    if getattr(product, "image", None):
        try:
            og_image_url = request.build_absolute_uri(product.image.url)
        except Exception:
            og_image_url = None
    rating_average = product.rating_average
    rating_count = product.rating_count

    # نظرات تاییدشده
    reviews = (
        product.reviews.filter(is_approved=True)
        .select_related("user")
        .order_by("-created_at")
    )

    # نظر خود کاربر (اگر وجود داشته باشد)
    user_review = None
    if request.user.is_authenticated:
        try:
            user_review = product.reviews.get(user=request.user)
        except Review.DoesNotExist:
            user_review = None

    # فرم (برای GET نمایش فرم، POST در ویوی جدا add_review هندل می‌شود)
    if user_review:
        review_form = ReviewForm(instance=user_review)
    else:
        review_form = ReviewForm()

    context = {
        "product": product,
        "final_price": final_price,
        "in_stock": in_stock,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "canonical_url": canonical_url,
        "rating_average": rating_average,
        "rating_count": rating_count,
        "reviews": reviews,
        "user_review": user_review,
        "review_form": review_form,
        "og_image_url": og_image_url,
    }

    return render(request, "shop/product_detail.html", context)

@login_required
@require_POST
def add_review(request, product_id):
    """
    ایجاد یا ویرایش نظر کاربر برای یک محصول.
    اگر قبلاً نظر داده باشد، همان را ویرایش می‌کنیم.
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)

    try:
        existing_review = Review.objects.get(product=product, user=request.user)
    except Review.DoesNotExist:
        existing_review = None

    form = ReviewForm(request.POST, instance=existing_review)

    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user

        # اگر می‌خوای همه نظرات اول برن تو صف تایید:
        # review.is_approved = False

        review.save()
        if existing_review:
            messages.success(request, "نظر شما بروزرسانی شد. ممنون از همراهی شما.")
        else:
            messages.success(request, "نظر شما ثبت شد. ممنون از همراهی شما.")
    else:
        messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")

    return redirect("shop:product_detail", slug=product.slug)


# ============ جستجو و تخفیف‌ها ============

def product_search(request):
    query = request.GET.get("q", "").strip()

    products_qs = (
        Product.objects.filter(is_active=True)
        .select_related("category", "brand")
    )

    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__name__icontains=query)
        )

    # فیلترهای اختیاری مثل صفحه دسته
    only_discount = request.GET.get("only_discount")
    if only_discount == "1":
        products_qs = products_qs.filter(
            Q(discount_price__isnull=False)
            | Q(
                category__discount_active=True,
                category__discount_percent__isnull=False,
            )
        ).distinct()

    in_stock = request.GET.get("in_stock")
    if in_stock == "1":
        products_qs = products_qs.filter(stock__gt=0)

    min_price = request.GET.get("min_price") or ""
    max_price = request.GET.get("max_price") or ""

    try:
        if min_price:
            products_qs = products_qs.filter(price__gte=int(min_price))
    except ValueError:
        min_price = ""

    try:
        if max_price:
            products_qs = products_qs.filter(price__lte=int(max_price))
    except ValueError:
        max_price = ""

    sort = request.GET.get("sort", "")

    if sort == "price_asc":
        products_qs = products_qs.order_by("price")
    elif sort == "price_desc":
        products_qs = products_qs.order_by("-price")
    elif sort == "new":
        products_qs = products_qs.order_by("-created_at")
    elif sort == "bestseller":
        products_qs = products_qs.order_by("-is_best_seller", "-created_at")
    else:
        products_qs = products_qs.order_by("-created_at")

    paginator = Paginator(products_qs, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    products = page_obj.object_list

    current_querystring = _get_querystring_without_page(request)

    if query:
        seo_title = f"نتایج جستجو برای «{query}» | ایران مارکت"
        seo_description = (
            f"نتایج جستجو برای «{query}» در ایران مارکت. "
            f"محصولات مرتبط را با امکان فیلتر، مرتب‌سازی و ارسال سریع ببینید."
        )
    else:
        seo_title = "جستجوی محصولات | ایران مارکت"
        seo_description = (
            "جستجوی محصولات سوپرمارکتی و مواد غذایی در ایران مارکت. "
            "با فیلتر قیمت، موجودی و تخفیف، محصول مورد نظر خود را سریع پیدا کنید."
        )

    return render(
        request,
        "shop/search_results.html",
        {
            "query": query,
            "products": products,
            "page_obj": page_obj,
            "sort": sort,
            "only_discount": only_discount,
            "in_stock": in_stock,
            "min_price": min_price,
            "max_price": max_price,
            "current_querystring": current_querystring,
            "seo_title": seo_title,
            "seo_description": seo_description,
        },
    )



def offers_list(request):
    products = (
        Product.objects.filter(is_active=True)
        .filter(
            Q(discount_price__isnull=False)
            | Q(category__discount_active=True, category__discount_percent__isnull=False)
        )
        .select_related("category", "brand")
        .distinct()
        .order_by("-created_at")
    )

    return render(
        request,
        "shop/offers_list.html",
        {
            "products": products,
        },
    )

def new_products_list(request):
    products = (
        Product.objects
        .filter(is_active=True)
        .select_related("category", "brand")
        .order_by("-created_at")
    )
    return render(
        request,
        "shop/product_list.html",
        {
            "title": "جدیدترین محصولات",
            "products": products,
        },
    )


def best_sellers_list(request):
    products = (
        Product.objects
        .filter(is_active=True, is_best_seller=True)
        .select_related("category", "brand")
        .order_by("-created_at")
    )
    return render(
        request,
        "shop/product_list.html",
        {
            "title": "پرفروش‌ترین‌ها",
            "products": products,
        },
    )


# ============ شهر فعلی و هزینه ارسال ============

def _get_current_city_from_request(request):
    """
    بر اساس پروفایل کاربر یا سشن، شهر فعلی را برمی‌گرداند.
    این منطق با context_processor تو هماهنگ است.
    """
    user = request.user
    if user.is_authenticated and hasattr(user, "profile") and user.profile.current_city:
        return user.profile.current_city

    city_id = request.session.get("selected_city_id")
    if city_id:
        try:
            return City.objects.get(id=city_id, is_active=True)
        except City.DoesNotExist:
            return None
    return None


def calculate_shipping_cost(request, cart_total):
    """
    هزینه ارسال را بر اساس city -> shipping_zone و جمع سبد حساب می‌کند.
    خروجی: (shipping_cost, current_city)
    """
    current_city = _get_current_city_from_request(request)
    if not current_city or not current_city.shipping_zone or not current_city.shipping_zone.is_active:
        return 0, current_city

    zone = current_city.shipping_zone
    shipping_cost = zone.base_shipping_cost

    # اگر آستانه ارسال رایگان تنظیم شده بود و جمع سبد بهش رسید
    if zone.free_shipping_threshold and cart_total >= zone.free_shipping_threshold:
        shipping_cost = 0

    return shipping_cost, current_city


# ============ سبد خرید و سفارش ============

@require_POST
def cart_add(request, product_id):
    """
    افزودن محصول به سبد.
    - اگر درخواست معمولی باشد → ریدایرکت و پیام فلش
    - اگر AJAX (fetch) باشد → JsonResponse با تعداد جدید سبد و پیام
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)

    try:
        quantity = int(request.POST.get("quantity", 1) or 1)
        if quantity < 1:
            quantity = 1
    except (TypeError, ValueError):
        quantity = 1

    cart.add(product=product, quantity=quantity, override_quantity=False)

    # تعداد آیتم‌های داخل سبد (به احتمال زیاد __len__ روی Cart همین را برمی‌گرداند)
    cart_count = len(cart)

    # تشخیص AJAX
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if is_ajax:
        return JsonResponse(
            {
                "success": True,
                "cart_count": cart_count,
                "message": "محصول به سبد خرید اضافه شد.",
            }
        )

    # حالت معمولی (غیر AJAX) – مثل قبل
    messages.success(request, "محصول به سبد خرید اضافه شد.")
    return redirect("shop:cart_detail")


def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart.remove(product)
    return redirect("shop:cart_detail")

@require_POST
def cart_update(request, product_id):
    """
    به‌روزرسانی تعداد یک آیتم در سبد خرید (افزایش / کاهش با دکمه‌های + و -).
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)

    action = request.POST.get("action")
    try:
        current_quantity = int(request.POST.get("current_quantity", 1))
    except (TypeError, ValueError):
        current_quantity = 1

    if action == "increase":
        new_quantity = current_quantity + 1
    elif action == "decrease":
        new_quantity = current_quantity - 1
    else:
        # اگر هیچ اکشنی نبود، تلاش می‌کنیم از فیلد quantity بخوانیم
        try:
            new_quantity = int(request.POST.get("quantity", current_quantity))
        except (TypeError, ValueError):
            new_quantity = current_quantity

    if new_quantity < 1:
        cart.remove(product)
    else:
        cart.add(product, quantity=new_quantity, override_quantity=True)

    return redirect("shop:cart_detail")


def cart_detail(request):
    cart = Cart(request)
    return render(request, "shop/cart_detail.html", {"cart": cart})

def _get_current_city_for_request(request):
    """
    Helper داخلی برای ویوها (مستقل از context processor):
    - اول از session
    - بعد از پروفایل کاربر
    """
    city = None
    city_id = request.session.get("selected_city_id")

    if city_id:
        try:
            city = City.objects.select_related("shipping_zone").get(
                id=city_id,
                is_active=True,
            )
        except City.DoesNotExist:
            city = None

    if not city and request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and profile.current_city and profile.current_city.is_active:
            city = profile.current_city

    return city


def calculate_shipping_cost(request, items_total):
    """
    محاسبه هزینه ارسال بر اساس:
    - شهر فعلی کاربر (current_city)
    - زون ارسال شهر
    - مبلغ سبد (items_total) و threshold ارسال رایگان
    """
    city = _get_current_city_for_request(request)

    if not city:
        # شهر انتخاب نشده → فعلاً هزینه ارسال را ۰ نشان می‌دهیم
        return 0, None

    if not getattr(city, "delivery_available", True):
        # برای این شهر ارسال نداریم
        return 0, city

    zone = city.shipping_zone
    if not zone or not zone.is_active:
        # زون تعریف نشده یا غیرفعال
        return 0, city

    shipping_cost = zone.base_shipping_cost

    if zone.free_shipping_threshold and items_total >= zone.free_shipping_threshold:
        shipping_cost = 0

    return shipping_cost, city


def checkout(request):
    cart = Cart(request)

    # اگر سبد خالی است، اجازه ادامه نده
    if len(cart) == 0:
        messages.error(request, "سبد خرید شما خالی است.")
        return redirect("shop:cart_detail")

    # جمع سبد بر اساس قیمت‌های به‌روز
    items_total = cart.get_total_price()

    # هزینه ارسال بر اساس شهر انتخابی
    shipping_cost, current_city = calculate_shipping_cost(request, items_total)

    applied_coupon = None
    discount_amount = 0

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            coupon_code = (form.cleaned_data.get("coupon_code") or "").strip()
            coupon_error = None

            # بررسی کوپن (اگر کدی وارد شده باشد)
            if coupon_code:
                now = timezone.now()
                normalized_code = coupon_code.upper()
                try:
                    coupon = Coupon.objects.get(
                        code__iexact=normalized_code,
                        active=True,
                        valid_from__lte=now,
                        valid_to__gte=now,
                    )

                    # فقط اولین سفارش
                    if coupon.for_first_order_only and request.user.is_authenticated:
                        has_paid_order = Order.objects.filter(
                            user=request.user,
                            paid=True,
                        ).exists()
                        if has_paid_order:
                            coupon_error = "این کد فقط برای اولین سفارش قابل استفاده است."

                    # حداقل مبلغ سفارش
                    if (
                        not coupon_error
                        and coupon.min_order_amount
                        and items_total < coupon.min_order_amount
                    ):
                        coupon_error = (
                            f"حداقل مبلغ سفارش برای استفاده از این کد "
                            f"{coupon.min_order_amount} تومان است."
                        )

                    # اگر مشکل نداشت، تخفیف را حساب کن
                    if not coupon_error:
                        applied_coupon = coupon

                        if coupon.discount_percent:
                            discount_amount += (items_total * coupon.discount_percent) // 100

                        if coupon.discount_amount:
                            discount_amount += coupon.discount_amount

                        # سقف تخفیف: از جمع سبد بیشتر نشود
                        if discount_amount > items_total:
                            discount_amount = items_total

                except Coupon.DoesNotExist:
                    coupon_error = "کد تخفیف نامعتبر است."

            # اگر کوپن ایراد داشت، برگرد به فرم
            if coupon_error:
                messages.error(request, coupon_error)
                discount_amount = 0
                payable_total = items_total - discount_amount + shipping_cost
                return render(
                    request,
                    "shop/checkout.html",
                    {
                        "cart": cart,
                        "form": form,
                        "items_total": items_total,
                        "discount_amount": discount_amount,
                        "shipping_cost": shipping_cost,
                        "payable_total": payable_total,
                        "applied_coupon": applied_coupon,
                        "current_city": current_city,
                    },
                )


            # اگر کوپن اوکی بود یا اصلاً وارد نشده بود
            payable_total = items_total - discount_amount + shipping_cost
            if payable_total < 0:
                payable_total = 0

            order = form.save(commit=False)

            if request.user.is_authenticated:
                order.user = request.user

            # ❗ این خط را حذف کردیم، چون items_total یک property است، نه فیلد
            # order.items_total = items_total

            order.discount_amount = discount_amount
            order.shipping_cost = shipping_cost
            order.total_price = payable_total  # جمع نهایی با ارسال

            if applied_coupon:
                order.coupon = applied_coupon
                order.coupon_code = applied_coupon.code
            elif coupon_code:
                # اگر کدی وارد شده ولی معتبر نبود و خواستی ذخیره شود
                order.coupon_code = coupon_code.upper()

            order.paid = False  # بعداً در گام پرداخت آپدیت می‌شود
            order.save()

            # ساخت آیتم‌های سفارش از روی سبد
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    price=item["price"],
                    quantity=item["quantity"],
                )

            cart.clear()

            notifications.send_order_created(order)

            messages.success(request, "سفارش شما ثبت شد. اکنون می‌توانید پرداخت را انجام دهید.")

            # هدایت به صفحه شروع پرداخت
            return redirect("shop:payment_start", order_id=order.id)

    else:
        form = CheckoutForm()

    # GET: فقط نمایش خلاصه قیمت بدون تخفیف
    payable_total = items_total + shipping_cost

    return render(
        request,
        "shop/checkout.html",
        {
            "cart": cart,
            "form": form,
            "items_total": items_total,
            "discount_amount": 0,
            "shipping_cost": shipping_cost,
            "payable_total": payable_total,
            "applied_coupon": None,
        },
    )


from .models import Order, OrderItem

@require_POST
def set_city(request):
    """
    تنظیم شهر انتخاب‌شده توسط کاربر:
    - ذخیره در session
    - اگر کاربر لاگین است، ذخیره در UserProfile.current_city
    """
    city_id = request.POST.get("city_id")

    if not city_id:
        messages.error(request, "لطفاً یک شهر را انتخاب کنید.")
        return redirect(request.META.get("HTTP_REFERER", "shop:home"))

    try:
        city = City.objects.select_related("province", "shipping_zone").get(
            id=city_id,
            is_active=True,
            delivery_available=True,
        )
    except City.DoesNotExist:
        messages.error(request, "شهر انتخاب‌شده معتبر نیست یا فعلاً برای آن ارسال نداریم.")
        return redirect(request.META.get("HTTP_REFERER", "shop:home"))

    request.session["selected_city_id"] = city.id

    if request.user.is_authenticated:
        profile = _get_or_create_profile(request.user)
        profile.current_city = city
        profile.save(update_fields=["current_city"])

    messages.success(request, f"شهر شما روی «{city.name}» تنظیم شد.")
    return redirect(request.META.get("HTTP_REFERER", "shop:home"))


def payment_start(request, order_id):
    """
    صفحه شروع پرداخت برای سفارش.
    فعلاً درگاه تستی: دو دکمه «موفق» و «ناموفق».
    """
    order = get_object_or_404(Order, id=order_id)

    # اگر می‌خواهی مطمئن شی فقط خود صاحب سفارش ببینه:
    if request.user.is_authenticated and order.user and order.user != request.user:
        messages.error(request, "دسترسی به این سفارش برای شما مجاز نیست.")
        return redirect("home")

    # اگر قبلاً پرداخت شده، مستقیم ببرش صفحه موفقیت
    if order.paid:
        messages.info(request, "این سفارش قبلاً پرداخت شده است.")
        return render(
            request,
            "shop/account/order_success.html",
            {"order": order},
        )

    items = OrderItem.objects.filter(order=order).select_related("product")

    return render(
        request,
        "shop/payment_start.html",
        {
            "order": order,
            "items": items,
        },
    )


def payment_callback(request, order_id, status):
    """
    شبیه callback درگاه پرداخت.
    status = "success"  یا  "failed"
    """
    order = get_object_or_404(Order, id=order_id)

    # اگر می‌خواهی مطمئن شوی فقط خود کاربر به این آدرس دسترسی دارد:
    if request.user.is_authenticated and order.user and order.user != request.user:
        messages.error(request, "دسترسی به این سفارش برای شما مجاز نیست.")
        return redirect("home")

    if status == "success":
        # شبیه یک شناسه پرداخت
        payment_ref = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        gateway_code = f"GW-{uuid.uuid4().hex[:8].upper()}"

        try:
            # متدی که در گام ۲ تعریف کردیم:
            order.apply_payment()
        except ValueError as e:
            # مثلاً موجودی کافی نبوده
            messages.error(
                request,
                f"پرداخت انجام شد اما پردازش سفارش به دلیل خطا در موجودی با مشکل مواجه شد: {e}",
            )
            return redirect("payment_start", order_id=order.id)

        order.payment_ref = payment_ref
        order.gateway_tracking_code = gateway_code
        order.save(update_fields=["payment_ref", "gateway_tracking_code"])

        notifications.send_payment_success(order)

        messages.success(request, "پرداخت شما با موفقیت انجام شد.")
        return render(
            request,
            "shop/account/order_success.html",
            {"order": order},
        )

    else:
        # پرداخت ناموفق/لغو شده
        messages.error(request, "پرداخت شما ناموفق بود یا توسط شما لغو شد.")
        return redirect("payment_start", order_id=order.id)



# ============ OTP Login ============

def _send_otp(identifier, code):
    """
    در حالت واقعی اینجا باید به سرویس SMS / ایمیل وصل شوی.
    فعلاً برای توسعه:
    - در کنسول print می‌کنیم
    - یک پیام info به کاربر می‌دهیم
    """
    print(f"[OTP] کد ورود برای {identifier}: {code}")


def login_view(request):
    """
    مرحله ۱: گرفتن موبایل یا ایمیل و ارسال کد OTP
    """
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()

        if not identifier:
            messages.error(request, "لطفاً شماره موبایل یا ایمیل خود را وارد کنید.")
            return render(request, "shop/login.html", {"identifier": identifier})

        # ساخت کد ۶ رقمی
        code = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=5)

        LoginOTP.objects.create(
            identifier=identifier,
            code=code,
            expires_at=expires_at,
        )

        _send_otp(identifier, code)
        messages.info(
            request,
            "کد ورود برای شما ارسال شد (در محیط توسعه داخل کنسول سرور هم چاپ شده است).",
        )

        # نگه‌داشتن شناسه در سشن برای مرحله بعد
        request.session["login_identifier"] = identifier

        return redirect("shop:verify_otp")

    # GET
    identifier = request.session.get("login_identifier", "")
    return render(request, "shop/login.html", {"identifier": identifier})


def verify_otp_view(request):
    """
    مرحله ۲: دریافت کد و ورود/ثبت‌نام کاربر
    """
    identifier = request.session.get("login_identifier")

    if not identifier:
        messages.error(request, "ابتدا شماره موبایل یا ایمیل خود را وارد کنید.")
        return redirect("shop:login")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        otp = (
            LoginOTP.objects.filter(identifier=identifier, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp:
            messages.error(request, "کد ورود معتبر نیست. لطفاً دوباره تلاش کنید.")
            return redirect("shop:login")

        if otp.is_expired:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            messages.error(request, "کد ورود منقضی شده است. دوباره وارد شوید.")
            return redirect("shop:login")

        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            messages.error(request, "کد وارد شده صحیح نیست.")
            return render(
                request,
                "shop/verify_otp.html",
                {"identifier": identifier},
            )

        # کد صحیح است
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        # تشخیص موبایل یا ایمیل
        if "@" in identifier:
            username = identifier
            defaults = {"email": identifier}
        else:
            username = identifier
            defaults = {}

        user, created = User.objects.get_or_create(username=username, defaults=defaults)

        auth_login(request, user)
        request.session.pop("login_identifier", None)

        messages.success(request, "با موفقیت وارد شدید.")
        return redirect("shop:home")

    # GET
    return render(request, "shop/verify_otp.html", {"identifier": identifier})


def logout_view(request):
    auth_logout(request)
    messages.info(request, "با موفقیت خارج شدید.")
    return redirect("shop:home")


# ============ حساب کاربری: داشبورد، پروفایل، آدرس‌ها ============

@login_required
def account_dashboard(request):
    profile = _get_or_create_profile(request.user)

    # آخرین سفارش
    last_order = request.user.orders.order_by("-created_at").first()

    # سفارش در حال پردازش/ارسال
    active_order = (
        request.user.orders.filter(
            status__in=["pending", "processing", "sent"]
        )
        .order_by("-created_at")
        .first()
    )

    total_orders = request.user.orders.count()

    month_ago = timezone.now() - timedelta(days=30)
    orders_last_month = request.user.orders.filter(created_at__gte=month_ago)
    total_spent_last_month = sum(o.total_price for o in orders_last_month)

    context = {
        "profile": profile,
        "last_order": last_order,
        "active_order": active_order,
        "total_orders": total_orders,
        "total_spent_last_month": total_spent_last_month,
        "active_tab": "dashboard",
    }
    return render(request, "shop/account/dashboard.html", context)


@login_required
def account_profile(request):
    profile = _get_or_create_profile(request.user)

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        date_of_birth = request.POST.get("date_of_birth") or None

        profile.full_name = full_name
        profile.email = email
        profile.phone = profile.phone or request.user.username

        if date_of_birth:
            try:
                profile.date_of_birth = date_of_birth
            except ValueError:
                pass

        request.user.email = email
        request.user.save()
        profile.save()

        messages.success(request, "اطلاعات حساب با موفقیت ذخیره شد.")

    return render(
        request,
        "shop/account/profile.html",
        {
            "profile": profile,
            "active_tab": "profile",
        },
    )


@login_required
def account_addresses(request):
    profile = _get_or_create_profile(request.user)

    if request.method == "POST":
        # ساخت یا ویرایش آدرس
        addr_id = request.POST.get("addr_id")
        label = request.POST.get("label", "").strip()
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        street = request.POST.get("street", "").strip()
        plaque = request.POST.get("plaque", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()
        is_default = bool(request.POST.get("is_default"))

        if addr_id:
            address = get_object_or_404(Address, id=addr_id, user=request.user)
        else:
            address = Address(user=request.user)

        address.label = label or "آدرس بدون نام"
        address.city = city
        address.district = district
        address.street = street
        address.plaque = plaque
        address.postal_code = postal_code
        address.save()

        if is_default:
            Address.objects.filter(user=request.user).exclude(id=address.id).update(
                is_default=False
            )
            address.is_default = True
            address.save()

        messages.success(request, "آدرس ذخیره شد.")
        return redirect("shop:account_addresses")

    # GET
    addresses = request.user.addresses.all().order_by("-is_default", "-created_at")
    return render(
        request,
        "shop/account/addresses.html",
        {
            "profile": profile,
            "addresses": addresses,
            "active_tab": "addresses",
        },
    )


@login_required
def account_address_delete(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.info(request, "آدرس حذف شد.")
    return redirect("shop:account_addresses")


@login_required
def account_address_set_default(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user).update(is_default=False)
    address.is_default = True
    address.save()
    messages.success(request, "آدرس پیش‌فرض بروزرسانی شد.")
    return redirect("shop:account_addresses")


# ============ حساب کاربری: سفارش‌ها، علاقه‌مندی‌ها، نوتیفیکیشن، پشتیبانی ============

@login_required
def account_orders(request):
    """
    لیست سفارش‌های کاربر فعلی.
    """
    orders = (
        Order.objects.filter(user=request.user)
        .select_related("user", "city")          # اگر city در Order داری
        .prefetch_related("items__product")      # related_name = "items" روی OrderItem
        .order_by("-created_at")
    )

    return render(
        request,
        "shop/account/orders.html",
        {"orders": orders},
    )

@login_required
def order_detail(request, order_id):
    """
    جزئیات یک سفارش برای کاربر فعلی.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related("product")

    # آیا کاربر اجازه لغو دارد؟
    can_cancel = (
        not order.paid
        and order.status in {Order.STATUS_PENDING, Order.STATUS_PROCESSING}
    )

    return render(
        request,
        "shop/account/order_detail.html",
        {
            "order": order,
            "items": items,
            "can_cancel": can_cancel,
        },
    )

@login_required
@require_POST
def order_cancel(request, order_id):
    """
    لغو سفارش توسط خود کاربر.
    فقط اگر:
    - صاحب سفارش باشد
    - هنوز پرداخت نشده باشد
    - در وضعیت pending یا processing باشد
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not order.paid and order.status in {Order.STATUS_PENDING, Order.STATUS_PROCESSING}:
        old_status = order.status
        order.mark_as_cancelled(restock=True)
        notifications.send_order_status_changed(order, old_status, order.status)
        messages.success(request, f"سفارش شماره {order.id} با موفقیت لغو شد.")
    else:
        messages.error(
            request,
            "امکان لغو این سفارش وجود ندارد (ممکن است قبلاً ارسال یا تحویل شده باشد).",
        )

    return redirect("shop:order_detail", order_id=order.id)


@login_required
def account_wishlist(request):
    items = (
        WishlistItem.objects.filter(user=request.user)
        .select_related("product")
        .order_by("-created_at")
    )
    return render(
        request,
        "shop/account/wishlist.html",
        {
            "items": items,
            "active_tab": "wishlist",
        },
    )


@login_required
def wishlist_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    messages.success(request, "محصول به علاقه‌مندی‌ها اضافه شد.")
    return redirect("shop:product_detail", slug=product.slug)


@login_required
def wishlist_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    WishlistItem.objects.filter(user=request.user, product=product).delete()
    messages.info(request, "محصول از علاقه‌مندی‌ها حذف شد.")
    return redirect("shop:account_wishlist")


@login_required
def account_notifications(request):
    profile = _get_or_create_profile(request.user)

    if request.method == "POST":
        profile.notify_order_sms = bool(request.POST.get("notify_order_sms"))
        profile.notify_promotions = bool(request.POST.get("notify_promotions"))
        profile.notify_site_notifications = bool(
            request.POST.get("notify_site_notifications")
        )
        profile.save()
        messages.success(request, "تنظیمات اطلاع‌رسانی ذخیره شد.")

    return render(
        request,
        "shop/account/notifications.html",
        {
            "profile": profile,
            "active_tab": "notifications",
        },
    )


@login_required
def account_support(request):
    if request.method == "POST":
        subject = request.POST.get("subject", "").strip()
        message_text = request.POST.get("message", "").strip()

        if subject and message_text:
            SupportTicket.objects.create(
                user=request.user,
                subject=subject,
                message=message_text,
            )
            messages.success(request, "درخواست شما ثبت شد. به زودی پاسخ داده می‌شود.")
            return redirect("shop:account_support")
        else:
            messages.error(request, "لطفاً موضوع و متن پیام را وارد کنید.")

    tickets = request.user.support_tickets.all()
    return render(
        request,
        "shop/account/support.html",
        {
            "tickets": tickets,
            "active_tab": "support",
        },
    )


# ============ تنظیم شهر کاربر ============

@require_POST
def set_city(request):
    city_id = request.POST.get("city_id")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

    if not city_id:
        messages.error(request, "لطفاً یک شهر را انتخاب کنید.")
        return redirect(next_url)

    try:
        city = City.objects.get(id=city_id, is_active=True, delivery_available=True)
    except City.DoesNotExist:
        messages.error(request, "شهر انتخاب‌شده معتبر نیست.")
        return redirect(next_url)

    # ذخیره در سشن
    request.session["selected_city_id"] = city.id

    # اگر لاگین است، در پروفایلش هم ذخیره کن
    if request.user.is_authenticated:
        profile = _get_or_create_profile(request.user)
        profile.current_city = city
        profile.save()

    messages.success(request, f"شهر شما روی «{city.name}» تنظیم شد.")
    return redirect(next_url)


# ============ صفحات راهنما / استاتیک ============

def about(request):
    return render(request, "shop/pages/about.html")


def buying_guide(request):
    return render(request, "shop/pages/buying_guide.html")


def shipping_methods(request):
    return render(request, "shop/pages/shipping_methods.html")


def return_policy(request):
    return render(request, "shop/pages/return_policy.html")


def faq(request):
    return render(request, "shop/pages/faq.html")
