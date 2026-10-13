from django.urls import path

from . import views

app_name = 'tu_van_dang_ky'

urlpatterns = [
    path('', views.TuVanDangKyView.as_view(), name='trang_tu_van'),
]
