from django.contrib import admin
from .models import *
from django import forms
from django.core.exceptions import ValidationError

admin.site.register(UserPoint)
admin.site.register(PointUsage)

# ---- StaffPin: 4자리 숫자만 입력 → 해시 저장(선택 입력) ----
class StaffPinAdminForm(forms.ModelForm):
    raw_pin = forms.CharField(
        label="새 PIN (4자리 숫자)",
        required=False,  # ← 선택 입력: 입력했을 때만 갱신
        widget=forms.PasswordInput(render_value=False),
        help_text="새로 등록/변경 시에만 입력하세요. 입력하지 않으면 기존 PIN을 유지합니다."
    )

    class Meta:
        model = StaffPin
        fields = ("is_active", "note")  # pin_hash는 노출/수정하지 않음

    def clean_raw_pin(self):
        raw = (self.cleaned_data.get("raw_pin") or "").strip()
        if raw and (not raw.isdigit() or len(raw) != 4):
            raise ValidationError("PIN은 반드시 4자리 숫자여야 합니다.")
        return raw

    def save(self, commit=True):
        obj = super().save(commit=False)
        raw = (self.cleaned_data.get("raw_pin") or "").strip()
        if raw:
            obj.set_pin(raw)  # 평문 PIN → 해시 저장
        if commit:
            obj.save()
        return obj


@admin.register(StaffPin)
class StaffPinAdmin(admin.ModelAdmin):
    form = StaffPinAdminForm
    list_display = ("created_at", "is_active", "note")
    list_filter = ("is_active",)
    search_fields = ("note",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {
            "fields": ("raw_pin", "is_active", "note", "created_at"),
            "description": "새 PIN(4자리 숫자)을 입력하면 자동으로 해시 저장됩니다. 비워두면 기존 PIN을 유지합니다.",
        }),
    )

    actions = ["deactivate_selected", "activate_selected"]

    @admin.action(description="선택한 PIN 비활성화")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated}개의 PIN을 비활성화했습니다.")

    @admin.action(description="선택한 PIN 활성화")
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated}개의 PIN을 활성화했습니다.")