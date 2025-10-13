

const qs = (id) => document.getElementById(id);

function getInitCenter() {
  const mapEl = qs('map');
  if (!mapEl) return { lat: 37.5665, lng: 126.9780 }; // 서울 시청 근처 폴백
  const lat = parseFloat(mapEl.dataset.initLat);
  const lng = parseFloat(mapEl.dataset.initLng);
  return {
    lat: Number.isFinite(lat) ? lat : 37.5665,
    lng: Number.isFinite(lng) ? lng : 126.9780,
  };
}

function setHiddenLatLng(lat, lng) {
  const fLat = qs('f-lat');
  const fLng = qs('f-lng');
  if (fLat) fLat.value = lat.toFixed(6);
  if (fLng) fLng.value = lng.toFixed(6);
}

function clearAddressFields() {
  const title = qs('addr-title');
  const sub   = qs('addr-sub');
  if (title) title.textContent = '주소를 찾을 수 없습니다';
  if (sub)   sub.textContent   = '';
  const name = qs('f-name'), l1 = qs('f-l1'), l2 = qs('f-l2'), l3 = qs('f-l3');
  if (name) name.value = '';
  if (l1)   l1.value   = '';
  if (l2)   l2.value   = '';
  if (l3)   l3.value   = '';
}

// === kakao map state (전역에 하나만) ===
let map = null;
let geocoder = null;
let gpsOverlay = null;     // CustomOverlay (파란 점 + pulse)
let accuracyCircle = null; // kakao.maps.Circle (정확도 원)

// 파란 GPS 점 + 퍼지는 링 + 정확도 원
function showGps(lat, lng, accuracy) {
  const pos = new kakao.maps.LatLng(lat, lng);

  // 파란 점(커스텀 오버레이)
  if (!gpsOverlay) {
    const el = document.createElement('div');
    // 중앙 고정핀(img.center-pin)과 구분 위해 custom-gps 보조 클래스 사용
    el.className = 'center-pin custom-gps';
    el.innerHTML = '<span class="pulse"></span>';

    gpsOverlay = new kakao.maps.CustomOverlay({
      position: pos,
      content: el,
      xAnchor: 0.5,
      yAnchor: 0.5,
      zIndex: 10,
    });
    gpsOverlay.setMap(map);
  } else {
    gpsOverlay.setPosition(pos);
  }

  // 정확도 원 (최소 30m 보정)
  const r = Math.max(accuracy || 30, 30);
  if (!accuracyCircle) {
    accuracyCircle = new kakao.maps.Circle({
      center: pos,
      radius: r,
      strokeWeight: 1,
      strokeColor: '#1D4ED8',
      strokeOpacity: 0.6,
      strokeStyle: 'solid',
      fillColor: '#3B82F6',
      fillOpacity: 0.2,
      zIndex: 9,
    });
    accuracyCircle.setMap(map);
  } else {
    accuracyCircle.setOptions({ center: pos, radius: r });
  }
}

// 지도 중심 좌표 기준으로 주소 갱신 + 히든필드 세팅
function updateCenterInfo() {
  const center = map.getCenter();
  const lat = center.getLat();
  const lng = center.getLng();
  setHiddenLatLng(lat, lng);

  geocoder.coord2Address(lng, lat, function (result, status) {
    if (status !== kakao.maps.services.Status.OK || !result || !result.length) {
      clearAddressFields();
      return;
    }

    const r = result[0];
    const road  = r.road_address;
    const jibun = r.address;

    const name = (road && road.address_name) || (jibun && jibun.address_name) || '';
    const l1   = (road && road.region_1depth_name) || (jibun && jibun.region_1depth_name) || '';
    const l2   = (road && road.region_2depth_name) || (jibun && jibun.region_2depth_name) || '';
    const l3   = (road && road.region_3depth_name) || (jibun && jibun.region_3depth_name) || '';

    const title = qs('addr-title');
    const sub   = qs('addr-sub');
    if (title) title.textContent = name || '주소 미확인';
    if (sub)   sub.textContent   = (l1 + ' ' + l2 + ' ' + l3).trim();

    const fName = qs('f-name'), f1 = qs('f-l1'), f2 = qs('f-l2'), f3 = qs('f-l3');
    if (fName) fName.value = name;
    if (f1)    f1.value    = l1;
    if (f2)    f2.value    = l2;
    if (f3)    f3.value    = l3;
  });
}

// 초기화
function initAddressPickMap() {
  if (!window.kakao || !kakao.maps) {
    alert('지도를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
    return;
  }

  const mapEl = qs('map');
  const center0 = getInitCenter();

  map = new kakao.maps.Map(mapEl, {
    center: new kakao.maps.LatLng(center0.lat, center0.lng),
    level: 3,
  });

  geocoder = new kakao.maps.services.Geocoder();

  kakao.maps.event.addListener(map, 'idle', updateCenterInfo);
  updateCenterInfo(); // 첫 렌더 갱신

  // 현재 위치로 이동 + GPS 핀 표시
  const btn = qs('btn-geolocate');
  if (btn) {
    btn.addEventListener('click', function () {
      if (!navigator.geolocation) {
        alert('브라우저가 위치 정보를 지원하지 않습니다.');
        return;
      }
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          showGps(lat, lng, pos.coords.accuracy);
          map.setCenter(new kakao.maps.LatLng(lat, lng));
        },
        function (err) {
          alert('현재 위치를 가져오지 못했습니다. 권한을 허용했는지 확인해 주세요.');
          console.error(err);
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
      );
    });
  }
}

// DOM 준비되면 실행 (script defer 가급적 사용)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAddressPickMap);
} else {
  initAddressPickMap();
}