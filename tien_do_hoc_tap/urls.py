from django.urls import path

from . import views

app_name = 'tien_do_hoc_tap'

urlpatterns = [
    path('cua-toi/', views.TienDoCuaToiView.as_view(), name='cua_toi'),
    path('co-van/', views.TienDoChoCoVanView.as_view(), name='co_van'),
]
