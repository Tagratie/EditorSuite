
// ── TOOL DEFINITIONS ─────────────────────────────────────────────────────────
const T={
  scraper:{cat:"scrapers",cl:"SCRAPERS",name:"Trending Audio Scraper",sub:"Find top sounds from any TikTok hashtag",
    f:[{id:"hashtag",l:"HASHTAG",p:"edit"},{id:"limit",l:"TARGET VIDEOS",s:["300","500","200","100"]}]},
  crosshash:{cat:"scrapers",cl:"SCRAPERS",name:"Cross-Hashtag Sounds",sub:"Sounds trending across multiple niches",
    f:[{id:"hashtags",l:"HASHTAGS (comma-separated)",p:"edit"}]},
  sp_exp:{cat:"scrapers",cl:"SCRAPERS",name:"Export to Spotify",sub:"Push trending TikTok sounds to a Spotify playlist",
    f:[{id:"hashtag",l:"HASHTAG TO SCRAPE",p:"edit"}]},
  hanalyze:{cat:"analytics",cl:"ANALYTICS",name:"Hashtag Analyzer",sub:"Analyse any TikTok hashtag — avg views, top videos from the last 7 days, trending sounds (UGC filtered), and related tags",
    _isHanalyze:true, f:[{id:"hashtags",l:"HASHTAGS",p:"edit"}]},
  competitor:{cat:"analytics",cl:"ANALYTICS",name:"Competitor Tracker",sub:"Side-by-side analysis of two accounts",
    f:[{id:"user1",l:"ACCOUNT 1",p:"@username"},{id:"user2",l:"ACCOUNT 2",p:"@username"}]},
  dl_vid:{cat:"downloaders",cl:"DOWNLOADERS",name:"Video Downloader",sub:"Single video or full profile — TikTok & YouTube",
    _isDlCentered:true,
    f:[{id:"url",l:"URL",p:""},{id:"quality",l:"QUALITY",s:["1080","720","480","best"]},{id:"limit",l:"LIMIT",s:["20","50","100","all"]}]},
  dl_prof:{cat:"downloaders",cl:"DOWNLOADERS",name:"Profile & Playlist DL",sub:"Full profiles, playlists & channels",
    f:[{id:"url",l:"URL OR @USERNAME",p:"@username or playlist URL"},{id:"limit",l:"MAX VIDEOS",s:["all","50","100","200"]}]},
  dl_spotify:{cat:"downloaders",cl:"DOWNLOADERS",name:"Spotify / SoundCloud DL",sub:"Track, album, or playlist as MP3",
    f:[{id:"url",l:"SPOTIFY OR SOUNDCLOUD URL",p:"https://open.spotify.com/track/..."},{id:"quality",l:"AUDIO QUALITY",s:["320","256","192","128"]}]},
  dl_audio:{cat:"downloaders",cl:"DOWNLOADERS",name:"Audio Extractor",sub:"MP3 from a local file or URL",
    f:[{id:"input",l:"FILE PATH OR URL",p:"C:\\video.mp4 or https://...",browse:"file",
        browseFilters:[{name:"Video / Audio",exts:"*.mp4;*.mkv;*.mov;*.avi;*.mp3;*.wav;*.flac"},{name:"All Files",exts:"*.*"}]},
       {id:"bitrate",l:"BITRATE",s:["320","256","192","128"]}]},
  compress:{cat:"studio",cl:"STUDIO",name:"Video Compressor",sub:"Single video or batch-compress an entire folder with HandBrake presets",
    f:[
      {id:"input",l:"VIDEO FILE OR FOLDER",p:"C:\\Videos\\clip.mp4 or C:\\Videos\\",browse:"file_or_folder",
        browseFilters:[{name:"Video Files",exts:"*.mp4;*.mkv;*.mov;*.avi;*.wmv;*.m4v"},{name:"All Files",exts:"*.*"}]},
      {id:"output",l:"OUTPUT FOLDER",p:"C:\\Compressed\\",browse:"folder"},
      {id:"preset",l:"COMPRESSION PRESET",type:"preset-cards",cards:[
        {id:"tiktok",  icon:"📱",name:"TikTok",    desc:"720p · ≤ 30 MB · fast encode"},
        {id:"instagram",icon:"📸",name:"Instagram", desc:"1080p · balanced quality"},
        {id:"discord", icon:"💬",name:"Discord",   desc:"< 25 MB · 720p · web-optimised"},
        {id:"web",     icon:"🌐",name:"Web Fast",  desc:"720p · CRF 23 · small file"},
        {id:"hq",      icon:"🎬",name:"High Quality",desc:"1080p · CRF 18 · large file"},
        {id:"ultra",   icon:"🗜",name:"Ultra Small",desc:"480p · max compression"},
      ]}
    ]},
  bg_rem:{cat:"studio",cl:"STUDIO",name:"Background Remover",sub:"AI background removal — single image or batch folder",
    f:[{id:"input",l:"FILE OR FOLDER PATH",p:"C:\\image.png",browse:"file_or_folder",
        browseFilters:[{name:"Images",exts:"*.png;*.jpg;*.jpeg;*.webp;*.bmp"},{name:"All Files",exts:"*.*"}]}]},
  model3d:{cat:"search",cl:"SEARCH",name:"3D Model Finder",sub:"Live-search Sketchfab for 3D models, characters, props, environments and more",
    _isLive:true,
    f:[{id:"query",l:"SEARCH MODELS",p:"low poly car, character sword, tree, building..."}]},

  footage:{cat:"search",cl:"SEARCH",name:"Stock Footage",sub:"Search free HD stock footage and cinematic car clips — instant download via yt-dlp",
    _isFootage:true, f:[{id:"query",l:"SEARCH",p:"ocean waves, forest drone, city night timelapse..."}]},
  scene_pack:{cat:"search",cl:"SEARCH",name:"Scene Pack Finder",sub:"Browse free scene packs by category",_isScenePack:true,f:[{id:"query",l:"SEARCH",p:"anime, dark, horror, aesthetic..."}]},
};

const ICONS={scraper:"🎵",crosshash:"⟁",sp_exp:"💚",
  hanalyze:"📊",competitor:"⚔️",
  dl_vid:"⬇️",dl_prof:"👤",dl_spotify:"🎧",dl_audio:"🎙",
  compress:"📦",bg_rem:"✂️",model3d:"🧊",footage:"🎬",scene_pack:"🎬"};

let det=null,hrun=false,trun=false,dtimer=null,activeToolId=null,appBusy=false;
let _streamGen=0; // incremented on tool switch; streams check before writing
const _toolOutputCache={};
let _homeOutputCache="";
let _soundsCache=null;
let _soundsSortMode="count";
let _3dSearchTimer=null;
let _3dFreeOnly=false;
let _3dCategory="all";

function saveHomeOutput(){const hr=document.getElementById("hr");if(hr)_homeOutputCache=hr.innerHTML;setHomeClearVisible(!!_homeOutputCache)}
function restoreHomeOutput(){const hr=document.getElementById("hr");if(hr)hr.innerHTML=_homeOutputCache||"";setHomeClearVisible(!!_homeOutputCache)}
function saveToolOutput(id){if(!id)return;const tr=document.getElementById("tr");if(tr)_toolOutputCache[id]=tr.innerHTML;setToolClearVisible(!!_toolOutputCache[id])}
function restoreToolOutput(id){const tr=document.getElementById("tr");if(tr)tr.innerHTML=(id&&_toolOutputCache[id])?_toolOutputCache[id]:"";setToolClearVisible(!!(id&&_toolOutputCache[id]))}
function clearHomeOutput(){_homeOutputCache="";const hr=document.getElementById("hr");if(hr){hr.innerHTML="";const _hw=document.getElementById("hr-wrap");if(_hw)_hw.style.display="none";}setHomeClearVisible(false)}
function clearToolOutput(id){if(id)_toolOutputCache[id]="";const tr=document.getElementById("tr");if(tr)tr.innerHTML="";if(id==="scraper")_soundsCache=null;setToolClearVisible(false)}
function setHomeClearVisible(on){const btn=document.getElementById("hclear");if(btn)btn.style.display=on?"inline-flex":"none";const row=document.getElementById("hor");if(!row)return;const q=document.getElementById("oq"),aq=document.getElementById("oaq"),lm=document.getElementById("olim");const any=(q&&q.style.display!=="none")||(aq&&aq.style.display!=="none")||(lm&&lm.style.display!=="none");if(on||any)row.style.display="flex";else row.style.display="none"}
function setToolClearVisible(on){const btn=document.getElementById("tclear");if(btn)btn.style.display=on?"inline-flex":"none"}
function _setClearForRes(resEl,hasOutput){if(!resEl)return;if(resEl.id==="hr")setHomeClearVisible(hasOutput);if(resEl.id==="tr")setToolClearVisible(hasOutput)}
function setSoundsSort(mode){_soundsSortMode=(mode==="avg")?"avg":"count";if(_soundsCache){const tr=document.getElementById("tr");if(tr)tr.innerHTML=rSounds(_soundsCache,"");setToolClearVisible(true)}}

// ── PRESET CATEGORIES ────────────────────────────────────────────────────────
const PC={
  "📺 Shows":{label:"Shows",defaults:{scraper:{hashtag:"strangerthings"},crosshash:{hashtags:"strangerthings, breakingbad, peakyblinders, theboys"},hanalyze:{hashtags:"strangerthings, breakingbad, peakyblinders, squidgame"},competitor:{user1:"netflix",user2:"hbomax"}},
    chips:{scraper:[{l:"Stranger Things",v:{hashtag:"strangerthings"}},{l:"Breaking Bad",v:{hashtag:"breakingbad"}},{l:"Peaky Blinders",v:{hashtag:"peakyblinders"}},{l:"The Boys",v:{hashtag:"theboys"}},{l:"Squid Game",v:{hashtag:"squidgame"}}],
      crosshash:[{l:"Netflix Hits",v:{hashtags:"strangerthings, theboys, squidgame, wednesday"}},{l:"Crime Drama",v:{hashtags:"breakingbad, peakyblinders, ozark, narcos"}},{l:"Sci-Fi",v:{hashtags:"strangerthings, blackmirror, westworld"}}],
      hanalyze:[{l:"Netflix Lineup",v:{hashtags:"strangerthings, theboys, squidgame, wednesdayaddams"}},{l:"Crime Shows",v:{hashtags:"breakingbad, peakyblinders, ozark, narcos"}}],
      competitor:[{l:"Netflix vs HBO",v:{user1:"netflix",user2:"hbomax"}},{l:"Netflix vs Disney+",v:{user1:"netflix",user2:"disneyplus"}}]}},
  "🎬 Movies":{label:"Movies",defaults:{scraper:{hashtag:"harrypotter"},crosshash:{hashtags:"harrypotter, marvel, starwars, lordoftherings"},hanalyze:{hashtags:"harrypotter, marvel, starwars, lordoftherings"},competitor:{user1:"marvel",user2:"dccomics"}},
    chips:{scraper:[{l:"Harry Potter",v:{hashtag:"harrypotter"}},{l:"Marvel",v:{hashtag:"marvel"}},{l:"Star Wars",v:{hashtag:"starwars"}},{l:"LOTR",v:{hashtag:"lordoftherings"}},{l:"Dune",v:{hashtag:"dune"}}],
      crosshash:[{l:"Fantasy Epic",v:{hashtags:"harrypotter, lordoftherings, dune, narnia"}},{l:"Marvel vs DC",v:{hashtags:"marvel, dc, avengers, batman"}},{l:"Sci-Fi",v:{hashtags:"starwars, interstellar, dune, tenet"}}],
      hanalyze:[{l:"Fantasy Films",v:{hashtags:"harrypotter, lordoftherings, dune, narnia"}},{l:"Marvel Universe",v:{hashtags:"marvel, avengers, spiderman, ironman"}}],
      competitor:[{l:"Marvel vs DC",v:{user1:"marvel",user2:"dccomics"}},{l:"Disney vs Universal",v:{user1:"disney",user2:"universalpictures"}}]}},
  "🎭 Creator":{label:"Creator",defaults:{},chips:{scraper:[{l:"Edit",v:{hashtag:"edit"}},{l:"VideoEdit",v:{hashtag:"videoedit"}},{l:"CapCut",v:{hashtag:"capcutedit"}},{l:"Transitions",v:{hashtag:"transition"}},{l:"Trending",v:{hashtag:"trending"}}],crosshash:[{l:"Edit + CC + Trans",v:{hashtags:"edit, capcutedit, transition"}},{l:"Edit + Fyp + Trend",v:{hashtags:"videoedit, fyp, trending"}}],hanalyze:[{l:"Edit Tags",v:{hashtags:"edit, videoedit, capcutedit, transition, fyp"}},{l:"Creator Tags",v:{hashtags:"contentcreator, youtuber, tiktokgrowth, fyp"}}],competitor:[{l:"CapCut vs VN",v:{user1:"capcutapp",user2:"vnvideoeditor"}}]}},
  "🎌 Anime":{label:"Anime",defaults:{scraper:{hashtag:"animeedit"},crosshash:{hashtags:"anime, animeedit, animetiktok, naruto, onepiece"},hanalyze:{hashtags:"anime, animeedit, naruto, onepiece"},competitor:{user1:"crunchyroll",user2:"funimation"}},
    chips:{scraper:[{l:"Anime Edits",v:{hashtag:"animeedit"}},{l:"Naruto",v:{hashtag:"naruto"}},{l:"One Piece",v:{hashtag:"onepiece"}},{l:"Demon Slayer",v:{hashtag:"demonslayer"}},{l:"JJK",v:{hashtag:"jujutsukaisen"}}],
      crosshash:[{l:"Big 3",v:{hashtags:"naruto, onepiece, bleach, dragonball"}},{l:"New Gen",v:{hashtags:"demonslayer, jujutsukaisen, chainsawman, myheroacademia"}}],
      hanalyze:[{l:"Big 3",v:{hashtags:"naruto, onepiece, bleach, dragonball"}},{l:"New Gen",v:{hashtags:"demonslayer, jujutsukaisen, chainsawman"}}],
      competitor:[{l:"Crunchyroll vs Funimation",v:{user1:"crunchyroll",user2:"funimation"}}]}},
};

let activeCategory=null;
let _customCategories=[];

function initCategories(){
  const grid=document.getElementById("pcat-grid");if(!grid)return;
  const builtIn=Object.keys(PC).map(name=>`<button class="sb-pcat-btn" data-cat="${name}" onclick="setCategory('${name}')">${name}</button>`);
  const custom=_customCategories.map((cat,i)=>`<button class="sb-pcat-btn sb-pcat-btn-custom" data-cat="${x(cat.name)}" onclick="setCategory('${x(cat.name)}')">${x(cat.name)}<span class="sb-pcat-del" onclick="event.stopPropagation();removeCustomCategory(${i})">✕</span></button>`);
  grid.innerHTML=[...builtIn,...custom].join("");
}

