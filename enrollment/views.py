from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from academics.excel_utils import phan_hoi_excel, tao_workbook_excel
from academics.models import HocKy
from academics.services import danh_sach_bo_loc_hoc_ky, trang_thai_dot_dang_ky
from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin, yeu_cau_vai_tro
from classes.models import LichHoc, LichThi, LopHocPhan
from classes.services import CAC_THU, xay_dung_luoi_tuan
from people.models import SinhVien

from .models import DangKyHocPhan, TrangThaiDangKy
from .pdf_utils import tao_pdf_bang
from .services import LoiDangKyHocPhan, dang_ky_hoc_phan, huy_dang_ky_hoc_phan, xac_dinh_trang_thai


class SinhVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.SINH_VIEN,)


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class DanhSachLopDangMoView(SinhVienMixin, ListView):
    template_name = 'enrollment/lop_dang_mo.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = LopHocPhan.objects.select_related('ma_hoc_phan', 'ma_giang_vien').annotate(
            so_dang_ky=Count('dang_ky', filter=Q(dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC))
        ).order_by('-nam_hoc', 'hoc_ky', 'ma_lop_hoc_phan')
        hoc_ky = self.request.GET.get('hoc_ky', '').strip()
        nam_hoc = self.request.GET.get('nam_hoc', '').strip()
        if hoc_ky:
            queryset = queryset.filter(hoc_ky=hoc_ky)
        if nam_hoc:
            queryset = queryset.filter(nam_hoc=nam_hoc)
        if self.request.GET.get('con_cho') == '1':
            queryset = queryset.filter(so_dang_ky__lt=F('si_so_toi_da'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoc_ky_loc'] = self.request.GET.get('hoc_ky', '')
        context['nam_hoc_loc'] = self.request.GET.get('nam_hoc', '')
        context['con_cho_loc'] = self.request.GET.get('con_cho', '')
        context['cac_hoc_ky'], context['cac_nam_hoc'] = danh_sach_bo_loc_hoc_ky()
        sinh_vien = getattr(self.request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is not None:
            context['ma_da_dang_ky'] = set(
                DangKyHocPhan.objects.filter(
                    ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
                ).values_list('ma_lop_hoc_phan_id', flat=True)
            )
        else:
            context['ma_da_dang_ky'] = set()
        context['co_ho_so'] = sinh_vien is not None
        # Gắn trực tiếp lên từng đối tượng LopHocPhan trong trang hiện tại (không dùng dict
        # khóa tuple vì template Django không tra được khóa tuple động); cache theo cặp
        # (hoc_ky, nam_hoc) để không gọi trang_thai_dot_dang_ky lặp lại cho các lớp cùng kỳ.
        cache_dot = {}
        for lop in context[self.context_object_name]:
            cap = (lop.hoc_ky, lop.nam_hoc)
            if cap not in cache_dot:
                cache_dot[cap] = trang_thai_dot_dang_ky(*cap)
            lop.dot_dang_ky = cache_dot[cap]
            # Trạng thái đầy đủ của sinh viên với lớp này (đã đăng ký/ngoài đợt/thiếu tiên
            # quyết/trùng lịch/đã đầy/đủ điều kiện) — dùng lại đúng hàm và thứ tự kiểm tra của
            # dang_ky_hoc_phan(), chỉ để hiển thị chip; việc đăng ký thật vẫn kiểm tra lại khi POST.
            if sinh_vien is not None:
                lop.trang_thai_dk = xac_dinh_trang_thai(sinh_vien, lop)
        return context


@yeu_cau_vai_tro(VaiTro.SINH_VIEN)
@require_POST
def dang_ky_hoc_phan_view(request, pk):
    sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
    if sinh_vien is None:
        messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
        return redirect('enrollment:lop_dang_mo')
    lop_hoc_phan = get_object_or_404(LopHocPhan, pk=pk)
    try:
        dang_ky_hoc_phan(sinh_vien, lop_hoc_phan)
    except LoiDangKyHocPhan as loi:
        messages.error(request, str(loi))
    else:
        messages.success(request, f'Đăng ký lớp "{lop_hoc_phan.ma_lop_hoc_phan}" thành công.')
    return redirect('enrollment:lop_dang_mo')


# Chặn "next" tùy ý trong URL (tránh open-redirect): chỉ nhận 2 giá trị cố định, việc hủy
# đăng ký có thể bắt đầu từ trang thời khóa biểu hoặc trang lịch sử đăng ký.
_NOI_QUAY_VE_SAU_KHI_HUY = {
    'thoi_khoa_bieu': 'enrollment:thoi_khoa_bieu',
    'lich_su': 'enrollment:lich_su_dang_ky',
}


@yeu_cau_vai_tro(VaiTro.SINH_VIEN)
def huy_dang_ky_view(request, pk):
    sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
    dang_ky = get_object_or_404(DangKyHocPhan, pk=pk)
    if sinh_vien is None or dang_ky.ma_sinh_vien_id != sinh_vien.pk:
        raise PermissionDenied('Bạn chỉ được hủy đăng ký của chính mình.')

    nguon = request.POST.get('nguon') or request.GET.get('nguon', 'lich_su')
    ten_url_ve = _NOI_QUAY_VE_SAU_KHI_HUY.get(nguon, 'enrollment:lich_su_dang_ky')

    if request.method == 'POST':
        try:
            huy_dang_ky_hoc_phan(dang_ky)
        except LoiDangKyHocPhan as loi:
            messages.error(request, str(loi))
        else:
            messages.success(request, f'Đã hủy đăng ký lớp "{dang_ky.ma_lop_hoc_phan_id}".')
        return redirect(ten_url_ve)

    return render(request, 'enrollment/huy_dang_ky_xac_nhan.html', {'dang_ky': dang_ky, 'nguon': nguon})


def _cac_hoc_ky_cua_sinh_vien(sinh_vien):
    """Các (hoc_ky, nam_hoc) mà sinh viên có lớp đăng ký còn hiệu lực, mới nhất trước."""
    return list(
        LopHocPhan.objects.filter(
            dang_ky__ma_sinh_vien=sinh_vien, dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ).values_list('hoc_ky', 'nam_hoc').distinct().order_by('-nam_hoc', '-hoc_ky')
    )


def chon_hoc_ky_thoi_khoa_bieu(request, sinh_vien):
    """Học kỳ để xem thời khóa biểu: tham số ?ky=<hoc_ky>:<nam_hoc> nếu hợp lệ; nếu không thì
    học kỳ đang diễn ra hôm nay (danh mục hoc_ky) khi sinh viên có lớp ở kỳ đó; nếu không nữa
    thì học kỳ gần nhất sinh viên có lớp. Trả về ((hoc_ky, nam_hoc) hoặc None, danh sách lựa chọn)."""
    cac_lua_chon = _cac_hoc_ky_cua_sinh_vien(sinh_vien)
    if not cac_lua_chon:
        return None, []
    hoc_ky, _, nam_hoc = request.GET.get('ky', '').partition(':')
    if (hoc_ky, nam_hoc) in cac_lua_chon:
        return (hoc_ky, nam_hoc), cac_lua_chon
    hom_nay = timezone.localdate()
    dang_dien_ra = HocKy.objects.filter(ngay_bat_dau__lte=hom_nay, ngay_ket_thuc__gte=hom_nay).first()
    if dang_dien_ra and (str(dang_dien_ra.hoc_ky), dang_dien_ra.nam_hoc) in cac_lua_chon:
        return (str(dang_dien_ra.hoc_ky), dang_dien_ra.nam_hoc), cac_lua_chon
    return cac_lua_chon[0], cac_lua_chon


def _lich_hoc_cua_sinh_vien(sinh_vien, hoc_ky_chon):
    if hoc_ky_chon is None:
        return LichHoc.objects.none()
    # Lọc thêm trang_thai=CON_HIEU_LUC ngay trong điều kiện join (không lọc sau) để
    # đảm bảo mỗi lớp chỉ khớp tối đa một dòng đăng ký của sinh viên này (đúng theo
    # UniqueConstraint uk_dang_ky_hoc_phan_dang_hieu_luc), annotate lấy được đúng
    # ma_dang_ky duy nhất đó để làm URL nút "Hủy đăng ký" mà không cần lọc gì thêm.
    return LichHoc.objects.filter(
        ma_lop_hoc_phan__dang_ky__ma_sinh_vien=sinh_vien,
        ma_lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ma_lop_hoc_phan__hoc_ky=hoc_ky_chon[0],
        ma_lop_hoc_phan__nam_hoc=hoc_ky_chon[1],
    ).annotate(
        ma_dang_ky_hien_tai=F('ma_lop_hoc_phan__dang_ky__pk')
    ).select_related('ma_lop_hoc_phan__ma_hoc_phan').order_by('thu', 'tiet_bat_dau')


class ThoiKhoaBieuView(SinhVienMixin, ListView):
    template_name = 'enrollment/thoi_khoa_bieu.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        sinh_vien = getattr(self.request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            self.hoc_ky_chon, self.cac_lua_chon = None, []
            return LichHoc.objects.none()
        self.hoc_ky_chon, self.cac_lua_chon = chon_hoc_ky_thoi_khoa_bieu(self.request, sinh_vien)
        return _lich_hoc_cua_sinh_vien(sinh_vien, self.hoc_ky_chon)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cac_ky'] = [
            {'gia_tri': f'{hk}:{nh}', 'nhan': f'Học kỳ {hk} - {nh}'} for hk, nh in self.cac_lua_chon
        ]
        context['ky_chon'] = f'{self.hoc_ky_chon[0]}:{self.hoc_ky_chon[1]}' if self.hoc_ky_chon else ''
        context['xem_luoi'] = self.request.GET.get('xem') == 'luoi'
        context['cac_thu'] = CAC_THU
        context['luoi_tuan'] = xay_dung_luoi_tuan(context[self.context_object_name])
        return context


class LichSuDangKyView(SinhVienMixin, ListView):
    template_name = 'enrollment/lich_su_dang_ky.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        sinh_vien = getattr(self.request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            return DangKyHocPhan.objects.none()
        # KHÔNG lọc theo trang_thai — "lịch sử" phải hiện đủ cả các lần đã hủy.
        return DangKyHocPhan.objects.filter(ma_sinh_vien=sinh_vien).select_related(
            'ma_lop_hoc_phan__ma_hoc_phan'
        ).order_by('-thoi_gian_dang_ky')


class DanhSachSinhVienLopView(YeuCauVaiTroMixin, ListView):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO, VaiTro.GIANG_VIEN)
    template_name = 'enrollment/danh_sach_sinh_vien_lop.html'
    context_object_name = 'danh_sach'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lop_hoc_phan = get_object_or_404(LopHocPhan, pk=kwargs['ma_lop_hoc_phan'])

    def get(self, request, *args, **kwargs):
        if request.user.vai_tro == VaiTro.GIANG_VIEN:
            giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
            if giang_vien is None or self.lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
                raise PermissionDenied('Bạn không phụ trách lớp học phần này.')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = DangKyHocPhan.objects.filter(ma_lop_hoc_phan=self.lop_hoc_phan).select_related('ma_sinh_vien')
        if self.request.user.vai_tro == VaiTro.GIANG_VIEN:
            # Giảng viên chỉ cần thấy sinh viên đang thực học lớp mình — không hiện các
            # đăng ký đã hủy (khác với Phòng Đào tạo, xem hien_trang_thai bên dưới).
            queryset = queryset.filter(trang_thai=TrangThaiDangKy.CON_HIEU_LUC)
        return queryset.order_by('ma_sinh_vien')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lop_hoc_phan'] = self.lop_hoc_phan
        # Phòng Đào tạo cần thấy đủ trạng thái (còn hiệu lực/đã hủy), không ẩn dòng nào.
        context['hien_trang_thai'] = self.request.user.vai_tro == VaiTro.PHONG_DAO_TAO
        return context


class TraCuuLichSuDangKyView(QuanLyPhongDaoTaoMixin, ListView):
    template_name = 'enrollment/tra_cuu_lich_su.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        ma_sinh_vien = self.request.GET.get('ma_sinh_vien', '').strip()
        if not ma_sinh_vien:
            return DangKyHocPhan.objects.none()
        return DangKyHocPhan.objects.filter(ma_sinh_vien=ma_sinh_vien).select_related(
            'ma_lop_hoc_phan__ma_hoc_phan'
        ).order_by('-thoi_gian_dang_ky')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ma_sinh_vien'] = self.request.GET.get('ma_sinh_vien', '')
        return context


class DanhSachSinhVienCoVanView(YeuCauVaiTroMixin, ListView):
    vai_tro_cho_phep = (VaiTro.CO_VAN_HOC_TAP,)
    template_name = 'enrollment/sinh_vien_phu_trach.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        co_van = getattr(self.request.user, 'ho_so_co_van', None)
        if co_van is None:
            return SinhVien.objects.none()
        return SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['co_ho_so'] = getattr(self.request.user, 'ho_so_co_van', None) is not None
        return context


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO, VaiTro.GIANG_VIEN)
def xuat_excel_sinh_vien_lop_view(request, ma_lop_hoc_phan):
    lop_hoc_phan = get_object_or_404(LopHocPhan, pk=ma_lop_hoc_phan)
    if request.user.vai_tro == VaiTro.GIANG_VIEN:
        giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
        if giang_vien is None or lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
            raise PermissionDenied('Bạn không phụ trách lớp học phần này.')

    queryset = DangKyHocPhan.objects.filter(ma_lop_hoc_phan=lop_hoc_phan).select_related('ma_sinh_vien')
    if request.user.vai_tro == VaiTro.GIANG_VIEN:
        queryset = queryset.filter(trang_thai=TrangThaiDangKy.CON_HIEU_LUC)
    queryset = queryset.order_by('ma_sinh_vien')

    cac_dong = [
        [
            dang_ky.ma_sinh_vien_id, dang_ky.ma_sinh_vien.ho_ten,
            dang_ky.thoi_gian_dang_ky.strftime('%d/%m/%Y %H:%M'), dang_ky.get_trang_thai_display(),
        ]
        for dang_ky in queryset
    ]
    workbook = tao_workbook_excel(
        'Sinh vien lop hoc phan', ['Mã sinh viên', 'Họ tên', 'Thời gian đăng ký', 'Trạng thái'], cac_dong,
    )
    return phan_hoi_excel(workbook, f'sinh_vien_{lop_hoc_phan.pk}.xlsx')


