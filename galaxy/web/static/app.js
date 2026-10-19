"use strict";

// ------------------------------------------------------------------ 状態
const S = {
  map: null,
  state: null,
  entries: [],
  next: 0,
  seen: -1,
  minImp: 3,
  mode: "owner",
  view: { k: 1, px: 0, py: 0 },
  selectedFaction: null,
  selectedPlanet: null,
  history: [],
  current: null,
  playing: false,
  busy: false,
  tab: "chronicle",
};
const MAX_FEED = 600;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}
const post = (path) => api(path, { method: "POST" });

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function color(fid, alpha = 1) {
  if (fid === null || fid === undefined) return `rgba(110,120,140,${alpha * 0.55})`;
  const h = (fid * 137.508) % 360;
  return `hsla(${h.toFixed(0)}, 62%, 58%, ${alpha})`;
}

// ------------------------------------------------------------------ 参照リンク
function ref(r, label) {
  if (!r) return "<span class='muted'>—</span>";
  const dead = r.type === "person" && r.alive === false ? " dead" : "";
  const fell = r.type === "faction" && r.alive === false ? " dead" : "";
  const mark = r.type === "person" && r.alive === false ? "†" : "";
  return `<span class="ref ${r.type}${dead}${fell}" data-ref="${r.type}" data-id="${r.id}">${esc(label ?? r.name)}${mark}</span>`;
}
const refs = (list) => (list && list.length ? list.map((r) => ref(r)).join("、") : "<span class='muted'>—</span>");

function linkify(text, list) {
  let html = esc(text);
  if (!list || !list.length) return html;
  const uniq = new Map();
  for (const r of list) if (r && r.name && !uniq.has(r.name)) uniq.set(r.name, r);
  const names = [...uniq.keys()].sort((a, b) => b.length - a.length);
  if (!names.length) return html;
  const pattern = new RegExp(names.map((n) => esc(n).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g");
  return html.replace(pattern, (m) => {
    const name = [...uniq.keys()].find((n) => esc(n) === m);
    const r = uniq.get(name);
    return `<span class="ref ${r.type}" data-ref="${r.type}" data-id="${r.id}">${m}</span>`;
  });
}

document.addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-ref]");
  if (!el) return;
  ev.preventDefault();
  openDetail(el.dataset.ref, Number(el.dataset.id));
});

// ------------------------------------------------------------------ 星図
const svg = $("#map");
const NS = "http://www.w3.org/2000/svg";

function mapSize() {
  const r = svg.getBoundingClientRect();
  return { w: r.width, h: r.height, R: Math.min(r.width, r.height) / 2.25 };
}
function toScreen(x, y, sz) {
  return [sz.w / 2 + x * sz.R * S.view.k + S.view.px, sz.h / 2 + y * sz.R * S.view.k + S.view.py];
}
function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

function starFill(p) {
  if (S.mode === "unrest") {
    if (p.owner === null) return "rgba(110,120,140,.4)";
    const u = Math.min(100, p.unrest) / 100;
    return `hsl(${(120 - u * 120).toFixed(0)}, 70%, ${50 + u * 8}%)`;
  }
  if (S.mode === "war") {
    const f = S.state && S.state.factions.find((x) => x.id === p.owner);
    return f && f.at_war ? color(p.owner) : "rgba(110,120,140,.35)";
  }
  return color(p.owner);
}

