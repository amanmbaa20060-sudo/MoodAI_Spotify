/**
 * MoodAI mobile web app — wired to Phase 3 BFF.
 * UI based on Google Stitch export (stitch_moodai_discovery_interface).
 */

const USER_ID = new URLSearchParams(window.location.search).get("user") || "demo-user";
const API_HEADERS = { "X-User-Id": USER_ID, "Content-Type": "application/json" };

const MOODS = [
  { id: "ENERGISED", label: "Energised", icon: "bolt", tint: "text-[#ff8b7c]" },
  { id: "FOCUSED", label: "Focused", icon: "target", tint: "text-primary" },
  { id: "LOW_KEY", label: "Low-key", icon: "dark_mode", tint: "text-secondary" },
  { id: "ADVENTUROUS", label: "Adventurous", icon: "explore", tint: "text-primary" },
  { id: "NOSTALGIC", label: "Nostalgic", icon: "history", tint: "text-tertiary" },
  { id: "SAD", label: "Sad", icon: "water_drop", tint: "text-secondary-fixed-dim" },
];

const state = {
  view: "home",
  home: null,
  currentDropId: null,
  activeMood: "LOW_KEY",
  selectedMood: "LOW_KEY",
  moodConfirmed: false,
  genericHomeMode: false,
  moodOptions: MOODS.map((m) => m.id),
  loading: false,
  searchQuery: "",
  searchResults: [],
  searchLoading: false,
  heardBeforeTrack: null,
  nowPlaying: null,
  playQueue: [],
  artistDetail: null,
  artistLoading: false,
  artistReturnView: "search",
  selectedArtistId: null,
  selectedArtistName: null,
  showFirstTimeTooltip: !localStorage.getItem("moodai_tooltip_dismissed"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function hashHue(seed) {
  let hash = 0;
  const text = String(seed || "track");
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash << 5) - hash + text.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) % 360;
}

