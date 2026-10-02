// Kaagaz web app: state and flows. Words live in i18n.js, HTML in render.js.
import { TABLE, errorText, getLang, pick, setLang, t } from "./i18n.js";
import * as R from "./render.js";

const API = (window.KAAGAZ_API || "").replace(/\/$/, "");
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const saved = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};
const params = new URLSearchParams(location.search);
const state = {
  token: saved.get("kaagaz.token"),
  role: ["parent", "son"].includes(params.get("role")) ? params.get("role") : saved.get("kaagaz.role") || "parent",
  health: null, data: null, card: null, inputId: null, inputGen: 0, toldSon: false,
  progress: null,            // {kind, stage, done, error} of the input being read
  rec: null,                 // {recorder, stream, startedAt, mode: "hold"|"tap", timer, limit}
  seen: new Set(), primed: false, sheetReturn: null, laterUntil: null,
};

function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, 5000);
}

async function api(path, opts = {}, retried = false) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let body = opts.body;
  if (opts.json !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.json); }
  let r;
  try { r = await fetch(API + path, { method: opts.method || "GET", headers, body }); }
  catch { const e = new Error(t("network")); e.network = true; throw e; }
  if (r.status === 401 && !retried && path !== "/api/households") {
    state.token = null;
    await ensureHousehold();
    return api(path, opts, true);
  }
  if (!r.ok) {
    let d = {};
    try { d = await r.json(); } catch { /* not json */ }
    const e = new Error(errorText(d.detail, t("failed")));
    e.status = r.status;
    e.detail = d.detail;
    throw e;
  }
  return (r.headers.get("content-type") || "").includes("json") ? r.json() : r.blob();
}

// ---------- language and role ----------
function applyLang() {
  $$("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  $$("[data-t-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.tPlaceholder); });
  $$("[data-t-aria]").forEach((el) => el.setAttribute("aria-label", t(el.dataset.tAria)));
  $$("#lang [data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === getLang())));
  document.title = getLang() === "hi" ? "काग़ज़ · Kaagaz" : "Kaagaz";
  renderHello();
  renderSpeak();
  renderMode();
  if (state.data) { renderItems(); renderInbox(); }
  if (state.progress) renderSteps();
  if (state.card) { state.card.actions = editedActions(); renderCard(); }
}

function switchLang(l) {
  if (l === getLang()) return;
  setLang(l);
  applyLang();
}

