from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from academics.models import LopHanhChinh
from academics.services import danh_sach_bo_loc_hoc_ky
from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin, yeu_cau_vai_tro
from classes.models import LopHocPhan
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from enrollment.pdf_utils import tao_pdf_bang
from people.models import SinhVien

from .forms import DiemForm
from .models import Diem
from .services import (
    canh_bao_hoc_vu, diem_trung_binh_hoc_ky, diem_trung_binh_nam_hoc, diem_trung_binh_tich_luy,
    hoc_ky_gan_nhat_co_du_diem, xep_loai_hoc_luc,
)


class GiangVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.GIANG_VIEN,)


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class BangDiemLopView(GiangVienMixin, ListView):
    template_name = 'grades/bang_diem_lop.html'
    context_object_name = 'danh_sach'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lop_hoc_phan = get_object_or_404(LopHocPhan, pk=kwargs['ma_lop_hoc_phan'])

    def get(self, request, *args, **kwargs):
        giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
        if giang_vien is None or self.lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
            raise PermissionDenied('Bạn không phụ trách lớp học phần này.')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        # Chỉ các đăng ký còn hiệu lực — sinh viên đã hủy đăng ký thì không còn thực học
        # lớp này nữa, không cần (và không nên) nhập điểm cho họ.
        return DangKyHocPhan.objects.filter(
            ma_lop_hoc_phan=self.lop_hoc_phan, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ).select_related('ma_sinh_vien', 'diem').order_by('ma_sinh_vien')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lop_hoc_phan'] = self.lop_hoc_phan
        context['ten_url_sua'] = 'grades:nhap_diem'
        context['cho_phep_tao_moi'] = True
        context['cho_phep_cong_bo'] = True
        return context


@yeu_cau_vai_tro(VaiTro.GIANG_VIEN)
@require_POST
def cong_bo_diem_lop_view(request, ma_lop_hoc_phan):
    lop_hoc_phan = get_object_or_404(LopHocPhan, pk=ma_lop_hoc_phan)
    giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
    if giang_vien is None or lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
        raise PermissionDenied('Bạn không phụ trách lớp học phần này.')
    # Công bố cả lớp cùng lúc (đơn giản hơn từng dòng) — chỉ công bố các dòng đã có đủ
    # điểm quá trình và điểm thi, bỏ qua các dòng còn thiếu điểm (không có gì để công bố).
    so_luong = Diem.objects.filter(
        ma_dang_ky__ma_lop_hoc_phan=lop_hoc_phan, ma_dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        diem_qua_trinh__isnull=False, diem_thi__isnull=False,
    ).update(da_cong_bo=True)
    if so_luong:
        messages.success(request, f'Đã công bố điểm cho {so_luong} sinh viên đã có đủ điểm trong lớp.')
    else:
        messages.warning(request, 'Chưa có sinh viên nào đủ điểm (quá trình + thi) để công bố.')
    return redirect('grades:bang_diem_lop', ma_lop_hoc_phan=lop_hoc_phan.pk)


class BangDiemLopPhongDaoTaoView(QuanLyPhongDaoTaoMixin, ListView):
    template_name = 'grades/bang_diem_lop.html'
    context_object_name = 'danh_sach'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lop_hoc_phan = get_object_or_404(LopHocPhan, pk=kwargs['ma_lop_hoc_phan'])

    def get_queryset(self):
        return DangKyHocPhan.objects.filter(
            ma_lop_hoc_phan=self.lop_hoc_phan, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ).select_related('ma_sinh_vien', 'diem').order_by('ma_sinh_vien')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lop_hoc_phan'] = self.lop_hoc_phan
        context['ten_url_sua'] = 'grades:sua_diem'
        context['cho_phep_tao_moi'] = False
        return context


