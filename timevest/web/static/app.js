"use strict";
const $ = (s, r = document) => r.querySelector(s);
const view = $("#view");
let token = null, investments = [], tab = "timer", tick = null;

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = sec => [sec / 3600, (sec % 3600) / 60, sec % 60].map(n => String(Math.floor(n)).padStart(2, "0")).join(":");
const hm = h => `${Math.floor(h)}h ${String(Math.round((h % 1) * 60)).padStart(2, "0")}m`;

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  setTimeout(() => (t.hidden = true), 2500);
}

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || res.statusText);
  }
  return res.json();
}

async function init() {
  try {
    const cfg = await (await fetch("/api/config")).json();
    if (!cfg.liffId) throw new Error("伺服器尚未設定 LIFF_ID");
    await liff.init({ liffId: cfg.liffId });
    if (!liff.isLoggedIn()) { liff.login(); return; }
    token = liff.getAccessToken();
    investments = await api("/investments");
  } catch (e) {
    view.innerHTML = `<div class="card">無法啟動：${esc(e.message)}</div>`;
    return;
  }
  document.querySelectorAll("nav button").forEach(b => b.onclick = () => go(b.dataset.tab));
  const initialTab = location.hash.replace("#", "") || "timer";
  go(["timer", "manual", "items", "cal", "stats"].includes(initialTab) ? initialTab : "timer");
}

function go(t) {
  tab = t; clearInterval(tick);
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b.dataset.tab === t));
  ({ timer: renderTimer, manual: renderManual, items: renderItems, cal: renderCal, stats: renderStats })[t]().catch(e => toast(e.message));
}

const invOptions = () => [...investments].sort((a, b) => !!b.favorite - !!a.favorite)
  .map(i => `<option value="${i.id}">${i.favorite ? "⭐ " : ""}${esc(i.name)}</option>`).join("");

async function itemOptions(invId, withNone = true) {
  const items = invId ? await api("/items?investment_id=" + invId) : [];
  return (withNone ? `<option value="">（不指定）</option>` : "") +
    items.map(i => `<option value="${i.id}">${esc(i.name)}</option>`).join("");
}

const progressLabel = inv => inv.progress_type === "pages" ? "讀到第幾頁（可留空）" :
  inv.progress_type === "percentage" ? "完成度 %（可留空）" : null;

function bindInvItem(root, onChange) {
  const inv = $("[name=inv]", root), item = $("[name=item]", root);
  const refresh = async () => {
    item.innerHTML = await itemOptions(inv.value);
    const cur = investments.find(i => i.id === inv.value);
    const pl = progressLabel(cur || {});
    const box = $("[name=progress]", root);
    if (box) { box.parentElement.hidden = !pl; if (pl) $("span", box.parentElement).textContent = pl; }
    onChange && onChange();
  };
  inv.onchange = refresh; refresh();
}

const progressField = `<div><label><span></span></label><input name="progress" type="number" inputmode="decimal" min="0"></div>`;

