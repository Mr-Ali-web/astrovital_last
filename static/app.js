"use strict";
const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const vitalSpecs = [
  ["heart_rate","Yurak urishi","♡"], ["spo2","Qondagi kislorod SpO₂","◉"],
  ["systolic_bp","Sistolik bosim","↗"], ["diastolic_bp","Diastolik bosim","↘"],
  ["body_temp","Tana harorati","♨"], ["resp_rate","Nafas tezligi","≈"]
];
const cabinSpecs = [
  ["o2_partial","O₂ bosimi"], ["co2_partial","CO₂ bosimi"], ["pressure","Kabina bosimi"],
  ["temperature","Harorat"], ["humidity","Namlik"], ["radiation","Radiatsiya"]
];
const levelNames = {normal:"BARQAROR",attention:"E’TIBOR",critical:"XAVF",unknown:"NOMA’LUM"};
let state = null;
let selectedCrew = null;
let initialized = false;
let inFlight = false;
let lastRefresh = 0;
let activeView = 'overview';
let lastCrewOptionSignature = '';
let viewLoadEpoch = 0;
let refreshTimer = null;
const viewGroups = {
  overview: 'overview', 'crew-section':'crew', individual:'crew',
  shared:'environment', zones:'environment', emergency:'emergency',
  alerts:'history', events:'history'
};
const viewDetails = {
  overview:['Missiya holati','Asosiy holat va sinov boshqaruvi'],
  'crew-section':['Ekipaj a’zolari','Ekipaj tarkibi va umumiy sog‘liq holati'],
  individual:['Tibbiy ko‘rsatkichlar','Tanlangan kosmonavtning individual trendlari'],
  shared:['Umumiy sababni tekshirish','Ekipaj, kabina va texnik holatlarning kesishma tahlili'],
  zones:['Kabina modullari','HAB/LAB atmosferasi va uskunalari'],
  emergency:['Favqulodda yordam','DEMO protokollar va lokal hodisalar boshqaruvi'],
  alerts:['Faol ogohlantirishlar','Sensor va tahlil qoidalari yaratgan signal va ogohlantirishlar'],
  events:['Hodisalar tarixi','SQLite jurnali va kosmonavt ismlari']
};
const groupTabs = {
  crew: [['crew-section','Ekipaj ro‘yxati'],['individual','Tibbiy ko‘rsatkichlar']],
  environment: [['shared','Umumiy sabab'],['zones','Kabina va uskunalar']],
  history: [['alerts','Ogohlantirishlar'],['events','Hodisalar tarixi']]
};