function drawMap() {
  if (!S.map) return;
  const sz = mapSize();
  svg.innerHTML = "";
  const k = S.view.k;
  const g = el("g", {}, svg);
  // 地域の境界
  for (const reg of S.map.regions.slice(0, -1)) {
    const [cx, cy] = toScreen(0, 0, sz);
    el("circle", { cx, cy, r: reg.radius * sz.R * k, class: "region-ring" }, g);
    const t = el("text", { x: cx + 4, y: cy - reg.radius * sz.R * k + 14, class: "region-label" }, g);
    t.textContent = reg.name;
  }
  const P = S.map.planets;
  const pos = P.map((p) => toScreen(p.x, p.y, sz));
  // 航路
  for (const [a, b] of S.map.lanes) {
    const border = P[a].owner !== P[b].owner;
    el("line", { x1: pos[a][0], y1: pos[a][1], x2: pos[b][0], y2: pos[b][1], class: border ? "lane border" : "lane" }, g);
  }
  const hot = new Set(S.state ? S.state.hot : []);
  const sel = S.selectedFaction;
  // 星
  for (const p of P) {
    const [x, y] = pos[p.id];
    const r = Math.max(3, Math.min(9, 2.2 + Math.log10(p.pop + 1) * 1.3)) * Math.min(1.8, Math.sqrt(k));
    if (S.mode !== "unrest" && hot.has(p.id)) el("circle", { cx: x, cy: y, r: r + 2, class: "hot-ring" }, g);
    const c = el("circle", { cx: x, cy: y, r, fill: starFill(p), class: "star", "data-pid": p.id }, g);
    if (sel !== null && p.owner !== sel) c.classList.add("dim");
    if (p.capital) el("circle", { cx: x, cy: y, r: r + 3.5, class: "cap-ring", stroke: color(p.owner, 0.9) }, g);
    if (S.selectedPlanet === p.id) el("circle", { cx: x, cy: y, r: r + 6, class: "sel-ring" }, g);
  }
  // 国名（首都の上）と星の名
  const byId = new Map((S.state ? S.state.factions : []).map((f) => [f.id, f]));
  for (const p of P) {
    const [x, y] = pos[p.id];
    if (p.capital && byId.has(p.owner)) {
      const t = el("text", { x, y: y - 12 * Math.min(1.6, Math.sqrt(k)), class: "label faction", "text-anchor": "middle" }, g);
      t.textContent = byId.get(p.owner).base;
    } else if (k >= 2.2) {
      const t = el("text", { x: x + 7, y: y + 4, class: "label" }, g);
      t.textContent = p.name;
    }
  }
}

// 拡大・移動
let drag = null;
svg.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const sz = mapSize();
  const rect = svg.getBoundingClientRect();
  const mx = ev.clientX - rect.left - sz.w / 2, my = ev.clientY - rect.top - sz.h / 2;
  const f = ev.deltaY < 0 ? 1.18 : 1 / 1.18;
  const nk = Math.max(0.6, Math.min(8, S.view.k * f));
  const ratio = nk / S.view.k;
  S.view.px = mx - (mx - S.view.px) * ratio;
  S.view.py = my - (my - S.view.py) * ratio;
  S.view.k = nk;
  drawMap();
}, { passive: false });
svg.addEventListener("pointerdown", (ev) => {
  const star = ev.target.closest && ev.target.closest(".star");
  drag = { x: ev.clientX, y: ev.clientY, px: S.view.px, py: S.view.py, moved: false,
           pid: star ? Number(star.dataset.pid) : null };
  svg.setPointerCapture(ev.pointerId);
});
svg.addEventListener("pointermove", (ev) => {
  if (drag) {
    const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
    if (drag.moved) {
      svg.classList.add("dragging");
      S.view.px = drag.px + dx;
      S.view.py = drag.py + dy;
      drawMap();
      return;
    }
  }
  const star = ev.target.closest && ev.target.closest(".star");
  const tip = $("#tooltip");
  if (!star) { tip.hidden = true; return; }
  const p = S.map.planets[Number(star.dataset.pid)];
  const f = S.state && S.state.factions.find((x) => x.id === p.owner);
  const rect = svg.getBoundingClientRect();
  tip.innerHTML = `<b>${esc(p.name)}</b>${p.capital ? " ★首都" : ""}<br>
    <span class="t-sub">${esc(p.type)}／人口${Math.round(p.pop).toLocaleString()}百万</span><br>
    ${f ? `<span style="color:${color(f.id)}">■</span> ${esc(f.name)}` : "<span class='t-sub'>無主の星</span>"}
    ${p.unrest > 30 ? `<br><span style="color:#ff9f9f">不穏度 ${p.unrest}</span>` : ""}`;
  tip.hidden = false;
  tip.style.left = Math.min(ev.clientX - rect.left + 14, rect.width - 270) + "px";
  tip.style.top = (ev.clientY - rect.top + 14) + "px";
});
svg.addEventListener("pointerup", (ev) => {
  const d = drag;
  drag = null;
  svg.classList.remove("dragging");
  if (d && !d.moved && d.pid !== null) openDetail("planet", d.pid);
});
svg.addEventListener("pointerleave", () => { $("#tooltip").hidden = true; });
window.addEventListener("resize", drawMap);
$("#map-reset").addEventListener("click", () => {
  S.view = { k: 1, px: 0, py: 0 };
  S.selectedFaction = null;
  S.selectedPlanet = null;
  drawMap();
});
$$("#map-mode button").forEach((b) => b.addEventListener("click", () => {
  $$("#map-mode button").forEach((x) => x.classList.toggle("on", x === b));
  S.mode = b.dataset.mode;
  drawMap();
}));

