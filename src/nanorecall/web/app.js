// NanoRecall Web Application Controller
// 100% Client-side interaction with local NanoRecall HTTP API

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchInput");
  const clearSearch = document.getElementById("clearSearch");
  const cardsGrid = document.getElementById("cardsGrid");
  const resultsCount = document.getElementById("resultsCount");
  const resultsTitle = document.getElementById("resultsTitle");
  const statFrames = document.getElementById("statFrames");
  const statDbSize = document.getElementById("statDbSize");
  const btnCaptureNow = document.getElementById("btnCaptureNow");
  const btnRefresh = document.getElementById("btnRefresh");
  const imageModal = document.getElementById("imageModal");
  const modalImg = document.getElementById("modalImg");
  const modalMeta = document.getElementById("modalMeta");
  const modalClose = document.getElementById("modalClose");

  let searchTimeout = null;

  // Load initial statistics and recent captures
  async function loadStats() {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      statFrames.textContent = data.total_frames || 0;
      statDbSize.textContent = `${data.file_size_kb || 0} KB`;
    } catch (err) {
      console.warn("Could not load stats:", err);
    }
  }

  async function loadRecent() {
    try {
      const res = await fetch("/api/recent");
      const items = await res.json();
      renderCards(items, "Recent Screen Memories");
    } catch (err) {
      console.warn("Could not load recent items:", err);
    }
  }

  async function executeSearch(query) {
    if (!query || !query.trim()) {
      clearSearch.style.display = "none";
      loadRecent();
      return;
    }

    clearSearch.style.display = "block";
    resultsTitle.textContent = `Search Results for "${query}"`;

    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      const items = await res.json();
      renderCards(items, `Search Results for "${query}"`, true);
    } catch (err) {
      console.error("Search failed:", err);
    }
  }

  function renderCards(items, title, isSearch = false) {
    resultsTitle.textContent = title;
    resultsCount.textContent = `${items.length} items`;
    cardsGrid.innerHTML = "";

    if (!items || items.length === 0) {
      cardsGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 2.5rem; margin-bottom: 12px;">🔍</div>
          <h3>No memory matches found</h3>
          <p style="font-size: 0.85rem; margin-top: 6px;">Try another query or click "Capture Now" to record your screen.</p>
        </div>
      `;
      return;
    }

    items.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = `memory-card ${isSearch && index === 0 ? "highlight" : ""}`;

      const scorePercent = item.score ? Math.min(100, Math.max(0, Math.round(item.score * 100))) : null;
      const scoreBadge = scorePercent !== null ? `<span class="score-badge">${scorePercent}% Match</span>` : "";

      const imgSrc = item.thumb_path ? `/image?path=${encodeURIComponent(item.thumb_path)}` : "/placeholder.png";

      card.innerHTML = `
        <div class="card-media">
          <img src="${imgSrc}" alt="${escapeHtml(item.window_title || 'Screen Capture')}" loading="lazy">
          ${scoreBadge}
        </div>
        <div class="card-body">
          <div class="card-meta-row">
            <span class="app-tag">${escapeHtml(item.app_name || 'App')}</span>
            <span>${escapeHtml(formatTime(item.timestamp))}</span>
          </div>
          <h4 class="card-title">${escapeHtml(item.window_title || 'Desktop Window')}</h4>
          <p class="card-snippet">${escapeHtml(item.snippet || 'No text snippet available')}</p>
        </div>
      `;

      card.addEventListener("click", () => {
        const fullImgSrc = item.image_path ? `/image?path=${encodeURIComponent(item.image_path)}` : imgSrc;
        modalImg.src = fullImgSrc;
        modalMeta.innerHTML = `
          <strong>${escapeHtml(item.app_name)}</strong> — ${escapeHtml(item.window_title)}<br>
          <span style="font-size: 0.8rem; color: #94a3b8;">Captured: ${escapeHtml(item.timestamp)}</span>
          <p style="margin-top: 8px;">${escapeHtml(item.snippet)}</p>
        `;
        imageModal.classList.add("open");
      });

      cardsGrid.appendChild(card);
    });
  }

  function formatTime(isoStr) {
    if (!isoStr) return "";
    try {
      const d = new Date(isoStr.replace("_", "T"));
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Search input typing with debounce
  searchInput.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      executeSearch(e.target.value);
    }, 180);
  });

  clearSearch.addEventListener("click", () => {
    searchInput.value = "";
    executeSearch("");
  });

  // Modal close
  modalClose.addEventListener("click", () => imageModal.classList.remove("open"));
  window.addEventListener("click", (e) => {
    if (e.target === imageModal) imageModal.classList.remove("open");
  });

  // Buttons
  btnRefresh.addEventListener("click", () => {
    loadStats();
    loadRecent();
  });

  btnCaptureNow.addEventListener("click", async () => {
    btnCaptureNow.textContent = "Capturing...";
    btnCaptureNow.disabled = true;
    try {
      await fetch("/api/capture", { method: "POST" });
      await loadStats();
      await loadRecent();
    } catch (err) {
      alert("Capture error: " + err);
    } finally {
      btnCaptureNow.textContent = "📸 Capture Now";
      btnCaptureNow.disabled = false;
    }
  });

  // Initialize
  loadStats();
  loadRecent();
});
