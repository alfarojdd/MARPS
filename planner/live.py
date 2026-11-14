"""Banco de pruebas interactivo del planificador: controles a la izquierda, mapa a la derecha, recálculo en vivo.

    .venv/bin/python tools/planner/live.py          # http://127.0.0.1:8766

No es el frontend del producto: es una herramienta para ver cómo se comporta el algoritmo. Solo usa la biblioteca
estándar para el servidor; el planificador es el mismo módulo `planner.py`.
"""
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import matplotlib
import numpy as np
from PIL import Image

import planner as P
import report as R

PORT = 8766
LOCK = threading.Lock()
PL = P.Planner()
CLASSIC = {}

CRISM_RGB = {1: (255, 0, 0), 2: (0, 255, 0), 3: (0, 255, 255), 4: (255, 128, 114), 5: (128, 128, 0),
             6: (255, 215, 0), 7: (255, 128, 0), 8: (218, 165, 32), 9: (139, 69, 19), 10: (0, 0, 255)}


def background(kind):
    g = PL.grid
    hs = np.nan_to_num(g["hillshade_ctx"], nan=0.5)
    if kind == "slope":
        rgb = (matplotlib.colormaps["magma_r"](np.clip(PL.F["slope"] / 25, 0, 1))[..., :3] * 255)
    else:
        rgb = np.dstack([hs * 255] * 3)
        if kind == "crism":
            for v, c in CRISM_RGB.items():
                m = g["crism_class"] == v
                rgb[m] = 0.55 * rgb[m] + 0.45 * np.array(c)
    buf = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


BG = {k: background(k) for k in ("relief", "crism", "slope")}


def shadow_background(hour):
    """Relieve con la sombra (azul) y la noche a una hora solar local, del mapa de sombras."""
    hs = np.nan_to_num(PL.grid["hillshade_ctx"], nan=0.5)
    rgb = np.dstack([hs * 255] * 3)
    if PL.sun is not None:
        H, W = hs.shape
        light = PL.sun.map_at(np.full((H, W), hour))
        if not PL.sun.is_day(hour):
            rgb *= 0.2
        else:
            m = light < 0.02
            rgb[m] = 0.35 * rgb[m] + 0.65 * np.array([25, 55, 165])
    buf = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


def meta():
    H, W = PL.H, PL.W
    places = {n: dict(zip(("r", "c"), P.lonlat_to_rc(PL.grid, *ll))) for n, ll in P.PLACES.items()}
    left, top = (float(v) for v in PL.grid["origin_xy"])
    return dict(width=W, height=H, res=P.RES, left=left, top=top, places=places, targets=sorted(P.TARGETS) + ["aqueous"],
                safety=list(P.SAFETY), crism=[dict(v=v, rgb=c) for v, c in CRISM_RGB.items()])


