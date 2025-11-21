# shop/admin.py
from django.contrib import admin
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import TruncDate
from django.utils import timezone
import datetime
import json
from django.contrib import messages
from . import notifications
from .models import (
    SiteSetting,
    Category,
    Brand,
    Product,
    Banner,
    Order,
    OrderItem,
    Province,
    City,
    UserProfile,
    Address,
    WishlistItem,
    SupportTicket,
    LoginOTP,
    OrderStats,
    Coupon,
    ShippingZone,
    Review,
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    ordering = ("order", "name")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "brand",
        "price",
        "discount_price",
        "stock",
        "is_active",
        "is_best_seller",
        "show_in_special_offer",
        "created_at",
    )
    list_filter = (
        "category",
        "brand",
        "is_active",
        "is_best_seller",
        "show_in_special_offer",
        "created_at",
    )
    list_editable = (
        "price",
        "discount_price",
        "stock",
        "is_active",
        "is_best_seller",
        "show_in_special_offer",
    )
    search_fields = ("name", "external_code")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category", "brand")
    readonly_fields = ("created_at", "updated_at", "rating")
    list_per_page = 50
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "position", "order", "is_active")
    list_editable = ("position", "order", "is_active")
    list_filter = ("position", "is_active")
    search_fields = ("title",)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = (
        "product__name",
        "user__username",
        "user__first_name",
        "user__last_name",
        "title",
        "comment",
    )
    autocomplete_fields = ("product", "user")
    list_editable = ("is_approved",)
    date_hierarchy = "created_at"



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "price", "quantity", "row_total")
    readonly_fields = ("row_total",)
    autocomplete_fields = ("product",)

    def row_total(self, obj):
        return obj.price * obj.quantity

    row_total.short_description = "جمع ردیف"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "phone",
        "status",
        "paid",
        "created_at",
        "total_price",
    )
    list_filter = ("status", "paid", "created_at")
    search_fields = ("id", "first_name", "last_name", "phone")
    inlines = [OrderItemInline]
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_per_page = 50
    raw_id_fields = ("user",)
    ordering = ("-created_at",)

    def customer_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    customer_name.short_description = "مشتری"

    actions = [
        "action_mark_as_paid",
        "action_mark_as_sent",
        "action_mark_as_delivered",
        "action_mark_as_cancelled",
    ]

    def action_mark_as_paid(self, request, queryset):
        success = 0
        failed = 0

        for order in queryset:
            try:
                order.apply_payment()
                success += 1
            except ValueError as e:
                failed += 1

        if success:
            self.message_user(
                request,
                f"{success} سفارش با موفقیت به عنوان پرداخت‌شده ثبت و موجودی آن‌ها کسر شد.",
            )
        if failed:
            self.message_user(
                request,
                f"برای {failed} سفارش به دلیل عدم موجودی کافی یا خطای دیگر، عملیات انجام نشد.",
                level=messages.ERROR,
            )

    action_mark_as_paid.short_description = "علامت‌گذاری به عنوان «پرداخت‌شده» و کسر موجودی"

    def action_mark_as_sent(self, request, queryset):
        updated = 0
        for order in queryset:
            old_status = order.status
            order.mark_as_sent()
            updated += 1
            notifications.send_order_status_changed(order, old_status, order.status)
        if updated:
            self.message_user(request, f"وضعیت {updated} سفارش به «ارسال شده» تغییر کرد.")

    action_mark_as_sent.short_description = "علامت‌گذاری به عنوان «ارسال شده»"

    def action_mark_as_delivered(self, request, queryset):
        updated = 0
        for order in queryset:
            old_status = order.status
            order.mark_as_delivered()
            updated += 1
            notifications.send_order_status_changed(order, old_status, order.status)
        if updated:
            self.message_user(request, f"وضعیت {updated} سفارش به «تحویل شده» تغییر کرد.")

    action_mark_as_delivered.short_description = "علامت‌گذاری به عنوان «تحویل شده»"

    def action_mark_as_cancelled(self, request, queryset):
        updated = 0
        for order in queryset:
            old_status = order.status
            # اینجا restock=True یعنی موجودی برگردد (تا زمانی که منطقی باشد)
            order.mark_as_cancelled(restock=True)
            updated += 1
            notifications.send_order_status_changed(order, old_status, order.status)
        if updated:
            self.message_user(request, f"{updated} سفارش لغو شد و موجودی آن‌ها در صورت امکان برگشت داده شد.")

    action_mark_as_cancelled.short_description = "لغو سفارش (با برگرداندن موجودی در صورت امکان)"