function setCategory(name){
  if(activeCategory===name){clearCategory();return}
  const custCat=_customCategories.find(c=>c.name===name);
  if(custCat&&!PC[name])PC[name]=buildCustomCategoryPC(custCat);
  activeCategory=name;
  document.querySelectorAll(".sb-pcat-btn").forEach(b=>b.classList.toggle("active",b.dataset.cat===name));
  document.getElementById("pcat-clear").classList.add("show");
  showContextBadge(name);fillToolFields(name);
}
function clearCategory(){activeCategory=null;document.querySelectorAll(".sb-pcat-btn").forEach(b=>b.classList.remove("active"));document.getElementById("pcat-clear").classList.remove("show");hideContextBadge()}
function showContextBadge(name){const b=document.getElementById("ccb"),t=document.getElementById("ccb-text");if(!b||!t)return;t.textContent=name+" preset active — fields auto-filled";b.classList.add("show")}
function hideContextBadge(){const b=document.getElementById("ccb");if(b)b.classList.remove("show")}
function fillToolFields(catName){const on=document.querySelector(".sb-tool.on");if(!on)return;const id=(on.getAttribute("onclick")||"").replace(/goTool\(['"](.+?)['"]\)/,"$1");if(!id)return;goTool(id)}

document.addEventListener("DOMContentLoaded",()=>{initCategories();setCategory("📺 Shows")});

// ── NAVIGATION ───────────────────────────────────────────────────────────────
function _setTopbarActive(id){
  ["tb-home","tb-coll","tb-acct","tb-settings","tb-community"].forEach(b=>{
    const el=document.getElementById(b);
    if(el) el.classList.toggle("on",b===id);
  });
}

// ── CENTERED SEARCH HELPERS ──────────────────────────────────────────────────
// ── VIDEO DOWNLOADER CENTERED ─────────────────────────────────────────────────
function setDlMode(mode){
  window._dlMode=mode;
  document.querySelectorAll(".cs-mode-btn").forEach(b=>b.classList.remove("active"));
  const btn=document.getElementById("dlm-"+mode); if(btn)btn.classList.add("active");
  const inp=document.getElementById("tf_dl_url");
  const lw=document.getElementById("dl-limit-wrap");
  if(mode==="bulk"){
    if(inp)inp.placeholder="@username or playlist URL…";
    if(lw)lw.style.display="";
  }else{
    if(inp)inp.placeholder="Paste a TikTok or YouTube URL…";
    if(lw)lw.style.display="none";
  }
}
async function runDlCentered(){
  const inp=document.getElementById("tf_dl_url");
  const url=(inp?inp.value:"").trim(); if(!url) return;
  _csSetSearched(true);
  const res=document.getElementById("cs-results");
  if(res)res.innerHTML='<div class="search-dots-wrap"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';
  const quality=document.getElementById("tf_quality")?.value||"720";
  const limit=document.getElementById("tf_limit")?.value||"20";
  const isBulk=(window._dlMode==="bulk");
  const toolId=isBulk?"dl_prof":"dl_vid";
  const opts=isBulk?{url,limit}:{url,quality};
  const fakeBar={style:{}},fakeLbl={textContent:""},fakeSt={textContent:""};
  await new Promise(resolve=>{
    doStream("/api/tool",{tool_id:toolId,options:opts},{
      barEl:fakeBar,lblEl:fakeLbl,stEl:fakeSt,resEl:res,feedId:"",onDone:resolve
    });
  });
}

let _csSearched = false;

function _csSetSearched(v){
  _csSearched = v;
  const center = document.getElementById("cs-center");
  if(center) center.classList.toggle("cs-searched", v);
}

// ── HASHTAG ANALYZER CENTERED ────────────────────────────────────────────────
async function _csRunHanalyze(){
  const inp = document.getElementById("tf_hashtags");
  const raw = (inp ? inp.value : "").trim();
  if(!raw) return;
  _csSetSearched(true);
  const res = document.getElementById("cs-results");
  if(res) res.innerHTML = '<div class="search-dots-wrap"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';

  // Parse tags
  const tags = raw.replace(/#/g,"").split(/[,\s]+/).filter(Boolean).map(t=>t.toLowerCase());

  // Use the existing doStream machinery via /api/tool
  const opts = { hashtags: tags.join(", ") };
  try{
    await new Promise((resolve)=>{
      const fakeBar={style:{}}, fakeLbl={textContent:""}, fakeSt={textContent:""};
      const fakeRes = { id:"_fake_res", innerHTML:"" };
      Object.defineProperty(fakeRes,"innerHTML",{
        set(v){
          if(res) res.innerHTML = v;
        },
        get(){ return res ? res.innerHTML : ""; }
      });
      doStream("/api/tool",{tool_id:"hanalyze",options:opts},{
        barEl:fakeBar, lblEl:fakeLbl, stEl:fakeSt, resEl:res,
        feedId:"",
        onDone:resolve
      });
    });
  }catch(e){
    if(res) res.innerHTML = '<div style="padding:40px;text-align:center;font-family:var(--fm);font-size:.8rem;color:#555">Analysis failed: '+x(e.message)+'</div>';
  }
}


async function _csRun(mode){
  _csSetSearched(true);
  const res = document.getElementById("cs-results");
  if(res) res.innerHTML = '<div class="search-dots-wrap"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';
  const tr = document.getElementById("tr");
  if(mode === "3d"){
    await run3DSearch();
    if(res && tr){ res.innerHTML = tr.innerHTML; tr.innerHTML = ""; }
  } else {
    await runFootageSearch();
    if(res && tr){ res.innerHTML = tr.innerHTML; tr.innerHTML = ""; }
  }
}


function goHome(){
  _setTopbarActive("tb-home");
  const _rstTpl=document.querySelector(".tpi-left"); if(_rstTpl) _rstTpl.style.display="";
  const _rstPt=document.getElementById("pt2"); if(_rstPt) _rstPt.style.flexDirection="";
  const _rstTr=document.getElementById("tr"); if(_rstTr){ _rstTr.style.overflow=""; _rstTr.style.padding=""; _rstTr.style.display=""; _rstTr.style.flexDirection=""; }
  // Restore tpi-left if hidden by centered search
  const _tl=document.querySelector(".tpi-left"); if(_tl) _tl.style.display="";
  const _pt2d=document.getElementById("pt2"); if(_pt2d) _pt2d.style.flexDirection="";
  if(document.getElementById("pt2").classList.contains("on"))saveToolOutput(activeToolId);
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("ph").classList.add("on");
  document.getElementById("hbtn").classList.add("on");
  restoreHomeOutput();
  document.getElementById("panels").scrollTop=0;
}

function goTool(id){
  _setTopbarActive(null);
  const _tl=document.querySelector(".tpi-left"); if(_tl) _tl.style.display="";
  const _pt2d2=document.getElementById("pt2"); if(_pt2d2) _pt2d2.style.flexDirection="";
  const t=T[id];if(!t)return;
  if(document.getElementById("ph").classList.contains("on"))saveHomeOutput();
  else if(document.getElementById("pt2").classList.contains("on"))saveToolOutput(activeToolId);
  const prevToolId=activeToolId;
  const wasRunningSameTool=(prevToolId===id&&trun);
  if(!wasRunningSameTool) _streamGen++;  // invalidate any running stream's writes
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("pt2").classList.add("on");
  document.querySelectorAll(".sb-tool").forEach(b=>{if(b.getAttribute("onclick")===`goTool('${id}')`)b.classList.add("on")});
  activeToolId=id;
  updateHistoryBtn();
  // Highlight active tool card on home
  const tpi=document.getElementById("tpi");
  tpi.className="tool-panel-inner "+t.cat;
  document.getElementById("tcb").textContent=t.cl;
  document.getElementById("tic").textContent=ICONS[id]||"⚙️";
  document.getElementById("tt").textContent=t.name;
  document.getElementById("ts").textContent=t.sub;

  // Build form HTML
  let h="";

  
  if(t._isFootage){
    document.getElementById("tf").innerHTML="";
    // Centered full-panel search
    const _tpr=document.getElementById("tr");
    const _tpl=document.querySelector(".tpi-left");
    if(_tpl) _tpl.style.display="none";
    const _pt=document.getElementById("pt2");
    if(_pt) _pt.style.flexDirection="column";
    if(_tpr) _tpr.innerHTML=`
      <div class="cs-wrap" id="cs-wrap">
        <div class="cs-center" id="cs-center">
          <div class="cs-label">Stock Footage</div>
          <div class="cs-bar">
            <input class="cs-input" id="tf_query" type="text" placeholder="ocean waves, forest drone, city night..." autocomplete="off" spellcheck="false">
          </div>
          <div class="cs-chips">
            <button class="mf-chip active" id="fm-general" onclick="setFootageMode(this,'general')">General</button>
            <button class="mf-chip" id="fm-cars" onclick="setFootageMode(this,'cars')">Cars</button>
            <div class="cs-count-wrap">
              <label class="cs-count-lbl">Results</label>
              <select class="cs-count-sel" id="cs-result-count">
                <option value="4">4</option><option value="6" selected>6</option>
                <option value="10">10</option><option value="16">16</option><option value="24">24</option>
              </select>
            </div>
          </div>
        </div>
        <div class="cs-results" id="cs-results"></div>
      </div>`;
    document.getElementById("panels").scrollTop=0;
    window._footageMode="general";
    setTimeout(()=>{
      const inp=document.getElementById("tf_query"); if(!inp) return;
      inp.focus();
      let dt=null;
      inp.addEventListener("input",()=>{
        clearTimeout(dt);
        if(!inp.value.trim()){ const r=document.getElementById("cs-results"); if(r) r.innerHTML=""; _csSetSearched(false); return; }
        dt=setTimeout(()=>_csRun("footage"),200);
      });
      inp.addEventListener("keydown",e=>{ if(e.key==="Enter"){ clearTimeout(dt); if(inp.value.trim()) _csRun("footage"); }});
    },0);
    return;
  }
  if(t._isLive){
    document.getElementById("tf").innerHTML="";
    const _tpr2=document.getElementById("tr");
    const _tpl2=document.querySelector(".tpi-left");
    if(_tpl2) _tpl2.style.display="none";
    const _pt2x=document.getElementById("pt2");
    if(_pt2x) _pt2x.style.flexDirection="column";
    if(_tpr2) _tpr2.innerHTML=`
      <div class="cs-wrap" id="cs-wrap">
        <div class="cs-center" id="cs-center">
          <div class="cs-label">3D Model Finder</div>
          <div class="cs-bar">
            <input class="cs-input" id="tf_query" type="text" placeholder="${t.f[0].p||'low poly car, character sword, building...'}" autocomplete="off" spellcheck="false">
          </div>
          <div class="cs-chips" id="mf-filters">
            <button class="mf-chip active" data-cat="all" onclick="set3DCat(this,'all')">All</button>
            <button class="mf-chip" data-cat="characters" onclick="set3DCat(this,'characters')">Characters</button>
            <button class="mf-chip" data-cat="vehicles" onclick="set3DCat(this,'vehicles')">Vehicles</button>
            <button class="mf-chip" data-cat="architecture" onclick="set3DCat(this,'architecture')">Architecture</button>
            <button class="mf-chip" data-cat="nature" onclick="set3DCat(this,'nature')">Nature</button>
            <button class="mf-chip" data-cat="weapons" onclick="set3DCat(this,'weapons')">Weapons</button>
            <button class="mf-chip" data-cat="props" onclick="set3DCat(this,'props')">Props</button>
            <button class="model-free-toggle" id="mft" onclick="toggle3DFree(this)">Free only</button>
            <div class="cs-count-wrap">
              <label class="cs-count-lbl">Results</label>
              <select class="cs-count-sel" id="cs-result-count">
                <option value="6">6</option><option value="12" selected>12</option>
                <option value="20">20</option><option value="30">30</option>
              </select>
            </div>
          </div>
        </div>
        <div class="cs-results" id="cs-results"></div>
      </div>`;
    document.getElementById("panels").scrollTop=0;
    window._3dCategory="all"; window._3dFreeOnly=false;
    setTimeout(()=>{
      const inp=document.getElementById("tf_query"); if(!inp) return;
      inp.focus();
      let dt=null;
      inp.addEventListener("input",()=>{
        clearTimeout(dt);
        if(!inp.value.trim()){ const r=document.getElementById("cs-results"); if(r) r.innerHTML=""; _csSetSearched(false); return; }
        dt=setTimeout(()=>_csRun("3d"),200);
      });
      inp.addEventListener("keydown",e=>{ if(e.key==="Enter"){ clearTimeout(dt); if(inp.value.trim()) _csRun("3d"); }});
    },0);
  if(t._isDlCentered){
    document.getElementById("tf").innerHTML="";
    const _dtpl=document.querySelector(".tpi-left"); if(_dtpl) _dtpl.style.display="none";
    const _dpt=document.getElementById("pt2"); if(_dpt) _dpt.style.flexDirection="column";
    const _dtr=document.getElementById("tr");
    if(_dtr) _dtr.innerHTML=`
      <div class="cs-wrap" id="cs-wrap">
        <div class="cs-center" id="cs-center">
          <div class="cs-label">Video Downloader</div>
          <div class="cs-mode-toggle">
            <button class="cs-mode-btn active" id="dlm-single" onclick="setDlMode('single')">Single</button>
            <button class="cs-mode-btn" id="dlm-bulk" onclick="setDlMode('bulk')">Bulk / Profile</button>
          </div>
          <div class="cs-bar">
            <input class="cs-input" id="tf_dl_url" type="text" placeholder="Paste a TikTok or YouTube URL…" autocomplete="off" spellcheck="false">
          </div>
          <div class="cs-chips">
            <div class="cs-count-wrap">
              <label class="cs-count-lbl">Quality</label>
              <select class="cs-count-sel" id="tf_quality">
                <option value="1080">1080p</option><option value="720" selected>720p</option>
                <option value="480">480p</option><option value="best">Best</option>
              </select>
            </div>
            <div class="cs-count-wrap" id="dl-limit-wrap" style="display:none">
              <label class="cs-count-lbl">Limit</label>
              <select class="cs-count-sel" id="tf_limit">
                <option value="20">20</option><option value="50">50</option>
                <option value="100">100</option><option value="all">All</option>
              </select>
            </div>
            <button class="cs-run-btn" onclick="runDlCentered()">
              <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14"><path d="M3 2l11 6-11 6z"/></svg>
              Download
            </button>
          </div>
        </div>
        <div class="cs-results" id="cs-results"></div>
      </div>`;
    document.getElementById("panels").scrollTop=0;
    window._dlMode="single";
    if(!wasRunningSameTool){ trun=false; restoreToolOutput(id); }
    setTimeout(()=>{
      const inp=document.getElementById("tf_dl_url"); if(!inp) return;
      inp.focus();
      inp.addEventListener("keydown",e=>{ if(e.key==="Enter"&&inp.value.trim()) runDlCentered(); });
    },0);
    return;
  }
  if(t._isScenePack){
    document.getElementById("tf").innerHTML="";
    const _stpl=document.querySelector(".tpi-left"); if(_stpl) _stpl.style.display="none";
    const _spt=document.getElementById("pt2"); if(_spt) _spt.style.flexDirection="column";
    const _str=document.getElementById("tr");
    if(_str) _str.innerHTML=`
      <div class="cs-wrap" id="cs-wrap">
        <div class="cs-center" id="cs-center">
          <div class="cs-label">Scene Pack Finder</div>
          <div style="font-family:var(--fm);font-size:.72rem;color:#2e2e2e;margin-bottom:16px;text-align:center">Free scene packs from vlscenepacks.com</div>
          <div class="cs-bar">
            <input class="cs-input" id="tf_query" type="text"
              placeholder="anime, dark, horror, aesthetic, cinematic…" autocomplete="off" spellcheck="false">
          </div>
          <div class="cs-chips">
            <button class="mf-chip active" data-sc="all"         onclick="setSceneCat(this,'all')">All</button>
            <button class="mf-chip" data-sc="anime"      onclick="setSceneCat(this,'anime')">Anime</button>
            <button class="mf-chip" data-sc="dark"       onclick="setSceneCat(this,'dark')">Dark</button>
            <button class="mf-chip" data-sc="aesthetic"  onclick="setSceneCat(this,'aesthetic')">Aesthetic</button>
            <button class="mf-chip" data-sc="horror"     onclick="setSceneCat(this,'horror')">Horror</button>
            <button class="mf-chip" data-sc="cinematic"  onclick="setSceneCat(this,'cinematic')">Cinematic</button>
            <button class="mf-chip" data-sc="trending"   onclick="setSceneCat(this,'trending')">Trending</button>
          </div>
        </div>
        <div class="cs-results" id="cs-results"></div>
      </div>`;
    document.getElementById("panels").scrollTop=0;
    window._sceneCat="all";
    setTimeout(()=>{
      const inp=document.getElementById("tf_query"); if(!inp) return;
      inp.focus();
      let dt=null;
      inp.addEventListener("input",()=>{ clearTimeout(dt); if(inp.value.trim()) dt=setTimeout(()=>runSceneSearch(),300); else { _csSetSearched(false); const r=document.getElementById("cs-results"); if(r) r.innerHTML=""; } });
      inp.addEventListener("keydown",e=>{ if(e.key==="Enter"&&inp.value.trim()){ clearTimeout(dt); runSceneSearch(); }});
    },0);
    return;
  }
    if(t._isHanalyze){
    document.getElementById("tf").innerHTML="";
    const _htpl=document.querySelector(".tpi-left");
    if(_htpl) _htpl.style.display="none";
    const _hpt=document.getElementById("pt2");
    if(_hpt) _hpt.style.flexDirection="column";
    const _htr=document.getElementById("tr");
    // Remove overflow from tr so flex sticky layout works
    if(_htr){ _htr.style.overflow="visible"; _htr.style.padding="0"; _htr.style.flex="1"; _htr.style.display="flex"; _htr.style.flexDirection="column"; }
    if(_htr) _htr.innerHTML=`
      <div class="cs-wrap" id="cs-wrap">
        <div class="cs-center" id="cs-center">
          <div class="cs-label">Hashtag Analyzer</div>
          <div style="font-family:var(--fm);font-size:.72rem;color:#2e2e2e;margin-bottom:8px;text-align:center">Avg views · top videos · trending sounds · related hashtags</div>
          <div class="cs-bar">
            <input class="cs-input" id="tf_hashtags" type="text"
              placeholder="#hashtag  or  #tag1 #tag2 …" autocomplete="off" spellcheck="false">
          </div>
          <div class="cs-chips">
            <div class="cs-hint" style="font-family:var(--fm);font-size:.7rem;color:#333">Last 7 days · UGC sounds filtered · press Enter</div>
          </div>
        </div>
        <div class="cs-results" id="cs-results"></div>
      </div>`;
    document.getElementById("panels").scrollTop=0;
    setTimeout(()=>{
      const inp=document.getElementById("tf_hashtags"); if(!inp) return;
      inp.focus();
      inp.addEventListener("keydown",e=>{ if(e.key==="Enter" && inp.value.trim()) _csRunHanalyze(); });
    },0);
    return;
  }
  } else {
    const normalFields=t.f.filter(f=>f.type!=="preset-cards");
    const cardFields=t.f.filter(f=>f.type==="preset-cards");
    if(normalFields.length){
      h+=`<div class="form-row${normalFields.length===1?" single":""}">`;
      normalFields.forEach(f=>{
        h+=`<div class="form-field"><label class="form-lbl">${f.l}</label>`;
        if(f.s){
          h+=`<select class="form-sel" id="tf_${f.id}">${f.s.map(o=>`<option value="${o}">${o}</option>`).join("")}</select>`;
        }else if(f.browse){
          const bfJson=f.browseFilters?JSON.stringify(f.browseFilters).replace(/"/g,"&quot;"):"[]";
          h+=`<div class="browse-row"><input class="form-in" id="tf_${f.id}" type="text" placeholder="${f.p||""}"><button class="browse-btn" onclick="browseInput('tf_${f.id}','${f.browse}','${bfJson}')">Browse…</button></div>`;
        }else{
          h+=`<input class="form-in" id="tf_${f.id}" type="text" placeholder="${f.p||""}">`;
        }
        h+=`</div>`;
      });
      h+=`</div>`;
    }
    cardFields.forEach(f=>{
      h+=`<div style="margin-bottom:18px;max-width:720px"><div class="preset-cards-lbl">${f.l}</div><div class="preset-cards-grid" id="pcg_${f.id}">`;
      (f.cards||[]).forEach((c,i)=>{
        const sel=i===0?" selected":"";
        h+=`<div class="preset-card${sel}" data-preset-field="tf_${f.id}" data-preset-val="${c.id}" onclick="selectPresetCard(this)"><span class="preset-card-check">✓</span><span class="preset-card-icon">${c.icon}</span><div class="preset-card-name">${c.name}</div><div class="preset-card-desc">${c.desc}</div></div>`;
      });
      (_customCompPresets||[]).forEach(cp=>{
        h+=`<div class="preset-card" data-preset-field="tf_${f.id}" data-preset-val="${x(cp.path)}" onclick="selectPresetCard(this)"><span class="preset-card-check">✓</span><span class="preset-card-icon">📂</span><div class="preset-card-name">${x(cp.name)}</div><div class="preset-card-desc" style="word-break:break-all;font-size:.64rem">${x(cp.path)}</div><button class="preset-card-del" onclick="event.stopPropagation();removeCompPreset('${x(cp.path)}','tf_${f.id}')">✕</button></div>`;
      });
      h+=`<div class="preset-card preset-card-add" onclick="addCompPreset('tf_${f.id}')"><span class="preset-card-icon" style="font-size:1.6rem;color:var(--amber);opacity:.6">+</span><div class="preset-card-name" style="color:var(--amber)">Add own preset</div><div class="preset-card-desc">Browse for a HandBrake preset .json</div><button class="browse-btn" style="margin-top:10px;width:100%;font-size:.72rem;padding:6px 0" onclick="event.stopPropagation();addCompPreset('tf_${f.id}')">Browse…</button></div></div>`;
      const defVal=f.cards&&f.cards[0]?f.cards[0].id:"";
      h+=`<input type="hidden" id="tf_${f.id}" value="${defVal}"></div>`;
    });
  }
  // Preset chips (category or tool-specific)
  if(!t._isLive){
    const catChips=activeCategory&&PC[activeCategory]&&PC[activeCategory].chips&&PC[activeCategory].chips[id]?PC[activeCategory].chips[id]:null;
    const chips=catChips||(t.presets&&t.presets.length?t.presets:null);
    if(chips){
      const lbl=catChips?(PC[activeCategory].label+" Presets"):"Presets";
      h+=`<div class="preset-row"><span class="preset-lbl">${lbl}</span>`;
      chips.forEach(p=>{const vals=JSON.stringify(p.v).replace(/"/g,"&quot;");h+=`<button class="preset-chip" onclick="applyPreset(${vals})">${p.l}</button>`;});
      h+=`</div>`;
    }
    h+=`<div class="tool-actions"><button class="run-btn" id="rbtn" onclick="runTool('${id}')"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M3 2l11 6-11 6z"/></svg> Run ${t.name}</button></div>`;
  } else {
    h+=`<div class="tool-actions"><button class="run-btn" id="rbtn" onclick="run3DSearch()"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M6.5 1A5.5 5.5 0 1 0 12 6.5a5.5 5.5 0 0 0-5.5-5.5zm0 10A4.5 4.5 0 1 1 11 6.5 4.5 4.5 0 0 1 6.5 11zm8.854 3.354l-3-3a.5.5 0 0 0-.708.708l3 3a.5.5 0 0 0 .708-.708z"/></svg> Search</button></div>`;
  }

  document.getElementById("tf").innerHTML=h;
  hideContextBadge();

  const tpEl=document.getElementById("tp"),trEl=document.getElementById("tr");
  if(wasRunningSameTool){
    if(tpEl)tpEl.style.display="block";
  }else{
    if(tpEl)tpEl.style.display="none";
    trun=false;
    restoreToolOutput(id);
  }
  document.getElementById("panels").scrollTop=0;

  // 3D input wired inside _isLive block
}

function set3DCat(btn,cat){
  _3dCategory=cat;
  document.querySelectorAll(".mf-chip").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");
  const inp=document.getElementById("tf_query");
  if(inp&&inp.value.trim()) _csRun("3d");
}

function toggle3DFree(btn){
  _3dFreeOnly=!_3dFreeOnly;
  btn.classList.toggle("active",_3dFreeOnly);
  const inp=document.getElementById("tf_query");
  if(inp&&inp.value.trim()) _csRun("3d");
}

async function run3DSearch(){
  const inp=document.getElementById("tf_query");
  const q=(inp?inp.value:"").trim();
  const dest=document.getElementById("cs-results")||document.getElementById("tr");
  if(!q){if(dest)dest.innerHTML="";return;}
  if(dest)dest.innerHTML='<div class="search-dots-wrap"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';
  try{
    const _3dCntEl=document.getElementById("cs-result-count"); const _3dCnt=_3dCntEl?_3dCntEl.value:"12";
    let url=`/api/3d-search?q=${encodeURIComponent(q)}&count=${_3dCnt}`;
    if(_3dCategory!=="all")url+=`&cat=${encodeURIComponent(_3dCategory)}`;
    if(_3dFreeOnly)url+=`&free=1`;
    const r=await fetch(url);
    const data=await r.json();
    if(dest)dest.innerHTML=r3DModels(data,q);
  }catch(e){
    if(dest)dest.innerHTML=errorCard("3D search failed: "+e.message);
  }
}

function r3DModels(data,query){
  let results=data.results||[];
  if(_3dFreeOnly)results=results.filter(m=>m.isDownloadable);
  if(!results.length)return`<div class="model-empty">No models found for "<strong>${x(query)}</strong>"<br><br><span style="font-size:.72rem;color:var(--text3)">Try broader keywords or disable filters</span></div>`;
  const cards=results.map(m=>{
    const imgs=m.thumbnails&&m.thumbnails.images?m.thumbnails.images:[];
    const thumb=(imgs.find(i=>i.width>=200)||imgs[0]||{}).url||"";
    const faces=m.faceCount?nK(m.faceCount)+" faces":"";
    const likes=m.likeCount?"♥ "+nK(m.likeCount):"";
    const stats=[faces,likes].filter(Boolean).join(" · ");
    const freeBadge=m.isDownloadable?`<span class="model-badge-free">FREE</span>`:"";
    const viewUrl=m.viewerUrl||`https://sketchfab.com/models/${m.uid||""}`;
    return`<div class="model-card" onclick="window.open('${x(viewUrl)}','_blank')">
      <div class="model-thumb-wrap">
        ${thumb?`<img class="model-thumb" src="${x(thumb)}" loading="lazy" alt="${x(m.name||'')}">`:
          `<div class="model-thumb-ph">3D</div>`}
        ${freeBadge}
      </div>
      <div class="model-info">
        <div class="model-name">${x(m.name||"Untitled")}</div>
        <div class="model-author">by ${x((m.user&&m.user.username)||"Unknown")}</div>
        ${stats?`<div class="model-stats">${stats}</div>`:""}
      </div>
    </div>`;
  }).join("");
  const src=data.source||"Sketchfab";
  return`<div class="model-grid">${cards}</div><div class="model-src">via ${x(src)}</div>`}

function applyPreset(vals){
  Object.entries(vals).forEach(([k,v])=>{const el=document.getElementById("tf_"+k);if(el)el.value=v});
  const btn=event&&event.target;
  if(btn&&btn.classList&&btn.classList.contains("preset-chip")){btn.classList.add("preset-chip-active");setTimeout(()=>btn.classList.remove("preset-chip-active"),600)}
}

// ── HOME DETECT ───────────────────────────────────────────────────────────────
const mi=document.getElementById("mi");
mi.addEventListener("input",()=>{clearTimeout(dtimer);dtimer=setTimeout(()=>doDetect(mi.value),260)});
mi.addEventListener("keydown",e=>{if(e.key==="Enter"&&det&&!hrun)runHome()});

async function doDetect(txt){
  if(!txt.trim()){setChip(null);return}
  try{const r=await fetch("/api/detect",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:txt})});det=await r.json();setChip(det);updateOpts(det.type)}catch(e){}
}
function setChip(d){
  const dc=document.getElementById("dc"),dl=document.getElementById("dlbl"),gb=document.getElementById("gb");
  if(!d||!d.type||d.type==="unknown"){dc.className="det-chip";gb.className="go-btn";return}
  const cm={tiktok_video:"dl",tiktok_profile:"dl",youtube_video:"dl",youtube_playlist:"dl",spotify_track:"mu",spotify_album:"mu",spotify_playlist:"mu",soundcloud:"mu",hashtag:"sc2"}[d.type]||"un";
  const ic={tiktok_video:"▶ ",tiktok_profile:"👤 ",youtube_video:"▶ ",youtube_playlist:"📋 ",spotify_track:"🎵 ",spotify_album:"💿 ",spotify_playlist:"🎧 ",soundcloud:"🎵 ",hashtag:"# "};
  dc.className=`det-chip show ${cm}`;dl.textContent=(ic[d.type]||"")+d.label;
  gb.className=hrun?"go-btn show busy":"go-btn show";
}
function updateOpts(tp){
  const row=document.getElementById("hor"),q=document.getElementById("oq"),aq=document.getElementById("oaq"),lm=document.getElementById("olim");
  const isV=["tiktok_video","youtube_video","tiktok_profile","youtube_playlist"].includes(tp);
  const isA=["spotify_track","spotify_album","spotify_playlist","soundcloud"].includes(tp);
  const isL=["hashtag","tiktok_profile","youtube_playlist"].includes(tp);
  q.style.display=isV?"flex":"none";aq.style.display=isA?"flex":"none";lm.style.display=isL?"flex":"none";
  row.style.display=(isV||isA||isL)?"flex":"none";setHomeClearVisible(!!_homeOutputCache);
}
async function doPaste(){try{const t=await navigator.clipboard.readText();mi.value=t;doDetect(t)}catch(e){mi.focus()}}
function ex(t){mi.value=t;mi.focus();doDetect(t)}

// ── RUN HOME ──────────────────────────────────────────────────────────────────
function runHome(){
  if(!det||!det.type||det.type==="unknown"||hrun)return;
  if(appBusy){const hr=document.getElementById("hr");if(hr){hr.innerHTML=errorCard("Another tool is already running.");_setClearForRes(hr,!!hr.innerHTML)}return}
  hrun=true;appBusy=true;
  const gb=document.getElementById("gb");gb.className="go-btn show busy";gb.textContent="Running...";
  const hp=document.getElementById("hp");hp.classList.add("show");
  document.getElementById("hr").innerHTML="";const _hw2=document.getElementById("hr-wrap");if(_hw2)_hw2.style.display="none";setHomeClearVisible(false);
  const hpb=document.getElementById("hpb");hpb.style.width="0%";hpb.classList.add("ind");
  document.getElementById("hpl").textContent="RUNNING";document.getElementById("hps").textContent="";
  const opts={quality:document.getElementById("sq")?.value||"1080",audio_quality:document.getElementById("saq")?.value||"320",limit:document.getElementById("slim")?.value||"300"};
  doStream("/api/run",{detected:det,options:opts},{
    barEl:hpb,lblEl:document.getElementById("hpl"),stEl:document.getElementById("hps"),
    resEl:document.getElementById("hr"),feedId:"hlf",onStart:()=>{const r=document.getElementById("hr");if(r)r.innerHTML="";},onEnd:()=>{const r=document.getElementById("hr");const w=document.getElementById("hr-wrap");if(r&&w){if(r.innerHTML.trim()===""){w.style.display="none";}else{w.style.display="block";}}},
    onDone:()=>{
      hrun=false;appBusy=false;
      const mi=document.getElementById("mi");if(mi)mi.value="";
      det=null;setChip(null);
      const hp=document.getElementById("hp");setTimeout(()=>{if(hp)hp.classList.remove("show")},2000);
      const g=document.getElementById("gb");g.className="go-btn";g.textContent="Run";
    }
  });
}

// ── RUN TOOL ──────────────────────────────────────────────────────────────────
function runTool(id){
  if(trun)return;
  if(appBusy){const tr=document.getElementById("tr");if(tr){tr.innerHTML=errorCard("Another tool is already running.");_setClearForRes(tr,!!tr.innerHTML)}return}
  const t=T[id];if(!t)return;
  trun=true;appBusy=true;activeToolId=id;
  document.getElementById("rbtn").classList.add("busy");
  const opts={};
  t.f.forEach(f=>{const el=document.getElementById("tf_"+f.id);if(el)opts[f.id]=el.value.trim()||el.placeholder||"edit"});
  const tp=document.getElementById("tp");tp.style.display="block";
  const tpb=document.getElementById("tpb");tpb.style.width="0%";tpb.classList.add("ind");
  document.getElementById("tpl").textContent="RUNNING";document.getElementById("tps").textContent="";
  document.getElementById("tr").innerHTML="";setToolClearVisible(false);
  doStream("/api/tool",{tool_id:id,options:opts},{
    barEl:tpb,lblEl:document.getElementById("tpl"),stEl:document.getElementById("tps"),
    resEl:document.getElementById("tr"),feedId:"tlf",
    onDone:()=>{
      trun=false;appBusy=false;
      const b=document.getElementById("rbtn");if(b)b.classList.remove("busy");
      const tp=document.getElementById("tp");
      if(tp) setTimeout(()=>{tp.style.display="none"},1200);
    }
  });
}

// ── STREAM ────────────────────────────────────────────────────────────────────
function makeLiveFeed(feedId){
  const feed=document.getElementById(feedId);if(!feed)return()=>{};
  feed.classList.add("show");
  const lines=[feed.children[0],feed.children[1],feed.children[2]];
  let buf=[];
  return function push(text,cls=""){
    buf.push({text,cls});if(buf.length>3)buf.shift();
    lines.forEach((el,i)=>{const entry=buf[i]||{text:"",cls:""};el.textContent=entry.text;el.className="lf-line"+(entry.cls?" "+entry.cls:"")+(i===buf.length-1?" active":"")});
  };
}

async function doStream(url,body,{barEl,lblEl,stEl,resEl,feedId,onDone,onStart}){
  const myGen=_streamGen; // capture at start — if _streamGen changes, we're stale
  function _stale(){ return myGen!==_streamGen && resEl && resEl.id==="tr"; }
  if(onStart) onStart();
  const pushLog=makeLiveFeed(feedId||"");let rd=null;
  try{
    const resp=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(!resp.ok){
      let msg="Request failed.";try{const data=await resp.json();msg=data.message||data.error||msg}catch(e){try{msg=await resp.text()||msg}catch(_e){}}
      if(resEl){resEl.innerHTML=errorCard(msg);_setClearForRes(resEl,!!resEl.innerHTML)}onDone();return;
    }
    const reader=resp.body.getReader();const dec=new TextDecoder();let buf="";
    while(true){
      const{value,done}=await reader.read();if(done)break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split("\n");buf=lines.pop();
      for(const line of lines){
        if(!line.startsWith("data: "))continue;
        let m;try{m=JSON.parse(line.slice(6))}catch(e){continue}
        if(m.type==="log"){const cls=/^✓|done|complete|saved/i.test(m.text)?"ok":/^✗|error|fail/i.test(m.text)?"err":/^⚠|warn/i.test(m.text)?"warn":"";pushLog(m.text,cls)}
        else if(m.type==="progress"){if(barEl){barEl.classList.remove("ind");barEl.style.width=(m.value/m.total*100).toFixed(1)+"%"}if(stEl)stEl.textContent=`${m.value} / ${m.total}`;if(m.track&&resEl)appendDlItem(resEl,m.track,m.ok)}
        else if(m.type==="result"){rd=m.data;if(resEl&&!_stale()){renderRes(resEl,rd,"");_setClearForRes(resEl,!!resEl.innerHTML)}}
        else if(m.type==="done"){if(barEl){barEl.classList.remove("ind");barEl.style.width="100%"}if(lblEl)lblEl.textContent="DONE";if(stEl)stEl.textContent="";pushLog("✓ "+m.text,"ok");updateHistoryBtn();if(resEl&&!_stale()){if(rd)renderRes(resEl,rd,m.text);else if(m.text)resEl.innerHTML=doneCard(m.text,m.path||"");_setClearForRes(resEl,!!resEl.innerHTML)}onDone()}
        else if(m.type==="error"){if(stEl)stEl.textContent="";if(lblEl)lblEl.textContent="ERROR";pushLog("✗ "+m.text,"err");if(resEl){resEl.innerHTML=errorCard(m.text);_setClearForRes(resEl,!!resEl.innerHTML)}onDone()}
        else if(m.type==="close")onDone();
      }
    }
  }catch(e){
    const msg=e.message.includes("fetch")?"Cannot connect to server — make sure EditorSuite is running via the .exe or .vbs launcher.":e.message;
    if(resEl){resEl.innerHTML=errorCard(msg);_setClearForRes(resEl,!!resEl.innerHTML)}onDone();
  }
}

// ── CUSTOM CATEGORIES ─────────────────────────────────────────────────────────
function _closeAddForm(){const f=document.getElementById("pcat-add-form");if(f)f.style.display="none";const btn=document.getElementById("pcat-add-btn");if(btn){btn.style.color="";btn.style.borderColor=""}}
function toggleCustomAdd(){
  const f=document.getElementById("pcat-add-form");
  const open=f.style.display==="none";
  if(open){
    f.style.display="flex";
    const btn=document.getElementById("pcat-add-btn");if(btn){btn.style.color="var(--purple)";btn.style.borderColor="var(--purple)"}
    const inp=document.getElementById("sb_cp_label");if(inp)inp.focus();
    setTimeout(()=>{function _o(e){if(!f.contains(e.target)&&e.target.id!=="pcat-add-btn"){const l=(document.getElementById("sb_cp_label")||{}).value||"",t=(document.getElementById("sb_cp_tag")||{}).value||"";if(!l.trim()&&!t.trim())_closeAddForm();document.removeEventListener("mousedown",_o)}}document.addEventListener("mousedown",_o)},0);
  }else _closeAddForm();
}
function buildCustomCategoryPC(cat){
  const tags=cat.hashtags||[];const multi=tags.join(", ");const first=tags[0]||"";
  const singleChips=tags.map(t=>({l:"#"+t,v:{hashtag:t}}));
  const multiChips=[{l:"All",v:{hashtags:multi}}];
  if(tags.length>2){for(let i=0;i<tags.length-1;i+=2){const slice=tags.slice(i,i+3).join(", ");multiChips.push({l:tags.slice(i,i+3).map(t=>"#"+t).join(" + "),v:{hashtags:slice}})}}
  return{label:cat.name,defaults:{scraper:{hashtag:first},crosshash:{hashtags:multi},hanalyze:{hashtags:multi}},chips:{scraper:singleChips,crosshash:multiChips,hanalyze:multiChips}};
}
async function sbAddCustomCategory(){
  const lbl=document.getElementById("sb_cp_label").value.trim();
  const raw=document.getElementById("sb_cp_tag").value.trim();
  if(!lbl||!raw)return;
  const tags=raw.split(",").map(t=>t.trim().replace(/^#/,"")).filter(Boolean);
  if(!tags.length)return;
  if(_customCategories.some(c=>c.name.toLowerCase()===lbl.toLowerCase())){document.getElementById("sb_cp_label").style.borderColor="var(--red)";setTimeout(()=>{document.getElementById("sb_cp_label").style.borderColor=""},1500);return}
  const cat={name:lbl,hashtags:tags};_customCategories.push(cat);
  await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({custom_categories:_customCategories})});
  document.getElementById("sb_cp_label").value="";document.getElementById("sb_cp_tag").value="";_closeAddForm();initCategories();
  const t2=document.createElement("div");t2.textContent="✓ "+lbl+" added";t2.style.cssText="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--bg3);border:1px solid var(--border2);color:var(--green);font-family:var(--fm);font-size:.75rem;padding:8px 18px;border-radius:8px;z-index:999;pointer-events:none;transition:opacity .4s";document.body.appendChild(t2);setTimeout(()=>{t2.style.opacity="0";setTimeout(()=>t2.remove(),400)},1800);
}
async function removeCustomCategory(idx){
  const cat=_customCategories[idx];if(!cat)return;
  if(activeCategory===cat.name)clearCategory();
  delete PC[cat.name];_customCategories.splice(idx,1);
  await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({custom_categories:_customCategories})});
  initCategories();
}

// ── SETTINGS ──────────────────────────────────────────────────────────────────
function goSettings(){
  _setTopbarActive("tb-settings");
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("ps").classList.add("on");
  document.getElementById("panels").scrollTop=0;loadSettings();
}
async function loadSettings(){
  try{
    const cfg=await fetch("/api/config").then(r=>r.json());
    ["my_username","root_dir","dir_sounds","dir_downloads","dir_audio","dir_analysis","dir_compress","dir_images","default_videos","default_top_n","scroll_delay","stale_limit","spotify_client_id","spotify_client_secret","pexels_api_key","google_client_id","google_client_secret"].forEach(k=>{const el=document.getElementById("cfg_"+k);if(el)el.value=cfg[k]||""});
    ["auto_open_folder"].forEach(k=>{const el=document.getElementById("cfg_"+k);if(el)el.checked=!!cfg[k]});
  }catch(e){console.error("loadSettings",e)}
}
async function saveSettings(){
  const btn=document.querySelector(".settings-save-btn");btn.disabled=true;
  const updates={};
  ["my_username","root_dir","dir_sounds","dir_downloads","dir_audio","dir_analysis","dir_compress","dir_images","default_videos","default_top_n","scroll_delay","stale_limit","spotify_client_id","spotify_client_secret"].forEach(k=>{const el=document.getElementById("cfg_"+k);if(el)updates[k]=el.value.trim()});
  ["auto_open_folder"].forEach(k=>{const el=document.getElementById("cfg_"+k);if(el)updates[k]=el.checked});
  try{await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(updates)});const toast=document.getElementById("stst");toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),2000)}catch(e){alert("Save failed: "+e.message)}
  btn.disabled=false;
}

