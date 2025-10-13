from django.urls import path
from .views import *

app_name = 'food'

urlpatterns = [
    path('', main, name='main'),
    path('splash/', splash, name='splash'),
    # 1. 요리를 할거야
    path('recipe/start/', recipe_input_view, name='recipe_input'),
    path('recipe/ingredients/', recipe_ingredient_result, name='recipe_ingredients'),
    path('recipe/ingredients/search/', ingredient_search_view, name='ingredient_search'),
    path('recipe/ingredients/search/add/', add_extra_ingredient, name='add_extra_ingredient'),
    path('recipe/ingredients/search/delete/<str:name>/', delete_extra_ingredient, name='delete_extra_ingredient'),
    path('recipe/ingredients/recent/delete/<str:keyword>/', delete_recent_search, name='delete_recent_search'),
    path('recipe/ingredients/recent/clear/', clear_recent_searches, name='clear_recent_searches'),
    path('recipe/ingredients/search/cancel/', cancel_ingredient_search, name='cancel_ingredient_search'),
    path('recipe/confirm/', confirm_shopping_list, name='confirm_shopping_list'),
    path('recipe/ai/', recipe_ai, name='recipe_ai'),

    # 2. 식재료를 고를거야
    path('ingredient/', ingredient_input_view, name='ingredient_input'),
    path('ingredient/add/', add_ingredient, name='add_ingredient'),
    path('ingredient/delete/<str:name>/', delete_ingredient, name='delete_ingredient'),
    path('ingredient/recent/delete/<str:keyword>/', delete_recent_ingredient, name='delete_recent_ingredient'),
    path('ingredient/recent/clear/', clear_recent_ingredient, name='clear_recent_ingredient'),
    path('ingredient/result/', ingredient_result_view, name='ingredient_result'),
    path("ingredient/idea/", ingredient_idea_page, name="ingredient_idea_page"),
    path("ingredient/idea/api/", ingredient_idea_api, name="ingredient_idea_api"),

    # 3. 남은 식재료로 요리 추천받기
    path("leftover/select/", select_recent_ingredients, name="select_recent_ingredients"),
    path("leftover/chat/", chat_with_selected_ingredients, name="chat_with_selected_ingredients"),
    path("leftover/save/", save_last_recipe, name="save_last_recipe"),
    path("leftover/clear/", clear_recipe_chat, name="clear_recipe_chat"),

    # 최근 장바구니 → 직접 추가 검색 관련
    path('leftover/extra/search/', leftover_extra_ingredient_search_view, name='leftover_extra_ingredient_search'),
    path('leftover/extra/add/', leftover_add_extra_ingredient, name='leftover_add_extra_ingredient'),
    path("leftover/remove_extra/<str:ingredient_name>/",leftover_remove_extra_ingredient, name="leftover_remove_extra_ingredient"),
    path('leftover/extra/delete/<str:name>/', leftover_delete_extra_ingredient, name='leftover_delete_extra_ingredient'),

    # 최근 검색어 관리
    path('leftover/extra/recent/delete/<str:keyword>/', delete_extra_recent_search, name='delete_extra_recent_search'),
    path('leftover/extra/recent/clear/', clear_extra_recent_searches, name='clear_extra_recent_searches'),

    #4. 장바구니
    path("cart/", cart_view, name="cart_view"),
]