from django.urls import path
from .views import *

app_name = 'accounts'

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # 내 활동
    path('activity/', activity_log_view, name='activity_log'),
    path('activity/history/', activity_history_view, name='activity_history'),
    path("activity/<int:shopping_list_id>/ajax/", activity_detail_ajax, name="activity_detail_ajax"),
    
    # 레시피 모아보기
    path('recipes/', my_recipes, name='my_recipes'),
    path('recipes/<int:recipe_id>/ajax/', recipe_detail_ajax, name='recipe_detail_ajax'),

    # 주소 설정
    path("address/", address_settings, name="address_settings"),
    path("address/search/", address_search, name="address_search"),
    path("address/save/", address_save, name="address_save"),
    path("address/delete/<int:addr_id>/", address_delete, name="address_delete"),
    path("address/select/<int:addr_id>/", address_select_primary, name="address_select_primary"),
    path("address/map/", address_pick_map, name="address_pick_map"),
    path("address/save-from-map/", address_save_from_map, name="address_save_from_map"),
]