let _customPresets=[];
function renderSidebarCustomPresets(){}
function injectCustomPresets(list){["scraper","sp_exp","hanalyze","crosshash"].forEach(id=>{if(!T[id])return;T[id].presets=(T[id].presets||[]).filter(p=>!p._custom);list.forEach(p=>T[id].presets.push({...p,_custom:true}))})}

// ── RENDERERS ─────────────────────────────────────────────────────────────────
function renderRes(el,d,msg){
  const type=d.type||"";
  if(type==="sounds")el.innerHTML=rSounds(d,msg);
  else if(type==="cross_sounds")el.innerHTML=rCrossSounds(d,msg);
  else if(type==="hashtag_analyze")el.innerHTML=rHashtagAnalyze(d,msg);
  else if(type==="competitor")el.innerHTML=rCompetitor(d,msg);
  else el.innerHTML=doneCard(msg||"Done");
}

function rSounds(d,msg){
  _soundsCache=d;
  const listCount=d.top_by_count||d.top||[];const listAvg=d.top_by_views||d.top||[];
  const list=_soundsSortMode==="avg"?listAvg:listCount;
  const getMetric=s=>_soundsSortMode==="avg"?(s.avg_views??s.avg_view??s.avg_plays??s.avg_views_per_video??s.views??s.total_views??s.plays??0):(s.count??0);
  const mx=list.length?Math.max(1,...list.map(getMetric)):1;
  const rows=list.map((s,i)=>{
    const pct=(getMetric(s)/mx*100).toFixed(0);
    const rc=i===0?"gold":i===1?"silver":i===2?"bronze":"";
    const title=s.title||"—";const author=s.author||"";
    const avgViews=s.avg_views??s.avg_view??s.avg_plays??s.avg_views_per_video;
    const views=s.views??s.total_views??s.plays;
    const viewText=avgViews!=null?`Avg ${nK(avgViews)} views`:(views!=null?`${nK(views)} views`:"");
    const meta=viewText?`<div class="s-meta">${viewText}</div>`:"";
    const postBtn=s.post_url?`<button class="s-post-btn" data-url="${x(s.post_url)}" onclick="openUrl(this.dataset.url)">View post</button>`:"";
    return`<div class="s-row"><div class="s-rank ${rc}">${i<3?(i===0?"🥇":i===1?"🥈":"🥉"):i+1}</div><div class="s-info"><div class="s-name">${x(title)}</div><div class="s-auth">${x(author)}</div>${meta}</div><div class="s-bar-wrap"><div class="s-bar" style="width:${pct}%"></div></div><div class="s-cnt">${s.count}×</div>${postBtn}<button class="s-dl-btn" onclick="dlSoundRow(this,'${x(title).replace(/'/g,"&#39;")}','${x(author).replace(/'/g,"&#39;")}')">⬇ Download</button></div>`;
  }).join("");
  const ob=d.html_path?`<button class="open-btn" data-path="${x(d.html_path)}" onclick="openF(this.dataset.path)">Open Full Report ↗</button>`:"";
  const showClear=!!(document.getElementById("tr")?.innerHTML);
  const sort=`<div class="sound-sort"><button class="clear-btn" id="tclear" onclick="clearToolOutput(activeToolId)" style="display:${showClear?"inline-flex":"none"}">Clear</button><button class="sort-btn ${_soundsSortMode==="count"?"on":""}" onclick="setSoundsSort('count')">Most Used</button><button class="sort-btn ${_soundsSortMode==="avg"?"on":""}" onclick="setSoundsSort('avg')">Avg Views</button></div>`;
  return`<div class="card"><div class="card-hdr"><div class="card-title">Trending Sounds — #${x(d.hashtag)}</div><div class="card-meta">${new Date().toLocaleTimeString()}</div>${sort}</div><div class="stats-strip c3"><div class="stat"><div class="stat-n">${n(d.scanned)}</div><div class="stat-l">Scanned</div></div><div class="stat"><div class="stat-n pink">${n(d.kept)}</div><div class="stat-l">Sounds found</div></div><div class="stat"><div class="stat-n dim">${n(d.removed)}</div><div class="stat-l">Filtered</div></div></div><div class="sound-rows">${rows}</div><div class="card-footer"><div class="cf-icon">✓</div><div class="cf-text">${x(msg||"Complete")}</div>${ob}</div></div>`;
}

function rCrossSounds(d,msg){
  const rows=(d.sounds||[]).map((s,i)=>{
    const pills=(s.tags||[]).map(t=>`<span class="tag-pill">#${x(t)}</span>`).join("");
    const post=s.post_url?`<button class="s-post-btn" data-url="${x(s.post_url)}" onclick="openUrl(this.dataset.url)">View post</button>`:"";
    const dl=`<button class="s-dl-btn" onclick="dlSoundRow(this,'${x(s.title||'').replace(/'/g,"&#39;")}','${x(s.author||'').replace(/'/g,"&#39;")}')">⬇ Download</button>`;
    return`<tr><td style="padding-left:20px;font-family:var(--fm);font-size:.67rem;color:var(--text3)">${i+1}</td><td><div class="s-name">${x(s.title||"—")}</div><div class="s-auth">${x(s.author||"")}</div></td><td>${pills}</td><td style="font-family:var(--fm);font-size:.77rem;color:var(--text2);text-align:right">${s.count}×</td><td style="text-align:right">${post}</td><td style="text-align:right;padding-right:20px">${dl}</td></tr>`;
  }).join("");
  return`<div class="card"><div class="card-hdr"><div class="card-title">Cross-Hashtag Sounds</div><div class="card-meta">${(d.tags||[]).map(t=>"#"+t).join(", ")}</div></div><table class="data-table"><thead><tr><th>#</th><th>Sound</th><th>Found in</th><th style="text-align:right">Count</th><th style="text-align:right">Post</th><th style="text-align:right;padding-right:20px">Download</th></tr></thead><tbody>${rows}</tbody></table><div class="card-footer"><div class="cf-icon">✓</div><div class="cf-text">${x(msg||"Done")}</div></div></div>`;
}

