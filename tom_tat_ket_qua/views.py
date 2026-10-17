from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from ai_core import lich_su_chat
from ai_core.gioi_han_tan_suat import kiem_tra_va_dem
from people.models import SinhVien

from .chat import chon_pham_vi, ket_qua_thanh_dict, tra_loi_ngay_thanh_dict
from .services import tom_tat_ket_qua_hoc_tap

GIOI_HAN_KY_TU = 300
LOI_CHAO = (
    'Mình tóm tắt kết quả học tập theo học kỳ, năm học hoặc toàn khóa, chỉ dựa trên điểm do hệ thống tính. '
    'Hãy gõ ví dụ "Tóm tắt học kỳ 1 năm học 2024-2025", "Tóm tắt năm học 2024-2025" hoặc "Tóm tắt toàn khóa".'
)


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class CoVanMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.CO_VAN_HOC_TAP,)


def xu_ly_tin_nhan(request, sinh_vien, khoa_lich_su):
    """Nhận một tin nhắn (POST), trả lời và lưu vào lịch sử chat. Chọn phạm vi trước: câu không cần AI (chưa có
    điểm, phạm vi không có dữ liệu, câu không liên quan) được trả lời ngay, không tính vào giới hạn tần suất."""
    if request.POST.get('xoa_lich_su'):
        lich_su_chat.xoa(request, khoa_lich_su)
        return
    cau = lich_su_chat.cau_gui_len(request)
    if not cau:
        messages.error(request, 'Vui lòng nhập câu hỏi.')
        return
    if len(cau) > GIOI_HAN_KY_TU:
        messages.error(request, f'Câu hỏi tối đa {GIOI_HAN_KY_TU} ký tự.')
        return

    lua_chon = chon_pham_vi(sinh_vien, cau)
    if lua_chon.tra_loi_ngay:
        lich_su_chat.them(request, khoa_lich_su, cau, tra_loi_ngay_thanh_dict(lua_chon.tra_loi_ngay))
        return
    duoc_phep, thong_bao = kiem_tra_va_dem(f'tom_tat_ket_qua:{request.user.pk}')
    if not duoc_phep:
        messages.error(request, thong_bao)
        return
    ket_qua = tom_tat_ket_qua_hoc_tap(
        sinh_vien, hoc_ky=lua_chon.hoc_ky, nam_hoc=lua_chon.nam_hoc, mo_ta_pham_vi=lua_chon.mo_ta,
    )
    lich_su_chat.them(request, khoa_lich_su, cau, ket_qua_thanh_dict(ket_qua, lua_chon))


def ngu_canh_chat(request, sinh_vien, khoa_lich_su):
    return {
        'lich_su': lich_su_chat.doc(request, khoa_lich_su),
        'mau_tra_loi': 'tom_tat_ket_qua/_tra_loi_chat.html',
        'loi_chao': LOI_CHAO,
        'goi_y_o_nhap': 'Ví dụ: Tóm tắt học kỳ 1 năm học 2024-2025',
        'gioi_han': GIOI_HAN_KY_TU,
    }


class TomTatCuaToiView(SinhVienMixin, View):
    template_name = 'tom_tat_ket_qua/trang_sinh_vien.html'

    def _sinh_vien(self, request):
        return getattr(request.user, 'ho_so_sinh_vien', None)

    def get(self, request):
        sinh_vien = self._sinh_vien(request)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')
        return render(request, self.template_name, ngu_canh_chat(request, sinh_vien, f'tom_tat:{sinh_vien.pk}'))

    def post(self, request):
        sinh_vien = self._sinh_vien(request)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')
        xu_ly_tin_nhan(request, sinh_vien, f'tom_tat:{sinh_vien.pk}')
        return redirect('tom_tat_ket_qua:toi')


class TomTatChoCoVanView(CoVanMixin, View):
    """Cố vấn chọn một sinh viên thuộc lớp mình phụ trách rồi chat; mỗi sinh viên có lịch sử riêng."""
    template_name = 'tom_tat_ket_qua/trang_co_van.html'

    def _danh_sach_sinh_vien(self, co_van):
        if co_van is None:
            return SinhVien.objects.none()
        return SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien')

    def _sinh_vien_trong_pham_vi(self, co_van, ma_sinh_vien):
        sinh_vien = get_object_or_404(SinhVien, pk=ma_sinh_vien)
        if sinh_vien.ma_lop.ma_co_van_id != co_van.pk:
            raise PermissionDenied('Sinh viên này không thuộc lớp bạn phụ trách.')
        return sinh_vien

    def get(self, request):
        co_van = getattr(request.user, 'ho_so_co_van', None)
        ngu_canh = {'danh_sach_sinh_vien': self._danh_sach_sinh_vien(co_van), 'sinh_vien_chon': None}
        ma_sinh_vien = request.GET.get('ma_sinh_vien', '').strip()
        if co_van is not None and ma_sinh_vien:
            sinh_vien = self._sinh_vien_trong_pham_vi(co_van, ma_sinh_vien)
            ngu_canh['sinh_vien_chon'] = sinh_vien
            ngu_canh.update(ngu_canh_chat(request, sinh_vien, f'tom_tat_cv:{request.user.pk}:{sinh_vien.pk}'))
            ngu_canh['truong_an'] = [('ma_sinh_vien', sinh_vien.pk)]
        return render(request, self.template_name, ngu_canh)

    def post(self, request):
        co_van = getattr(request.user, 'ho_so_co_van', None)
        if co_van is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ cố vấn học tập.')
            return redirect('accounts:trang_chu')
        sinh_vien = self._sinh_vien_trong_pham_vi(co_van, request.POST.get('ma_sinh_vien', '').strip())
        xu_ly_tin_nhan(request, sinh_vien, f'tom_tat_cv:{request.user.pk}:{sinh_vien.pk}')
        return redirect(f"{reverse('tom_tat_ket_qua:co_van')}?{urlencode({'ma_sinh_vien': sinh_vien.pk})}")
