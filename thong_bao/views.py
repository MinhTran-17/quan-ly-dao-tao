from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, ListView

from accounts.models import VaiTro
from accounts.permissions import YeuCauVaiTroMixin

from .forms import GuiThongBaoCoVanForm, GuiThongBaoGiangVienForm, GuiThongBaoPhongDaoTaoForm
from .models import DaDocThongBao, ThongBao
from .services import danh_dau_da_doc, thong_bao_lien_quan


class QuanLyPhongDaoTaoMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.PHONG_DAO_TAO,)


class GiangVienMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.GIANG_VIEN,)


class CoVanMixin(YeuCauVaiTroMixin):
    vai_tro_cho_phep = (VaiTro.CO_VAN_HOC_TAP,)


class GuiThongBaoPhongDaoTaoView(QuanLyPhongDaoTaoMixin, CreateView):
    model = ThongBao
    form_class = GuiThongBaoPhongDaoTaoForm
    template_name = 'thong_bao/gui_thong_bao.html'
    extra_context = {'tieu_de': 'Gửi thông báo', 'mo_ta': 'Gửi cho tất cả người dùng hoặc theo vai trò.'}

    def get_success_url(self):
        return self.request.path

    def form_valid(self, form):
        form.instance.nguoi_gui = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Đã gửi thông báo.')
        return response


class DanhSachThongBaoDaGuiView(QuanLyPhongDaoTaoMixin, ListView):
    """Các thông báo do Phòng Đào tạo đã gửi (mọi tài khoản Phòng Đào tạo), mới nhất trước. Khác trang "Thông báo"
    (danh_sach) vốn chỉ liệt kê thông báo LIÊN QUAN tới người đang xem (thường là thông báo gửi cho họ)."""

    template_name = 'thong_bao/da_gui.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        return (
            ThongBao.objects.filter(nguoi_gui__vai_tro=VaiTro.PHONG_DAO_TAO)
            .select_related('nguoi_gui', 'lop_hoc_phan', 'lop_hanh_chinh').order_by('-thoi_gian_gui', '-pk')
        )


class GuiThongBaoGiangVienView(GiangVienMixin, View):
    template_name = 'thong_bao/gui_thong_bao.html'

    def _giang_vien(self, request):
        return getattr(request.user, 'ho_so_giang_vien', None)

    def get(self, request):
        form = GuiThongBaoGiangVienForm(giang_vien=self._giang_vien(request))
        return render(request, self.template_name, {
            'form': form, 'tieu_de': 'Gửi thông báo lớp học phần',
            'mo_ta': 'Gửi cho sinh viên đã đăng ký còn hiệu lực của một lớp học phần bạn phụ trách.',
        })

    def post(self, request):
        giang_vien = self._giang_vien(request)
        form = GuiThongBaoGiangVienForm(request.POST, giang_vien=giang_vien)
        if giang_vien is not None and form.is_valid():
            thong_bao = form.save(commit=False)
            thong_bao.nguoi_gui = request.user
            thong_bao.save()
            messages.success(request, 'Đã gửi thông báo.')
            return redirect('thong_bao:gui_giang_vien')
        return render(request, self.template_name, {
            'form': form, 'tieu_de': 'Gửi thông báo lớp học phần',
            'mo_ta': 'Gửi cho sinh viên đã đăng ký còn hiệu lực của một lớp học phần bạn phụ trách.',
        })


class GuiThongBaoCoVanView(CoVanMixin, View):
    template_name = 'thong_bao/gui_thong_bao.html'

    def _co_van(self, request):
        return getattr(request.user, 'ho_so_co_van', None)

    def get(self, request):
        form = GuiThongBaoCoVanForm(co_van=self._co_van(request))
        return render(request, self.template_name, {
            'form': form, 'tieu_de': 'Gửi thông báo lớp hành chính',
            'mo_ta': 'Gửi cho sinh viên thuộc một lớp hành chính bạn phụ trách.',
        })

    def post(self, request):
        co_van = self._co_van(request)
        form = GuiThongBaoCoVanForm(request.POST, co_van=co_van)
        if co_van is not None and form.is_valid():
            thong_bao = form.save(commit=False)
            thong_bao.nguoi_gui = request.user
            thong_bao.save()
            messages.success(request, 'Đã gửi thông báo.')
            return redirect('thong_bao:gui_co_van')
        return render(request, self.template_name, {
            'form': form, 'tieu_de': 'Gửi thông báo lớp hành chính',
            'mo_ta': 'Gửi cho sinh viên thuộc một lớp hành chính bạn phụ trách.',
        })


class DanhSachThongBaoView(LoginRequiredMixin, ListView):
    template_name = 'thong_bao/danh_sach.html'
    context_object_name = 'danh_sach'
    paginate_by = 20

    def get_queryset(self):
        # Không đặt tên thuộc tính là "da_doc": đó là tên quan hệ ngược của DaDocThongBao,
        # gán trực tiếp vào sẽ báo TypeError.
        return thong_bao_lien_quan(self.request.user).annotate(
            da_doc_boi_toi=Exists(
                DaDocThongBao.objects.filter(thong_bao=OuterRef('pk'), tai_khoan=self.request.user)
            )
        )


class ChiTietThongBaoView(LoginRequiredMixin, View):
    template_name = 'thong_bao/chi_tiet.html'

    def get(self, request, pk):
        thong_bao = get_object_or_404(thong_bao_lien_quan(request.user), pk=pk)
        danh_dau_da_doc(thong_bao, request.user)
        return render(request, self.template_name, {'thong_bao': thong_bao})
