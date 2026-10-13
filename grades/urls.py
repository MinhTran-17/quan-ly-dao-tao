from django.urls import path

from . import views

app_name = 'grades'

urlpatterns = [
    path('lop-phu-trach/<str:ma_lop_hoc_phan>/', views.BangDiemLopView.as_view(), name='bang_diem_lop'),
    path('dang-ky/<int:ma_dang_ky>/nhap/', views.nhap_diem_view, name='nhap_diem'),
    path('lop-phu-trach/<str:ma_lop_hoc_phan>/cong-bo/', views.cong_bo_diem_lop_view, name='cong_bo_diem_lop'),

    path(
        'phong-dao-tao/lop/<str:ma_lop_hoc_phan>/',
        views.BangDiemLopPhongDaoTaoView.as_view(),
        name='bang_diem_lop_phong_dao_tao',
    ),
    path('dang-ky/<int:ma_dang_ky>/sua/', views.sua_diem_view, name='sua_diem'),

    path('sinh-vien/<str:ma_sinh_vien>/', views.bang_diem_sinh_vien_view, name='bang_diem_sinh_vien'),
    path('toi/', views.bang_diem_cua_toi_view, name='bang_diem_cua_toi'),
    path('toi/xuat-pdf/', views.xuat_bang_diem_pdf_view, name='xuat_bang_diem_pdf'),

    path('canh-bao/co-van/', views.DanhSachCanhBaoCoVanView.as_view(), name='canh_bao_co_van'),
    path('canh-bao/phong-dao-tao/', views.DanhSachCanhBaoPhongDaoTaoView.as_view(), name='canh_bao_phong_dao_tao'),
]
