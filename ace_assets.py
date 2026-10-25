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
  {key:'track',z:395,fields:'objectid'}
];
function _nhcStyle(key,p){
  if(key==='cone')return{color:'#ffffff',weight:1,opacity:0.7,fillColor:'#ffffff',fillOpacity:0.15};
  if(key==='track')return{color:'#ffffff',weight:2,opacity:0.9,dashArray:'6,4'};
  if(key==='warnings'){var w=_NHC_WW[p.tcww];return{color:w?w[0]:'#ffffff',weight:5,opacity:1};}
  var c=_NHC_RADII[p.radii]||_NHC_RADII[34];
  if(key==='swath')return{stroke:false,fillColor:c,fillOpacity:0.12};
  return{color:c,weight:1,opacity:0.9,fillColor:c,fillOpacity:0.2};
}
function _nhcFetch(url,cb){
  if(!window.fetch)return;
  var ctl=window.AbortController?new AbortController():null;
  var timer=ctl?setTimeout(function(){ctl.abort();},10000):null;
  fetch(url,ctl?{signal:ctl.signal}:{}).then(function(r){return r.ok?r.json():null;}).then(function(j){
    clearTimeout(timer);
    // ArcGIS reports query errors as a 200 with {error:...} and no features.
    if(j&&j.features&&j.features.length)cb(j);
  }).catch(function(){clearTimeout(timer);});
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
function _addNhcLayers(map,d,refLon,opts){
  var ids=d.nhc_layers,drawn=opts.drawn;
  _NHC_LAYERS.forEach(function(spec){
    if(spec.key==='track'&&opts.skipTrack)return;
    var url='%(nhc_service)s/'+ids[spec.key]+'/query?where='+encodeURIComponent(spec.where||'1=1')
      +'&outFields='+spec.fields+'&geometryPrecision=3&f=geojson';
    _nhcFetch(url,function(gj){
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

# Dashboard-only: one map of every active storm in both basins (#178). Builds
# after the page has loaded, so MapLibre never competes with the first paint.
ACTIVE_MAP_CSS = """  .active-map { background:var(--card); border-radius:12px; padding:16px; margin-bottom:16px; }
  .active-map .track-map { height:clamp(300px,55vh,480px); }
  .active-map .nhc-legend { margin-top:0; }
  .active-map-storms { display:flex; flex-wrap:wrap; gap:8px; margin-top:4px; }
  .active-map-storm { color:var(--accent); text-decoration:none; border:1px solid var(--border); border-radius:16px; padding:4px 12px; font-size:0.85em; }
  .active-map-storm:hover, .active-map-storm:focus-visible { border-color:var(--accent); }
  .active-map-basin { color:var(--muted); font-size:0.85em; }"""

ACTIVE_MAP_JS = """function _buildActiveMap(){
  var el=document.getElementById('trmap-active');
  if(!el||el._leaflet_id||!ACE_ACTIVE.length)return;
  if(typeof L==='undefined'){_hideTrackSkeleton('active');_libMissing(el,'Map unavailable right now. Active storms are listed below.');return;}
  var map=L.map(el,{zoomControl:true,attributionControl:true,maxZoom:10});
  _addBasemap(map,'active');
  setTimeout(function(){_hideTrackSkeleton('active');},4000);
  _trMapObjs.active=map;
  var drawn={},boundsPts=[];
  ACE_ACTIVE.forEach(function(s){
    var d=ACE_TRACKS[s.slug];
    if(!d||!d.points||!d.points.length)return;
    var p=d.points[d.points.length-1];
    // One frame for both basins: a Central Pacific storm past 180 deg stays west of Hawaii.
    var ll=[p.lat,p.lon>90?p.lon-360:p.lon];
    var c=_tc(p.status,p.wind);
    L.circleMarker(ll,{radius:8,fillColor:c,color:'#fff',weight:2,fillOpacity:1,opacity:1}).addTo(map)
      .bindTooltip('<b>'+d.name+'</b><br>'+p.status+' \xb7 '+_fmtWind(p.wind),{direction:'top',offset:[0,-8]})
      .on('click',function(){_openStormRow('storm-row-'+s.slug);});
    boundsPts.push(ll);
    var ofcl=d.spaghetti&&d.spaghetti.OFCL;
    if(ofcl&&ofcl.length)boundsPts=boundsPts.concat(_unwrapSeries([ll].concat(ofcl.map(function(q){return[q.lat,q.lon];}))).slice(1));
    if(d.nhc_layers)_addNhcLayers(map,d,ll[1],{legend:'nhclegend-active',drawn:drawn,skipTrack:false});
  });
  if(boundsPts.length)map.fitBounds(L.latLngBounds(boundsPts),{padding:[40,40],maxZoom:6});
}
window.addEventListener('load',_buildActiveMap);"""

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
