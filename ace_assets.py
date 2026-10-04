"""CSS and JS shared by the dashboard and the storm pages.

Plain strings (not f-strings), so braces are single here. Each is inserted into
a page template at the spot it was extracted from, so pages keep their original
cascade/script order.
"""

BASE_CSS = """  :root {
    --bg:#0a1628; --card:#132238; --box:#1a2d4a; --accent:#4fc3f7; --accent2:#29b6f6;
    --accent-h3:#81d4fa; --text:#e0e6ed; --text-strong:#ffffff; --muted:#8aa0ab;
    --muted-dark:#78909c; --border:#1e3a5f; --danger:#ef5350; --danger-bg:#2a1a1a;
    --danger-text:#ef8a80; --total-row:#1a2d4a; --sources-bg:#0d1b2a; --gauge-bg:#1e3a5f;
    --pace-last:#ffb74d;
  }
  [data-theme="light"] {
    --bg:#f0f4f8; --card:#ffffff; --box:#e8f0fe; --accent:#0277bd; --accent2:#0288d1;
    --accent-h3:#01579b; --text:#1a2d4a; --text-strong:#0a1628; --muted:#4f6773;
    --muted-dark:#455a64; --border:#b0bec5; --danger:#d32f2f; --danger-bg:#ffeaea;
    --danger-text:#c62828; --total-row:#e8f0fe; --sources-bg:#e2ecf7; --gauge-bg:#c9daf8;
    --pace-last:#e65100;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  :focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); padding:12px; transition:background 0.2s,color 0.2s; }
  .header { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; margin:8px 0; padding:0 4px; }
  h1 { grid-column:2; color:var(--accent); font-size:1.4em; text-align:center; display:flex; align-items:center; justify-content:center; gap:8px; }
  .logo { height:1.5em; width:auto; vertical-align:middle; }
  .header-actions { grid-column:3; justify-self:end; display:flex; gap:6px; align-items:center; }
  .theme-btn, .unit-btn { background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:4px 10px; cursor:pointer; font-size:0.9em; }"""

NAV_CSS = """  .nav-link { text-align:center; margin-bottom:12px; display:flex; justify-content:center; gap:8px; flex-wrap:wrap; }
  .nav-link a { color:var(--accent); text-decoration:none; font-size:0.85em; border:1px solid var(--accent); border-radius:20px; padding:4px 14px; }
  .nav-link a:hover { background:var(--accent); color:var(--bg); }"""

HEADINGS_CSS = """  h2 { color:var(--accent); font-size:1.2em; margin-bottom:12px; border-bottom:1px solid var(--border); padding-bottom:8px; }
  h3 { color:var(--accent-h3); font-size:1em; margin:16px 0 8px; }"""

