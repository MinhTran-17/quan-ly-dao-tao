from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin, yeu_cau_vai_tro

from classes.models import LopHocPhan

from .forms import (
    CapNhatLopHanhChinhForm, ChiTietChuongTrinhForm, ChuongTrinhDaoTaoForm, DieuKienTienQuyetForm, DotDangKyForm,
    HocKyForm, HocPhanForm, LopHanhChinhForm, NganhHocForm,
)
from .models import (
    ChiTietChuongTrinh, ChuongTrinhDaoTao, DieuKienTienQuyet, DotDangKy, HocKy, HocPhan, LopHanhChinh, NganhHoc,
)
from .services import co_dang_ky_trong_dot


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class DanhSachNganhHocView(QuanLyPhongDaoTaoMixin, ListView):
    model = NganhHoc
    template_name = 'academics/nganh_hoc_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = NganhHoc.objects.order_by('ma_nganh')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            queryset = queryset.filter(Q(ma_nganh__icontains=tu_khoa) | Q(ten_nganh__icontains=tu_khoa))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaoNganhHocView(QuanLyPhongDaoTaoMixin, CreateView):
    model = NganhHoc
    form_class = NganhHocForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:nganh_hoc_danh_sach')
    extra_context = {'tieu_de': 'Tạo ngành học', 'url_danh_sach': 'academics:nganh_hoc_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo ngành "{self.object.ma_nganh}".')
        return response


class CapNhatNganhHocView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = NganhHoc
    form_class = NganhHocForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:nganh_hoc_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật ngành học', 'url_danh_sach': 'academics:nganh_hoc_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật ngành "{self.object.ma_nganh}".')
        return response