// ------------------------------------------------------------------ 年代記
const MARKS = { 1: "・", 2: "◇", 3: "◆", 4: "★", 5: "✦" };

function renderFeed() {
  const feed = $("#feed");
  if (!S.entries.length) {
    feed.innerHTML = `<div class="empty">まだ記録はない。時を進めると、ここに銀河の歴史が刻まれていく。</div>`;
    return;
  }
  let html = "";
  let year = null;
  for (let i = S.entries.length - 1; i >= 0; i--) {
    const e = S.entries[i];
    if (e.year !== year) {
      year = e.year;
      html += `<div class="year-head">残光暦 ${year}年</div>`;
    }
    const fresh = e.i > S.seen ? " fresh" : "";
    html += `<div class="entry imp${e.imp}${fresh}"><span class="mark">${MARKS[e.imp]}</span>
      <span class="mon">${e.month}月</span><span class="txt">${linkify(e.text, e.refs)}</span>`;
    if (e.quote) html += `<div class="quote"><span class="who">${ref(e.speaker)}</span>「${esc(e.quote)}」</div>`;
    if (e.reply) html += `<div class="quote"><span class="who">${e.replier ? ref(e.replier) : "傍らの者"}</span>「${esc(e.reply)}」</div>`;
    html += `</div>`;
  }
  feed.innerHTML = html;
}

async function loadChronicle(reset) {
  if (reset) { S.entries = []; S.next = 0; }
  const data = await api(`/api/chronicle?since=${S.next}&min=${S.minImp}&limit=${reset ? 400 : MAX_FEED}`);
  S.next = data.next;
  S.entries = S.entries.concat(data.entries).slice(-MAX_FEED);
  return data.entries;
}

$("#min-imp").addEventListener("change", async (ev) => {
  S.minImp = Number(ev.target.value);
  await loadChronicle(true);
  S.seen = S.next;
  renderFeed();
});

function showBanner(entries) {
  const big = entries.filter((e) => e.imp >= 5);
  if (!big.length) return;
  const e = big[big.length - 1];
  const b = $("#banner");
  b.innerHTML = `${esc(e.year)}年${e.month}月　${esc(e.text)}${e.quote ? `<span class="q">「${esc(e.quote)}」</span>` : ""}`;
  b.hidden = false;
  clearTimeout(showBanner.timer);
  showBanner.timer = setTimeout(() => { b.hidden = true; }, 5500);
}

// ------------------------------------------------------------------ 一覧
function renderFactions() {
  if (!S.state) return;
  $("#faction-list").innerHTML = S.state.factions.map((f) => `
    <div class="card${S.selectedFaction === f.id ? " selected" : ""}" data-ref="faction" data-id="${f.id}">
      <div class="card-top"><span class="swatch" style="background:${color(f.id)}"></span>
        <span class="card-title">${esc(f.name)}</span>
        ${f.at_war ? '<span class="pill war">交戦中</span>' : ""}</div>
      <div class="card-sub">${esc(f.gov)}・${esc(f.ideology)}　${f.planets}星系　艦隊${f.fleet.toLocaleString()}　安定${f.stability}</div>
      <div class="card-sub">${esc(f.leader_title)} ${f.leader ? esc(f.leader.name) : "空位"}</div>
    </div>`).join("");
}

