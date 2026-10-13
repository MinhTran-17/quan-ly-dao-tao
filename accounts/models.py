from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class VaiTro(models.TextChoices):
    PHONG_DAO_TAO = 'PHONG_DAO_TAO', 'Phòng Đào tạo'
    GIANG_VIEN = 'GIANG_VIEN', 'Giảng viên'
    SINH_VIEN = 'SINH_VIEN', 'Sinh viên'
    CO_VAN_HOC_TAP = 'CO_VAN_HOC_TAP', 'Cố vấn học tập'


class TaiKhoanManager(BaseUserManager):
    def create_user(self, ten_dang_nhap, vai_tro, password=None, **extra_fields):
        if not ten_dang_nhap:
            raise ValueError('Tài khoản phải có tên đăng nhập')
        if not vai_tro:
            raise ValueError('Tài khoản phải có vai trò')
        user = self.model(ten_dang_nhap=ten_dang_nhap, vai_tro=vai_tro, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, ten_dang_nhap):
        return self.get(ten_dang_nhap=ten_dang_nhap)


class TaiKhoan(AbstractBaseUser):
    # Không kế thừa PermissionsMixin và bỏ last_login để bảng tai_khoan
    # không có cột ngoài docs/erd.md (xem mục "Bảng phụ của Django" cuối file đó).
    last_login = None

    ma_tai_khoan = models.AutoField(primary_key=True)
    ten_dang_nhap = models.CharField(max_length=50, unique=True)
    # Tên thuộc tính "password" là bắt buộc để AbstractBaseUser hoạt động
    # (set_password/check_password), cột thật trong MySQL vẫn là mat_khau_ma_hoa.
    password = models.CharField(max_length=255, db_column='mat_khau_ma_hoa')
    vai_tro = models.CharField(max_length=20, choices=VaiTro.choices)
    # Tên thuộc tính "is_active" là quy ước Django dùng khi xác thực đăng nhập,
    # cột thật trong MySQL vẫn là trang_thai.
    is_active = models.BooleanField(default=True, db_column='trang_thai')
    # True khi tài khoản vừa được Phòng Đào tạo đặt lại mật khẩu (mật khẩu tạm) hoặc
    # mới tạo và cần đổi mật khẩu ngay; middleware chặn mọi trang khác cho tới khi đổi xong.
    phai_doi_mat_khau = models.BooleanField(default=False)

    objects = TaiKhoanManager()

    USERNAME_FIELD = 'ten_dang_nhap'
    REQUIRED_FIELDS = ['vai_tro']

    class Meta:
        db_table = 'tai_khoan'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(vai_tro__in=VaiTro.values),
                name='ck_tai_khoan_vai_tro',
            ),
        ]

    def __str__(self):
        return self.ten_dang_nhap