STORM_PANEL_CSS = """  .track-row td { padding:0; border-bottom:2px solid var(--border); }
  .track-panel { overflow:hidden; max-height:0; visibility:hidden; transition:max-height 0.35s ease, visibility 0s linear 0.35s; background:var(--card); }
  .track-panel.open { max-height:1500px; visibility:visible; transition:max-height 0.35s ease, visibility 0s; }
  .track-inner { padding:12px 14px 14px; }
  .track-map { height:320px; border-radius:8px; border:1px solid var(--border); margin-bottom:10px; }
  .track-map-wrap { position:relative; margin-bottom:10px; }
  .track-map-wrap .track-map { margin-bottom:0; }
  .track-map-skeleton { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:var(--box); border-radius:8px; border:1px solid var(--border); }
  .skeleton-spinner { width:28px; height:28px; border-radius:50%; border:3px solid var(--border); border-top-color:var(--accent); animation:skeleton-spin 0.8s linear infinite; }
  @keyframes skeleton-spin { to { transform:rotate(360deg); } }
  .storm-meta { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:10px; }
  .meta-box { background:var(--box); border-radius:6px; padding:8px 10px; }
  .meta-label { color:var(--muted); font-size:0.72em; text-transform:uppercase; }
  .meta-value { color:var(--text-strong); font-size:0.95em; font-weight:bold; }
  .meta-sub { color:var(--muted); font-size:0.72em; }
  .active-badge { display:inline-flex; align-items:center; gap:5px; background:#0d2a14; border:1px solid #4caf50; border-radius:12px; padding:3px 8px; font-size:0.75em; color:#4caf50; margin-bottom:8px; }
  .intensity-bar { display:flex; height:8px; border-radius:4px; overflow:hidden; margin-bottom:10px; }
  .intensity-seg { flex-shrink:0; }
  .track-legend { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
  .legend-item { display:flex; align-items:center; gap:4px; font-size:0.72em; color:var(--muted); }
  .legend-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
  .spaghetti-toggle { display:flex; align-items:center; gap:6px; font-size:0.78em; color:var(--muted); margin-top:8px; cursor:pointer; }
  .spaghetti-legend { margin-top:6px; }
  .lib-missing { color:var(--muted); font-size:0.85em; text-align:center; padding:24px 8px; }
  .sp-cycle { color:var(--muted); font-size:0.9em; }
  .sp-note { font-size:0.72em; color:var(--muted); margin-top:4px; }
  .spaghetti-legend .legend-dot { width:14px; height:3px; border-radius:2px; }
  .nhc-link { font-size:0.78em; color:var(--muted); text-align:right; margin-top:6px; }
  .nhc-link a { color:var(--accent); text-decoration:none; }
  .nhc-link a:hover { text-decoration:underline; }"""

CONE_CSS = """  .cone-graphic { margin-bottom:10px; }
  .cone-graphic img { display:block; width:100%; height:auto; border-radius:8px; border:1px solid var(--border); }
  .cone-credit { font-size:0.72em; color:var(--muted); text-align:center; margin-top:4px; }
  .cone-credit a { color:var(--accent); text-decoration:none; }
  .cone-credit a:hover { text-decoration:underline; }"""

WIND_JS = """var WIND_UNITS=['kt','mph','kmh'];
var WIND_UNIT_LABELS={kt:'kt',mph:'mph',kmh:'km/h'};
function _windUnit() {
  try{var u=localStorage.getItem('ace-wind-unit');if(WIND_UNITS.indexOf(u)>=0)return u;}catch(e){}
  return 'kt';
}
function _convertWind(kt) {
  var unit=_windUnit();
  if(unit==='mph')return Math.round(kt*1.15078);
  if(unit==='kmh')return Math.round(kt*1.852);
  return kt;
}
function _fmtWind(kt) {
  return _convertWind(kt)+' '+WIND_UNIT_LABELS[_windUnit()];
}
function applyWindUnit() {
  var unit=_windUnit();
  var btn=document.getElementById('unitBtn');
  if(btn){btn.textContent=WIND_UNIT_LABELS[unit];btn.setAttribute('aria-label','Wind speed unit: '+WIND_UNIT_LABELS[unit]);}
  document.querySelectorAll('.wind-val').forEach(function(el){
    el.textContent=String(_convertWind(parseFloat(el.getAttribute('data-kt'))));
  });
  document.querySelectorAll('.wind-val-unit').forEach(function(el){
    el.textContent=_fmtWind(parseFloat(el.getAttribute('data-kt')));
  });
  document.querySelectorAll('.wind-th-label').forEach(function(el){
    el.textContent=el.getAttribute('data-'+unit+'-label')||el.textContent;
  });
  document.querySelectorAll('.intensity-seg').forEach(function(el){
    var kt=parseFloat(el.getAttribute('data-wind-kt'));
    if(isNaN(kt))return;
    el.title=el.getAttribute('data-status')+' '+_fmtWind(kt)+' '+el.getAttribute('data-time');
  });
}
function toggleWindUnit() {
  var next=WIND_UNITS[(WIND_UNITS.indexOf(_windUnit())+1)%WIND_UNITS.length];
  try{localStorage.setItem('ace-wind-unit',next);}catch(e){}
  applyWindUnit();
}"""

