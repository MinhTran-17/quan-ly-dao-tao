from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import (
    CapNhatTaiKhoanForm, DangNhapForm, DatLaiMatKhauQuaEmailForm, DoiMatKhauForm, QuenMatKhauForm, TaoTaiKhoanForm,
    ThongTinLienHeForm,
)
from .gioi_han_dang_nhap import cho_phep_yeu_cau_quen_mat_khau, lay_ip
from .gui_email import che_email, logger as logger_email
from .models import TaiKhoan, VaiTro
from .permissions import YeuCauVaiTroMixin, yeu_cau_vai_tro
from .services import tao_mat_khau_tam
from .tong_hop_co_van import tong_hop_trang_chu_co_van
from .tong_hop_giang_vien import tong_hop_trang_chu_giang_vien
from .tong_hop_phong_dao_tao import tong_hop_trang_chu_phong_dao_tao
from .tong_hop_sinh_vien import tong_hop_trang_chu_sinh_vien


class DangNhapView(LoginView):
    template_name = 'accounts/dang_nhap.html'
    authentication_form = DangNhapForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Xin chào, {self.request.user.ten_dang_nhap}.')
        return response


class QuenMatKhauView(PasswordResetView):
    """Bước 1: nhập email, gửi link đặt lại (link dùng một lần, hết hạn sau PASSWORD_RESET_TIMEOUT).
    Mỗi email và mỗi IP tối đa 3 yêu cầu trong 15 phút (accounts/gioi_han_dang_nhap.py)."""
    template_name = 'accounts/quen_mat_khau.html'
    form_class = QuenMatKhauForm
    subject_template_name = 'accounts/email/dat_lai_mat_khau_tieu_de.txt'
    email_template_name = 'accounts/email/dat_lai_mat_khau.txt'
    success_url = reverse_lazy('accounts:quen_mat_khau_da_gui')
    extra_email_context = {'TEN_HE_THONG': settings.TEN_HE_THONG}

    def form_valid(self, form):
        if not cho_phep_yeu_cau_quen_mat_khau(form.cleaned_data['email'], lay_ip(self.request)):
            logger_email.info('Quên mật khẩu: không gửi thư tới %s (vượt giới hạn 3 yêu cầu/15 phút).',
                              che_email(form.cleaned_data['email']))
            form.add_error(None, 'Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau 15 phút.')
            return self.form_invalid(form)
        return super().form_valid(form)


class QuenMatKhauDaGuiView(PasswordResetDoneView):
    template_name = 'accounts/quen_mat_khau_da_gui.html'


class DatLaiMatKhauXacNhanView(PasswordResetConfirmView):
    template_name = 'accounts/dat_lai_mat_khau_xac_nhan.html'
    form_class = DatLaiMatKhauQuaEmailForm
    success_url = reverse_lazy('accounts:dat_lai_mat_khau_xong')


class DatLaiMatKhauXongView(PasswordResetCompleteView):
    template_name = 'accounts/dat_lai_mat_khau_xong.html'


@require_POST
def dang_xuat(request):
    logout(request)
    return redirect('accounts:dang_nhap')


@login_required
def trang_chu(request):
    # Mỗi vai trò có khối tổng hợp riêng (dữ liệu gọi lại từ service sẵn có); lưới thẻ chức năng
    # đã bỏ vì menu trên thanh có đủ liên kết.
    context = {}
    if request.user.vai_tro == VaiTro.SINH_VIEN:
        context['tong_hop'] = tong_hop_trang_chu_sinh_vien(
            request.user, getattr(request.user, 'ho_so_sinh_vien', None),
        )
    elif request.user.vai_tro == VaiTro.PHONG_DAO_TAO:
        context['tong_hop'] = tong_hop_trang_chu_phong_dao_tao()
    elif request.user.vai_tro == VaiTro.GIANG_VIEN:
        context['tong_hop'] = tong_hop_trang_chu_giang_vien(
            getattr(request.user, 'ho_so_giang_vien', None), request.user,
        )
    elif request.user.vai_tro == VaiTro.CO_VAN_HOC_TAP:
        context['tong_hop'] = tong_hop_trang_chu_co_van(
            getattr(request.user, 'ho_so_co_van', None), request.user,
        )
    return render(request, 'accounts/trang_chu.html', context)


