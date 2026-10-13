from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from academics.services import danh_sach_bo_loc_hoc_ky
from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin
from enrollment.models import TrangThaiDangKy

from .forms import LichHocForm, LichThiForm, LopHocPhanForm
from .models import LichHoc, LichThi, LopHocPhan
from .services import CAC_THU, xay_dung_luoi_tuan


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class DanhSachLopHocPhanView(QuanLyPhongDaoTaoMixin, ListView):
    model = LopHocPhan
    template_name = 'classes/lop_hoc_phan_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = LopHocPhan.objects.select_related('ma_hoc_phan', 'ma_giang_vien')
        queryset = queryset.order_by('-nam_hoc', 'hoc_ky', 'ma_lop_hoc_phan')
        tu_khoa = self.request.GET.get('q', '').strip()
        hoc_ky = self.request.GET.get('hoc_ky', '').strip()
        nam_hoc = self.request.GET.get('nam_hoc', '').strip()
        if tu_khoa:
            queryset = queryset.filter(
                Q(ma_lop_hoc_phan__icontains=tu_khoa) | Q(ma_hoc_phan__ten_hoc_phan__icontains=tu_khoa)
            )
        if hoc_ky:
            queryset = queryset.filter(hoc_ky=hoc_ky)
        if nam_hoc:
            queryset = queryset.filter(nam_hoc=nam_hoc)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['hoc_ky_loc'] = self.request.GET.get('hoc_ky', '')
        context['nam_hoc_loc'] = self.request.GET.get('nam_hoc', '')
        context['cac_hoc_ky'], context['cac_nam_hoc'] = danh_sach_bo_loc_hoc_ky()
        return context


class TaoLopHocPhanView(QuanLyPhongDaoTaoMixin, CreateView):
    model = LopHocPhan
    form_class = LopHocPhanForm
    template_name = 'classes/form_chung.html'
    success_url = reverse_lazy('classes:lop_hoc_phan_danh_sach')
    extra_context = {'tieu_de': 'Tạo lớp học phần', 'url_danh_sach': 'classes:lop_hoc_phan_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo lớp học phần "{self.object.ma_lop_hoc_phan}".')
        return response


class CapNhatLopHocPhanView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = LopHocPhan
    form_class = LopHocPhanForm
    template_name = 'classes/form_chung.html'
    success_url = reverse_lazy('classes:lop_hoc_phan_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật lớp học phần', 'url_danh_sach': 'classes:lop_hoc_phan_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật lớp học phần "{self.object.ma_lop_hoc_phan}".')
        return response


class DanhSachLichHocView(QuanLyPhongDaoTaoMixin, ListView):
    model = LichHoc
    template_name = 'classes/lich_hoc_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = LichHoc.objects.select_related('ma_lop_hoc_phan').order_by('ma_lop_hoc_phan', 'thu')
        ma_lop_hoc_phan = self.request.GET.get('ma_lop_hoc_phan', '').strip()
        if ma_lop_hoc_phan:
            queryset = queryset.filter(ma_lop_hoc_phan=ma_lop_hoc_phan)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['danh_sach_lop_hoc_phan'] = LopHocPhan.objects.order_by('ma_lop_hoc_phan')
        context['ma_lop_hoc_phan_loc'] = self.request.GET.get('ma_lop_hoc_phan', '')
        return context


class TaoLichHocView(QuanLyPhongDaoTaoMixin, CreateView):
    model = LichHoc
    form_class = LichHocForm
    template_name = 'classes/form_chung.html'
    success_url = reverse_lazy('classes:lich_hoc_danh_sach')
    extra_context = {'tieu_de': 'Tạo lịch học', 'url_danh_sach': 'classes:lich_hoc_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Đã tạo lịch học.')
        return response


class CapNhatLichHocView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = LichHoc
    form_class = LichHocForm
    template_name = 'classes/form_chung.html'
    success_url = reverse_lazy('classes:lich_hoc_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật lịch học', 'url_danh_sach': 'classes:lich_hoc_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Đã cập nhật lịch học.')
        return response


