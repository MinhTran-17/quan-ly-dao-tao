from django.urls import path

from . import views

app_name = 'academics'

urlpatterns = [
    path('nganh/', views.DanhSachNganhHocView.as_view(), name='nganh_hoc_danh_sach'),
    path('nganh/tao/', views.TaoNganhHocView.as_view(), name='nganh_hoc_tao'),
    path('nganh/<str:pk>/sua/', views.CapNhatNganhHocView.as_view(), name='nganh_hoc_sua'),
    path('nganh/<str:pk>/xoa/', views.XoaNganhHocView.as_view(), name='nganh_hoc_xoa'),

    path('lop-hanh-chinh/', views.DanhSachLopHanhChinhView.as_view(), name='lop_hanh_chinh_danh_sach'),
    path('lop-hanh-chinh/tao/', views.TaoLopHanhChinhView.as_view(), name='lop_hanh_chinh_tao'),
    path('lop-hanh-chinh/<str:pk>/sua/', views.CapNhatLopHanhChinhView.as_view(), name='lop_hanh_chinh_sua'),

    path('hoc-phan/', views.DanhSachHocPhanView.as_view(), name='hoc_phan_danh_sach'),
    path('hoc-phan/tao/', views.TaoHocPhanView.as_view(), name='hoc_phan_tao'),
    path('hoc-phan/<str:pk>/sua/', views.CapNhatHocPhanView.as_view(), name='hoc_phan_sua'),
    path('hoc-phan/<str:pk>/xoa/', views.XoaHocPhanView.as_view(), name='hoc_phan_xoa'),

    path('dieu-kien-tien-quyet/', views.DanhSachDieuKienTienQuyetView.as_view(), name='dieu_kien_tien_quyet_danh_sach'),
    path('dieu-kien-tien-quyet/tao/', views.TaoDieuKienTienQuyetView.as_view(), name='dieu_kien_tien_quyet_tao'),
    path(
        'dieu-kien-tien-quyet/<int:pk>/sua/',
        views.CapNhatDieuKienTienQuyetView.as_view(),
        name='dieu_kien_tien_quyet_sua',
    ),
    path('dieu-kien-tien-quyet/<int:pk>/xoa/', views.XoaDieuKienTienQuyetView.as_view(), name='dieu_kien_tien_quyet_xoa'),

    path('hoc-ky/', views.DanhSachHocKyView.as_view(), name='hoc_ky_danh_sach'),
    path('hoc-ky/tao/', views.TaoHocKyView.as_view(), name='hoc_ky_tao'),
    path('hoc-ky/<int:pk>/sua/', views.CapNhatHocKyView.as_view(), name='hoc_ky_sua'),
    path('hoc-ky/<int:pk>/xoa/', views.XoaHocKyView.as_view(), name='hoc_ky_xoa'),

    path('dot-dang-ky/', views.DanhSachDotDangKyView.as_view(), name='dot_dang_ky_danh_sach'),
    path('dot-dang-ky/tao/', views.TaoDotDangKyView.as_view(), name='dot_dang_ky_tao'),
    path('dot-dang-ky/<int:pk>/sua/', views.CapNhatDotDangKyView.as_view(), name='dot_dang_ky_sua'),
    path('dot-dang-ky/<int:pk>/xoa/', views.XoaDotDangKyView.as_view(), name='dot_dang_ky_xoa'),

    path('chuong-trinh/', views.DanhSachChuongTrinhDaoTaoView.as_view(), name='chuong_trinh_danh_sach'),
    path('chuong-trinh/tao/', views.TaoChuongTrinhDaoTaoView.as_view(), name='chuong_trinh_tao'),
    path('chuong-trinh/<int:pk>/sua/', views.CapNhatChuongTrinhDaoTaoView.as_view(), name='chuong_trinh_sua'),
    path('chuong-trinh/<int:pk>/xoa/', views.XoaChuongTrinhDaoTaoView.as_view(), name='chuong_trinh_xoa'),
    path('chuong-trinh/<int:pk>/', views.ChiTietChuongTrinhView.as_view(), name='chuong_trinh_chi_tiet'),
    path(
        'chuong-trinh/chi-tiet/<int:pk>/sua/',
        views.SuaChiTietChuongTrinhView.as_view(),
        name='chuong_trinh_chi_tiet_sua',
    ),
    path('chuong-trinh/chi-tiet/<int:pk>/xoa/', views.xoa_chi_tiet_chuong_trinh, name='chuong_trinh_chi_tiet_xoa'),
]
