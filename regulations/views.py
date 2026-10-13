import os

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin, yeu_cau_vai_tro
from hoi_dap_quy_che.trich_xuat import trich_van_ban

from .forms import TaiLieuQuyCheSuaForm, TaiLieuQuyCheTaoForm
from .models import TaiLieuQuyChe


def _canh_bao_neu_khong_trich_duoc_chu(request, tai_lieu):
    """Không chặn việc tải lên/cập nhật — chỉ báo cho Phòng Đào tạo biết để họ có thể
    thay bằng bản khác nếu cần (ví dụ PDF ảnh quét không có lớp chữ để trích)."""
    van_ban = trich_van_ban(tai_lieu.duong_dan_file)
    if not van_ban.strip():
        messages.warning(
            request,
            f'Không trích được chữ từ tệp của tài liệu "{tai_lieu.ten_tai_lieu}" (có thể là bản quét '
            'ảnh không có lớp chữ). Chatbot hỏi đáp quy chế sẽ không dùng được nội dung tài liệu này '
            'cho tới khi được thay bằng bản có thể trích chữ.',
        )


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class DanhSachTaiLieuView(QuanLyPhongDaoTaoMixin, ListView):
    model = TaiLieuQuyChe
    template_name = 'regulations/danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        queryset = TaiLieuQuyChe.objects.order_by('-ngay_cap_nhat')
        tu_khoa = self.request.GET.get('q', '').strip()
        if tu_khoa:
            queryset = queryset.filter(ten_tai_lieu__icontains=tu_khoa)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class TaiLieuQuyCheTaoView(QuanLyPhongDaoTaoMixin, CreateView):
    model = TaiLieuQuyChe
    form_class = TaiLieuQuyCheTaoForm
    template_name = 'regulations/form_chung.html'
    success_url = reverse_lazy('regulations:danh_sach')
    extra_context = {'tieu_de': 'Tải lên tài liệu quy chế', 'url_danh_sach': 'regulations:danh_sach'}

    def form_valid(self, form):
        tai_lieu = form.save(commit=False)
        hom_nay = timezone.localdate()
        tai_lieu.ngay_tai_len = hom_nay
        tai_lieu.ngay_cap_nhat = hom_nay
        tai_lieu.save()
        self.object = tai_lieu
        _canh_bao_neu_khong_trich_duoc_chu(self.request, tai_lieu)
        messages.success(self.request, f'Đã tải lên tài liệu "{tai_lieu.ten_tai_lieu}".')
        return redirect(self.success_url)


class TaiLieuQuyCheSuaView(QuanLyPhongDaoTaoMixin, UpdateView):
    model = TaiLieuQuyChe
    form_class = TaiLieuQuyCheSuaForm
    template_name = 'regulations/form_chung.html'
    success_url = reverse_lazy('regulations:danh_sach')
    extra_context = {'tieu_de': 'Cập nhật tài liệu quy chế', 'url_danh_sach': 'regulations:danh_sach'}

    def form_valid(self, form):
        tai_lieu = form.save(commit=False)
        tep_moi = form.cleaned_data.get('duong_dan_file')
        tep_da_doi = False
        if tep_moi:
            # Lấy lại tệp cũ từ CSDL (self.object trong bộ nhớ đã bị form gán tệp mới),
            # chỉ xóa khi thật sự là tệp khác (không phải tệp cũ được giữ nguyên).
            tep_cu = TaiLieuQuyChe.objects.get(pk=tai_lieu.pk).duong_dan_file
            if tep_cu and tep_cu.name != tep_moi.name:
                tep_cu.delete(save=False)
                tep_da_doi = True
        tai_lieu.ngay_cap_nhat = timezone.localdate()
        tai_lieu.save()
        self.object = tai_lieu
        if tep_da_doi:
            _canh_bao_neu_khong_trich_duoc_chu(self.request, tai_lieu)
        messages.success(self.request, f'Đã cập nhật tài liệu "{tai_lieu.ten_tai_lieu}".')
        return redirect(self.success_url)


class XoaTaiLieuView(QuanLyPhongDaoTaoMixin, DeleteView):
    model = TaiLieuQuyChe
    template_name = 'regulations/xac_nhan_xoa.html'
    success_url = reverse_lazy('regulations:danh_sach')
    context_object_name = 'tai_lieu'

    def form_valid(self, form):
        tai_lieu = self.object
        ten = tai_lieu.ten_tai_lieu
        if tai_lieu.duong_dan_file:
            tai_lieu.duong_dan_file.delete(save=False)
        response = super().form_valid(form)
        messages.success(self.request, f'Đã xóa tài liệu "{ten}".')
        return response


@yeu_cau_vai_tro(VaiTro.PHONG_DAO_TAO)
def tai_ve_view(request, pk):
    tai_lieu = get_object_or_404(TaiLieuQuyChe, pk=pk)
    if not tai_lieu.duong_dan_file or not tai_lieu.duong_dan_file.storage.exists(tai_lieu.duong_dan_file.name):
        raise Http404('Tệp không tồn tại trên máy chủ.')
    duoi = os.path.splitext(tai_lieu.duong_dan_file.name)[1]
    return FileResponse(
        tai_lieu.duong_dan_file.open('rb'),
        as_attachment=True,
        filename=f'{tai_lieu.ten_tai_lieu}{duoi}',
    )