function setRole(role) {
  state.role = role;
  saved.set("kaagaz.role", role);
  $$("#roles [data-role]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.role === role)));
  document.body.dataset.role = role;
  state.primed = false;
  renderHello();
  if (state.health) refresh();
}

function renderHello() {
  $("#hello").textContent = t(state.role === "son" ? "hello_son" : "hello_parent");
  const active = (state.data?.obligations || []).filter((o) => o.status === "active").length;
  $("#count").textContent = state.data ? t("count", active) : "";
}

function renderMode() {
  const mode = state.health?.mode;
  const chip = $("#mode-chip");
  chip.hidden = !mode;
  if (!mode) return;
  chip.textContent = t(`mode_${mode}`);
  chip.className = `chip ${mode}`;
}

// ---------- server ----------
async function wake() {
  const t0 = Date.now();
  for (;;) {
    try {
      const r = await fetch(API + "/api/health");
      if (r.ok) { state.health = await r.json(); break; }
    } catch { /* still asleep */ }
    if (Date.now() - t0 > 120000) {
      $("#waking-text").dataset.t = "waking_failed";
      $("#waking-text").textContent = t("waking_failed");
      $(".waking-bar").hidden = true;
      return false;
    }
    await sleep(3000);
  }
  document.body.classList.remove("asleep");
  renderMode();
  return true;
}

async function ensureHousehold() {
  if (state.token) return;
  const r = await api("/api/households", { method: "POST" });
  state.token = r.token;
  saved.set("kaagaz.token", r.token);
}

async function refresh() {
  if (!state.token) return;
  try { state.data = await api(`/api/state?role=${state.role}`); }
  catch (e) { console.warn(e); return; }
  renderItems();
  renderInbox();
  renderHello();
  const fresh = state.data.inbox.filter((n) => !n.read && !state.seen.has(n.id));
  state.data.inbox.forEach((n) => state.seen.add(n.id));
  if (state.primed && fresh.length) {
    toast(pick(fresh[0], "text"));
    navigator.vibrate?.(200);
  }
  state.primed = true;
}

function renderItems() { $("#items").innerHTML = R.items(state.data); }

function renderInbox() {
  const { unread } = state.data;
  $("#unread").hidden = !unread;
  $("#unread").textContent = unread;
  $("#unread").setAttribute("aria-label", t("unread", unread));
  $("#inbox").innerHTML = R.inbox(state.data, state.role);
}

// ---------- voice out ----------
let audio;
async function speak(text) {
  if (!text) return;
  const lang = getLang();
  if (state.health?.tts === "elevenlabs") {
    try {
      const blob = await api("/api/tts", { method: "POST", json: { text, lang } });
      audio?.pause();
      audio = new Audio(URL.createObjectURL(blob));
      await audio.play();
      return;
    } catch (e) { console.warn("server voice failed, using browser voice", e); }
  }
  if ("speechSynthesis" in window) {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === "hi" ? "hi-IN" : "en-IN";
    const v = speechSynthesis.getVoices().find((x) => x.lang?.toLowerCase().startsWith(lang));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  }
}

// ---------- sending ----------
function renderSteps() {
  const p = state.progress;
  const el = $("#steps");
  el.hidden = !p;
  if (!p) return;
  el.innerHTML = R.steps(p.kind, p.stage, p.done)
    + (p.error ? `<li class="err" role="alert">${R.esc(errorText(p.error, t("failed")))}</li>` : "");
}

async function sendInput(form, kind) {
  // Only the newest input may show a card: an older one finishing late would put its card on screen
  // while "Yes, save it" confirmed the newer input — one record mixing two papers.
  const gen = ++state.inputGen;
  const stale = () => gen !== state.inputGen;
  hideCard();
  state.progress = { kind, stage: "sent", done: false, error: null };
  renderSteps();
  $("#steps").scrollIntoView({ behavior: "smooth", block: "center" });
  form.append("role", state.role);
  try {
    const { input_id: id } = await api("/api/inputs", { method: "POST", body: form });
    const t0 = Date.now();
    for (;;) {
      await sleep(2000);
      if (stale()) return;
      const p = await api(`/api/inputs/${id}`);
      if (stale()) return;
      state.progress.stage = p.stage || state.progress.stage;
      if (p.status === "ready") {
        state.progress = null;
        renderSteps();
        state.inputId = id;
        showCard(p.card);
        return;
      }
      if (p.status === "failed") { const e = new Error(); e.detail = p.message; throw e; }
      renderSteps();
      if (Date.now() - t0 > 300000) { const e = new Error(); e.detail = t("too_slow"); throw e; }
    }
  } catch (e) {
    if (stale()) return;
    const detail = e.network ? t("network") : e.detail ?? e.message;
    state.progress.error = detail;
    renderSteps();
    toast(errorText(detail, t("failed")));
  }
}

async function shrink(blob) {
  const bmp = await createImageBitmap(blob).catch(() => null);
  if (!bmp) return blob;   // can't decode here (e.g. HEIC on desktop): send as is; the server caps size
  const scale = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale);
  c.height = Math.round(bmp.height * scale);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return new Promise((r) => c.toBlob(r, "image/jpeg", 0.85));
}

async function sendPhoto(blob) {
  const f = new FormData();
  f.append("kind", "photo");
  f.append("file", await shrink(blob), "paper.jpg");
  await sendInput(f, "photo");
}

// ---------- speak button: hold to talk, or tap to start and tap to send ----------
function renderSpeak() {
  const r = state.rec;
  const key = !r ? "speak" : r.mode === "tap" ? "speak_tap" : "speak_hold";
  $("#speak-label").textContent = t(key);
  $("#speak-sr").textContent = t(key);
  $("#btn-speak").classList.toggle("rec", !!r);
  $("#btn-speak").setAttribute("aria-pressed", String(!!r));
  $("#speak-timer").hidden = !r;
}

async function startRecording(mode) {
  if (state.rec) return;
  state.rec = { mode, startedAt: Date.now(), starting: true };
  renderSpeak();
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch { state.rec = null; renderSpeak(); toast(t("mic_denied")); return; }
  const r = state.rec;
  if (!r) { stream.getTracks().forEach((x) => x.stop()); return; }
  const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((x) => window.MediaRecorder?.isTypeSupported(x)) || "";
  const recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
  const chunks = [];
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  recorder.onstop = async () => {
    stream.getTracks().forEach((x) => x.stop());
    clearTimeout(r.limit);
    clearInterval(r.timer);
    state.rec = null;
    renderSpeak();
    const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
    if (blob.size < 1000) { toast(t("heard_nothing")); return; }
    const f = new FormData();
    f.append("kind", "voice");
    f.append("file", blob, (recorder.mimeType || "").includes("mp4") ? "voice.m4a" : "voice.webm");
    await sendInput(f, "voice");
  };
  recorder.start();
  Object.assign(r, { recorder, starting: false, startedAt: Date.now() });
  const tick = () => {
    const s = Math.floor((Date.now() - r.startedAt) / 1000);
    $("#speak-timer").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  };
  tick();
  r.timer = setInterval(tick, 250);
  r.limit = setTimeout(() => stopRecording(), 30000);
  if (r.releaseEarly) stopRecording();   // the finger came up while the microphone was still opening
}

