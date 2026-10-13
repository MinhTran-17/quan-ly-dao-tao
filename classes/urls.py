from django.urls import path

from . import views

app_name = 'classes'

urlpatterns = [
    path('lop-hoc-phan/', views.DanhSachLopHocPhanView.as_view(), name='lop_hoc_phan_danh_sach'),
    path('lop-hoc-phan/tao/', views.TaoLopHocPhanView.as_view(), name='lop_hoc_phan_tao'),
    path('lop-hoc-phan/<str:pk>/sua/', views.CapNhatLopHocPhanView.as_view(), name='lop_hoc_phan_sua'),

    path('lich-hoc/', views.DanhSachLichHocView.as_view(), name='lich_hoc_danh_sach'),
    path('lich-hoc/tao/', views.TaoLichHocView.as_view(), name='lich_hoc_tao'),
    path('lich-hoc/<int:pk>/sua/', views.CapNhatLichHocView.as_view(), name='lich_hoc_sua'),
    path('lich-hoc/<int:pk>/xoa/', views.XoaLichHocView.as_view(), name='lich_hoc_xoa'),

    path('lop-phu-trach/', views.LopPhuTrachView.as_view(), name='lop_phu_trach'),
    path('lich-giang-day/', views.LichGiangDayView.as_view(), name='lich_giang_day'),

    path('lich-thi/', views.DanhSachLichThiView.as_view(), name='lich_thi_danh_sach'),
    path('lich-thi/tao/', views.TaoLichThiView.as_view(), name='lich_thi_tao'),
    path('lich-thi/<int:pk>/sua/', views.CapNhatLichThiView.as_view(), name='lich_thi_sua'),
    path('lich-thi/<int:pk>/xoa/', views.XoaLichThiView.as_view(), name='lich_thi_xoa'),
]
