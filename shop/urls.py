# shop/urls.py
from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),

    path("categories/", views.category_list, name="category_list"),
    path("offers/", views.offers_list, name="offers_list"),
    path("products/new/", views.new_products_list, name="new_products"),
    path("products/best-sellers/", views.best_sellers_list, name="best_sellers"),
    path("category/<str:slug>/", views.category_detail, name="category_detail"),
    path("product/<str:slug>/", views.product_detail, name="product_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("product/<int:product_id>/review/", views.add_review, name="add_review"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),

    path("search/", views.product_search, name="product_search"),
    path("offers/", views.offers_list, name="offers_list"),

    # OTP Auth
    path("auth/login/", views.login_view, name="login"),
    path("auth/verify/", views.verify_otp_view, name="verify_otp"),
    path("auth/logout/", views.logout_view, name="logout"),
        # حساب کاربری
    path("account/", views.account_dashboard, name="account_dashboard"),
    path("account/profile/", views.account_profile, name="account_profile"),
    path("account/addresses/", views.account_addresses, name="account_addresses"),
    path(
        "account/addresses/<int:address_id>/delete/",
        views.account_address_delete,
        name="account_address_delete",
    ),
    path(
        "account/addresses/<int:address_id>/default/",
        views.account_address_set_default,
        name="account_address_set_default",
    ),
        path("account/orders/", views.account_orders, name="account_orders"),
    path("account/orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path(
        "account/orders/<int:order_id>/cancel/",
        views.order_cancel,
        name="order_cancel",
    ),

    path("account/wishlist/", views.account_wishlist, name="account_wishlist"),
    path(
        "account/wishlist/add/<int:product_id>/",
        views.wishlist_add,
        name="wishlist_add",
    ),
    path(
        "account/wishlist/remove/<int:product_id>/",
        views.wishlist_remove,
        name="wishlist_remove",
    ),
    path(
        "account/notifications/",
        views.account_notifications,
        name="account_notifications",
    ),
    path("account/support/", views.account_support, name="account_support"),
    path("location/set-city/", views.set_city, name="set_city"),
    path("payment/<int:order_id>/", views.payment_start, name="payment_start"),
    path(
        "payment/<int:order_id>/<str:status>/",
        views.payment_callback,
        name="payment_callback",
    ),
    path("set-city/", views.set_city, name="set_city"),
        # صفحات راهنما و اطلاعات
    path("about/", views.about, name="about"),
    path("buying-guide/", views.buying_guide, name="buying_guide"),
    path("shipping-methods/", views.shipping_methods, name="shipping_methods"),
    path("return-policy/", views.return_policy, name="return_policy"),
    path("faq/", views.faq, name="faq"),


]
