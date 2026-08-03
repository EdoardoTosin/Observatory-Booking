/**
 * Interactive Leaflet + OpenStreetMap location picker for the System
 * Settings tab. Keeps the (still submitted) latitude/longitude number
 * inputs in sync with a draggable marker, so admins don't have to know
 * coordinates offhand.
 */
document.addEventListener("DOMContentLoaded", function () {
  const mapContainer = document.getElementById("locationMap");
  if (!mapContainer || typeof L === "undefined") {
    return;
  }

  const config = window.LOCATION_MAP_CONFIG || {};
  const latitudeInput = document.getElementById("latitude");
  const longitudeInput = document.getElementById("longitude");

  let map = null;
  let marker = null;

  // The Configuration tab may be `display:none` (the `hidden` class) at
  // load time if another tab is active - Leaflet can't measure a hidden
  // container, so the map is created lazily the first time this tab
  // actually becomes visible, and resized on every later activation in
  // case the container's dimensions changed since.
  function initializeMap() {
    const defaultIcon = L.icon({
      iconUrl: config.iconUrl,
      iconRetinaUrl: config.iconRetinaUrl,
      shadowUrl: config.shadowUrl,
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
      shadowSize: [41, 41],
    });

    const initialLat = Number(config.latitude) || 0;
    const initialLng = Number(config.longitude) || 0;

    map = L.map("locationMap").setView([initialLat, initialLng], 6);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    marker = L.marker([initialLat, initialLng], {
      icon: defaultIcon,
      draggable: true,
    }).addTo(map);

    marker.on("dragend", function () {
      const position = marker.getLatLng();
      updateInputs(position.lat, position.lng);
    });

    map.on("click", function (event) {
      marker.setLatLng(event.latlng);
      updateInputs(event.latlng.lat, event.latlng.lng);
    });

    latitudeInput.addEventListener("change", syncMarkerFromInputs);
    longitudeInput.addEventListener("change", syncMarkerFromInputs);
  }

  function updateInputs(lat, lng) {
    latitudeInput.value = lat.toFixed(6);
    longitudeInput.value = lng.toFixed(6);
  }

  function syncMarkerFromInputs() {
    if (!marker) {
      return;
    }
    const lat = Number(latitudeInput.value);
    const lng = Number(longitudeInput.value);
    if (Number.isNaN(lat) || Number.isNaN(lng)) {
      return;
    }
    marker.setLatLng([lat, lng]);
    map.panTo([lat, lng]);
  }

  function isConfigurationTabVisible() {
    const tab = document.getElementById("configurationTab");
    return tab && !tab.classList.contains("hidden");
  }

  function activateMap() {
    if (!map) {
      initializeMap();
    } else {
      map.invalidateSize();
    }
  }

  if (isConfigurationTabVisible()) {
    activateMap();
  }

  document.addEventListener("admin:tabchange", function (event) {
    if (event.detail.tab === "configuration") {
      activateMap();
    }
  });
});