function stopRecording() {
  const r = state.rec;
  if (!r) return;
  if (r.starting) { r.releaseEarly = true; return; }
  if (r.recorder?.state === "recording") r.recorder.stop();
}

function wireSpeak() {
  const btn = $("#btn-speak");
  let downAt = 0;
  let startedHere = false;
  btn.addEventListener("pointerdown", (e) => {
    if (e.button > 0) return;
    btn.setPointerCapture?.(e.pointerId);
    downAt = Date.now();
    if (state.rec) { startedHere = false; stopRecording(); return; }   // second tap sends
    startedHere = true;
    startRecording("hold");
  });
  btn.addEventListener("pointerup", () => {
    if (!startedHere || !state.rec) return;
    startedHere = false;
    if (Date.now() - downAt > 600) stopRecording();                  // held: let go to send
    else { state.rec.mode = "tap"; renderSpeak(); }                    // tapped: keep listening
  });
  btn.addEventListener("pointercancel", () => { if (startedHere) stopRecording(); startedHere = false; });
  btn.addEventListener("contextmenu", (e) => e.preventDefault());
  btn.addEventListener("keydown", (e) => {
    if ((e.key !== "Enter" && e.key !== " ") || e.repeat) return;
    e.preventDefault();
    if (state.rec) stopRecording();
    else startRecording("tap");
  });
}

// ---------- the card ----------
function renderCard() {
  const el = $("#card");
  el.innerHTML = R.card(state.card, state.data?.today, { toldSon: state.toldSon });
  el.hidden = false;
}

function showCard(card) {
  state.card = card;
  state.toldSon = false;
  renderCard();
  $("#card").scrollIntoView({ behavior: "smooth", block: "start" });
  $("#card").focus({ preventScroll: true });
  speak(pick(card, "readback"));
}

function hideCard() {
  $("#card").hidden = true;
  state.card = null;
}

function editedActions() {
  const acts = structuredClone(state.card.actions);
  $$("#card [data-k]").forEach((inp) => {
    const a = acts[Number(inp.dataset.i)];
    const k = inp.dataset.k;
    if (k === "escalate") a.escalate = inp.checked;
    else if (k === "amount_inr") a.amount_inr = inp.value === "" ? null : Number(inp.value);
    else a[k] = inp.value.trim() || null;
  });
  return acts;
}

async function confirmCard() {
  const btn = $("#c-ok");
  if (btn) btn.disabled = true;   // one tap, one save (the server also guards against repeats)
  try {
    const actions = editedActions().filter((a) => R.CHANGES.includes(a.tool));
    const { results } = await api(`/api/inputs/${state.inputId}/confirm`, { method: "POST", json: { actions, role: state.role } });
    $("#card").classList.add("thunk");
    await sleep(320);
    $("#card").classList.remove("thunk");
    hideCard();
    toast(t("saved"));
    refresh();
    const offer = (results || []).find((x) => x.repeat_offer)?.repeat_offer;
    if (offer) openSheet(R.repeatSheet(offer));
  } catch (e) {
    if (btn) btn.disabled = false;
    toast(e.message);
  }
}

async function warnSon() {
  const btn = $("#c-son");
  if (btn) btn.disabled = true;
  try {
    await api(`/api/inputs/${state.inputId}/warn-son`, { method: "POST" });
    state.toldSon = true;
    if (btn) btn.textContent = t("told_son");
    toast(t("told_son"));
  } catch (e) {
    if (btn) btn.disabled = false;
    toast(e.message);
  }
}

// ---------- sheets ----------
function openSheet(html) {
  const sheet = $("#sheet");
  state.sheetReturn = document.activeElement;
  state.laterUntil = null;
  sheet.querySelector(".sheet-panel").innerHTML = html;
  sheet.hidden = false;
  sheet.querySelector(".sheet-panel button:not(.sheet-x)")?.focus();
}

function closeSheet() {
  const sheet = $("#sheet");
  if (sheet.hidden) return;
  sheet.hidden = true;
  state.sheetReturn?.focus?.();
}

async function onSheetClick(e) {
  const b = e.target.closest("button,[data-close]");
  if (!b) return;
  if (b.hasAttribute("data-close")) { closeSheet(); return; }
  try {
    if (b.dataset.until) {
      state.laterUntil = b.dataset.until;
      $$("#sheet .chip-btn").forEach((c) => c.setAttribute("aria-pressed", String(c === b)));
      $("#later-date").value = "";
    } else if (b.dataset.laterOk) {
      const until = $("#later-date").value || state.laterUntil;
      if (!until) { toast(t("pick_date")); return; }
      b.disabled = true;
      await api(`/api/obligations/${b.dataset.laterOk}/snooze`, { method: "POST", json: { until, role: state.role } });
      closeSheet();
      toast(t("snoozed", R.dateLong(until)));
      refresh();
    } else if (b.dataset.repeat) {
      b.disabled = true;
      const r = await api(`/api/obligations/${b.dataset.repeat}/repeat`, { method: "POST", json: { role: state.role } });
      closeSheet();
      toast(t("repeat_saved", R.dateLong(r.due_date)));
      refresh();
    }
  } catch (err) {
    b.disabled = false;
    toast(err.message);
  }
}