async function api(url, method="GET", payload) {
  const options = {method, headers:{"Content-Type":"application/json"}};
  if (payload !== undefined) options.body = JSON.stringify(payload);
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(String(detail));
  }
  return await res.json();
}
function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => $("toast").classList.add("hidden"), 4400);
}
const numberOf = point => point && point.quality === "good" && typeof point.value === "number" ? point.value : null;
const showNum = (point, digits) => {
  const value = numberOf(point);
  return value === null ? "—" : Number(value.toFixed(digits ?? 1)).toLocaleString("uz-UZ");
};
function renderCrew(crew) {
  $("crewCount").textContent = String(crew.length);
  const ids = new Set(crew.map(p=>p.crew_id));
  if (!ids.has(selectedCrew)) selectedCrew = crew[0]?.crew_id ?? null;
  $("crewGrid").innerHTML = crew.map(p => `
    <button class="crew-card ${selectedCrew === p.crew_id ? "selected" : ""}" data-crew="${esc(p.crew_id)}" type="button" aria-pressed="${selectedCrew === p.crew_id}">
      <div class="crew-top"><div><div class="crew-name">${esc(p.name)}</div><span class="crew-id">${esc(p.crew_id)} · ${esc(p.zone_id)}</span></div>
      <span class="mini-pill ${esc(p.level)}">${esc(levelNames[p.level] || p.level)}</span></div>
      <div class="crew-values"><span>♡ <b>${showNum(p.vitals.heart_rate, 0)}</b> <small>bpm</small></span>
      <span>◉ <b>${showNum(p.vitals.spo2, 1)}</b> <small>% SpO₂</small></span></div>
      <span class="crew-id">${p.active_alert_count} individual ogohlantirish</span>
    </button>`).join("");
}
function renderMetrics(person, alerts) {
  if (!person) return;
  $("individualTitle").textContent = person.name + " — tibbiy monitoring";
  $("individualZone").textContent = person.crew_id + " · " + person.zone_id;
  $("manualSymptom").value = person.symptoms[0] || "";
  const problemKeys = new Set(alerts.filter(a=>a.scope==="crew" && a.subject_id===person.crew_id).map(a=>a.code));
  const flagged = {
    spo2:["LOW_SPO2","TREND_SPO2_DOWN"],
    heart_rate:["HIGH_HEART_RATE","TREND_HR_UP"],
    resp_rate:["HIGH_RESP_RATE","LOW_RESP_RATE","TREND_RR_UP"],
    systolic_bp:["HIGH_BP","LOW_BP"],
    body_temp:["HIGH_BODY_TEMP","LOW_BODY_TEMP"]
  };
  $("vitalGrid").innerHTML = vitalSpecs.map(([key, title, icon])=>{
    const item = person.vitals[key];
    const lost = numberOf(item)===null;
    const bad = (flagged[key] || []).some(code=>problemKeys.has(code));
    return `<article class="metric ${bad ? "bad" : ""} ${lost ? "unknown" : ""}">
      <div class="metric-top"><span>${esc(title)}</span><b>${icon}</b></div>
      <div class="metric-value">${showNum(item, 1)}<small>${esc(item?.unit)}</small></div>
    </article>`;
  }).join("");
}
function renderZones(zones, systems) {
  $("zoneGrid").innerHTML = zones.map(z => `<article class="zone-card">
    <div class="zone-head"><h3>${esc(z.zone_id)} · ${esc(z.name)}</h3>
      <span class="mini-pill ${esc(z.level)}">${esc(levelNames[z.level] || z.level)}</span></div>
    <div class="zone-metrics">${cabinSpecs.map(([key,title])=>{
      const p=z.sensors[key];return `<div class="zone-metric"><label>${esc(title)}</label>
      <strong>${showNum(p, key === "co2_partial" ? 3 : 1)}</strong><small>${esc(p?.unit)}</small></div>`;
    }).join("")}</div></article>`).join("");
  $("systemStrip").innerHTML = `<span>HAYOT TA’MINOTI · DEMO</span>` +
    Object.entries(systems).map(([key,p])=>{
      const v=numberOf(p), label=key === "scrubber_ok" ? "CO₂ tozalash" : key === "hab_fan_ok" ? "HAB ventilyator" : key;
      const level=v===0 ? "critical" : v===1 ? "good" : "unknown";
      return `<span>${esc(label)} <b class="${level}">${v===0 ? "NOSOZLIK SIGNALI" : v===1 ? "SIM: OK" : "NOMA’LUM"}</b></span>`;
    }).join("");
}
function renderFindings(items) {
  $("sharedCount").textContent = String(items.length);
  $("findingList").innerHTML = items.length ? items.map(f => `
    <article class="finding ${esc(f.level)}">
      <div class="finding-head"><h3>${esc(f.title)}</h3><span class="mini-pill ${esc(f.level)}">${esc(levelNames[f.level] || f.level)}</span></div>
      <p>${esc(f.interpretation)}</p>
      <div class="muted-strong">EKIPAJ: ${esc(f.affected_crew.join(", ") || "—")} &nbsp;|&nbsp; MODUL: ${esc(f.affected_zones.join(", ") || "—")}</div>
      <ul>${f.evidence.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>
      <div class="muted-strong">NOANIQLIK: ${esc(f.uncertainties.join(" "))}</div>
      <p class="finding-actions"><button class="link-button" type="button" data-protocol="${esc(f.protocol_id)}">Yo‘riqnoma ↗</button>
      <button class="button primary" type="button" data-start-protocol="${esc(f.protocol_id)}" data-start-crew="${esc(f.affected_crew.join(','))}" data-start-zones="${esc(f.affected_zones.join(','))}" data-start-code="${esc(f.code)}">+ Hodisa yaratish</button></p>
    </article>`).join("") : `<div class="empty">Bir nechta kosmonavtda o‘xshash xavfli signal hozircha topilmadi.<br>Bu muhitning yoki kema tizimlarining mutlaq xavfsizligini anglatmaydi.</div>`;
}
function renderAlerts(alerts) {
  $("alertsCount").textContent = `${alerts.length} ta`;
  $("alertList").innerHTML = alerts.length ? alerts.slice(0, 35).map(a=>`
    <div class="alert-card ${esc(a.severity)}">
      <div class="alert-title">${a.severity==="critical" ? "⛔" : "⚠"} ${esc(a.subject_id)} · ${esc(a.title)}</div>
      <div class="alert-description">${esc(a.description)}</div>
      <div class="finding-actions"><button class="link-button" data-protocol="${esc(a.protocol_id)}">Yo‘riqnoma ↗</button>
      <button class="button primary" data-start-protocol="${esc(a.protocol_id)}" data-start-crew="${esc(a.scope==='crew'?a.subject_id:'')}" data-start-zones="${esc(a.scope==='zone'?a.subject_id:'')}" data-start-code="${esc(a.code)}">+ Hodisa yaratish</button></div>
    </div>`).join("") : `<div class="empty">Hozir faol sinov ogohlantirishi yo‘q.</div>`;
}
function renderEvents(items) {
  $("eventList").innerHTML = items.length ? items.slice(0, 24).map(e => {
    // Event names are snapshots saved at occurrence time; never use today's roster.
    const individual = e.scope === "crew";
    const actor = individual
      ? (e.subject_name ? `${e.subject_name} (${e.subject_id})` : `Ismi noma’lum (${e.subject_id})`)
      : e.scope === "zone" ? `${e.subject_name || e.subject_id} (${e.subject_id})`
      : "Umumiy tizim";
    const affected = Array.isArray(e.affected_crew) ? e.affected_crew : [];
    const members = affected.length ? `<div class="event-crew">Ta’sirlangan kosmonavtlar: ${
      affected.map(p => `${esc(p.name)} (${esc(p.crew_id)})`).join(", ")}</div>` : "";
    return `<div class="event-row">
      <time class="event-time">${esc(new Date(e.created_at).toLocaleTimeString("uz-UZ"))}</time>
      <div class="event-desc">
        <strong>${esc(e.event_type)} · <span class="event-actor">${esc(actor)}</span></strong>
        <div>${esc(e.message)}</div>${members}
      </div></div>`;
  }).join("") : `<div class="empty">Hodisalar yo‘q</div>`;
}
function plot(canvasId, history, key, color, minY, maxY) {
  const canvas = $(canvasId), rect=canvas.getBoundingClientRect(), w=rect.width;
  if (!w) return;
  const h=175,dpr=window.devicePixelRatio||1;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const l=34,t=14,r=12,b=20,drawW=w-l-r,drawH=h-t-b;
  ctx.font="10px Segoe UI";ctx.lineWidth=1;ctx.strokeStyle="#294659";ctx.fillStyle="#90afc3";
  for(let i=0;i<=3;i++) {
    const y=t+i*drawH/3;ctx.beginPath();ctx.moveTo(l,y);ctx.lineTo(w-r,y);ctx.stroke();
    ctx.fillText(String(Math.round(maxY-(maxY-minY)*i/3)),2,y+4);
  }
  const vals=history.map(d=>numberOf(d.vitals?.[key]));
  if(vals.length<2)return;
  let started=false;ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=2;
  vals.forEach((v,i)=>{
    if(v===null){started=false;return;}
    const x=l+(i*drawW/Math.max(vals.length-1,1));
    const y=Math.max(t,Math.min(t+drawH,t+drawH-(v-minY)/(maxY-minY)*drawH));
    if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);
  });ctx.stroke();
}
function syncGlobalCrew(crew) {
  const ids = new Set(crew.map(p=>p.crew_id));
  if(!ids.has(selectedCrew)) selectedCrew = crew[0]?.crew_id ?? null;
  const signature = JSON.stringify(crew.map(p=>[p.crew_id,p.name,p.zone_id]));
  if(signature!==lastCrewOptionSignature){
    $("selectedCrew").innerHTML=crew.map(p=>`<option value="${esc(p.crew_id)}">${esc(p.name)} • ${esc(p.zone_id)}</option>`).join("");
    lastCrewOptionSignature=signature;
  }
  $("selectedCrew").value=selectedCrew||"";
}
function updateGlobalStatus(status) {
  syncGlobalCrew(status.crew);
  $("connectionTag").textContent=status.earth_link ? "● YER ALOQASI (DEMO)" : "● OFFLINE REJIM";
  $("connectionTag").className="pill"+(status.earth_link?"":" offline");
  $("lastSeen").textContent="Namuna: "+new Date(status.mission.timestamp).toLocaleTimeString("uz-UZ");
  $("globalRisk").textContent="MISSIYA: "+(levelNames[status.level]||status.level);
  $("globalRisk").className="pill risk-pill risk-"+status.level;
  $("navAlertCount").textContent=String(status.active_alerts.length);
  $("navAlertCount").classList.toggle('has-alerts',status.active_alerts.length>0);
}
function updateOverview(status) {
  $("scenario").value=status.mission.scenario;
  $("overall").textContent=levelNames[status.level] || status.level;
  $("overall").className="status-main "+({normal:"ok",attention:"warn",critical:"critical",unknown:"unknown"}[status.level]||"");
  $("statusSub").textContent="Faqat sintetik kuzatuv";
  $("crewCount").textContent=String(status.crew.length);
  $("sharedCount").textContent=String(status.shared_findings.length);
  $("earthLinkText").textContent=status.earth_link ? "MAVJUD" : "UZILGAN";
  $("earthLinkText").className="status-main "+(status.earth_link ? "ok" : "warn");
  $("outboxCount").textContent=String(status.pending_outbox);
  $("toggleLink").textContent=status.earth_link ? "Aloqani uzish" : "Aloqani tiklash";
}
async function renderActiveView(status) {
  const view=activeView;
  const epoch=++viewLoadEpoch;
  switch(view){
    case 'overview': updateOverview(status); break;
    case 'crew-section': renderCrew(status.crew); break;
    case 'individual': {
      renderMetrics(status.crew.find(p=>p.crew_id===selectedCrew),status.active_alerts);
      if(!selectedCrew) break;
      const history=await api(`/api/crew/${encodeURIComponent(selectedCrew)}/history?limit=60`);
      if(view!==activeView || epoch!==viewLoadEpoch) return;
      plot('hrChart',history.items,'heart_rate','#65ddc0',40,170);
      plot('spo2Chart',history.items,'spo2','#7cb5f5',75,101);
      break;
    }
    case 'shared': renderFindings(status.shared_findings); break;
    case 'zones': renderZones(status.zones,status.mission.systems); break;
    case 'alerts': renderAlerts(status.active_alerts); break;
    case 'events': {
      const events=await api('/api/events?limit=24');
      if(view===activeView && epoch===viewLoadEpoch) renderEvents(events.items);
      break;
    }
    case 'emergency':
      syncCaseSelectors(status);
      await ensureStage3();
      break;
  }
}
async function refresh() {
  if(inFlight) return;
  inFlight=true;
  try{
    const status=await api('/api/status');
    state=status;
    if(!initialized){
      $('scenario').innerHTML=Object.entries(status.scenarios).map(([v,label])=>`<option value="${esc(v)}">${esc(label)}</option>`).join('');
      $('manualSymptom').innerHTML='<option value="">Alomat yo‘q</option>'+Object.entries(status.symptom_labels).map(([v,label])=>`<option value="${esc(v)}">${esc(label)}</option>`).join('');
      initialized=true;
    }
    updateGlobalStatus(status);
    // Monitoring is independent on the server; only the visible page is rendered.
    await renderActiveView(status);
    lastRefresh=Date.now();
  }catch(err){
    $('globalRisk').textContent='MA’LUMOT YANGILANMADI';
    $('globalRisk').className='pill risk-pill risk-attention';
    toast('Yangilashda xato: '+err.message);
  }finally{
    inFlight=false;
    if(refreshAfterFlight){refreshAfterFlight=false;void refresh();}
  }
}
function closeMobileNav(){
  $('mainNav').classList.remove('nav-open');
  $('mobileMenuButton').setAttribute('aria-expanded','false');
}
function activateView() {
  const id=decodeURIComponent(location.hash.replace(/^#/,''));
  const next=Object.prototype.hasOwnProperty.call(viewGroups,id)?id:'overview';
  const changed=activeView!==next;
  activeView=next;
  const group=viewGroups[next];
  document.querySelectorAll('[data-view]').forEach(el=>{el.hidden=el.dataset.view!==next;});
  document.querySelectorAll('#mainNav a[data-primary]').forEach(el=>{
    if(el.dataset.primary===group)el.setAttribute('aria-current','page');
    else el.removeAttribute('aria-current');
  });
  const tabs=groupTabs[group] || [];
  $('subNav').hidden=tabs.length===0;
  $('subNav').innerHTML=tabs.map(([id,name])=>`<a href="#${id}" ${id===next?'aria-current="page"':''}>${esc(name)}</a>`).join('');
  $('pageTitle').textContent=viewDetails[next][0];
  $('pageDescription').textContent=viewDetails[next][1];
  closeMobileNav();
  if(changed){
    viewLoadEpoch++;
    window.scrollTo(0,0);
    $('pageTitle').focus({preventScroll:true});
  }
  if(state){
    if(inFlight) refreshAfterFlight=true;
    else refresh();
  }
}
let refreshAfterFlight=false;
function pollingInterval(){return document.hidden ? 20000 : 4000;}
function scheduleNextRefresh(){
  if(refreshTimer)clearTimeout(refreshTimer);
  refreshTimer=setTimeout(async()=>{
    await refresh();
    if(refreshAfterFlight){refreshAfterFlight=false;await refresh();}
    scheduleNextRefresh();
  },pollingInterval());
}
async function command(url,payload,method="POST") {
  try { await api(url,method,payload); await refresh(); }
  catch(err){toast("Amal bajarilmadi: "+err.message);}
}
async function openPlaybook(id) {
  try {
    const p=await api("/api/playbooks/"+encodeURIComponent(id));
    $("protocolTitle").textContent=p.title;
    $("protocolSteps").innerHTML=p.steps.map(x=>`<li>${esc(x)}</li>`).join("");
    $("protocolModal").classList.remove("hidden");
  } catch(err){toast("Yo‘riqnoma topilmadi: "+err.message);}
}
$("crewGrid").addEventListener("click",e=>{
  const card=e.target.closest("[data-crew]");if(!card)return;
  selectedCrew=card.dataset.crew;location.hash="#individual";if(activeView==="individual")refresh();
});
$("selectedCrew").addEventListener("change",e=>{selectedCrew=e.target.value;if(state && !inFlight)renderActiveView(state);else refreshAfterFlight=true;});
$("scenario").addEventListener("change",e=>command("/api/scenario",{scenario:e.target.value}));
$("manualSymptom").addEventListener("change",e=>{
  if(selectedCrew)command(`/api/crew/${encodeURIComponent(selectedCrew)}/symptoms`,{symptoms:e.target.value?[e.target.value]:[]});
});
$("toggleLink").addEventListener("click",()=>{if(state)command("/api/link",{available:!state.earth_link});});
$("forceStep").addEventListener("click",()=>command("/api/step",{}));
$("crewAddForm").addEventListener("submit",async e=>{
  e.preventDefault();
  const name=$("newCrewName").value.trim();
  if(!name)return;
  try {
    const result=await api("/api/crew","POST",{name,zone_id:$("newCrewZone").value});
    selectedCrew=result.crew[result.crew.length-1].crew_id;
    $("newCrewName").value="";await refresh();
  }catch(err){toast("Ekipaj qo‘shilmadi: "+err.message);}
});
$("removeCrew").addEventListener("click",()=>{
  if(!selectedCrew)return;
  if(!window.confirm(`${selectedCrew} ekipaj ro‘yxatidan chiqarilsinmi? (Faqat DEMO)`))return;
  command(`/api/crew/${encodeURIComponent(selectedCrew)}`,undefined,"DELETE");
});
for(const id of ["alertList","findingList"]){
  $(id).addEventListener("click",e=>{
    const start=e.target.closest("[data-start-protocol]");
    if(start) { beginCase(start.dataset.startProtocol, start.dataset.startCrew.split(",").filter(Boolean),
                          start.dataset.startZones.split(",").filter(Boolean), start.dataset.startCode); return; }
    const b=e.target.closest("[data-protocol]");if(b)openPlaybook(b.dataset.protocol);
  });
}
function closeModal(){$("protocolModal").classList.add("hidden");}
$("closeModal").addEventListener("click",closeModal);
$("closeModalBottom").addEventListener("click",closeModal);
$("protocolModal").addEventListener("click",e=>{if(e.target.id==="protocolModal")closeModal();});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal();});
let resizeTimer;
window.addEventListener('resize',()=>{
  if(activeView!=='individual'||!state)return;
  clearTimeout(resizeTimer);
  resizeTimer=setTimeout(()=>{if(!inFlight)renderActiveView(state);},200);
});
window.addEventListener('hashchange',activateView);
document.addEventListener('visibilitychange',()=>{scheduleNextRefresh();if(!document.hidden)refresh();});
activateView();
refresh().then(scheduleNextRefresh);


