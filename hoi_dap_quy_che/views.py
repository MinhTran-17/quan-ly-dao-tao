from django.contrib import messages
from django.shortcuts import render
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin

from .forms import CauHoiForm
from .gioi_han_tan_suat import kiem_tra_va_dem
from .services import hoi_dap_quy_che


class HoiDapMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP)


class TrangHoiDapView(HoiDapMixin, View):
    template_name = 'hoi_dap_quy_che/trang_chat.html'

    def get(self, request):
        return self._render(request, CauHoiForm(), None)

    def post(self, request):
        form = CauHoiForm(request.POST)
        if not form.is_valid():
            return self._render(request, form, None)

        duoc_phep, thong_bao = kiem_tra_va_dem(request.user)
        if not duoc_phep:
            messages.error(request, thong_bao)
            return self._render(request, form, None)

        ket_qua = hoi_dap_quy_che(form.cleaned_data['cau_hoi'])
        return self._render(request, CauHoiForm(), ket_qua)

    def _render(self, request, form, ket_qua):
        return render(request, self.template_name, {'form': form, 'ket_qua': ket_qua})