@yeu_cau_vai_tro(VaiTro.GIANG_VIEN)
def nhap_diem_view(request, ma_dang_ky):
    dang_ky = get_object_or_404(DangKyHocPhan, pk=ma_dang_ky)
    giang_vien = getattr(request.user, 'ho_so_giang_vien', None)
    if giang_vien is None or dang_ky.ma_lop_hoc_phan.ma_giang_vien_id != giang_vien.pk:
        raise PermissionDenied('Bạn không phụ trách lớp học phần này.')
    if dang_ky.trang_thai != TrangThaiDangKy.CON_HIEU_LUC:
        messages.error(request, 'Không thể nhập điểm vì sinh viên đã hủy đăng ký lớp này.')
        return redirect('grades:bang_diem_lop', ma_lop_hoc_phan=dang_ky.ma_lop_hoc_phan_id)
    diem, _ = Diem.objects.get_or_create(ma_dang_ky=dang_ky)
    if request.method == 'POST':
        form = DiemForm(request.POST, instance=diem)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã lưu điểm cho sinh viên "{dang_ky.ma_sinh_vien_id}".')
            return redirect('grades:bang_diem_lop', ma_lop_hoc_phan=dang_ky.ma_lop_hoc_phan_id)
    else:
        form = DiemForm(instance=diem)
    return render(request, 'grades/nhap_diem.html', {'form': form, 'dang_ky': dang_ky})


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO)
def sua_diem_view(request, ma_dang_ky):
    dang_ky = get_object_or_404(DangKyHocPhan, pk=ma_dang_ky)
    if dang_ky.trang_thai != TrangThaiDangKy.CON_HIEU_LUC:
        messages.error(request, 'Không thể sửa điểm vì sinh viên đã hủy đăng ký lớp này.')
        return redirect('grades:bang_diem_lop_phong_dao_tao', ma_lop_hoc_phan=dang_ky.ma_lop_hoc_phan_id)
    diem = get_object_or_404(Diem, ma_dang_ky=dang_ky)
    if request.method == 'POST':
        form = DiemForm(request.POST, instance=diem)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật điểm cho sinh viên "{dang_ky.ma_sinh_vien_id}".')
            return redirect('grades:bang_diem_lop_phong_dao_tao', ma_lop_hoc_phan=dang_ky.ma_lop_hoc_phan_id)
    else:
        form = DiemForm(instance=diem)
    return render(request, 'grades/nhap_diem.html', {'form': form, 'dang_ky': dang_ky})


def _kiem_tra_quyen_xem_bang_diem(request, sinh_vien):
    vai_tro = request.user.vai_tro
    if vai_tro == VaiTro.PHONG_DAO_TAO:
        return
    if vai_tro == VaiTro.SINH_VIEN:
        ho_so = getattr(request.user, 'ho_so_sinh_vien', None)
        if ho_so is not None and ho_so.pk == sinh_vien.pk:
            return
        raise PermissionDenied('Bạn chỉ được xem bảng điểm của chính mình.')
    if vai_tro == VaiTro.CO_VAN_HOC_TAP:
        ho_so = getattr(request.user, 'ho_so_co_van', None)
        if ho_so is not None and sinh_vien.ma_lop.ma_co_van_id == ho_so.pk:
            return
        raise PermissionDenied('Sinh viên này không thuộc lớp bạn phụ trách.')
    raise PermissionDenied('Bạn không có quyền xem bảng điểm.')


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO, VaiTro.CO_VAN_HOC_TAP, VaiTro.SINH_VIEN)
def bang_diem_sinh_vien_view(request, ma_sinh_vien):
    sinh_vien = get_object_or_404(SinhVien, pk=ma_sinh_vien)
    _kiem_tra_quyen_xem_bang_diem(request, sinh_vien)
    # Chỉ sinh viên tự xem của chính mình mới bị ẩn điểm chưa công bố — Giảng viên/Cố vấn
    # học tập/Phòng Đào tạo luôn xem điểm thật (đã kiểm tra quyền ở trên).
    chi_diem_da_cong_bo = request.user.vai_tro == VaiTro.SINH_VIEN

    # Chỉ đăng ký còn hiệu lực — lớp đã hủy đăng ký thì không có điểm (hủy bị chặn nếu đã
    # có điểm) nên không thuộc về bảng điểm/kết quả học tập của sinh viên.
    danh_sach = list(DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan__ma_hoc_phan', 'diem').order_by(
        '-ma_lop_hoc_phan__nam_hoc', 'ma_lop_hoc_phan__hoc_ky'
    ))
    for dang_ky in danh_sach:
        diem = getattr(dang_ky, 'diem', None)
        # True nghĩa là có điểm thật nhưng đang bị ẩn (chờ công bố) — chỉ xảy ra khi chính
        # sinh viên tự xem; Giảng viên/Cố vấn/Phòng Đào tạo luôn thấy điểm thật.
        dang_ky.cho_cong_bo = bool(
            chi_diem_da_cong_bo and diem is not None and not diem.da_cong_bo
            and (diem.diem_qua_trinh is not None or diem.diem_thi is not None)
        )

    # Bộ lọc chỉ gồm các năm học/học kỳ mà sinh viên có đăng ký (không lấy cả danh mục học kỳ).
    cac_ky_cua_sv = sorted(
        {(dk.ma_lop_hoc_phan.hoc_ky, dk.ma_lop_hoc_phan.nam_hoc) for dk in danh_sach},
        key=lambda ky: (ky[1], ky[0]), reverse=True,
    )
    cac_nam_hoc = sorted({nam_hoc for _, nam_hoc in cac_ky_cua_sv}, reverse=True)
    cac_hoc_ky = sorted({hoc_ky for hoc_ky, _ in cac_ky_cua_sv})

    # Chưa chọn năm học (lúc mới vào, hoặc năm không hợp lệ): hiện điểm của mọi học kỳ, chỉ có điểm trung bình
    # và xếp loại tích lũy. Chọn năm + kỳ: xem đúng học kỳ đó. Chọn năm, để trống kỳ ("Cả năm"): xem cả năm học
    # — trừ khi năm đó mới có một học kỳ thì xem học kỳ đó.
    hoc_ky_loc = request.GET.get('hoc_ky', '').strip()
    nam_hoc_loc = request.GET.get('nam_hoc', '').strip()
    tat_ca = nam_hoc_loc not in cac_nam_hoc
    ca_nam = False
    chi_mot_ky = False
    if tat_ca:
        hoc_ky_loc = nam_hoc_loc = ''
    elif not hoc_ky_loc:
        ky_trong_nam = [hoc_ky for hoc_ky, nam_hoc in cac_ky_cua_sv if nam_hoc == nam_hoc_loc]
        if len(ky_trong_nam) == 1:
            hoc_ky_loc, chi_mot_ky = ky_trong_nam[0], True
        else:
            ca_nam = True

    danh_sach_hien_thi = [
        dk for dk in danh_sach
        if tat_ca or (
            dk.ma_lop_hoc_phan.nam_hoc == nam_hoc_loc and (ca_nam or dk.ma_lop_hoc_phan.hoc_ky == hoc_ky_loc)
        )
    ]

    diem_tb_ky_chon = None
    canh_bao = None
    if ca_nam:
        diem_tb_ky_chon = diem_trung_binh_nam_hoc(sinh_vien, nam_hoc_loc, chi_diem_da_cong_bo)
    elif hoc_ky_loc and nam_hoc_loc:
        diem_tb_ky_chon = diem_trung_binh_hoc_ky(sinh_vien, hoc_ky_loc, nam_hoc_loc, chi_diem_da_cong_bo)
        canh_bao = canh_bao_hoc_vu(sinh_vien, hoc_ky_loc, nam_hoc_loc, chi_diem_da_cong_bo)
    diem_tb_tich_luy = diem_trung_binh_tich_luy(sinh_vien, chi_diem_da_cong_bo)

    return render(request, 'grades/bang_diem_sinh_vien.html', {
        'sinh_vien': sinh_vien,
        'danh_sach': danh_sach_hien_thi,
        'co_dang_ky': bool(danh_sach),
        'hoc_ky_loc': '' if ca_nam else hoc_ky_loc,
        'nam_hoc_loc': nam_hoc_loc,
        'tat_ca': tat_ca,
        'ca_nam': ca_nam,
        'chi_mot_ky': chi_mot_ky,
        'cac_hoc_ky': cac_hoc_ky,
        'cac_nam_hoc': cac_nam_hoc,
        'diem_tb_hoc_ky': diem_tb_ky_chon,
        'xep_loai_hoc_ky': xep_loai_hoc_luc(diem_tb_ky_chon),
        'diem_tb_tich_luy': diem_tb_tich_luy,
        'xep_loai_tich_luy': xep_loai_hoc_luc(diem_tb_tich_luy),
        'canh_bao': canh_bao,
    })


