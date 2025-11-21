# shop/notifications.py
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def _get_order_email(order):
    """
    ایمیل مقصد نوتیفیکیشن را از Order استخراج می‌کند.
    اولویت:
    - ایمیل خود Order (اگر فیلدی داری)
    - ایمیل user مرتبط با سفارش
    """
    # اگر در Order فیلد email داری، می‌توانی اینجا استفاده‌اش کنی:
    email = getattr(order, "email", None)

    if not email and order.user_id and order.user and order.user.email:
        email = order.user.email

    return email


def send_order_created(order):
    """
    نوتیفیکیشن بعد از ثبت سفارش (قبل از پرداخت).
    """
    to_email = _get_order_email(order)
    if not to_email:
        return  # ایمیل نداریم، نوتیفیکیشن را نادیده می‌گیریم.

    subject = f"ثبت سفارش جدید #{order.id} در ایران مارکت"
    created_str = timezone.localtime(order.created_at).strftime("%Y/%m/%d - %H:%M")

    message = (
        f"{order.first_name} عزیز،\n\n"
        f"سفارش شما با شماره {order.id} در تاریخ {created_str} ثبت شد.\n"
        f"مبلغ قابل پرداخت: {order.total_price:,.0f} تومان\n\n"
        "برای تکمیل، لطفاً پرداخت را انجام دهید.\n"
        "ایران مارکت"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=True,
    )


def send_payment_success(order):
    """
    نوتیفیکیشن بعد از پرداخت موفق.
    """
    to_email = _get_order_email(order)
    if not to_email:
        return

    subject = f"پرداخت سفارش #{order.id} با موفقیت انجام شد"
    created_str = timezone.localtime(order.created_at).strftime("%Y/%m/%d - %H:%M")

    message = (
        f"{order.first_name} عزیز،\n\n"
        f"پرداخت سفارش شماره {order.id} با موفقیت ثبت شد.\n"
        f"تاریخ ثبت سفارش: {created_str}\n"
        f"مبلغ پرداختی: {order.total_price:,.0f} تومان\n\n"
        "سفارش شما در صف آماده‌سازی است.\n"
        "ایران مارکت"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=True,
    )


def send_order_status_changed(order, old_status, new_status):
    """
    نوتیفیکیشن تغییر وضعیت سفارش (مثلاً ارسال شد، تحویل شد، لغو شد).
    """
    to_email = _get_order_email(order)
    if not to_email:
        return

    subject = f"به‌روزرسانی وضعیت سفارش #{order.id}"

    # متن ساده بر اساس وضعیت جدید
    status_map = {
        getattr(order, "STATUS_PENDING", "pending"): "در انتظار بررسی",
        getattr(order, "STATUS_PROCESSING", "processing"): "در حال آماده‌سازی",
        getattr(order, "STATUS_SENT", "sent"): "ارسال شده",
        getattr(order, "STATUS_DELIVERED", "delivered"): "تحویل شده",
        getattr(order, "STATUS_CANCELLED", "cancelled"): "لغو شده",
    }

    new_status_label = status_map.get(new_status, str(new_status))

    message = (
        f"{order.first_name} عزیز،\n\n"
        f"وضعیت سفارش شماره {order.id} به «{new_status_label}» تغییر کرد.\n\n"
        "ایران مارکت"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[to_email],
        fail_silently=True,
    )


# ---- آماده‌سازی برای SMS (فعلاً فقط اسکلت) ----

def send_sms(to_phone, text):
    """
    اسکلت ارسال SMS.
    در آینده می‌توانی اینجا به وب‌سرویس SMS (SMS.ir, Kavenegar, ...) وصل شوی.
    فعلاً کاری نمی‌کند.
    """
    # TODO: اتصال به درگاه SMS
    return
