from django.urls import path

from . import views

app_name = 'tom_tat_ket_qua'

urlpatterns = [
    path('toi/', views.TomTatCuaToiView.as_view(), name='toi'),
    path('co-van/', views.TomTatChoCoVanView.as_view(), name='co_van'),
]
