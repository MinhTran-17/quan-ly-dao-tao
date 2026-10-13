from django.urls import path

from . import views

app_name = 'enrollment'

urlpatterns = [
    path('lop-dang-mo/', views.DanhSachLopDangMoView.as_view(), name='lop_dang_mo'),
    path('lop-dang-mo/<str:pk>/dang-ky/', views.dang_ky_hoc_phan_view, name='dang_ky'),
    path('dang-ky/<int:pk>/huy/', views.huy_dang_ky_view, name='huy_dang_ky'),
    path('thoi-khoa-bieu/', views.ThoiKhoaBieuView.as_view(), name='thoi_khoa_bieu'),
    path('thoi-khoa-bieu/xuat-pdf/', views.xuat_thoi_khoa_bieu_pdf_view, name='thoi_khoa_bieu_xuat_pdf'),
    path('lich-su-dang-ky/', views.LichSuDangKyView.as_view(), name='lich_su_dang_ky'),

    path('lop-hoc-phan/<str:ma_lop_hoc_phan>/sinh-vien/', views.DanhSachSinhVienLopView.as_view(), name='danh_sach_sinh_vien_lop'),
    path(
        'lop-hoc-phan/<str:ma_lop_hoc_phan>/sinh-vien/xuat-excel/',
        views.xuat_excel_sinh_vien_lop_view, name='xuat_excel_sinh_vien_lop',
    ),
    path('tra-cuu-sinh-vien/', views.TraCuuLichSuDangKyView.as_view(), name='tra_cuu_lich_su'),

    path('sinh-vien-phu-trach/', views.DanhSachSinhVienCoVanView.as_view(), name='sinh_vien_phu_trach'),
    path('sinh-vien-phu-trach/xuat-excel/', views.xuat_excel_sinh_vien_phu_trach_view, name='xuat_excel_sinh_vien_phu_trach'),

    path('lich-thi/', views.LichThiSinhVienView.as_view(), name='lich_thi'),
    path('lich-thi/xuat-pdf/', views.xuat_lich_thi_pdf_view, name='lich_thi_xuat_pdf'),
]
