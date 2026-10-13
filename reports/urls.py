from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('si-so-theo-lop/', views.SiSoTheoLopReportView.as_view(), name='si_so_theo_lop'),
    path('si-so-theo-lop/xuat-excel/', views.XuatExcelSiSoTheoLopView.as_view(), name='si_so_theo_lop_xuat_excel'),
    path('hoc-phan-nhieu-dang-ky/', views.HocPhanNhieuDangKyReportView.as_view(), name='hoc_phan_nhieu_dang_ky'),
    path(
        'hoc-phan-nhieu-dang-ky/xuat-excel/',
        views.XuatExcelHocPhanNhieuDangKyView.as_view(),
        name='hoc_phan_nhieu_dang_ky_xuat_excel',
    ),
    path('ket-qua-hoc-tap/', views.KetQuaHocTapReportView.as_view(), name='ket_qua_hoc_tap'),
    path('ket-qua-hoc-tap/xuat-excel/', views.XuatExcelKetQuaHocTapView.as_view(), name='ket_qua_hoc_tap_xuat_excel'),
]