@yeu_cau_vai_tro(VaiTro.CO_VAN_HOC_TAP)
def xuat_excel_sinh_vien_phu_trach_view(request):
    co_van = getattr(request.user, 'ho_so_co_van', None)
    queryset = (
        SinhVien.objects.none() if co_van is None else
        SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien')
    )
    cac_dong = [[sv.ma_sinh_vien, sv.ho_ten, sv.ma_lop.ten_lop, sv.email, sv.so_dien_thoai] for sv in queryset]
    workbook = tao_workbook_excel(
        'Sinh vien phu trach', ['Mã sinh viên', 'Họ tên', 'Lớp hành chính', 'Email', 'Số điện thoại'], cac_dong,
    )
    return phan_hoi_excel(workbook, 'sinh_vien_phu_trach.xlsx')


def _lich_thi_cua_sinh_vien(sinh_vien):
    return LichThi.objects.filter(
        lop_hoc_phan__dang_ky__ma_sinh_vien=sinh_vien,
        lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('lop_hoc_phan__ma_hoc_phan').order_by('ngay_thi', 'gio_bat_dau')


class LichThiSinhVienView(SinhVienMixin, ListView):
    model = LichThi
    template_name = 'enrollment/lich_thi.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        sinh_vien = getattr(self.request.user, 'ho_so_sinh_vien', None)
        if sinh_vien is None:
            return LichThi.objects.none()
        return _lich_thi_cua_sinh_vien(sinh_vien)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['co_ho_so'] = getattr(self.request.user, 'ho_so_sinh_vien', None) is not None
        return context


_CAC_COT_LICH_THI = [
    ('Lớp học phần', 3), ('Học phần', 6), ('Ngày thi', 2.5), ('Giờ bắt đầu', 2.5), ('Phòng thi', 2.5),
]


@yeu_cau_vai_tro(VaiTro.SINH_VIEN)
def xuat_lich_thi_pdf_view(request):
    sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
    if sinh_vien is None:
        messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
        return redirect('enrollment:lich_thi')

    danh_sach = _lich_thi_cua_sinh_vien(sinh_vien)
    cac_dong = [
        [
            lich.lop_hoc_phan_id, lich.lop_hoc_phan.ma_hoc_phan.ten_hoc_phan,
            f'{lich.ngay_thi:%d/%m/%Y}', lich.gio_bat_dau.strftime('%H:%M'), lich.phong_thi,
        ]
        for lich in danh_sach
    ]
    buffer = tao_pdf_bang(
        'LỊCH THI', _CAC_COT_LICH_THI, cac_dong, dong_trong='Bạn chưa có lịch thi nào.',
    )
    return FileResponse(buffer, as_attachment=True, filename='lich_thi.pdf')


_CAC_COT_THOI_KHOA_BIEU = [
    ('Học phần', 5.3), ('Lớp học phần', 3.2), ('Thứ', 1.9), ('Tiết bắt đầu', 2.7), ('Số tiết', 1.6), ('Phòng học', 2.3),
]
_TEN_THU = dict(CAC_THU)


@yeu_cau_vai_tro(VaiTro.SINH_VIEN)
def xuat_thoi_khoa_bieu_pdf_view(request):
    sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
    if sinh_vien is None:
        messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
        return redirect('enrollment:thoi_khoa_bieu')

    hoc_ky_chon, _ = chon_hoc_ky_thoi_khoa_bieu(request, sinh_vien)
    danh_sach = _lich_hoc_cua_sinh_vien(sinh_vien, hoc_ky_chon)
    tieu_de = 'THỜI KHÓA BIỂU'
    if hoc_ky_chon:
        tieu_de += f' - HỌC KỲ {hoc_ky_chon[0]} NĂM HỌC {hoc_ky_chon[1]}'
    cac_dong = [
        [
            lich.ma_lop_hoc_phan.ma_hoc_phan.ten_hoc_phan, lich.ma_lop_hoc_phan_id,
            _TEN_THU.get(lich.thu, lich.thu), lich.tiet_bat_dau, lich.so_tiet, lich.phong_hoc,
        ]
        for lich in danh_sach
    ]
    buffer = tao_pdf_bang(
        tieu_de, _CAC_COT_THOI_KHOA_BIEU, cac_dong, dong_trong='Bạn chưa đăng ký lớp học phần nào.',
    )
    return FileResponse(buffer, as_attachment=True, filename='thoi_khoa_bieu.pdf')
