from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from food.models import Ingredient

User = get_user_model()

class MarketType(models.TextChoices):
    MART = 'mart', '마트'
    TRAD = 'trad', '전통시장'


class Market(models.Model):
    name = models.CharField(max_length=100)
    market_type = models.CharField(max_length=10, choices=MarketType.choices)
    info = models.CharField(max_length=100) 
    address = models.CharField(max_length=200)
    dong = models.CharField(max_length=10, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone = models.CharField(max_length=20, blank=True)
    image = models.ImageField(upload_to='market/', blank=True, null=True)
    secret_code = models.CharField(max_length=20)
    open_days = models.CharField(max_length=50, help_text="예: 월,화,수,목,금")
    open_time = models.TimeField(help_text="예: 09:00")
    close_time = models.TimeField(help_text="예: 18:00")

    def __str__(self):
        return self.name


class MarketStock(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.market.market_type == MarketType.TRAD:
            raise ValidationError('전통시장에는 MarketStock을 등록할 수 없습니다.')

    def __str__(self):
        return f"{self.market.name} - {self.ingredient.name}"


class ShoppingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} - {self.user.username} - {self.created_at.date()}"


class ShoppingListIngredient(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['shopping_list', 'ingredient'],
                name='uniq_shoppinglist_ingredient'
            )
        ]

    def __str__(self):
        return f"{self.shopping_list.id} - {self.ingredient.name}"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE)
    visited_at = models.DateTimeField(auto_now_add=True)
    point_earned = models.IntegerField(default=0)
    steps = models.PositiveIntegerField(null=True, blank=True,)
    calories_kcal = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    travel_minutes = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.point_earned}P"


class NearbyPlace(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='nearby_places')

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20)
    info = models.CharField(max_length=200, blank=True, help_text='한 줄 소개')
    open_days = models.CharField(max_length=50, help_text="예: 월,화,수,목,금")
    open_time = models.TimeField(help_text="예: 09:00")
    close_time = models.TimeField(help_text="예: 18:00")
    distance_m = models.PositiveIntegerField(help_text='단위: m')
    image = models.ImageField(upload_to='market/nearby/', blank=True, null=True)
    link_url = models.URLField(blank=True, help_text='상세 보기 링크')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.market.name} - {self.name}'



# ====== 필터 설정 ======
class MarketFilterSetting(models.Model):
    class TypePref(models.TextChoices):
        NONE = 'none', '상관 없어요'
        MART = MarketType.MART, '동네 마트를 우선 보여주세요'
        TRAD = MarketType.TRAD, '전통 시장을 우선 보여주세요'

    class DistancePref(models.TextChoices):
        WITHIN_1KM = 'within_1km', '1km 이내만 보여주세요'  # d <= 1000m
        ANY_2KM    = 'any_2km',    '상관 없어요'            # d <= 2000m

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='market_filter'
    )

    # 거리 선택(기본: 1km 이내)
    distance_preference = models.CharField(
        max_length=20,
        choices=DistancePref.choices,
        default=DistancePref.WITHIN_1KM
    )

    # 마켓 타입 우선순위
    type_preference = models.CharField(
        max_length=10,
        choices=TypePref.choices,
        default=TypePref.NONE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 거리 범위 편의 메서드
    @property
    def distance_range_m(self) -> tuple[int, int, bool]:
        """
        반환: (min_m, max_m, min_is_strict)
        - WITHIN_1KM -> (0, 1000, False)   : 0 <= d <= 1000
        - ANY_2KM    -> (1000, 2000, True) : 1000 < d <= 2000
        """
        if self.distance_preference == self.DistancePref.ANY_2KM:
            return (0, 2000, False)
        return (0, 1000, False)

    def __str__(self):
        return f'{self.user} filter'