LIB_MISSING_JS = """function _libMissing(box,msg){
  if(!box||box.querySelector('.lib-missing'))return;
  var p=document.createElement('p');p.className='lib-missing';p.textContent=msg;box.appendChild(p);
}"""

TRACK_MAP_JS = """var _trMaps={};
var _trSpagLayers={};
var _trMapObjs={};
var _SC={TD:'#9e9e9e',TS:'#81d4fa',SS:'#81d4fa'};
var _SPAG_COLORS={AVNO:'#29b6f6',EMX:'#ab47bc',UKX:'#66bb6a',CMC:'#8d6e63',HWRF:'#ec407a',HMON:'#7e57c2',NVGM:'#26c6da',OFCL:'#ffffff'};
var _SPAG_LABELS={AVNO:'GFS',EMX:'ECMWF',UKX:'UKMET',CMC:'CMC',HWRF:'HWRF',HMON:'HMON',NVGM:'Navy',OFCL:'NHC Official'};
function _tc(st,w){
  if(st==='HU'){if(w>=137)return'#b71c1c';if(w>=113)return'#ef5350';if(w>=96)return'#ff8a65';if(w>=83)return'#ffb74d';return'#ffe082';}
  return _SC[st]||'#9e9e9e';
}
function toggleTrack(slug){
  var panel=document.getElementById('trpanel-'+slug);
  var btn=document.getElementById('trbtn-'+slug);
  if(!panel)return;
  var open=panel.classList.contains('open');
  if(open){panel.classList.remove('open');if(btn){btn.classList.remove('open');btn.setAttribute('aria-expanded','false');}return;}
  panel.classList.add('open');
  if(btn){btn.classList.add('open');btn.setAttribute('aria-expanded','true');}
  if(!_trMaps[slug]){_trMaps[slug]=true;setTimeout(function(){_buildMap(slug);},25);}
}
function _hideTrackSkeleton(slug){
  var sk=document.getElementById('trskel-'+slug);
  if(sk)sk.style.display='none';
}
function _unwrapLon(prevLon,lon){
  while(lon-prevLon>180)lon-=360;
  while(lon-prevLon<-180)lon+=360;
  return lon;
}
function _unwrapSeries(lls){
  var out=[lls[0].slice()];
  for(var i=1;i<lls.length;i++){
    out.push([lls[i][0],_unwrapLon(out[i-1][1],lls[i][1])]);
  }
  return out;
}
function _buildMap(slug){
  var d=ACE_TRACKS[slug];
  var el=document.getElementById('trmap-'+slug);
  if(!d||!d.points||!d.points.length||!el||el._leaflet_id){_hideTrackSkeleton(slug);return;}
  if(typeof L==='undefined'){_hideTrackSkeleton(slug);_libMissing(el,'Map unavailable right now. Storm details are shown above.');return;}
  var map=L.map(el,{zoomControl:true,attributionControl:true});
  var tiles=L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=cb1_2ju7_1_dab4d1e9c4e0819a594bda11',{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains:'abcd',maxZoom:10
  }).addTo(map);
  tiles.on('load',function(){_hideTrackSkeleton(slug);});
  setTimeout(function(){_hideTrackSkeleton(slug);},4000);
  var pts=d.points,lls=_unwrapSeries(pts.map(function(p){return[p.lat,p.lon];}));
  for(var i=0;i<pts.length-1;i++){
    L.polyline([lls[i],lls[i+1]],{color:_tc(pts[i].status,pts[i].wind),weight:5,opacity:1}).addTo(map);
  }
  pts.forEach(function(p,i){
    var c=_tc(p.status,p.wind),last=(i===pts.length-1);
    var mk=L.circleMarker([p.lat,p.lon],{radius:last?7:4,fillColor:c,color:last?'#fff':c,weight:last?2:1,fillOpacity:1,opacity:1}).addTo(map);
    mk.bindTooltip('<b>'+d.name+'</b><br>'+p.time+'<br>'+p.status+' \xb7 '+_fmtWind(p.wind),{direction:'top',offset:[0,-6]});
    if(last&&d.active)mk.bindPopup('<b>Current Position</b><br>'+p.time+'<br>'+p.status+' \xb7 '+_fmtWind(p.wind),{maxWidth:160}).openPopup();
  });
  var boundsPts=lls.slice();
  var spagGroup=L.layerGroup();
  var legendHtml='';
  if(d.spaghetti){
    Object.keys(d.spaghetti).forEach(function(model){
      var mpts=d.spaghetti[model];
      if(!mpts||!mpts.length)return;
      // Anchor to the storm's last known position so this model's series
      // unwraps in the same longitude frame as the BTK track and any other
      // model — otherwise each series could independently drift to opposite
      // sides of the antimeridian and the combined bounds would be wrong.
      var mlls=_unwrapSeries([lls[lls.length-1]].concat(mpts.map(function(p){return[p.lat,p.lon];}))).slice(1);
      var color=_SPAG_COLORS[model]||'#ffffff',label=_SPAG_LABELS[model]||model;
      var cyc=(d.spaghetti_cycles||{})[model];
      L.polyline(mlls,{color:color,weight:model==='OFCL'?3:2,opacity:0.85,dashArray:model==='OFCL'?null:'4,4'})
        .bindTooltip(label+(cyc?' \xb7 '+cyc:''),{sticky:true}).addTo(spagGroup);
      L.circleMarker(mlls[mlls.length-1],{radius:3,color:color,fillColor:color,fillOpacity:1,weight:1}).addTo(spagGroup);
      boundsPts=boundsPts.concat(mlls);
      legendHtml+='<div class="legend-item"><div class="legend-dot" style="background:'+color+'"></div>'+label+(cyc?' <span class="sp-cycle">'+cyc+'</span>':'')+'</div>';
    });
  }
  spagGroup.addTo(map);
  _trSpagLayers[slug]=spagGroup;
  _trMapObjs[slug]=map;
  var legendEl=document.getElementById('splegend-'+slug);
  if(legendEl)legendEl.innerHTML=legendHtml;
  if(boundsPts.length)map.fitBounds(L.latLngBounds(boundsPts),{padding:[50,50],maxZoom:6});
}
function _toggleSpaghetti(slug){
  var cb=document.getElementById('sptoggle-'+slug);
  var group=_trSpagLayers[slug],map=_trMapObjs[slug];
  if(!cb||!group||!map)return;
  if(cb.checked)group.addTo(map);else map.removeLayer(group);
}"""

