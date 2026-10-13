from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        # tai_khoan không có cột last_login (xem docs/erd.md), nên phải ngắt
        # tín hiệu mặc định của Django để tránh lỗi khi đăng nhập thành công.
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.disconnect(update_last_login)
