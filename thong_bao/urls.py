from django.urls import path

from . import views

app_name = 'thong_bao'

urlpatterns = [
    path('', views.DanhSachThongBaoView.as_view(), name='danh_sach'),
    path('<int:pk>/', views.ChiTietThongBaoView.as_view(), name='chi_tiet'),
    path('gui/phong-dao-tao/', views.GuiThongBaoPhongDaoTaoView.as_view(), name='gui_phong_dao_tao'),
    path('da-gui/', views.DanhSachThongBaoDaGuiView.as_view(), name='da_gui'),
    path('gui/giang-vien/', views.GuiThongBaoGiangVienView.as_view(), name='gui_giang_vien'),
    path('gui/co-van/', views.GuiThongBaoCoVanView.as_view(), name='gui_co_van'),
]
