const numberFormat = new Intl.NumberFormat();

const refs = {
  dataStatus: document.querySelector("#dataStatus"),
  searchInput: document.querySelector("#searchInput"),
  stateSelect: document.querySelector("#stateSelect"),
  typeSelect: document.querySelector("#typeSelect"),
  resetButton: document.querySelector("#resetButton"),
  totalMetric: document.querySelector("#totalMetric"),
  visibleMetric: document.querySelector("#visibleMetric"),
  clusterMetric: document.querySelector("#clusterMetric"),
  resultCount: document.querySelector("#resultCount"),
  licenseList: document.querySelector("#licenseList"),
  mapStatus: document.querySelector("#mapStatus"),
};

const map = L.map("map", {
  preferCanvas: true,
  minZoom: 2,
  maxZoom: 18,
  worldCopyJump: true,
}).setView([39.5, -98.35], 4);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
const markerById = new Map();
let markerAbort = null;
let listAbort = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactNumber(value) {
  return numberFormat.format(value ?? 0);
}

function shortNumber(value) {
  if (value >= 10000) return `${Math.round(value / 1000)}k`;
  if (value >= 1000) return `${Math.round(value / 100) / 10}k`;
  return String(value);
}

function sourceLabel(value) {
  if (value === "census_zcta_2025") return "ZCTA centroid";
  if (value === "state_centroid_fallback") return "State centroid";
  return "No coordinates";
}

function debounce(fn, delay) {
  let handle = null;
  return (...args) => {
    window.clearTimeout(handle);
    handle = window.setTimeout(() => fn(...args), delay);
  };
}

function filterParams(includeBounds = true) {
  const params = new URLSearchParams();
  if (includeBounds) {
    const bounds = map.getBounds();
    params.set("north", bounds.getNorth().toFixed(6));
    params.set("south", bounds.getSouth().toFixed(6));
    params.set("east", bounds.getEast().toFixed(6));
    params.set("west", bounds.getWest().toFixed(6));
  }
  params.set("zoom", String(map.getZoom()));

  const state = refs.stateSelect.value;
  const licenseType = refs.typeSelect.value;
  const query = refs.searchInput.value.trim();
  if (state) params.set("state", state);
  if (licenseType) params.set("license_type", licenseType);
  if (query) params.set("q", query);
  return params;
}

function markerRadius(marker) {
  return marker.kind === "license" ? 6 : 18;
}

function licenseMarkerStyle(marker) {
  return {
    radius: markerRadius(marker),
    color: "#ffffff",
    weight: 1.5,
    fillColor: "#1464a5",
    fillOpacity: 0.9,
  };
}

function clusterSize(count) {
  if (count >= 2500) return 52;
  if (count >= 1000) return 48;
  if (count >= 250) return 42;
  if (count >= 60) return 36;
  return 30;
}

function clusterClass(count) {
  if (count >= 1000) return "cluster-heavy";
  if (count >= 250) return "cluster-medium";
  return "cluster-light";
}

