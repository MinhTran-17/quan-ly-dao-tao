from django import forms

from .models import TaiLieuQuyChe, validate_tai_lieu_file


class TaiLieuQuyCheTaoForm(forms.ModelForm):
    duong_dan_file = forms.FileField(label='Tệp quy chế (PDF hoặc DOCX)', validators=[validate_tai_lieu_file])

    class Meta:
        model = TaiLieuQuyChe
        fields = ['ten_tai_lieu', 'duong_dan_file']
        labels = {'ten_tai_lieu': 'Tên tài liệu'}


class TaiLieuQuyCheSuaForm(forms.ModelForm):
    duong_dan_file = forms.FileField(
        label='Thay tệp mới (để trống nếu giữ tệp cũ)', required=False, validators=[validate_tai_lieu_file],
    )

    class Meta:
        model = TaiLieuQuyChe
        fields = ['ten_tai_lieu', 'duong_dan_file']
        labels = {'ten_tai_lieu': 'Tên tài liệu'}
