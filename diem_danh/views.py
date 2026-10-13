from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from classes.models import LopHocPhan
from enrollment.models import TrangThaiDangKy
from people.models import SinhVien

from .models import DiemDanh


class GiangVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.GIANG_VIEN,)


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class DiemDanhLopView(GiangVienMixin, View):
    """Điểm danh cả lớp cho một ngày (mặc định hôm nay): lưu một lần cho mọi sinh viên
    đang có đăng ký còn hiệu lực. Nếu ngày đó đã điểm danh, GET nạp lại trạng thái đã lưu
    để sửa, POST ghi đè qua update_or_create (không tạo trùng)."""

    template_name = 'diem_danh/diem_danh_lop.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lop_hoc_phan = get_object_or_404(LopHocPhan, pk=kwargs['ma_lop_hoc_phan'])

    def _kiem_tra_quyen(self, request):
        giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
        if giang_vien is None or self.lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
            raise PermissionDenied('Bạn không phụ trách lớp học phần này.')

    def _danh_sach_sinh_vien(self):
        return SinhVien.objects.filter(
            dang_ky_hoc_phan__ma_lop_hoc_phan=self.lop_hoc_phan,
            dang_ky_hoc_phan__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ).order_by('ma_sinh_vien')

    def _lay_ngay(self, request):
        return parse_date(request.GET.get('ngay') or request.POST.get('ngay') or '') or timezone.localdate()

    def get(self, request, *args, **kwargs):
        self._kiem_tra_quyen(request)
        ngay = self._lay_ngay(request)
        diem_danh_hien_co = {
            dd.sinh_vien_id: dd.co_mat
            for dd in DiemDanh.objects.filter(lop_hoc_phan=self.lop_hoc_phan, ngay_diem_danh=ngay)
        }
        danh_sach = list(self._danh_sach_sinh_vien())
        for sv in danh_sach:
            sv.co_mat = diem_danh_hien_co.get(sv.pk, True)
        return render(request, self.template_name, {
            'lop_hoc_phan': self.lop_hoc_phan,
            'danh_sach': danh_sach,
            'ngay': ngay,
            'da_diem_danh_ngay_nay': bool(diem_danh_hien_co),
        })

    def post(self, request, *args, **kwargs):
        self._kiem_tra_quyen(request)
        ngay = self._lay_ngay(request)
        for sv in self._danh_sach_sinh_vien():
            co_mat = request.POST.get(f'co_mat_{sv.pk}') == 'on'
            DiemDanh.objects.update_or_create(
                lop_hoc_phan=self.lop_hoc_phan, sinh_vien=sv, ngay_diem_danh=ngay,
                defaults={'co_mat': co_mat},
            )
        messages.success(
            request, f'Đã lưu điểm danh ngày {ngay:%d/%m/%Y} cho lớp "{self.lop_hoc_phan.ma_lop_hoc_phan}".',
        )
        return redirect(f"{request.path}?ngay={ngay.isoformat()}")


class LichSuDiemDanhLopView(GiangVienMixin, View):
    template_name = 'diem_danh/lich_su_diem_danh_lop.html'

    def get(self, request, ma_lop_hoc_phan):
        lop_hoc_phan = get_object_or_404(LopHocPhan, pk=ma_lop_hoc_phan)
        giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
        if giang_vien is None or lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
            raise PermissionDenied('Bạn không phụ trách lớp học phần này.')

        theo_ngay = list(
            DiemDanh.objects.filter(lop_hoc_phan=lop_hoc_phan)
            .values('ngay_diem_danh')
            .annotate(tong=Count('id'), so_co_mat=Count('id', filter=Q(co_mat=True)))
            .order_by('-ngay_diem_danh')
        )
        for muc in theo_ngay:
            muc['ty_le'] = round(muc['so_co_mat'] * 100 / muc['tong'], 1) if muc['tong'] else 0
        return render(request, self.template_name, {'lop_hoc_phan': lop_hoc_phan, 'danh_sach': theo_ngay})


class LichSuDiemDanhSinhVienView(SinhVienMixin, View):
    template_name = 'diem_danh/lich_su_diem_danh_sinh_vien.html'

    def get(self, request):
        sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
            return redirect('accounts:trang_chu')

        danh_sach = DiemDanh.objects.filter(sinh_vien=sinh_vien).select_related(
            'lop_hoc_phan__ma_hoc_phan'
        ).order_by('lop_hoc_phan', '-ngay_diem_danh')

        theo_lop = {}
        for dd in danh_sach:
            muc = theo_lop.setdefault(dd.lop_hoc_phan_id, {
                'lop_hoc_phan': dd.lop_hoc_phan, 'danh_sach': [], 'tong': 0, 'so_co_mat': 0,
            })
            muc['danh_sach'].append(dd)
            muc['tong'] += 1
            if dd.co_mat:
                muc['so_co_mat'] += 1
        for muc in theo_lop.values():
            muc['ty_le'] = round(muc['so_co_mat'] * 100 / muc['tong'], 1) if muc['tong'] else 0

        return render(request, self.template_name, {'theo_lop': list(theo_lop.values())})
