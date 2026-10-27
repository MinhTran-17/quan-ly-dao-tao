import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import TaiKhoan

# Thông điệp tiếng Việt cho các validator mật khẩu mặc định của Django (bản dịch "vi" của Django không đủ, có thông
# báo còn bằng tiếng Anh). Khóa là mã lỗi của validator; mã lạ thì giữ nguyên thông điệp gốc.
THONG_DIEP_MAT_KHAU = {
    'password_too_short': 'Mật khẩu quá ngắn, cần có ít nhất {min_length} ký tự.',
    'password_too_common': 'Mật khẩu này quá phổ biến, hãy chọn mật khẩu khó đoán hơn.',
    'password_entirely_numeric': 'Mật khẩu không được chỉ gồm chữ số.',
    'password_too_similar': 'Mật khẩu quá giống với thông tin tài khoản (tên đăng nhập).',
}


def kiem_tra_mat_khau(mat_khau, user=None):
    """validate_password của Django nhưng báo lỗi bằng tiếng Việt (cùng quy tắc, cùng AUTH_PASSWORD_VALIDATORS)."""
    try:
        validate_password(mat_khau, user=user)
    except ValidationError as loi:
        raise ValidationError([
            ValidationError(THONG_DIEP_MAT_KHAU[e.code].format(**(e.params or {})), code=e.code)
            if e.code in THONG_DIEP_MAT_KHAU else e
            for e in loi.error_list
        ])


validate_so_dien_thoai = RegexValidator(
    regex=r'^0\d{9}$',
    message='Số điện thoại phải gồm 10 chữ số và bắt đầu bằng số 0.',
)

# Tên đăng nhập: chữ cái không dấu, chữ số, dấu gạch dưới (chặn "....", "///", khoảng trắng, chữ có dấu).
# Áp dụng khi tạo/đổi tên ở form và khi nhập sinh viên từ Excel; tài khoản cũ sai quy tắc vẫn đăng nhập được
# (liệt kê bằng lệnh python manage.py kiem_tra_ten_dang_nhap).
MAU_TEN_DANG_NHAP = re.compile(r'[A-Za-z0-9_]+')


def ten_dang_nhap_hop_le(ten):
    return isinstance(ten, str) and MAU_TEN_DANG_NHAP.fullmatch(ten) is not None


def thong_bao_ten_dang_nhap_khong_hop_le(ten):
    return (f'Tên đăng nhập "{ten}" không hợp lệ: chỉ được dùng chữ cái không dấu, chữ số và dấu gạch dưới (_), '
            'không có khoảng trắng, dấu chấm hay ký tự đặc biệt.')


def _kiem_tra_ten_dang_nhap(form):
    ten = (form.cleaned_data.get('ten_dang_nhap') or '').strip()
    # Khi sửa tài khoản mà giữ nguyên tên cũ (kể cả tên cũ sai quy tắc) thì không chặn việc sửa trường khác.
    if form.instance.pk and ten == form.instance.ten_dang_nhap:
        return ten
    if not ten_dang_nhap_hop_le(ten):
        raise forms.ValidationError(thong_bao_ten_dang_nhap_khong_hop_le(ten))
    return ten


