/* ── State ─────────────────────────────────────────────────────────────────── */
let totalVehicles = 0;
let totalRevenue  = 0;

/* ── DOM refs ──────────────────────────────────────────────────────────────── */
const fileInput     = document.getElementById("fileInput");
const dropZone      = document.getElementById("dropZone");
const previewWrap   = document.getElementById("previewWrap");
const previewImg    = document.getElementById("previewImg");
const scanBtn       = document.getElementById("scanBtn");
const placeholder   = document.getElementById("placeholder");
const loader        = document.getElementById("loader");
const resultContent = document.getElementById("resultContent");
const errorBox      = document.getElementById("errorBox");

/* ── Live clock ────────────────────────────────────────────────────────────── */
function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString("en-PK", { hour12: false });
}
updateClock();
setInterval(updateClock, 1000);

/* ── File input handling ───────────────────────────────────────────────────── */
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "var(--purple)";
  dropZone.style.background  = "var(--purple-glow)";
});

dropZone.addEventListener("dragleave", () => {
  dropZone.style.borderColor = "";
  dropZone.style.background  = "";
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "";
  dropZone.style.background  = "";
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewWrap.style.display = "block";
    scanBtn.disabled = false;
    resetResults();
  };
  reader.readAsDataURL(file);
}

/* ── Scan button ───────────────────────────────────────────────────────────── */
scanBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  scanBtn.disabled = true;
  showLoader();

  const formData = new FormData();
  formData.append("image", file);

  try {
    const res  = await fetch("/process", { method: "POST", body: formData });
    const data = await res.json();
    showResult(data);
  } catch (err) {
    showError("Network error: " + err.message);
  } finally {
    scanBtn.disabled = false;
  }
});

/* ── UI helpers ────────────────────────────────────────────────────────────── */
function resetResults() {
  placeholder.style.display   = "flex";
  loader.style.display        = "none";
  resultContent.style.display = "none";
  errorBox.style.display      = "none";
}

function showLoader() {
  placeholder.style.display   = "none";
  loader.style.display        = "flex";
  resultContent.style.display = "none";
  errorBox.style.display      = "none";
}

function showResult(data) {
  loader.style.display = "none";

  if (data.error) {
    showError(data.error);
    return;
  }

  // Populate result fields
  document.getElementById("rPlate").textContent = data.plate;
  document.getElementById("rTime").textContent  = data.entry_time;
  document.getElementById("rFee").textContent   = data.fee;

  // Images — add cache-busting timestamp so refreshed images load
  const ts = Date.now();
  document.getElementById("annoImg").src = data.anno_url + "?t=" + ts;
  document.getElementById("cropImg").src = data.crop_url + "?t=" + ts;

  // Slip
  const slipWrap   = document.getElementById("slipWrap");
  const slipImg    = document.getElementById("slipImg");
  const downloadBtn = document.getElementById("downloadBtn");
  slipImg.src          = data.slip_url + "?t=" + ts;
  downloadBtn.href     = data.slip_url;
  downloadBtn.download = "parking_slip.png";
  slipWrap.style.display = "block";

  resultContent.style.display = "block";
  errorBox.style.display      = "none";

  // Update dashboard counters
  totalVehicles += 1;
  totalRevenue  += 30;
  document.getElementById("totalVehicles").textContent = totalVehicles;
  document.getElementById("lastPlate").textContent     = data.plate;
  document.getElementById("revenue").textContent       = "Rs. " + totalRevenue;
}

function showError(msg) {
  loader.style.display        = "none";
  resultContent.style.display = "none";
  placeholder.style.display   = "none";
  errorBox.textContent        = "⚠  " + msg;
  errorBox.style.display      = "block";
}