class XoaNganhHocView(QuanLyPhongDaoTaoMixin, DeleteView):
    """Xóa ngành học: chỉ khi chưa có lớp hành chính hay chương trình đào tạo nào dùng ngành đó
    (cả hai khóa ngoại đều PROTECT); đang được dùng thì chặn kèm số lượng cụ thể."""

    model = NganhHoc
    template_name = 'academics/nganh_hoc_xac_nhan_xoa.html'
    success_url = reverse_lazy('academics:nganh_hoc_danh_sach')
    context_object_name = 'nganh'

    @staticmethod
    def _dang_su_dung(nganh):
        return (
            LopHanhChinh.objects.filter(ma_nganh=nganh).count(),
            ChuongTrinhDaoTao.objects.filter(nganh=nganh).count(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['so_lop_hanh_chinh'], context['so_chuong_trinh'] = self._dang_su_dung(self.object)
        return context

    def form_valid(self, form):
        nganh = self.object
        so_lop, so_chuong_trinh = self._dang_su_dung(nganh)
        if so_lop or so_chuong_trinh:
            messages.error(
                self.request,
                f'Không thể xóa ngành "{nganh}" vì còn {so_lop} lớp hành chính và {so_chuong_trinh} chương trình '
                'đào tạo đang dùng ngành này.',
            )
            return redirect(self.success_url)
        ten = str(nganh)
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa ngành "{ten}".')
        return response


class DanhSachLopHanhChinhView(QuanLyPhongDaoTaoMixin, ListView):
    model = LopHanhChinh
    template_name = 'academics/lop_hanh_chinh_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = LopHanhChinh.objects.select_related(
            'ma_nganh', 'ma_co_van', 'chuong_trinh_dao_tao'
        ).order_by('ma_lop')
        tu_khoa = self.request.GET.get('q', '').strip()
        ma_nganh = self.request.GET.get('ma_nganh', '').strip()
        if tu_khoa:
            queryset = queryset.filter(Q(ma_lop__icontains=tu_khoa) | Q(ten_lop__icontains=tu_khoa))
        if ma_nganh:
            queryset = queryset.filter(ma_nganh=ma_nganh)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['danh_sach_nganh'] = NganhHoc.objects.order_by('ma_nganh')
        context['q'] = self.request.GET.get('q', '')
        context['ma_nganh_loc'] = self.request.GET.get('ma_nganh', '')
        return context


class TaoLopHanhChinhView(QuanLyPhongDaoTaoMixin, CreateView):
    model = LopHanhChinh
    form_class = LopHanhChinhForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:lop_hanh_chinh_danh_sach')
    extra_context = {'tieu_de': 'Tạo lớp hành chính', 'url_danh_sach': 'academics:lop_hanh_chinh_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo lớp "{self.object.ma_lop}".')
        return response


class CapNhatLopHanhChinhView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = LopHanhChinh
    form_class = CapNhatLopHanhChinhForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:lop_hanh_chinh_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật lớp hành chính', 'url_danh_sach': 'academics:lop_hanh_chinh_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật lớp "{self.object.ma_lop}".')
        return response


class DanhSachHocPhanView(QuanLyPhongDaoTaoMixin, ListView):
    model = HocPhan
    template_name = 'academics/hoc_phan_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = HocPhan.objects.order_by('ma_hoc_phan')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            queryset = queryset.filter(Q(ma_hoc_phan__icontains=tu_khoa) | Q(ten_hoc_phan__icontains=tu_khoa))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaoHocPhanView(QuanLyPhongDaoTaoMixin, CreateView):
    model = HocPhan
    form_class = HocPhanForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:hoc_phan_danh_sach')
    extra_context = {'tieu_de': 'Tạo học phần', 'url_danh_sach': 'academics:hoc_phan_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo học phần "{self.object.ma_hoc_phan}".')
        return response


class CapNhatHocPhanView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = HocPhan
    form_class = HocPhanForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:hoc_phan_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật học phần', 'url_danh_sach': 'academics:hoc_phan_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật học phần "{self.object.ma_hoc_phan}".')
        return response


class XoaHocPhanView(QuanLyPhongDaoTaoMixin, DeleteView):
    """Xóa học phần: chỉ khi chưa có lớp học phần, điều kiện tiên quyết (ở cả hai phía) hay chương trình đào tạo
    nào dùng học phần đó (các khóa ngoại đều PROTECT); đang được dùng thì chặn kèm số lượng cụ thể."""

    model = HocPhan
    template_name = 'academics/hoc_phan_xac_nhan_xoa.html'
    success_url = reverse_lazy('academics:hoc_phan_danh_sach')
    context_object_name = 'hoc_phan'

    @staticmethod
    def _dang_su_dung(hoc_phan):
        return {
            'lop_hoc_phan': hoc_phan.lop_hoc_phan.count(),
            'dieu_kien_tien_quyet': (
                hoc_phan.dieu_kien_tien_quyet.count() + hoc_phan.la_tien_quyet_cua.count()
            ),
            'chuong_trinh_dao_tao': hoc_phan.chi_tiet_chuong_trinh.count(),
        }

    @staticmethod
    def _mo_ta(su_dung):
        return (
            f'{su_dung["lop_hoc_phan"]} lớp học phần, {su_dung["dieu_kien_tien_quyet"]} điều kiện tiên quyết và '
            f'{su_dung["chuong_trinh_dao_tao"]} mục trong chương trình đào tạo'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        su_dung = self._dang_su_dung(self.object)
        context['dang_dung'] = any(su_dung.values())
        context['mo_ta_su_dung'] = self._mo_ta(su_dung)
        return context

    def form_valid(self, form):
        hoc_phan = self.object
        su_dung = self._dang_su_dung(hoc_phan)
        if any(su_dung.values()):
            messages.error(
                self.request,
                f'Không thể xóa học phần "{hoc_phan.ma_hoc_phan}" vì còn {self._mo_ta(su_dung)} đang dùng học phần này.',
            )
            return redirect(self.success_url)
        ma = hoc_phan.ma_hoc_phan
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa học phần "{ma}".')
        return response


class DanhSachDieuKienTienQuyetView(QuanLyPhongDaoTaoMixin, ListView):
    model = DieuKienTienQuyet
    template_name = 'academics/dieu_kien_tien_quyet_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = DieuKienTienQuyet.objects.select_related('ma_hoc_phan', 'ma_hoc_phan_tien_quyet')
        queryset = queryset.order_by('ma_hoc_phan')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            # ma_hoc_phan và ma_hoc_phan_tien_quyet là khóa ngoại: tìm trên cột của học phần được trỏ tới
            # (icontains trực tiếp trên khóa ngoại làm trang báo lỗi 500).
            queryset = queryset.filter(
                Q(ma_hoc_phan__ma_hoc_phan__icontains=tu_khoa) | Q(ma_hoc_phan__ten_hoc_phan__icontains=tu_khoa)
                | Q(ma_hoc_phan_tien_quyet__ma_hoc_phan__icontains=tu_khoa)
                | Q(ma_hoc_phan_tien_quyet__ten_hoc_phan__icontains=tu_khoa)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaoDieuKienTienQuyetView(QuanLyPhongDaoTaoMixin, CreateView):
    model = DieuKienTienQuyet
    form_class = DieuKienTienQuyetForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:dieu_kien_tien_quyet_danh_sach')
    extra_context = {
        'tieu_de': 'Tạo điều kiện tiên quyết',
        'url_danh_sach': 'academics:dieu_kien_tien_quyet_danh_sach',
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Đã tạo điều kiện tiên quyết.')
        return response


class CapNhatDieuKienTienQuyetView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = DieuKienTienQuyet
    form_class = DieuKienTienQuyetForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:dieu_kien_tien_quyet_danh_sach')
    extra_context = {
        'tieu_de': 'Cập nhật điều kiện tiên quyết',
        'url_danh_sach': 'academics:dieu_kien_tien_quyet_danh_sach',
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Đã cập nhật điều kiện tiên quyết.')
        return response


class XoaDieuKienTienQuyetView(QuanLyPhongDaoTaoMixin, DeleteView):
    """Xóa một điều kiện tiên quyết. Không có bảng nào tham chiếu tới dòng này (chỉ là luật khi đăng ký), nên
    không cần chặn; các đăng ký đã có không bị ảnh hưởng, chỉ các lần đăng ký sau không còn bị kiểm tra luật này."""

    model = DieuKienTienQuyet
    template_name = 'academics/dieu_kien_tien_quyet_xac_nhan_xoa.html'
    success_url = reverse_lazy('academics:dieu_kien_tien_quyet_danh_sach')
    context_object_name = 'dieu_kien'

    def get_queryset(self):
        return DieuKienTienQuyet.objects.select_related('ma_hoc_phan', 'ma_hoc_phan_tien_quyet')

    def form_valid(self, form):
        dieu_kien = self.object
        mo_ta = f'"{dieu_kien.ma_hoc_phan.ten_hoc_phan}" cần tiên quyết "{dieu_kien.ma_hoc_phan_tien_quyet.ten_hoc_phan}"'
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa điều kiện tiên quyết: {mo_ta}.')
        return response


class DanhSachHocKyView(QuanLyPhongDaoTaoMixin, ListView):
    model = HocKy
    template_name = 'academics/hoc_ky_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20


class TaoHocKyView(QuanLyPhongDaoTaoMixin, CreateView):
    model = HocKy
    form_class = HocKyForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:hoc_ky_danh_sach')
    extra_context = {'tieu_de': 'Tạo học kỳ', 'url_danh_sach': 'academics:hoc_ky_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo "{self.object}".')
        return response


class CapNhatHocKyView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = HocKy
    form_class = HocKyForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:hoc_ky_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật học kỳ', 'url_danh_sach': 'academics:hoc_ky_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật "{self.object}".')
        return response


class XoaHocKyView(QuanLyPhongDaoTaoMixin, DeleteView):
    model = HocKy
    template_name = 'academics/hoc_ky_xac_nhan_xoa.html'
    success_url = reverse_lazy('academics:hoc_ky_danh_sach')
    context_object_name = 'hoc_ky'

    def form_valid(self, form):
        hoc_ky = self.object
        dang_su_dung = LopHocPhan.objects.filter(
            hoc_ky=str(hoc_ky.hoc_ky), nam_hoc=hoc_ky.nam_hoc,
        ).exists()
        if dang_su_dung:
            messages.error(
                self.request,
                f'Không thể xóa "{hoc_ky}" vì đã có lớp học phần dùng học kỳ/năm học này.',
            )
            return redirect(self.success_url)
        ten = str(hoc_ky)
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa "{ten}".')
        return response


class DanhSachDotDangKyView(QuanLyPhongDaoTaoMixin, ListView):
    model = DotDangKy
    template_name = 'academics/dot_dang_ky_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        return DotDangKy.objects.select_related('hoc_ky').order_by('-hoc_ky__nam_hoc', 'hoc_ky__hoc_ky', 'ngay_mo')


class TaoDotDangKyView(QuanLyPhongDaoTaoMixin, CreateView):
    model = DotDangKy
    form_class = DotDangKyForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:dot_dang_ky_danh_sach')
    extra_context = {'tieu_de': 'Tạo đợt đăng ký', 'url_danh_sach': 'academics:dot_dang_ky_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo "{self.object}".')
        return response


class CapNhatDotDangKyView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = DotDangKy
    form_class = DotDangKyForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:dot_dang_ky_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật đợt đăng ký', 'url_danh_sach': 'academics:dot_dang_ky_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật "{self.object}".')
        return response


class XoaDotDangKyView(QuanLyPhongDaoTaoMixin, DeleteView):
    model = DotDangKy
    template_name = 'academics/dot_dang_ky_xac_nhan_xoa.html'
    success_url = reverse_lazy('academics:dot_dang_ky_danh_sach')
    context_object_name = 'dot_dang_ky'

    def form_valid(self, form):
        dot = self.object
        if co_dang_ky_trong_dot(dot):
            messages.error(self.request, f'Không thể xóa "{dot}" vì đã có sinh viên đăng ký trong đợt này.')
            return redirect(self.success_url)
        ten = str(dot)
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa "{ten}".')
        return response


class DanhSachChuongTrinhDaoTaoView(QuanLyPhongDaoTaoMixin, ListView):
    model = ChuongTrinhDaoTao
    template_name = 'academics/chuong_trinh_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = ChuongTrinhDaoTao.objects.select_related('nganh').annotate(
            so_hoc_phan=Count('chi_tiet')
        ).order_by('nganh', 'khoa_hoc')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            queryset = queryset.filter(
                Q(ten_chuong_trinh__icontains=tu_khoa) | Q(nganh__ten_nganh__icontains=tu_khoa)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaoChuongTrinhDaoTaoView(QuanLyPhongDaoTaoMixin, CreateView):
    model = ChuongTrinhDaoTao
    form_class = ChuongTrinhDaoTaoForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:chuong_trinh_danh_sach')
    extra_context = {'tieu_de': 'Tạo chương trình đào tạo', 'url_danh_sach': 'academics:chuong_trinh_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo chương trình "{self.object.ten_chuong_trinh}".')
        return response


class CapNhatChuongTrinhDaoTaoView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = ChuongTrinhDaoTao
    form_class = ChuongTrinhDaoTaoForm
    template_name = 'academics/form_chung.html'
    success_url = reverse_lazy('academics:chuong_trinh_danh_sach')
    extra_context = {
        'tieu_de': 'Cập nhật chương trình đào tạo', 'url_danh_sach': 'academics:chuong_trinh_danh_sach',
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật chương trình "{self.object.ten_chuong_trinh}".')
        return response


class XoaChuongTrinhDaoTaoView(QuanLyPhongDaoTaoMixin, DeleteView):
    """Xóa chương trình đào tạo. Chặn nếu còn lớp hành chính được gán chương trình này (khóa ngoại PROTECT). Các dòng
    học phần trong lộ trình (chi_tiet_chuong_trinh) là nội dung của chính chương trình nên được xóa cùng, trong một
    transaction; trang xác nhận nêu rõ số học phần sẽ bị xóa khỏi lộ trình. Bản thân các học phần không bị xóa."""

    model = ChuongTrinhDaoTao
    template_name = 'academics/chuong_trinh_xac_nhan_xoa.html'
    success_url = reverse_lazy('academics:chuong_trinh_danh_sach')
    context_object_name = 'chuong_trinh'

    def get_queryset(self):
        return ChuongTrinhDaoTao.objects.select_related('nganh')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['so_lop_hanh_chinh'] = LopHanhChinh.objects.filter(chuong_trinh_dao_tao=self.object).count()
        context['so_hoc_phan'] = ChiTietChuongTrinh.objects.filter(chuong_trinh=self.object).count()
        return context

    def form_valid(self, form):
        chuong_trinh = self.object
        so_lop = LopHanhChinh.objects.filter(chuong_trinh_dao_tao=chuong_trinh).count()
        if so_lop:
            messages.error(
                self.request,
                f'Không thể xóa chương trình "{chuong_trinh.ten_chuong_trinh}" vì còn {so_lop} lớp hành chính đang '
                'được gán chương trình này. Hãy gán chương trình khác (hoặc bỏ gán) ở trang sửa lớp hành chính trước.',
            )
            return redirect(self.success_url)
        ten = chuong_trinh.ten_chuong_trinh
        with transaction.atomic():
            ChiTietChuongTrinh.objects.filter(chuong_trinh=chuong_trinh).delete()
            response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa chương trình "{ten}".')
        return response


class ChiTietChuongTrinhView(QuanLyPhongDaoTaoMixin, View):
    """Trang quản lý một chương trình đào tạo: danh sách học phần đã có trong chương
    trình, và khung tìm/lọc + thêm học phần chưa có (mỗi dòng học phần khả dụng có một
    form nhỏ riêng để nhập học kỳ dự kiến/bắt buộc rồi thêm ngay, không cần trang riêng)."""

    template_name = 'academics/chuong_trinh_chi_tiet.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.chuong_trinh = get_object_or_404(ChuongTrinhDaoTao, pk=kwargs['pk'])

    def _hoc_phan_kha_dung(self, tu_khoa):
        da_co = ChiTietChuongTrinh.objects.filter(chuong_trinh=self.chuong_trinh).values_list('hoc_phan_id', flat=True)
        queryset = HocPhan.objects.exclude(pk__in=da_co).order_by('ma_hoc_phan')
        if tu_khoa:
            queryset = queryset.filter(Q(ma_hoc_phan__icontains=tu_khoa) | Q(ten_hoc_phan__icontains=tu_khoa))
        return queryset

    def get(self, request, *args, **kwargs):
        tu_khoa = request.GET.get('q', '').strip()
        return render(request, self.template_name, {
            'chuong_trinh': self.chuong_trinh,
            'chi_tiet_danh_sach': ChiTietChuongTrinh.objects.filter(
                chuong_trinh=self.chuong_trinh
            ).select_related('hoc_phan').order_by('hoc_ky_du_kien', 'hoc_phan'),
            'hoc_phan_kha_dung': self._hoc_phan_kha_dung(tu_khoa),
            'q': tu_khoa,
        })

    def post(self, request, *args, **kwargs):
        form = ChiTietChuongTrinhForm(request.POST)
        if form.is_valid():
            chi_tiet = form.save(commit=False)
            chi_tiet.chuong_trinh = self.chuong_trinh
            try:
                # Bọc trong savepoint riêng: bắt IntegrityError mà không lồng atomic() sẽ
                # làm "bẩn" cả transaction bên ngoài (ví dụ transaction bọc mỗi test của
                # Django TestCase), khiến mọi truy vấn sau đó lỗi "you can't execute
                # queries until the end of the 'atomic' block" dù đã catch được lỗi này.
                with transaction.atomic():
                    chi_tiet.save()
            except IntegrityError:
                messages.error(request, 'Học phần này đã có trong chương trình.')
            else:
                messages.success(
                    request, f'Đã thêm học phần "{chi_tiet.hoc_phan.ten_hoc_phan}" vào chương trình.',
                )
        else:
            messages.error(request, 'Không thêm được học phần: dữ liệu không hợp lệ.')
        return redirect('academics:chuong_trinh_chi_tiet', pk=self.chuong_trinh.pk)


class SuaChiTietChuongTrinhView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = ChiTietChuongTrinh
    form_class = ChiTietChuongTrinhForm
    template_name = 'academics/chi_tiet_chuong_trinh_form.html'

    def get_success_url(self):
        return reverse('academics:chuong_trinh_chi_tiet', args=[self.object.chuong_trinh_id])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật học phần "{self.object.hoc_phan.ten_hoc_phan}" trong chương trình.')
        return response


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO)
@require_POST
def xoa_chi_tiet_chuong_trinh(request, pk):
    chi_tiet = get_object_or_404(ChiTietChuongTrinh, pk=pk)
    chuong_trinh_pk = chi_tiet.chuong_trinh_id
    ten_hoc_phan = chi_tiet.hoc_phan.ten_hoc_phan
    # Chỉ là dữ liệu tham chiếu (chương trình khung) — không chặn cứng dù học phần này có
    # thể đã được dùng để tính tiến độ cho sinh viên, theo đúng yêu cầu (không bắt buộc).
    chi_tiet.delete()
    messages.success(request, f'Đã bỏ học phần "{ten_hoc_phan}" khỏi chương trình.')
    return redirect('academics:chuong_trinh_chi_tiet', pk=chuong_trinh_pk)
