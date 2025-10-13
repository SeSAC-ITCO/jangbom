from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password

User = get_user_model()

class UserPoint(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='point')
    total_point = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.total_point}P"
    
class PointUsage(models.Model):
    """포인트 사용(차감) 이력"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_usages')
    amount = models.PositiveIntegerField()  # 양수 (사용한 포인트)
    created_at = models.DateTimeField(default=timezone.now)
    request_id = models.CharField(max_length=64, blank=True, null=True, unique=True)  # 중복 방지 키
    memo = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'created_at'])]

    def __str__(self):
        return f"{self.user} 사용 -{self.amount}P @ {self.created_at:%Y-%m-%d %H:%M}"


class StaffPin(models.Model):
    """
    관리자용 4자리 PIN 저장(해시만 저장).
    여러 개 등록 가능하며, is_active=True인 것 중 최신 1개만 사용.
    """
    pin_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        state = "활성" if self.is_active else "비활성"
        return f"[{state}] {self.created_at:%Y-%m-%d %H:%M} {self.note or ''}"

    def set_pin(self, raw_pin: str):
        self.pin_hash = make_password(raw_pin)

    def verify(self, raw_pin: str) -> bool:
        return check_password(raw_pin, self.pin_hash)