from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from people.models import SinhVien

from .services import tinh_tien_do


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class CoVanMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.CO_VAN_HOC_TAP,)


class TienDoCuaToiView(SinhVienMixin, View):
    template_name = 'tien_do_hoc_tap/trang_sinh_vien.html'

    def get(self, request):
        sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')
        return render(request, self.template_name, {'ket_qua': tinh_tien_do(sinh_vien, chi_diem_da_cong_bo=True)})


class TienDoChoCoVanView(CoVanMixin, View):
    template_name = 'tien_do_hoc_tap/trang_co_van.html'

    def _danh_sach_sinh_vien(self, co_van):
        if co_van is None:
            return SinhVien.objects.none()
        return SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien')

    def get(self, request):
        co_van = getattr(request.user, 'ho_so_co_van', None)
        ma_sinh_vien = request.GET.get('ma_sinh_vien', '').strip()
        sinh_vien_chon = None
        ket_qua = None
        if ma_sinh_vien:
            sinh_vien_chon = get_object_or_404(SinhVien, pk=ma_sinh_vien)
            if co_van is None or sinh_vien_chon.ma_lop.ma_co_van_id != co_van.pk:
                raise PermissionDenied('Sinh viên này không thuộc lớp bạn phụ trách.')
            ket_qua = tinh_tien_do(sinh_vien_chon)
        return render(request, self.template_name, {
            'danh_sach_sinh_vien': self._danh_sach_sinh_vien(co_van),
            'sinh_vien_chon': sinh_vien_chon,
            'ket_qua': ket_qua,
        })