@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "base_shipping_cost",
        "free_shipping_threshold",
        "is_active",
        "order",
    )
    list_editable = ("base_shipping_cost", "free_shipping_threshold", "is_active", "order")
    search_fields = ("name",)
    ordering = ("order", "name")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "description",
        "discount_percent",
        "discount_amount",
        "min_order_amount",
        "active",
        "valid_from",
        "valid_to",
        "for_first_order_only",
    )
    list_filter = ("active", "for_first_order_only", "valid_from", "valid_to")
    search_fields = ("code", "description")
    ordering = ("-created_at",)


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name",)
    ordering = ("order", "name")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "province",
        "delivery_available",
        "is_popular",
        "is_active",
        "order",
    )
    list_filter = ("province", "delivery_available", "is_popular", "is_active")
    list_editable = ("delivery_available", "is_popular", "is_active", "order")
    search_fields = ("name", "province__name")
    ordering = ("province__name", "order", "name")


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):
    list_display = (
        "identifier",
        "code",
        "created_at",
        "expires_at",
        "is_used",
        "attempts",
    )
    list_filter = ("is_used", "created_at")
    search_fields = ("identifier",)
    readonly_fields = ("identifier", "code", "created_at", "expires_at", "attempts")

    def has_add_permission(self, request):
        # تولید OTP فقط از طریق لاجیک برنامه؛ نه از طریق پنل
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone", "current_city", "notify_order_sms", "notify_promotions")
    search_fields = ("user__username", "full_name", "phone", "email")
    list_filter = ("current_city", "notify_order_sms", "notify_promotions")
    raw_id_fields = ("user",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "city", "is_default")
    list_filter = ("city", "is_default")
    search_fields = ("user__username", "label", "city", "district")
    raw_id_fields = ("user",)
    list_per_page = 50


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__username", "product__name")
    raw_id_fields = ("user", "product")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "subject", "message")
    raw_id_fields = ("user",)


@admin.register(OrderStats)
class OrderStatsAdmin(admin.ModelAdmin):
    """
    مدل پروکسی برای نمایش داشبورد فروش در ادمین.
    به‌جای لیست سفارش‌ها، یک صفحه‌ی آماری نمایش می‌دهد.
    """
    change_list_template = "admin/sales_dashboard.html"
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """
        این ویو داده‌های آماری را محاسبه کرده و به قالب داشبورد می‌فرستد.
        فقط سفارش‌های paid=True در آمار فروش شمرده می‌شوند.
        """
        # بازه‌های زمانی
        now = timezone.now()
        today = now.date()
        last_7_date = today - datetime.timedelta(days=6)

        # سفارش‌ها
        all_orders_qs = Order.objects.all()
        paid_orders_qs = all_orders_qs.filter(paid=True)

        total_orders = all_orders_qs.count()
        paid_orders = paid_orders_qs.count()
        unpaid_orders = total_orders - paid_orders

        # فروش کل (جمع مبلغ آیتم‌های سفارش‌های پرداخت‌شده)
        total_revenue = (
            OrderItem.objects.filter(order__paid=True)
            .aggregate(
                total=Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=0),
                )
            )["total"]
            or 0
        )

        # فروش و تعداد سفارش‌های امروز
        today_revenue = (
            OrderItem.objects.filter(order__paid=True, order__created_at__date=today)
            .aggregate(
                total=Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=0),
                )
            )["total"]
            or 0
        )
        today_orders = paid_orders_qs.filter(created_at__date=today).count()

        # فروش ۷ روز اخیر (برای نمودار)
        last_7_qs = (
            OrderItem.objects.filter(
                order__paid=True,
                order__created_at__date__gte=last_7_date,
            )
            .annotate(date=TruncDate("order__created_at"))
            .values("date")
            .annotate(
                revenue=Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=0),
                ),
                orders=Count("order", distinct=True),
            )
            .order_by("date")
        )
        last_7_map = {row["date"]: row for row in last_7_qs}

        days = [last_7_date + datetime.timedelta(days=i) for i in range(7)]
        chart_labels = [d.strftime("%Y-%m-%d") for d in days]
        chart_revenue = [int((last_7_map.get(d) or {}).get("revenue") or 0) for d in days]
        chart_orders = [int((last_7_map.get(d) or {}).get("orders") or 0) for d in days]

        # پرفروش‌ترین محصولات
        top_products = list(
            OrderItem.objects.filter(order__paid=True)
            .values("product_id", "product__name")
            .annotate(
                units=Sum("quantity"),
                revenue=Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=0),
                ),
            )
            .order_by("-revenue")[:10]
        )

        # فروش بر اساس شهر (تقریبی: براساس current_city پروفایل کاربر)
        sales_by_city = list(
            OrderItem.objects.filter(
                order__paid=True,
                order__user__profile__current_city__isnull=False,
            )
            .values("order__user__profile__current_city__name")
            .annotate(
                revenue=Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=0),
                ),
                orders=Count("order", distinct=True),
            )
            .order_by("-revenue")[:10]
        )

        extra_context = extra_context or {}
        extra_context.update(
            {
                "total_orders": total_orders,
                "paid_orders": paid_orders,
                "unpaid_orders": unpaid_orders,
                "total_revenue": int(total_revenue),
                "today_orders": today_orders,
                "today_revenue": int(today_revenue),
                "chart_labels": json.dumps(chart_labels),
                "chart_revenue": json.dumps(chart_revenue),
                "chart_orders": json.dumps(chart_orders),
                "top_products": top_products,
                "sales_by_city": sales_by_city,
            }
        )

        return super().changelist_view(request, extra_context=extra_context)


# تنظیم عنوان‌های کلی پنل مدیریت
admin.site.site_header = "مدیریت فروشگاه ایران مارکت"
admin.site.site_title = "پنل مدیریت ایران مارکت"
admin.site.index_title = "خوش آمدید به پنل مدیریت ایران مارکت"