class DanhSachTaiKhoanView(YeuCauVaiTroMixin, ListView):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)
    model = TaiKhoan
    template_name = 'accounts/tai_khoan_danh_sach.html'
    context_object_name = 'danh_sach_tai_khoan'
    paginate_by = 20

    def get_queryset(self):
        queryset = TaiKhoan.objects.all().order_by('ten_dang_nhap')
        tu_khoa = self.request.GET.get('q', '').strip()
        vai_tro = self.request.GET.get('vai_tro', '').strip()
        trang_thai = self.request.GET.get('trang_thai', '').strip()
        if tu_khoa:
            queryset = queryset.filter(ten_dang_nhap__icontains=tu_khoa)
        if vai_tro:
            queryset = queryset.filter(vai_tro=vai_tro)
        if trang_thai in ('1', '0'):
            queryset = queryset.filter(is_active=(trang_thai == '1'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vai_tro_choices'] = VaiTro.choices
        context['q'] = self.request.GET.get('q', '')
        context['vai_tro_loc'] = self.request.GET.get('vai_tro', '')
        context['trang_thai_loc'] = self.request.GET.get('trang_thai', '')
        return context


class TaoTaiKhoanView(YeuCauVaiTroMixin, CreateView):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)
    model = TaiKhoan
    form_class = TaoTaiKhoanForm
    template_name = 'accounts/tai_khoan_form.html'
    success_url = reverse_lazy('accounts:tai_khoan_danh_sach')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã tạo tài khoản "{self.object.ten_dang_nhap}".')
        return response


class CapNhatTaiKhoanView(YeuCauVaiTroMixin, UpdateView):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)
    model = TaiKhoan
    pk_url_kwarg = 'pk'
    form_class = CapNhatTaiKhoanForm
    template_name = 'accounts/tai_khoan_form.html'
    success_url = reverse_lazy('accounts:tai_khoan_danh_sach')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Đã cập nhật tài khoản "{self.object.ten_dang_nhap}".')
        return response


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO)
@require_POST
def khoa_tai_khoan(request, pk):
    tai_khoan = get_object_or_404(TaiKhoan, pk=pk)
    if tai_khoan.pk == request.user.pk:
        messages.error(request, 'Không thể tự khóa tài khoản đang đăng nhập.')
        return redirect('accounts:tai_khoan_danh_sach')
    tai_khoan.is_active = False
    tai_khoan.save(update_fields=['is_active'])
    messages.success(request, f'Đã khóa tài khoản "{tai_khoan.ten_dang_nhap}".')
    return redirect('accounts:tai_khoan_danh_sach')


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO)
@require_POST
def mo_khoa_tai_khoan(request, pk):
    tai_khoan = get_object_or_404(TaiKhoan, pk=pk)
    tai_khoan.is_active = True
    tai_khoan.save(update_fields=['is_active'])
    messages.success(request, f'Đã mở khóa tài khoản "{tai_khoan.ten_dang_nhap}".')
    return redirect('accounts:tai_khoan_danh_sach')