def plan(d):
    mission, system = d.get("mission", {}), d.get("system", {})
    p = P.Params.from_dict(mission)
    key = (p.origin, p.destination, p.return_to_origin)
    with LOCK:
        t = time.perf_counter()
        if key not in CLASSIC:
            CLASSIC[key] = PL.plan(P.classic(p))
        report, route, classic_route = R.build_report(PL, mission, system, CLASSIC[key])
        seconds = time.perf_counter() - t
    W = PL.W
    cells = lambda r: [[int(n % W), int(n // W)] for n in r["path"]] if r and r.get("ok") else []
    charge = report.get("route", {}).get("charging_stop")
    return dict(seconds=seconds, report=report, draw=dict(
        route=cells(route), classic=cells(classic_route),
        pois=[dict(c=int(q["rc"][1]), r=int(q["rc"][0])) for q in (route or {}).get("pois", [])],
        charge=dict(c=charge["rc"][1], r=charge["rc"][0]) if charge else None))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json", code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, default=float).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self._send(PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/meta":
            self._send(meta())
        elif self.path.startswith("/bg/shadow.png"):
            h = float(self.path.split("h=")[1]) if "h=" in self.path else 12.0
            self._send(shadow_background(h), "image/png")
        elif self.path.startswith("/bg/") and self.path[4:].removesuffix(".png") in BG:
            self._send(BG[self.path[4:].removesuffix(".png")], "image/png")
        else:
            self._send(b"not found", "text/plain", 404)

    def do_POST(self):
        if self.path != "/plan":
            return self._send(b"not found", "text/plain", 404)
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self._send(plan(body))
        except (ValueError, KeyError) as e:  # parámetros inválidos: se muestran en la página
            self._send(dict(error=str(e)), code=400)


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Planificador en vivo</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#14171c;--panel:#1d2229;--line:#2e3641;--fg:#e6e9ee;--mute:#8d97a5;--acc:#e4572e;--ok:#5fd38d;--bad:#ff7a66;--warn:#f3c14b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif;display:flex;height:100vh}
#side{width:340px;min-width:340px;padding:14px;overflow:auto;background:var(--panel);border-right:1px solid var(--line)}
#main{flex:1;display:flex;flex-direction:column;min-width:0}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:16px 0 6px}h2:first-child{margin-top:0}
label{display:flex;align-items:center;gap:8px;margin:5px 0}
select,input[type=range]{width:100%}select{background:var(--bg);color:var(--fg);border:1px solid var(--line);padding:4px;border-radius:4px}
.row{display:flex;gap:8px}.row>*{flex:1}.tgt{display:grid;grid-template-columns:20px 1fr 90px;gap:6px;align-items:center;margin:3px 0}
.val{color:var(--mute);font-variant-numeric:tabular-nums}
#mapwrap{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:10px}
canvas{max-width:100%;max-height:100%;border:1px solid var(--line);cursor:crosshair;background:#000}
#bottom{padding:8px 14px 12px;border-top:1px solid var(--line);background:var(--panel);overflow:auto;max-height:45%}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{padding:2px 10px;text-align:right;border-bottom:1px solid var(--line)}
td:first-child,th:first-child{text-align:left}.good{color:var(--ok)}.bad{color:var(--bad)}
#status{color:var(--mute);font-size:12px;margin:8px 0}.err{color:var(--bad)}
.legend{display:flex;gap:14px;font-size:12px;color:var(--mute);margin-bottom:6px;flex-wrap:wrap;align-items:center}
.sw{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:4px}
button{background:var(--bg);color:var(--fg);border:1px solid var(--line);padding:5px 8px;border-radius:4px;cursor:pointer}button.on{border-color:var(--acc);color:var(--acc)}
#warn div{padding:5px 8px;margin:4px 0;border-left:3px solid var(--warn);background:#2a2618;font-size:13px}
#warn div.critical{border-color:var(--bad);background:#2d1b19}#warn div.sugg{border-color:#4aa3df;background:#17242e}
@media(max-width:820px){body{flex-direction:column;height:auto}#side{width:auto;min-width:0;border-right:0}#main{min-height:100vh}#bottom{max-height:none}}
#feas{font-weight:600}pre{font-size:11px;white-space:pre-wrap;background:var(--bg);padding:8px;border-radius:4px;max-height:360px;overflow:auto}
</style></head><body>
<div id="side">
 <h2>Mapa</h2>
 <select id="bg"><option value="relief">Relieve</option><option value="crism" selected>Relieve + mineralogía CRISM</option><option value="slope">Pendiente</option><option value="shadow">Sombras a la hora de salida</option></select>
 <h2>Origen y destino <span class="val">(clic en el mapa)</span></h2>
 <div class="row"><select id="origin"></select><select id="destination"></select></div>
 <div class="row" style="margin-top:6px"><button id="setA" class="on">Clic = A</button><button id="setB">Clic = B</button></div>
 <h2>Parámetros del LLM</h2>
 <label><input type="checkbox" id="human"> human (tripulación a bordo)</label>
 <label><input type="checkbox" id="power"> power (ahorrar energía)</label>
 <label><input type="checkbox" id="return_to_origin"> return_to_origin (ida y vuelta)</label>
 <div class="row"><div>safety<select id="safety"></select></div>
  <div>route_preference<select id="route_preference"><option value="">null</option><option>shortest</option><option>fastest</option></select></div></div>
 <h2>science_targets</h2><div id="targets"></div>
 <div style="margin-top:6px">science_detour<select id="science_detour"><option>low</option><option selected>medium</option><option>high</option></select></div>
 <h2>Estado del sistema (no lo pone el LLM)</h2>
 <label>Hora de salida (LTST) <span class="val" id="hourv"></span></label><input type="range" id="start_hour" min="5" max="18" step="0.25" value="9">
 <label>Batería <span class="val" id="battv"></span></label><input type="range" id="battery_kwh" min="0" max="40" step="0.5" value="30">
 <div id="status"></div>
</div>
<div id="main">
 <div id="mapwrap"><canvas id="cv"></canvas></div>
 <div id="bottom">
  <div class="legend"><span id="feas"></span><span><i class="sw" style="border-top:3px dashed #fff;height:0"></i>A* clásico</span>
   <span><i class="sw" style="background:#ff8a3d"></i>ruta con contexto</span><span style="color:#b266ff">● parada científica</span>
   <span style="color:#ffd84a">■ parada de carga</span><span id="sunv" class="val"></span><button id="jsonBtn" style="margin-left:auto">Ver JSON</button></div>
  <div id="warn"></div><div id="tbl"></div><pre id="json" hidden></pre>
 </div>
</div>
<script>
const $=id=>document.getElementById(id);let M,img=new Image(),res=null,click='origin',timer=null,pend=0;
const ROWS=[["distance_km","Distancia (km)",2],["time_h","Tiempo de conducción (h)",2],["drive_kwh","Energía de tracción (kWh)",2],["energy_kwh","Energía total (kWh)",1],
["ascent_m","Subida acumulada (m)",0],["max_pitch_deg","Pendiente máx. (°)",1],["max_cross_deg","Pendiente lateral máx. (°)",1],
["rough_km","Tramo rugoso (km)",2],["soft_km","Suelo blando (km)",2],["dunes_km","Dunas (km)",2],["unknown_km","Sin dato térmico (km)",2],
["shadow_km","En sombra del terreno (km)",2],["night_km","De noche (km)",2]];
async function init(){M=await (await fetch('/meta')).json();
 for(const id of ['origin','destination'])$(id).innerHTML=Object.keys(M.places).map(n=>`<option>${n}</option>`).join('');
 $('origin').value='crater_floor_south';$('destination').value='delta_top';
 $('safety').innerHTML=M.safety.map(s=>`<option ${s=='normal'?'selected':''}>${s}</option>`).join('');
 $('targets').innerHTML=M.targets.map(t=>`<div class="tgt"><input type="checkbox" data-t="${t}"><span>${t}</span><input type="range" min="0.1" max="1" step="0.1" value="1" data-p="${t}"></div>`).join('');
 const cv=$('cv');cv.width=M.width;cv.height=M.height;setBg();
 document.querySelectorAll('#side input,#side select').forEach(e=>e.addEventListener('input',()=>{labels();if(e.id=='bg'||(e.id=='start_hour'&&$('bg').value=='shadow'))setBg();if(e.id!='bg')schedule()}));
 $('setA').onclick=()=>{click='origin';$('setA').className='on';$('setB').className=''};
 $('setB').onclick=()=>{click='destination';$('setB').className='on';$('setA').className=''};
 $('jsonBtn').onclick=()=>{$('json').hidden=!$('json').hidden;$('jsonBtn').textContent=$('json').hidden?'Ver JSON':'Ocultar JSON'};
 cv.addEventListener('click',e=>{const r=cv.getBoundingClientRect(),c=(e.clientX-r.left)*M.width/r.width,rr=(e.clientY-r.top)*M.height/r.height;
  const k=3396190*Math.PI/180,lon=(M.left+(c+.5)*M.res)/k,lat=(M.top-(rr+.5)*M.res)/k,v=lon.toFixed(5)+','+lat.toFixed(5);
  const o=document.createElement('option');o.value=v;o.textContent=(click=='origin'?'A ':'B ')+v;$(click).appendChild(o);$(click).value=v;schedule()});
 labels();schedule()}
function setBg(){img=new Image();img.onload=draw;const v=$('bg').value;img.src='/bg/'+v+'.png'+(v=='shadow'?'?h='+$('start_hour').value:'')}
function hhmm(h){return String(Math.floor(h)).padStart(2,'0')+':'+String(Math.round(h%1*60)).padStart(2,'0')}
function labels(){$('hourv').textContent=hhmm(+$('start_hour').value);$('battv').textContent=$('battery_kwh').value+' / 40 kWh'}
function payload(){const t=[...document.querySelectorAll('[data-t]')].filter(e=>e.checked).map(e=>({target:e.dataset.t,priority:+document.querySelector(`[data-p="${e.dataset.t}"]`).value}));
 return {mission:{origin:$('origin').value,destination:$('destination').value,human:$('human').checked,power:$('power').checked,
  return_to_origin:$('return_to_origin').checked,safety:$('safety').value,route_preference:$('route_preference').value||null,
  science_targets:t,science_detour:$('science_detour').value},
  system:{start_hour:+$('start_hour').value,battery_kwh:+$('battery_kwh').value,battery_capacity_kwh:40}}}
function schedule(){clearTimeout(timer);timer=setTimeout(run,150)}
async function run(){const my=++pend;$('status').textContent='calculando…';$('status').className='';
 const r=await fetch('/plan',{method:'POST',body:JSON.stringify(payload())});const d=await r.json();if(my!=pend)return;
 if(d.error){$('status').textContent=d.error;$('status').className='err';return}
 res=d;draw();panel();$('status').textContent=`ok · ${d.seconds.toFixed(1)} s`}
function line(path,col,w,dash){const x=$('cv').getContext('2d');x.beginPath();path.forEach(([c,r],i)=>i?x.lineTo(c+.5,r+.5):x.moveTo(c+.5,r+.5));
 x.strokeStyle=col;x.lineWidth=w;x.setLineDash(dash);x.stroke();x.setLineDash([])}
function mark(c,r,fill,rad,txt,sq){const x=$('cv').getContext('2d');x.beginPath();sq?x.rect(c-rad,r-rad,2*rad,2*rad):x.arc(c+.5,r+.5,rad,0,7);
 x.fillStyle=fill;x.fill();x.strokeStyle='#000';x.lineWidth=3;x.stroke();
 if(txt){x.font='bold 44px sans-serif';x.lineWidth=6;x.strokeText(txt,c+22,r-14);x.fillStyle='#fff';x.fillText(txt,c+22,r-14)}}
function draw(){const cv=$('cv'),x=cv.getContext('2d');if(!M)return;x.clearRect(0,0,cv.width,cv.height);x.drawImage(img,0,0,cv.width,cv.height);if(!res)return;
 const D=res.draw;if(D.classic.length)line(D.classic,'#ffffff',5,[16,12]);
 if(D.route.length){line(D.route,'#000',12,[]);line(D.route,'#ff8a3d',7,[])}
 D.pois.forEach(p=>mark(p.c,p.r,'#b266ff',13));if(D.charge)mark(D.charge.c,D.charge.r,'#ffd84a',15,'',true);
 const p=D.route.length?D.route:D.classic;if(p.length){mark(...p[0],'#fff',16,'A');mark(...p[p.length-1],'#fff',16,'B')}}
function panel(){const R=res.report;$('json').textContent=JSON.stringify(R,null,1);
 $('sunv').textContent=R.sun?`☀ ${R.sun.sunrise}–${R.sun.sunset} (${R.sun.source})`:'';
 $('feas').innerHTML=R.feasible?'<span class="good">✔ viable</span>':'<span class="bad">✖ no viable</span>';
 $('warn').innerHTML=(R.warnings||[]).map(w=>`<div class="${w.severity}">${w.code}: ${w.message}</div>`).join('')+
  (R.suggestions||[]).map(s=>`<div class="sugg">${s.code}: ${s.energy_kwh} kWh, batería al llegar ${s.battery_end_kwh} kWh${s.fits_reserve?'':' (no basta)'}</div>`).join('');
 if(!R.route){$('tbl').innerHTML='';return}const a=R.classic_astar,b=R.route,C=R.comparison;
 let h='<table><tr><th></th><th>A* clásico</th><th>con contexto</th><th>Δ</th></tr>';
 for(const [k,l,dg] of ROWS){if(!(k in b))continue;const x=a[k],y=b[k],d=x?(y-x)/x*100:0,cls=Math.abs(d)<1?'':(d<0?'good':'bad');
  h+=`<tr><td>${l}</td><td>${x.toFixed(dg)}</td><td>${y.toFixed(dg)}</td><td class="${cls}">${x?(d>0?'+':'')+d.toFixed(0)+' %':'–'}</td></tr>`}
 for(const k of Object.keys(b).filter(k=>k.startsWith('on_')))h+=`<tr><td>Sobre ${k.slice(3,-3)} (km)</td><td></td><td>${b[k].toFixed(2)}</td><td></td></tr>`;
 h+=`<tr><td>Paradas científicas</td><td></td><td>${b.science_stops.length}</td><td></td></tr>`;
 h+=`<tr><td>Salida → llegada (límite ${b.daylight_limit})</td><td></td><td>${b.departure} → ${b.arrival}</td><td class="${b.daylight_margin_h<0?'bad':'good'}">${b.daylight_margin_h>=0?'+':''}${b.daylight_margin_h.toFixed(1)} h</td></tr>`;
 h+=`<tr><td>Batería al llegar</td><td></td><td>${b.battery_end_kwh.toFixed(1)} kWh (${b.battery_end_pct.toFixed(0)} %)</td><td></td></tr>`;
 h+=`<tr><td>Por qué (coste evitado)</td><td colspan="3">${R.why.map(w=>w.factor+' '+w.share_pct+' %').join(' · ')||'–'}</td></tr>`;
 $('tbl').innerHTML=h+'</table>'}
init();
</script></body></html>
"""

if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