function albumArtStyle(track) {
  const hue = hashHue(track.track_id || track.title);
  return `background: linear-gradient(135deg, hsl(${hue}, 42%, 22%), hsl(${(hue + 48) % 360}, 55%, 32%))`;
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatMoodLabel(mood) {
  return MOODS.find((m) => m.id === mood)?.label || mood.replace(/_/g, " ");
}

function formatDateLabel() {
  return new Date().toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...API_HEADERS, ...(options.headers || {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("opacity-0", "translate-y-4", "pointer-events-none");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-4", "pointer-events-none");
  }, 2800);
}

function setView(view) {
  state.view = view;
  document.getElementById("view-home").classList.toggle("hidden", view !== "home");
  document.getElementById("view-search").classList.toggle("hidden", view !== "search");
  document.getElementById("view-library").classList.toggle("hidden", view !== "library");
  document.getElementById("view-artist").classList.toggle("hidden", view !== "artist");
  document.getElementById("header-back-btn")?.classList.toggle("hidden", view === "home");
  document.querySelectorAll("[data-nav]").forEach((btn) => {
    const active = btn.dataset.nav === view && view !== "artist";
    btn.classList.toggle("text-primary", active);
    btn.classList.toggle("font-bold", active);
    btn.classList.toggle("text-on-surface-variant", !active);
    const icon = btn.querySelector(".material-symbols-outlined");
    if (icon) {
      icon.style.fontVariationSettings = active ? "'FILL' 1" : "'FILL' 0";
    }
  });
  if (view === "search" && !state.searchResults.length) {
    document.getElementById("search-input")?.focus();
  }
  if (view === "artist") {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function goHome() {
  state.artistDetail = null;
  setView("home");
  if (state.genericHomeMode) {
    document.getElementById("greeting").textContent = `${greeting()} · Browse`;
    renderHome();
    return;
  }
  document.getElementById("greeting").textContent = state.moodConfirmed
    ? `${greeting()} · ${formatMoodLabel(state.activeMood)}`
    : greeting();
  if (state.home) {
    renderHome();
  } else {
    loadHome();
  }
}

function artistLink(name, artistId = null) {
  if (!name) return "Unknown artist";
  const attrs = artistId
    ? `data-artist-id="${escapeHtml(artistId)}"`
    : `data-artist-name="${escapeHtml(name)}"`;
  return `<button type="button" ${attrs} class="artist-link text-left truncate hover:text-primary transition-colors underline-offset-2 hover:underline">${escapeHtml(name)}</button>`;
}

function renderArtistNames(artists) {
  if (!artists?.length) return "Unknown artist";
  return artists.map((name) => artistLink(name)).join(", ");
}

function openArtist({ artistId = null, artistName = null } = {}) {
  if (!artistId && !artistName) return;
  if (state.view !== "artist") {
    state.artistReturnView = state.view;
  }
  state.selectedArtistId = artistId;
  state.selectedArtistName = artistName;
  setView("artist");
  loadArtistDetail({ artistId, artistName });
}

async function loadArtistDetail({ artistId = null, artistName = null } = {}) {
  state.artistLoading = true;
  state.artistDetail = null;
  renderArtistSkeleton();
  try {
    const path = artistId
      ? `/v1/artists/${encodeURIComponent(artistId)}`
      : `/v1/artists/lookup/by-name?name=${encodeURIComponent(artistName)}`;
    state.artistDetail = await api(path);
    renderArtistDetail();
  } catch (error) {
    renderArtistError(error.message);
  } finally {
    state.artistLoading = false;
  }
}

function renderArtistSkeleton() {
  document.getElementById("artist-content").innerHTML = `
    <div class="animate-pulse space-y-stack-lg">
      <div class="h-6 bg-surface-container rounded w-32"></div>
      <div class="flex flex-col items-center gap-4 py-4">
        <div class="w-40 h-40 rounded-full bg-surface-container"></div>
        <div class="h-8 bg-surface-container rounded w-48"></div>
        <div class="h-4 bg-surface-container rounded w-24"></div>
      </div>
      <div class="space-y-3">
        <div class="h-16 bg-surface-container rounded-xl"></div>
        <div class="h-16 bg-surface-container rounded-xl"></div>
        <div class="h-16 bg-surface-container rounded-xl"></div>
      </div>
    </div>`;
}

function renderArtistError(message) {
  document.getElementById("artist-content").innerHTML = `
    <div class="text-center py-16 space-y-4">
      <span class="material-symbols-outlined text-5xl text-on-surface-variant">person_off</span>
      <h3 class="font-headline-md text-headline-md">Artist not found</h3>
      <p class="text-on-surface-variant font-body-sm">${escapeHtml(message)}</p>
      <button type="button" id="artist-home-btn" class="px-6 py-3 rounded-full bg-primary text-on-primary font-bold">Back to home</button>
    </div>`;
  document.getElementById("artist-home-btn")?.addEventListener("click", goHome);
}

function renderArtistDetail() {
  const artist = state.artistDetail;
  if (!artist) return;

  const genre = artist.top_genre
    ? `<span class="px-3 py-1 bg-surface-container-highest text-primary-fixed rounded-full font-label-caps text-[10px] uppercase tracking-widest border border-outline-variant">${escapeHtml(artist.top_genre)}</span>`
    : "";
  const tracks = artist.tracks || [];

  document.getElementById("greeting").textContent = `${greeting()} · Artist`;

  document.getElementById("artist-content").innerHTML = `
    <section class="flex flex-col items-center text-center space-y-4 py-2">
      <div class="w-40 h-40 rounded-full overflow-hidden border-2 border-outline-variant shadow-xl artist-glow">
        <img class="w-full h-full object-cover" src="${escapeHtml(artist.image_url)}" alt="${escapeHtml(artist.image_alt || artist.name)}" loading="lazy" />
      </div>
      <div class="space-y-2">
        <h1 class="font-headline-md text-headline-md text-on-surface">${escapeHtml(artist.name)}</h1>
        <p class="font-caption text-on-surface-variant">${artist.track_count} tracks in catalog</p>
        ${genre}
      </div>
    </section>

    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h2 class="font-headline-md text-headline-md">Tracks</h2>
        ${tracks.length ? `
          <button type="button" id="play-all-artist" class="px-4 py-2 rounded-full bg-primary text-on-primary font-bold text-sm flex items-center gap-1.5 active:scale-95 transition-transform">
            <span class="material-symbols-outlined text-[18px]" style="font-variation-settings: 'FILL' 1">play_arrow</span>
            Play all
          </button>` : ""}
      </div>
      <div class="bg-surface-container rounded-3xl border border-outline-variant overflow-hidden">
        ${tracks.length ? `
          <div class="px-4 py-3 border-b border-outline-variant flex justify-between items-center">
            <span class="font-label-caps text-label-caps text-on-surface-variant">Catalog</span>
            <span class="text-caption font-caption text-primary">${tracks.length} tracks</span>
          </div>
          <div class="p-2 space-y-1">
            ${tracks.map((track) => trackRow(track, { compact: true, showArtistLink: false, showAlbumName: true })).join("")}
          </div>` : `<p class="text-center py-10 text-on-surface-variant font-body-sm">No tracks found for this artist.</p>`}
      </div>
    </section>`;

  bindArtistLinks(document.getElementById("artist-content"));
  bindArtistTrackEvents(tracks);

  document.getElementById("play-all-artist")?.addEventListener("click", () => {
    if (!tracks.length) return;
    state.nowPlaying = tracks[0];
    state.playQueue = tracks.slice();
    updateMiniPlayer();
    showToast(`Playing all ${tracks.length} tracks · starting with ${tracks[0].title}`);
  });
}

function bindArtistLinks(root = document) {
  root.querySelectorAll("[data-artist-id]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openArtist({ artistId: btn.dataset.artistId });
    });
  });
  root.querySelectorAll("[data-artist-name]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openArtist({ artistName: btn.dataset.artistName });
    });
  });
}

