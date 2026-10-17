from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from ai_core import lich_su_chat
from ai_core.gioi_han_tan_suat import kiem_tra_va_dem

from .chat import chon_hoc_ky, ket_qua_thanh_dict, tra_loi_ngay_thanh_dict
from .services import tu_van_dang_ky

GIOI_HAN_KY_TU = 300
LOI_CHAO = (
    'Mình gợi ý nên đăng ký lớp học phần nào, dựa trên tiên quyết, lịch học và sĩ số do hệ thống tính sẵn. Hãy nói '
    'học kỳ muốn đăng ký và mong muốn của bạn, ví dụ "Tư vấn học kỳ 1 năm học 2025-2026, em muốn học các môn về AI".'
)


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class TuVanDangKyView(SinhVienMixin, View):
    template_name = 'tu_van_dang_ky/trang_tu_van.html'

    def _sinh_vien(self, request):
        return getattr(request.user, 'ho_so_sinh_vien', None)

    def get(self, request):
        sinh_vien = self._sinh_vien(request)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')
        return render(request, self.template_name, {
            'lich_su': lich_su_chat.doc(request, f'tu_van:{sinh_vien.pk}'),
            'mau_tra_loi': 'tu_van_dang_ky/_tra_loi_chat.html',
            'loi_chao': LOI_CHAO,
            'goi_y_o_nhap': 'Ví dụ: Tư vấn học kỳ 1 năm học 2025-2026, em muốn tránh học thứ 7',
            'gioi_han': GIOI_HAN_KY_TU,
        })

    def post(self, request):
        sinh_vien = self._sinh_vien(request)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')
        khoa = f'tu_van:{sinh_vien.pk}'
        if request.POST.get('xoa_lich_su'):
            lich_su_chat.xoa(request, khoa)
            return redirect('tu_van_dang_ky:trang_tu_van')
        cau = lich_su_chat.cau_gui_len(request)
        if not cau:
            messages.error(request, 'Vui lòng nhập câu hỏi.')
            return redirect('tu_van_dang_ky:trang_tu_van')
        if len(cau) > GIOI_HAN_KY_TU:
            messages.error(request, f'Câu hỏi tối đa {GIOI_HAN_KY_TU} ký tự.')
            return redirect('tu_van_dang_ky:trang_tu_van')

        lua_chon = chon_hoc_ky(cau)
        if lua_chon.tra_loi_ngay:
            lich_su_chat.them(request, khoa, cau, tra_loi_ngay_thanh_dict(lua_chon.tra_loi_ngay))
            return redirect('tu_van_dang_ky:trang_tu_van')
        duoc_phep, thong_bao = kiem_tra_va_dem(f'tu_van_dang_ky:{request.user.pk}')
        if not duoc_phep:
            messages.error(request, thong_bao)
            return redirect('tu_van_dang_ky:trang_tu_van')
        # Cả câu gõ làm "ghi chú của sinh viên" — đặt trong khối dữ liệu không tin cậy của prompt.
        ket_qua = tu_van_dang_ky(sinh_vien, lua_chon.hoc_ky, lua_chon.nam_hoc, cau)
        lich_su_chat.them(request, khoa, cau, ket_qua_thanh_dict(ket_qua, lua_chon))
        return redirect('tu_van_dang_ky:trang_tu_van')
