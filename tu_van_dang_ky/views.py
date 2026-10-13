from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from ai_core.gioi_han_tan_suat import kiem_tra_va_dem

from .forms import TuVanForm
from .services import tu_van_dang_ky


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class TuVanDangKyView(SinhVienMixin, FormView):
    template_name = 'tu_van_dang_ky/trang_tu_van.html'
    form_class = TuVanForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('ket_qua', None)
        return context

    def form_valid(self, form):
        sinh_vien = getattr(self.request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            messages.error(self.request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')

        duoc_phep, thong_bao = kiem_tra_va_dem(f'tu_van_dang_ky:{self.request.user.pk}')
        if not duoc_phep:
            messages.error(self.request, thong_bao)
            return self.render_to_response(self.get_context_data(form=form, ket_qua=None))

        ket_qua = tu_van_dang_ky(
            sinh_vien,
            form.cleaned_data['hoc_ky'],
            form.cleaned_data['nam_hoc'],
            form.cleaned_data.get('ghi_chu', ''),
        )
        return self.render_to_response(self.get_context_data(form=form, ket_qua=ket_qua))
