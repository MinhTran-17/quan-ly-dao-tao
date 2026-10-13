from django import forms

from classes.models import LopHocPhan


class TuVanForm(forms.Form):
    hoc_ky = forms.ChoiceField(label='Học kỳ')
    nam_hoc = forms.ChoiceField(label='Năm học')
    ghi_chu = forms.CharField(
        label='Ghi chú (tuỳ chọn, tối đa 300 ký tự)',
        max_length=300,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 300}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoc_ky_values = LopHocPhan.objects.order_by('hoc_ky').values_list('hoc_ky', flat=True).distinct()
        nam_hoc_values = LopHocPhan.objects.order_by('-nam_hoc').values_list('nam_hoc', flat=True).distinct()
        self.fields['hoc_ky'].choices = [(gia_tri, gia_tri) for gia_tri in hoc_ky_values]
        self.fields['nam_hoc'].choices = [(gia_tri, gia_tri) for gia_tri in nam_hoc_values]