// ── HASHTAG ANALYZER video open ──────────────────────────────────────────────
function haOpenVideo(url, thumb, sound){
  if(!url) return;
  // Open in system default browser via /api/open for audio support
  fetch("/api/open",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({path:url, url:true})}).catch(()=>{
    // Fallback: window.open
    window.open(url,"_blank","noopener");
  });
}


function rHashtagAnalyze(d,msg){
  const EXCL = new Set(["fyp","foryou","foryoupage","viral","trending","tiktok","xyzbca","blowthisup","explore","fy","parati","pourtoi"]);
  const rows = d.rows||[];

  // ── Stats cards
  const statsHtml = rows.map(r=>{
    const tag = r.tag||"";
    const avgV = r.avg_views||0;
    const posts = r.posts||0;
    const diff = r.difficulty||"";
    const diffColor = diff==="Low"?"#4ade80":diff==="Medium"?"#fbbf24":"#f43f5e";
    return `<div class="ha-stat-card">
      <div class="ha-tag">${x(tag)}</div>
      <div class="ha-avg">${nK(avgV)}<span class="ha-avg-lbl"> avg views</span></div>
      <div class="ha-row"><span class="ha-lbl">Posts</span><span class="ha-val">${nK(posts)}</span></div>
      <div class="ha-row"><span class="ha-lbl">Avg likes</span><span class="ha-val">${nK(r.avg_likes||0)}</span></div>
      ${diff?`<div class="ha-row"><span class="ha-lbl">Competition</span><span style="color:${diffColor};font-family:var(--fm);font-size:.75rem;font-weight:600">${x(diff)}</span></div>`:""}
    </div>`;
  }).join("");

  // ── Related hashtags (from co_tags field, exclude banned)
  const allCoTags = [];
  (d.co_tags||[]).forEach(t=>{ if(!EXCL.has(t.toLowerCase().replace(/^#/,""))) allCoTags.push(t); });
  const relHtml = allCoTags.length ? `
    <div class="ha-section">
      <div class="ha-section-title">Related Hashtags</div>
      <div class="ha-tags-wrap">${allCoTags.slice(0,20).map(t=>`<span class="ha-pill">${x(t.startsWith("#")?t:"#"+t)}</span>`).join("")}</div>
    </div>` : "";

  // ── Top videos
  const topVids = (d.top_videos||[]).slice(0,8);
  const vidsHtml = topVids.length ? `
    <div class="ha-section">
      <div class="ha-section-title">Top Videos · Last 7 Days</div>
      <div class="ha-vids-grid">${topVids.map(v=>`
        <div class="ha-vid-card" onclick="haOpenVideo('${x(v.url||"")}','${x(v.thumb||"")}','${x(v.sound||"")}')">
          ${v.thumb?`<div class="ha-vid-thumb"><img src="${x(v.thumb)}" loading="lazy" onerror="this.parentElement.style.background='#111'"></div>`:'<div class="ha-vid-thumb" style="background:#111"></div>'}
          <div class="ha-vid-info">
            <div class="ha-vid-views">${nK(v.views||0)} views</div>
            ${v.sound?`<div class="ha-vid-sound">♪ ${x(v.sound)}</div>`:""}
            <div class="ha-vid-date" style="font-family:var(--fm);font-size:.65rem;color:#333">${x(v.date||"")}</div>
          </div>
        </div>`).join("")}
      </div>
    </div>` : "";

  // ── Top sounds
  const sounds = d.top_sounds||[];
  const soundsHtml = sounds.length ? `
    <div class="ha-section">
      <div class="ha-section-title">Trending Sounds</div>
      <div style="display:flex;flex-direction:column;gap:6px">${sounds.slice(0,6).map((s,i)=>`
        <div class="ha-sound-row">
          <span class="ha-sound-rank">${i+1}</span>
          <span class="ha-sound-name">${x(s.name||s)}</span>
          ${s.count?`<span class="ha-sound-count">${nK(s.count)}x</span>`:""}
        </div>`).join("")}
      </div>
    </div>` : "";

  return `<div class="ha-wrap">
    <div class="ha-stats-row">${statsHtml}</div>
    ${relHtml}${vidsHtml}${soundsHtml}
  </div>`;
}

function rCompetitor(d,msg){
  const s1=d.stats1||{},s2=d.stats2||{};
  const stat=(lbl,v1,v2)=>`<div class="col-stat"><div class="col-stat-lbl">${lbl}</div><div class="col-stat-val">${nK(v1)}</div></div><div class="col-stat"><div class="col-stat-lbl">${lbl}</div><div class="col-stat-val" style="color:var(--purple)">${nK(v2)}</div></div>`;
  return`<div class="card"><div class="card-hdr"><div class="card-title">Competitor Comparison</div></div><div class="two-col"><div class="col-hdr"><span class="at">@${x(d.user1)}</span></div><div class="col-hdr"><span class="at" style="color:var(--purple)">@${x(d.user2)}</span></div>${stat("Avg Views",s1.avg,s2.avg)}${stat("Total Views",s1.total,s2.total)}${stat("Posts",s1.count,s2.count)}${stat("Peak Views",s1.top_views&&s1.top_views[0],s2.top_views&&s2.top_views[0])}</div><div class="card-footer"><div class="cf-icon">✓</div><div class="cf-text">${x(msg||"Done")}</div></div></div>`;
}

function appendDlItem(el,name,ok){
  let list=el.querySelector(".dl-progress-list");
  if(!list){el.innerHTML=`<div class="card"><div class="card-hdr"><div class="card-title">Downloading…</div></div><div class="dl-progress-list"></div></div>`;list=el.querySelector(".dl-progress-list")}
  const row=document.createElement("div");row.className="dl-item";row.innerHTML=`<div class="dl-item-icon">${ok?"✓":"✗"}</div><div class="dl-item-name">${x(name)}</div>`;row.style.color=ok?"var(--green)":"var(--text3)";list.appendChild(row);el.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function doneCard(msg,path){
  const match=msg.match(/(?:Saved(?: to)?|→)\s*(.+)/i);
  const savePath=path||(match?match[1].trim():"");
  const btns=savePath?`<div class="dl-btns"><button class="dl-btn primary" data-path="${x(savePath)}" onclick="openFolder(this.dataset.path)">📁 Open Folder</button></div>`:"";
  return`<div class="card"><div class="card-body"><div class="dl-status"><div class="dl-icon">✓</div><div class="dl-text">Done</div><div class="dl-sub">${x(msg)}</div>${btns}</div></div></div>`;
}
function errorCard(msg){return`<div class="card" style="border-color:rgba(244,63,94,.28)"><div class="card-body"><div class="dl-status"><div class="dl-icon">✗</div><div class="dl-text" style="color:var(--red)">Error</div><div class="dl-sub">${x(msg)}</div></div></div></div>`}
function switchTab(btn,panelId){const card=btn.closest(".card");card.querySelectorAll(".tab-btn").forEach(b=>b.classList.remove("on"));card.querySelectorAll(".tab-panel").forEach(p=>p.classList.remove("on"));btn.classList.add("on");document.getElementById(panelId)?.classList.add("on")}



// ── ACCOUNT / STATS ──────────────────────────────────────────────────────────

// navigation
function goAccount(){
  _setTopbarActive("tb-acct");
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("pac").classList.add("on");
  document.getElementById("sb-acct-btn").classList.add("on");
  document.getElementById("panels").scrollTop=0;
  
}


// ── FOLLOWING PICKER ──────────────────────────────────────────────────────────
let _fwSearchTimer = null;

async function fwOnFocus(){
  const drop = document.getElementById("fw-drop");
  if(!drop) return;
  drop.classList.add("open");
  if(!_fwLoaded) await fwLoad("");
}

function fwClose(){
  const drop = document.getElementById("fw-drop");
  if(drop) drop.classList.remove("open");
}

async function fwOnInput(val){
  const drop = document.getElementById("fw-drop");
  if(!drop) return;
  drop.classList.add("open");
  clearTimeout(_fwSearchTimer);
  _fwSearchTimer = setTimeout(()=>fwLoad(val), 280);
}

async function fwLoad(q){
  const drop = document.getElementById("fw-drop");
  if(!drop) return;

  // Filter cache first for instant feel
  if(_fwLoaded && _fwCache.length){
    fwRender(q ? _fwCache.filter(u=>
      u.handle.toLowerCase().includes(q.toLowerCase()) ||
      u.name.toLowerCase().includes(q.toLowerCase())
    ) : _fwCache);
    return;
  }

  drop.innerHTML=`<div class="fw-picker-loading"><div class="acct-spinner" style="display:inline-block"></div> Loading following list…</div>`;
  try{
    const r = await fetch(`/api/my-following?q=${encodeURIComponent(q)}&handle=${encodeURIComponent()}`);
    const data = await r.json();
    _fwCache = data.users||[];
    _fwLoaded = true;
    fwRender(q ? _fwCache.filter(u=>
      u.handle.toLowerCase().includes(q.toLowerCase()) ||
      u.name.toLowerCase().includes(q.toLowerCase())
    ) : _fwCache);
  }catch(e){
    drop.innerHTML=`<div class="fw-picker-empty">Could not load following list</div>`;
  }
}

function fwRender(users){
  const drop = document.getElementById("fw-drop");
  if(!drop) return;
  if(!users.length){
    drop.innerHTML=`<div class="fw-picker-empty">No matches</div>`;
    return;
  }
  drop.innerHTML = users.slice(0,40).map(u=>`
    <div class="fw-picker-item" onclick="fwSelect('${x(u.handle)}')">
      <div class="fw-picker-avatar">${u.handle.slice(0,1).toUpperCase()}</div>
      <div>
        <div class="fw-picker-handle">@${x(u.handle)}</div>
        <div class="fw-picker-name">${x(u.name)}</div>
      </div>
    </div>`).join("");
}

function fwSelect(handle){
  const inp = document.getElementById("cw-in");
  if(inp) inp.value = handle;
  fwClose();
}

// ── CREATOR WATCH ─────────────────────────────────────────────────────────────
let _cwCreators = [];       // [{handle, lastPostId, lastPostUrl, lastPostTime, newPost}]
let _cwPollTimer = null;
let _cwPolling = false;
const CW_POLL_INTERVAL = 90000; // 90 seconds

async function cwAdd(){
  const inp = document.getElementById("cw-in");
  if(!inp) return;
  const handle = inp.value.trim().replace(/^@/,"").toLowerCase();
  if(!handle) return;
  if(_cwCreators.find(c=>c.handle===handle)) { inp.value=""; return; }
  _cwCreators.push({handle, lastPostId:"", lastPostUrl:"", lastPostTime:"", newPost:false});
  inp.value="";
  await cwSave();
  renderNotifFeed();
  cwStartPoll();
  cwCheckOne(handle);   // immediate check; first result sets baseline, no "new post" false alarm
}

async function cwRemove(idx){
  _cwCreators.splice(idx,1);
  await cwSave();
  renderNotifFeed();
  if(!_cwCreators.length) cwStopPoll();
}

async function cwSave(){
  try{
    await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({watched_creators:_cwCreators})});
  }catch(e){}
}

function cwStartPoll(){
  if(_cwPollTimer) return;
  _cwPollTimer = setInterval(cwCheckAll, CW_POLL_INTERVAL);
}
function cwStopPoll(){
  if(_cwPollTimer){ clearInterval(_cwPollTimer); _cwPollTimer=null; }
}

async function cwCheckNow(){
  const st = document.getElementById("cw-poll-st");
  if(st) st.textContent = "Checking...";
  await cwCheckAll();
}

async function cwCheckAll(){
  if(_cwPolling) return;
  _cwPolling = true;
  const st = document.getElementById("cw-poll-st");
  for(const c of _cwCreators){
    if(st) st.textContent = `Checking @${c.handle}...`;
    const _nSt2=document.getElementById('notif-poll-st');if(_nSt2)_nSt2.textContent=`Checking @${c.handle}…`;
    await cwCheckOne(c.handle);
  }
  _cwPolling = false;
  const now = new Date().toLocaleTimeString();
  if(st) st.textContent = `Last checked ${now}`;
}

async function cwCheckOne(handle){
  try{
    const r = await fetch(`/api/creator-latest?handle=${encodeURIComponent(handle)}`);
    if(!r.ok) return;
    const data = await r.json();
    const idx = _cwCreators.findIndex(c=>c.handle===handle);
    if(idx<0) return;
    const c = _cwCreators[idx];
    const freshId = data.latest_id || "";
    const freshUrl = data.latest_url || "";
    const freshTime = data.latest_time || "";
    if(freshId && freshId !== c.lastPostId && c.lastPostId !== ""){
      // New post detected — only notify if we had a previous baseline (not first-ever check)
      c.newPost = true;
      _cwCreators[idx] = {...c, lastPostId:freshId, lastPostUrl:freshUrl, lastPostTime:new Date().toLocaleTimeString()};
      cwNotify(handle, freshUrl);
    } else {
      _cwCreators[idx] = {...c, lastPostId:freshId||c.lastPostId, lastPostUrl:freshUrl||c.lastPostUrl, lastPostTime:freshTime||c.lastPostTime};
    }
    await cwSave();
    // Re-render if the watch panel is open
    renderNotifFeed();
  }catch(e){}
}

function renderNotifFeed(){
  const feed = document.getElementById("notif-feed");
  if(!feed) return;
  const badge = document.getElementById("notif-badge");
  if(!_cwCreators.length){
    feed.innerHTML=`<div class="notif-empty">📭 No creators watched yet.<br>Add a TikTok handle above to get notified when they post.</div>`;
    if(badge) badge.style.display="none";
    return;
  }
  const newCount = _cwCreators.filter(c=>c.newPost).length;
  if(badge){ badge.textContent=newCount; badge.style.display=newCount?"inline":"none"; }
  const sbBadge=document.getElementById("sb-acct-badge");
  if(sbBadge&&newCount){ sbBadge.textContent=newCount; sbBadge.style.display="inline"; sbBadge.style.background="var(--pink)"; }
  feed.innerHTML = _cwCreators.map((c,i)=>{
    const viewBtn = c.lastPostUrl ? `<button class="cw-action-btn" onclick="openUrl('${x(c.lastPostUrl)}')">View post ↗</button>` : "";
    const dlBtn   = c.lastPostUrl ? `<button class="cw-action-btn dl" onclick="cwDownload('${x(c.lastPostUrl)}')">⬇ Download</button>` : "";
    const timeStr = c.lastPostTime || "Not checked yet";
    return `<div class="notif-item${c.newPost?" new-post":""}">
      <div class="notif-avatar">${c.handle.slice(0,1).toUpperCase()}</div>
      <div class="notif-body">
        <div class="notif-handle">@${x(c.handle)}${c.newPost?`<span class="notif-new-badge">NEW POST</span>`:""}</div>
        <div class="notif-time">${timeStr}</div>
      </div>
      <div class="notif-actions">${viewBtn}${dlBtn}</div>
      <button style="background:none;border:none;color:var(--text3);cursor:pointer;padding:4px 8px;border-radius:5px;font-size:.8rem;transition:all .15s" onclick="cwRemove(${i})" onmouseover="this.style.color='var(--red)'" onmouseout="this.style.color='var(--text3)'">✕</button>
    </div>`;
  }).join("");
}
function renderCWatchRight(){ renderNotifFeed(); }

function cwNotify(handle, url){
  // Browser notification
  if(Notification.permission==="granted"){
    const notif = new Notification("EditorSuite — New post!", {
      body: `@${handle} just posted something new.`,
      icon: "/static/favicon.ico",
      tag: "notif-"+handle,
    });
    notif.onclick = ()=>{ window.focus(); if(url) window.open(url,"_blank"); notif.close(); };
  }
  // Also request permission if not granted yet
  if(Notification.permission==="default"){
    Notification.requestPermission().then(perm=>{
      if(perm==="granted") cwNotify(handle,url);
    });
  }
}

function cwDownload(url){
  if(!url||appBusy) return;
  appBusy=true;
  // Show a small inline download toast rather than hijacking the tool panel
  const sink=document.createElement("div"),fakeBar=document.createElement("div"),
        fakeLbl=document.createElement("div"),fakeSt=document.createElement("div");
  doStream("/api/tool",{tool_id:"dl_vid",options:{url,quality:"1080"}},{
    barEl:fakeBar,lblEl:fakeLbl,stEl:fakeSt,resEl:sink,feedId:"",
    onDone:()=>{
      appBusy=false;
      const toast=document.createElement("div");
      toast.textContent = fakeLbl.textContent==="ERROR" ? "✗ Download failed" : "✓ Saved to Downloads";
      toast.style.cssText="position:fixed;bottom:24px;right:24px;background:var(--bg3);border:1px solid var(--border2);color:"+(fakeLbl.textContent==="ERROR"?"var(--red)":"var(--green)")+";font-family:var(--fm);font-size:.76rem;padding:10px 18px;border-radius:9px;z-index:9999;pointer-events:none;transition:opacity .4s";
      document.body.appendChild(toast);
      setTimeout(()=>{toast.style.opacity="0";setTimeout(()=>toast.remove(),400)},2200);
    }
  });
}

// Request notification permission early
if(typeof Notification!=="undefined" && Notification.permission==="default"){
  document.addEventListener("click",function _reqNotif(){
    Notification.requestPermission();
    document.removeEventListener("click",_reqNotif);
  },{once:true});
}


// ── ARTIST SEARCH ──────────────────────────────────────────────────────────
let _artistSrc = "yt";
let _watchedArtists = [];
let _artistPollTimer = null;

function setArtistSrc(btn, src){
  _artistSrc = src;
  document.querySelectorAll("[data-src]").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");
  const inp = document.getElementById("tf_query");
  if(inp && inp.value.trim()) runArtistSearch();
}

async function runArtistSearch(){
  const inp = document.getElementById("tf_query");
  const q = (inp ? inp.value : "").trim();
  const tr = document.getElementById("tr");
  if(!q){if(tr)tr.innerHTML="";return;}
  if(tr) tr.innerHTML=`<div style="padding:48px;text-align:center;font-family:var(--fm);font-size:.76rem;color:var(--text3)">Searching…</div>`;
  try{
    const r = await fetch(`/api/artist-search?q=${encodeURIComponent(q)}&platform=${encodeURIComponent(_artistSrc)}`);
    const data = await r.json();
    if(tr) tr.innerHTML = rArtistResults(data.artists||[], q);
  }catch(e){
    if(tr) tr.innerHTML = errorCard("Search failed: "+e.message);
  }
}

function rArtistResults(artists, query){
  if(!artists.length) return `<div style="padding:48px;text-align:center;font-family:var(--fm);font-size:.8rem;color:var(--text3)">No results for "<strong style="color:var(--text)">${x(query)}</strong>"<br><span style="font-size:.72rem">Try switching to YouTube Music</span></div>`;
  const cards = artists.map(a=>{
    const watching = _watchedArtists.some(w=>w.id===a.id);
    const src = a.platform==="spotify"
      ? `<span style="color:#1ed760;font-family:var(--fm);font-size:.62rem;background:rgba(30,215,96,.1);padding:2px 7px;border-radius:4px;margin-left:6px">Spotify</span>`
      : `<span style="color:#f00;font-family:var(--fm);font-size:.62rem;background:rgba(255,0,0,.08);padding:2px 7px;border-radius:4px;margin-left:6px">YT Music</span>`;
    const meta = [a.genres?a.genres.split(",")[0]:"",a.followers?nK(a.followers)+" followers":""].filter(Boolean).join(" · ");
    return `<div class="artist-card" onclick="openArtistTracks('${x(a.id)}','${x(a.name)}','${x(a.platform)}')">
      ${a.image?`<img class="artist-img" src="${x(a.image)}" onerror="this.style.display='none'">`:`<div class="artist-img-ph">🎤</div>`}
      <div class="artist-info">
        <div class="artist-name">${x(a.name)}${src}</div>
        ${meta?`<div class="artist-meta">${meta}</div>`:""}
      </div>
      <button class="artist-watch-btn${watching?" watching":""}" onclick="event.stopPropagation();toggleWatchArtist(this,'${x(a.id)}','${x(a.name)}','${x(a.platform)}','${x(a.latest_release_id||"")}','${x(a.latest_release_title||"")}')">
        ${watching?"🔔":"+ Watch"}
      </button>
    </div>`;
  }).join("");
  return `<div style="display:flex;flex-direction:column;gap:8px">${cards}</div>`;
}

async function openArtistTracks(id, name, platform){
  const tr = document.getElementById("tr");
  if(tr) tr.innerHTML=`<div style="padding:48px;text-align:center;font-family:var(--fm);font-size:.76rem;color:var(--text3)">Loading ${x(name)}…</div>`;
  try{
    const r = await fetch(`/api/artist-tracks?id=${encodeURIComponent(id)}&platform=${encodeURIComponent(platform)}&name=${encodeURIComponent(name)}`);
    const data = await r.json();
    if(tr) tr.innerHTML = rArtistDetail(data, name, id, platform);
  }catch(e){
    if(tr) tr.innerHTML = errorCard("Could not load: "+e.message);
  }
}

function rArtistDetail(data, name, id, platform){
  const tracks = data.tracks||[];
  const watching = _watchedArtists.some(w=>w.id===id);
  const header = `<div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;padding-bottom:20px;border-bottom:1px solid var(--border)">
    ${data.image?`<img src="${x(data.image)}" style="width:64px;height:64px;border-radius:50%;object-fit:cover;border:2px solid var(--border2);flex-shrink:0">`:`<div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,rgba(56,189,248,.2),rgba(168,85,247,.2));display:flex;align-items:center;justify-content:center;font-size:1.8rem;flex-shrink:0">🎤</div>`}
    <div style="flex:1;min-width:0">
      <div style="font-family:var(--fd);font-size:1.2rem;font-weight:800;margin-bottom:4px">${x(name)}</div>
      ${data.followers?`<div style="font-family:var(--fm);font-size:.7rem;color:var(--text3)">${nK(data.followers)} followers</div>`:""}
    </div>
    <div style="display:flex;gap:8px;flex-shrink:0">
      <button class="artist-watch-btn${watching?" watching":""}" onclick="toggleWatchArtist(this,'${x(id)}','${x(name)}','${x(platform)}','${x((tracks[0]||{}).id||"")}','${x((tracks[0]||{}).title||"")}')">
        ${watching?"🔔 Watching":"+ Watch"}
      </button>
      <button class="cw-action-btn" onclick="runArtistSearch()" style="opacity:1">← Back</button>
    </div>
  </div>`;
  const rows = tracks.map((t,i)=>{
    const dur = t.duration_ms?`${Math.floor(t.duration_ms/60000)}:${String(Math.floor((t.duration_ms%60000)/1000)).padStart(2,"0")}`:(t.duration||"");
    return `<div class="track-row"><div class="track-num">${i+1}</div>
      ${t.image?`<img class="track-img" src="${x(t.image)}" onerror="this.style.display='none'">`:`<div class="track-img" style="display:flex;align-items:center;justify-content:center;font-size:.9rem">🎵</div>`}
      <div class="track-info"><div class="track-name">${x(t.title||"—")}</div>${t.album?`<div class="track-album">${x(t.album)}</div>`:""}</div>
      ${dur?`<div class="track-dur">${dur}`:""}${dur?"</div>":""}
      <button class="track-dl-btn" onclick="dlTrack(this,'${x((t.title||"").replace(/'/g,"&#39;"))}','${x(name.replace(/'/g,"&#39;"))}')">⬇ Download</button>
    </div>`;
  }).join("");
  return header+`<div style="background:var(--bg2);border:1px solid var(--border2);border-radius:12px;overflow:hidden"><div class="artist-section-hdr">${tracks.length} track${tracks.length!==1?"s":""}</div><div class="track-rows">${rows||`<div style="padding:24px;font-family:var(--fm);font-size:.77rem;color:var(--text3)">No tracks found — try YouTube Music</div>`}</div></div>`;
}

function toggleWatchArtist(btn, id, name, platform, latestId, latestTitle){
  const i = _watchedArtists.findIndex(w=>w.id===id);
  if(i>=0){ _watchedArtists.splice(i,1); btn.textContent="+ Watch"; btn.classList.remove("watching"); }
  else { _watchedArtists.push({id,name,platform,latestReleaseId:latestId,latestReleaseTitle:latestTitle,newRelease:false}); btn.textContent="🔔 Watching"; btn.classList.add("watching"); artistStartPoll(); }
  saveArtistWatched();
}
async function saveArtistWatched(){ try{ await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({watched_artists:_watchedArtists})}); }catch(e){} }
function artistStartPoll(){ if(_artistPollTimer) return; _artistPollTimer=setInterval(artistCheckAll,180000); }
async function artistCheckAll(){
  for(const a of _watchedArtists){
    try{
      const r=await fetch(`/api/artist-latest?id=${encodeURIComponent(a.id)}&platform=${encodeURIComponent(a.platform)}&name=${encodeURIComponent(a.name)}`);
      if(!r.ok) continue;
      const data=await r.json();
      if(data.latest_id && data.latest_id!==a.latestReleaseId && a.latestReleaseId){
        a.newRelease=true; a.latestReleaseId=data.latest_id; a.latestReleaseTitle=data.latest_title||"";
        if(Notification.permission==="granted"){
          const n=new Notification("New Release!",{body:`${a.name} dropped "${data.latest_title||"something new"}"`,icon:"/static/favicon.ico",tag:"artist-"+a.id});
          n.onclick=()=>{window.focus();if(data.latest_url)window.open(data.latest_url,"_blank");n.close();};
        }
      } else if(!a.latestReleaseId){ a.latestReleaseId=data.latest_id||""; }
    }catch(e){}
  }
  await saveArtistWatched();
}
async function dlTrack(btn, title, artist){
  if(btn.classList.contains("busy")||btn.classList.contains("done")) return;
  if(appBusy){btn.textContent="Busy";setTimeout(()=>{if(!btn.classList.contains("done"))btn.textContent="⬇ Download"},1200);return;}
  btn.classList.add("busy"); btn.textContent="↻ Downloading"; appBusy=true;
  const sink=document.createElement("div"),fb=document.createElement("div"),fl=document.createElement("div"),fs=document.createElement("div");
  doStream("/api/tool",{tool_id:"dl_song",options:{title,artist}},{barEl:fb,lblEl:fl,stEl:fs,resEl:sink,feedId:"",
    onDone:()=>{ appBusy=false; btn.classList.remove("busy"); if(fl.textContent==="ERROR"){btn.textContent="⬇ Download";}else{btn.classList.add("done");btn.textContent="✓ Saved";} }
  });
}

// ── STOCK FOOTAGE ─────────────────────────────────────────────────────────────
let _footageMode = "general";

function setFootageMode(btn, mode){
  _footageMode = mode;
  document.querySelectorAll(".footage-mode-btn").forEach(b=>{
    b.style.background="transparent";b.style.color="var(--text3)";b.classList.remove("active");
  });
  btn.style.background="rgba(251,191,36,.15)";btn.style.color="var(--amber)";btn.classList.add("active");
  const gUI=document.getElementById("footage-general-ui");
  const cUI=document.getElementById("footage-cars-ui");
  if(gUI) gUI.style.display=mode==="general"?"block":"none";
  if(cUI) cUI.style.display=mode==="cars"?"block":"none";
  const tr=document.getElementById("tr");if(tr)tr.innerHTML="";
  // Focus the right input
  setTimeout(()=>{
    const inp=document.getElementById(mode==="cars"?"tf_car":"tf_query");
    if(inp)inp.focus();
  },0);
}

async function runFootageSearch(){
  const tr=document.getElementById("tr");
  let q="", mode=(_footageMode||"general");
  if(mode==="cars"){
    const ci=document.getElementById("tf_car");
    q=(ci?ci.value:"").trim();
    if(!q){if(tr)tr.innerHTML="";return;}
  } else {
    const gi=document.getElementById("tf_query");
    q=(gi?gi.value:"").trim();
    if(!q){if(tr)tr.innerHTML="";return;}
  }
  const dest=document.getElementById("cs-results")||tr;
  if(dest)dest.innerHTML='<div class="search-dots-wrap"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';
  try{
    const _cntEl=document.getElementById("cs-result-count"); const _cnt=_cntEl?_cntEl.value:"6";
    const url=`/api/footage-search?q=${encodeURIComponent(q)}&mode=${encodeURIComponent(mode)}&count=${_cnt}`;
    const r=await fetch(url);
    if(!r.ok) throw new Error(`Server error ${r.status}`);
    const data=await r.json();
    if(data.error) throw new Error(data.error);
    if(dest)dest.innerHTML=rFootage(data,q,mode);
  }catch(e){
    if(dest)dest.innerHTML=errorCard("Footage search failed: "+e.message);
  }
}

function rFootage(data,query,mode){
  const results=data.results||[];
  if(!results.length) return`<div style="padding:60px;text-align:center;font-family:var(--fm);font-size:.8rem;color:var(--text3)">No footage found for "<strong style="color:var(--text)">${x(query)}</strong>"<br><span style="font-size:.72rem">Try different keywords</span></div>`;
  const label=mode==="cars"?`"${x(query)}" cinematic footage`:x(query);
  const cards=results.map(v=>{
    const dur=v.duration?`${Math.floor(v.duration/60)}:${String(Math.round(v.duration%60)).padStart(2,"0")}`:"";
    const views=v.views?nK(v.views)+" views":"";
    const info=[dur,views].filter(Boolean).join(" · ");
    const thumb=v.thumbnail||"";
    return`<div class="model-card">
      <div class="model-thumb-wrap" style="aspect-ratio:16/9;position:relative">
        ${thumb?`<img class="model-thumb" src="${x(thumb)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
          <div class="model-thumb-ph" style="display:none">🎬</div>`
          :`<div class="model-thumb-ph">🎬</div>`}
        ${dur?`<span style="position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,.75);color:#fff;font-family:var(--fm);font-size:.65rem;padding:2px 6px;border-radius:4px">${dur}</span>`:""}
      </div>
      <div class="model-info">
        <div class="model-name" style="font-size:.82rem">${x(v.title||"—")}</div>
        <div class="model-author">${x(v.channel||"")}${info?` · ${info}`:""}</div>
        <div style="display:flex;gap:6px;margin-top:8px">
          <button class="cw-action-btn" style="flex:1;opacity:1" onclick="openUrl('${x(v.url||'')}')">View ↗</button>
          <button class="cw-action-btn dl" style="flex:1;opacity:1" onclick="footageDl('${x(v.url||'')}')">⬇ Download</button>
        </div>
      </div>
    </div>`;
  }).join("");
  return`<div class="model-grid-wrap">
    <div class="model-grid-header">
      <span class="model-grid-count">${results.length} results · YouTube · "${label}"</span>
    </div>
    <div class="model-grid" style="grid-template-columns:repeat(auto-fill,minmax(220px,1fr))">${cards}</div>
  </div>`;
}

async function footageDl(url){
  if(!url||appBusy) return;
  appBusy=true;
  const sink=document.createElement("div"),fakeBar=document.createElement("div"),
        fakeLbl=document.createElement("div"),fakeSt=document.createElement("div");
  doStream("/api/tool",{tool_id:"dl_vid",options:{url,quality:"best"}},{
    barEl:fakeBar,lblEl:fakeLbl,stEl:fakeSt,resEl:sink,feedId:"",
    onDone:()=>{
      appBusy=false;
      const toast=document.createElement("div");
      const ok=fakeLbl.textContent!=="ERROR";
      toast.textContent=ok?"✓ Saved to Downloads":"✗ Download failed";
      toast.style.cssText=`position:fixed;bottom:24px;right:24px;background:var(--bg3);border:1px solid var(--border2);color:${ok?"var(--green)":"var(--red)"};font-family:var(--fm);font-size:.76rem;padding:10px 18px;border-radius:9px;z-index:9999;pointer-events:none;transition:opacity .4s`;
      document.body.appendChild(toast);
      setTimeout(()=>{toast.style.opacity="0";setTimeout(()=>toast.remove(),400)},2500);
    }
  });
}

// ── CUSTOM COMP PRESETS ───────────────────────────────────────────────────────
let _customCompPresets=[];
(async function(){try{const cfg=await fetch("/api/config").then(r=>r.json());_customCompPresets=cfg.custom_comp_presets||[]}catch(e){}})();

async function addCompPreset(fieldId){
  const result=await fetch("/api/browse-file",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filters:[{name:"HandBrake Preset JSON",exts:"*.json"},{name:"All Files",exts:"*.*"}]})}).then(r=>r.json()).catch(()=>({path:""}));
  const path=result&&result.path;if(!path)return;
  const rawName=path.replace(/\\/g,"/").split("/").pop().replace(/\.json$/i,"");
  const name=rawName.replace(/[-_]/g," ").replace(/\b\w/g,c=>c.toUpperCase());
  if(_customCompPresets.some(p=>p.path===path))return;
  _customCompPresets.push({name,path});
  await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({custom_comp_presets:_customCompPresets})});
  const on=document.querySelector(".sb-tool.on");if(on){const id=(on.getAttribute("onclick")||"").replace(/goTool\(['"](.+?)['"]\)/,"$1");if(id)goTool(id)}
  setTimeout(()=>{const grid=document.getElementById("pcg_"+fieldId.replace("tf_",""));if(!grid)return;const newCard=[...grid.querySelectorAll(".preset-card:not(.preset-card-add)")].find(c=>c.dataset.presetVal===path);if(newCard)selectPresetCard(newCard)},50);
}
async function removeCompPreset(path,fieldId){
  _customCompPresets=_customCompPresets.filter(p=>p.path!==path);
  await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({custom_comp_presets:_customCompPresets})});
  const on=document.querySelector(".sb-tool.on");if(on){const id=(on.getAttribute("onclick")||"").replace(/goTool\(['"](.+?)['"]\)/,"$1");if(id)goTool(id)}
}

// ── BROWSE HELPERS ────────────────────────────────────────────────────────────
async function browseInput(inputId,mode,filtersJson){
  const btn=event&&event.target;if(btn){btn.disabled=true;btn.textContent="…"}
  try{
    let filters=[];try{filters=JSON.parse(filtersJson||"[]")}catch(e){}
    let result={path:""};
    if(mode==="folder"){result=await fetch("/api/browse-folder",{method:"POST"}).then(r=>r.json())}
    else{result=await fetch("/api/browse-file",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filters})}).then(r=>r.json());if(!result.path&&mode==="file_or_folder")result=await fetch("/api/browse-folder",{method:"POST"}).then(r=>r.json())}
    if(result.path){const el=document.getElementById(inputId);if(el)el.value=result.path}
  }catch(e){}
  if(btn){btn.disabled=false;btn.textContent="Browse…"}
}
function selectPresetCard(card){
  const grid=card.closest(".preset-cards-grid");if(grid)grid.querySelectorAll(".preset-card").forEach(c=>c.classList.remove("selected"));
  card.classList.add("selected");
  const hidden=document.getElementById(card.dataset.presetField);if(hidden)hidden.value=card.dataset.presetVal;
}

// ── OPEN / DOWNLOAD ───────────────────────────────────────────────────────────
async function openF(path){await fetch("/api/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path})})}
async function openFolder(path){await fetch("/api/open-folder",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path})})}
function openUrl(url){if(!url)return;try{window.open(url,"_blank")}catch(e){}}
function dlSoundRow(btn,title,artist){
  if(btn.classList.contains("busy")||btn.classList.contains("done"))return;
  if(appBusy){btn.textContent="Busy";setTimeout(()=>{if(!btn.classList.contains("busy")&&!btn.classList.contains("done"))btn.textContent="⬇ Download"},1200);return}
  btn.classList.add("busy");btn.textContent="↻ Downloading";appBusy=true;
  const sink=document.createElement("div"),fakeBar=document.createElement("div"),fakeLbl=document.createElement("div"),fakeSt=document.createElement("div");
  doStream("/api/tool",{tool_id:"dl_song",options:{title,artist}},{barEl:fakeBar,lblEl:fakeLbl,stEl:fakeSt,resEl:sink,feedId:"",
    onDone:()=>{appBusy=false;btn.classList.remove("busy");if(fakeLbl.textContent==="ERROR"){btn.textContent="⬇ Download"}else{btn.classList.add("done");btn.textContent="✓ Saved"}}});
}

const x=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const n=v=>Number(v).toLocaleString();
const nK=v=>{v=Number(v)||0;return v>=1e6?(v/1e6).toFixed(1)+"M":v>=1e3?(v/1e3).toFixed(1)+"K":String(v)};

// ── KEYBOARD SHORTCUTS ───────────────────────────────────────────────────────
document.addEventListener("keydown",function(e){
  if(e.key==="Escape"){
    closeVidPlayer();
    cancelVidName();
    closeCollDialog();
  }
});

// ── SCENE PACK FINDER ──────────────────────────────────────────────────────
let _sceneCat = "all";

function setSceneCat(btn, cat){
  _sceneCat = cat;
  document.querySelectorAll("[data-sc]").forEach(b=>b.classList.remove("active"));
  if(btn) btn.classList.add("active");
  runSceneSearch();
}

async function runSceneSearch(){
  const inp  = document.getElementById("tf_query");
  const q    = (inp ? inp.value : "").trim();
  const dest = document.getElementById("cs-results") || document.getElementById("tr");
  if(!dest) return;
  _csSetSearched(true);
  dest.innerHTML = '<div class="search-dots-wrap"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';
  try{
    const data = await fetch(`/api/scene-search?q=${encodeURIComponent(q)}&cat=${encodeURIComponent(_sceneCat)}`).then(r=>r.json());
    dest.innerHTML = rScenePacks(data, q);
  }catch(e){
    dest.innerHTML = errorCard("Scene search failed: "+e.message);
  }
}

function rScenePacks(data, query){
  const results = data.results||[];
  if(!results.length) return `<div class="model-empty">No scene packs found for "<strong style="color:#888">${x(query||_sceneCat)}</strong>"<br><span style="font-size:.72rem">Try a different keyword or category</span></div>`;
  const cards = results.map(p=>`
    <div class="scene-card" onclick="window.open('${x(p.url||"")}','_blank')">
      ${p.thumb
        ? `<div class="scene-card-thumb"><img src="${x(p.thumb)}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\"scene-card-ph\">🎬</div>'"></div>`
        : `<div class="scene-card-thumb scene-card-ph">🎬</div>`}
      <div class="scene-card-info">
        <div class="scene-card-name">${x(p.name||"Scene Pack")}</div>
        ${p.tags&&p.tags.length ? `<div class="scene-card-tags">${p.tags.slice(0,3).map(t=>`<span class="ha-pill" style="font-size:.62rem;padding:3px 8px">${x(t)}</span>`).join("")}</div>` : ""}
        <div style="display:flex;gap:6px;margin-top:8px">
          <button class="cw-action-btn" style="flex:1" onclick="event.stopPropagation();window.open('${x(p.download||p.url||"")}','_blank')">⬇ Download</button>
        </div>
      </div>
    </div>`).join("");
  const src = (data.results||[]).some(r=>r.source==="YouTube") ? "Results via YouTube Search" : "vlscenepacks.com";
  return `<div class="scene-grid">${cards}</div><div class="model-src">${src}</div>`;
}

// ── TIKTOK INTEGRATION ──────────────────────────────────────────────────────
function openTikTokLogin(){
  const b=document.getElementById("tt-login-banner");
  if(b) b.style.display=b.style.display==="none"||b.style.display===""?"block":"none";
}

async function connectTikTok(){
  const inp     = document.getElementById("tt-cookie-in");
  const session = (inp?inp.value:"").trim();
  if(!session){ showToast("Paste your TikTok sessionid cookie first","var(--red)"); return; }
  await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({tt_session:session})}).catch(()=>{});
  showToast("Connecting to TikTok…");
  document.getElementById("tt-login-banner").style.display="none";
  await syncTikTokCollections(session);
}

async function syncTikTokCollections(session){
  showToast("Syncing TikTok favorites & reposts…");
  try{
    const data = await fetch("/api/tiktok-sync",{method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({session})}).then(r=>r.json());
    if(data.error){ showToast("TikTok sync failed: "+data.error,"var(--red)"); return; }
    function _upsertColl(name,emoji,rarity,vids){
      let c=_collections.find(c=>c.name===name);
      if(!c){ c={id:"tt-"+name.replace(/\s/g,"-")+"-"+Date.now(),name,rarity,emoji,thumb:"",videos:[],creators:[]}; _collections.push(c); }
      let added=0;
      (vids||[]).forEach(v=>{
        if(!c.videos.find(ev=>ev.url===v.url)){
          c.videos.push({url:v.url,desc:v.desc||"",thumb:v.thumb||"",localPath:"",added:new Date().toLocaleDateString(),creator:v.creator||""});
          added++;
        }
      });
      return added;
    }
    const fa=_upsertColl("TikTok Favorites","❤️","epic",data.favorites);
    const ra=_upsertColl("TikTok Reposts","🔁","rare",data.reposts);
    await saveColl();
    renderCollections();
    showToast("✓ Synced: "+fa+" favorites, "+ra+" reposts added");
  }catch(e){ showToast("TikTok sync error: "+e.message,"var(--red)"); }
}

// ── COMMUNITY COLLECTIONS ───────────────────────────────────────────────────
let _commTab = "presets";
const _COMM_META = {
  presets:    {label:"Presets",    icon:"🎛"},
  songs:      {label:"Songs",      icon:"🎵"},
  characters: {label:"Characters", icon:"🎭"},
  shows:      {label:"Shows",      icon:"📺"},
};

function setCommTab(btn,tab){
  _commTab=tab;
  document.querySelectorAll(".comm-tab").forEach(b=>b.classList.remove("on"));
  if(btn) btn.classList.add("on");
  renderCommTab(tab);
}

async function renderCommTab(tab){
  const body=document.getElementById("comm-body");
  if(!body) return;
  body.innerHTML='<div class="search-dots-wrap" style="padding:60px 0"><span class="search-dot"></span><span class="search-dot"></span><span class="search-dot"></span></div>';
  try{
    const data=await fetch(`/api/community?tab=${encodeURIComponent(tab)}`).then(r=>r.json());
    const items=data.items||[];
    const meta=_COMM_META[tab]||{icon:"📦",label:tab};
    if(!items.length){
      body.innerHTML=`<div class="comm-empty"><div class="comm-empty-icon">${meta.icon}</div><div class="comm-empty-title">No ${meta.label} yet</div><div class="comm-empty-sub">Be the first to contribute!</div></div>`;
      return;
    }
    body.innerHTML=`<div class="comm-grid">${items.map(renderCommItem).join("")}</div>`;
  }catch(e){
    body.innerHTML=`<div class="comm-empty"><div class="comm-empty-icon">⚠</div><div class="comm-empty-title">Could not load</div><div class="comm-empty-sub">${x(e.message)}</div></div>`;
  }
}

function renderCommItem(item){
  const tClr={presets:"var(--cyan)",songs:"var(--green)",characters:"var(--amber)",shows:"var(--purple)"}[item.type||_commTab]||"#666";
  return `<div class="comm-card">
    ${item.thumb
      ? `<div class="comm-card-thumb"><img src="${x(item.thumb)}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\"comm-card-ph\">📦</div>'"></div>`
      : `<div class="comm-card-thumb comm-card-ph">📦</div>`}
    <div class="comm-card-info">
      <div class="comm-card-top">
        <span class="comm-card-type" style="color:${tClr}">${x((item.type||_commTab).toUpperCase())}</span>
        ${item.verified?`<span class="comm-card-badge">✓</span>`:""}
      </div>
      <div class="comm-card-name">${x(item.name||"Untitled")}</div>
      ${item.author?`<div class="comm-card-author">by ${x(item.author)}</div>`:""}
      ${item.desc?`<div class="comm-card-desc">${x(item.desc)}</div>`:""}
      <div style="display:flex;gap:6px;margin-top:10px">
        ${item.url?`<button class="cw-action-btn" style="flex:1" onclick="window.open('${x(item.url)}','_blank')">View ↗</button>`:""}
        ${item.download?`<button class="cw-action-btn dl" style="flex:1" onclick="window.open('${x(item.download)}','_blank')">⬇ Get</button>`:""}
      </div>
    </div>
  </div>`;
}

async function submitCommEntry(){
  const inp=document.getElementById("comm-upload-in");
  const val=(inp?inp.value:"").trim();
  if(!val){ showToast("Enter a link or title first","var(--red)"); return; }
  const token=localStorage.getItem("es_token");
  if(!token){ showToast("Sign in first to contribute","var(--red)"); return; }
  try{
    const d=await fetch("/api/community",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({tab:_commTab,value:val,token})}).then(r=>r.json());
    if(d.ok){ showToast("✓ Submitted — thank you!"); if(inp)inp.value=""; renderCommTab(_commTab); }
    else showToast(d.error||"Submit failed","var(--red)");
  }catch(e){ showToast(e.message,"var(--red)"); }
}


