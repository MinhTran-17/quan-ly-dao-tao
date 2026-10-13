from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from academics.excel_utils import phan_hoi_excel, tao_workbook_excel
from academics.models import LopHanhChinh, NganhHoc
from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin

from .forms import CoVanHocTapForm, GiangVienForm, NhapSinhVienExcelForm, SinhVienForm
from .models import CoVanHocTap, GiangVien, SinhVien
from .services import TIEU_DE_COT_MAU_SINH_VIEN, xu_ly_file_excel_sinh_vien


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class DanhSachSinhVienView(QuanLyPhongDaoTaoMixin, ListView):
    model = SinhVien
    template_name = 'people/sinh_vien_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = SinhVien.objects.select_related('ma_lop').order_by('ma_sinh_vien')
        tu_khoa = self.request.GET.get('q', '').strip()
        ma_lop = self.request.GET.get('ma_lop', '').strip()
        ma_nganh = self.request.GET.get('ma_nganh', '').strip()
        if tu_khoa:
            queryset = queryset.filter(Q(ma_sinh_vien__icontains=tu_khoa) | Q(ho_ten__icontains=tu_khoa))
        if ma_lop:
            queryset = queryset.filter(ma_lop=ma_lop)
        if ma_nganh:
            queryset = queryset.filter(ma_lop__ma_nganh=ma_nganh)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['danh_sach_lop'] = LopHanhChinh.objects.order_by('ma_lop')
        context['danh_sach_nganh'] = NganhHoc.objects.order_by('ma_nganh')
        context['q'] = self.request.GET.get('q', '')
        context['ma_lop_loc'] = self.request.GET.get('ma_lop', '')
        context['ma_nganh_loc'] = self.request.GET.get('ma_nganh', '')
        return context


class TaoSinhVienView(QuanLyPhongDaoTaoMixin, CreateView):
    model = SinhVien
    form_class = SinhVienForm
    template_name = 'people/ho_so_form.html'
    success_url = reverse_lazy('people:sinh_vien_danh_sach')
    extra_context = {'tieu_de': 'Tạo sinh viên', 'url_danh_sach': 'people:sinh_vien_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo sinh viên "{self.object.ma_sinh_vien}".')
        return response


class CapNhatSinhVienView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = SinhVien
    form_class = SinhVienForm
    template_name = 'people/ho_so_form.html'
    success_url = reverse_lazy('people:sinh_vien_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật sinh viên', 'url_danh_sach': 'people:sinh_vien_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật sinh viên "{self.object.ma_sinh_vien}".')
        return response


class TaiMauSinhVienExcelView(QuanLyPhongDaoTaoMixin, View):
    def get(self, request):
        workbook = tao_workbook_excel('Mau sinh vien', TIEU_DE_COT_MAU_SINH_VIEN, [])
        return phan_hoi_excel(workbook, 'mau_sinh_vien.xlsx')


class NhapSinhVienExcelView(QuanLyPhongDaoTaoMixin, View):
    template_name = 'people/nhap_sinh_vien_excel.html'

    def get(self, request):
        return render(request, self.template_name, {'form': NhapSinhVienExcelForm()})

    def post(self, request):
        form = NhapSinhVienExcelForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
        ket_qua = xu_ly_file_excel_sinh_vien(form.cleaned_data['file_excel'])
        return render(request, 'people/nhap_sinh_vien_excel_ket_qua.html', {'ket_qua': ket_qua})


class DanhSachGiangVienView(QuanLyPhongDaoTaoMixin, ListView):
    model = GiangVien
    template_name = 'people/giang_vien_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = GiangVien.objects.order_by('ma_giang_vien')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            queryset = queryset.filter(Q(ma_giang_vien__icontains=tu_khoa) | Q(ho_ten__icontains=tu_khoa))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaoGiangVienView(QuanLyPhongDaoTaoMixin, CreateView):
    model = GiangVien
    form_class = GiangVienForm
    template_name = 'people/ho_so_form.html'
    success_url = reverse_lazy('people:giang_vien_danh_sach')
    extra_context = {'tieu_de': 'Tạo giảng viên', 'url_danh_sach': 'people:giang_vien_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo giảng viên "{self.object.ma_giang_vien}".')
        return response


class CapNhatGiangVienView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = GiangVien
    form_class = GiangVienForm
    template_name = 'people/ho_so_form.html'
    success_url = reverse_lazy('people:giang_vien_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật giảng viên', 'url_danh_sach': 'people:giang_vien_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật giảng viên "{self.object.ma_giang_vien}".')
        return response


