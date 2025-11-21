// shop/static/shop/js/cart.js
// مدیریت AJAX برای همه فرم‌های افزودن به سبد خرید (.js-add-to-cart-form)

(function () {
    // گرفتن CSRF از کوکی (الگوی رسمی جنگو)
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            var cookies = document.cookie.split(";");
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                // آیا این کوکی با نام مورد نظر شروع می‌شود؟
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // نمایش Toast کنار نوار بالای سایت (سمت راست، نزدیک آیکون سبد)
    function showCartToast(message, isError) {
        var container = document.getElementById("cart-toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "cart-toast-container";
            // موقعیت کلی را با کلاس کنترل می‌کنیم (CSS در base.html)
            container.className = "cart-toast-container position-fixed";
            container.style.zIndex = "1080";
            document.body.appendChild(container);
        }

        var alert = document.createElement("div");
        alert.className =
            "cart-toast-alert shadow-sm " +
            (isError ? "alert alert-danger" : "alert alert-success");

        alert.textContent = message || (isError ? "خطایی رخ داد." : "به سبد خرید اضافه شد.");

        container.appendChild(alert);

        // بعد از مدتی محو شود (با انیمیشن نرم)
        setTimeout(function () {
            alert.classList.add("is-hiding");
            alert.addEventListener("transitionend", function () {
                if (alert && alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            });
        }, 2500);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var forms = document.querySelectorAll(".js-add-to-cart-form");
        if (!forms.length) {
            return;
        }

        var csrftoken = getCookie("csrftoken");

        forms.forEach(function (form) {
            form.addEventListener("submit", function (e) {
                e.preventDefault();

                var url = form.action;
                var formData = new FormData(form);

                fetch(url, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": csrftoken
                    },
                    body: formData
                })
                    .then(function (response) {
                        var contentType = response.headers.get("content-type") || "";
                        if (contentType.indexOf("application/json") !== -1) {
                            return response.json();
                        }
                        // اگر JSON نبود (غیرمنتظره)، برای اینکه UX خراب نشود صفحه را رفرش می‌کنیم
                        window.location.reload();
                        return null;
                    })
                    .then(function (data) {
                        if (!data) {
                            return;
                        }

                        if (data.success) {
                            // به‌روزرسانی شمارنده سبد اگر در DOM وجود داشته باشد
                            var cartCountEl = document.getElementById("cart-count");
                            if (cartCountEl && typeof data.cart_count !== "undefined") {
                                cartCountEl.textContent = data.cart_count;
                            }
                            showCartToast(data.message || "محصول به سبد خرید اضافه شد.", false);
                        } else {
                            showCartToast(data.message || "خطا در افزودن به سبد خرید.", true);
                        }
                    })
                    .catch(function () {
                        showCartToast("خطایی رخ داد؛ دوباره تلاش کنید.", true);
                    });
            });
        });
    });
})();
