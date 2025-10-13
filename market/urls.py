from django.urls import path
from .views import *

app_name = 'market'

urlpatterns = [
    path("filter/recipe", edit_market_filter_recipe, name="edit_market_filter_recipe"),
    path("filter/ingredient", edit_market_filter_ingredient, name="edit_market_filter_ingredient"),
    path('nearest/', nearest_market_view, name = "nearest_market"),
    path('direction/', map_direction_view, name='map_direction'),
    path('arrival/<int:shoppinglist_id>/', market_arrival_view, name='market_arrival'),
    path("arrival/<int:shoppinglist_id>/save", save_selected_ingredients_view, name="save_selected_ingredients"),
    path("tip", ingredient_tip_page, name="ingredient_tip_page"),
    path("api/ingredient-tip", ingredient_tip_api, name="ingredient_tip_api"),
    path('verify-secret/', verify_secret_code, name='verify_secret'),
    path('secret-input/<int:market_id>/', secret_input_view, name='secret_input'),
    path('success/<int:shoppinglist_id>/', shopping_success_view, name='shopping_success'),
    path("nearby/<int:market_id>/random/", nearby_places_random_api, name="nearby_random"),
]