/* Stage 3: offline DEMO case tracking. Entirely separate from clinical decisions and AI. */
let protocols = [];
let crewSignature = "";
let currentIncidentId = null;
let loadedIncidents = [];
const statusText = {pending:"Kutilmoqda", acknowledged:"Ko‘rib chiqildi", completed:"Bajarildi (DEMO)", blocked:"Bloklangan"};
const approvalNotice = "DEMO / tibbiy tasdiqlanmagan. Bu qadamlar haqiqiy davolash ko‘rsatmasi emas.";
function checkedValues(container) {
  return [...$(container).querySelectorAll('input[type="checkbox"]:checked')].map(el=>el.value);
}
function syncCaseSelectors(data) {
  const signature = JSON.stringify(data.crew.map(p => [p.crew_id,p.name,p.zone_id]));
  if(signature === crewSignature) return;
  const oldCrew=new Set(checkedValues("incidentCrewChoices")), oldZones=new Set(checkedValues("incidentZoneChoices"));
  const oldActor=$('incidentActor').value;
  crewSignature=signature;
  $('incidentCrewChoices').innerHTML=data.crew.map(p => `<label class="check-choice"><input type="checkbox" value="${esc(p.crew_id)}" ${oldCrew.has(p.crew_id)?'checked':''}> ${esc(p.name)} <small>${esc(p.zone_id)}</small></label>`).join('');
  $('incidentZoneChoices').innerHTML=data.zones.map(z => `<label class="check-choice"><input type="checkbox" value="${esc(z.zone_id)}" ${oldZones.has(z.zone_id)?'checked':''}> ${esc(z.zone_id)} <small>${esc(z.name)}</small></label>`).join('');
  $('incidentActor').innerHTML=data.crew.map(p=>`<option value="${esc(p.crew_id)}">${esc(p.name)}</option>`).join('');
  if(data.crew.some(p=>p.crew_id===oldActor))$('incidentActor').value=oldActor;
  if(!checkedValues("incidentCrewChoices").length && selectedCrew) {
    const input=$('incidentCrewChoices').querySelector(`input[value="${CSS.escape(selectedCrew)}"]`);
    if(input)input.checked=true;
  }
}
function caseActorOptions(selected) {
  return (state?.crew||[]).map(p=>`<option value="${esc(p.crew_id)}" ${p.crew_id===selected?'selected':''}>${esc(p.name)}</option>`).join('');
}
function renderProtocolCatalog() {
  $('incidentProtocol').innerHTML = protocols.map(p=>`<option value="${esc(p.id)}">${esc(p.title)}</option>`).join('');
  $('protocolCatalog').innerHTML = protocols.map(p => `<div class="protocol-item">
    <div><strong>${esc(p.title)}</strong><p>${esc(p.description)}</p><span class="proto-version">${esc(p.version)} · ${esc(p.scope)}</span></div>
    <button class="link-button" data-protocol-catalog="${esc(p.id)}" type="button">Ko‘rish</button>
  </div>`).join('');
}
function renderResources(resources) {
  $('resourceList').innerHTML = resources.map(r=>`<div class="resource-item"><span>${esc(r.name)}</span><span class="mini-pill ${r.available?'normal':'attention'}">${r.available?'SIM: BOR':'SIM: YO‘Q'}</span></div>`).join('');
}
let stage3Promise = null;
let stage3Loaded = false;
async function ensureStage3(){
  if(stage3Loaded)return;
  if(stage3Promise)return stage3Promise;
  stage3Promise=(async()=>{
    const [p,r] = await Promise.all([api('/api/protocols'),api('/api/resources')]);
    protocols=p.items;
    renderProtocolCatalog();renderResources(r.items);
    await loadIncidents();
    stage3Loaded=true;
  })();
  try{await stage3Promise;}catch(err){stage3Promise=null;toast('Yordam markazini yuklashda xato: '+err.message);}
}
async function beginCase(protocolId, crewIds=[], zoneIds=[], code='MANUAL_REPORT') {
  location.hash='#emergency';
  if(activeView!=='emergency')activateView();
  await ensureStage3();
  if(state)syncCaseSelectors(state);
  if(!protocols.some(p=>p.id===protocolId)) { toast('Protokol topilmadi'); return; }
  $('incidentProtocol').value=protocolId;
  $('incidentOrigin').value=code || 'MANUAL_REPORT';
  for(const input of $('incidentCrewChoices').querySelectorAll('input'))input.checked=crewIds.includes(input.value);
  for(const input of $('incidentZoneChoices').querySelectorAll('input'))input.checked=zoneIds.includes(input.value);
  if(!crewIds.length && !zoneIds.length && selectedCrew) {
    const input=[...$('incidentCrewChoices').querySelectorAll('input')].find(x=>x.value===selectedCrew);
    if(input)input.checked=true;
  }
  document.getElementById('emergency').scrollIntoView({behavior:'smooth',block:'start'});
  $('incidentProtocol').focus({preventScroll:true});
}
function renderIncidentList(items) {
  loadedIncidents=items;
  const open=items.filter(i=>i.status==='open').length;
  $('caseStats').textContent=`${open} ochiq / ${items.length} jami · SQLite`;
  $('incidentList').innerHTML = items.length ? items.map(i => {
    const people = i.crew_snapshot.map(p=>p.name).join(', ');
    return `<button type="button" class="case-item ${i.id===currentIncidentId?'active':''}" data-case-id="${esc(i.id)}">
      <span class="case-id">${esc(i.id)}</span><span class="mini-pill ${i.status==='open'?'attention':'normal'}">${i.status==='open'?'OCHIQ':'KO‘RIB CHIQILGAN'}</span>
      <strong>${esc(protocols.find(p=>p.id===i.protocol_id)?.title||i.protocol_id)}</strong>
      <span class="case-meta">${esc(people||i.zone_ids.join(', ')||'Umumiy')} · ${esc(new Date(i.created_at).toLocaleString('uz-UZ'))}</span>
    </button>`;
  }).join('') : '<div class="empty">Hali yordam hodisasi yaratilmagan. Protokol tanlab yangi hodisa oching.</div>';
}
async function loadIncidents(preferred=null) {
  const response=await api('/api/incidents?limit=80');
  const items=response.items;
  if(preferred)currentIncidentId=preferred;
  if(currentIncidentId && !items.some(i=>i.id===currentIncidentId)) currentIncidentId=null;
  if(!currentIncidentId && items.length)currentIncidentId=items[0].id;
  renderIncidentList(items);
  if(currentIncidentId)await showIncident(currentIncidentId);
}
async function showIncident(id) {
  try {
    const record=await api('/api/incidents/'+encodeURIComponent(id));
    currentIncidentId=id;
    renderIncidentList(loadedIncidents);
    const people=record.crew_snapshot.map(p=>`${esc(p.name)} (${esc(p.crew_id)})`).join(', ');
    const readOnly=record.status!=='open';
    const steps=record.steps_snapshot.map(s=>{
      const saved=record.steps.find(a=>a.step_index===s.index);
      return `<div class="case-step" data-step="${s.index}">
        <div class="case-step-main"><span class="step-index">${s.index+1}</span><div><strong>${esc(s.title)}</strong>
        <p class="case-meta">Oxirgi holat: <b>${esc(statusText[saved.status]||saved.status)}</b>${saved.actor_name?' · '+esc(saved.actor_name):''}</p></div></div>
        ${readOnly?'':`<div class="case-step-actions"><label>Holat<select data-step-state>
          ${Object.entries(statusText).map(([val,label])=>`<option value="${val}" ${val===saved.status?'selected':''}>${esc(label)}</option>`).join('')}
          </select></label><label>Kim qayd etdi<select data-step-actor>${caseActorOptions(state?.crew[0]?.crew_id)}</select></label>
          <label class="case-step-note">Izoh<input data-step-note maxlength="500" value="${esc(saved.note||'')}" placeholder="Ixtiyoriy qayd" /></label>
          <button type="button" class="button" data-save-step="${s.index}">Saqlash</button></div>`}
        </div>`;
    }).join('');
    const evidence=record.evidence_snapshot;
    const audit=record.audit.map(a=>`<li><time>${esc(new Date(a.created_at).toLocaleString('uz-UZ'))}</time> · ${esc(a.action)} · ${esc(a.actor_name||'—')} </li>`).join('');
    $('caseDetail').innerHTML=`<div class="section-head case-detail-head"><div><div class="eyebrow">INCIDENT WORKFLOW · ${esc(record.approval_snapshot)}</div><h3>${esc(record.id)}</h3></div><span class="mini-pill ${readOnly?'normal':'attention'}">${readOnly?'KO‘RIB CHIQILGAN':'OCHIQ'}</span></div>
      <p class="warning-copy">${esc(approvalNotice)} Protokol versiyasi: <b>${esc(record.protocol_version)}</b>. Kiritilgan harakatlar faqat simulyatsiya jurnaliga yoziladi.</p>
      <div class="case-summary"><div><small>PROTOKOL</small><strong>${esc(protocols.find(p=>p.id===record.protocol_id)?.title||record.protocol_id)}</strong></div>
      <div><small>KOSMONAVTLAR</small><strong>${people||'—'}</strong></div><div><small>MODULLAR</small><strong>${esc(record.zone_ids.join(', ')||'—')}</strong></div>
      <div><small>MANBA</small><strong>${esc(record.origin_code)}</strong></div></div>
      <p class="case-meta">Signal dalili: ${esc(evidence.source||'unknown')} · Sana: ${esc(evidence.timestamp||record.created_at)} · Tibbiy tasdiqlangan: YO‘Q</p>
      ${record.missing_resources.length?`<div class="missing-resources">⚠ DEMO inventarda yetishmaydi: ${esc(record.missing_resources.join(', '))}. Tekshiruvni bloklash yoki resurs holatini qayd etish mumkin, hech bir muolajani avtomatik bajarmang.</div>`:''}
      <div class="section-head"><h3>Tekshiruv qadamlari</h3><span class="subtag">Har qadam alohida audit qilinadi</span></div>
      <div class="case-steps">${steps}</div>
      ${readOnly?'':`<div class="case-review"><label>Qaydni yakunlovchi ekipaj a’zosi <select id="reviewActor">${caseActorOptions(state?.crew[0]?.crew_id)}</select></label>
        <label>Yakuniy qayd <input id="reviewNote" maxlength="500" placeholder="Demo tekshiruv yakunlandi..." /></label>
        <button id="reviewCaseButton" class="button primary" type="button">Tekshiruvni yakunlash</button></div>`}
      <details class="audit-log"><summary>Audit tarixi (${record.audit.length})</summary><ol>${audit}</ol></details>`;
  }catch(err){toast('Hodisani ochishda xato: '+err.message);}
}
$('incidentForm').addEventListener('submit',async e=>{
  e.preventDefault();
  const protocol_id=$('incidentProtocol').value;
  const crew_ids=checkedValues('incidentCrewChoices'), zone_ids=checkedValues('incidentZoneChoices');
  const payload={protocol_id, crew_ids, zone_ids, origin_code:$('incidentOrigin').value||'MANUAL_REPORT',
                actor_id:$('incidentActor').value,note:$('incidentNote').value};
  const btn=$('incidentForm').querySelector('button[type="submit"]');btn.disabled=true;
  try{
    const created=await api('/api/incidents','POST',payload);
    $('incidentNote').value=''; $('incidentOrigin').value='MANUAL_REPORT';
    await loadIncidents(created.id); await refresh();
    document.getElementById('caseDetail').scrollIntoView({behavior:'smooth',block:'start'});
    toast('DEMO hodisa yaratildi: '+created.id);
  }catch(err){toast('Hodisa yaratilmadi: '+err.message);}finally{btn.disabled=false;}
});
$('incidentList').addEventListener('click',e=>{
  const b=e.target.closest('[data-case-id]');if(b)showIncident(b.dataset.caseId);
});
$('caseDetail').addEventListener('click',async e=>{
  const step=e.target.closest('[data-save-step]');
  if(step){
    const row=step.closest('[data-step]'); const index=Number(step.dataset.saveStep);
    step.disabled=true;
    try{
      await api(`/api/incidents/${encodeURIComponent(currentIncidentId)}/steps/${index}`,'PATCH',{
        status:row.querySelector('[data-step-state]').value, actor_id:row.querySelector('[data-step-actor]').value,
        note:row.querySelector('[data-step-note]').value });
      await loadIncidents(currentIncidentId);await refresh();
      toast('Qadam DEMO jurnalga yozildi');
    }catch(err){toast('Saqlanmadi: '+err.message);step.disabled=false;}return;
  }
  if(e.target.closest('#reviewCaseButton')){
    const btn=e.target.closest('button');btn.disabled=true;
    try{
      await api(`/api/incidents/${encodeURIComponent(currentIncidentId)}/review`,'POST',{
        actor_id:$('reviewActor').value,note:$('reviewNote').value});
      await loadIncidents(currentIncidentId);await refresh();toast('Demo tekshiruv yakunlandi');
    }catch(err){toast('Yakunlanmadi: '+err.message);btn.disabled=false;}
  }
});
$('protocolCatalog').addEventListener('click',e=>{
  const b=e.target.closest('[data-protocol-catalog]');if(b)openPlaybook(b.dataset.protocolCatalog);
});
$('reloadIncidents').addEventListener('click',()=>loadIncidents().catch(err=>toast(err.message)));
$('mobileMenuButton').addEventListener('click',()=>{
  const expanded=$('mobileMenuButton').getAttribute('aria-expanded')==='true';
  $('mobileMenuButton').setAttribute('aria-expanded',String(!expanded));
  $('mainNav').classList.toggle('nav-open',!expanded);
});
$('mainNav').addEventListener('click',e=>{
  if(e.target.closest('a')){$('mainNav').classList.remove('nav-open');$('mobileMenuButton').setAttribute('aria-expanded','false');}
});
// Stage 3 data is fetched only when the emergency page is opened.