// ── HEARTBEAT ─────────────────────────────────────────────────────────────────
(function(){
  setInterval(()=>fetch("/api/ping",{method:"POST",keepalive:true}).catch(()=>{}),5000);
  window.addEventListener("beforeunload",()=>navigator.sendBeacon("/api/shutdown"));
})();

// ── MOUSE GLOW ────────────────────────────────────────────────────────────────
(function(){
  function attachGlow(el){el.addEventListener("mousemove",e=>{const r=el.getBoundingClientRect();el.style.setProperty("--mx",(e.clientX-r.left)+"px");el.style.setProperty("--my",(e.clientY-r.top)+"px")})}
  const pc=document.querySelector(".paste-card");if(pc)attachGlow(pc);
  document.querySelectorAll(".tool-card").forEach(attachGlow);
})();

// ── FIRST RUN ─────────────────────────────────────────────────────────────────
function _loadConfig(cfg){
  _customCategories=cfg.custom_categories||[];
  _customCompPresets=cfg.custom_comp_presets||[];
  _customPresets=cfg.custom_presets||[];
  _cwCreators=cfg.watched_creators||[];
  _watchedArtists=cfg.watched_artists||[];
  _collections=cfg.collections||[];
  loadFavs(cfg);
  if(_watchedArtists.length) artistStartPoll();
  if(_customPresets.length) injectCustomPresets(_customPresets);
  initCategories();
  cwStartPoll();
  if(_cwCreators.length) setTimeout(cwCheckAll,2000);
  // Update collections badge
  const cb=document.getElementById("sb-coll-badge");
  if(cb){cb.textContent=_collections.length;cb.style.display=_collections.length?"inline":"none";}
}

