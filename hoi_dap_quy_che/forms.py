from django import forms


class CauHoiForm(forms.Form):
    cau_hoi = forms.CharField(
        label='Câu hỏi về quy chế đào tạo',
        max_length=500,
        widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 500}),
    )
