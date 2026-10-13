from django.urls import path

from . import views

app_name = 'regulations'

urlpatterns = [
    path('', views.DanhSachTaiLieuView.as_view(), name='danh_sach'),
    path('tao/', views.TaiLieuQuyCheTaoView.as_view(), name='tao'),
    path('<int:pk>/sua/', views.TaiLieuQuyCheSuaView.as_view(), name='sua'),
    path('<int:pk>/xoa/', views.XoaTaiLieuView.as_view(), name='xoa'),
    path('<int:pk>/tai-ve/', views.tai_ve_view, name='tai_ve'),
]