class XoaTaiKhoanView(YeuCauVaiTroMixin, DeleteView):
    """Xóa tài khoản: chỉ khi chưa gắn hồ sơ sinh viên/giảng viên/cố vấn, chưa gửi hay đọc thông báo nào (các khóa
    ngoại tới tài khoản đều PROTECT) và không phải chính tài khoản đang đăng nhập. Ngược lại thì chặn kèm lý do và
    gợi ý khóa tài khoản."""

    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)
    model = TaiKhoan
    template_name = 'accounts/tai_khoan_xac_nhan_xoa.html'
    success_url = reverse_lazy('accounts:tai_khoan_danh_sach')
    context_object_name = 'tai_khoan'

    @staticmethod
    def _ly_do_khong_xoa_duoc(tai_khoan):
        ly_do = []
        for ten_quan_he, ten in (
            ('ho_so_sinh_vien', 'sinh viên'), ('ho_so_giang_vien', 'giảng viên'), ('ho_so_co_van', 'cố vấn học tập'),
        ):
            if hasattr(tai_khoan, ten_quan_he):
                ly_do.append(f'đang gắn hồ sơ {ten}')
        so_da_gui = tai_khoan.thong_bao_da_gui.count()
        if so_da_gui:
            ly_do.append(f'đã gửi {so_da_gui} thông báo')
        so_da_doc = tai_khoan.thong_bao_da_doc.count()
        if so_da_doc:
            ly_do.append(f'có {so_da_doc} lượt đã đọc thông báo')
        return ly_do

    def get(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            messages.error(request, 'Không thể tự xóa tài khoản đang đăng nhập.')
            return redirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ly_do'] = self._ly_do_khong_xoa_duoc(self.object)
        return context

    def form_valid(self, form):
        tai_khoan = self.object
        if tai_khoan.pk == self.request.user.pk:
            messages.error(self.request, 'Không thể tự xóa tài khoản đang đăng nhập.')
            return redirect(self.success_url)
        ly_do = self._ly_do_khong_xoa_duoc(tai_khoan)
        if ly_do:
            messages.error(
                self.request,
                f'Không thể xóa tài khoản "{tai_khoan.ten_dang_nhap}" vì tài khoản này {", ".join(ly_do)}. '
                'Nếu không còn dùng, hãy khóa tài khoản thay vì xóa.',
            )
            return redirect(self.success_url)
        ten = tai_khoan.ten_dang_nhap
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa tài khoản "{ten}".')
        return response


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO)
@require_POST
def dat_lai_mat_khau(request, pk):
    tai_khoan = get_object_or_404(TaiKhoan, pk=pk)
    if tai_khoan.pk == request.user.pk:
        messages.error(request, 'Không thể tự đặt lại mật khẩu của chính tài khoản đang đăng nhập.')
        return redirect('accounts:tai_khoan_danh_sach')
    mat_khau_tam = tao_mat_khau_tam(tai_khoan)
    tai_khoan.set_password(mat_khau_tam)
    tai_khoan.phai_doi_mat_khau = True
    tai_khoan.save(update_fields=['password', 'phai_doi_mat_khau'])
    # Hiện đúng một lần ngay trong trang kết quả của chính request này — không lưu vào
    # session/CSDL/log ở bất kỳ đâu khác, tải lại trang sẽ không xem lại được mật khẩu này.
    return render(request, 'accounts/dat_lai_mat_khau_ket_qua.html', {
        'tai_khoan': tai_khoan, 'mat_khau_tam': mat_khau_tam,
    })


@login_required
def doi_mat_khau(request):
    if request.method == 'POST':
        form = DoiMatKhauForm(request.POST, tai_khoan=request.user)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['mat_khau_moi'])
            request.user.phai_doi_mat_khau = False
            request.user.save(update_fields=['password', 'phai_doi_mat_khau'])
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Đã đổi mật khẩu thành công.')
            return redirect('accounts:trang_chu')
    else:
        form = DoiMatKhauForm(tai_khoan=request.user)
    return render(request, 'accounts/doi_mat_khau.html', {'form': form})


@login_required
def thong_tin_ca_nhan(request):
    ho_so = (
        getattr(request.user, 'ho_so_sinh_vien', None)
        or getattr(request.user, 'ho_so_giang_vien', None)
        or getattr(request.user, 'ho_so_co_van', None)
    )
    form = None
    if ho_so is not None:
        if request.method == 'POST':
            form = ThongTinLienHeForm(request.POST, ho_so=ho_so)
            if form.is_valid():
                ho_so.email = form.cleaned_data['email']
                ho_so.so_dien_thoai = form.cleaned_data['so_dien_thoai']
                ho_so.save(update_fields=['email', 'so_dien_thoai'])
                messages.success(request, 'Đã cập nhật thông tin liên hệ.')
                return redirect('accounts:thong_tin_ca_nhan')
        else:
            form = ThongTinLienHeForm(initial={'email': ho_so.email, 'so_dien_thoai': ho_so.so_dien_thoai}, ho_so=ho_so)
    return render(request, 'accounts/thong_tin_ca_nhan.html', {'ho_so': ho_so, 'form': form})