// ---------------- 計時 ----------------
async function renderTimer() {
  const session = await api("/session");
  if (!session) {
    view.innerHTML = `<div class="card">
      <label>投資帳戶</label><select name="inv">${invOptions()}</select>
      <label>項目</label><select name="item"></select>
      <div class="row"><input name="newitem" placeholder="新增項目名稱" style="flex:1"><button class="ghost small" id="add">新增</button></div>
      <div class="clock">00:00:00</div>
      <button class="primary" id="start">▶ 開始專注</button></div>`;
    const card = view;
    bindInvItem(card);
    $("#add").onclick = async () => {
      const name = $("[name=newitem]").value.trim(); if (!name) return;
      const it = await api("/items", { method: "POST", body: { investment_id: $("[name=inv]").value, name } });
      $("[name=newitem]").value = "";
      $("[name=item]").innerHTML = await itemOptions($("[name=inv]").value);
      $("[name=item]").value = it.id;
    };
    $("#start").onclick = async () => {
      await api("/session/start", { method: "POST", body: { investment_id: $("[name=inv]").value, item_id: $("[name=item]").value || null } });
      const initialTab = location.hash.replace("#", "") || "timer";
  go(["timer", "manual", "items", "cal", "stats"].includes(initialTab) ? initialTab : "timer");
    };
    return;
  }
  const inv = investments.find(i => i.id === session.investment_id) || {};
  const items = await api("/items?investment_id=" + session.investment_id);
  const item = items.find(i => i.id === session.item_id);
  const start = new Date(session.start).getTime();
  view.innerHTML = `<div class="card">
    <div class="sub">${esc(inv.name)}${item ? " · " + esc(item.name) : ""}</div>
    <div class="clock" id="clock">00:00:00</div>
    ${progressLabel(inv) ? progressField : ""}
    <label>備註（可留空）</label><input name="memo">
    <button class="primary" id="finish">⏹ 結束並記錄</button>
    <button class="danger" id="cancel">放棄這次記錄</button></div>`;
  if (progressLabel(inv)) $("[name=progress]").previousElementSibling.querySelector("span").textContent = progressLabel(inv);
  const upd = () => ($("#clock").textContent = fmt(Math.max(0, (Date.now() - start) / 1000)));
  upd(); tick = setInterval(upd, 1000);
  $("#finish").onclick = async () => {
    const p = $("[name=progress]")?.value;
    const r = await api("/session/finish", { method: "POST", body: { progress_value: p ? Number(p) : null, memo: $("[name=memo]").value || null } });
    toast("已記錄 ✅" + (r.milestones.length ? "　解鎖里程碑！" : ""));
    const initialTab = location.hash.replace("#", "") || "timer";
  go(["timer", "manual", "items", "cal", "stats"].includes(initialTab) ? initialTab : "timer");
  };
  $("#cancel").onclick = async () => { if (confirm("確定放棄？")) { await api("/session/cancel", { method: "POST" }); const initialTab = location.hash.replace("#", "") || "timer";
  go(["timer", "manual", "items", "cal", "stats"].includes(initialTab) ? initialTab : "timer"); } };
}

// ---------------- 手動補記 ----------------
async function renderManual() {
  const nowLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  view.innerHTML = `<div class="card">
    <label>投資帳戶</label><select name="inv">${invOptions()}</select>
    <label>項目</label><select name="item"></select>
    <label>開始</label><input type="datetime-local" name="start" value="${nowLocal}">
    <label>結束</label><input type="datetime-local" name="end" value="${nowLocal}">
    ${progressField}
    <label>備註</label><input name="memo">
    <button class="primary" id="save">儲存記錄</button></div>`;
  bindInvItem(view);
  $("#save").onclick = async () => {
    const p = $("[name=progress]").value;
    await api("/activities", { method: "POST", body: {
      investment_id: $("[name=inv]").value, item_id: $("[name=item]").value || null,
      start: $("[name=start]").value, end: $("[name=end]").value,
      progress_value: p ? Number(p) : null, memo: $("[name=memo]").value || null } });
    toast("已儲存 ✅");
  };
}