// ---------- push ----------
function b64ToBytes(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) { toast(t("push_unsupported")); return; }
  if (!state.health?.push_key) { toast(t("push_unavailable")); return; }
  if ((await Notification.requestPermission()) !== "granted") { toast(t("push_denied")); return; }
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = (await reg.pushManager.getSubscription())
      || (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(state.health.push_key) }));
    await api("/api/push/subscribe", { method: "POST", json: { role: state.role, subscription: sub.toJSON(), lang: getLang() } });
    toast(t(state.role === "son" ? "push_done_son" : "push_done_parent"));
  } catch (e) { toast(e.message || t("push_unavailable")); }
}

// ---------- wiring ----------
function wire() {
  $$("#lang [data-lang]").forEach((b) => b.addEventListener("click", () => switchLang(b.dataset.lang)));
  $$("#roles [data-role]").forEach((b) => b.addEventListener("click", () => setRole(b.dataset.role)));
  $("#intro-close").addEventListener("click", () => { $("#intro").hidden = true; saved.set("kaagaz.intro", "1"); });
  wireSpeak();
  $("#btn-scan").addEventListener("click", () => $("#file").click());
  $("#file").addEventListener("change", (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) sendPhoto(f); });
  $("#btn-type").addEventListener("click", () => {
    const box = $("#ask-box");
    box.hidden = !box.hidden;
    $("#btn-type").setAttribute("aria-expanded", String(!box.hidden));
    if (!box.hidden) $("#ask-text").focus();
  });
  $("#ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("#ask-text").value.trim();
    if (!text) return;
    $("#ask-text").value = "";
    const f = new FormData();
    f.append("kind", "text");
    f.append("text", text);
    sendInput(f, "text");
  });
  $$("#samples [data-sample]").forEach((b) => b.addEventListener("click", async () => {
    try {
      const r = await fetch(`samples/${b.dataset.sample}.jpg`);
      if (!r.ok) throw new Error();
      await sendPhoto(await r.blob());
    } catch { toast(t("network")); }
  }));
  $("#card").addEventListener("click", (e) => {
    const id = e.target.closest("button")?.id;
    if (id === "c-ok") confirmCard();
    else if (id === "c-edit") $("#card input:not([type=checkbox])")?.focus();
    else if (id === "c-play") speak(pick(state.card, "readback"));
    else if (id === "c-son") warnSon();
    else if (id === "c-no") hideCard();
  });
  $("#items").addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.later) { openSheet(R.laterSheet(b.dataset.later, state.data.today)); return; }
    if (!b.dataset.done) return;
    b.disabled = true;
    try {
      const r = await api(`/api/obligations/${b.dataset.done}/done`, { method: "POST", json: { role: state.role } });
      toast(t("done_toast"));
      await refresh();
      if (r.repeat_offer) openSheet(R.repeatSheet(r.repeat_offer));
    } catch (err) { b.disabled = false; toast(err.message); }
  });
  $("#inbox").addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const note = state.data?.inbox.find((n) => n.id === (b.dataset.play || b.dataset.read));
    if (!note) return;
    if (b.dataset.play) speak(pick(note, "text"));
    try { await api(`/api/notifications/${encodeURIComponent(note.id)}/read`, { method: "POST" }); refresh(); }
    catch (err) { console.warn(err); }
  });
  $("#btn-push").addEventListener("click", enablePush);
  $("#sheet").addEventListener("click", onSheetClick);
  $("#sheet").addEventListener("change", (e) => {
    if (e.target.id !== "later-date") return;
    state.laterUntil = null;
    $$("#sheet .chip-btn").forEach((c) => c.setAttribute("aria-pressed", "false"));
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });
}

async function init() {
  if (["localhost", "127.0.0.1"].includes(location.hostname)) window.__i18n = { ...TABLE, errorText };
  setLang(getLang());
  wire();
  setRole(state.role);
  $("#intro").hidden = saved.get("kaagaz.intro") === "1";
  applyLang();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
  if (!(await wake())) return;
  try { await ensureHousehold(); } catch (e) { toast(e.message); return; }
  await refresh();
  setInterval(() => { if (document.visibilityState === "visible") refresh(); }, 5000);
}

init();
