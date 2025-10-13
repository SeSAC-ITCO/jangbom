from django.contrib import admin
from .models import *

admin.site.register(Market)
admin.site.register(MarketStock)
admin.site.register(ShoppingList)
admin.site.register(ShoppingListIngredient)
admin.site.register(ActivityLog)
admin.site.register(NearbyPlace)
admin.site.register(MarketFilterSetting)