// ── LOGIN / SETUP ─────────────────────────────────────────────────────────────
let _setupTab = "up";

function setSetupTab(tab){
  _setupTab = tab;
  document.getElementById("stab-in").classList.toggle("on", tab==="in");
  document.getElementById("stab-up").classList.toggle("on", tab==="up");
  document.getElementById("setup-btn").textContent = tab==="in" ? "Sign in →" : "Create account →";
}

async function setupSubmit(){
  const email = document.getElementById("setup-email").value.trim();
  const pass  = document.getElementById("setup-pass").value;
  const btn   = document.getElementById("setup-btn");
  if(!email || !pass){ showSetupError("Enter your email and password."); return; }
  if(pass.length < 6){ showSetupError("Password must be at least 6 characters."); return; }
  btn.disabled = true;
  btn.textContent = "Please wait…";
  document.getElementById("setup-error-msg").classList.remove("show");

  const endpoint = _setupTab === "in" ? "/api/auth/login" : "/api/auth/register";
  let data, ok;
  try{
    const r = await fetch(endpoint, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({email, password: pass})
    });
    data = await r.json();
    ok   = r.ok;
  }catch(e){
    // fetch itself failed = server not reachable
    showSetupError("Could not reach EditorSuite server. Make sure the app is running.");
    btn.disabled = false;
    btn.textContent = _setupTab === "in" ? "Sign in →" : "Create account →";
    return;
  }

  // ── Registration: Supabase may require email confirmation ─────────────────
  if(_setupTab === "register" || _setupTab === "up"){
    // Supabase returns 200 with user but NO session if confirmation is required
    if(ok && data.user && !data.access_token && !data.token){
      // Email confirmation required — tell user and let them sign in after confirming
      showSetupError("✉ Check your email and click the confirmation link, then come back and Sign in.");
      document.getElementById("setup-error-msg").style.color = "var(--cyan)";
      btn.disabled = false;
      btn.textContent = "Create account →";
      // Switch to sign-in tab so they can log in after confirming
      setTimeout(()=> setSetupTab("in"), 2000);
      return;
    }
    // If Supabase has email confirmation disabled, we get a session immediately
    if(ok && (data.access_token || data.token)){
      // fall through to login success below
    } else if(!ok){
      let msg = data.message || data.error || data.msg || JSON.stringify(data);
      if(msg.includes("already registered") || msg.includes("already exists"))
        msg = "That email already has an account — sign in instead.";
      else if(msg.includes("weak") || msg.includes("password"))
        msg = "Password too weak — use at least 8 characters with numbers.";
      else if(msg.includes("valid email") || msg.includes("invalid"))
        msg = "Enter a valid email address.";
      showSetupError(msg);
      btn.disabled = false;
      btn.textContent = "Create account →";
      return;
    }
  }

  // ── Login / session success ───────────────────────────────────────────────
  if(!ok){
    let msg = data.message || data.error || data.msg || "Login failed";
    if(msg.includes("Invalid login") || msg.includes("credentials"))
      msg = "Wrong email or password.";
    else if(msg.includes("Email not confirmed"))
      msg = "Confirm your email first — check your inbox.";
    else if(msg.includes("No auth server") || msg.includes("503"))
      msg = "Supabase not configured — run setup_server.py, or skip for now.";
    showSetupError(msg);
    btn.disabled = false;
    btn.textContent = _setupTab === "in" ? "Sign in →" : "Create account →";
    return;
  }

  const token   = data.token || data.access_token  || "";
  const refresh = data.refresh || data.refresh_token || "";
  if(token){
    localStorage.setItem("es_token",   token);
    localStorage.setItem("es_refresh", refresh);
    localStorage.setItem("es_email",   email);
  }

  try{
    await fetch("/api/config", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({setup_complete:true, user_email:email})});
    if(token){ await syncFromCloud(token); await fetchAndApplyRole(token); }
  }catch(e){}

  document.getElementById("setup-overlay").classList.add("hidden");
  renderAcctPanel();
  showToast("✓ Signed in as " + email);
}

async function syncFromCloud(token){
  /** Pull collections + settings from cloud and merge into local config. */
  try{
    const keys = ["collections","watched_creators","watched_artists","settings"];
    for(const key of keys){
      const r = await fetch("/api/userdata/get", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({token, key})
      });
      const data = await r.json();
      if(data.value !== undefined && data.value !== null){
        await fetch("/api/config", {method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({[key]: data.value})});
      }
    }
  }catch(e){ console.warn("Cloud sync failed:", e.message); }
}

async function syncToCloud(){
  /** Push current local data up to the cloud. Called on config save. */
  const token = localStorage.getItem("es_token");
  if(!token) return;
  try{
    const cfg = await fetch("/api/config").then(r=>r.json()).catch(()=>({}));
    const pushKeys = ["collections","watched_creators","watched_artists"];
    for(const key of pushKeys){
      if(cfg[key] !== undefined){
        await fetch("/api/userdata/set", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({token, key, value:cfg[key]})
        });
      }
    }
  }catch(e){ console.warn("Cloud push failed:", e.message); }
}

// ── CREATOR / ADMIN ROLE ─────────────────────────────────────────────────────
let _userRole = "user";

async function fetchAndApplyRole(token){
  try{
    const r = await fetch("/api/auth/role",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({token})
    });
    const data = await r.json();
    const role = data.role || "user";
    localStorage.setItem("es_role", role);
    applyRole(role);
  }catch(e){}
}

function applyRole(role){
  _userRole = role;
  const badge = document.getElementById("sb-creator-badge");
  if(role === "admin"){
    if(badge) badge.style.display = "block";
    renderAdminPanel();
  } else {
    if(badge) badge.style.display = "none";
  }
}

function renderAdminPanel(){
  // Inject an admin panel into settings if admin
  const wrap = document.querySelector(".settings-wrap");
  if(!wrap || document.getElementById("admin-panel-block")) return;
  const block = document.createElement("div");
  block.id = "admin-panel-block";
  block.innerHTML = `
    <div class="admin-panel">
      <div class="admin-panel-title">⚡ Creator Access</div>
      <div class="admin-stat">
        <span>Role</span>
        <span class="admin-stat-val">Administrator</span>
      </div>
      <div class="admin-stat">
        <span>Account</span>
        <span class="admin-stat-val">${x(localStorage.getItem("es_email")||"")}</span>
      </div>
      <div class="admin-stat">
        <span>Cloud sync</span>
        <span class="admin-stat-val" style="color:var(--green)">Active</span>
      </div>
      <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="adminSyncAll()" style="background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);border-radius:7px;color:var(--amber);font-family:var(--fm);font-size:.72rem;padding:6px 14px;cursor:pointer;transition:all .2s" onmouseover="this.style.background='rgba(251,191,36,.2)'" onmouseout="this.style.background='rgba(251,191,36,.1)'">↑ Push all data</button>
        <button onclick="adminPullAll()" style="background:rgba(168,85,247,.1);border:1px solid rgba(168,85,247,.3);border-radius:7px;color:var(--purple);font-family:var(--fm);font-size:.72rem;padding:6px 14px;cursor:pointer;transition:all .2s" onmouseover="this.style.background='rgba(168,85,247,.2)'" onmouseout="this.style.background='rgba(168,85,247,.1)'">↓ Pull from cloud</button>
        <button onclick="adminSignOut()" style="background:none;border:1px solid var(--border2);border-radius:7px;color:var(--text3);font-family:var(--fm);font-size:.72rem;padding:6px 14px;cursor:pointer;transition:all .2s" onmouseover="this.style.borderColor='var(--red)';this.style.color='var(--red)'" onmouseout="this.style.borderColor='var(--border2)';this.style.color='var(--text3)'">Sign out</button>
      </div>
    </div>`;
  wrap.insertBefore(block, wrap.firstChild);
}

async function adminSyncAll(){
  const token = localStorage.getItem("es_token");
  if(!token){ showToast("Not signed in","var(--red)"); return; }
  await syncToCloud();
  showToast("✓ All data pushed to cloud");
}

async function adminPullAll(){
  const token = localStorage.getItem("es_token");
  if(!token){ showToast("Not signed in","var(--red)"); return; }
  await syncFromCloud(token);
  showToast("✓ Data pulled from cloud — reload to see changes");
}

function adminSignOut(){
  localStorage.removeItem("es_token");
  localStorage.removeItem("es_refresh");
  localStorage.removeItem("es_email");
  localStorage.removeItem("es_role");
  _userRole = "user";
  applyRole("user");
  showToast("Signed out");
  // Show login next time on startup (but don't interrupt current session)
  fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({setup_complete:false})}).catch(()=>{});
}

function showToast(msg, color){
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = `position:fixed;bottom:24px;right:24px;background:var(--bg3);
    border:1px solid var(--border2);color:${color||"var(--green)"};
    font-family:var(--fm);font-size:.78rem;padding:12px 20px;border-radius:10px;
    z-index:9999;pointer-events:none;animation:fadeup .3s ease`;
  document.body.appendChild(t);
  setTimeout(()=>{t.style.opacity="0";t.style.transition="opacity .4s";
    setTimeout(()=>t.remove(), 400)}, 3000);
}

async function setupGoogleLogin(){
  try{
    const cfg = await fetch("/api/config").then(r=>r.json());
    const url = (cfg.auth_url||"").replace(/\/+$/,"");
    if(!url){
      showSetupError("Supabase not configured. Run setup_server.py first, or skip for now.");
      return;
    }
    const redirect = encodeURIComponent(`http://127.0.0.1:7331/auth/callback`);
    const oauthUrl = `${url}/auth/v1/authorize?provider=google&redirect_to=${redirect}`;
    // Open in a popup so the main window stays open
    const popup = window.open(oauthUrl, "es_oauth",
      "width=520,height=640,left=200,top=100,toolbar=no,menubar=no");
    if(!popup){
      // Popup blocked — fall back to redirect
      window.location.href = oauthUrl;
    }
  }catch(e){
    showSetupError("Could not start Google sign-in: " + e.message);
  }
}

// Listen for OAuth token from the callback popup
window.addEventListener("message", async function(ev){
  if(!ev.data || ev.data.type !== "oauth_token") return;
  const {token, refresh} = ev.data;
  if(!token) return;
  localStorage.setItem("es_token",   token);
  localStorage.setItem("es_refresh", refresh||"");
  try{
    // Get email from token payload
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g,"+").replace(/_/g,"/")));
    const email = payload.email || payload.sub || "";
    localStorage.setItem("es_email", email);
    await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({setup_complete:true,user_email:email})});
    await syncFromCloud(token);
    await fetchAndApplyRole(token);
    document.getElementById("setup-overlay").classList.add("hidden");
    showToast("✓ Signed in with Google" + (email ? " as "+email : ""));
  }catch(e){
    showSetupError("Google sign-in error: " + e.message);
  }
});

function showSetupError(msg){
  const el=document.getElementById("setup-error-msg");
  if(el){el.textContent=msg;el.classList.add("show");}
}

function setupSkip(){
  // Session-only skip — doesn't write to config so login shows again next run
  // unless user has actually logged in
  sessionStorage.setItem("es_skipped","1");
  document.getElementById("setup-overlay").classList.add("hidden");
}

// ── SETTINGS ──────────────────────────────────────────────────────────────────
async function loadSettings(){
  try{
    const cfg=await fetch("/api/config").then(r=>r.json());
    const el=document.getElementById("cfg_root_dir");
    if(el) el.value=cfg.root_dir||"";
    const disp=document.getElementById("cfg_root_dir_display");
    if(disp&&cfg.root_dir) disp.textContent="Currently: "+cfg.root_dir;
  }catch(e){console.error("loadSettings",e)}
}

async function saveSettings(){
  const btn=document.querySelector(".settings-save-btn");
  if(btn) btn.disabled=true;
  const el=document.getElementById("cfg_root_dir");
  const val=el?el.value.trim():"";
  try{
    await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({root_dir:val})});
    const toast=document.getElementById("stst");
    if(toast){toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),2000);}
    const disp=document.getElementById("cfg_root_dir_display");
    if(disp&&val) disp.textContent="Currently: "+val;
    syncToCloud().catch(()=>{});   // push to cloud if logged in
  }catch(e){alert("Save failed: "+e.message);}
  if(btn) btn.disabled=false;
}

async function browseOutputFolder(){
  try{
    const r=await fetch("/api/browse-folder",{method:"POST"});
    const data=await r.json();
    if(data.path){
      const el=document.getElementById("cfg_root_dir");
      if(el){el.value=data.path;el.focus();}
      const disp=document.getElementById("cfg_root_dir_display");
      if(disp) disp.textContent="Currently: "+data.path;
    }
  }catch(e){}
}

// ── COLLECTIONS ───────────────────────────────────────────────────────────────
let _collections = [];   // [{id, name, rarity, emoji, videos:[], creators:[]}]
let _activeCollId = null;
let _vidViewMode = "grid";
let _collTab = "all";
let _collRarity = "normal";

function showToolHistory(){
  const cache = _toolOutputCache[activeToolId];
  if(!cache) return;
  const tr = document.getElementById("tr");
  if(tr) tr.innerHTML = cache;
}
function updateHistoryBtn(){
  const btn = document.getElementById("t-hist-btn");
  if(!btn) return;
  btn.style.display=(activeToolId&&_toolOutputCache[activeToolId])?"inline-flex":"none";
}
function goAccount(){
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("pac").classList.add("on");
  renderAcctPanel();
}

function renderAcctPanel(){
  const token = localStorage.getItem("es_token");
  const email = localStorage.getItem("es_email") || "";
  const si    = document.getElementById("pac-signed-in");
  const so    = document.getElementById("pac-signed-out");
  const av    = document.getElementById("pac-avatar");
  const em    = document.getElementById("pac-email");
  const dot   = document.getElementById("sb-acct-dot");

  if(token){
    if(si) si.style.display="block";
    if(so) so.style.display="none";
    if(av) av.textContent=(email||"?").slice(0,1).toUpperCase();
    if(em) em.textContent=email||"Signed in";
    if(dot) dot.style.display="inline-block";
    // Fill stats
    const totalVids     = _collections.reduce((a,c)=>a+c.videos.length,0);
    const totalCreators = _collections.reduce((a,c)=>a+c.creators.length,0);
    const sv = document.getElementById("pac-stat-colls");
    const vv = document.getElementById("pac-stat-vids");
    const cv = document.getElementById("pac-stat-creators");
    if(sv) sv.textContent=_collections.length;
    if(vv) vv.textContent=totalVids;
    if(cv) cv.textContent=totalCreators;
    // Fill starred tools
    const fl = document.getElementById("pac-favs-list");
    if(fl){
      if(_favTools.length){
        fl.innerHTML=_favTools.map(tid=>{
          const t=T[tid];
          return t?`<span style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:5px 10px;font-family:var(--fm);font-size:.72rem;color:#888">${t.name}</span>`:"";
        }).join("");
      } else {
        fl.innerHTML='<span style="font-family:var(--fm);font-size:.75rem;color:#444">No starred tools yet — click ☆ next to any tool</span>';
      }
    }
  } else {
    if(si) si.style.display="none";
    if(so) so.style.display="block";
    if(dot) dot.style.display="none";
  }
}

