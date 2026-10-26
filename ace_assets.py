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
  .track-map.leaflet-container { background:#1b1b1d; } /* OpenFreeMap dark water, so no flash before the basemap loads */
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
  .spaghetti-legend .legend-dot, .legend-dot.legend-line { width:14px; height:3px; border-radius:2px; }
  .nhc-legend { margin-top:8px; }
  .nhc-legend .legend-dot { box-shadow:0 0 0 1px var(--muted); }
  .nhc-legend:empty { display:none; }
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
// Distances follow the wind unit's system: miles with kt or mph (US visitors,
// whatever the site's knots default), km with km/h.
var DIST_UNIT_KM={kt:1.609344,mph:1.609344,kmh:1};
var DIST_UNIT_LABELS={kt:'mi',mph:'mi',kmh:'km'};
function _fmtDist(km) {
  var unit=_windUnit();
  return Math.round(km/DIST_UNIT_KM[unit]).toLocaleString('en-US')+' '+DIST_UNIT_LABELS[unit];
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
  document.querySelectorAll('.dist-val').forEach(function(el){
    el.textContent=_fmtDist(parseFloat(el.getAttribute('data-km')));
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
// MapLibre is ~1 MB, so it loads on first map open, from the same vendor dir as Leaflet.
var _mlglWaiting=null;
function _loadMaplibre(cb){
  if(window.maplibregl&&L.maplibreGL){cb(true);return;}
  if(_mlglWaiting){_mlglWaiting.push(cb);return;}
  _mlglWaiting=[cb];
  var ls=document.querySelector('script[src*="leaflet-1.9.4/leaflet.js"]');
  var base=ls?ls.src.slice(0,ls.src.indexOf('leaflet-1.9.4/')):'vendor/';
  function done(ok){var w=_mlglWaiting;_mlglWaiting=ok?null:[];w.forEach(function(f){f(ok);});}
  function add(tag,attrs,onload){
    var e=document.createElement(tag);
    Object.keys(attrs).forEach(function(k){e.setAttribute(k,attrs[k]);});
    e.crossOrigin='anonymous';
    if(onload){e.onload=onload;e.onerror=function(){done(false);};}
    document.head.appendChild(e);
  }
  add('link',{rel:'stylesheet',href:base+'%(css)s',integrity:'%(css_sri)s'});
  add('script',{src:base+'%(js)s',integrity:'%(js_sri)s'},function(){
    add('script',{src:base+'%(plugin)s',integrity:'%(plugin_sri)s'},function(){done(true);});
  });
}
function _addBasemap(map,slug){
  _loadMaplibre(function(ok){
    if(!ok){_hideTrackSkeleton(slug);return;}
    // Once MapLibre is cached this runs synchronously, before _buildMap has set
    // the view; Leaflet defers onAdd until then, so the GL map wouldn't exist yet.
    map.whenReady(function(){
      var gl=L.maplibreGL({style:'%(style)s',
        attribution:'<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> &copy; <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'
      }).addTo(map);
      var glMap=gl.getMaplibreMap();
      if(!glMap){_hideTrackSkeleton(slug);return;}
      // The OpenFreeMap style names a few POI icons its sprite lacks; a blank stands in.
      glMap.on('styleimagemissing',function(e){
        if(!glMap.hasImage(e.id))glMap.addImage(e.id,{width:1,height:1,data:new Uint8Array(4)});
      });
      glMap.once('load',function(){_hideTrackSkeleton(slug);});
    });
  });
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
// NHC advisory layers (#169), drawn under the best track. Each layer is its own
// request; one that fails, times out or comes back empty is just left off.
var _NHC_WW={HWR:['#ff1744','Hurricane Warning'],HWA:['#ff80ab','Hurricane Watch'],TWR:['#2979ff','Tropical Storm Warning'],TWA:['#ffeb3b','Tropical Storm Watch']};
var _NHC_RADII={34:'#ffeb3b',50:'#ff9800',64:'#f44336'};
// Bottom to top. Only the fields we style by, at ~100 m precision, and only the
// current wind radii (tau 0): the full forecast set is ~10x the bytes.
var _NHC_LAYERS=[
  {key:'swath',z:360,fields:'radii'},
  {key:'cone',z:370,fields:'objectid'},
  {key:'radii',z:380,fields:'radii',where:'tau=0'},
  {key:'warnings',z:390,fields:'tcww'},
  {key:'track',z:395,fields:'objectid'},
  // Not drawn: their times give the proximity readout's closest approach (#180).
  {key:'points',fields:'tau,validtime,fldatelbl',dataOnly:true}
];
function _nhcStyle(key,p){
  if(key==='cone')return{color:'#ffffff',weight:1,opacity:0.7,fillColor:'#ffffff',fillOpacity:0.15};
  if(key==='track')return{color:'#ffffff',weight:2,opacity:0.9,dashArray:'6,4'};
  if(key==='warnings'){var w=_NHC_WW[p.tcww];return{color:w?w[0]:'#ffffff',weight:5,opacity:1};}
  var c=_NHC_RADII[p.radii]||_NHC_RADII[34];
  if(key==='swath')return{stroke:false,fillColor:c,fillOpacity:0.12};
  return{color:c,weight:1,opacity:0.9,fillColor:c,fillOpacity:0.2};
}
// cb(geojson) with at least one feature, or cb(null) on any failure or empty layer.
function _nhcFetch(url,cb){
  if(!window.fetch){cb(null);return;}
  var ctl=window.AbortController?new AbortController():null;
  var timer=ctl?setTimeout(function(){ctl.abort();},10000):null;
  fetch(url,ctl?{signal:ctl.signal}:{}).then(function(r){return r.ok?r.json():null;}).then(function(j){
    clearTimeout(timer);
    // ArcGIS reports query errors as a 200 with {error:...} and no features.
    cb(j&&j.features&&j.features.length?j:null);
  }).catch(function(){clearTimeout(timer);cb(null);});
}
function _nhcLegend(legendId,drawn){
  var el=document.getElementById(legendId);
  if(!el)return;
  var items=[];
  function add(color,label,line){items.push('<div class="legend-item"><div class="legend-dot'+(line?' legend-line':'')+'" style="background:'+color+'"></div>'+label+'</div>');}
  if(drawn.cone)add('#ffffff','Forecast cone');
  if(drawn.track)add('#ffffff','NHC forecast track',true);
  if(drawn.radii)[34,50,64].forEach(function(r){if(drawn.radii[r])add(_NHC_RADII[r],r+' kt winds');});
  if(drawn.warnings)['HWR','HWA','TWR','TWA'].forEach(function(k){if(drawn.warnings[k])add(_NHC_WW[k][0],_NHC_WW[k][1],true);});
  if(drawn.swath)add('rgba(255,235,59,0.45)','Past wind swath');
  el.innerHTML=items.join('');
}
// `opts.legend` is the legend element's id and `opts.drawn` what's on it so far,
// shared when several storms draw on one map. `opts.skipTrack` when the map
// already shows the OFCL model track, which is this same forecast.
// `opts.onData(key, geojson|null)`, if given, hears every layer's outcome and
// also gets the data-only layers.
function _addNhcLayers(map,d,refLon,opts){
  var ids=d.nhc_layers,drawn=opts.drawn;
  _NHC_LAYERS.forEach(function(spec){
    if(spec.key==='track'&&opts.skipTrack)return;
    if(spec.dataOnly&&!opts.onData)return;
    var url='%(nhc_service)s/'+ids[spec.key]+'/query?where='+encodeURIComponent(spec.where||'1=1')
      +'&outFields='+spec.fields+'&geometryPrecision=3&f=geojson';
    _nhcFetch(url,function(gj){
      if(opts.onData)opts.onData(spec.key,gj);
      if(!gj||spec.dataOnly)return;
      var pane='nhc-'+spec.key;
      if(!map.getPane(pane))map.createPane(pane).style.zIndex=spec.z;
      L.geoJSON(gj,{pane:pane,interactive:spec.key==='warnings',
        // NHC sends -180..180; shift into the track's unwrapped frame near the antimeridian.
        coordsToLatLng:function(c){return L.latLng(c[1],_unwrapLon(refLon,c[0]));},
        style:function(f){return _nhcStyle(spec.key,f.properties||{});},
        onEachFeature:function(f,layer){
          var p=f.properties||{};
          if(spec.key==='radii'||spec.key==='warnings'){
            var k=spec.key==='radii'?p.radii:p.tcww;
            drawn[spec.key]=drawn[spec.key]||{};drawn[spec.key][k]=true;
          }else drawn[spec.key]=true;
          if(spec.key==='warnings'&&_NHC_WW[p.tcww])layer.bindTooltip(_NHC_WW[p.tcww][1],{sticky:true});
        }}).addTo(map);
      if(!map._nhcCredited){
        map._nhcCredited=true;
        map.attributionControl.addAttribution('Advisory layers: <a href="https://www.nhc.noaa.gov/gis/" target="_blank" rel="noopener">NHC</a>');
      }
      _nhcLegend(opts.legend,drawn);
    });
  });
}
function _buildMap(slug){
  var d=ACE_TRACKS[slug];
  var el=document.getElementById('trmap-'+slug);
  if(!d||!d.points||!d.points.length||!el||el._leaflet_id){_hideTrackSkeleton(slug);return;}
  if(typeof L==='undefined'){_hideTrackSkeleton(slug);_libMissing(el,'Map unavailable right now. Storm details are shown above.');return;}
  var map=L.map(el,{zoomControl:true,attributionControl:true,maxZoom:10});
  _addBasemap(map,slug);
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
  if(d.active&&d.nhc_layers)_addNhcLayers(map,d,lls[lls.length-1][1],
    {legend:'nhclegend-'+slug,drawn:{},skipTrack:!!(d.spaghetti&&d.spaghetti.OFCL)});
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

NOMINATIM_SEARCH = 'https://nominatim.openstreetmap.org/search'

# Dashboard-only: one map of every active storm in both basins (#178). Builds
# after the page has loaded, so MapLibre never competes with the first paint.
ACTIVE_MAP_CSS = """  .active-map { background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; }
  .active-map .track-map { height:clamp(300px,55vh,480px); }
  .active-map .nhc-legend { margin-top:0; }
  .active-map-storms { display:flex; flex-wrap:wrap; gap:8px; margin-top:4px; }
  .active-map-storm { color:var(--accent); text-decoration:none; border:1px solid var(--border); border-radius:16px; padding:4px 12px; font-size:0.85em; }
  .active-map-storm:hover, .active-map-storm:focus-visible { border-color:var(--accent); }
  .active-map-basin { color:var(--muted); font-size:0.85em; }
  .loc-form { margin-bottom:12px; }
  .loc-label { display:block; font-size:0.9em; color:var(--text); margin-bottom:6px; }
  .loc-row { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
  .loc-row input[type=search] { flex:1 1 180px; min-width:0; font:inherit; font-size:16px; color:var(--text); background:var(--box); border:1px solid var(--border); border-radius:8px; padding:9px 12px; }
  .loc-btn { font:inherit; font-size:0.9em; min-height:40px; cursor:pointer; border-radius:8px; padding:8px 14px; border:1px solid var(--border); background:var(--box); color:var(--text); }
  .loc-btn.loc-primary { background:var(--accent); border-color:var(--accent); color:var(--bg); font-weight:bold; }
  .loc-btn:focus-visible, .loc-row input:focus-visible, .loc-pick:focus-visible, .loc-link:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  .loc-msg { min-height:1.2em; margin:6px 0 0; font-size:0.85em; color:var(--text); }
  .loc-msg:empty { display:none; }
  .loc-picks { display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }
  .loc-pick { font:inherit; font-size:0.85em; cursor:pointer; border-radius:16px; padding:6px 12px; border:1px solid var(--accent); background:transparent; color:var(--accent); text-align:left; }
  .loc-meta { margin-top:8px; font-size:0.82em; color:var(--muted); justify-content:space-between; }
  .loc-remember { display:flex; align-items:center; gap:6px; cursor:pointer; }
  .loc-link { font:inherit; background:none; border:none; padding:4px 0; color:var(--accent); cursor:pointer; text-decoration:underline; }
  .loc-note { margin:6px 0 0; font-size:0.75em; color:var(--muted); }
  .loc-note a { color:var(--accent); }
  .loc-readout { margin:4px 0 12px; }
  .prox-title { margin:8px 0; }
  .prox-list { list-style:none; display:grid; gap:8px; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }
  .prox-item { background:var(--box); border:1px solid var(--border); border-radius:8px; padding:10px 12px; }
  .prox-top { display:flex; justify-content:space-between; align-items:baseline; gap:8px; }
  .prox-name { color:var(--accent); font-weight:bold; text-decoration:none; }
  .prox-cat { font-size:0.75em; color:var(--muted); border:1px solid; border-radius:10px; padding:1px 8px; white-space:nowrap; }
  .prox-dist { font-size:1.3em; font-weight:bold; color:var(--text-strong); margin:4px 0; font-variant-numeric:tabular-nums; }
  .prox-facts { list-style:none; font-size:0.85em; color:var(--text); display:grid; gap:3px; }
  .prox-note { color:var(--muted); }
  .prox-asof { font-size:0.72em; color:var(--muted); margin-top:6px; }
  .prox-disclaimer { font-size:0.8em; color:var(--muted); border-left:3px solid var(--accent); padding:4px 10px; margin-top:10px; }
  .prox-disclaimer a { color:var(--accent); }
  .leaflet-tooltip.dist-tip { background:var(--card); color:var(--text-strong); border:1px solid var(--border); font-weight:bold; font-size:12px; box-shadow:none; padding:1px 6px; }
  .leaflet-tooltip.dist-tip::before { display:none; }
  .loc-pin span { display:block; width:18px; height:18px; border-radius:50% 50% 50% 0; background:#00e676; border:2px solid #fff; transform:rotate(-45deg); box-shadow:0 2px 6px rgba(0,0,0,0.5); }"""

ACTIVE_MAP_JS = """function _buildActiveMap(){
  var el=document.getElementById('trmap-active');
  if(!el||el._leaflet_id||!ACE_ACTIVE.length)return;
  if(typeof L==='undefined'){_hideTrackSkeleton('active');_libMissing(el,'Map unavailable right now. Active storms are listed below.');return;}
  var map=L.map(el,{zoomControl:true,attributionControl:true,maxZoom:10});
  _addBasemap(map,'active');
  setTimeout(function(){_hideTrackSkeleton('active');},4000);
  _trMapObjs.active=map;
  var drawn={},boundsPts=[];
  _proxStorms=[];
  ACE_ACTIVE.forEach(function(s){
    var d=ACE_TRACKS[s.slug];
    if(!d||!d.points||!d.points.length)return;
    var p=d.points[d.points.length-1];
    // One frame for both basins: a Central Pacific storm past 180 deg stays west of Hawaii.
    var ll=[p.lat,p.lon>90?p.lon-360:p.lon];
    _proxStorms.push({slug:s.slug,name:d.name,lat:ll[0],lon:ll[1],status:p.status,wind:p.wind,time:p.time,nhc:!!d.nhc_layers});
    var c=_tc(p.status,p.wind);
    L.circleMarker(ll,{radius:8,fillColor:c,color:'#fff',weight:2,fillOpacity:1,opacity:1}).addTo(map)
      .bindTooltip('<b>'+d.name+'</b><br>'+p.status+' \xb7 '+_fmtWind(p.wind),{direction:'top',offset:[0,-8]})
      .on('click',function(e){L.DomEvent.stopPropagation(e);_openStormRow('storm-row-'+s.slug);});  // not a pin drop
    boundsPts.push(ll);
    var ofcl=d.spaghetti&&d.spaghetti.OFCL;
    if(ofcl&&ofcl.length)boundsPts=boundsPts.concat(_unwrapSeries([ll].concat(ofcl.map(function(q){return[q.lat,q.lon];}))).slice(1));
    if(d.nhc_layers){
      var data=_nhcData[s.slug]={pending:_NHC_LAYERS.length};
      _addNhcLayers(map,d,ll[1],{legend:'nhclegend-active',drawn:drawn,skipTrack:false,
        onData:function(key,gj){data[key]=gj;data.pending--;_locRender();}});
    }
  });
  map._stormBounds=boundsPts;
  map.on('click',function(e){
    var lat=e.latlng.lat,lon=((e.latlng.lng+540)%360)-180;
    _locSet({lat:lat,lon:lon,label:'Dropped pin ('+Math.abs(lat).toFixed(2)+(lat<0?'S':'N')+', '+Math.abs(lon).toFixed(2)+(lon<0?'W':'E')+')'});
  });
  var start=_aceLoc||_locLoad();
  if(start)_locSet(start);
  else _locFit();
}
window.addEventListener('load',_buildActiveMap);

// Location input (#179). The place a visitor gives stays in this page (and in
// localStorage only if they ask); searches go from the browser to Nominatim.
var _aceLoc=null,_locPin=null,_locLast=-1e9,_locBusy=false;
var _LOC_KEY='ace-location';
function _el(id){return document.getElementById(id);}
function _locMsg(t){var e=_el('loc-msg');if(e)e.textContent=t||'';}
function _kmBetween(lat1,lon1,lat2,lon2){
  var r=Math.PI/180,a=Math.sin((lat2-lat1)*r/2),b=Math.sin((lon2-lon1)*r/2);
  return 12742*Math.asin(Math.sqrt(a*a+Math.cos(lat1*r)*Math.cos(lat2*r)*b*b));
}
function _locLabel(r){
  var a=r.address||{},parts=[];
  var street=[a.house_number,a.road].filter(Boolean).join(' ');
  if(street)parts.push(street);
  else if(r.addresstype==='postcode'&&a.postcode)parts.push(a.postcode);
  var place=a.city||a.town||a.village||a.hamlet||a.suburb||a.county;
  if(place)parts.push(place);
  if(a.state)parts.push(a.state);
  if(a.country&&a.country_code!=='us')parts.push(a.country);
  return parts.length?parts.join(', '):(r.display_name||'Selected place');
}
// Nominatim also returns the county or state a city sits in, and repeats of one
// address; a pick list of those would be noise.
function _locDistinct(results){
  var places=results.filter(function(r){return['county','state','country','region'].indexOf(r.addresstype)<0;});
  if(!places.length)places=results;
  var out=[];
  places.forEach(function(r){
    var lat=+r.lat,lon=+r.lon;
    if(!isFinite(lat)||!isFinite(lon))return;
    if(!out.some(function(o){return _kmBetween(o.lat,o.lon,lat,lon)<25;}))out.push({lat:lat,lon:lon,label:_locLabel(r)});
  });
  return out;
}
function _locPicks(places){
  var box=_el('loc-picks');
  if(!box)return;
  box.innerHTML='';
  box.hidden=!places.length;
  places.forEach(function(p){
    var b=document.createElement('button');
    b.type='button';b.className='loc-pick';b.textContent=p.label;
    b.onclick=function(){_locSet(p);_el('loc-q').focus();};
    box.appendChild(b);
  });
  if(places.length)box.firstChild.focus();
}
function _locSubmit(ev){
  if(ev)ev.preventDefault();
  var q=_el('loc-q').value.trim();
  if(!q){_locMsg('Enter a city, ZIP code or address.');return false;}
  if(_locBusy||!window.fetch)return false;
  _locBusy=true;_locPicks([]);_locMsg('Searching...');
  // Nominatim's usage policy allows one request a second.
  var wait=Math.max(0,1000-(performance.now()-_locLast));
  setTimeout(function(){
    _locLast=performance.now();
    var url='%(nominatim)s?format=jsonv2&addressdetails=1&limit=5&q='+encodeURIComponent(q)
      +(/^[0-9]{5}(-[0-9]{4})?$/.test(q)?'&countrycodes=us':'');
    var ctl=window.AbortController?new AbortController():null;
    var timer=ctl?setTimeout(function(){ctl.abort();},10000):null;
    fetch(url,ctl?{signal:ctl.signal}:{}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json();}).then(function(rs){
      clearTimeout(timer);_locBusy=false;
      var places=_locDistinct(Array.isArray(rs)?rs:[]);
      if(!places.length)_locMsg('No place found for "'+q+'". Try a city and state, or a ZIP code.');
      else if(places.length===1)_locSet(places[0]);
      else{_locMsg('Several places match "'+q+'". Pick one:');_locPicks(places);}
    }).catch(function(){
      clearTimeout(timer);_locBusy=false;
      _locMsg('Place search is not responding right now. Try again, use your location, or tap the map.');
    });
  },wait);
  return false;
}
function _locUseMine(){
  if(!navigator.geolocation)return;
  _locMsg('Finding your location...');
  navigator.geolocation.getCurrentPosition(function(pos){
    _locSet({lat:pos.coords.latitude,lon:pos.coords.longitude,label:'your current location'});
  },function(err){
    _locMsg(err&&err.code===1
      ?'Location access is off for this site. Search for a place or tap the map instead.'
      :'Could not get your location. Search for a place or tap the map instead.');
  },{timeout:10000,maximumAge:600000});
}
function _locFit(){
  var map=_trMapObjs.active;
  if(!map)return;
  var pts=(map._stormBounds||[]).slice();
  if(_locPin)pts.push(_locPin.getLatLng());
  if(pts.length)map.fitBounds(L.latLngBounds(pts),{padding:[40,40],maxZoom:6});
}
function _locSet(p){
  _aceLoc=p;
  _locPicks([]);
  _locMsg('Showing '+p.label+'.');
  _el('loc-clear').hidden=false;
  if(_el('loc-remember').checked)_locSave();
  var map=_trMapObjs.active;
  if(!map)return;  // drawn when the map builds
  var ll=[p.lat,p.lon>90?p.lon-360:p.lon];  // the storms' frame
  if(!_locPin)_locPin=L.marker(ll,{icon:L.divIcon({className:'loc-pin',html:'<span></span>',iconSize:[22,22],iconAnchor:[11,24]}),keyboard:false,title:'Your location'}).addTo(map);
  else _locPin.setLatLng(ll);
  _locPin.unbindTooltip().bindTooltip(document.createTextNode(p.label),{direction:'top',offset:[0,-22]});
  _locFit();
  _locRender();
}
function _locClear(){
  _aceLoc=null;
  if(_locPin){_locPin.remove();_locPin=null;}
  _locMsg('');_locPicks([]);
  _el('loc-clear').hidden=true;
  try{localStorage.removeItem(_LOC_KEY);}catch(e){}
  _locFit();
  _locRender();
}
function _locSave(){try{localStorage.setItem(_LOC_KEY,JSON.stringify(_aceLoc));}catch(e){}}
function _locRemember(){
  if(_el('loc-remember').checked){if(_aceLoc)_locSave();}
  else{try{localStorage.removeItem(_LOC_KEY);}catch(e){}}
}
function _locLoad(){
  try{
    var v=JSON.parse(localStorage.getItem(_LOC_KEY)||'null');
    if(v&&isFinite(v.lat)&&isFinite(v.lon)){
      _el('loc-remember').checked=true;
      return{lat:+v.lat,lon:+v.lon,label:String(v.label||'Saved location')};
    }
  }catch(e){}
  return null;
}
// Proximity readout (#180): how far each active storm is from the pin, and,
// from NHC's layers when they loaded, the cone, closest approach and wind field.
var _proxStorms=[],_nhcData={},_locLines=null;
function _esc(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function _bearing(lat1,lon1,lat2,lon2){
  var r=Math.PI/180,dl=(lon2-lon1)*r;
  var y=Math.sin(dl)*Math.cos(lat2*r),x=Math.cos(lat1*r)*Math.sin(lat2*r)-Math.sin(lat1*r)*Math.cos(lat2*r)*Math.cos(dl);
  return(Math.atan2(y,x)/r+360)%360;
}
var _COMPASS=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
function _compass(deg){return _COMPASS[Math.round(deg/22.5)%16];}
// Flat km grid centered on (lat0,lon0): close enough at storm-to-coast distances.
function _proj(lat0,lon0,lat,lon){return[(_unwrapLon(lon0,lon)-lon0)*111.32*Math.cos(lat0*Math.PI/180),(lat-lat0)*110.57];}
// Nearest point to p on segment a-b, all [x,y]: returns [fraction along a-b, distance].
function _segNearest(p,a,b){
  var dx=b[0]-a[0],dy=b[1]-a[1],l=dx*dx+dy*dy;
  var t=l?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l)):0;
  var x=a[0]+t*dx-p[0],y=a[1]+t*dy-p[1];
  return[t,Math.sqrt(x*x+y*y)];
}
// Outer rings ([lon,lat] lists) of a feature's Polygon or MultiPolygon.
function _rings(f){
  var g=f.geometry||{};
  if(g.type==='Polygon')return[g.coordinates[0]];
  if(g.type==='MultiPolygon')return g.coordinates.map(function(p){return p[0];});
  return[];
}
function _inRing(lat,lon,ring){
  var inside=false;
  for(var i=0,j=ring.length-1;i<ring.length;j=i++){
    var xi=_unwrapLon(lon,ring[i][0]),yi=ring[i][1],xj=_unwrapLon(lon,ring[j][0]),yj=ring[j][1];
    if((yi>lat)!==(yj>lat)&&lon<(xj-xi)*(lat-yi)/(yj-yi)+xi)inside=!inside;
  }
  return inside;
}
function _kmToRing(lat,lon,ring){
  var best=Infinity,p=[0,0];
  for(var i=1;i<ring.length;i++){
    var d=_segNearest(p,_proj(lat,lon,ring[i-1][1],ring[i-1][0]),_proj(lat,lon,ring[i][1],ring[i][0]))[1];
    if(d<best)best=d;
  }
  return best;
}
// A forecast point's time in ms: validtime is 'DD/HHMM' UTC, and fldatelbl
// ('2026-10-25 12:00 PM Sun CST') supplies the year and month.
function _nhcTime(props){
  var m=/^([0-9]+)-([0-9]+)-([0-9]+)/.exec(props.fldatelbl||''),v=/^([0-9]+)[/]([0-9]{2})([0-9]{2})$/.exec(props.validtime||'');
  if(!m||!v)return null;
  var month=+m[2]-1,day=+v[1];
  if(day-+m[3]>15)month--;else if(+m[3]-day>15)month++;
  return Date.UTC(+m[1],month,day,+v[2],+v[3]);
}
function _catName(status,wind){
  if(status==='HU'){
    var c=wind>=137?5:wind>=113?4:wind>=96?3:wind>=83?2:1;
    return'Category '+c+' hurricane';
  }
  return{TS:'Tropical storm',SS:'Subtropical storm',TD:'Tropical depression',SD:'Subtropical depression'}[status]||status;
}
function _distHtml(km){return'<span class="dist-val" data-km="'+km.toFixed(1)+'">'+_fmtDist(km)+'</span>';}
// Beyond this the flat-grid distances drift and the detail isn't useful.
var _PROX_DETAIL_KM=1500;
// Facts from NHC's layers for one storm, as sentences; [] when there are none.
function _proxFacts(st,lat,lon){
  var data=_nhcData[st.slug],facts=[];
  if(!data)return facts;
  var cone=data.cone&&data.cone.features.some(function(f){return _rings(f).some(function(r){return _inRing(lat,lon,r);});});
  if(cone)facts.push('You are inside the forecast cone.');
  var pts=data.points&&data.points.features.filter(function(f){return f.geometry&&f.geometry.type==='Point';})
    .sort(function(a,b){return a.properties.tau-b.properties.tau;});
  if(pts&&pts.length>1){
    var xy=pts.map(function(f){return _proj(lat,lon,f.geometry.coordinates[1],f.geometry.coordinates[0]);});
    var best={d:Infinity};
    for(var i=1;i<xy.length;i++){
      var n=_segNearest([0,0],xy[i-1],xy[i]);
      if(n[1]<best.d)best={d:n[1],i:i,t:n[0]};
    }
    var a=pts[best.i-1].properties,b=pts[best.i].properties;
    var tau=a.tau+best.t*(b.tau-a.tau),t0=_nhcTime(pts[0].properties);
    if(best.d>_PROX_DETAIL_KM)facts.push('Not forecast to come within ~'+_distHtml(_PROX_DETAIL_KM)+'.');
    else if(tau<1)facts.push('Not forecast to come any closer than it is now.');
    else{
      var x=xy[best.i-1][0]+best.t*(xy[best.i][0]-xy[best.i-1][0]),y=xy[best.i-1][1]+best.t*(xy[best.i][1]-xy[best.i-1][1]);
      var hour=3600000,when=t0===null?'':' around '+new Date(Math.round((t0+tau*hour)/hour)*hour).toLocaleString('en-US',{weekday:'short',hour:'numeric'});
      facts.push(best.d<10?'Forecast to pass over or near you'+when+'.'
        :'Forecast to pass ~'+_distHtml(best.d)+' '+_compass((Math.atan2(x,y)*180/Math.PI+360)%360)+' of you'+when+'.');
    }
  }
  if(data.radii){
    var byKt={};
    data.radii.features.forEach(function(f){var k=f.properties.radii;(byKt[k]=byKt[k]||[]).push(f);});
    function inside(k){return(byKt[k]||[]).some(function(f){return _rings(f).some(function(r){return _inRing(lat,lon,r);});});}
    if(inside(64))facts.push('Inside the hurricane-force (64 kt) wind field.');
    else if(inside(50))facts.push('Inside the 50 kt wind field.');
    else if(inside(34))facts.push('Inside the tropical-storm-force wind field.');
    else if(byKt[34]){
      var edge=Math.min.apply(null,byKt[34].map(function(f){return Math.min.apply(null,_rings(f).map(function(r){return _kmToRing(lat,lon,r);}));}));
      if(edge<=_PROX_DETAIL_KM)facts.push('Tropical-storm-force winds are ~'+_distHtml(edge)+' away.');
    }
  }
  return facts;
}
function _locRender(){
  var box=_el('loc-readout'),map=_trMapObjs.active;
  if(!box)return;
  if(_locLines){_locLines.remove();_locLines=null;}
  if(!_aceLoc||!_proxStorms.length){box.hidden=true;box.innerHTML='';return;}
  var lat=_aceLoc.lat,lon=_aceLoc.lon;
  var rows=_proxStorms.map(function(st){return{st:st,km:_kmBetween(lat,lon,st.lat,st.lon)};})
    .sort(function(a,b){return a.km-b.km;});
  if(map)_locLines=L.layerGroup().addTo(map);
  var items=rows.map(function(row){
    var st=row.st,c=_tc(st.status,st.wind),data=_nhcData[st.slug];
    if(_locLines){
      var pin=[lat,_unwrapLon(st.lon,lon)];
      L.polyline([pin,[st.lat,st.lon]],{color:c,weight:2,opacity:0.9,dashArray:'5,5',interactive:false})
        .bindTooltip(_distHtml(row.km),{permanent:true,direction:'center',className:'dist-tip',interactive:false})
        .addTo(_locLines);
    }
    var facts=_proxFacts(st,lat,lon);
    var note=facts.length?'':!st.nhc||(data&&!data.pending)
      ?'<li class="prox-note">Distance to the center only: NHC forecast layers aren&#8217;t available for this storm right now.</li>'
      :'<li class="prox-note">Loading NHC forecast&#8230;</li>';
    return'<li class="prox-item" data-slug="'+st.slug+'">'
      +'<div class="prox-top"><a class="prox-name" href="#storm-row-'+st.slug+'" onclick="return !_openStormRow(this.hash.slice(1))">'+_esc(st.name)+'</a>'
      +'<span class="prox-cat" style="border-color:'+c+'">'+_catName(st.status,st.wind)+'</span></div>'
      +'<div class="prox-dist">'+_distHtml(row.km)+' '+_compass(_bearing(lat,lon,st.lat,st.lon))+'</div>'
      +'<ul class="prox-facts">'+facts.map(function(f){return'<li>'+f+'</li>';}).join('')+note+'</ul>'
      +'<div class="prox-asof">Center as of '+_esc(st.time||'')+'</div></li>';
  });
  box.innerHTML='<h3 class="prox-title">Distance from '+_esc(_aceLoc.label)+'</h3>'
    +'<ol class="prox-list">'+items.join('')+'</ol>'
    +'<p class="prox-disclaimer">Not for safety decisions. Follow the <a href="https://www.nhc.noaa.gov/" target="_blank" rel="noopener">National Hurricane Center</a> and your local officials.</p>';
  box.hidden=false;
}
document.addEventListener('DOMContentLoaded',function(){
  var geo=_el('loc-geo');
  if(geo&&navigator.geolocation&&window.isSecureContext)geo.hidden=false;
});
"""
ACTIVE_MAP_JS = ACTIVE_MAP_JS.replace('%(nominatim)s', NOMINATIM_SEARCH)

THEME_INIT_JS = """(function(){try{var t=localStorage.getItem('ace-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light');else if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches)document.documentElement.setAttribute('data-theme','light');}catch(e){}})();"""

# Subresource-integrity hashes for the vendored Leaflet files. The dashboard
# template carries the same values inline; a test keeps both in step.
LEAFLET_CSS_SRI = 'sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H'
LEAFLET_JS_SRI = 'sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH'

# Track-map basemap: OpenFreeMap vector tiles (free, no key) drawn through
# MapLibre inside Leaflet. 5.x because 6.x ships only as an ES module, which
# the Leaflet plugin can't use. TRACK_MAP_JS loads these lazily.
BASEMAP = {
    'style': 'https://tiles.openfreemap.org/styles/dark',
    'js': 'maplibre-gl-5.24.0/maplibre-gl.js',
    'js_sri': 'sha384-5+cfbwT0iiub6VsQAdn6yz16nr6sDiQoHx6tm4O8OVYXHYOxcffFmCJBL0dgdvGp',
    'css': 'maplibre-gl-5.24.0/maplibre-gl.css',
    'css_sri': 'sha384-uTttxo/aOKbdE5RlD/SPzSDoDmNvGlUYPjONi2MN/b7c9HPSvW07OIuyP7uL6jxK',
    'plugin': 'maplibre-gl-leaflet-0.1.4/leaflet-maplibre-gl.js',
    'plugin_sri': 'sha384-tXYNKOHx4T02jMP7YYCtBxPIv1B5gaA5mcVPBzqMp6d7VzWzxJgI2aWF/nJLrQdS',
}
for _key, _value in BASEMAP.items():
    TRACK_MAP_JS = TRACK_MAP_JS.replace(f'%({_key})s', _value)

# NHC's live advisory layers (#169). Layer ids per storm come from
# ace_data.nhc_gis_layer_ids(); the service sends CORS headers for any origin.
NHC_GIS_SERVICE = ('https://mapservices.weather.noaa.gov/tropical/rest/services/'
                   'tropical/NHC_tropical_weather/MapServer')
TRACK_MAP_JS = TRACK_MAP_JS.replace('%(nhc_service)s', NHC_GIS_SERVICE)

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