@login_required
def bang_diem_cua_toi_view(request):
    sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
    if sinh_vien is None:
        messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
        return redirect('accounts:trang_chu')
    return redirect('grades:bang_diem_sinh_vien', ma_sinh_vien=sinh_vien.pk)


class CoVanMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.CO_VAN_HOC_TAP,)


class DanhSachCanhBaoCoVanView(CoVanMixin, View):
    """Sinh viên thuộc lớp phụ trách đang bị cảnh báo học vụ ở học kỳ gần nhất (của riêng
    từng sinh viên) có đủ điểm — dùng điểm thật (chi_diem_da_cong_bo=False mặc định), vì
    đây là trang của Cố vấn học tập, không phải sinh viên tự xem."""

    template_name = 'grades/canh_bao_hoc_vu_co_van.html'

    def get(self, request):
        co_van = getattr(request.user, 'ho_so_co_van', None)
        sinh_vien_qs = (
            SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien')
            if co_van is not None else SinhVien.objects.none()
        )
        danh_sach_canh_bao = []
        for sv in sinh_vien_qs:
            hoc_ky_nam_hoc = hoc_ky_gan_nhat_co_du_diem(sv)
            if hoc_ky_nam_hoc is None:
                continue
            hoc_ky, nam_hoc = hoc_ky_nam_hoc
            ket_qua = canh_bao_hoc_vu(sv, hoc_ky, nam_hoc)
            if ket_qua['canh_bao']:
                danh_sach_canh_bao.append({'sinh_vien': sv, 'hoc_ky': hoc_ky, 'nam_hoc': nam_hoc, **ket_qua})
        return render(request, self.template_name, {'danh_sach': danh_sach_canh_bao})