function pacShowLogin(){
  const ov=document.getElementById("setup-overlay");
  if(ov) ov.classList.remove("hidden");
  goHome();
}

function pacSignOut(){
  if(!confirm("Sign out of EditorSuite?")) return;
  localStorage.removeItem("es_token");
  localStorage.removeItem("es_refresh");
  localStorage.removeItem("es_email");
  localStorage.removeItem("es_role");
  fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({setup_complete:false})}).catch(()=>{});
  renderAcctPanel();
  showToast("Signed out");
}

// ── FAVOURITES ────────────────────────────────────────────────────────────────
let _favTools = [];   // array of tool IDs

function toggleFav(id){
  const idx = _favTools.indexOf(id);
  if(idx >= 0) _favTools.splice(idx, 1);
  else _favTools.push(id);
  saveFavs();
  renderFavs();
}

function saveFavs(){
  localStorage.setItem("es_favtools", JSON.stringify(_favTools));
  fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({fav_tools:_favTools})}).catch(()=>{});
}

function loadFavs(cfg){
  // Prefer config (syncs across machines), fall back to localStorage
  const fromCfg = cfg && cfg.fav_tools;
  const fromLS  = JSON.parse(localStorage.getItem("es_favtools")||"[]");
  _favTools = (fromCfg && fromCfg.length) ? fromCfg : fromLS;
  renderFavs();
}

function renderFavs(){
  const section = document.getElementById("sb-favs-section");
  const list    = document.getElementById("sb-favs-list");
  const sep     = document.getElementById("sb-favs-sep");
  if(!section || !list) return;

  // Update star states on all rows
  document.querySelectorAll(".sb-fav-star").forEach(star=>{
    const tid = star.id.replace("fav-star-","");
    if(_favTools.includes(tid)){
      star.textContent = "★";
      star.classList.add("on");
    } else {
      star.textContent = "☆";
      star.classList.remove("on");
    }
  });

  if(!_favTools.length){
    section.className = "fav-cat empty";
    if(sep) sep.style.display="none";
    return;
  }

  section.className = "fav-cat has-favs";
  if(sep) sep.style.display="";

  list.innerHTML = _favTools.map(tid=>{
    const t = T[tid];
    if(!t) return "";
    const icon = ICONS[tid] || "⚙️";
    const name = t.name || tid;
    return `<div class="sb-tool fav-item" id="sb-fav-${tid}" onclick="goTool('${tid}')">
      <div class="sb-tool-icon">${icon}</div>
      <div class="sb-tool-name">${name}</div>
      <span class="sb-fav-star on" onclick="event.stopPropagation();toggleFav('${tid}')" title="Remove from favourites">★</span>
    </div>`;
  }).join("");
}

function goCollections(){
  _setTopbarActive("tb-coll");
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("pcoll").classList.add("on");
  // Restore detail view if a collection was open before switching panels
  if(_activeCollId) renderCollectionDetail(_activeCollId);
  else renderCollections();
}

function goCommunity(){
  _setTopbarActive("tb-community");
  const _rstTpl=document.querySelector(".tpi-left"); if(_rstTpl) _rstTpl.style.display="";
  const _rstPt=document.getElementById("pt2"); if(_rstPt) _rstPt.style.flexDirection="";
  const _rstTr=document.getElementById("tr"); if(_rstTr){ _rstTr.style.overflow=""; _rstTr.style.padding=""; _rstTr.style.display=""; _rstTr.style.flexDirection=""; }
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("on"));
  document.getElementById("pcomm").classList.add("on");
  renderCommTab("presets");
}

function openCollDialog(){
  document.getElementById("coll-dialog").style.display="flex";
  document.getElementById("coll-name-in").value="";
  document.getElementById("coll-name-in").focus();
  pickRarity(document.querySelector(".rarity-opt[data-r='normal']"),"normal");
  // Reset thumb picker
  const tf=document.getElementById("coll-thumb-file");
  const pr=document.getElementById("coll-thumb-preview");
  const ph=document.getElementById("coll-thumb-placeholder");
  const er=document.getElementById("coll-thumb-err");
  if(tf) tf.value="";
  if(pr){ pr.src=""; pr.style.display="none"; }
  if(ph) ph.style.display="flex";
  if(er) er.style.display="none";
}
function pickCollThumb(){
  const f=document.getElementById("coll-thumb-file"); if(f) f.click();
}
function previewCollThumb(inp){
  if(!inp.files||!inp.files[0]) return;
  const pr=document.getElementById("coll-thumb-preview");
  const ph=document.getElementById("coll-thumb-placeholder");
  const er=document.getElementById("coll-thumb-err");
  const url=URL.createObjectURL(inp.files[0]);
  if(pr){ pr.src=url; pr.style.display="block"; }
  if(ph) ph.style.display="none";
  if(er) er.style.display="none";
}

function closeCollDialog(){
  document.getElementById("coll-dialog").style.display="none";
}

function pickRarity(el, r){
  _collRarity=r;
  document.querySelectorAll(".rarity-opt").forEach(o=>{
    o.classList.remove("sel","sel-legendary","sel-epic","sel-rare");
  });
  el.classList.add("sel","sel-"+r);
  const custom=document.getElementById("coll-custom-emoji");
  if(custom) custom.style.display=r==="custom"?"block":"none";
}

async function createCollection(){
  const name=document.getElementById("coll-name-in").value.trim();
  if(!name) return;
  // Require a thumbnail
  const thumbFile=document.getElementById("coll-thumb-file");
  const errEl=document.getElementById("coll-thumb-err");
  if(!thumbFile||!thumbFile.files||!thumbFile.files[0]){
    if(errEl) errEl.style.display="block";
    return;
  }
  if(errEl) errEl.style.display="none";
  // Read thumb as data URL
  const thumbDataUrl = await new Promise(res=>{
    const fr=new FileReader(); fr.onload=e=>res(e.target.result); fr.readAsDataURL(thumbFile.files[0]);
  });
  let emoji="📂";
  if(_collRarity==="legendary") emoji="🌟";
  else if(_collRarity==="epic")  emoji="⚡";
  else if(_collRarity==="rare")  emoji="🔷";
  const coll={id:Date.now().toString(),name,rarity:_collRarity,emoji,
    thumb:thumbDataUrl,videos:[],creators:[]};
  _collections.push(coll);
  await saveColl();
  closeCollDialog();
  renderCollections();
}

async function saveColl(){
  try{
    await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({collections:_collections})});
    syncToCloud().catch(()=>{});
  }catch(e){}
  const cb=document.getElementById("sb-coll-badge");
  if(cb){cb.textContent=_collections.length;cb.style.display=_collections.length?"inline":"none";}
}

async function deleteCollection(id,e){
  e.stopPropagation();
  if(!confirm("Delete this collection?")) return;
  _collections=_collections.filter(c=>c.id!==id);
  await saveColl();
  if(_activeCollId===id){_activeCollId=null;}
  renderCollections();
}

function setCollTab(btn, tab){
  _collTab=tab;
  document.querySelectorAll(".coll-tab").forEach(b=>b.classList.remove("on"));
  btn.classList.add("on");
  if(_activeCollId) renderCollectionDetail(_activeCollId);
  else renderCollections();
}

const _folderSVG = `<svg viewBox="0 0 48 40" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" style="width:52px;height:44px;color:#2a2a2a"><path d="M4 8h16l4 4h20a2 2 0 0 1 2 2v22a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2z"/></svg>`;

function renderCollections(){
  const body=document.getElementById("coll-body");
  if(!body) return;
  document.getElementById("coll-panel-title").textContent="Collections";
  document.getElementById("coll-panel-sub").textContent="Your TikTok video collections";
  document.getElementById("coll-new-btn").style.display="";

  if(!_collections.length){
    body.innerHTML=`<div style="padding:60px;text-align:center;font-family:var(--fm);font-size:.8rem;color:var(--text3)">
      No collections yet.<br><br>
      <span style="font-size:.72rem">Click <strong style="color:var(--text)">+ New Collection</strong> to create your first one.</span>
    </div>`;
    return;
  }

  const cards = _collections.map(c=>{
    const count = c.videos.length + c.creators.length;
    // Prefer the user-set thumbnail, then first video thumb, then folder icon
    const thumbSrc = c.thumb || (c.videos[0]?.thumb
      ? `/api/serve-thumb?path=${encodeURIComponent(c.videos[0].thumb)}`
      : "");
    const thumb = thumbSrc
      ? `<img src="${x(thumbSrc)}" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`+
        `<span class="coll-thumb-folder" style="display:none">${_folderSVG}</span>`
      : `<span class="coll-thumb-folder">${_folderSVG}</span>`;
    return `<div class="coll-card rarity-${x(c.rarity)}" onclick="openCollection('${x(c.id)}')">
      <div class="coll-card-thumb">${thumb}</div>
      <div class="coll-card-info">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <div class="coll-card-name">${x(c.name)}</div>
          ${c.rarity==="epic"?`<span style="font-family:var(--fm);font-size:.65rem;padding:2px 8px;border-radius:4px;background:rgba(168,85,247,.15);color:var(--purple)">⚡ Epic</span>`:""}${c.rarity==="rare"?`<span style="font-family:var(--fm);font-size:.65rem;padding:2px 8px;border-radius:4px;background:rgba(56,189,248,.15);color:var(--blue)">🔷 Rare</span>`:""}
        </div>
        <div class="coll-card-meta">${count} item${count!==1?"s":""}</div>
      </div>
      <button onclick="deleteCollection('${x(c.id)}',event)" style="position:absolute;top:8px;right:8px;
        background:rgba(0,0,0,.5);border:none;border-radius:50%;width:24px;height:24px;
        color:var(--text3);font-size:.75rem;cursor:pointer;display:none;align-items:center;justify-content:center"
        class="coll-del-btn">✕</button>
    </div>`;
  }).join("");
  body.innerHTML=`<div class="coll-grid">${cards}</div>`;
  // Show delete buttons on hover
  body.querySelectorAll(".coll-card").forEach(c=>{
    const del=c.querySelector(".coll-del-btn");
    c.addEventListener("mouseenter",()=>{if(del)del.style.display="flex";});
    c.addEventListener("mouseleave",()=>{if(del)del.style.display="none";});
  });
}

function openCollection(id){
  _activeCollId=id;
  renderCollectionDetail(id);
}

function renderCollectionDetail(id){
  const coll=_collections.find(c=>c.id===id);
  if(!coll) return;
  const body=document.getElementById("coll-body");
  document.getElementById("coll-panel-title").textContent=`${coll.emoji} ${coll.name}`;
  const totalVids = coll.videos.length;
  const totalC    = coll.creators.length;
  document.getElementById("coll-panel-sub").textContent=
    `${totalVids} video${totalVids!==1?"s":""}${totalC?" · "+totalC+" creator"+(totalC!==1?"s":""):""}`;
  document.getElementById("coll-new-btn").style.display="none";

  // Unowned videos = videos not belonging to any tracked creator
  const trackedHandles = new Set(coll.creators.map(c=>c.handle));
  const unownedVids = coll.videos.filter(v=>!v.creator||!trackedHandles.has(v.creator));

  const creatorHtml = renderCollCreators(coll);
  const unownedHtml = unownedVids.length ? renderUnownedVideos(unownedVids, coll) : "";

  body.innerHTML=`
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <button class="coll-back-btn" onclick="_activeCollId=null;renderCollections()">← Back</button>
    </div>
    <div class="coll-add-bar">
      <input class="coll-add-in" id="coll-add-in" type="text"
        placeholder="@creator handle or TikTok/YouTube URL">
      <button class="coll-add-btn" onclick="addToCollection('${x(id)}')">+ Add</button>
    </div>
    ${creatorHtml}
    ${unownedHtml}`;
}

function renderUnownedVideos(vids, coll){
  const cards = vids.map((v,i)=>{
    const globalIdx = coll.videos.indexOf(v);
    const src = v.thumb ? `/api/serve-thumb?path=${encodeURIComponent(v.thumb.replace(/\\/g,"/"))}` : "";
    const isDownloading = !!v.downloading;
    return `<div class="vid-card${isDownloading?" downloading":""}">
      <div class="vid-card-thumb" onclick="${isDownloading?"void(0)":`openScrollFromCard('${x(coll.id)}','',${i})`}">
        ${isDownloading
          ? `<div class="vid-card-thumb-ph"><div class="acct-spinner" style="width:22px;height:22px;border-width:2.5px;border-top-color:var(--pink)"></div></div>`
          : src
            ? `<img src="${src}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
               <div class="vid-card-thumb-ph" style="display:none">🎬</div>`
            : `<div class="vid-card-thumb-ph">${v.localPath?"🎬":"🔗"}</div>`}
        ${!isDownloading?`<div class="vid-card-overlay">▶</div>`:""}
      </div>
      <div class="vid-card-info">
        <div class="vid-card-desc">${x(v.desc||"Video")}</div>
        <div class="vid-card-meta">${x(v.added||"")}</div>
      </div>
      <button class="vid-card-dots" onclick="toggleVidMenu(event,'${x(coll.id)}',${globalIdx})">⋮</button>
    </div>`;
  }).join("");
  return `<div class="ha-section" style="margin-top:16px">
    <div class="ha-section-title">Videos</div>
    <div class="vid-cards-grid">${cards}</div>
  </div>`;
}

