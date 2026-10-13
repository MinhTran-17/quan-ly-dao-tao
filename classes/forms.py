from django import forms

from academics.models import HocKy

from .models import LichHoc, LichThi, LopHocPhan


class LopHocPhanForm(forms.ModelForm):
    si_so_toi_da = forms.IntegerField(label='Sĩ số tối đa', min_value=1)
    # Không phải cột của LopHocPhan (xem academics.HocKy) — chỉ dùng để chọn một mục
    # trong danh mục học kỳ rồi sao chép hoc_ky/nam_hoc của mục đó vào bản ghi, xem save().
    hoc_ky_chon = forms.ModelChoiceField(
        label='Học kỳ',
        queryset=HocKy.objects.all(),
        empty_label='-- Chọn học kỳ --',
        help_text='Lấy từ danh mục học kỳ (mục Học vụ). Chưa thấy học kỳ cần chọn thì tạo '
                   'thêm trong danh mục trước.',
    )

    class Meta:
        model = LopHocPhan
        fields = ['ma_lop_hoc_phan', 'si_so_toi_da', 'ma_hoc_phan', 'ma_giang_vien']
        labels = {
            'ma_lop_hoc_phan': 'Mã lớp học phần',
            'ma_hoc_phan': 'Học phần',
            'ma_giang_vien': 'Giảng viên phụ trách',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(['ma_lop_hoc_phan', 'hoc_ky_chon', 'si_so_toi_da', 'ma_hoc_phan', 'ma_giang_vien'])
        if self.instance.pk:
            self.fields['ma_lop_hoc_phan'].disabled = True
            hoc_ky_hien_tai = HocKy.objects.filter(
                hoc_ky=self.instance.hoc_ky, nam_hoc=self.instance.nam_hoc,
            ).first()
            if hoc_ky_hien_tai:
                self.initial['hoc_ky_chon'] = hoc_ky_hien_tai.pk

    def save(self, commit=True):
        lop = super().save(commit=False)
        hoc_ky_chon = self.cleaned_data['hoc_ky_chon']
        lop.hoc_ky = str(hoc_ky_chon.hoc_ky)
        lop.nam_hoc = hoc_ky_chon.nam_hoc
        if commit:
            lop.save()
        return lop


class LichHocForm(forms.ModelForm):
    thu = forms.IntegerField(label='Thứ', min_value=2, max_value=8, help_text='2 = Thứ Hai, ... 8 = Chủ nhật')
    tiet_bat_dau = forms.IntegerField(label='Tiết bắt đầu', min_value=1)
    so_tiet = forms.IntegerField(label='Số tiết', min_value=1)

    class Meta:
        model = LichHoc
        fields = ['ma_lop_hoc_phan', 'thu', 'tiet_bat_dau', 'so_tiet', 'phong_hoc']
        labels = {
            'ma_lop_hoc_phan': 'Lớp học phần',
            'phong_hoc': 'Phòng học',
        }


class LichThiForm(forms.ModelForm):
    thoi_luong_phut = forms.IntegerField(label='Thời lượng (phút)', min_value=1)

    class Meta:
        model = LichThi
        fields = ['lop_hoc_phan', 'ngay_thi', 'gio_bat_dau', 'thoi_luong_phut', 'phong_thi']
        labels = {
            'lop_hoc_phan': 'Lớp học phần',
            'ngay_thi': 'Ngày thi',
            'gio_bat_dau': 'Giờ bắt đầu',
            'phong_thi': 'Phòng thi',
        }
        widgets = {
            'ngay_thi': forms.DateInput(attrs={'type': 'date'}),
            'gio_bat_dau': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Không cho đổi lớp học phần khi sửa — chỉ đổi ngày giờ/phòng thi.
            self.fields['lop_hoc_phan'].disabled = True
        else:
            # Chỉ hiện lớp chưa có lịch thi khi tạo mới (lich_thi là OneToOneField).
            self.fields['lop_hoc_phan'].queryset = LopHocPhan.objects.filter(lich_thi__isnull=True)
