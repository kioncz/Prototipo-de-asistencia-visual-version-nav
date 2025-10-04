// Modo navegación integrado (overlay sobre el mismo video)
// Encapsulado para evitar colisiones globales.
(function(){
let activo = false;
let enviando = false;
let ultimoEnvio = 0;
let overlay, ctx;
let polyCache = null, polyId = null;
let calidad = 0.8;
let intervaloBase = 300, intervaloActual = intervaloBase;
const MIN_INTERVALO = 120, MAX_INTERVALO = 600;
let conf = 0.25, iou = 0.45, imgsz = 640, dinamico = true;
const suavizado = {}; const ALPHA = 0.4;
let ultimoFPSCalc = performance.now(), framesProcesados = 0, fpsEstimado = 0;
let rafId = null;
let abortCtrl = null;
// --- Proximidad / vibración ---
// Vibración de proximidad continua
let proximityVibrationEnabled = true;
let lastContinuousVibrationTs = 0; // último disparo global
// Intervalos según pasos (ms): más cerca => más frecuencia
const INTERVALO_PASOS = { 1: 450, 2: 650, 3: 900, 4: 1200, 5: 1600 };

function vibrarPorPasos(pasos){
  if (!proximityVibrationEnabled) return;
  if (!navigator.vibrate) return;
  // Patrones: menor pasos => mayor intensidad
  const base = {
    1: [260,120,260],
    2: [180,90,180],
    3: [140,80,140],
    4: [100,70,100],
    5: 80
  };
  let patron = base[pasos];
  if (!patron) return;
  // Ajuste por nivel global de vibración si existe
  if (window.vibracionControles){
    const nivel = window.vibracionControles.getNivelActual();
    const factor = (nivel===1?0.9:(nivel===2?1.0:1.15));
    if (Array.isArray(patron)) patron = patron.map(t=>Math.round(t*factor)); else patron = Math.round(patron*factor);
  }
  navigator.vibrate(patron);
}

function vibracionContinuaProximidad(dets){
  // Seleccionar el obstáculo en_camino con menor número de pasos (más cercano)
  let mejor = null;
  for (const d of dets){
    if (!d.en_camino) continue;
    if (d.pasos == null) continue;
    if (d.pasos < 1 || d.pasos > 5) continue;
    if (!mejor || d.pasos < mejor.pasos) mejor = d;
  }
  if (!mejor) return; // nada cercano
  const pasos = mejor.pasos;
  const intervalo = INTERVALO_PASOS[pasos] || 1000;
  const ahora = Date.now();
  if (ahora - lastContinuousVibrationTs >= intervalo){
    vibrarPorPasos(pasos);
    lastContinuousVibrationTs = ahora;
  }
}

function navigationActive(){ return activo; }

function ensureOverlay(){
  if (overlay) return;
  const video = document.getElementById('video');
  if (!video) return;
  const wrapper = video.parentElement || document.body;
  wrapper.style.position = 'relative';
  overlay = document.createElement('canvas');
  overlay.id = 'nav_overlay';
  overlay.style.position = 'absolute';
  overlay.style.left = '0';
  overlay.style.top = '0';
  overlay.style.pointerEvents = 'none';
  overlay.style.zIndex = '20';
  overlay.width = video.videoWidth || 640;
  overlay.height = video.videoHeight || 480;
  overlay.style.width = video.clientWidth + 'px';
  overlay.style.height = video.clientHeight + 'px';
  ctx = overlay.getContext('2d');
  wrapper.appendChild(overlay);
  // (export eliminado - API expuesta vía window.navigationMode)
}

function ajustar(){
  if (!overlay) return;
  const video = document.getElementById('video');
  if (!video) return;
  if (video.videoWidth){
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
  }
  overlay.style.width = video.clientWidth + 'px';
  overlay.style.height = video.clientHeight + 'px';
}

function suavizar(label, box){
  if(!suavizado[label]) { suavizado[label] = {...box}; return box; }
  const p = suavizado[label];
  const s = {x1: p.x1 + ALPHA*(box.x1-p.x1), y1: p.y1 + ALPHA*(box.y1-p.y1), x2: p.x2 + ALPHA*(box.x2-p.x2), y2: p.y2 + ALPHA*(box.y2-p.y2)};
  suavizado[label] = s; return s;
}

function capturarBase64(){
  const video = document.getElementById('video');
  if (!video || !video.videoWidth) return null;
  const off = document.createElement('canvas');
  off.width = video.videoWidth; off.height = video.videoHeight;
  off.getContext('2d').drawImage(video,0,0);
  return off.toDataURL('image/jpeg', calidad);
}

async function enviarFrame(){
  if (!activo || enviando) return;
  const b64 = capturarBase64();
  if (!b64) return;
  enviando = true;
  abortCtrl = new AbortController();
  try {
    const resp = await fetch('/navegacion_frame', {
      method:'POST', headers:{'Content-Type':'application/json'}, signal: abortCtrl.signal,
      body: JSON.stringify({frame:b64, conf, iou, imgsz, compact:true, poly_id: polyId})
    });
    if (!resp.ok) throw new Error('resp '+resp.status);
    const json = await resp.json();
    if (json.d){
      framesProcesados++;
      if (performance.now()-ultimoFPSCalc>1000){ fpsEstimado=framesProcesados; framesProcesados=0; ultimoFPSCalc=performance.now(); }
      if (json.pid) polyId = json.pid;
      if (json.p) polyCache = json.p;
      const dets = json.d.map(a=>({
        x1:a[0], y1:a[1], x2:a[2], y2:a[3], label:a[4], en_camino:!!a[5], confidencia:a[6], base_x:a[7], base_y:a[8],
        dist_cm: a.length>9 ? a[9] : null,
        pasos: a.length>10 ? a[10] : null
      }));
      dibujar(dets, {total: json.t, en_camino: json.ec, conf: json.c, iou: json.i, imgsz: json.g, inference_ms: json.ms, camino_poly: polyCache});
      if (dinamico && json.ms){
        if (json.ms > 320) intervaloActual = Math.min(MAX_INTERVALO, intervaloActual + 40);
        else if (json.ms < 160) intervaloActual = Math.max(MIN_INTERVALO, intervaloActual - 30);
      }
      if (json.ms > 350 && calidad > 0.55) calidad -= 0.05; else if (json.ms < 180 && calidad < 0.85) calidad += 0.05;
    }
  } catch(e){
    // Silent catch; navigation may stop mid-request
  } finally { enviando = false; }
}

function dibujar(dets, meta){
  if (!ctx || !overlay) return;
  ajustar();
  ctx.clearRect(0,0,overlay.width,overlay.height);
  const poly = meta.camino_poly || polyCache || [];
  if (poly && poly.length===4){
    ctx.strokeStyle = 'rgba(0,255,0,0.85)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(poly[0][0], poly[0][1]);
    for (let i=1;i<poly.length;i++) ctx.lineTo(poly[i][0], poly[i][1]);
    ctx.closePath(); ctx.stroke();
  }
  const obstEnCamino = [];
  dets.forEach(d => {
    const sm = suavizar(d.label + (d.en_camino?'#c':''), {x1:d.x1,y1:d.y1,x2:d.x2,y2:d.y2});
    const color = d.en_camino ? 'rgba(255,0,0,0.9)' : 'rgba(0,128,255,0.9)';
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.strokeRect(sm.x1,sm.y1,sm.x2-sm.x1,sm.y2-sm.y1);
    ctx.font = '13px sans-serif'; ctx.fillStyle = color;
    const confTxt = d.confidencia!=null ? ` ${(d.confidencia*100).toFixed(1)}%` : '';
    let extra = '';
    if (d.pasos!=null && d.pasos>=1 && d.pasos<=5) extra = ` ${d.pasos}p`;
    ctx.fillText(d.label + confTxt + extra, sm.x1+4, sm.y1+14);
    if (d.base_x!=null && d.base_y!=null){ ctx.beginPath(); ctx.arc(d.base_x,d.base_y,4,0,Math.PI*2); ctx.fill(); }
    if (d.en_camino) obstEnCamino.push(d.label);
  });
  // Vibración continua basada en el obstáculo más cercano
  vibracionContinuaProximidad(dets);
  if (obstEnCamino.length){
    ctx.font = '15px sans-serif'; ctx.fillStyle = 'rgba(255,0,0,0.9)';
    ctx.fillText('En camino: '+[...new Set(obstEnCamino)].join(', '), 10, 30);
  }
  // Sin panel de métricas
}

function loop(ts){
  if (!activo){ return; }
  if (!ultimoEnvio || (ts - ultimoEnvio) > intervaloActual){ ultimoEnvio = ts || performance.now(); enviarFrame(); }
  rafId = requestAnimationFrame(loop);
}

function startNavigation(){
  if (activo) return;
  activo = true; ultimoEnvio = 0; intervaloActual = intervaloBase; calidad = 0.8;
  ensureOverlay();
  const estado = document.getElementById('estado');
  if (estado) estado.textContent = 'Modo navegación activo ("detener navegación" para salir)';
  rafId = requestAnimationFrame(loop);
}

function stopNavigation(){
  if (!activo) return;
  activo = false;
  if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
  if (abortCtrl){ try { abortCtrl.abort(); } catch(_e){} }
  enviando = false;
  if (ctx && overlay){ ctx.clearRect(0,0,overlay.width,overlay.height); }
  const estado = document.getElementById('estado');
  if (estado) estado.textContent = 'Modo navegación detenido';
  if (overlay && overlay.parentNode){ overlay.parentNode.removeChild(overlay); }
  overlay = null; ctx = null; polyCache = null; polyId = null;
  Object.keys(suavizado).forEach(k=>delete suavizado[k]);
}

window.navigationMode = { startNavigation, stopNavigation, navigationActive };
// API para controlar vibración de proximidad y pruebas manuales
window.navigationMode.toggleProximityVibration = (on)=>{ proximityVibrationEnabled = !!on; };
window.navigationMode.proximityTest = (pasos)=> vibrarPorPasos(pasos);
})();