function bindArtistTrackEvents(tracks) {
  document.querySelectorAll("#artist-content [data-play]").forEach((btn) => {
    const track = tracks.find((item) => item.track_id === btn.dataset.play);
    if (track) {
      btn.addEventListener("click", () => {
        state.nowPlaying = track;
        updateMiniPlayer();
        showToast(`Playing ${track.title}`);
      });
    }
  });
}

async function loadHome({ preserveMoodFlow = false } = {}) {
  state.loading = true;
  if (!preserveMoodFlow) {
    state.genericHomeMode = false;
  }
  renderHomeSkeleton();
  try {
    const home = await api("/v1/home");
    state.home = home;
    state.activeMood = home.active_mood;
    if (!preserveMoodFlow) {
      state.selectedMood = home.active_mood;
      state.moodConfirmed = false;
    } else {
      state.selectedMood = state.moodConfirmed ? state.activeMood : state.selectedMood;
    }
    state.moodOptions = home.mood_options?.length ? home.mood_options : state.moodOptions;
    const dropModule = home.modules.find((m) => m.type === "discovery_drop");
    state.currentDropId = dropModule?.data?.drop_id || null;
    renderHome();
  } catch (error) {
    renderHomeError(error.message);
  } finally {
    state.loading = false;
  }
}

function selectMood(mood) {
  if (state.moodConfirmed && mood === state.activeMood) return;
  state.selectedMood = mood;
  state.moodConfirmed = false;
  dismissTooltip();
  renderHome();
}

async function confirmMood() {
  const mood = state.selectedMood;
  if (!mood) return;

  const confirmBtn = document.getElementById("confirm-mood-btn");
  confirmBtn?.setAttribute("disabled", "true");
  confirmBtn?.classList.add("opacity-60");

  try {
    const result = await api("/v1/users/me/mood", {
      method: "PUT",
      body: JSON.stringify({ mood, persist: true }),
    });
    state.home = result.home;
    state.activeMood = result.active_mood;
    state.selectedMood = result.active_mood;
    state.moodConfirmed = true;
    const dropModule = result.home.modules.find((m) => m.type === "discovery_drop");
    state.currentDropId = dropModule?.data?.drop_id || null;
    dismissTooltip();
    showToast(`Discovery unlocked for ${formatMoodLabel(mood)}`);
    renderHome();
  } catch (error) {
    showToast("Could not confirm mood. Try again.");
  } finally {
    confirmBtn?.removeAttribute("disabled");
    confirmBtn?.classList.remove("opacity-60");
  }
}

