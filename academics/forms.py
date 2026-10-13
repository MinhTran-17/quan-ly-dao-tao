from django import forms

from .models import (
    ChiTietChuongTrinh, ChuongTrinhDaoTao, DieuKienTienQuyet, DotDangKy, HocKy, HocPhan, LopHanhChinh, NganhHoc,
)

_DINH_DANG_NGAY_GIO = '%Y-%m-%dT%H:%M'


class NganhHocForm(forms.ModelForm):
    class Meta:
        model = NganhHoc
        fields = ['ma_nganh', 'ten_nganh']
        labels = {'ma_nganh': 'Mã ngành', 'ten_nganh': 'Tên ngành'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['ma_nganh'].disabled = True


class LopHanhChinhForm(forms.ModelForm):
    class Meta:
        model = LopHanhChinh
        fields = ['ma_lop', 'ten_lop', 'ma_nganh', 'ma_co_van']
        labels = {
            'ma_lop': 'Mã lớp',
            'ten_lop': 'Tên lớp',
            'ma_nganh': 'Ngành',
            'ma_co_van': 'Cố vấn học tập phụ trách',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['ma_lop'].disabled = True


class CapNhatLopHanhChinhForm(forms.ModelForm):
    """Form riêng cho sửa lớp hành chính (khác LopHanhChinhForm dùng khi tạo): thêm việc
    gán chương trình đào tạo, chỉ áp dụng khi sửa theo đúng yêu cầu (không phải khi tạo)."""

    class Meta:
        model = LopHanhChinh
        fields = ['ma_lop', 'ten_lop', 'ma_nganh', 'ma_co_van', 'chuong_trinh_dao_tao']
        labels = {
            'ma_lop': 'Mã lớp',
            'ten_lop': 'Tên lớp',
            'ma_nganh': 'Ngành',
            'ma_co_van': 'Cố vấn học tập phụ trách',
            'chuong_trinh_dao_tao': 'Chương trình đào tạo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ma_lop'].disabled = True
        self.fields['chuong_trinh_dao_tao'].required = False
        self.fields['chuong_trinh_dao_tao'].empty_label = '-- Chưa gán --'
        # Chỉ hiện chương trình cùng ngành với lớp (ngành hiện có khi sửa, hoặc ngành vừa
        # chọn trong dữ liệu gửi lên) — vẫn kiểm tra khớp lại ở clean() vì ngành có thể đổi
        # cùng lúc trong cùng lần submit.
        if self.is_bound:
            ma_nganh_hien_tai = self.data.get(self.add_prefix('ma_nganh'))
        else:
            ma_nganh_hien_tai = self.instance.ma_nganh_id
        self.fields['chuong_trinh_dao_tao'].queryset = (
            ChuongTrinhDaoTao.objects.filter(nganh_id=ma_nganh_hien_tai)
            if ma_nganh_hien_tai else ChuongTrinhDaoTao.objects.none()
        )

    def clean(self):
        cleaned_data = super().clean()
        ma_nganh = cleaned_data.get('ma_nganh')
        chuong_trinh = cleaned_data.get('chuong_trinh_dao_tao')
        if chuong_trinh and ma_nganh and chuong_trinh.nganh_id != ma_nganh.pk:
            self.add_error('chuong_trinh_dao_tao', 'Chương trình đào tạo phải cùng ngành với lớp hành chính.')
        return cleaned_data


class HocPhanForm(forms.ModelForm):
    so_tin_chi = forms.IntegerField(label='Số tín chỉ', min_value=1)

    class Meta:
        model = HocPhan
        fields = ['ma_hoc_phan', 'ten_hoc_phan', 'so_tin_chi']
        labels = {'ma_hoc_phan': 'Mã học phần', 'ten_hoc_phan': 'Tên học phần'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['ma_hoc_phan'].disabled = True


class DieuKienTienQuyetForm(forms.ModelForm):
    class Meta:
        model = DieuKienTienQuyet
        fields = ['ma_hoc_phan', 'ma_hoc_phan_tien_quyet']
        labels = {'ma_hoc_phan': 'Học phần', 'ma_hoc_phan_tien_quyet': 'Học phần tiên quyết'}


class HocKyForm(forms.ModelForm):
    hoc_ky = forms.IntegerField(label='Học kỳ', min_value=1)

    class Meta:
        model = HocKy
        fields = ['hoc_ky', 'nam_hoc', 'ngay_bat_dau', 'ngay_ket_thuc']
        labels = {
            'nam_hoc': 'Năm học',
            'ngay_bat_dau': 'Ngày bắt đầu',
            'ngay_ket_thuc': 'Ngày kết thúc',
        }
        help_texts = {
            'nam_hoc': 'Định dạng YYYY-YYYY, ví dụ 2025-2026.',
        }
        widgets = {
            'ngay_bat_dau': forms.DateInput(attrs={'type': 'date'}),
            'ngay_ket_thuc': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        bat_dau = cleaned_data.get('ngay_bat_dau')
        ket_thuc = cleaned_data.get('ngay_ket_thuc')
        if bat_dau and ket_thuc and ket_thuc <= bat_dau:
            self.add_error('ngay_ket_thuc', 'Ngày kết thúc phải sau ngày bắt đầu.')
        return cleaned_data


class DotDangKyForm(forms.ModelForm):
    # Khai báo tường minh (thay vì để ModelForm tự sinh) để chỉ định input_formats/format
    # khớp với những gì trình duyệt gửi lên cho <input type="datetime-local">
    # ("YYYY-MM-DDTHH:MM"), vì định dạng mặc định của Django là có dấu cách, không phải "T".
    ngay_mo = forms.DateTimeField(
        label='Ngày mở', input_formats=[_DINH_DANG_NGAY_GIO],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=_DINH_DANG_NGAY_GIO),
    )
    ngay_dong = forms.DateTimeField(
        label='Ngày đóng', input_formats=[_DINH_DANG_NGAY_GIO],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=_DINH_DANG_NGAY_GIO),
    )

    class Meta:
        model = DotDangKy
        fields = ['hoc_ky', 'ngay_mo', 'ngay_dong']
        labels = {'hoc_ky': 'Học kỳ'}

    def clean(self):
        cleaned_data = super().clean()
        hoc_ky = cleaned_data.get('hoc_ky')
        ngay_mo = cleaned_data.get('ngay_mo')
        ngay_dong = cleaned_data.get('ngay_dong')
        if hoc_ky and ngay_mo and ngay_dong:
            if ngay_dong <= ngay_mo:
                self.add_error('ngay_dong', 'Ngày đóng phải sau ngày mở.')
            else:
                # Không cho hai đợt cùng học kỳ chồng lấp thời gian — kiểm tra ở đây vì
                # MySQL không có UNIQUE/EXCLUDE constraint theo khoảng (xem academics/models.py).
                chong_lap = DotDangKy.objects.filter(
                    hoc_ky=hoc_ky, ngay_mo__lt=ngay_dong, ngay_dong__gt=ngay_mo,
                )
                if self.instance.pk:
                    chong_lap = chong_lap.exclude(pk=self.instance.pk)
                if chong_lap.exists():
                    raise forms.ValidationError(
                        'Đợt đăng ký này chồng lấp thời gian với một đợt khác đã có của cùng học kỳ.'
                    )
        return cleaned_data


class ChuongTrinhDaoTaoForm(forms.ModelForm):
    class Meta:
        model = ChuongTrinhDaoTao
        fields = ['nganh', 'ten_chuong_trinh', 'khoa_hoc']
        labels = {'nganh': 'Ngành', 'ten_chuong_trinh': 'Tên chương trình', 'khoa_hoc': 'Khóa học'}
        help_texts = {'khoa_hoc': 'Ví dụ: Khóa 1.'}


class ChiTietChuongTrinhForm(forms.ModelForm):
    hoc_ky_du_kien = forms.IntegerField(label='Học kỳ dự kiến', min_value=1, max_value=8)

    class Meta:
        model = ChiTietChuongTrinh
        fields = ['hoc_phan', 'hoc_ky_du_kien', 'bat_buoc']
        labels = {'hoc_phan': 'Học phần', 'bat_buoc': 'Bắt buộc'}
        widgets = {'hoc_phan': forms.HiddenInput()}
