from django.urls import path

from . import views

app_name = 'diem_danh'

urlpatterns = [
    path('lop/<str:ma_lop_hoc_phan>/', views.DiemDanhLopView.as_view(), name='diem_danh_lop'),
    path('lop/<str:ma_lop_hoc_phan>/lich-su/', views.LichSuDiemDanhLopView.as_view(), name='lich_su_diem_danh_lop'),
    path('cua-toi/', views.LichSuDiemDanhSinhVienView.as_view(), name='lich_su_cua_toi'),
]
