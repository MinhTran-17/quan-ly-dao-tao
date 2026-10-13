from django import forms

from academics.models import LopHanhChinh
from classes.models import LopHocPhan

from .models import DoiTuongThongBao, ThongBao

_DOI_TUONG_THEO_VAI_TRO = [
    (DoiTuongThongBao.TAT_CA, 'Tất cả'),
    (DoiTuongThongBao.PHONG_DAO_TAO, 'Phòng Đào tạo'),
    (DoiTuongThongBao.GIANG_VIEN, 'Giảng viên'),
    (DoiTuongThongBao.SINH_VIEN, 'Sinh viên'),
    (DoiTuongThongBao.CO_VAN_HOC_TAP, 'Cố vấn học tập'),
]


class GuiThongBaoPhongDaoTaoForm(forms.ModelForm):
    doi_tuong = forms.ChoiceField(label='Gửi cho', choices=_DOI_TUONG_THEO_VAI_TRO)

    class Meta:
        model = ThongBao
        fields = ['tieu_de', 'noi_dung', 'doi_tuong']
        labels = {'tieu_de': 'Tiêu đề', 'noi_dung': 'Nội dung'}
        widgets = {'noi_dung': forms.Textarea(attrs={'rows': 5})}


class GuiThongBaoGiangVienForm(forms.ModelForm):
    lop_hoc_phan = forms.ModelChoiceField(label='Lớp học phần', queryset=LopHocPhan.objects.none())

    class Meta:
        model = ThongBao
        fields = ['lop_hoc_phan', 'tieu_de', 'noi_dung']
        labels = {'tieu_de': 'Tiêu đề', 'noi_dung': 'Nội dung'}
        widgets = {'noi_dung': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, giang_vien=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = LopHocPhan.objects.none() if giang_vien is None else (
            LopHocPhan.objects.filter(ma_giang_vien=giang_vien).order_by('-nam_hoc', 'hoc_ky')
        )
        self.fields['lop_hoc_phan'].queryset = queryset

    def save(self, commit=True):
        thong_bao = super().save(commit=False)
        thong_bao.doi_tuong = DoiTuongThongBao.LOP_HOC_PHAN
        if commit:
            thong_bao.save()
        return thong_bao


class GuiThongBaoCoVanForm(forms.ModelForm):
    lop_hanh_chinh = forms.ModelChoiceField(label='Lớp hành chính', queryset=LopHanhChinh.objects.none())

    class Meta:
        model = ThongBao
        fields = ['lop_hanh_chinh', 'tieu_de', 'noi_dung']
        labels = {'tieu_de': 'Tiêu đề', 'noi_dung': 'Nội dung'}
        widgets = {'noi_dung': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, co_van=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = LopHanhChinh.objects.none() if co_van is None else (
            LopHanhChinh.objects.filter(ma_co_van=co_van).order_by('ma_lop')
        )
        self.fields['lop_hanh_chinh'].queryset = queryset

    def save(self, commit=True):
        thong_bao = super().save(commit=False)
        thong_bao.doi_tuong = DoiTuongThongBao.LOP_HANH_CHINH
        if commit:
            thong_bao.save()
        return thong_bao
