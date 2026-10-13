from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q
from django.views import View
from django.views.generic import ListView, TemplateView
from openpyxl.styles import Font

from academics.excel_utils import phan_hoi_excel, tao_workbook_excel
from academics.models import HocPhan
from academics.services import danh_sach_bo_loc_hoc_ky
from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from classes.models import LopHocPhan
from enrollment.models import TrangThaiDangKy
from grades.models import Diem


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


def _loc_hoc_ky_nam_hoc(request):
    return request.GET.get('hoc_ky', '').strip(), request.GET.get('nam_hoc', '').strip()


def _queryset_si_so_theo_lop(request):
    queryset = LopHocPhan.objects.select_related('ma_hoc_phan').annotate(
        so_dang_ky=Count('dang_ky', filter=Q(dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC))
    ).order_by('-nam_hoc', 'hoc_ky', 'ma_lop_hoc_phan')
    hoc_ky, nam_hoc = _loc_hoc_ky_nam_hoc(request)
    if hoc_ky:
        queryset = queryset.filter(hoc_ky=hoc_ky)
    if nam_hoc:
        queryset = queryset.filter(nam_hoc=nam_hoc)
    return queryset


class SiSoTheoLopReportView(QuanLyPhongDaoTaoMixin, ListView):
    template_name = 'reports/si_so_theo_lop.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        return _queryset_si_so_theo_lop(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoc_ky_loc'], context['nam_hoc_loc'] = _loc_hoc_ky_nam_hoc(self.request)
        context['cac_hoc_ky'], context['cac_nam_hoc'] = danh_sach_bo_loc_hoc_ky()
        return context


class XuatExcelSiSoTheoLopView(QuanLyPhongDaoTaoMixin, View):
    def get(self, request):
        cac_dong = [
            [lop.ma_lop_hoc_phan, lop.ma_hoc_phan.ten_hoc_phan, lop.hoc_ky, lop.nam_hoc, lop.so_dang_ky, lop.si_so_toi_da]
            for lop in _queryset_si_so_theo_lop(request)
        ]
        workbook = tao_workbook_excel(
            'Si so theo lop',
            ['Mã lớp học phần', 'Học phần', 'Học kỳ', 'Năm học', 'Đã đăng ký', 'Sĩ số tối đa'],
            cac_dong,
        )
        return phan_hoi_excel(workbook, 'si_so_theo_lop.xlsx')


def _queryset_hoc_phan_nhieu_dang_ky(request):
    hoc_ky, nam_hoc = _loc_hoc_ky_nam_hoc(request)
    dieu_kien = Q(lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC)
    if hoc_ky:
        dieu_kien &= Q(lop_hoc_phan__hoc_ky=hoc_ky)
    if nam_hoc:
        dieu_kien &= Q(lop_hoc_phan__nam_hoc=nam_hoc)
    return HocPhan.objects.annotate(
        so_dang_ky=Count('lop_hoc_phan__dang_ky', filter=dieu_kien)
    ).order_by('-so_dang_ky', 'ma_hoc_phan')


class HocPhanNhieuDangKyReportView(QuanLyPhongDaoTaoMixin, ListView):
    template_name = 'reports/hoc_phan_nhieu_dang_ky.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        return _queryset_hoc_phan_nhieu_dang_ky(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoc_ky_loc'], context['nam_hoc_loc'] = _loc_hoc_ky_nam_hoc(self.request)
        context['cac_hoc_ky'], context['cac_nam_hoc'] = danh_sach_bo_loc_hoc_ky()
        return context


class XuatExcelHocPhanNhieuDangKyView(QuanLyPhongDaoTaoMixin, View):
    def get(self, request):
        cac_dong = [
            [hang, hp.ma_hoc_phan, hp.ten_hoc_phan, hp.so_dang_ky]
            for hang, hp in enumerate(_queryset_hoc_phan_nhieu_dang_ky(request), start=1)
        ]
        workbook = tao_workbook_excel(
            'Hoc phan nhieu dang ky', ['Hạng', 'Mã học phần', 'Tên học phần', 'Số lượt đăng ký'], cac_dong,
        )
        return phan_hoi_excel(workbook, 'hoc_phan_nhieu_dang_ky.xlsx')


