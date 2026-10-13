from django.urls import include, path

urlpatterns = [
    path('', include('accounts.urls')),
    path('nhan-su/', include('people.urls')),
    path('dao-tao/', include('academics.urls')),
    path('lop/', include('classes.urls')),
    path('dang-ky/', include('enrollment.urls')),
    path('diem/', include('grades.urls')),
    path('quy-che/', include('regulations.urls')),
    path('thong-ke/', include('reports.urls')),
    path('tien-do-hoc-tap/', include('tien_do_hoc_tap.urls')),
    path('diem-danh/', include('diem_danh.urls')),
    path('thong-bao/', include('thong_bao.urls')),
    path('tu-van-dang-ky/', include('tu_van_dang_ky.urls')),
    path('tom-tat-ket-qua/', include('tom_tat_ket_qua.urls')),
    path('hoi-dap-quy-che/', include('hoi_dap_quy_che.urls')),
]