THEME_INIT_JS = """(function(){try{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');else if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.setAttribute('data-theme','light');}catch(e){}})();"""

# Subresource-integrity hashes for the vendored Leaflet files. The dashboard
# template carries the same values inline; a test keeps both in step.
LEAFLET_CSS_SRI = 'sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H'
LEAFLET_JS_SRI = 'sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH'

STORM_PAGE_CSS = """
  .container { max-width:900px; margin:0 auto; }
  .storm-card { background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; }
  .storm-sub { color:var(--muted); font-size:0.9em; margin:-4px 0 12px; }
  .storm-actions { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 0; }
  .storm-actions button { background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:20px; padding:6px 14px; cursor:pointer; font-size:0.85em; }
  .lf-list { list-style:none; }
  .lf-list li { padding:6px 0; border-bottom:1px solid var(--border); font-size:0.92em; }
  .lf-list li:last-child { border-bottom:none; }
  .sibling-list { list-style:none; display:flex; flex-wrap:wrap; gap:8px; }
  .sibling-list a { display:inline-block; color:var(--accent); text-decoration:none; border:1px solid var(--border); border-radius:16px; padding:4px 12px; font-size:0.85em; }
  .sibling-list a[aria-current="page"] { background:var(--accent); color:var(--bg); border-color:var(--accent); font-weight:bold; }
  .sources { background:var(--sources-bg); border-radius:8px; padding:12px 14px; font-size:0.78em; color:var(--muted); margin-top:16px; }
  .sources a { color:var(--accent); }
  .page-note { color:var(--muted); font-size:0.78em; margin:10px 2px 0; }
"""
