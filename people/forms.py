from django import forms
from django.contrib.auth import get_user_model

from accounts.models import VaiTro

from .lien_he import kiem_tra_lien_he
from .ma_ho_so import ma_hop_le, thong_bao_ma_khong_hop_le
from .models import CoVanHocTap, GiangVien, SinhVien

TaiKhoan = get_user_model()


def _tai_khoan_kha_dung(model, vai_tro, instance=None):
    """Tài khoản đúng vai_tro và chưa gắn hồ sơ nào của model này (trừ hồ sơ đang sửa)."""
    da_gan = model.objects.all()
    if instance is not None and instance.pk:
        da_gan = da_gan.exclude(pk=instance.pk)
    ma_da_gan = da_gan.values_list('ma_tai_khoan', flat=True)
    return TaiKhoan.objects.filter(vai_tro=vai_tro).exclude(pk__in=ma_da_gan).order_by('ten_dang_nhap')


def _kiem_tra_ma_ho_so(form, truong, nhan):
    """Mã hồ sơ chỉ gồm chữ cái không dấu và chữ số. Khi sửa hồ sơ, mã bị khóa (disabled) nên giữ nguyên
    giá trị cũ, kể cả dữ liệu cũ không hợp lệ — để vẫn sửa được các trường khác."""
    ma = form.cleaned_data.get(truong)
    if form.instance.pk:
        return ma
    ma = (ma or '').strip()
    if not ma_hop_le(ma):
        raise forms.ValidationError(thong_bao_ma_khong_hop_le(nhan, ma))
    return ma


def _kiem_tra_trung_lien_he(form):
    """Email/số điện thoại không trùng với hồ sơ sinh viên, giảng viên, cố vấn khác (xem people/lien_he.py)."""
    ho_so_dang_sua = form.instance if form.instance.pk else None
    loi = kiem_tra_lien_he(form.cleaned_data.get('email'), form.cleaned_data.get('so_dien_thoai'), ho_so_dang_sua)
    for truong, thong_bao in loi.items():
        form.add_error(truong, thong_bao)


class SinhVienForm(forms.ModelForm):
    class Meta:
        model = SinhVien
        fields = ['ma_sinh_vien', 'ho_ten', 'ngay_sinh', 'email', 'so_dien_thoai', 'ma_lop', 'ma_tai_khoan']
        labels = {
            'ma_sinh_vien': 'Mã sinh viên',
            'ho_ten': 'Họ tên',
            'ngay_sinh': 'Ngày sinh',
            'email': 'Email',
            'so_dien_thoai': 'Số điện thoại',
            'ma_lop': 'Lớp hành chính',
            'ma_tai_khoan': 'Tài khoản đăng nhập',
        }
        widgets = {'ngay_sinh': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ma_tai_khoan'].queryset = _tai_khoan_kha_dung(SinhVien, VaiTro.SINH_VIEN, self.instance)
        if self.instance.pk:
            self.fields['ma_sinh_vien'].disabled = True

    def clean_ma_sinh_vien(self):
        return _kiem_tra_ma_ho_so(self, 'ma_sinh_vien', 'Mã sinh viên')

    def clean(self):
        cleaned_data = super().clean()
        _kiem_tra_trung_lien_he(self)
        return cleaned_data


class GiangVienForm(forms.ModelForm):
    class Meta:
        model = GiangVien
        fields = ['ma_giang_vien', 'ho_ten', 'email', 'so_dien_thoai', 'ma_tai_khoan']
        labels = {
            'ma_giang_vien': 'Mã giảng viên',
            'ho_ten': 'Họ tên',
            'email': 'Email',
            'so_dien_thoai': 'Số điện thoại',
            'ma_tai_khoan': 'Tài khoản đăng nhập',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ma_tai_khoan'].queryset = _tai_khoan_kha_dung(GiangVien, VaiTro.GIANG_VIEN, self.instance)
        if self.instance.pk:
            self.fields['ma_giang_vien'].disabled = True

    def clean_ma_giang_vien(self):
        return _kiem_tra_ma_ho_so(self, 'ma_giang_vien', 'Mã giảng viên')

    def clean(self):
        cleaned_data = super().clean()
        _kiem_tra_trung_lien_he(self)
        return cleaned_data


class NhapSinhVienExcelForm(forms.Form):
    file_excel = forms.FileField(label='Tệp Excel (.xlsx)')

    def clean_file_excel(self):
        file_excel = self.cleaned_data['file_excel']
        if not file_excel.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('Chỉ chấp nhận tệp .xlsx.')
        return file_excel


class CoVanHocTapForm(forms.ModelForm):
    class Meta:
        model = CoVanHocTap
        fields = ['ma_co_van', 'ho_ten', 'email', 'so_dien_thoai', 'ma_tai_khoan']
        labels = {
            'ma_co_van': 'Mã cố vấn',
            'ho_ten': 'Họ tên',
            'email': 'Email',
            'so_dien_thoai': 'Số điện thoại',
            'ma_tai_khoan': 'Tài khoản đăng nhập',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ma_tai_khoan'].queryset = _tai_khoan_kha_dung(CoVanHocTap, VaiTro.CO_VAN_HOC_TAP, self.instance)
        if self.instance.pk:
            self.fields['ma_co_van'].disabled = True

    def clean_ma_co_van(self):
        return _kiem_tra_ma_ho_so(self, 'ma_co_van', 'Mã cố vấn')

    def clean(self):
        cleaned_data = super().clean()
        _kiem_tra_trung_lien_he(self)
        return cleaned_data
