from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from ai_core.gioi_han_tan_suat import kiem_tra_va_dem
from people.models import SinhVien

from .services import tom_tat_ket_qua_hoc_tap


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class CoVanMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.CO_VAN_HOC_TAP,)


class TomTatCuaToiView(SinhVienMixin, View):
    template_name = 'tom_tat_ket_qua/trang_sinh_vien.html'

    def get(self, request):
        return render(request, self.template_name, {'ket_qua': None})

    def post(self, request):
        sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')
        duoc_phep, thong_bao = kiem_tra_va_dem(f'tom_tat_ket_qua:{request.user.pk}')
        if not duoc_phep:
            messages.error(request, thong_bao)
            return render(request, self.template_name, {'ket_qua': None})
        ket_qua = tom_tat_ket_qua_hoc_tap(sinh_vien)
        return render(request, self.template_name, {'ket_qua': ket_qua})


class TomTatChoCoVanView(CoVanMixin, View):
    template_name = 'tom_tat_ket_qua/trang_co_van.html'

    def _danh_sach_sinh_vien(self, co_van):
        if co_van is None:
            return SinhVien.objects.none()
        return SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien')

    def get(self, request):
        co_van = getattr(request.user, 'ho_so_co_van', None)
        return render(request, self.template_name, {
            'danh_sach_sinh_vien': self._danh_sach_sinh_vien(co_van),
            'sinh_vien_chon': None,
            'ket_qua': None,
        })

    def post(self, request):
        co_van = getattr(request.user, 'ho_so_co_van', None)
        if co_van is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ cố vấn học tập.')
            return redirect('accounts:trang_chu')

        ma_sinh_vien = request.POST.get('ma_sinh_vien', '').strip()
        sinh_vien = get_object_or_404(SinhVien, pk=ma_sinh_vien)
        if sinh_vien.ma_lop.ma_co_van_id != co_van.pk:
            raise PermissionDenied('Sinh viên này không thuộc lớp bạn phụ trách.')

        duoc_phep, thong_bao = kiem_tra_va_dem(f'tom_tat_ket_qua:{request.user.pk}')
        if not duoc_phep:
            messages.error(request, thong_bao)
            return render(request, self.template_name, {
                'danh_sach_sinh_vien': self._danh_sach_sinh_vien(co_van),
                'sinh_vien_chon': sinh_vien,
                'ket_qua': None,
            })

        ket_qua = tom_tat_ket_qua_hoc_tap(sinh_vien)
        return render(request, self.template_name, {
            'danh_sach_sinh_vien': self._danh_sach_sinh_vien(co_van),
            'sinh_vien_chon': sinh_vien,
            'ket_qua': ket_qua,
        })