function openGenericHome() {
  state.genericHomeMode = true;
  state.moodConfirmed = false;
  renderHome();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function backToPersonalizedHome() {
  state.genericHomeMode = false;
  renderHome();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function searchArtists(query) {
  const q = query.trim();
  if (!q) {
    state.searchResults = [];
    renderSearch();
    return;
  }
  state.searchLoading = true;
  renderSearch();
  try {
    const data = await api(`/v1/search/artists?q=${encodeURIComponent(q)}`);
    state.searchResults = data.artists || [];
    state.searchQuery = data.query;
  } catch (error) {
    state.searchResults = [];
    showToast("Search failed. Check your connection.");
  } finally {
    state.searchLoading = false;
    renderSearch();
  }
}

function openHeardBefore(track) {
  state.heardBeforeTrack = track;
  const sheet = document.getElementById("heard-before-sheet");
  document.getElementById("heard-before-track-title").textContent = track.title;
  sheet.classList.remove("translate-y-full", "pointer-events-none");
  document.getElementById("sheet-backdrop").classList.remove("opacity-0", "pointer-events-none");
}

function closeHeardBefore() {
  state.heardBeforeTrack = null;
  document.getElementById("heard-before-sheet").classList.add("translate-y-full", "pointer-events-none");
  document.getElementById("sheet-backdrop").classList.add("opacity-0", "pointer-events-none");
}

async function confirmHeardBefore() {
  const track = state.heardBeforeTrack;
  if (!track) return;
  try {
    await api(`/v1/discovery-drop/tracks/${encodeURIComponent(track.track_id)}/heard-before`, {
      method: "POST",
      body: JSON.stringify({ drop_id: state.currentDropId }),
    });
    closeHeardBefore();
    showToast("Got it — we'll skip this next time.");
    await loadHome({ preserveMoodFlow: true });
  } catch (error) {
    showToast("Could not save feedback.");
  }
}

function dismissTooltip() {
  state.showFirstTimeTooltip = false;
  localStorage.setItem("moodai_tooltip_dismissed", "1");
  document.getElementById("mood-tooltip")?.classList.add("hidden");
}

function moodChip(mood, selected) {
  const meta = MOODS.find((m) => m.id === mood) || { label: mood, icon: "mood", tint: "text-on-surface-variant" };
  if (selected) {
    return `
      <button type="button" data-mood="${mood}" class="mood-gateway-chip flex-shrink-0 flex items-center gap-2 px-5 py-2.5 rounded-full bg-primary-container text-on-primary-container transition-all active:scale-95">
        <span class="material-symbols-outlined text-[20px]" style="font-variation-settings: 'FILL' 1">${meta.icon}</span>
        <span class="font-body-sm text-body-sm font-bold">${escapeHtml(meta.label)}</span>
      </button>`;
  }
  return `
    <button type="button" data-mood="${mood}" class="mood-gateway-chip flex-shrink-0 flex items-center gap-2 px-5 py-2.5 rounded-full bg-surface-container-low border border-outline-variant text-on-surface-variant transition-all active:scale-95">
      <span class="material-symbols-outlined text-[20px] ${meta.tint}">${meta.icon}</span>
      <span class="font-body-sm text-body-sm">${escapeHtml(meta.label)}</span>
    </button>`;
}

function trackRow(track, { showHeardBefore = false, compact = false, showArtistLink = true, showAlbumName = false } = {}) {
  const artists = (track.artists || []).join(", ") || "Unknown artist";
  const secondaryLine = showAlbumName
    ? escapeHtml(track.album_name || "Unknown album")
    : showArtistLink
      ? renderArtistNames(track.artists)
      : escapeHtml(artists);
  const size = compact ? "w-12 h-12" : "w-14 h-14";
  return `
    <div class="group flex items-center justify-between p-2 -mx-2 rounded-xl hover:bg-surface-container-high transition-colors">
      <div class="flex items-center gap-4 min-w-0 flex-1">
        <div class="${size} rounded-lg overflow-hidden flex-shrink-0" style="${albumArtStyle(track)}"></div>
        <div class="flex flex-col min-w-0">
          <span class="font-body-md text-body-md font-bold text-on-surface truncate">${escapeHtml(track.title)}</span>
          <span class="text-caption font-caption text-on-surface-variant truncate">${secondaryLine}</span>
          ${track.reason_text ? `
            <div class="flex items-center gap-1.5 mt-1">
              <span class="material-symbols-outlined text-primary text-[14px]">auto_awesome</span>
              <span class="text-[11px] font-medium text-primary uppercase tracking-wider line-clamp-2">${escapeHtml(track.reason_text)}</span>
            </div>` : ""}
        </div>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        ${showHeardBefore ? `
          <button type="button" data-heard="${escapeHtml(track.track_id)}" class="w-9 h-9 rounded-full text-on-surface-variant hover:text-primary transition-colors" aria-label="Heard it before">
            <span class="material-symbols-outlined text-[20px]">more_horiz</span>
          </button>` : ""}
        <button type="button" data-play="${escapeHtml(track.track_id)}" class="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-on-primary-container active:scale-90 transition-transform" aria-label="Play">
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1">play_arrow</span>
        </button>
      </div>
    </div>`;
}

function freshPickCard(track) {
  const artistName = (track.artists || [])[0] || "Unknown artist";
  return `
    <div class="flex-shrink-0 w-44 snap-start group cursor-pointer">
      <div class="aspect-square rounded-2xl overflow-hidden mb-3 border border-outline-variant group-hover:scale-[1.02] transition-transform duration-300" style="${albumArtStyle(track)}"></div>
      <h4 class="font-body-md text-body-md font-bold text-on-surface truncate">${escapeHtml(track.title)}</h4>
      <p class="text-caption font-caption text-on-surface-variant truncate">${artistLink(artistName)}</p>
    </div>`;
}

function artistCard(artist) {
  const genre = artist.top_genre
    ? `<span class="px-3 py-1 bg-surface-container-highest text-primary-fixed rounded-full font-label-caps text-[10px] uppercase tracking-widest border border-outline-variant">${escapeHtml(artist.top_genre)}</span>`
    : "";
  return `
    <button type="button" data-artist-id="${escapeHtml(artist.artist_id)}" class="artist-card glass-card artist-glow p-4 rounded-xl flex flex-col items-center text-center transition-all duration-300 w-full active:scale-[0.98]">
      <div class="w-[120px] h-[120px] rounded-full overflow-hidden border-2 border-outline-variant mb-4">
        <img class="w-full h-full object-cover" src="${escapeHtml(artist.image_url)}" alt="${escapeHtml(artist.image_alt || artist.name)}" loading="lazy" />
      </div>
      <h3 class="font-body-lg text-body-lg text-on-surface mb-1 truncate w-full">${escapeHtml(artist.name)}</h3>
      <p class="font-caption text-caption text-on-surface-variant mb-3">${artist.track_count} tracks in catalog</p>
      ${genre}
    </button>`;
}

function renderHomeSkeleton() {
  document.getElementById("home-content").innerHTML = `
    <div class="animate-pulse space-y-stack-lg">
      <div class="h-10 bg-surface-container rounded-full w-3/4"></div>
      <div class="bg-surface-container rounded-3xl h-80 border border-outline-variant"></div>
      <div class="h-8 bg-surface-container rounded w-1/3"></div>
      <div class="flex gap-4">
        <div class="w-44 h-44 bg-surface-container rounded-2xl"></div>
        <div class="w-44 h-44 bg-surface-container rounded-2xl"></div>
      </div>
    </div>`;
}

function renderHomeError(message) {
  document.getElementById("home-content").innerHTML = `
    <div class="text-center py-16 space-y-4">
      <span class="material-symbols-outlined text-5xl text-on-surface-variant">cloud_off</span>
      <h3 class="font-headline-md text-headline-md">Can't reach MoodAI</h3>
      <p class="text-on-surface-variant font-body-sm">${escapeHtml(message)}</p>
      <button type="button" id="retry-home" class="px-6 py-3 rounded-full bg-primary text-on-primary font-bold">Retry</button>
    </div>`;
  document.getElementById("retry-home")?.addEventListener("click", loadHome);
}

function renderEmptyDrop(activeMood) {
  return `
    <div class="flex flex-col items-center text-center py-10 space-y-6">
      <div class="relative w-40 h-40 flex items-center justify-center">
        <div class="absolute inset-0 bg-primary/10 blur-[50px] rounded-full"></div>
        <span class="material-symbols-outlined text-primary text-[96px] opacity-40 relative z-10">schedule</span>
      </div>
      <div class="space-y-2 max-w-xs">
        <h3 class="font-headline-md text-headline-md">Curating your rhythm...</h3>
        <p class="font-body-md text-on-surface-variant">Your first <span class="text-primary font-bold">Discovery Drop</span> arrives at <span class="text-primary font-bold">6:00 AM</span></p>
        <p class="font-caption text-outline italic">Pick a mood above — we'll match ${escapeHtml(formatMoodLabel(activeMood))} vibes when it lands.</p>
      </div>
    </div>`;
}

function renderHome() {
  if (state.genericHomeMode) {
    renderGenericHome();
    return;
  }
  renderPersonalizedHome();
}

function renderGenericHome() {
  const home = state.home;
  const freshPicks = home?.modules?.find((m) => m.type === "fresh_picks")?.data || {};
  const freshTracks = (freshPicks.tracks || []).slice(0, 8);

  document.getElementById("greeting").textContent = `${greeting()} · Browse`;

  document.getElementById("home-content").innerHTML = `
    <section class="space-y-4">
      <button type="button" id="back-personalized" class="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors">
        <span class="material-symbols-outlined text-[20px]">arrow_back</span>
        <span class="font-body-sm">Back to mood discovery</span>
      </button>
      <div class="bg-surface-container rounded-3xl p-6 border border-outline-variant space-y-4">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined text-primary text-3xl">explore</span>
          <div>
            <h2 class="font-headline-md text-headline-md text-on-surface">Generic Home</h2>
            <p class="font-body-sm text-on-surface-variant">Browse freely without mood-based personalization</p>
          </div>
        </div>
        <p class="font-body-md text-on-surface-variant">
          Explore the full catalog, search artists visually, or pick from popular tracks below.
        </p>
        <button type="button" id="generic-search-cta" class="w-full py-3.5 rounded-full bg-primary text-on-primary font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform">
          <span class="material-symbols-outlined">search</span>
          Search artists
        </button>
      </div>
    </section>

    <section class="space-y-4">
      <h3 class="font-headline-md text-headline-md">Popular in catalog</h3>
      <div class="flex gap-gutter overflow-x-auto hide-scrollbar snap-x pb-2">
        ${freshTracks.length ? freshTracks.map(freshPickCard).join("") : `<p class="text-on-surface-variant font-body-sm">Loading catalog picks…</p>`}
      </div>
    </section>

    <section class="bg-surface-container-low rounded-2xl p-5 border border-outline-variant text-center space-y-3">
      <span class="material-symbols-outlined text-secondary text-3xl">favorite</span>
      <p class="font-body-sm text-on-surface-variant">Want mood-matched picks again?</p>
      <button type="button" id="return-mood-flow" class="px-6 py-2.5 rounded-full border border-primary text-primary font-bold active:scale-95 transition-transform">
        Set my mood
      </button>
    </section>`;

  document.getElementById("back-personalized")?.addEventListener("click", backToPersonalizedHome);
  document.getElementById("return-mood-flow")?.addEventListener("click", backToPersonalizedHome);
  document.getElementById("generic-search-cta")?.addEventListener("click", () => setView("search"));

  bindArtistLinks(document.getElementById("home-content"));

  document.querySelectorAll("[data-play]").forEach((btn) => {
    const track = freshTracks.find((t) => t.track_id === btn.dataset.play);
    if (track) {
      btn.addEventListener("click", () => {
        state.nowPlaying = track;
        updateMiniPlayer();
        showToast(`Playing ${track.title}`);
      });
    }
  });
}

function renderPersonalizedHome() {
  const home = state.home;
  if (!home) return;

  const moodGateway = home.modules.find((m) => m.type === "mood_gateway")?.data || {};
  const discoveryDrop = home.modules.find((m) => m.type === "discovery_drop")?.data || {};
  const freshPicks = home.modules.find((m) => m.type === "fresh_picks")?.data || {};
  const options = moodGateway.options || state.moodOptions;
  const dropTracks = discoveryDrop.tracks || [];
  const freshTracks = (freshPicks.tracks || []).slice(0, 12);
  const selectedMood = state.selectedMood;
  const locked = !state.moodConfirmed;
  const lockClass = locked ? "content-locked" : "content-unlocked";

  document.getElementById("greeting").textContent = state.moodConfirmed
    ? `${greeting()} · ${formatMoodLabel(state.activeMood)}`
    : greeting();

  const dropBody = dropTracks.length
    ? dropTracks.map((t) => trackRow(t, { showHeardBefore: !locked })).join("")
    : renderEmptyDrop(selectedMood);

  document.getElementById("home-content").innerHTML = `
    <section class="space-y-4 relative">
      ${state.showFirstTimeTooltip && locked ? `
        <div id="mood-tooltip" class="absolute -top-12 left-1/2 -translate-x-1/2 z-10 px-4 py-2 bg-primary-container text-on-primary-container rounded-lg shadow-lg whitespace-nowrap">
          <span class="font-body-sm font-bold">Start here — pick how you feel</span>
        </div>` : ""}
      <p class="font-label-caps text-label-caps text-on-surface-variant tracking-widest">HOW ARE YOU FEELING?</p>
      <div id="mood-chips" class="flex gap-3 overflow-x-auto hide-scrollbar pb-2"></div>
      <button
        type="button"
        id="confirm-mood-btn"
        class="w-full py-3.5 rounded-full font-bold flex items-center justify-center gap-2 active:scale-95 transition-all ${
          locked
            ? "bg-primary text-on-primary shadow-lg shadow-primary/20"
            : "bg-surface-container-high text-primary border border-primary/40"
        }"
      >
        <span class="material-symbols-outlined text-[20px]">${locked ? "lock_open" : "check_circle"}</span>
        <span>${locked ? `Confirm ${escapeHtml(formatMoodLabel(selectedMood))} mood` : `${escapeHtml(formatMoodLabel(state.activeMood))} mood confirmed`}</span>
      </button>
      ${locked ? `<p class="text-center font-caption text-on-surface-variant">Confirm your mood to unlock personalized discovery</p>` : ""}
    </section>

    <div id="personalized-zone" class="relative space-y-stack-lg">
      ${locked ? `
        <div class="lock-overlay absolute inset-0 z-20 flex flex-col items-center justify-center px-6 text-center rounded-3xl">
          <span class="material-symbols-outlined text-primary text-4xl mb-3">lock</span>
          <p class="font-body-md font-bold text-on-surface">Personalized discovery locked</p>
          <p class="font-body-sm text-on-surface-variant mt-1 max-w-xs">Choose a mood and tap confirm above to reveal your Discovery Drop</p>
        </div>` : ""}

      <div id="personalized-content" class="${lockClass} space-y-stack-lg">
        <section>
          <div class="bg-surface-container rounded-3xl p-6 border border-outline-variant luminous-shadow relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-64 h-64 bg-primary/10 blur-[80px] rounded-full pointer-events-none"></div>
            <div class="relative z-10 space-y-6">
              <div class="flex justify-between items-start gap-4">
                <div class="space-y-1">
                  <h2 class="font-headline-md text-headline-md text-on-surface">Your Discovery Drop</h2>
                  <p class="font-body-sm text-body-sm text-on-surface-variant">Today • ${formatDateLabel()} — ${dropTracks.length || 10} fresh tracks for your ${escapeHtml(formatMoodLabel(state.moodConfirmed ? state.activeMood : selectedMood))} mood</p>
                </div>
                <span class="material-symbols-outlined text-primary text-[28px]" style="font-variation-settings: 'FILL' 1">auto_awesome</span>
              </div>
              <div class="space-y-1">${dropBody}</div>
              ${dropTracks.length && !locked ? `
                <div class="pt-2 border-t border-outline-variant flex justify-between items-center gap-3">
                  <button type="button" id="play-all-drop" class="px-5 py-2 rounded-full bg-primary text-on-primary font-bold text-sm active:scale-95 transition-transform">Play all</button>
                  <span class="text-caption font-label-caps text-on-surface-variant">${dropTracks.length} tracks</span>
                </div>` : ""}
            </div>
          </div>
        </section>

        <section class="space-y-4">
          <div class="flex justify-between items-center">
            <h3 class="font-headline-md text-headline-md">Fresh Picks</h3>
            <span class="material-symbols-outlined text-on-surface-variant">chevron_right</span>
          </div>
          <div class="flex gap-gutter overflow-x-auto hide-scrollbar snap-x pb-2">
            ${freshTracks.length ? freshTracks.map(freshPickCard).join("") : `<p class="text-on-surface-variant font-body-sm">Finding more tracks for your mood…</p>`}
          </div>
        </section>
      </div>
    </div>

    <section class="pt-2 pb-4">
      <div class="bg-surface-container-low rounded-2xl p-5 border border-outline-variant text-center space-y-3">
        <p class="font-body-sm text-on-surface-variant">Not finding what you want in personalized picks?</p>
        <button type="button" id="generic-home-cta" class="w-full py-3 rounded-full border border-outline-variant text-on-surface hover:border-primary hover:text-primary font-bold active:scale-95 transition-all flex items-center justify-center gap-2">
          <span class="material-symbols-outlined text-[20px]">home</span>
          Browse generic home
        </button>
      </div>
    </section>`;

  document.getElementById("mood-chips").innerHTML = options
    .map((m) => moodChip(m, m === selectedMood))
    .join("");

  bindHomeEvents(dropTracks, freshTracks, locked);
}

function bindHomeEvents(dropTracks, freshTracks, locked = false) {
  document.querySelectorAll("[data-mood]").forEach((btn) => {
    btn.addEventListener("click", () => selectMood(btn.dataset.mood));
  });

  document.getElementById("confirm-mood-btn")?.addEventListener("click", () => {
    if (!state.moodConfirmed) confirmMood();
  });

  document.getElementById("generic-home-cta")?.addEventListener("click", openGenericHome);

  if (locked) return;

  document.querySelectorAll("[data-heard]").forEach((btn) => {
    const track = dropTracks.find((t) => t.track_id === btn.dataset.heard);
    if (track) btn.addEventListener("click", () => openHeardBefore(track));
  });

  document.querySelectorAll("[data-play]").forEach((btn) => {
    const track = [...dropTracks, ...freshTracks].find((t) => t.track_id === btn.dataset.play);
    if (track) {
      btn.addEventListener("click", () => {
        state.nowPlaying = track;
        updateMiniPlayer();
        showToast(`Playing ${track.title}`);
      });
    }
  });

  document.getElementById("play-all-drop")?.addEventListener("click", () => {
    if (dropTracks[0]) {
      state.nowPlaying = dropTracks[0];
      updateMiniPlayer();
      showToast(`Playing ${dropTracks[0].title}`);
    }
  });

  bindArtistLinks(document.getElementById("home-content"));
}

function renderSearch() {
  const grid = document.getElementById("search-results");
  const empty = document.getElementById("search-empty");
  const loading = document.getElementById("search-loading");

  loading.classList.toggle("hidden", !state.searchLoading);
  empty.classList.add("hidden");
  grid.innerHTML = "";

  if (state.searchLoading) return;

  if (!state.searchQuery) {
    empty.classList.remove("hidden");
    empty.innerHTML = `
      <span class="material-symbols-outlined text-5xl text-on-surface-variant mb-4">search</span>
      <p class="font-body-md text-on-surface-variant">Search artists visually</p>
      <p class="font-caption text-outline mt-2">Recognize faces, not text lists</p>`;
    return;
  }

  if (!state.searchResults.length) {
    empty.classList.remove("hidden");
    empty.innerHTML = `
      <span class="material-symbols-outlined text-5xl text-on-surface-variant mb-4">person_off</span>
      <p class="font-body-md text-on-surface-variant">No artists found for "${escapeHtml(state.searchQuery)}"</p>`;
    return;
  }

  grid.innerHTML = state.searchResults.map(artistCard).join("");
  bindArtistLinks(document.getElementById("search-results"));
}

function updateMiniPlayer() {
  const bar = document.getElementById("mini-player");
  if (!state.nowPlaying) {
    bar.classList.add("translate-y-full", "opacity-0", "pointer-events-none");
    return;
  }
  const track = state.nowPlaying;
  bar.classList.remove("translate-y-full", "opacity-0", "pointer-events-none");
  document.getElementById("mini-player-art").style.cssText = albumArtStyle(track);
  document.getElementById("mini-player-title").textContent = track.title;
  const artistEl = document.getElementById("mini-player-artist");
  const artistNames = track.artists || [];
  if (artistNames.length === 1) {
    artistEl.innerHTML = artistLink(artistNames[0]);
    bindArtistLinks(artistEl);
  } else {
    artistEl.textContent = artistNames.join(", ") || "Unknown artist";
  }
}

function bindShellEvents() {
  document.getElementById("header-back-btn")?.addEventListener("click", goHome);

  document.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.nav === "home") {
        goHome();
        return;
      }
      setView(btn.dataset.nav);
    });
  });

  const searchInput = document.getElementById("search-input");
  let searchTimer;
  searchInput?.addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    const value = event.target.value;
    searchTimer = setTimeout(() => {
      state.searchQuery = value;
      searchArtists(value);
    }, 350);
  });

  document.getElementById("sheet-backdrop")?.addEventListener("click", closeHeardBefore);
  document.getElementById("heard-before-cancel")?.addEventListener("click", closeHeardBefore);
  document.getElementById("heard-before-confirm")?.addEventListener("click", confirmHeardBefore);

  const header = document.getElementById("app-header");
  window.addEventListener("scroll", () => {
    header?.classList.toggle("shadow-md", window.scrollY > 20);
  });
}