async function renderPeople() {
  const q = $("#search").value.trim();
  const dead = $("#include-dead").checked;
  const list = q ? await api(`/api/search?q=${encodeURIComponent(q)}`) : await api(`/api/famous?n=60&dead=${dead ? 1 : 0}`);
  $("#people-list").innerHTML = list.length ? list.map((p) => `
    <div class="card" data-ref="person" data-id="${p.id}">
      <div class="card-top"><span class="card-title">${esc(p.name)}${p.alive ? "" : "†"}</span><span class="pill">名声 ${p.fame}</span></div>
      <div class="card-sub">${esc(p.species)}・${p.age}歳　${esc(p.job)}</div>
    </div>`).join("") : `<div class="empty">該当する人物はいない。</div>`;
}
let searchTimer;
$("#search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(renderPeople, 250); });
$("#include-dead").addEventListener("change", renderPeople);

async function renderWars() {
  const wars = await api("/api/wars");
  $("#war-list").innerHTML = wars.length ? wars.map((w) => `
    <div class="card" data-ref="war" data-id="${w.id}">
      <div class="card-top"><span class="card-title">${esc(w.name)}</span>
        ${w.active ? '<span class="pill war">継続中</span>' : `<span class="pill">${w.start}〜${w.end}年</span>`}</div>
      <div class="card-sub">${w.attackers.map((f) => esc(f.name)).join("・")} ⇄ ${w.defenders.map((f) => esc(f.name)).join("・")}</div>
      <div class="card-sub">${w.active ? `${w.start}年〜　戦況 <span class="score">${w.score > 0 ? "+" : ""}${w.score}</span>` : esc(w.outcome)}</div>
    </div>`).join("") : `<div class="empty">この銀河はまだ戦争を知らない。</div>`;
}

// ------------------------------------------------------------------ タブ
function showTab(name) {
  S.tab = name;
  $$("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  $$(".tab-body").forEach((b) => { b.hidden = b.id !== `tab-${name}`; });
  if (name === "factions") renderFactions();
  if (name === "people") renderPeople();
  if (name === "wars") renderWars();
}
$$("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

// ------------------------------------------------------------------ 詳細
async function openDetail(type, id, push = true) {
  const data = await api(`/api/${type}/${id}`).catch(() => null);
  if (!data) return;
  if (push && S.current) S.history.push(S.current);
  S.current = { type, id };
  S.selectedFaction = type === "faction" ? id : null;
  S.selectedPlanet = type === "planet" ? id : null;
  $("#detail-tab").hidden = false;
  $("#back").disabled = !S.history.length;
  $("#detail").innerHTML = RENDER[type](data);
  showTab("detail");
  $("#tab-detail").scrollTop = 0;
  drawMap();
}
$("#back").addEventListener("click", () => {
  const prev = S.history.pop();
  if (prev) openDetail(prev.type, prev.id, false);
});

async function refreshDetail() {
  if (S.tab !== "detail" || !S.current) return;
  const data = await api(`/api/${S.current.type}/${S.current.id}`).catch(() => null);
  if (data) $("#detail").innerHTML = RENDER[S.current.type](data);
}

const sec = (title, body) => (body ? `<div class="d-sec"><h3>${title}</h3>${body}</div>` : "");
const kv = (rows) => `<dl class="kv">${rows.filter((r) => r[1] !== null && r[1] !== undefined && r[1] !== "")
  .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;
const timeline = (items) => (items.length ? `<ul class="timeline">${items.map((x) =>
  `<li><span class="when">${esc(x.date)}</span>${esc(x.text)}</li>`).join("")}</ul>` : "");

const RENDER = {
  person(p) {
    const life = p.alive ? `${p.born}年生まれ・${p.age}歳` : `${p.born}〜${p.died}年・享年${p.age}`;
    const stats = p.stats.map((s) => `<div class="stat"><span>${s.name}</span>
      <span class="bar${s.key === "resonance" ? " res" : ""}"><i style="width:${Math.min(100, s.value * 4)}%"></i></span>
      <span>${s.value}</span></div>`).join("");
    const fam = p.family;
    const famRows = [["親", fam.parents], ["伴侶", fam.spouse], ["先立った伴侶", fam.former_spouses],
      ["子", fam.children], ["師", fam.mentor], ["弟子", fam.apprentices], ["宿敵", fam.rivals]]
      .filter(([, v]) => v.length).map(([k, v]) => `<dt>${k}</dt><dd>${refs(v)}</dd>`).join("");
    const career = p.career.map((c) => `<tr><td class="n">${c.from}〜${c.to ?? ""}</td>
      <td>${esc(c.org)}<br><b>${esc(c.title)}</b>${c.reason ? `<span class="muted">（${esc(c.reason)}）</span>` : ""}</td></tr>`).join("");
    return `
      <div class="d-head">
        <div class="d-kicker">人物伝</div>
        <div class="d-title">${esc(p.name)}${p.alive ? "" : " †"}</div>
        <div class="d-sub">${esc(p.species)}・${esc(p.sex)}　${life}</div>
        <div class="d-sub">${esc(p.job)}</div>
      </div>
      ${kv([["出自", esc(p.origin)], ["生まれ", ref(p.birth_planet)], ["所在", ref(p.planet)],
            ["所属", ref(p.faction)], ["理念", esc(p.ideology)], ["名声", p.fame], ["資産", p.wealth.toLocaleString()]])}
      ${p.titles.length ? sec("称号", `<div class="chips">${p.titles.map((t) => `<span class="chip acq">${esc(t)}</span>`).join("")}</div>`) : ""}
      ${sec("性格", `<div class="chips">${p.traits.map((t) => `<span class="chip${t.acquired ? " acq" : ""}" title="${esc(t.desc)}">${esc(t.name)}</span>`).join("")}</div>`)}
      ${sec("能力", `<div class="stats">${stats}</div>`)}
      ${famRows ? sec("縁", `<dl class="family">${famRows}</dl>`) : ""}
      ${career ? sec("経歴", `<table class="table">${career}</table>`) : ""}
      ${sec("生涯", timeline(p.bio))}
      ${p.quotes.length ? sec("語録", p.quotes.slice().reverse().map((q) => `<div class="say">「${esc(q.text)}」<span class="when">${esc(q.date)}</span></div>`).join("")) : ""}
      ${p.alive ? "" : sec("最期", `<div class="death">${esc(p.death_text || "")}</div>`)}
    `;
  },

  faction(f) {
    const rel = (rows) => rows.map((r) => `<div class="rel">${ref(r.faction)}<span class="v ${r.value >= 0 ? "pos" : "neg"}">${r.value > 0 ? "+" : ""}${r.value}</span></div>`).join("");
    const rulers = f.rulers.slice().reverse().map((r) => `<tr><td class="n">${r.from}〜${r.to ?? ""}</td>
      <td>${ref(r.person)}${r.fate ? `<span class="muted">（${esc(r.fate)}）</span>` : ""}</td></tr>`).join("");
    const tech = f.tech.map((t) => `<tr><td class="n">${esc(t.field)}</td><td>第${t.level}段階　${esc(t.latest)}</td></tr>`).join("");
    const wars = f.wars.slice().reverse().map((w) => `<div>${ref({ type: "war", id: w.id, name: w.name })}
      <span class="muted">${w.start}〜${w.end ?? ""}年 ${w.active ? "継続中" : esc(w.outcome)}</span></div>`).join("");
    return `
      <div class="d-head">
        <div class="d-kicker">国家史</div>
        <div class="d-title"><span class="swatch" style="background:${color(f.id)}"></span>${esc(f.name)}</div>
        <div class="d-sub">${esc(f.gov)}・${esc(f.ideology)}　${f.alive ? `建国 残光暦${f.founded}年` : `${f.founded}〜${f.fell}年（滅亡）`}</div>
      </div>
      <p class="legend-text">「${esc(f.motto)}」</p>
      ${f.legend ? `<p class="legend-text">${esc(f.legend)}</p>` : ""}
      <p class="muted">${esc(f.ideology_desc)}</p>
      ${kv([["元首", f.leader ? `${esc(f.leader_title)} ${ref(f.leader)}` : "空位"], ["首都", ref(f.capital_ref)],
            ["主要種族", esc(f.species)], ["領土", `${f.planets}星系`], ["艦隊", f.fleet.toLocaleString()],
            ["国庫", f.treasury.toLocaleString()], ["安定度", f.stability], ["戦争疲弊", f.exhaustion],
            ["独立元", f.parent ? ref(f.parent) : null]])}
      ${f.alive ? sec("外交", kv([["同盟", refs(f.allies)], ["通商", refs(f.trade)]]) +
        `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px"><div>${rel(f.friends)}</div><div>${rel(f.enemies)}</div></div>`) : ""}
      ${wars ? sec("戦争", wars) : ""}
      ${f.alive ? sec("技術", `<table class="table">${tech}</table>`) : ""}
      ${f.territory.length ? sec("領土", `<div class="chips">${f.territory.map((p) => `<span class="chip">${ref(p)}</span>`).join("")}</div>`) : ""}
      ${sec("歴代の元首", `<table class="table">${rulers}</table>`)}
      ${sec("歩み", timeline(f.history.slice().reverse()))}
    `;
  },

  planet(p) {
    const residents = p.residents.map((r) => `<tr><td>${ref(r)}</td><td class="muted">${esc(r.species)}・${r.age}歳<br>${esc(r.job)}</td></tr>`).join("");
    const corps = p.corps.map((c) => `<div><b>${esc(c.name)}</b> <span class="muted">${esc(c.sector)}・${c.hq ? "本社" : "支社"}</span>
      ${c.hq && c.ceo ? `<br><span class="muted">社長</span> ${ref(c.ceo)}　<span class="muted">「${esc(c.motto)}」</span>` : ""}</div>`).join("");
    return `
      <div class="d-head">
        <div class="d-kicker">惑星</div>
        <div class="d-title">${esc(p.name)}</div>
        <div class="d-sub">${esc(p.ptype)}／${esc(p.region)}</div>
      </div>
      <p class="legend-text">${esc(p.desc)}</p>
      ${kv([["支配", p.owner ? ref(p.owner) : "無主"], ["人口", `${p.population.toLocaleString()}百万`],
            ["発展度", p.development], ["主要種族", esc(p.species)], ["住民の理念", esc(p.culture)],
            ["不穏度", p.unrest], ["防衛力", p.defense]])}
      ${sec("航路", `<div class="chips">${p.lanes.map((l) => `<span class="chip">${ref(l)}</span>`).join("")}</div>`)}
      ${residents ? sec("名のある住人", `<table class="table">${residents}</table>`) : ""}
      ${corps ? sec("企業", corps) : ""}
      ${sec("この星の歴史", timeline(p.history.slice().reverse()))}
    `;
  },

  war(w) {
    const battles = w.battles.slice().reverse().map((b) => `<tr><td class="n">${esc(b.date)}</td>
      <td>${b.decisive ? "★ " : ""}${esc(b.name)}<br><span class="muted">${ref(b.winner)}の勝利${b.commander ? `（指揮 ${ref(b.commander)}）` : ""}</span></td></tr>`).join("");
    const caps = w.captured.map((c) => `<tr><td class="n">${esc(c.date)}</td><td>${ref(c.planet)}：${ref(c.from)} → ${ref(c.to)}</td></tr>`).join("");
    return `
      <div class="d-head">
        <div class="d-kicker">戦史</div>
        <div class="d-title">${esc(w.name)}</div>
        <div class="d-sub">${w.start}年〜${w.end ?? "継続中"}${w.end ? "年" : ""}　原因：${esc(w.cause)}</div>
      </div>
      ${kv([["攻撃側", refs(w.attackers)], ["防衛側", refs(w.defenders)], ["目標", ref(w.goal)],
            ["戦況", `${w.score > 0 ? "+" : ""}${w.score}（正なら攻撃側優勢）`], ["結末", w.outcome ? esc(w.outcome) : "未決"]])}
      ${caps ? sec("領土の変化", `<table class="table">${caps}</table>`) : ""}
      ${w.fallen.length ? sec("散った者たち", refs(w.fallen)) : ""}
      ${sec(`会戦（${w.battles.length}回）`, battles ? `<table class="table">${battles}</table>` : "<div class='muted'>まだ砲火は交わされていない。</div>")}
    `;
  },
};

// ------------------------------------------------------------------ 更新
function renderHeader() {
  const s = S.state;
  $("#date").textContent = s.date;
  $("#galaxy-name").textContent = `${s.galaxy}年代記`;
  const c = s.counts;
  $("#counts").textContent = `国家 ${c.factions}　人物 ${c.persons.toLocaleString()}　企業 ${c.corps}　戦争 ${c.wars}　惑星 ${c.planets}　（シード ${s.seed}）`;
}

async function refresh() {
  const [state, map, fresh] = await Promise.all([api("/api/state"), api("/api/map"), loadChronicle(false)]);
  S.state = state;
  S.map = map;
  renderHeader();
  renderFeed();
  S.seen = S.next - 1;
  drawMap();
  if (S.tab === "factions") renderFactions();
  if (S.tab === "wars") renderWars();
  if (S.tab === "detail") refreshDetail();
  showBanner(fresh);
}

function setBusy(on, text) {
  S.busy = on;
  $("#busy").hidden = !on;
  if (text) $("#busy-text").textContent = text;
  $$("[data-step]").forEach((b) => { b.disabled = on && !S.playing; });
}

async function step(months, quiet) {
  if (!quiet) setBusy(true, months >= 120 ? "十年の時が流れています……" : "時が流れています……");
  try {
    await post(`/api/step?months=${months}`);
    await refresh();
  } finally {
    if (!quiet) setBusy(false);
  }
}
$$("[data-step]").forEach((b) => b.addEventListener("click", () => {
  if (S.busy) return;
  step(Number(b.dataset.step));
}));

async function playLoop() {
  while (S.playing) {
    const [delay, months] = $("#speed").value.split(",").map(Number);
    const t0 = performance.now();
    try { await step(months, true); } catch (e) { S.playing = false; break; }
    const wait = Math.max(0, delay - (performance.now() - t0));
    await new Promise((r) => setTimeout(r, wait));
  }
  updatePlay();
}
function updatePlay() {
  const b = $("#play");
  b.textContent = S.playing ? "❚❚ 一時停止" : "▶ 再生";
  b.classList.toggle("playing", S.playing);
}
$("#play").addEventListener("click", () => {
  S.playing = !S.playing;
  updatePlay();
  if (S.playing) playLoop();
});
document.addEventListener("keydown", (ev) => {
  if (ev.target.matches("input, select, textarea")) return;
  if (ev.code === "Space") { ev.preventDefault(); $("#play").click(); }
});

// ------------------------------------------------------------------ 序章・新しい銀河
function modal(body, actions) {
  $("#modal-body").innerHTML = body;
  const box = $("#modal-actions");
  box.innerHTML = "";
  for (const [label, cls, fn] of actions) {
    const b = document.createElement("button");
    b.className = `btn ${cls}`;
    b.textContent = label;
    b.addEventListener("click", fn);
    box.appendChild(b);
  }
  $("#modal").hidden = false;
}
const closeModal = () => { $("#modal").hidden = true; };

async function showPrologue() {
  const p = await api("/api/prologue");
  const facs = p.factions.slice(0, 8).map((f) => `<div class="faction-intro">
    <span class="ft"><span class="swatch" style="display:inline-block;background:${color(f.id)};margin-right:6px"></span>${esc(f.name)}</span>
    <span class="muted">　${esc(f.gov)}・${esc(f.ideology)}・${f.planets}星系</span><br>
    <span class="legend-text">${esc(f.legend)}</span></div>`).join("");
  modal(`<h2 class="prologue-title">序 章</h2><div class="prologue">${esc(p.text)}</div>
    <div class="d-sec"><h3>主な勢力</h3>${facs}</div>
    <div class="d-sec"><h3>星々の間に響くもの</h3><div class="prologue">${esc(p.resonance)}</div></div>`,
  [["観測を始める", "primary", closeModal]]);
}
$("#show-prologue").addEventListener("click", showPrologue);

$("#new-world").addEventListener("click", () => {
  modal(`<h2 class="prologue-title">新しい銀河</h2>
    <div class="form">
      <label for="f-seed">シード</label><input id="f-seed" class="input" type="number" value="${Math.floor(Math.random() * 100000)}">
      <label for="f-planets">惑星の数</label><input id="f-planets" class="input" type="number" min="30" max="300" value="120">
    </div>
    <p class="muted">同じシードからは、同じ歴史が生まれます。惑星が多いほど歴史は豊かになりますが、時の流れは遅くなります。</p>`,
  [["やめる", "ghost", closeModal], ["生成する", "primary", async () => {
    const seed = Number($("#f-seed").value) || 1;
    const planets = Number($("#f-planets").value) || 120;
    closeModal();
    S.playing = false;
    updatePlay();
    setBusy(true, "銀河を生成しています……");
    try {
      await post(`/api/new?seed=${seed}&planets=${planets}`);
      await reset();
    } finally {
      setBusy(false);
    }
    showPrologue();
  }]]);
});

async function reset() {
  S.history = [];
  S.current = null;
  S.selectedFaction = null;
  S.selectedPlanet = null;
  S.view = { k: 1, px: 0, py: 0 };
  $("#detail-tab").hidden = true;
  await loadChronicle(true);
  S.seen = S.next;
  await refresh();
  showTab("chronicle");
}

// ------------------------------------------------------------------ 起動
(async () => {
  await reset();
  if (S.state.t === 0) showPrologue();
})();
