import requests
from django.conf import settings

TMAP_PEDESTRIAN_URL = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"

def get_pedestrian_route(start_lat, start_lng, end_lat, end_lng):
    headers = {
        "appKey": settings.TMAP_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    body = {
        "startX": float(start_lng), "startY": float(start_lat),
        "endX": float(end_lng),     "endY": float(end_lat),
        "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO",
        "startName": "출발", "endName": "도착", "searchOption": "0",
    }
    r = requests.post(TMAP_PEDESTRIAN_URL, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    data = r.json()

    path, total_distance, total_time = [], 0, 0
    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        if geom.get("type") == "LineString":
            for x, y in geom.get("coordinates", []):
                path.append({"lat": y, "lng": x})
        props = feat.get("properties", {})
        total_distance = props.get("totalDistance", total_distance)
        total_time = props.get("totalTime", total_time)

    return {"path": path, "distance_m": total_distance, "duration_s": total_time}