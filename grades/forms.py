from django import forms

from .models import Diem


class DiemForm(forms.ModelForm):
    diem_qua_trinh = forms.DecimalField(
        label='Điểm quá trình', max_digits=4, decimal_places=2, min_value=0, max_value=10, required=False,
    )
    diem_thi = forms.DecimalField(
        label='Điểm thi', max_digits=4, decimal_places=2, min_value=0, max_value=10, required=False,
    )

    class Meta:
        model = Diem
        fields = ['diem_qua_trinh', 'diem_thi']

    def save(self, commit=True):
        diem = super().save(commit=False)
        # Sửa điểm sau khi đã công bố phải công bố lại — tự ẩn khỏi sinh viên cho tới lúc
        # đó. changed_data rỗng (bấm Lưu mà không đổi gì) thì giữ nguyên trạng thái công bố.
        if 'diem_qua_trinh' in self.changed_data or 'diem_thi' in self.changed_data:
            diem.da_cong_bo = False
        if commit:
            diem.save()
        return diem
