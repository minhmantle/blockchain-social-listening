import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from collections import Counter

st.set_page_config(
    page_title="Mantle Social Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MANTLE_GREEN   = "#00D395"
MANTLE_DARK    = "#0A1A0F"
MANTLE_SURFACE = "#0D1F15"
MANTLE_BORDER  = "#1A3320"
MANTLE_TEXT    = "#E0F5EC"
MANTLE_MUTED   = "#4A7A5A"

CHAIN_COLORS = {
    "Mantle":  MANTLE_GREEN,
    "Solana":  "#9945FF",
    "Base":    "#2563EB",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
.stApp{{background-color:{MANTLE_DARK};}}
.main .block-container{{padding:1.5rem 2rem 3rem;max-width:1400px;}}
#MainMenu,footer,header{{visibility:hidden;}}
section[data-testid="stSidebar"]{{display:none;}}
.stTabs [data-baseweb="tab-list"]{{gap:4px;background:{MANTLE_SURFACE};border-bottom:1px solid {MANTLE_BORDER};padding:0 4px;}}
.stTabs [data-baseweb="tab"]{{background:transparent;border-radius:6px 6px 0 0;color:{MANTLE_MUTED};font-size:13px;font-weight:600;padding:10px 22px;border:none;letter-spacing:0.02em;}}
.stTabs [aria-selected="true"]{{background:{MANTLE_SURFACE} !important;color:{MANTLE_GREEN} !important;border-bottom:2px solid {MANTLE_GREEN} !important;}}
.kpi-card{{background:{MANTLE_SURFACE};border:1px solid {MANTLE_BORDER};border-radius:12px;padding:18px 20px;}}
.kpi-label{{font-size:11px;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:600;}}
.kpi-value{{font-size:26px;font-weight:800;color:#fff;letter-spacing:-0.5px;}}
.kpi-delta-up{{font-size:12px;color:{MANTLE_GREEN};margin-top:5px;font-weight:500;}}
.kpi-delta-dn{{font-size:12px;color:#f87171;margin-top:5px;font-weight:500;}}
.kpi-neutral{{font-size:12px;color:{MANTLE_MUTED};margin-top:5px;}}
.post-card{{background:{MANTLE_SURFACE};border:1px solid {MANTLE_BORDER};border-radius:10px;padding:16px;margin-bottom:10px;}}
.post-card:hover{{border-color:{MANTLE_GREEN}44;}}
.post-handle{{font-size:13px;font-weight:700;color:{MANTLE_TEXT};}}
.post-meta{{font-size:11px;color:{MANTLE_MUTED};}}
.post-text{{font-size:13px;color:#aaa;line-height:1.55;margin:8px 0;}}
.narrative-pill{{display:inline-block;font-size:10px;padding:2px 8px;border-radius:99px;margin:2px;font-weight:600;}}
.section-title{{font-size:13px;font-weight:800;color:{MANTLE_TEXT};text-transform:uppercase;letter-spacing:0.12em;margin:12px 0 10px;border-bottom:1px solid {MANTLE_BORDER};padding-bottom:8px;}}
.tab-title{{font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.3px;margin-bottom:10px;}}
.header-bar{{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid {MANTLE_BORDER};}}
.live-pill{{background:#0A2E14;color:{MANTLE_GREEN};border:1px solid #1A5E2A;padding:4px 12px;border-radius:99px;font-size:11px;font-weight:600;}}
.search-note{{font-size:11px;color:{MANTLE_MUTED};background:{MANTLE_SURFACE};border:1px solid {MANTLE_BORDER};border-radius:6px;padding:6px 12px;margin-bottom:6px;}}
.kw-active{{font-size:11px;color:{MANTLE_GREEN};background:#0A2E14;border:1px solid #1A5E2A;border-radius:6px;padding:6px 12px;margin-bottom:6px;font-weight:600;}}
</style>
""", unsafe_allow_html=True)

NARRATIVES = {
    "DeFi":          ["defi","dex","liquidity","yield","swap","lending","amm","tvl","staking"],
    "RWA":           ["rwa","real world asset","tokenized","tokenization","treasury","bond","t-bill"],
    "AI":            ["ai","artificial intelligence","machine learning","llm","agent","gpt"],
    "Infrastructure":["infrastructure","layer2","l2","rollup","scalability","tps","validator","node"],
    "NFT":           ["nft","collectible","mint","opensea","marketplace"],
    "Gaming":        ["gaming","gamefi","game","play to earn","p2e","metaverse"],
    "Institutional": ["institution","institutional","blackrock","fidelity","bank","fund","etf",
                      "investment","hedge fund","enterprise","corporate","adoption"],
}

NARRATIVE_COLORS = {
    "DeFi":"#3b82f6","RWA":"#f59e0b","AI":"#8b5cf6",
    "Infrastructure":"#10b981","NFT":"#ec4899",
    "Gaming":"#f97316","Institutional":"#06b6d4","Other":"#6b7280",
}

AXIS = dict(gridcolor="#1A3320",showgrid=True,zeroline=False,color="#A0C8B0",tickfont=dict(color="#A0C8B0",size=11))
BASE_LAYOUT = dict(
    paper_bgcolor=MANTLE_SURFACE, plot_bgcolor=MANTLE_SURFACE,
    font=dict(color="#A0C8B0",size=11,family="Inter"),
    legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=13,color="#E0F5EC",family="Inter"),
                itemsizing="constant",tracegroupgap=4),
    hovermode="x unified",
    margin=dict(l=10,r=10,t=36,b=10),
)

BLOCKCHAIN_KW = ["crypto","blockchain","web3","defi","nft","token","chain","onchain",
                 "l2","layer2","wallet","protocol","dao","dapp","eth","btc","sol","bnb","mantle","base"]

def get_token():
    try: return st.secrets["TWITTER_BEARER_TOKEN"]
    except: return None

def hdrs(t): return {"Authorization":f"Bearer {t}"}

@st.cache_data(ttl=600)
def get_user(handle,token):
    r=requests.get(f"https://api.twitter.com/2/users/by/username/{handle}",
        headers=hdrs(token),params={"user.fields":"public_metrics,description"})
    return r.json().get("data",{}) if r.status_code==200 else {}

@st.cache_data(ttl=600)
def get_tweets(uid,token,start_iso,end_iso,max_results=100):
    params={"max_results":min(max_results,100),"start_time":start_iso,"end_time":end_iso,
            "tweet.fields":"public_metrics,created_at,text",
            "exclude":"retweets,replies"}
    r=requests.get(f"https://api.twitter.com/2/users/{uid}/tweets",headers=hdrs(token),params=params)
    if r.status_code!=200: return []
    return r.json().get("data",[]) or []

@st.cache_data(ttl=600)
def search_tweets(query,token,start_iso,end_iso,max_results=50):
    params={"query":query,"max_results":min(max_results,100),
            "start_time":start_iso,"end_time":end_iso,
            "tweet.fields":"public_metrics,created_at,author_id,text",
            "expansions":"author_id","user.fields":"username,name,public_metrics"}
    r=requests.get("https://api.twitter.com/2/tweets/search/recent",headers=hdrs(token),params=params)
    if r.status_code!=200: return []
    data=r.json()
    tweets=data.get("data",[])
    users={u["id"]:u for u in data.get("includes",{}).get("users",[])}
    for t in tweets:
        u=users.get(t.get("author_id"),{})
        t["author_name"]=u.get("name","Unknown")
        t["author_handle"]=u.get("username","unknown")
        t["author_followers"]=u.get("public_metrics",{}).get("followers_count",0)
    return tweets

def filter_by_kw(tweets, kw):
    if not kw: return tweets
    kw_lower = kw.lower()
    return [t for t in tweets if kw_lower in t.get("text","").lower()]

def fmt(n):
    if not n: return "0"
    n=int(n)
    if n>=1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n>=1_000_000:     return f"{n/1_000_000:.1f}M"
    if n>=1_000:         return f"{n/1_000:.1f}K"
    return str(n)

def eng(m):
    return (m.get("like_count",0) or 0)+(m.get("retweet_count",0) or 0)*3+(m.get("reply_count",0) or 0)*2

def get_imp(t):
    m=t.get("public_metrics",{})
    v=m.get("impression_count") or 0
    if v>0: return v
    return eng(m)*100

def parse_dt(s):
    for f in ["%Y-%m-%dT%H:%M:%S.%fZ","%Y-%m-%dT%H:%M:%SZ"]:
        try: return datetime.strptime(s,f)
        except: pass
    return datetime.utcnow()

def time_ago(s):
    d=datetime.utcnow()-parse_dt(s)
    if d.days>=1: return f"{d.days}d ago"
    h=d.seconds//3600
    if h>=1: return f"{h}h ago"
    return f"{d.seconds//60}m ago"

def detect_nar(text):
    tl=text.lower()
    found=[n for n,kws in NARRATIVES.items() if any(k in tl for k in kws)]
    return found if found else ["Other"]

def iso_range(s,e):
    si=datetime.combine(s,datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
    ei=min(datetime.combine(e,datetime.max.time()),datetime.utcnow()-timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return si,ei

def search_iso():
    e=datetime.utcnow()-timedelta(seconds=30)
    s=e-timedelta(days=6)
    return s.strftime("%Y-%m-%dT%H:%M:%SZ"),e.strftime("%Y-%m-%dT%H:%M:%SZ")

def group_by(tweets,period):
    rows=[]
    for t in tweets:
        dt=parse_dt(t["created_at"])
        m=t.get("public_metrics",{})
        if period=="Day": key=dt.date()
        elif period=="Week": key=dt.date()-timedelta(days=dt.weekday())
        else: key=dt.date().replace(day=1)
        imp=get_imp(t)
        rows.append({"period":key,"likes":m.get("like_count",0) or 0,
                     "retweets":m.get("retweet_count",0) or 0,
                     "replies":m.get("reply_count",0) or 0,
                     "eng_val":eng(m),"impressions":imp})
    if not rows:
        return pd.DataFrame(columns=["period","likes","retweets","replies","eng_val","impressions"])
    return pd.DataFrame(rows).groupby("period").sum().reset_index().sort_values("period")

def date_controls(pfx):
    if f"{pfx}_sv" not in st.session_state:
        st.session_state[f"{pfx}_sv"]=date.today()-timedelta(days=7)
    if f"{pfx}_ev" not in st.session_state:
        st.session_state[f"{pfx}_ev"]=date.today()
    c1,c2,c3=st.columns([2,2,1])
    with c1:
        start=st.date_input("From",value=st.session_state[f"{pfx}_sv"],max_value=date.today(),key=f"{pfx}_s")
        st.session_state[f"{pfx}_sv"]=start
    with c2:
        end=st.date_input("To",value=st.session_state[f"{pfx}_ev"],max_value=date.today(),key=f"{pfx}_e")
        st.session_state[f"{pfx}_ev"]=end
    with c3:
        st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
        period=st.selectbox("Group by",["Day","Week","Month"],key=f"{pfx}_p",label_visibility="collapsed")
    return start,end,period

def kpi(col,label,value,delta=None,sub=None,color=MANTLE_GREEN):
    d=""
    if delta is not None:
        cls="kpi-delta-up" if delta>=0 else "kpi-delta-dn"
        arrow="▲" if delta>=0 else "▼"
        d=f'<div class="{cls}">{arrow} {abs(delta):.1f}% vs prev period</div>'
    elif sub:
        d=f'<div class="kpi-neutral">{sub}</div>'
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color}">{value}</div>
      {d}
    </div>""",unsafe_allow_html=True)

def render_post(t,rank,color,chain_name=None,is_user=False):
    m=t.get("public_metrics",{})
    text=t.get("text","")
    brief=text[:200]+("…" if len(text)>200 else "")
    ev=eng(m)
    imp=get_imp(t)
    tid=t.get("id","")
    if is_user:
        handle=t.get("author_handle","unknown")
        name=t.get("author_name","User")
        followers=t.get("author_followers",0)
    else:
        handle={"Mantle":"Mantle_Official","Solana":"solana","Base":"base"}.get(chain_name,"")
        name=chain_name or "Official"
        followers=None
    link=f"https://x.com/{handle}/status/{tid}" if tid else "#"
    ago=time_ago(t.get("created_at",""))
    narrs=detect_nar(text)
    badge=f'<span class="narrative-pill" style="background:{color}22;color:{color};border:1px solid {color}44;font-size:10px;padding:2px 8px;border-radius:99px">{chain_name}</span>' if chain_name else ""
    pills=" ".join([f'<span class="narrative-pill" style="background:{NARRATIVE_COLORS.get(n,"#333")}22;color:{NARRATIVE_COLORS.get(n,"#888")};border:1px solid {NARRATIVE_COLORS.get(n,"#333")}33">{n}</span>' for n in narrs])
    fstr=f" · {fmt(followers)} followers" if followers else ""
    st.markdown(f"""
    <div class="post-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
        <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0">
          <span style="font-size:16px;font-weight:800;color:#333;min-width:24px">#{rank}</span>
          <div>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              {badge}<span class="post-handle">@{handle}</span>
              <span class="post-meta">{ago}{fstr}</span>
            </div>
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:14px;font-weight:800;color:{color}">{fmt(imp)}</div>
          <div style="font-size:10px;color:{MANTLE_MUTED}">views</div>
        </div>
      </div>
      <div class="post-text">{brief}</div>
      <div style="margin-bottom:8px">{pills}</div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="font-size:12px;color:{MANTLE_MUTED}">
          ♥ {fmt(m.get("like_count",0))} &nbsp;·&nbsp;
          ↺ {fmt(m.get("retweet_count",0))} &nbsp;·&nbsp;
          💬 {fmt(m.get("reply_count",0))}
        </div>
        <a href="{link}" target="_blank" style="font-size:11px;color:{color};text-decoration:none;padding:4px 12px;border:1px solid {color}44;border-radius:6px;white-space:nowrap;background:{color}11;font-weight:600">View ↗</a>
      </div>
    </div>""",unsafe_allow_html=True)

def kw_bar(key_input, key_btn, key_clear, placeholder):
    """Keyword search bar — returns (kw, active)"""
    c1,c2,c3=st.columns([4,1,1])
    with c1:
        kw=st.text_input("Keyword",placeholder=placeholder,key=key_input,label_visibility="collapsed")
    with c2:
        search=st.button("Search",key=key_btn,use_container_width=True)
    with c3:
        clear=st.button("Clear",key=key_clear,use_container_width=True)
    # persist active keyword in session state
    sk=f"{key_input}_active"
    if search and kw:
        st.session_state[sk]=kw
    if clear:
        st.session_state[sk]=""
    active=st.session_state.get(sk,"")
    if active:
        st.markdown(f'<div class="kw-active">🔍 Filtering by: <b>{active}</b> — metrics & posts below reflect this keyword only</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="search-note">💡 Enter a keyword to filter the entire dashboard</div>',unsafe_allow_html=True)
    return active

# ── TAB 1 ────────────────────────────────────────────────────────────────────
def tab_mantle(token):
    st.markdown('<div class="tab-title">Mantle — Performance Deep Dive</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔍 Keyword Filter</div>',unsafe_allow_html=True)
    kw=kw_bar("t1_kw","t1_kw_btn","t1_kw_clr","Filter by keyword — e.g. RWA, mETH, DeFi, hackathon…")

    st.markdown('<div class="section-title">Performance Overview</div>',unsafe_allow_html=True)
    start,end,period=date_controls("t1")
    start_iso,end_iso=iso_range(start,end)
    days=(end-start).days+1
    prev_s_iso,prev_e_iso=iso_range(start-timedelta(days=days),start-timedelta(days=1))

    with st.spinner("Fetching Mantle data…"):
        user=get_user("Mantle_Official",token)
        uid=user.get("id","")
        all_tweets=get_tweets(uid,token,start_iso,end_iso) if uid else []
        all_prev=get_tweets(uid,token,prev_s_iso,prev_e_iso) if uid else []

    # apply keyword filter
    tweets=filter_by_kw(all_tweets,kw)
    prev_tw=filter_by_kw(all_prev,kw)

    followers=user.get("public_metrics",{}).get("followers_count",0) or 0
    total_eng=sum(eng(t.get("public_metrics",{})) for t in tweets)
    prev_eng=sum(eng(t.get("public_metrics",{})) for t in prev_tw)
    total_likes=sum(t.get("public_metrics",{}).get("like_count",0) or 0 for t in tweets)
    total_rts=sum(t.get("public_metrics",{}).get("retweet_count",0) or 0 for t in tweets)
    total_views=sum(get_imp(t) for t in tweets)
    post_count=len(tweets)
    prev_posts=len(prev_tw)
    post_delta=((post_count-prev_posts)/prev_posts*100) if prev_posts else 0
    prev_views=sum(get_imp(t) for t in prev_tw)
    view_delta=((total_views-prev_views)/prev_views*100) if prev_views else 0
    eng_rate=round(total_eng/total_views*100,2) if total_views else 0

    k1,k2,k3,k4,k5=st.columns(5)
    kpi(k1,"Followers",fmt(followers),sub="current total")
    kpi(k2,"Posts published",str(post_count),delta=post_delta)
    kpi(k3,"Total views",fmt(total_views),delta=view_delta)
    kpi(k4,"Total likes",fmt(total_likes),sub=f"Retweets: {fmt(total_rts)}")
    kpi(k5,"Eng. rate",f"{eng_rate:.2f}%",sub="engagement / views")

    st.markdown("<div style='margin-top:16px'></div>",unsafe_allow_html=True)

    df=group_by(tweets,period)
    if not df.empty:
        fig=go.Figure()
        fig.add_trace(go.Bar(x=df["period"],y=df["impressions"],name="Views",
                             marker_color=MANTLE_GREEN,opacity=0.8,
                             hovertemplate="%{x}: %{y:,}<extra>Views</extra>"))
        fig.add_trace(go.Scatter(x=df["period"],y=df["eng_val"],name="Engagement",
                                 mode="lines+markers",yaxis="y2",
                                 line=dict(color="#f59e0b",width=2),marker=dict(size=5),
                                 hovertemplate="%{x}: %{y:,}<extra>Engagement</extra>"))
        title_kw=f' · keyword: "{kw}"' if kw else ""
        fig.update_layout(**BASE_LAYOUT,height=280,
                          xaxis=AXIS,
                          yaxis=dict(**AXIS,title="Views"),
                          yaxis2=dict(title=dict(text="Engagement",font=dict(color="#f59e0b")),overlaying="y",side="right",
                                      showgrid=False,zeroline=False,tickfont=dict(color="#f59e0b")),
                          title=dict(text=f"Views & Engagement by {period} — @Mantle_Official{title_kw}",
                                     font=dict(size=13,color="#E0F5EC"),x=0))
        st.plotly_chart(fig,use_container_width=True)

    all_nar=[]
    for t in tweets: all_nar.extend(detect_nar(t.get("text","")))
    nar_counts=Counter(all_nar)
    if nar_counts:
        st.markdown('<div class="section-title">Narrative Breakdown</div>',unsafe_allow_html=True)
        nc1,nc2=st.columns([1,2])
        with nc1:
            labels=list(nar_counts.keys())
            values=list(nar_counts.values())
            colors=[NARRATIVE_COLORS.get(l,"#666") for l in labels]
            fp=go.Figure(go.Pie(labels=labels,values=values,
                                marker=dict(colors=colors,line=dict(color=MANTLE_DARK,width=2)),
                                textfont_size=11,hole=0.55,
                                hovertemplate="%{label}: %{value} posts<extra></extra>"))
            pl={k:v for k,v in BASE_LAYOUT.items() if k!="margin"}
            fp.update_layout(**pl,height=220,showlegend=False,margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fp,use_container_width=True)
        with nc2:
            total_n=sum(nar_counts.values()) or 1
            for nm,cnt in sorted(nar_counts.items(),key=lambda x:-x[1]):
                c=NARRATIVE_COLORS.get(nm,"#666")
                pct=cnt/total_n*100
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                  <div style="width:10px;height:10px;border-radius:2px;background:{c};flex-shrink:0"></div>
                  <div style="flex:1;font-size:13px;color:{MANTLE_TEXT};font-weight:500">{nm}</div>
                  <div style="font-size:12px;color:{MANTLE_MUTED}">{cnt} posts · {pct:.0f}%</div>
                  <div style="width:80px;background:{MANTLE_BORDER};border-radius:4px;height:6px">
                    <div style="width:{pct}%;background:{c};border-radius:4px;height:6px"></div>
                  </div>
                </div>""",unsafe_allow_html=True)

    sorted_tw=sorted(tweets,key=get_imp,reverse=True)
    st.markdown('<div class="section-title">Top 5 Posts by Views — Mantle Official</div>',unsafe_allow_html=True)
    if sorted_tw:
        for i,t in enumerate(sorted_tw[:5],1):
            render_post(t,i,MANTLE_GREEN,chain_name="Mantle",is_user=False)
    else:
        st.info("No posts found for this time range." + (f' Try removing the keyword filter "{kw}".' if kw else ""))

# ── TAB 2 ────────────────────────────────────────────────────────────────────
def tab_competitive(token):
    st.markdown('<div class="tab-title">Competitive Analysis — Mantle vs Solana vs Base</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔍 Keyword Filter</div>',unsafe_allow_html=True)
    kw=kw_bar("t2_kw","t2_kw_btn","t2_kw_clr","Filter all chains by keyword — e.g. RWA, institutional, airdrop…")

    start,end,period=date_controls("t2")
    start_iso,end_iso=iso_range(start,end)
    days=(end-start).days+1
    prev_s_iso,prev_e_iso=iso_range(start-timedelta(days=days),start-timedelta(days=1))
    si7,ei7=search_iso()

    all_data={}
    with st.spinner("Fetching all chains…"):
        for name,color in CHAIN_COLORS.items():
            handle={"Mantle":"Mantle_Official","Solana":"solana","Base":"base"}[name]
            u=get_user(handle,token)
            uid=u.get("id","")
            raw_tw=get_tweets(uid,token,start_iso,end_iso) if uid else []
            raw_prev=get_tweets(uid,token,prev_s_iso,prev_e_iso) if uid else []
            tw=filter_by_kw(raw_tw,kw)
            ptw=filter_by_kw(raw_prev,kw)
            all_data[name]={"user":u,"tweets":tw,"prev":ptw,"color":color,"handle":handle}

    st.markdown('<div class="section-title">Performance Snapshot</div>',unsafe_allow_html=True)
    cols=st.columns(len(CHAIN_COLORS))
    for col,(name,d) in zip(cols,all_data.items()):
        color=d["color"]
        followers=d["user"].get("public_metrics",{}).get("followers_count",0) or 0
        total_v=sum(get_imp(t) for t in d["tweets"])
        prev_v=sum(get_imp(t) for t in d["prev"])
        delta=((total_v-prev_v)/prev_v*100) if prev_v else 0
        arrow="▲" if delta>=0 else "▼"
        dcls=f"color:{MANTLE_GREEN}" if delta>=0 else "color:#f87171"
        col.markdown(f"""
        <div class="kpi-card">
          <div style="font-size:12px;font-weight:800;color:{color};text-transform:uppercase;letter-spacing:.1em;margin-bottom:12px">{name}</div>
          <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:2px">Followers</div>
          <div style="font-size:20px;font-weight:800;color:#fff;margin-bottom:10px">{fmt(followers)}</div>
          <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:2px">Total views</div>
          <div style="font-size:20px;font-weight:800;color:{color}">{fmt(total_v)}</div>
          <div style="font-size:12px;{dcls};margin-top:4px;font-weight:600">{arrow} {abs(delta):.1f}% vs prev</div>
          <div style="font-size:11px;color:{MANTLE_MUTED};margin-top:8px">{len(d['tweets'])} posts</div>
        </div>""",unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>",unsafe_allow_html=True)

    fig=go.Figure()
    for name,d in all_data.items():
        df=group_by(d["tweets"],period)
        if not df.empty:
            fig.add_trace(go.Scatter(x=df["period"],y=df["impressions"],name=name,
                                     mode="lines+markers",
                                     line=dict(color=d["color"],width=2),marker=dict(size=5),
                                     hovertemplate=f"{name}: %{{y:,}}<extra></extra>"))
    title_kw=f' · keyword: "{kw}"' if kw else ""
    fig.update_layout(**BASE_LAYOUT,height=280,xaxis=AXIS,yaxis=AXIS,
                      title=dict(text=f"Views by {period} — all chains{title_kw}",
                                 font=dict(size=13,color="#E0F5EC"),x=0))
    st.plotly_chart(fig,use_container_width=True)

    st.markdown('<div class="section-title">Top 3 Official Posts by Views</div>',unsafe_allow_html=True)
    pcols=st.columns(len(CHAIN_COLORS))
    for col,(name,d) in zip(pcols,all_data.items()):
        stw=sorted(d["tweets"],key=get_imp,reverse=True)
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:800;color:{d["color"]};margin-bottom:10px;text-transform:uppercase;letter-spacing:.08em">{name}</div>',unsafe_allow_html=True)
            if stw:
                for i,t in enumerate(stw[:3],1):
                    render_post(t,i,d["color"],chain_name=name,is_user=False)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No data</div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Top User / KOL Mentions by Views (last 7 days)</div>',unsafe_allow_html=True)
    mcols=st.columns(len(CHAIN_COLORS))
    for col,(name,d) in zip(mcols,all_data.items()):
        if name=="Base":
            q='"Base chain" OR "Base blockchain" OR "build on Base" (crypto OR blockchain OR web3) -from:base -is:retweet lang:en min_faves:50'
        elif name=="Solana":
            q=f'(#Solana OR "Solana network" OR "SOL blockchain") (crypto OR blockchain OR defi OR web3) -from:solana -is:retweet lang:en min_faves:50'
        else:
            q=f'(#Mantle OR "Mantle network" OR "Mantle blockchain" OR mETH) (crypto OR blockchain OR defi OR web3) -from:Mantle_Official -is:retweet lang:en min_faves:20'
        with st.spinner(f"Fetching {name} mentions…"):
            mentions=search_tweets(q,token,si7,ei7,max_results=100)
        mentions=filter_by_kw(mentions,kw)
        mentions=[t for t in mentions if any(k in t.get("text","").lower() for k in BLOCKCHAIN_KW)]
        sm=sorted(mentions,key=get_imp,reverse=True)
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:800;color:{d["color"]};margin-bottom:10px;text-transform:uppercase">{name} mentions</div>',unsafe_allow_html=True)
            if sm:
                for i,t in enumerate(sm[:3],1):
                    render_post(t,i,d["color"],chain_name=name,is_user=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No mentions found</div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Narrative Distribution by Chain</div>',unsafe_allow_html=True)
    nfig=go.Figure()
    for name,d in all_data.items():
        all_n=[]
        for t in d["tweets"]: all_n.extend(detect_nar(t.get("text","")))
        counts=Counter(all_n)
        total=sum(counts.values()) or 1
        nfig.add_trace(go.Bar(name=name,
            x=list(NARRATIVES.keys())+["Other"],
            y=[counts.get(k,0)/total*100 for k in list(NARRATIVES.keys())+["Other"]],
            marker_color=d["color"],
            hovertemplate="%{x}: %{y:.1f}%<extra>"+name+"</extra>"))
    nfig.update_layout(**BASE_LAYOUT,barmode="group",height=260,
                       xaxis=AXIS,yaxis=dict(**AXIS,ticksuffix="%"),
                       title=dict(text="Narrative distribution % by chain",
                                  font=dict(size=13,color="#E0F5EC"),x=0))
    st.plotly_chart(nfig,use_container_width=True)

# Research accounts — hidden from UI
RESEARCH_KW = [
    "research","analysis","report","thread","deep dive","breakdown",
    "insight","data","metrics","onchain","on-chain","study","findings",
    "trends","outlook","review","alpha","thesis","framework","explained",
    "how","why","what","chart","graph","stat","number","billion","million",
    "growth","decline","increase","decrease","market","protocol","ecosystem",
]
RESEARCH_ACCOUNTS = [
    "a16zcrypto",
    "MessariCrypto",
    "TheBlockCo",
    "Delphi_Digital",
    "glassnode",
]

# ── TAB 3 ────────────────────────────────────────────────────────────────────
def tab_research(token):
    st.markdown('<div class="tab-title">Industry Research — Notable Reads</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔍 Keyword Filter</div>',unsafe_allow_html=True)
    kw=kw_bar("t3_kw","t3_kw_btn","t3_kw_clr","Filter research by topic — e.g. RWA, L2, DeFi, Mantle…")

    start,end,period=date_controls("t3")
    start_iso,end_iso=iso_range(start,end)

    # Fetch from all research accounts
    all_posts=[]
    with st.spinner("Fetching research posts from all accounts…"):
        for handle in RESEARCH_ACCOUNTS:
            u=get_user(handle,token)
            uid=u.get("id","")
            if not uid: continue
            tw=get_tweets(uid,token,start_iso,end_iso,max_results=100)
            # tag each tweet with author info
            for t in tw:
                t["author_handle"]=handle
                t["author_name"]=u.get("name",handle)
                t["author_followers"]=u.get("public_metrics",{}).get("followers_count",0)
            all_posts.extend(tw)

    # apply keyword filter
    filtered=filter_by_kw(all_posts,kw)
    # keep only research/article content
    filtered=[p for p in filtered if any(k in p.get("text","").lower() for k in RESEARCH_KW)]
    sorted_posts=sorted(filtered,key=get_imp,reverse=True)

    kw_label=f' · keyword: "{kw}"' if kw else ""
    st.caption(f"Found {len(filtered)} posts from {len(RESEARCH_ACCOUNTS)} research accounts{kw_label}")

    if not filtered:
        st.warning("No posts found. Try adjusting the date range or keyword.")
        return

    # Narrative distribution chart — all posts (not just top 15)
    all_nar=[]
    for p in filtered: all_nar.extend(detect_nar(p.get("text","")))
    nar_counts=Counter(all_nar)
    nar_counts.pop("Other",None)

    if nar_counts:
        st.markdown('<div class="section-title">Narrative Distribution — All Research Posts</div>',unsafe_allow_html=True)
        sn=sorted(nar_counts.items(),key=lambda x:-x[1])
        total_n=sum(v for _,v in sn) or 1
        fb=go.Figure(go.Bar(
            x=[n for n,_ in sn],
            y=[c/total_n*100 for _,c in sn],
            marker_color=[NARRATIVE_COLORS.get(n,"#666") for n,_ in sn],
            text=[f"{c/total_n*100:.0f}%" for _,c in sn],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f}% (%{customdata} posts)<extra></extra>",
            customdata=[c for _,c in sn]))
        fb.update_layout(**BASE_LAYOUT,height=240,showlegend=False,
                         xaxis=AXIS,yaxis=dict(**AXIS,ticksuffix="%"),
                         title=dict(text=f"Narrative distribution — {len(filtered)} posts{kw_label}",
                                    font=dict(size=13,color="#E0F5EC"),x=0))
        st.plotly_chart(fb,use_container_width=True)

    # Top 15 posts by views
    st.markdown('<div class="section-title">Top 15 Research Posts by Views</div>',unsafe_allow_html=True)
    for i,t in enumerate(sorted_posts[:15],1):
        render_post(t,i,"#A0C8B0",is_user=True)

# ── TAB 4: MARKET NARRATIVE ──────────────────────────────────────────────────
# Queries per narrative — count tweets in last 7 days
NARRATIVE_QUERIES = {
    "DeFi":           "(defi OR dex OR yield OR liquidity OR lending OR amm) (crypto OR blockchain) -is:retweet lang:en",
    "RWA":            "(rwa OR \"real world asset\" OR tokenized OR tokenization OR \"treasury token\") (crypto OR blockchain) -is:retweet lang:en",
    "AI x Crypto":    "(ai OR \"artificial intelligence\" OR llm OR \"ai agent\") (crypto OR blockchain OR web3 OR defi) -is:retweet lang:en",
    "Infrastructure": "(layer2 OR l2 OR rollup OR \"base layer\" OR validator OR restaking) (crypto OR blockchain) -is:retweet lang:en",
    "NFT":            "(nft OR \"digital collectible\" OR mint OR pfp) (crypto OR blockchain) -is:retweet lang:en",
    "Gaming":         "(gamefi OR \"play to earn\" OR p2e OR \"onchain game\" OR gaming) (crypto OR blockchain) -is:retweet lang:en",
    "Institutional":  "(institutional OR etf OR blackrock OR fidelity OR \"hedge fund\" OR \"asset manager\") (crypto OR bitcoin OR ethereum) -is:retweet lang:en",
    "Stablecoin":     "(stablecoin OR usdt OR usdc OR \"stable coin\" OR depeg) (crypto OR blockchain) -is:retweet lang:en",
    "Meme":           "(memecoin OR meme OR \"dog coin\" OR shitcoin OR pump) (crypto OR blockchain) -is:retweet lang:en",
}

@st.cache_data(ttl=600)
def count_narrative_tweets(query, token, start_iso, end_iso):
    """Use search/recent with max_results=10 just to get meta.result_count"""
    params={
        "query": query,
        "max_results": 10,
        "start_time": start_iso,
        "end_time": end_iso,
        "tweet.fields": "public_metrics,created_at,text",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics",
    }
    r=requests.get("https://api.twitter.com/2/tweets/search/recent",
                   headers=hdrs(token),params=params)
    if r.status_code!=200: return 0, []
    data=r.json()
    # get sample tweets for top posts section
    tweets=data.get("data",[]) or []
    users={u["id"]:u for u in data.get("includes",{}).get("users",[])}
    for t in tweets:
        u=users.get(t.get("author_id"),{})
        t["author_handle"]=u.get("username","unknown")
        t["author_name"]=u.get("name","Unknown")
        t["author_followers"]=u.get("public_metrics",{}).get("followers_count",0)
    # result_count is more accurate than len(tweets)
    count=data.get("meta",{}).get("result_count",len(tweets))
    return count, tweets

def tab_market(token):
    st.markdown('<div class="tab-title">Market Narrative Trends — Last 7 Days</div>',unsafe_allow_html=True)
    st.markdown('<div class="search-note">⚡ Based on X Search API — limited to last 7 days · ~9 API calls per load</div>',unsafe_allow_html=True)

    si,ei=search_iso()

    # Fetch counts for all narratives
    st.markdown('<div class="section-title">Narrative Volume — Tweet Count</div>',unsafe_allow_html=True)

    counts={}
    sample_tweets={}
    progress=st.progress(0,text="Fetching narrative data…")
    for i,(name,q) in enumerate(NARRATIVE_QUERIES.items()):
        progress.progress((i+1)/len(NARRATIVE_QUERIES),text=f"Fetching {name}…")
        c,tw=count_narrative_tweets(q,token,si,ei)
        counts[name]=c
        sample_tweets[name]=tw
    progress.empty()

    if not any(counts.values()):
        st.warning("No data returned. Check API token or try again later.")
        return

    # Sort by count
    sorted_counts=sorted(counts.items(),key=lambda x:-x[1])
    total=sum(v for _,v in sorted_counts) or 1

    # Bar chart — tweet volume
    fig=go.Figure(go.Bar(
        x=[n for n,_ in sorted_counts],
        y=[c for _,c in sorted_counts],
        marker_color=[NARRATIVE_COLORS.get(n,"#6b7280") for n,_ in sorted_counts],
        text=[f"{c:,}" for _,c in sorted_counts],
        textposition="outside",
        hovertemplate="%{x}: %{y:,} tweets<extra></extra>",
    ))
    fig.update_layout(**BASE_LAYOUT,height=300,showlegend=False,
                      xaxis=AXIS,yaxis=AXIS,
                      title=dict(text="Tweet volume by narrative — last 7 days",
                                 font=dict(size=13,color="#E0F5EC"),x=0))
    st.plotly_chart(fig,use_container_width=True)

    # Pie chart — % share
    c1,c2=st.columns([1,1])
    with c1:
        st.markdown('<div class="section-title">Narrative Share %</div>',unsafe_allow_html=True)
        fp=go.Figure(go.Pie(
            labels=[n for n,_ in sorted_counts],
            values=[c for _,c in sorted_counts],
            marker=dict(colors=[NARRATIVE_COLORS.get(n,"#6b7280") for n,_ in sorted_counts],
                        line=dict(color=MANTLE_DARK,width=2)),
            textfont_size=11,hole=0.5,
            hovertemplate="%{label}: %{value:,} tweets (%{percent})<extra></extra>"))
        pl={k:v for k,v in BASE_LAYOUT.items() if k!="margin"}
        fp.update_layout(**pl,height=300,showlegend=True,margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fp,use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">Ranking</div>',unsafe_allow_html=True)
        for rank,(name,cnt) in enumerate(sorted_counts,1):
            c=NARRATIVE_COLORS.get(name,"#666")
            pct=cnt/total*100
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
              <div style="font-size:14px;font-weight:800;color:#555;min-width:20px">#{rank}</div>
              <div style="width:10px;height:10px;border-radius:2px;background:{c};flex-shrink:0"></div>
              <div style="flex:1;font-size:13px;color:{MANTLE_TEXT};font-weight:600">{name}</div>
              <div style="font-size:12px;color:{MANTLE_MUTED}">{cnt:,} tweets</div>
              <div style="width:80px;background:{MANTLE_BORDER};border-radius:4px;height:6px">
                <div style="width:{pct}%;background:{c};border-radius:4px;height:6px"></div>
              </div>
              <div style="font-size:12px;color:{c};font-weight:700;min-width:36px">{pct:.1f}%</div>
            </div>""",unsafe_allow_html=True)

    # Sample top posts per top 3 narratives
    st.markdown('<div class="section-title">Sample Posts — Top 3 Narratives</div>',unsafe_allow_html=True)
    top3=[n for n,_ in sorted_counts[:3]]
    cols=st.columns(3)
    for col,name in zip(cols,top3):
        c=NARRATIVE_COLORS.get(name,"#6b7280")
        tw=sorted(sample_tweets.get(name,[]),key=get_imp,reverse=True)
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:800;color:{c};margin-bottom:10px;text-transform:uppercase;letter-spacing:.08em">{name}</div>',unsafe_allow_html=True)
            if tw:
                for i,t in enumerate(tw[:3],1):
                    render_post(t,i,c,is_user=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No sample posts</div>',unsafe_allow_html=True)

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    token=get_token()
    st.markdown(f"""
    <div class="header-bar">
      <div style="display:flex;align-items:center;gap:14px">
        <div>
          <div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px">Mantle Social Intelligence</div>
          <div style="font-size:12px;color:{MANTLE_MUTED};margin-top:2px;font-weight:500">Mantle · Solana · Base &nbsp;·&nbsp; X API v2</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <span class="live-pill">● Live · {datetime.now().strftime('%H:%M UTC')}</span>
      </div>
    </div>""",unsafe_allow_html=True)

    if not token:
        st.error("Missing TWITTER_BEARER_TOKEN — add in Streamlit → Settings → Secrets")
        st.code('TWITTER_BEARER_TOKEN = "your_token_here"')
        st.stop()

    col_r,_=st.columns([1,8])
    with col_r:
        if st.button("🔄 Refresh",use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    t1,t2,t3=st.tabs(["📊  Mantle Deep Dive","⚔️  Competitive Analysis","🔬  Industry Research"])
    with t1: tab_mantle(token)
    with t2: tab_competitive(token)
    with t3: tab_research(token)

if __name__=="__main__":
    main()