// ---------------- 項目 / 帳戶 ----------------
async function renderItems() {
  view.innerHTML = `<div class="card"><label>投資帳戶</label><div class="row"><select name="inv">${invOptions()}</select><button class="ghost small" id="fav" style="margin-left:8px"></button></div>
    <div class="row"><input name="newitem" placeholder="新增項目" style="flex:1"><input name="total" type="number" placeholder="總頁數" style="width:90px"><button class="ghost small" id="add">＋</button></div></div>
    <div id="list"></div>
    <div class="card"><div class="row"><input name="newinv" placeholder="新增投資帳戶（例：閱讀、吉他）" style="flex:1"><button class="ghost small" id="addinv">新增</button></div>
    <button class="danger" id="delinv">刪除目前帳戶（含所有項目）</button></div>`;
  const sel = $("[name=inv]");
  const paintFav = () => { const i = investments.find(x => x.id === sel.value); $("#fav").textContent = i && i.favorite ? "⭐ 常用" : "☆ 設為常用"; };
  $("#fav").onclick = async () => {
    const i = investments.find(x => x.id === sel.value); if (!i) return;
    await api("/investments/" + i.id, { method: "PATCH", body: { favorite: !i.favorite } });
    investments = await api("/investments"); const keep = sel.value; renderItems().then(() => { $("[name=inv]").value = keep; $("[name=inv]").onchange(); });
  };
  const load = async () => {
    paintFav();
    if (!sel.value) { $("#list").innerHTML = `<div class="mute">尚無帳戶</div>`; return; }
    const items = await api("/items?investment_id=" + sel.value);
    const inv = investments.find(i => i.id === sel.value);
    $("#list").innerHTML = items.map(it => {
      const pct = Math.round((it.progress || 0) * 100);
      return `<div class="card" data-id="${it.id}"><div class="row"><b>${esc(it.name)}</b><span class="mute">${esc(it.status)}</span></div>
        <div class="bar"><i style="width:${pct}%"></i></div>
        <div class="row mute" style="margin-top:6px"><span>${pct}%${it.total ? ` · 共 ${it.total}` : ""}</span>
        <span>${inv && inv.progress_type !== "none" ? `<button class="ghost small" data-act="prog">更新進度</button>` : ""}
        <button class="ghost small" data-act="done">${it.status === "completed" ? "重啟" : "完成"}</button>
        <button class="danger small" data-act="del">刪</button></span></div></div>`;
    }).join("") || `<div class="mute">這個帳戶還沒有項目</div>`;
  };
  sel.onchange = load; load();
  $("#list").onclick = async e => {
    const act = e.target.dataset.act; if (!act) return;
    const id = e.target.closest("[data-id]").dataset.id;
    if (act === "del") { if (!confirm("刪除此項目？")) return; await api("/items/" + id, { method: "DELETE" }); }
    if (act === "done") await api("/items/" + id, { method: "PATCH", body: { status: e.target.textContent === "完成" ? "completed" : "inProgress" } });
    if (act === "prog") { const v = prompt("目前進度（頁數或 %）"); if (v === null || v === "") return; await api("/items/" + id, { method: "PATCH", body: { current: Number(v) } }); }
    load();
  };
  $("#add").onclick = async () => {
    const name = $("[name=newitem]").value.trim(); if (!name) return;
    const total = $("[name=total]").value;
    await api("/items", { method: "POST", body: { investment_id: sel.value, name, total: total ? Number(total) : null } });
    $("[name=newitem]").value = ""; $("[name=total]").value = ""; load();
  };
  $("#addinv").onclick = async () => {
    const name = $("[name=newinv]").value.trim(); if (!name) return;
    await api("/investments", { method: "POST", body: { name } });
    investments = await api("/investments"); renderItems();
  };
  $("#delinv").onclick = async () => {
    if (!sel.value || !confirm("確定刪除此帳戶及其所有項目？（BigQuery 歷史紀錄不會刪）")) return;
    await api("/investments/" + sel.value, { method: "DELETE" });
    investments = await api("/investments"); renderItems();
  };
}