def _tinh_ket_qua_hoc_tap(request):
    hoc_ky, nam_hoc = _loc_hoc_ky_nam_hoc(request)

    diem_qs = Diem.objects.select_related(
        'ma_dang_ky__ma_lop_hoc_phan__ma_hoc_phan'
    ).exclude(diem_qua_trinh__isnull=True).exclude(diem_thi__isnull=True).filter(
        ma_dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    )
    if hoc_ky:
        diem_qs = diem_qs.filter(ma_dang_ky__ma_lop_hoc_phan__hoc_ky=hoc_ky)
    if nam_hoc:
        diem_qs = diem_qs.filter(ma_dang_ky__ma_lop_hoc_phan__nam_hoc=nam_hoc)

    # Chỉ một truy vấn để lấy toàn bộ điểm liên quan; việc tính điểm tổng kết
    # và gộp nhóm thực hiện trên dữ liệu đã lấy về (không truy vấn thêm trong vòng lặp).
    danh_sach_diem = list(diem_qs)

    phan_bo = {
        'duoi_4': 0,
        'tu_4_den_duoi_5_5': 0,
        'tu_5_5_den_duoi_7': 0,
        'tu_7_den_duoi_8_5': 0,
        'tu_8_5_tro_len': 0,
    }
    theo_hoc_phan = {}

    for diem in danh_sach_diem:
        tong_ket = diem.tinh_diem_tong_ket()
        if tong_ket is None:
            continue
        if tong_ket < settings.DIEM_DAT_TOI_THIEU:
            phan_bo['duoi_4'] += 1
        elif tong_ket < Decimal('5.5'):
            phan_bo['tu_4_den_duoi_5_5'] += 1
        elif tong_ket < Decimal('7.0'):
            phan_bo['tu_5_5_den_duoi_7'] += 1
        elif tong_ket < Decimal('8.5'):
            phan_bo['tu_7_den_duoi_8_5'] += 1
        else:
            phan_bo['tu_8_5_tro_len'] += 1

        hoc_phan = diem.ma_dang_ky.ma_lop_hoc_phan.ma_hoc_phan
        thong_ke = theo_hoc_phan.setdefault(
            hoc_phan.pk, {'ten': hoc_phan.ten_hoc_phan, 'tong': 0, 'dat': 0}
        )
        thong_ke['tong'] += 1
        if tong_ket >= settings.DIEM_DAT_TOI_THIEU:
            thong_ke['dat'] += 1

    for thong_ke in theo_hoc_phan.values():
        thong_ke['ty_le_dat'] = (
            round(thong_ke['dat'] * 100 / thong_ke['tong'], 1) if thong_ke['tong'] else 0
        )

    return {
        'phan_bo': phan_bo,
        'diem_dat_toi_thieu': settings.DIEM_DAT_TOI_THIEU,
        'tong_so_diem': len(danh_sach_diem),
        'theo_hoc_phan': sorted(theo_hoc_phan.values(), key=lambda muc: muc['ten']),
        'hoc_ky_loc': hoc_ky,
        'nam_hoc_loc': nam_hoc,
    }


class KetQuaHocTapReportView(QuanLyPhongDaoTaoMixin, TemplateView):
    template_name = 'reports/ket_qua_hoc_tap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_tinh_ket_qua_hoc_tap(self.request))
        context['cac_hoc_ky'], context['cac_nam_hoc'] = danh_sach_bo_loc_hoc_ky()
        return context


class XuatExcelKetQuaHocTapView(QuanLyPhongDaoTaoMixin, View):
    def get(self, request):
        ket_qua = _tinh_ket_qua_hoc_tap(request)
        nhan_phan_bo = [
            (f'Dưới {ket_qua["diem_dat_toi_thieu"]} (Không đạt)', ket_qua['phan_bo']['duoi_4']),
            ('4.0 - dưới 5.5 (Trung bình)', ket_qua['phan_bo']['tu_4_den_duoi_5_5']),
            ('5.5 - dưới 7.0 (Khá)', ket_qua['phan_bo']['tu_5_5_den_duoi_7']),
            ('7.0 - dưới 8.5 (Giỏi)', ket_qua['phan_bo']['tu_7_den_duoi_8_5']),
            ('Từ 8.5 (Xuất sắc)', ket_qua['phan_bo']['tu_8_5_tro_len']),
        ]
        workbook = tao_workbook_excel('Phan bo diem', ['Khoảng điểm', 'Số lượt'], nhan_phan_bo)

        sheet2 = workbook.create_sheet('Ty le dat theo hoc phan')
        sheet2.append(['Học phần', 'Số lượt có điểm', 'Số lượt đạt', 'Tỷ lệ đạt (%)'])
        for cell in sheet2[1]:
            cell.font = Font(bold=True)
        for hp in ket_qua['theo_hoc_phan']:
            sheet2.append([hp['ten'], hp['tong'], hp['dat'], hp['ty_le_dat']])

        return phan_hoi_excel(workbook, 'ket_qua_hoc_tap.xlsx')
