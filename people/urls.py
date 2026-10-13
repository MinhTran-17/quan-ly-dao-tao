from django.urls import path

from . import views

app_name = 'people'

urlpatterns = [
    path('sinh-vien/', views.DanhSachSinhVienView.as_view(), name='sinh_vien_danh_sach'),
    path('sinh-vien/tao/', views.TaoSinhVienView.as_view(), name='sinh_vien_tao'),
    path('sinh-vien/<str:pk>/sua/', views.CapNhatSinhVienView.as_view(), name='sinh_vien_sua'),
    path('sinh-vien/<str:pk>/xoa/', views.XoaSinhVienView.as_view(), name='sinh_vien_xoa'),
    path('sinh-vien/nhap-excel/', views.NhapSinhVienExcelView.as_view(), name='sinh_vien_nhap_excel'),
    path('sinh-vien/nhap-excel/mau/', views.TaiMauSinhVienExcelView.as_view(), name='sinh_vien_mau_excel'),

    path('giang-vien/', views.DanhSachGiangVienView.as_view(), name='giang_vien_danh_sach'),
    path('giang-vien/tao/', views.TaoGiangVienView.as_view(), name='giang_vien_tao'),
    path('giang-vien/<str:pk>/sua/', views.CapNhatGiangVienView.as_view(), name='giang_vien_sua'),
    path('giang-vien/<str:pk>/xoa/', views.XoaGiangVienView.as_view(), name='giang_vien_xoa'),

    path('co-van/', views.DanhSachCoVanView.as_view(), name='co_van_danh_sach'),
    path('co-van/tao/', views.TaoCoVanView.as_view(), name='co_van_tao'),
    path('co-van/<str:pk>/sua/', views.CapNhatCoVanView.as_view(), name='co_van_sua'),
    path('co-van/<str:pk>/xoa/', views.XoaCoVanView.as_view(), name='co_van_xoa'),
]
