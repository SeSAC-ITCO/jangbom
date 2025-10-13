from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    nickname = models.CharField(max_length=30, unique=True)

    # 현재 대표 주소만 FK로 가리킴
    selected_address = models.ForeignKey(
        'Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='selected_by'
    )

    # (미러 필드) 대표 주소 정보 복사본
    address      = models.CharField(max_length=200, blank=True, null=True)  # 전체 주소
    addr_level1   = models.CharField(max_length=20, blank=True, null=True)   # 시·도
    addr_level2   = models.CharField(max_length=30, blank=True, null=True)   # 시·군·구
    addr_level3   = models.CharField(max_length=40, blank=True, null=True)   # 읍·면·동
    latitude      = models.FloatField(blank=True, null=True)
    longitude     = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.username

    @property
    def active_address(self):
        """대표 주소 객체 가져오기."""
        return self.selected_address


class Address(models.Model):
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='addresses'
    )

    address      = models.CharField(max_length=200)          # 전체 주소
    addr_level1   = models.CharField(max_length=20)            # 시·도
    addr_level2   = models.CharField(max_length=30)            # 시·군·구
    addr_level3   = models.CharField(max_length=40, blank=True) # 읍·면·동
    latitude      = models.FloatField()
    longitude     = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.address}"