async function init() {
  bindShellEvents();
  setView("home");

  try {
    const health = await fetch("/healthz").then((response) => response.json());
    if (health.product !== "MoodAI Spotify" || health.phase !== "3") {
      showWrongAppScreen();
      return;
    }
    if (health.mode === "demo") {
      document.getElementById("greeting").textContent = `${greeting()} · Demo catalog`;
    }
  } catch {
    showWrongAppScreen(
      "Could not verify MoodAI API. You may be on the wrong port (e.g. 8000 is often another app)."
    );
    return;
  }

  await loadHome();
}

function showWrongAppScreen(message) {
  const text =
    message ||
    "This URL is not MoodAI. Port 8000 may be another project (e.g. AI Travel Planner). Run: python scripts/run_dev.py and open http://127.0.0.1:8010/";
  document.getElementById("home-content").innerHTML = `
    <div class="text-center py-16 space-y-4 px-4">
      <span class="material-symbols-outlined text-5xl text-tertiary">wrong_location</span>
      <h3 class="font-headline-md text-headline-md">Wrong app on this port</h3>
      <p class="text-on-surface-variant font-body-sm">${escapeHtml(text)}</p>
      <a href="http://127.0.0.1:8010/" class="inline-block px-6 py-3 rounded-full bg-primary text-on-primary font-bold">Open MoodAI on :8010</a>
    </div>`;
  document.getElementById("view-search").classList.add("hidden");
  document.getElementById("view-library").classList.add("hidden");
  document.getElementById("view-artist").classList.add("hidden");
}

init();
