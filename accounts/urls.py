from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.trang_chu, name='trang_chu'),
    path('dang-nhap/', views.DangNhapView.as_view(), name='dang_nhap'),
    path('dang-xuat/', views.dang_xuat, name='dang_xuat'),
    path('tai-khoan/', views.DanhSachTaiKhoanView.as_view(), name='tai_khoan_danh_sach'),
    path('tai-khoan/tao/', views.TaoTaiKhoanView.as_view(), name='tai_khoan_tao'),
    path('tai-khoan/<int:pk>/sua/', views.CapNhatTaiKhoanView.as_view(), name='tai_khoan_sua'),
    path('tai-khoan/<int:pk>/khoa/', views.khoa_tai_khoan, name='tai_khoan_khoa'),
    path('tai-khoan/<int:pk>/mo-khoa/', views.mo_khoa_tai_khoan, name='tai_khoan_mo_khoa'),
    path('tai-khoan/<int:pk>/xoa/', views.XoaTaiKhoanView.as_view(), name='tai_khoan_xoa'),
    path('tai-khoan/<int:pk>/dat-lai-mat-khau/', views.dat_lai_mat_khau, name='tai_khoan_dat_lai_mat_khau'),
    path('thong-tin-ca-nhan/', views.thong_tin_ca_nhan, name='thong_tin_ca_nhan'),
    path('doi-mat-khau/', views.doi_mat_khau, name='doi_mat_khau'),
]
