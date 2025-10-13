from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()

class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='ingredients/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name'] 
    
class SavedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200) 
    description = models.TextField()         
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"
    

class FoodBannerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_user(self, user):
        dong = getattr(user, "addr_level3", "") or ""
        # dong이 비어 있으면(전체 노출) 또는 사용자의 동과 일치하면 매칭
        return self.filter(Q(dong="") | Q(dong=dong))

    def for_category(self, category):
        return self.filter(category=category)


class FoodBanner(models.Model):
    class Category(models.TextChoices):
        MART = "mart", "마트"
        CAFE = "cafe", "카페"
        TRAD = "trad", "시장"

    title = models.CharField(max_length=80)
    category = models.CharField(max_length=10, choices=Category.choices)
    dong = models.CharField(max_length=40, blank=True, help_text="읍/면/동. 비워두면 전체 노출")
    link_url = models.URLField(blank=True)
    image = models.ImageField(upload_to="banners/")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # 커스텀 QuerySet을 기본 매니저로 사용
    objects = FoodBannerQuerySet.as_manager()

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
