from django import forms
from .models import Order, Review


class CheckoutForm(forms.ModelForm):
    coupon_code = forms.CharField(
        label="کد تخفیف",
        required=False,
        help_text="اگر کد تخفیف دارید، اینجا وارد کنید.",
    )

    class Meta:
        model = Order
        fields = ["first_name", "last_name", "phone", "address"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "phone": "شماره تماس",
            "address": "آدرس کامل",
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "comment"]
        labels = {
            "rating": "امتیاز شما",
            "title": "عنوان نظر",
            "comment": "متن نظر",
        }
        widgets = {
            "rating": forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)]
            ),
            "title": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "comment": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 3}
            ),
        }