function toggleVidMenu(e, collId, vidIdx){
  e.stopPropagation();
  document.querySelectorAll(".creator-ctx-menu").forEach(m=>m.remove());
  const coll = _collections.find(c=>c.id===collId);
  const v    = coll&&coll.videos[vidIdx];
  const rect = e.currentTarget.getBoundingClientRect();
  const menu = document.createElement("div");
  menu.className = "creator-ctx-menu";
  menu.innerHTML = (v&&v.localPath
    ? `<div class="ctx-item" onclick="_openPath('${x(collId)}',${vidIdx})">Show in Explorer</div>`
    : "") +
    `<div class="ctx-item danger" onclick="_removeVid('${x(collId)}',${vidIdx})">Remove</div>`;
  menu.style.top  = (rect.bottom+4)+"px";
  menu.style.left = Math.max(8, rect.right-190)+"px";
  document.body.appendChild(menu);
  setTimeout(()=>document.addEventListener("click",()=>menu.remove(),{once:true}),10);
}
function _openPath(collId, vidIdx){
  const coll=_collections.find(c=>c.id===collId);
  const v=coll&&coll.videos[vidIdx];
  if(v&&v.localPath) fetch("/api/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:v.localPath})});
  document.querySelectorAll(".creator-ctx-menu").forEach(m=>m.remove());
}
function _removeVid(collId, vidIdx){
  document.querySelectorAll(".creator-ctx-menu").forEach(m=>m.remove());
  removeFromCollection(collId,"video",vidIdx);
}


function renderCollVideos(coll){
  if(!coll.videos.length) return `<div style="padding:40px;text-align:center;font-family:var(--fm);font-size:.78rem;color:var(--text3)">
    No videos yet — paste a TikTok or YouTube URL above to add one.</div>`;

  const cards = coll.videos.map((v,i)=>{
    const hasLocal      = !!(v.localPath && v.localPath.length > 0);
    const isDownloading = !!v.downloading;
    const safeLocal     = (v.localPath||"").replace(/\\/g,"/");
    const safeName      = x(v.desc || "Video");

    // Thumbnail content
    let thumbContent;
    if(isDownloading){
      thumbContent = `<div style="display:flex;flex-direction:column;align-items:center;gap:8px">
        <div class="acct-spinner" style="width:22px;height:22px;border-width:2.5px;border-top-color:var(--pink)"></div>
        <span style="font-family:var(--fm);font-size:.6rem;color:var(--text3)">Downloading…</span>
      </div>`;
    } else if(v.thumb){
      thumbContent = `<img src="/api/serve-thumb?path=${encodeURIComponent(v.thumb)}"
        onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
        <span style="display:none;font-size:2.2rem">🎬</span>`;
    } else {
      thumbContent = `<span style="font-size:2.2rem">${hasLocal ? "🎬" : "🔗"}</span>`;
    }

    const clickFn = hasLocal
      ? `openVidPlayer('${safeLocal}','${safeName}')`
      : `window.open('${x(v.url||"")}','_blank')`;

    return `<div class="vid-item${isDownloading?" downloading":""}">
      <div class="vid-thumb" onclick="${isDownloading?"":clickFn}" style="${isDownloading?"cursor:default":"cursor:pointer"}">
        ${thumbContent}
        ${!isDownloading?`<div class="vid-thumb-overlay"><div class="vid-play-btn">${hasLocal?"▶":"↗"}</div></div>`:""}
        ${isDownloading?`<div class="vid-dl-badge">⬇ Saving…</div>`:hasLocal?`<div class="vid-dl-badge ok">✓ Local</div>`:""}
      </div>
      <div class="vid-info">
        <div class="vid-desc">${safeName}</div>
        <div class="vid-meta">${x(v.added||"")}</div>
      </div>
      <button class="vid-remove-btn" onclick="removeFromCollection('${x(coll.id)}','video',${i})">✕</button>
    </div>`;
  }).join("");

  return `<div class="vid-grid">${cards}</div>`;
}
function renderCollCreators(coll){
  if(!coll.creators.length) return "";
  const items = coll.creators.map((c,i)=>{
    const handle = c.handle||"";
    const pfpSrc = c.pfp ? `/api/serve-thumb?path=${encodeURIComponent(c.pfp)}` : "";
    // Videos belonging to this creator
    const creatorVids = coll.videos.filter(v=>v.creator===handle);
    const dl = _activeDownloads[collId(coll)+":"+i];
    const isDownloading = !!(dl && dl.active);

    // Show first 4 videos, rest hidden
    const SHOW = 4;
    const visible = creatorVids.slice(0, SHOW);
    const hidden  = creatorVids.slice(SHOW);

    const vidCards = creatorVids.length ? `
      <div class="creator-vids-row" id="cvids-${i}">
        ${visible.map((v,vi)=>renderMiniVidCard(v, coll.videos.indexOf(v), coll.id, creatorVids.indexOf(v))).join("")}
        ${hidden.length ? `
          <div class="mini-vid-more" onclick="expandCreatorVids(${i},this,'${x(coll.id)}','${x(handle)}')">
            +${hidden.length} more
          </div>` : ""}
      </div>` : "";

    return `<div class="creator-row" id="creator-row-${i}">
      <div class="creator-row-head">
        <div class="creator-pfp" id="cpfp-${i}">
          ${pfpSrc
            ? `<img src="${pfpSrc}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
            : ""}
          <span ${pfpSrc?"style='display:none'":""}>${handle.slice(0,1).toUpperCase()}</span>
        </div>
        <div style="flex:1;min-width:0">
          <div class="notif-handle">@${x(handle)}</div>
          <div class="notif-time">${creatorVids.length} video${creatorVids.length!==1?"s":""} · Added ${c.added||""}</div>
        </div>
        <div class="creator-dl-bar" style="flex-shrink:0">
          <select class="creator-dl-select" id="dl-limit-${i}">
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="all">All</option>
          </select>
          <button class="creator-dl-btn" id="dl-btn-${i}"
            onclick="downloadCreatorVideos('${x(coll.id)}','${x(handle)}',${i})">
            ${isDownloading?"⏳ Downloading…":"⬇ Download"}
          </button>
          <span class="creator-dl-counter" id="dl-count-${i}" style="display:none"></span>
        </div>
        <div class="three-dots-btn" onclick="toggleCreatorMenu(event,'${x(coll.id)}',${i},'${x(handle)}')">⋮</div>
      </div>
      <div class="creator-dl-progress${isDownloading?" show":""}" id="dl-prog-${i}">${isDownloading?(dl.text||"Downloading…"):""}</div>
      ${vidCards}
    </div>`;
  }).join("");
  return `<div style="display:flex;flex-direction:column;gap:10px">${items}</div>`;
}

function collId(coll){ return coll.id; }

function renderMiniVidCard(v, globalIdx, collId, localIdx){
  const thumbSrc = v.thumb
    ? `/api/serve-thumb?path=${encodeURIComponent(v.thumb.replace(/\\/g,"/"))}`
    : "";
  const clickFn = (v.localPath || v.url)
    ? `openScrollFromCard('${x(collId)}','${x(v.creator||"")}',${localIdx})`
    : "void(0)";
  // Get creator PFP from _collections
  const coll = _collections.find(c=>c.id===collId);
  const creator = v.creator ? coll?.creators.find(c=>c.handle===v.creator) : null;
  const pfpSrc = creator?.pfp ? `/api/serve-thumb?path=${encodeURIComponent(creator.pfp)}` : "";
  const creatorInitial = (v.creator||"?").slice(0,1).toUpperCase();
  return `<div class="vid-card" onclick="${clickFn}">
    <div class="vid-card-thumb">
      ${thumbSrc
        ? `<img src="${thumbSrc}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
           <div class="vid-card-thumb-ph" style="display:none">🎬</div>`
        : `<div class="vid-card-thumb-ph">🎬</div>`}
      <div class="vid-card-overlay">▶</div>
      ${v.downloading ? `<div class="vid-card-dl-badge">⬇ Saving…</div>` : ""}
    </div>
    <div class="vid-card-info">
      <div class="vid-card-creator">
        ${pfpSrc
          ? `<img class="vid-card-pfp" src="${pfpSrc}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="vid-card-pfp vid-card-pfp-init" style="display:none">${creatorInitial}</div>`
          : `<div class="vid-card-pfp vid-card-pfp-init">${creatorInitial}</div>`}
        <span class="vid-card-handle">${v.creator ? "@"+x(v.creator) : ""}</span>
      </div>
      <div class="vid-card-desc">${x(v.desc||"")}</div>
    </div>
  </div>`;
}

function openScrollFromCard(collId, handle, startLocalIdx){
  const coll = _collections.find(c=>c.id===collId);
  if(!coll) return;
  const vids = handle
    ? coll.videos.filter(v=>v.creator===handle)
    : coll.videos;
  openScrollPlayer(vids, startLocalIdx);
}

function expandCreatorVids(creatorIdx, btn, collId, handle){
  const coll = _collections.find(c=>c.id===collId);
  if(!coll) return;
  const vids = coll.videos.filter(v=>v.creator===handle);
  const row  = document.getElementById(`cvids-${creatorIdx}`);
  if(!row) return;
  row.innerHTML = vids.map((v,vi)=>renderMiniVidCard(v, coll.videos.indexOf(v), collId, vi)).join("");
}

function toggleCreatorMenu(e, collId, creatorIdx, handle){
  e.stopPropagation();
  document.querySelectorAll(".creator-ctx-menu").forEach(m=>m.remove());
  const btn  = e.currentTarget;
  const rect = btn.getBoundingClientRect();
  const menu = document.createElement("div");
  menu.className = "creator-ctx-menu";
  menu.innerHTML = `
    <div class="ctx-item" onclick="openCreatorFolder('${x(handle)}')">Show in Explorer</div>
    <div class="ctx-item danger" onclick="deleteCreatorAndVideos('${x(collId)}',${creatorIdx},'${x(handle)}')">Delete creator + videos</div>`;
  menu.style.top  = (rect.bottom+4)+"px";
  menu.style.left = Math.max(8, rect.right-190)+"px";
  document.body.appendChild(menu);
  setTimeout(()=>document.addEventListener("click",()=>menu.remove(),{once:true}),10);
}

function openCreatorFolder(handle){
  fetch("/api/open",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({path:"", folder:true, handle})}).catch(()=>{});
}

async function deleteCreatorAndVideos(collId, creatorIdx, handle){
  const coll = _collections.find(c=>c.id===collId);
  if(!coll) return;
  if(!confirm(`Delete @${handle} and all their downloaded videos?`)) return;
  // Remove creator
  coll.creators.splice(creatorIdx, 1);
  // Remove all videos from this creator
  coll.videos = coll.videos.filter(v=>v.creator!==handle);
  await saveColl();
  renderCollectionDetail(collId);
}


let _pendingVid = null;
const _activeDownloads = {}; // key: "collId:creatorIdx"

async function addToCollection(collId){
  const inp=document.getElementById("coll-add-in");
  const val=(inp?inp.value:"").trim();
  if(!val) return;
  const coll=_collections.find(c=>c.id===collId);
  if(!coll) return;

  const isCreator = val.startsWith("@") || (!val.startsWith("http") && !val.includes("/"));
  if(isCreator){
    const handle=val.replace(/^@/,"").toLowerCase();
    if(coll.creators.find(c=>c.handle===handle)){ inp.value=""; return; }
    const newCreator = {handle, added:new Date().toLocaleDateString(), videoCount:0, pfp:""};
    coll.creators.push(newCreator);
    inp.value="";
    await saveColl();
    renderCollectionDetail(collId);
    // Fetch PFP in background
    fetch("/api/creator-pfp",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({handle})}).then(r=>r.json()).then(d=>{
        if(d.pfp){ newCreator.pfp=d.pfp; saveColl().catch(()=>{}); renderCollectionDetail(collId); }
      }).catch(()=>{});
  } else {
    // Video URL — ask for name then download
    if(coll.videos.find(v=>v.url===val)){ inp.value=""; return; }
    inp.value="";
    _pendingVid = {collId, url:val};
    const dialog = document.getElementById("vid-name-dialog");
    const nameIn  = document.getElementById("vid-name-in");
    if(dialog){ dialog.style.display="flex"; }
    if(nameIn){ nameIn.value=""; setTimeout(()=>nameIn.focus(),100); }
  }
}

function cancelVidName(){
  _pendingVid=null;
  const d=document.getElementById("vid-name-dialog");
  if(d) d.style.display="none";
}

async function confirmVidName(){
  if(!_pendingVid) return;
  const nameIn = document.getElementById("vid-name-in");
  const btn    = document.getElementById("vid-name-confirm-btn");
  const name   = (nameIn?nameIn.value.trim():"") || "TikTok Video";
  const {collId, url} = _pendingVid;
  const coll = _collections.find(c=>c.id===collId);
  if(!coll) return;

  const dialog = document.getElementById("vid-name-dialog");
  if(dialog) dialog.style.display="none";
  if(btn){ btn.innerHTML="Add to Collection"; btn.disabled=false; }
  _pendingVid = null;

  const vid = {url, desc:name, thumb:"", localPath:"", added:new Date().toLocaleDateString(), downloading:true};
  coll.videos.push(vid);
  await saveColl();
  renderCollectionDetail(collId);

  // Download in background
  try{
    const r = await fetch("/api/tool",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({tool_id:"dl_vid",options:{url,quality:"720"}})
    });
    const reader=r.body.getReader(); const dec=new TextDecoder(); let buf="";
    while(true){
      const {value,done}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split("\n"); buf=lines.pop();
      for(const line of lines){
        if(!line.startsWith("data: ")) continue;
        let ev; try{ev=JSON.parse(line.slice(6))}catch(e){continue}
        if(ev.type==="done"){ vid.localPath=ev.path||""; }
      }
    }
  }catch(e){ console.warn("Download failed:",e.message); }

  vid.downloading=false;

  if(vid.localPath){
    try{
      const td=await fetch("/api/extract-thumb",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({path:vid.localPath})
      }).then(r=>r.json());
      if(td.thumb) vid.thumb=td.thumb;
    }catch(e){}
  }
  // Also try to get creator + description from yt-dlp metadata
  if(vid.localPath && (!vid.creator || !vid.desc || vid.desc==="TikTok Video")){
    try{
      const meta=await fetch("/api/video-meta",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({path:vid.localPath})
      }).then(r=>r.json()).catch(()=>({}));
      if(meta.creator && !vid.creator) vid.creator=meta.creator;
      if(meta.desc && (vid.desc==="TikTok Video"||!vid.desc)) vid.desc=meta.desc;
    }catch(e){}
  }

  const collAfter=_collections.find(c=>c.id===collId);
  if(collAfter){
    const vi=collAfter.videos.indexOf(vid);
    if(vi>=0) collAfter.videos[vi]={...vid};
  }
  await saveColl();
  renderCollectionDetail(collId);
}


// ── CUSTOM VIDEO PLAYER ──────────────────────────────────────────────────────
let _vpVideos = [];
let _vpIdx    = 0;
let _vpLoop   = false;
let _vpAuto   = false;
let _vpScrubbing = false;

function openVidPlayer(filePath, title, videos, startIdx){
  // Can be called with a single video or a playlist
  if(Array.isArray(videos) && videos.length){
    _vpVideos = videos;
    _vpIdx    = startIdx || 0;
  } else {
    _vpVideos = [{localPath:filePath, desc:title||"", url:""}];
    _vpIdx    = 0;
  }
  const ov = document.getElementById("vid-player-overlay");
  if(!ov) return;
  ov.classList.add("open");
  vpLoad(_vpIdx);
  document.addEventListener("keydown", _vpKeyHandler);
}

function closeVidPlayer(){
  const ov  = document.getElementById("vid-player-overlay");
  const vid = document.getElementById("vp-video");
  if(vid){ vid.pause(); vid.src=""; }
  if(ov) ov.classList.remove("open");
  document.removeEventListener("keydown", _vpKeyHandler);
}
function vpClose(){ closeVidPlayer(); }

function vpLoad(idx, dir){
  const v   = _vpVideos[idx];
  if(!v) return;
  const vid = document.getElementById("vp-video");
  const ttl = document.getElementById("vp-title");
  const ctr = document.getElementById("vp-counter");
  const noL = document.getElementById("vp-no-local");
  const wb  = document.getElementById("vp-open-web");
  const pp  = document.getElementById("vp-play-btn");
  const pPrev = document.getElementById("vp-nav-prev");
  const pNext = document.getElementById("vp-nav-next");

  if(ttl) ttl.textContent = v.desc || "Video";
  if(ctr) ctr.textContent = _vpVideos.length>1 ? `${idx+1} / ${_vpVideos.length}` : "";
  if(pPrev) pPrev.disabled = idx === 0;
  if(pNext) pNext.disabled = idx === _vpVideos.length-1;

  if(v.localPath){
    const cleanPath = (v.localPath||"").replace(/\\/g,"/");
    const src = `/api/serve-video?path=${encodeURIComponent(cleanPath)}`;
    if(vid){
      vid.style.display="block";
      if(vid.src !== window.location.origin+src){
        vid.src = src;
        vid.load();
      }
      vid.play().catch(()=>{});
      // Swipe animation
      if(dir){
        vid.classList.remove('slide-up','slide-down');
        void vid.offsetWidth; // reflow
        vid.classList.add(dir > 0 ? 'slide-up' : 'slide-down');
        setTimeout(()=>vid.classList.remove('slide-up','slide-down'), 350);
      }
    }
    if(noL) noL.style.display="none";
  } else {
    if(vid){ vid.pause(); vid.src=""; vid.style.display="none"; }
    if(noL) noL.style.display="flex";
    if(noL) noL.style.alignItems="center";
    if(noL) noL.style.justifyContent="center";
    if(noL) noL.style.flexDirection="column";
    if(wb && v.url) wb.onclick = ()=>window.open(v.url,"_blank");
  }
  if(pp) pp.textContent = "⏸";
  vpUpdateProgress();
}

function vpNav(dir){
  const next = _vpIdx + dir;
  if(next < 0 || next >= _vpVideos.length) return;
  _vpIdx = next;
  vpLoad(_vpIdx, dir);
}

function vpTogglePlay(){
  const vid = document.getElementById("vp-video");
  const btn = document.getElementById("vp-play-btn");
  if(!vid) return;
  if(vid.paused){ vid.play(); if(btn) btn.textContent="⏸"; }
  else { vid.pause(); if(btn) btn.textContent="▶"; }
}

function vpSkip(sec){
  const vid = document.getElementById("vp-video");
  if(vid) vid.currentTime = Math.max(0, Math.min(vid.duration||0, vid.currentTime+sec));
}

function vpToggleLoop(){
  const vid = document.getElementById("vp-video");
  const btn = document.getElementById("vp-loop-btn");
  _vpLoop = !_vpLoop;
  if(vid) vid.loop = _vpLoop;
  if(btn) btn.classList.toggle("active", _vpLoop);
}

function vpToggleAuto(){
  _vpAuto = !_vpAuto;
  const btn = document.getElementById("vp-auto-btn");
  if(btn) btn.classList.toggle("active", _vpAuto);
  if(btn) btn.title = _vpAuto ? "Auto-advance ON" : "Auto-advance OFF";
}

function vpToggleMute(){
  const vid = document.getElementById("vp-video");
  const btn = document.getElementById("vp-mute-btn");
  if(!vid) return;
  vid.muted = !vid.muted;
  if(btn) btn.style.opacity = vid.muted ? ".3" : "1";
}

function vpSetVol(v){
  const vid = document.getElementById("vp-video");
  if(vid) vid.volume = parseFloat(v);
}

function vpUpdateProgress(){
  const vid  = document.getElementById("vp-video");
  const bar  = document.getElementById("vp-progress-bar");
  const thb  = document.getElementById("vp-progress-thumb");
  const time = document.getElementById("vp-time");
  if(!vid || !bar) return;
  const pct = vid.duration ? (vid.currentTime/vid.duration)*100 : 0;
  bar.style.width = pct+"%";
  if(thb) thb.style.left = pct+"%";
  const fmt = s=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,"0")}`;
  if(time) time.textContent = `${fmt(vid.currentTime||0)} / ${fmt(vid.duration||0)}`;
}

function vpScrubClick(e){
  const vid  = document.getElementById("vp-video");
  const wrap = document.getElementById("vp-progress-wrap");
  if(!vid||!wrap) return;
  const r = wrap.getBoundingClientRect();
  const pct = Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));
  vid.currentTime = pct*(vid.duration||0);
}

function vpScrubStart(e){
  _vpScrubbing=true;
  vpScrubClick(e);
  const up=()=>{_vpScrubbing=false;document.removeEventListener("mouseup",up);};
  document.addEventListener("mouseup",up);
}

// Wire progress updates
document.addEventListener("DOMContentLoaded",()=>{
  const vid = document.getElementById("vp-video");
  if(vid){
    vid.addEventListener("timeupdate", vpUpdateProgress);
    vid.addEventListener("ended",()=>{
      if(_vpLoop){ /* video.loop handles it */ return; }
      if(_vpAuto && _vpIdx < _vpVideos.length-1){ vpNav(1); return; }
      const b=document.getElementById("vp-play-btn"); if(b) b.textContent="▶";
    });
    vid.addEventListener("play",()=>{ const b=document.getElementById("vp-play-btn"); if(b) b.textContent="⏸"; });
    vid.addEventListener("pause",()=>{ const b=document.getElementById("vp-play-btn"); if(b) b.textContent="▶"; });
  }
});

function _vpKeyHandler(e){
  if(e.key==="Escape") closeVidPlayer();
  else if(e.key===" "||e.key==="k"){ e.preventDefault(); vpTogglePlay(); }
  else if(e.key==="ArrowRight") vpNav(1);
  else if(e.key==="ArrowLeft")  vpNav(-1);
  else if(e.key==="l") vpSkip(10);
  else if(e.key==="j") vpSkip(-10);
  else if(e.key==="m") vpToggleMute();
}

// openScrollPlayer now uses the new player
function openScrollPlayer(videos, startIdx){
  openVidPlayer("","",videos,startIdx);
}
function openScrollFromCard(collId, handle, startLocalIdx){
  const coll = _collections.find(c=>c.id===collId);
  if(!coll) return;
  const vids = handle ? coll.videos.filter(v=>v.creator===handle) : coll.videos;
  openVidPlayer("","",vids,startLocalIdx);
}
function closeScrollPlayer(){ closeVidPlayer(); }

// ── GRID/SCROLL VIEW ────────────────────────────────────────────────────────
function setVidView(mode){ _vidViewMode=mode; }


async function downloadCreatorVideos(collId, handle, idx){
  const limitSel = document.getElementById(`dl-limit-${idx}`);
  const btn      = document.getElementById(`dl-btn-${idx}`);
  const prog     = document.getElementById(`dl-prog-${idx}`);
  const limit    = limitSel ? limitSel.value : "20";
  const dlKey    = `${collId}:${idx}`;
  let dlCount    = 0;

  _activeDownloads[dlKey] = {active:true, text:"Starting…"};
  if(btn){btn.disabled=true;btn.textContent="⏳ Downloading…";}
  if(prog){prog.textContent="Starting download…";prog.classList.add("show");}

  const coll = _collections.find(c=>c.id===collId);
  if(!coll){ delete _activeDownloads[dlKey]; if(btn){btn.disabled=false;btn.textContent="⬇ Download";} return; }

  const total = limit==="all" ? "?" : limit;
  const updateProg = (text, count)=>{
    _activeDownloads[dlKey] = {active:true, text};
    const p = document.getElementById(`dl-prog-${idx}`);
    if(p){p.textContent=text;p.classList.add("show");}
    const b = document.getElementById(`dl-btn-${idx}`);
    if(b){b.disabled=true;b.textContent="⏳ Downloading…";}
    const ct = document.getElementById(`dl-count-${idx}`);
    if(ct && count!=null){
      ct.textContent=`${count} / ${total}`;
      ct.style.display="inline";
    }
  };

  try{
    const r = await fetch("/api/creator-bulk-download",{
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({handle,limit})
    });
    const reader=r.body.getReader(); const dec=new TextDecoder(); let buf="";
    while(true){
      const{value,done}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split("\n"); buf=lines.pop();
      for(const line of lines){
        if(!line.startsWith("data: ")) continue;
        let ev; try{ev=JSON.parse(line.slice(6))}catch(e){continue}
        if(ev.type==="progress") updateProg(ev.text||"");
        if(ev.type==="video_ready"){
          dlCount = ev.count || (dlCount+1);
          updateProg(`Downloaded ${dlCount} video${dlCount!==1?"s":""}…`, dlCount);
          // Re-fetch coll in case reference changed
          const liveColl = _collections.find(c=>c.id===collId);
          if(liveColl){
            liveColl.videos.push({
              url:ev.url||"",
              desc:ev.title||handle,
              thumb:ev.thumb||"",
              localPath:ev.path||"",
              added:new Date().toLocaleDateString(),
              downloading:false,
              creator:handle
            });
            const ci=liveColl.creators.findIndex(c=>c.handle===handle);
            if(ci>=0) liveColl.creators[ci].videoCount=(liveColl.creators[ci].videoCount||0)+1;
          }
          saveColl().catch(()=>{});
          if(_activeCollId===collId) renderCollectionDetail(collId);
        }
        if(ev.type==="done"){
          delete _activeDownloads[dlKey];
          updateProg(`✓ ${dlCount} video${dlCount!==1?"s":""} downloaded`);
          const ct=document.getElementById(`dl-count-${idx}`);
          if(ct) ct.style.display="none";
          await saveColl();
          if(_activeCollId===collId) renderCollectionDetail(collId);
          break;
        }
        if(ev.type==="error"){
          delete _activeDownloads[dlKey];
          updateProg(`✗ ${ev.text}`);
        }
      }
    }
  }catch(e){
    delete _activeDownloads[dlKey];
    const p=document.getElementById(`dl-prog-${idx}`);
    if(p){p.textContent=`✗ ${e.message}`;p.classList.add("show");}
  }finally{
    delete _activeDownloads[dlKey];
    const b=document.getElementById(`dl-btn-${idx}`);
    if(b){b.disabled=false;b.textContent="⬇ Download";}
  }
}


async function removeFromCollection(collId, type, idx){
  const coll=_collections.find(c=>c.id===collId);
  if(!coll) return;
  if(type==="video") coll.videos.splice(idx,1);
  else coll.creators.splice(idx,1);
  await saveColl();
  renderCollectionDetail(collId);
}

// ── FIRST RUN ─────────────────────────────────────────────────────────────────
async function checkFirstRun(){
  // Show the login overlay immediately — never block on it
  // We'll hide it once we know the user is authenticated or has skipped
  const overlay = document.getElementById("setup-overlay");

  // Only hide overlay if user has an actual saved token (real login)
  const storedToken = localStorage.getItem("es_token");
  const sessionSkip = sessionStorage.getItem("es_skipped");
  if(storedToken || sessionSkip){
    if(overlay) overlay.classList.add("hidden");
  }

  // Try to load config — server may not be up yet, so retry
  let cfg = {};
  for(let i = 0; i < 40; i++){
    try{
      const r = await fetch("/api/config");
      if(!r.ok) throw new Error("not ready");
      cfg = await r.json();
      break;   // got it
    }catch(e){
      await new Promise(r => setTimeout(r, 250));
    }
  }

  // Load whatever config we got (may be empty on first run — that's fine)
  _loadConfig(cfg);

  // Restore role if logged in
  const storedRole = localStorage.getItem("es_role");
  if(storedRole) applyRole(storedRole);
  if(storedToken) fetchAndApplyRole(storedToken).catch(()=>{});
  renderAcctPanel();

  // setup_complete alone doesn't hide — need real token
  // (prevents old config from skipping login on fresh installs)
}
document.addEventListener("DOMContentLoaded",()=>checkFirstRun());
