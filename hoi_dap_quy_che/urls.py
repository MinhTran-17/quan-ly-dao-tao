from django.urls import path

from . import views

app_name = 'hoi_dap_quy_che'

urlpatterns = [
    path('', views.TrangHoiDapView.as_view(), name='trang_chat'),
]
