from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from ai_core import lich_su_chat

from .chat import ket_qua_thanh_dict
from .forms import CauHoiForm
from .gioi_han_tan_suat import kiem_tra_va_dem
from .services import hoi_dap_quy_che

LOI_CHAO = (
    'Mình trả lời câu hỏi về quy chế đào tạo, chỉ dựa trên các tài liệu quy chế Phòng Đào tạo đã tải lên và có '
    'trích nguồn Điều, khoản. Câu hỏi ngoài quy chế sẽ không được trả lời.'
)


class HoiDapMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP)


class TrangHoiDapView(HoiDapMixin, View):
    template_name = 'hoi_dap_quy_che/trang_chat.html'

    def _khoa(self, request):
        return f'hoi_dap:{request.user.pk}'

    def get(self, request):
        gioi_han = CauHoiForm.base_fields['cau_hoi'].max_length
        return render(request, self.template_name, {
            'lich_su': lich_su_chat.doc(request, self._khoa(request)),
            'mau_tra_loi': 'hoi_dap_quy_che/_tra_loi_chat.html',
            'loi_chao': LOI_CHAO,
            'goi_y_o_nhap': 'Ví dụ: Sinh viên được học cải thiện điểm như thế nào?',
            'gioi_han': gioi_han,
        })

    def post(self, request):
        if request.POST.get('xoa_lich_su'):
            lich_su_chat.xoa(request, self._khoa(request))
            return redirect('hoi_dap_quy_che:trang_chat')
        form = CauHoiForm({'cau_hoi': lich_su_chat.cau_gui_len(request)})
        if not form.is_valid():
            messages.error(request, ' '.join(form.errors['cau_hoi']))
            return redirect('hoi_dap_quy_che:trang_chat')

        duoc_phep, thong_bao = kiem_tra_va_dem(request.user)
        if not duoc_phep:
            messages.error(request, thong_bao)
            return redirect('hoi_dap_quy_che:trang_chat')

        cau_hoi = form.cleaned_data['cau_hoi']
        lich_su_chat.them(request, self._khoa(request), cau_hoi, ket_qua_thanh_dict(hoi_dap_quy_che(cau_hoi)))
        return redirect('hoi_dap_quy_che:trang_chat')