// ---------------- 收益 ----------------
async function renderStats() {
  view.innerHTML = `<div class="card mute">載入中…</div>`;
  const [all, week] = await Promise.all([api("/stats"), api("/stats?days=7")]);
  const s = all.summary;
  const bars = rows => rows.map(r => `<div style="margin-top:10px"><div class="row"><span>${esc(r.name)}</span><span class="mute">${hm(r.hours)} · ${Math.round(r.percentage * 100)}%</span></div>
    <div class="bar"><i style="width:${Math.round(r.percentage * 100)}%;background:${esc(r.color)}"></i></div></div>`).join("") || `<div class="mute">尚無資料</div>`;
  view.innerHTML = `<div class="card" style="text-align:center"><div class="mute">專注資產總額</div><div class="big">${hm(s.total_hours)}</div>
    <div class="row" style="justify-content:space-around"><span class="mute">今日 ${hm(s.today_hours)}</span><span class="mute">🔥 連續 ${s.streak_days} 天</span></div></div>
    <div class="card"><b>近 7 天分配</b>${bars(week.allocation)}</div>
    <div class="card"><b>累積分配</b>${bars(all.allocation)}</div>
    <div class="card"><b>里程碑</b>${all.milestones.map(m => `<div style="margin-top:10px">🏆 ${esc(m.title)}<div class="mute">${esc(m.description || "")}</div></div>`).join("") || `<div class="mute">尚無里程碑</div>`}</div>`;
}

init();


// ---------------- 行事曆綁定 ----------------
async function renderCal() {
  view.innerHTML = `<div class="card mute">載入中…</div>`;
  const list = await api("/calendars");
  view.innerHTML = `
    <div class="card">
      <b>📱 綁定 iPhone / 手機行事曆</b>
      <div class="mute" style="margin: 8px 0 14px; line-height: 1.5;">
        1. 打開 iPhone「行事曆」App ➔ 點下方「行事曆」<br>
        2. 點日曆旁的 ℹ️ ➔ 開啟「公開行事曆」➔「共享連結」拷貝網址<br>
        3. 貼在下方即可完成自動同步與提醒！
      </div>
      <label>行事曆名稱</label>
      <input name="cal_label" placeholder="例如：iPhone 個人課表" value="iPhone 行事曆">
      <label>日曆網址（webcal:// 或 https://）</label>
      <input name="cal_url" placeholder="webcal://p123-caldav.icloud.com/...">
      <label>對應習慣帳戶</label>
      <select name="cal_inv">${invOptions()}</select>
      <button class="primary" id="save_cal">🔗 確認綁定</button>
    </div>

    <div class="card">
      <b>📋 已綁定的行事曆</b>
      <div id="cal_list" style="margin-top: 10px;"></div>
    </div>
  `;

  const renderCalList = (items) => {
    if (!items.length) {
      $("#cal_list").innerHTML = `<div class="mute">尚未綁定任何行事曆</div>`;
      return;
    }
    $("#cal_list").innerHTML = items.map(c => `
      <div class="row" style="padding: 10px 0; border-bottom: 1px solid var(--line);">
        <div>
          <div>${esc(c.emoji || "📱")} <b>${esc(c.label)}</b></div>
          <div class="mute" style="font-size: 11px; margin-top: 2px;">對應帳戶：${esc(c.investment || "無")}</div>
        </div>
        <button class="danger small" data-key="${esc(c.key)}">解綁</button>
      </div>
    `).join("");

    $("#cal_list").querySelectorAll("button[data-key]").forEach(btn => {
      btn.onclick = async () => {
        if (!confirm("確定解除此行事曆綁定？")) return;
        const res = await api("/calendars/" + btn.dataset.key, { method: "DELETE" });
        toast("已解除綁定");
        renderCalList(res.calendars);
      };
    });
  };

  renderCalList(list);

  $("#save_cal").onclick = async () => {
    const label = $("[name=cal_label]").value.trim();
    const url = $("[name=cal_url]").value.trim();
    const invSel = $("[name=cal_inv]");
    const invName = invSel.options[invSel.selectedIndex]?.text.replace("⭐ ", "").trim();
    if (!url) { toast("請輸入日曆網址"); return; }
    try {
      const res = await api("/calendars", {
        method: "POST",
        body: { label, url, investment: invName }
      });
      toast("綁定成功！✅");
      $("[name=cal_url]").value = "";
      renderCalList(res.calendars);
    } catch (e) {
      toast("綁定失敗：" + e.message);
    }
  };
}