class DangNhapForm(AuthenticationForm):
    username = forms.CharField(
        label='Tên đăng nhập',
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}),
    )
    password = forms.CharField(
        label='Mật khẩu',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    error_messages = {
        'invalid_login': 'Tên đăng nhập hoặc mật khẩu không đúng.',
        'inactive': 'Tài khoản đã bị khóa.',
    }


class TaoTaiKhoanForm(forms.ModelForm):
    mat_khau = forms.CharField(label='Mật khẩu', widget=forms.PasswordInput)

    class Meta:
        model = TaiKhoan
        fields = ['ten_dang_nhap', 'vai_tro', 'is_active']
        labels = {
            'ten_dang_nhap': 'Tên đăng nhập',
            'vai_tro': 'Vai trò',
            'is_active': 'Kích hoạt tài khoản',
        }
        error_messages = {'ten_dang_nhap': {'unique': 'Tên đăng nhập này đã tồn tại.'}}

    def clean_ten_dang_nhap(self):
        return _kiem_tra_ten_dang_nhap(self)

    def clean_mat_khau(self):
        mat_khau = self.cleaned_data['mat_khau']
        kiem_tra_mat_khau(mat_khau)
        return mat_khau

    def save(self, commit=True):
        tai_khoan = super().save(commit=False)
        tai_khoan.set_password(self.cleaned_data['mat_khau'])
        if commit:
            tai_khoan.save()
        return tai_khoan


class CapNhatTaiKhoanForm(forms.ModelForm):
    class Meta:
        model = TaiKhoan
        fields = ['ten_dang_nhap', 'vai_tro', 'is_active']
        labels = {
            'ten_dang_nhap': 'Tên đăng nhập',
            'vai_tro': 'Vai trò',
            'is_active': 'Kích hoạt tài khoản',
        }
        error_messages = {'ten_dang_nhap': {'unique': 'Tên đăng nhập này đã tồn tại.'}}

    def clean_ten_dang_nhap(self):
        return _kiem_tra_ten_dang_nhap(self)

    def clean_vai_tro(self):
        vai_tro_moi = self.cleaned_data['vai_tro']
        # self.instance.vai_tro ở đây vẫn là giá trị cũ trong CSDL, vì construct_instance()
        # (gán cleaned_data vào instance) chạy sau clean_<field> trong full_clean().
        if self.instance.pk and vai_tro_moi != self.instance.vai_tro:
            co_ho_so = any(
                getattr(self.instance, ten_thuoc_tinh, None) is not None
                for ten_thuoc_tinh in ('ho_so_sinh_vien', 'ho_so_giang_vien', 'ho_so_co_van')
            )
            if co_ho_so:
                raise forms.ValidationError(
                    'Không thể đổi vai trò vì tài khoản đã gắn hồ sơ '
                    '(sinh viên/giảng viên/cố vấn học tập).'
                )
        return vai_tro_moi


class ThongTinLienHeForm(forms.Form):
    """Form tự phục vụ để sinh viên/giảng viên/cố vấn học tập tự cập nhật email và số điện
    thoại của hồ sơ mình (people.SinhVien/GiangVien/CoVanHocTap đều dùng CharField không kiểm
    tra định dạng ở tầng model — kiểm tra định dạng thực hiện ở đây, không sửa 3 model đó)."""

    email = forms.EmailField(label='Email', max_length=100)
    so_dien_thoai = forms.CharField(label='Số điện thoại', max_length=15, validators=[validate_so_dien_thoai])

    def __init__(self, *args, ho_so, **kwargs):
        self.ho_so = ho_so
        super().__init__(*args, **kwargs)

    def clean(self):
        # Không trùng email/số điện thoại của hồ sơ khác; thông báo chung, không nêu hồ sơ nào (tránh lộ thông tin người khác).
        from people.lien_he import kiem_tra_lien_he
        cleaned_data = super().clean()
        loi = kiem_tra_lien_he(cleaned_data.get('email'), cleaned_data.get('so_dien_thoai'), self.ho_so, chi_tiet=False)
        for truong, thong_bao in loi.items():
            self.add_error(truong, thong_bao)
        return cleaned_data


class DoiMatKhauForm(forms.Form):
    mat_khau_cu = forms.CharField(label='Mật khẩu hiện tại', widget=forms.PasswordInput)
    mat_khau_moi = forms.CharField(label='Mật khẩu mới', widget=forms.PasswordInput)
    mat_khau_moi_xac_nhan = forms.CharField(label='Xác nhận mật khẩu mới', widget=forms.PasswordInput)

    def __init__(self, *args, tai_khoan, **kwargs):
        self.tai_khoan = tai_khoan
        super().__init__(*args, **kwargs)

    def clean_mat_khau_cu(self):
        mat_khau_cu = self.cleaned_data['mat_khau_cu']
        if not self.tai_khoan.check_password(mat_khau_cu):
            raise forms.ValidationError('Mật khẩu hiện tại không đúng.')
        return mat_khau_cu

    def clean(self):
        cleaned_data = super().clean()
        moi = cleaned_data.get('mat_khau_moi')
        xac_nhan = cleaned_data.get('mat_khau_moi_xac_nhan')
        if moi and xac_nhan and moi != xac_nhan:
            self.add_error('mat_khau_moi_xac_nhan', 'Xác nhận mật khẩu mới không khớp với mật khẩu mới.')
        # Kể cả lần đổi bắt buộc sau khi được đặt lại: không giữ nguyên mật khẩu tạm.
        if moi and self.tai_khoan.check_password(moi):
            self.add_error('mat_khau_moi', 'Mật khẩu mới không được trùng mật khẩu hiện tại.')
        elif moi:
            kiem_tra_mat_khau(moi, user=self.tai_khoan)
        return cleaned_data
