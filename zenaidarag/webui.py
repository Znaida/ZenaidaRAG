"""Interfaz web de escritorio de ZenaidaVet (Fase 7).

Una sola pagina HTML autocontenida (CSS + JS inline, sin CDNs) servida por la
API en `/`. Se muestra dentro de una ventana nativa (pywebview) o en el
navegador. Consume los endpoints existentes: /health, /ask (SSE), /documents,
/shutdown.
"""
from __future__ import annotations

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZenaidaVet</title>
<link rel="icon" type="image/png" href="/logo.png">
<style>
  :root { --bg:#0f172a; --panel:#1e293b; --accent:#14b8a6; --text:#e2e8f0; --muted:#94a3b8; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: 'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--text); height:100vh; display:flex; flex-direction:column; }
  header { padding:14px 20px; background:var(--panel); display:flex; align-items:center; gap:12px; border-bottom:2px solid var(--accent); }
  header h1 { font-size:20px; margin:0; }
  header .logo { width:34px; height:34px; border-radius:50%; object-fit:cover; display:block; }
  header .llm-select { margin-left:auto; background:#0f172a; color:var(--text); border:1px solid #334155; border-radius:8px; padding:6px 10px; font:inherit; font-size:13px; cursor:pointer; }
  header .llm-select:focus { outline:2px solid var(--accent); }
  header .status { margin-left:14px; font-size:13px; color:var(--muted); }
  header .dot { display:inline-block; width:9px; height:9px; border-radius:50%; background:#eab308; margin-right:6px; }
  header .dot.ok { background:#22c55e; }
  main { flex:1; display:flex; min-height:0; }
  .sidebar { width:290px; background:var(--panel); padding:16px; display:flex; flex-direction:column; gap:12px; border-right:1px solid #334155; }
  .sidebar h2 { font-size:13px; text-transform:uppercase; color:var(--muted); margin:0; letter-spacing:.5px; }
  #docs { list-style:none; margin:0; padding:0; overflow-y:auto; flex:1; }
  #docs li { padding:8px 10px; background:#0f172a; border-radius:8px; margin-bottom:6px; font-size:13px; display:flex; justify-content:space-between; gap:8px; }
  #docs li .meta { display:flex; align-items:center; gap:8px; }
  #docs li .chunks { color:var(--muted); font-size:11px; white-space:nowrap; }
  #docs li .del { background:none; border:none; color:#64748b; cursor:pointer; font-size:14px; padding:2px 4px; border-radius:5px; }
  #docs li .del:hover { background:#7f1d1d; color:#fff; }
  #docs .empty { color:var(--muted); font-style:italic; }
  .progress { background:#0f172a; border-radius:10px; padding:12px 14px; align-self:flex-start; max-width:78%; width:340px; }
  .progress .label { font-size:13px; margin-bottom:8px; color:var(--text); }
  .progress .bar { height:10px; background:#334155; border-radius:6px; overflow:hidden; }
  .progress .fill { height:100%; width:0%; background:var(--accent); transition:width .2s ease; }
  .progress .pct { font-size:11px; color:var(--muted); margin-top:6px; text-align:right; }
  button { font:inherit; border:none; border-radius:8px; padding:10px 14px; cursor:pointer; font-weight:600; }
  .btn-accent { background:var(--accent); color:#042f2e; }
  .btn-accent:hover { filter:brightness(1.1); }
  .btn-danger { background:#dc2626; color:#fff; }
  .btn-danger:hover { filter:brightness(1.1); }
  .chat { flex:1; display:flex; flex-direction:column; min-width:0; }
  #messages { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:14px; }
  .msg { max-width:78%; padding:11px 14px; border-radius:12px; line-height:1.5; white-space:pre-wrap; }
  .msg.user { align-self:flex-end; background:var(--accent); color:#042f2e; }
  .msg.bot { align-self:flex-start; background:var(--panel); }
  .msg .sources { margin-top:8px; font-size:12px; color:var(--muted); border-top:1px solid #334155; padding-top:6px; }
  .composer { display:flex; gap:10px; padding:14px 20px; background:var(--panel); border-top:1px solid #334155; }
  .composer input { flex:1; padding:12px; border-radius:8px; border:1px solid #334155; background:#0f172a; color:var(--text); font:inherit; }
  .composer input:focus { outline:2px solid var(--accent); }
  footer { padding:10px 20px; background:var(--panel); border-top:1px solid #334155; display:flex; align-items:center; }
  footer .hint { font-size:12px; color:var(--muted); }
  footer .spacer { flex:1; }
  .disclaimer { font-size:11px; color:var(--muted); padding:0 20px 8px; background:var(--panel); }
</style>
</head>
<body>
  <header>
    <img class="logo" src="/logo.png" alt="ZenaidaVet">
    <h1>ZenaidaVet</h1>
    <select class="llm-select" id="llmSelect" title="Motor de lenguaje (LLM)"></select>
    <span class="status"><span class="dot" id="dot"></span><span id="statusText">Iniciando…</span></span>
  </header>
  <main>
    <aside class="sidebar">
      <h2>Documentos cargados</h2>
      <ul id="docs"><li class="empty">Cargando…</li></ul>
      <button class="btn-accent" id="uploadBtn">＋ Cargar documentos</button>
      <input type="file" id="fileInput" multiple hidden
             accept=".pdf,.docx,.md,.txt,.csv,.xlsx">
    </aside>
    <section class="chat">
      <div id="messages"></div>
      <div class="disclaimer">Asistente de apoyo informativo. No reemplaza el criterio de un médico veterinario.</div>
      <div class="composer">
        <input id="q" type="text" placeholder="Escribí tu pregunta…" autocomplete="off">
        <button class="btn-accent" id="sendBtn">Enviar</button>
      </div>
    </section>
  </main>
  <footer>
    <span class="hint">ZenaidaVet corre 100% local en esta computadora.</span>
    <span class="spacer"></span>
    <button class="btn-danger" id="shutdownBtn">⏻ Apagar</button>
  </footer>

<script>
const $ = (id) => document.getElementById(id);

async function refreshHealth() {
  try {
    const r = await fetch('/health');
    const h = await r.json();
    $('dot').classList.add('ok');
    $('statusText').textContent = h.llm_model + ' · ' + (h.indexed_chunks ?? 0) + ' fragmentos';
  } catch (e) {
    $('statusText').textContent = 'Sin conexión';
  }
}

async function loadLLM() {
  const sel = $('llmSelect');
  try {
    const r = await fetch('/llm');
    const d = await r.json();
    sel.innerHTML = '';
    for (const opt of d.options) {
      const o = document.createElement('option');
      o.value = opt.id; o.textContent = opt.label;
      if (opt.id === d.current) o.selected = true;
      sel.appendChild(o);
    }
    sel.dataset.current = d.current;
  } catch (e) { /* si falla, el selector queda vacio; no bloquea el chat */ }
}

async function changeLLM(e) {
  const sel = $('llmSelect');
  const provider = sel.value;
  const prev = sel.dataset.current || provider;
  try {
    const r = await fetch('/llm', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({provider})
    });
    const d = await r.json();
    if (!d.ok) {
      addMsg('No se pudo cambiar a ' + provider + ': ' + d.error, 'bot');
      sel.value = prev;            // revertir la seleccion visual
      return;
    }
    sel.dataset.current = provider;
    addMsg('Motor de lenguaje cambiado a ' + provider + ' (' + d.model + ').', 'bot');
    refreshHealth();
  } catch (err) {
    addMsg('Error al cambiar el motor de lenguaje.', 'bot');
    sel.value = prev;
  }
}

async function refreshDocs() {
  const ul = $('docs');
  try {
    const r = await fetch('/documents');
    const docs = await r.json();
    if (!docs.length) { ul.innerHTML = '<li class="empty">Aún no hay documentos.</li>'; return; }
    ul.innerHTML = '';
    for (const d of docs) {
      const li = document.createElement('li');
      const name = document.createElement('span');
      name.textContent = d.source;
      const meta = document.createElement('span');
      meta.className = 'meta';
      meta.innerHTML = '<span class="chunks">' + d.chunks + ' frag.</span>';
      const del = document.createElement('button');
      del.className = 'del'; del.title = 'Eliminar documento'; del.textContent = '🗑';
      del.onclick = () => deleteDoc(d.source);
      meta.appendChild(del);
      li.appendChild(name); li.appendChild(meta);
      ul.appendChild(li);
    }
  } catch (e) { ul.innerHTML = '<li class="empty">Error al listar.</li>'; }
}

function addMsg(text, cls, sources) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  if (sources && sources.length) {
    const s = document.createElement('div');
    s.className = 'sources';
    s.textContent = 'Fuentes: ' + sources.join(', ');
    div.appendChild(s);
  }
  $('messages').appendChild(div);
  $('messages').scrollTop = $('messages').scrollHeight;
  return div;
}

async function ask() {
  const q = $('q').value.trim();
  if (!q) return;
  $('q').value = '';
  addMsg(q, 'user');
  const bot = addMsg('', 'bot');
  try {
    const resp = await fetch('/ask', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({question:q})
    });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '', answer = '', sources = [];
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buf += dec.decode(value, {stream:true});
      buf = buf.replace(/\\r/g, '');   // normaliza CRLF (SSE puede usar \\r\\n)
      const parts = buf.split('\\n\\n');
      buf = parts.pop();
      for (const block of parts) {
        let ev = 'message', data = '';
        for (const line of block.split('\\n')) {
          if (line.startsWith('event:')) ev = line.slice(6).trim();
          else if (line.startsWith('data:')) {
            // SSE agrega UN espacio tras "data:"; quitar solo ese, no los del token.
            const d = line.slice(5).replace(/^ /, '');
            data += (data ? '\\n' : '') + d;
          }
        }
        if (ev === 'token') { answer += data; bot.textContent = answer; }
        else if (ev === 'sources') { try { sources = JSON.parse(data); } catch(e){} }
      }
      $('messages').scrollTop = $('messages').scrollHeight;
    }
    // No mostrar fuentes cuando la respuesta es la negativa honesta.
    const a = answer.toLowerCase();
    const refusal = a.includes('no tengo') && a.includes('suficiente');
    if (sources.length && !refusal) {
      const s = document.createElement('div');
      s.className = 'sources'; s.textContent = 'Fuentes: ' + sources.join(', ');
      bot.appendChild(s);
    }
  } catch (e) { bot.textContent = 'Error de conexión.'; }
}

function addProgress(label) {
  const box = document.createElement('div');
  box.className = 'progress';
  box.innerHTML = '<div class="label"></div><div class="bar"><div class="fill"></div></div><div class="pct">0%</div>';
  box.querySelector('.label').textContent = label;
  $('messages').appendChild(box);
  $('messages').scrollTop = $('messages').scrollHeight;
  return box;
}

function ingestWithProgress(name) {
  // Devuelve una promesa que se resuelve cuando termina la ingesta del archivo.
  return new Promise((resolve) => {
    const box = addProgress('Procesando ' + name + '…');
    const fill = box.querySelector('.fill');
    const pct = box.querySelector('.pct');
    const es = new EventSource('/documents/ingest?name=' + encodeURIComponent(name));
    es.addEventListener('progress', (e) => {
      const p = JSON.parse(e.data);
      fill.style.width = p.percent + '%';
      pct.textContent = p.percent + '% (' + p.done + '/' + p.total + ' fragmentos)';
    });
    es.addEventListener('done', (e) => {
      const p = JSON.parse(e.data);
      fill.style.width = '100%';
      box.querySelector('.label').textContent = '✓ ' + name + ' cargado';
      pct.textContent = p.chunks + ' fragmentos indexados';
      es.close(); resolve();
    });
    es.addEventListener('error', () => {
      box.querySelector('.label').textContent = '✗ Error al procesar ' + name;
      es.close(); resolve();
    });
  });
}

async function uploadFiles(files) {
  const fd = new FormData();
  for (const f of files) fd.append('files', f);
  try {
    const r = await fetch('/documents/upload', { method:'POST', body: fd });
    const res = await r.json();
    for (const skip of (res.skipped || [])) addMsg('Formato no soportado: ' + skip, 'bot');
    // Ingesta secuencial con barra de progreso por archivo.
    for (const name of (res.saved || [])) await ingestWithProgress(name);
    refreshDocs(); refreshHealth();
  } catch (e) { addMsg('Error al cargar documentos.', 'bot'); }
}

async function deleteDoc(source) {
  if (!confirm('¿Eliminar "' + source + '" del índice?')) return;
  try {
    await fetch('/documents?source=' + encodeURIComponent(source), { method:'DELETE' });
    refreshDocs(); refreshHealth();
  } catch (e) { addMsg('Error al eliminar el documento.', 'bot'); }
}

async function shutdown() {
  if (!confirm('¿Apagar ZenaidaVet?')) return;
  try { await fetch('/shutdown', {method:'POST'}); } catch(e){}
  document.body.innerHTML = '<div style="display:flex;height:100vh;align-items:center;justify-content:center;color:#94a3b8;font-size:18px;">ZenaidaVet apagado. Ya podés cerrar esta ventana.</div>';
  if (window.pywebview) { try { window.pywebview.api.close(); } catch(e){} }
}

$('sendBtn').onclick = ask;
$('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') ask(); });
$('uploadBtn').onclick = () => $('fileInput').click();
$('fileInput').onchange = (e) => { if (e.target.files.length) uploadFiles(e.target.files); e.target.value=''; };
$('shutdownBtn').onclick = shutdown;
$('llmSelect').onchange = changeLLM;

refreshHealth();
refreshDocs();
loadLLM();
setInterval(refreshHealth, 5000);
</script>
</body>
</html>
"""


def index_page() -> str:
    """Devuelve el HTML de la interfaz."""
    return PAGE
