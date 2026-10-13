from django import forms
from django.contrib.auth import get_user_model

from accounts.models import VaiTro

from .models import CoVanHocTap, GiangVien, SinhVien

TaiKhoan = get_user_model()


def _tai_khoan_kha_dung(model, vai_tro, instance=None):
    """Tài khoản đúng vai_tro và chưa gắn hồ sơ nào của model này (trừ hồ sơ đang sửa)."""
    da_gan = model.objects.all()
    if instance is not None and instance.pk:
        da_gan = da_gan.exclude(pk=instance.pk)
    ma_da_gan = da_gan.values_list('ma_tai_khoan', flat=True)
    return TaiKhoan.objects.filter(vai_tro=vai_tro).exclude(pk__in=ma_da_gan).order_by('ten_dang_nhap')


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