class XoaLichHocView(QuanLyPhongDaoTaoMixin, DeleteView):
    """Xóa một dòng lịch học. Không có bảng nào tham chiếu tới lịch học nên không chặn; nhưng lịch học quyết định
    thời khóa biểu của sinh viên và kiểm tra trùng lịch khi đăng ký, nên trang xác nhận nêu rõ số sinh viên đang
    đăng ký lớp đó sẽ bị ảnh hưởng để Phòng Đào tạo tự quyết định."""

    model = LichHoc
    template_name = 'classes/lich_hoc_xac_nhan_xoa.html'
    success_url = reverse_lazy('classes:lich_hoc_danh_sach')
    context_object_name = 'lich'

    def get_queryset(self):
        return LichHoc.objects.select_related('ma_lop_hoc_phan')

    def _so_sinh_vien_dang_ky(self):
        return self.object.ma_lop_hoc_phan.dang_ky.filter(trang_thai=TrangThaiDangKy.CON_HIEU_LUC).count()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['so_sinh_vien'] = self._so_sinh_vien_dang_ky()
        return context

    def form_valid(self, form):
        lich = self.object
        mo_ta = f'lớp "{lich.ma_lop_hoc_phan_id}", Thứ {lich.thu}, tiết {lich.tiet_bat_dau}'
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa lịch học ({mo_ta}).')
        return response


class GiangVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.GIANG_VIEN,)

    def get_giang_vien(self):
        return getattr(self.request.user, 'ho_so_giang_vien', None)


class LopPhuTrachView(GiangVienMixin, ListView):
    model = LopHocPhan
    template_name = 'classes/lop_phu_trach.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        giang_vien = self.get_giang_vien()
        if giang_vien is None:
            return LopHocPhan.objects.none()
        return LopHocPhan.objects.filter(ma_giang_vien=giang_vien).select_related('ma_hoc_phan').order_by(
            '-nam_hoc', 'hoc_ky'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['co_ho_so'] = self.get_giang_vien() is not None
        return context


class LichGiangDayView(GiangVienMixin, ListView):
    model = LichHoc
    template_name = 'classes/lich_giang_day.html'
    context_object_name = 'danh_sach'

    def get_queryset(self):
        giang_vien = self.get_giang_vien()
        if giang_vien is None:
            return LichHoc.objects.none()
        return LichHoc.objects.filter(ma_lop_hoc_phan__ma_giang_vien=giang_vien).select_related(
            'ma_lop_hoc_phan__ma_hoc_phan'
        ).order_by('thu', 'tiet_bat_dau')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['co_ho_so'] = self.get_giang_vien() is not None
        context['xem_luoi'] = self.request.GET.get('xem') == 'luoi'
        context['cac_thu'] = CAC_THU
        context['luoi_tuan'] = xay_dung_luoi_tuan(context[self.context_object_name])
        return context


class DanhSachLichThiView(QuanLyPhongDaoTaoMixin, ListView):
    model = LichThi
    template_name = 'classes/lich_thi_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = LichThi.objects.select_related('lop_hoc_phan__ma_hoc_phan').order_by(
            '-lop_hoc_phan__nam_hoc', 'lop_hoc_phan__hoc_ky', 'ngay_thi', 'gio_bat_dau'
        )
        hoc_ky = self.request.GET.get('hoc_ky', '').strip()
        nam_hoc = self.request.GET.get('nam_hoc', '').strip()
        if hoc_ky:
            queryset = queryset.filter(lop_hoc_phan__hoc_ky=hoc_ky)
        if nam_hoc:
            queryset = queryset.filter(lop_hoc_phan__nam_hoc=nam_hoc)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoc_ky_loc'] = self.request.GET.get('hoc_ky', '')
        context['nam_hoc_loc'] = self.request.GET.get('nam_hoc', '')
        context['cac_hoc_ky'], context['cac_nam_hoc'] = danh_sach_bo_loc_hoc_ky()
        return context


class TaoLichThiView(QuanLyPhongDaoTaoMixin, CreateView):
    model = LichThi
    form_class = LichThiForm
    template_name = 'classes/form_chung.html'
    success_url = reverse_lazy('classes:lich_thi_danh_sach')
    extra_context = {'tieu_de': 'Tạo lịch thi', 'url_danh_sach': 'classes:lich_thi_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo lịch thi cho lớp "{self.object.lop_hoc_phan_id}".')
        return response


class CapNhatLichThiView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = LichThi
    form_class = LichThiForm
    template_name = 'classes/form_chung.html'
    success_url = reverse_lazy('classes:lich_thi_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật lịch thi', 'url_danh_sach': 'classes:lich_thi_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật lịch thi cho lớp "{self.object.lop_hoc_phan_id}".')
        return response


class XoaLichThiView(QuanLyPhongDaoTaoMixin, DeleteView):
    model = LichThi
    template_name = 'classes/lich_thi_xac_nhan_xoa.html'
    success_url = reverse_lazy('classes:lich_thi_danh_sach')
    context_object_name = 'lich_thi'

    def form_valid(self, form):
        ten = f'{self.object.lop_hoc_phan_id}'
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa lịch thi của lớp "{ten}".')
        return response