class DanhSachCanhBaoPhongDaoTaoView(QuanLyPhongDaoTaoMixin, View):
    """Giống trang của Cố vấn học tập nhưng cho toàn trường, lọc theo học kỳ/năm học (bắt
    buộc chọn để tránh quét toàn bộ sinh viên) và lớp hành chính (tùy chọn)."""

    template_name = 'grades/canh_bao_hoc_vu_phong_dao_tao.html'

    def get(self, request):
        hoc_ky_loc = request.GET.get('hoc_ky', '').strip()
        nam_hoc_loc = request.GET.get('nam_hoc', '').strip()
        ma_lop_loc = request.GET.get('ma_lop', '').strip()

        danh_sach_canh_bao = []
        if hoc_ky_loc and nam_hoc_loc:
            sinh_vien_qs = SinhVien.objects.select_related('ma_lop').order_by('ma_sinh_vien')
            if ma_lop_loc:
                sinh_vien_qs = sinh_vien_qs.filter(ma_lop_id=ma_lop_loc)
            for sv in sinh_vien_qs:
                ket_qua = canh_bao_hoc_vu(sv, hoc_ky_loc, nam_hoc_loc)
                if ket_qua['canh_bao']:
                    danh_sach_canh_bao.append({'sinh_vien': sv, **ket_qua})

        cac_hoc_ky, cac_nam_hoc = danh_sach_bo_loc_hoc_ky()
        return render(request, self.template_name, {
            'danh_sach': danh_sach_canh_bao,
            'hoc_ky_loc': hoc_ky_loc,
            'nam_hoc_loc': nam_hoc_loc,
            'ma_lop_loc': ma_lop_loc,
            'cac_hoc_ky': cac_hoc_ky,
            'cac_nam_hoc': cac_nam_hoc,
            'danh_sach_lop': LopHanhChinh.objects.order_by('ma_lop'),
        })


_CAC_COT_BANG_DIEM = [
    ('Học phần', 6), ('Tín chỉ', 1.5), ('Học kỳ', 1.5), ('Năm học', 2.2),
    ('Điểm QT', 1.8), ('Điểm thi', 1.8), ('Tổng kết', 1.8),
]


@yeu_cau_vai_tro(VaiTro.SINH_VIEN)
def xuat_bang_diem_pdf_view(request):
    sinh_vien = getattr(request.user, 'ho_so_sinh_vien', None)
    if sinh_vien is None:
        messages.error(request, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
        return redirect('accounts:trang_chu')

    # Sinh viên tự xuất bảng điểm của chính mình — chỉ dùng điểm đã công bố, giống trang
    # bang_diem_sinh_vien_view khi chính sinh viên tự xem (không mở rộng ra ngoài, theo
    # đúng ranh giới đã thống nhất ở lượt 4/6).
    danh_sach = DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan__ma_hoc_phan', 'diem').order_by(
        '-ma_lop_hoc_phan__nam_hoc', 'ma_lop_hoc_phan__hoc_ky'
    )
    cac_dong = []
    for dang_ky in danh_sach:
        hoc_phan = dang_ky.ma_lop_hoc_phan.ma_hoc_phan
        diem = getattr(dang_ky, 'diem', None)
        if diem is None:
            diem_qt = diem_thi = tong_ket = 'Chưa nhập'
        elif not diem.da_cong_bo:
            diem_qt = diem_thi = tong_ket = 'Đang chờ công bố'
        else:
            diem_qt = diem.diem_qua_trinh if diem.diem_qua_trinh is not None else '-'
            diem_thi = diem.diem_thi if diem.diem_thi is not None else '-'
            gia_tri_tong_ket = diem.tinh_diem_tong_ket()
            tong_ket = gia_tri_tong_ket if gia_tri_tong_ket is not None else '-'
        cac_dong.append([
            hoc_phan.ten_hoc_phan, hoc_phan.so_tin_chi, dang_ky.ma_lop_hoc_phan.hoc_ky,
            dang_ky.ma_lop_hoc_phan.nam_hoc, diem_qt, diem_thi, tong_ket,
        ])

    diem_tb_tich_luy = diem_trung_binh_tich_luy(sinh_vien, chi_diem_da_cong_bo=True)
    xep_loai = xep_loai_hoc_luc(diem_tb_tich_luy)
    ghi_chu = (
        f'Điểm trung bình tích lũy: {diem_tb_tich_luy if diem_tb_tich_luy is not None else "Chưa có"}'
        f' - Xếp loại: {xep_loai or "Chưa có"}'
    )
    buffer = tao_pdf_bang(
        f'BẢNG ĐIỂM - {sinh_vien.pk}', _CAC_COT_BANG_DIEM, cac_dong,
        dong_trong='Chưa có dữ liệu điểm.', ghi_chu_dau_trang=ghi_chu,
    )
    return FileResponse(buffer, as_attachment=True, filename='bang_diem.pdf')