class DanhSachCoVanView(QuanLyPhongDaoTaoMixin, ListView):
    model = CoVanHocTap
    template_name = 'people/co_van_danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = CoVanHocTap.objects.order_by('ma_co_van')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            queryset = queryset.filter(Q(ma_co_van__icontains=tu_khoa) | Q(ho_ten__icontains=tu_khoa))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaoCoVanView(QuanLyPhongDaoTaoMixin, CreateView):
    model = CoVanHocTap
    form_class = CoVanHocTapForm
    template_name = 'people/ho_so_form.html'
    success_url = reverse_lazy('people:co_van_danh_sach')
    extra_context = {'tieu_de': 'Tạo cố vấn học tập', 'url_danh_sach': 'people:co_van_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo cố vấn học tập "{self.object.ma_co_van}".')
        return response


class CapNhatCoVanView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = CoVanHocTap
    form_class = CoVanHocTapForm
    template_name = 'people/ho_so_form.html'
    success_url = reverse_lazy('people:co_van_danh_sach')
    extra_context = {'tieu_de': 'Cập nhật cố vấn học tập', 'url_danh_sach': 'people:co_van_danh_sach'}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật cố vấn học tập "{self.object.ma_co_van}".')
        return response


class XoaHoSoView(QuanLyPhongDaoTaoMixin, DeleteView):
    """Xóa hồ sơ sinh viên/giảng viên/cố vấn học tập: chỉ khi chưa có dữ liệu nào đi kèm (các khóa ngoại tới hồ sơ đều
    PROTECT); đang liên quan thì chặn kèm số lượng cụ thể và gợi ý khóa tài khoản. Chỉ xóa HỒ SƠ: tài khoản đăng nhập
    gắn với hồ sơ vẫn còn (không còn gắn hồ sơ nào)."""

    template_name = 'people/ho_so_xac_nhan_xoa.html'
    context_object_name = 'ho_so'
    ten_loai = ''
    ten_url_danh_sach = ''
    # ((tên quan hệ ngược, mô tả), ...) — các bản ghi khác đang tham chiếu tới hồ sơ.
    quan_he_phu_thuoc = ()

    def get_success_url(self):
        return reverse_lazy(self.ten_url_danh_sach)

    def _dang_lien_quan(self, ho_so):
        ket_qua = []
        for ten_quan_he, mo_ta in self.quan_he_phu_thuoc:
            so_luong = getattr(ho_so, ten_quan_he).count()
            if so_luong:
                ket_qua.append(f'{so_luong} {mo_ta}')
        return ket_qua

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ten_loai'] = self.ten_loai
        context['dang_lien_quan'] = self._dang_lien_quan(self.object)
        context['url_danh_sach'] = self.ten_url_danh_sach
        return context

    def form_valid(self, form):
        ho_so = self.object
        dang_lien_quan = self._dang_lien_quan(ho_so)
        if dang_lien_quan:
            messages.error(
                self.request,
                f'Không thể xóa {self.ten_loai} "{ho_so.pk}" vì còn {", ".join(dang_lien_quan)} liên quan. '
                'Nếu người này không còn hoạt động, hãy khóa tài khoản thay vì xóa hồ sơ.',
            )
            return redirect(self.get_success_url())
        ma = ho_so.pk
        ten_dang_nhap = ho_so.ma_tai_khoan.ten_dang_nhap
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Đã xóa hồ sơ {self.ten_loai} "{ma}". Tài khoản "{ten_dang_nhap}" vẫn còn nhưng không gắn hồ sơ nào.',
        )
        return response


class XoaSinhVienView(XoaHoSoView):
    model = SinhVien
    ten_loai = 'sinh viên'
    ten_url_danh_sach = 'people:sinh_vien_danh_sach'
    quan_he_phu_thuoc = (('dang_ky_hoc_phan', 'bản đăng ký học phần'), ('diem_danh', 'bản ghi điểm danh'))


class XoaGiangVienView(XoaHoSoView):
    model = GiangVien
    ten_loai = 'giảng viên'
    ten_url_danh_sach = 'people:giang_vien_danh_sach'
    quan_he_phu_thuoc = (('lop_phu_trach', 'lớp học phần đang phụ trách'),)


class XoaCoVanView(XoaHoSoView):
    model = CoVanHocTap
    ten_loai = 'cố vấn học tập'
    ten_url_danh_sach = 'people:co_van_danh_sach'
    quan_he_phu_thuoc = (('lop_phu_trach', 'lớp hành chính đang phụ trách'),)