function clusterIcon(item) {
  const size = clusterSize(item.count);
  return L.divIcon({
    className: `cluster-bubble ${clusterClass(item.count)}`,
    html: `<span>${escapeHtml(shortNumber(item.count))}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function popupForLicense(item) {
  const address = [item.address, item.city, item.state, item.zip].filter(Boolean).join(", ");
  return `
    <strong class="popup-title">${escapeHtml(item.display_name)}</strong>
    <div class="popup-meta">
      ${escapeHtml(item.type_label)} (${escapeHtml(item.license_type)})<br />
      ${escapeHtml(address)}<br />
      FFL ${escapeHtml(item.ffl_number)}<br />
      ${escapeHtml(sourceLabel(item.geo_source))}
    </div>
  `;
}

function popupForCluster(item) {
  const samples = (item.samples || []).map(escapeHtml).join("<br />");
  return `
    <strong class="popup-title">${compactNumber(item.count)} licenses</strong>
    <div class="popup-meta">
      ${escapeHtml(item.primary_state || "")}<br />
      ${samples}
    </div>
  `;
}

function renderMarkers(payload) {
  markerLayer.clearLayers();
  markerById.clear();

  for (const item of payload.markers) {
    if (item.kind === "cluster") {
      const marker = L.marker([item.lat, item.lon], { icon: clusterIcon(item) }).addTo(markerLayer);
      marker.bindPopup(popupForCluster(item));
      marker.on("click", () => {
        marker.openPopup();
        map.flyTo([item.lat, item.lon], Math.min(map.getZoom() + 2, 12), { duration: 0.35 });
      });
    } else {
      const marker = L.circleMarker([item.lat, item.lon], licenseMarkerStyle(item)).addTo(markerLayer);
      marker.bindPopup(popupForLicense(item));
      markerById.set(item.id, marker);
    }
  }

  refs.visibleMetric.textContent = compactNumber(payload.total);
  refs.clusterMetric.textContent = compactNumber(payload.returned);
  refs.mapStatus.textContent = `${compactNumber(payload.total)} in view · ${compactNumber(
    payload.returned,
  )} ${payload.mode}`;
}

function renderList(payload) {
  refs.resultCount.textContent = `${compactNumber(payload.licenses.length)} of ${compactNumber(
    payload.total,
  )}`;
  refs.licenseList.textContent = "";

  if (!payload.licenses.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No entries";
    refs.licenseList.append(empty);
    return;
  }

  for (const item of payload.licenses) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "license-card";
    const address = [item.city, item.state, item.zip].filter(Boolean).join(", ");
    button.innerHTML = `
      <strong>${escapeHtml(item.display_name)}</strong>
      <small>${escapeHtml(item.address)}</small>
      <small>${escapeHtml(address)}</small>
      <span class="type-pill">${escapeHtml(item.type_label)} · ${escapeHtml(item.license_type)}</span>
    `;
    button.addEventListener("click", () => focusLicense(item));
    refs.licenseList.append(button);
  }
}

function focusLicense(item) {
  if (item.lat == null || item.lon == null) return;

  const latlng = [item.lat, item.lon];
  map.flyTo(latlng, Math.max(map.getZoom(), 12), { duration: 0.3 });

  const existing = markerById.get(item.id);
  if (existing) {
    existing.openPopup();
    return;
  }

  L.popup().setLatLng(latlng).setContent(popupForLicense(item)).openOn(map);
}

async function loadStatsAndFilters() {
  const [statsResponse, filtersResponse] = await Promise.all([
    fetch("/api/stats"),
    fetch("/api/filters"),
  ]);
  if (!statsResponse.ok) throw new Error("Stats request failed");
  if (!filtersResponse.ok) throw new Error("Filters request failed");

  const stats = await statsResponse.json();
  const filters = await filtersResponse.json();

  refs.totalMetric.textContent = compactNumber(stats.total);
  refs.dataStatus.textContent = `${compactNumber(stats.geocoded)} mapped · ZIP-area estimates`;

  for (const item of filters.states) {
    const option = document.createElement("option");
    option.value = item.state;
    option.textContent = `${item.state} (${compactNumber(item.count)})`;
    refs.stateSelect.append(option);
  }

  for (const item of filters.license_types) {
    const option = document.createElement("option");
    option.value = item.license_type;
    option.textContent = `${item.license_type} · ${item.type_label} (${compactNumber(item.count)})`;
    refs.typeSelect.append(option);
  }
}

async function loadMarkers() {
  if (markerAbort) markerAbort.abort();
  markerAbort = new AbortController();
  const params = filterParams(true);

  refs.mapStatus.textContent = "Loading";
  try {
    const response = await fetch(`/api/markers?${params}`, { signal: markerAbort.signal });
    if (!response.ok) throw new Error("Marker request failed");
    renderMarkers(await response.json());
  } catch (error) {
    if (error.name === "AbortError") return;
    refs.mapStatus.textContent = "Map data unavailable";
    console.error(error);
  }
}

async function loadList() {
  if (listAbort) listAbort.abort();
  listAbort = new AbortController();
  const params = filterParams(true);
  params.set("limit", "75");

  try {
    const response = await fetch(`/api/licenses?${params}`, { signal: listAbort.signal });
    if (!response.ok) throw new Error("List request failed");
    renderList(await response.json());
  } catch (error) {
    if (error.name === "AbortError") return;
    refs.licenseList.innerHTML = '<div class="empty-state">Entries unavailable</div>';
    console.error(error);
  }
}

const refresh = debounce(() => {
  loadMarkers();
  loadList();
}, 170);

refs.searchInput.addEventListener("input", refresh);
refs.stateSelect.addEventListener("change", refresh);
refs.typeSelect.addEventListener("change", refresh);
refs.resetButton.addEventListener("click", () => {
  refs.searchInput.value = "";
  refs.stateSelect.value = "";
  refs.typeSelect.value = "";
  map.setView([39.5, -98.35], 4);
  refresh();
});

map.on("moveend zoomend", refresh);

loadStatsAndFilters()
  .then(() => {
    loadMarkers();
    loadList();
  })
  .catch((error) => {
    refs.dataStatus.textContent = "Database unavailable";
    refs.mapStatus.textContent = "Database unavailable";
    console.error(error);
  });
