from market.integrations.tmap_client import get_pedestrian_route

def route_user_to_market(user, market):
    return get_pedestrian_route(
        user.latitude, user.longitude, market.latitude, market.longitude
    )