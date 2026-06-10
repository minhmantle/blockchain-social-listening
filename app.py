import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import time
import re
from collections import Counter

st.set_page_config(
    page_title="Blockchain Social Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #080810; }
.main .block-container { padding: 1.5rem 2rem 3rem; max-width: 1400px; }
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none; }
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #0d0d1a;
    border-bottom: 1px solid #1e1e3a; padding: 0 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 6px 6px 0 0;
    color: #666; font-size: 13px; font-weight: 500;
    padding: 10px 20px; border: none;
}
.stTabs [aria-selected="true"] {
    background: #13132a !important; color: #fff !important;
    border-bottom: 2px solid #7c5cbf !important;
}
.kpi-card {
    background: #0d0d1a; border: 1px solid #1e1e3a;
    border-radius: 12px; padding: 18px 20px;
}
.kpi-label { font-size: 11px; color: #555; text-transform: uppercase;
    letter-spacing: 0.1em; margin-bottom: 8px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }
.kpi-delta-up { font-size: 12px; color: #4ade80; margin-top: 5px; }
.kpi-delta-dn { font-size: 12px; color: #f87171; margin-top: 5px; }
.kpi-neutral { font-size: 12px; color: #666; margin-top: 5px; }
.post-card {
    background: #0d0d1a; border: 1px solid #1e1e3a;
    border-radius: 10px; padding: 16px; margin-bottom: 10px;
}
.post-card:hover { border-color: #2e2e5e; }
.post-meta { font-size: 11px; color: #555; margin-bottom: 4px; }
.post-handle { font-size: 13px; font-weight: 600; color: #e0e0ff; }
.post-text { font-size: 13px; color: #999; line-height: 1.55; margin: 8px 0; }
.post-stats { font-size: 12px; color: #555; }
.chain-badge {
    display: inline-block; font-size: 10px; font-weight: 600;
    padding: 2px 8px; border-radius: 99px; margin-right: 6px;
}
.section-title {
    font-size: 12px; font-weight: 600; color: #555;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin: 20px 0 12px; border-bottom: 1px solid #1e1e3a; padding-bottom: 8px;
}
.narrative-pill {
    display: inline-block; font-size: 11px; padding: 3px 10px;
    border-radius: 99px; margin: 3px; font-weight: 500;
}
.header-bar {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1.5rem; padding-bottom: 1rem;
    border-bottom: 1px solid #1e1e3a;
}
.live-pill {
    background: #0a2e14; color: #4ade80; border: 1px solid #1a5e2a;
    padding: 4px 12px; border-radius: 99px; font-size: 11px; font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

CHAINS = {
    "Mantle":  {"handle": "Mantle_Official", "color": "#7c5cbf", "short": "MNT"},
    "Solana":  {"handle": "solana",           "color": "#9945FF", "short": "SOL"},
    "Base":    {"handle": "base",             "color": "#2563eb", "short": "BASE"},
}

NARRATIVES = {
    "DeFi":           ["defi", "dex", "liquidity", "yield", "swap", "lending", "amm", "tvl", "staking"],
    "RWA":            ["rwa", "real world asset", "tokenized", "tokenisation", "tokenization", "treasury", "bond"],
    "AI":             ["ai", "artificial intelligence", "machine learning", "llm", "agent"],
    "Infrastructure": ["infrastructure", "layer2", "l2", "rollup", "scalability", "tps", "validator", "node"],
    "NFT":            ["nft", "collectible", "mint", "opensea", "marketplace"],
    "Gaming":         ["gaming", "gamefi", "game", "play to earn", "p2e", "metaverse"],
    "Institutional":  ["institution", "institutional", "blackrock", "fidelity", "bank", "fund", "etf",
                       "investment", "hedge fund", "enterprise", "adoption", "corporate"],
}

NARRATIVE_COLORS = {
    "DeFi": "#3b82f6", "RWA": "#f59e0b", "AI": "#8b5cf6",
    "Infrastructure": "#10b981", "NFT": "#ec4899",
    "Gaming": "#f97316", "Institutional": "#06b6d4", "Other": "#6b7280",
}

CHART_LAYOUT = dict(
    paper_bgcolor="#0d0d1a", plot_bgcolor="#0d0d1a",
    font=dict(color="#888", size=11, family="Inter"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
    hovermode="x unified",
    margin=dict(l=10, r=10, t=36, b=10),
)

AXIS_STYLE = dict(gridcolor="#1e1e3a", showgrid=True, zeroline=False, color="#666")

def get_token():
    try:
        return st.secrets["TWITTER_BEARER_TOKEN"]
    except:
        return None

def hdrs(token):
    return {"Authorization": f"Bearer {token}"}

@st.cache_data(ttl=300)
def get_user(handle, token):
    r = requests.get(
        f"https://api.twitter.com/2/users/by/username/{handle}",
        headers=hdrs(token),
        params={"user.fields": "public_metrics,description"}
    )
    return r.json().get("data", {}) if r.status_code == 200 else {}

@st.cache_data(ttl=300)
def get_tweets(user_id, token, start_iso, end_iso, max_results=100):
    params = {
        "max_results": min(max_results, 100),
        "start_time": start_iso,
        "end_time": end_iso,
        "tweet.fields": "public_metrics,created_at,text",
        "exclude": "retweets,replies"
    }
    r = requests.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        headers=hdrs(token), params=params
    )
    return r.json().get("data", []) if r.status_code == 200 else []

@st.cache_data(ttl=300)
def search_tweets(query, token, start_iso, end_iso, max_results=50):
    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "start_time": start_iso,
        "end_time": end_iso,
        "tweet.fields": "public_metrics,created_at,author_id,text",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics"
    }
    r = requests.get(
        "https://api.twitter.com/2/tweets/search/recent",
        headers=hdrs(token), params=params
    )
    if r.status_code != 200:
        return []
    data = r.json()
    tweets = data.get("data", [])
    users  = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    for t in tweets:
        u = users.get(t.get("author_id"), {})
        t["author_name"]      = u.get("name", "Unknown")
        t["author_handle"]    = u.get("username", "unknown")
        t["author_followers"] = u.get("public_metrics", {}).get("followers_count", 0)
    return tweets

def fmt(n):
    if not n: return "0"
    n = int(n)
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:     return f"{n/1_000_000:.1f}M"
    if n >= 1_000:         return f"{n/1_000:.1f}K"
    return str(n)

def eng(m):
    return (m.get("like_count",0) or 0) + \
           (m.get("retweet_count",0) or 0)*3 + \
           (m.get("reply_count",0) or 0)*2

def parse_dt(s):
    for f in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
        try: return datetime.strptime(s, f)
        except: pass
    return datetime.utcnow()

def time_ago(s):
    diff = datetime.utcnow() - parse_dt(s)
    if diff.days >= 1: return f"{diff.days}d ago"
    h = diff.seconds // 3600
    if h >= 1: return f"{h}h ago"
    return f"{diff.seconds//60}m ago"

def detect_narratives(text):
    tl = text.lower()
    found = [n for n, kws in NARRATIVES.items() if any(k in tl for k in kws)]
    return found if found else ["Other"]

def iso_range(start_d, end_d):
    s = datetime.combine(start_d, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
    e = min(
        datetime.combine(end_d, datetime.max.time()),
        datetime.utcnow()
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return s, e

def group_by(tweets, period):
    rows = []
    for t in tweets:
        dt = parse_dt(t["created_at"])
        m  = t.get("public_metrics", {})
        if period == "Day":    key = dt.date()
        elif period == "Week": key = dt.date() - timedelta(days=dt.weekday())
        else:                  key = dt.date().replace(day=1)
        imp = m.get("impression_count") or 0
        if imp == 0:
            imp = eng(m) * 40
        rows.append({"period": key,
                     "likes":       m.get("like_count",0) or 0,
                     "retweets":    m.get("retweet_count",0) or 0,
                     "replies":     m.get("reply_count",0) or 0,
                     "eng_val":     eng(m),
                     "impressions": imp})
    if not rows:
        return pd.DataFrame(columns=["period","likes","retweets","replies","eng_val","impressions"])
    return pd.DataFrame(rows).groupby("period").sum().reset_index().sort_values("period")

def date_controls(pfx):
    # Init defaults in session state
    if f"{pfx}_start_val" not in st.session_state:
        st.session_state[f"{pfx}_start_val"] = date.today() - timedelta(days=7)
    if f"{pfx}_end_val" not in st.session_state:
        st.session_state[f"{pfx}_end_val"] = date.today()

    c1,c2,c3,c4,c5 = st.columns([2,2,1,1,1])
    with c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("7D", key=f"{pfx}_7d", use_container_width=True):
            st.session_state[f"{pfx}_start_val"] = date.today() - timedelta(days=7)
            st.session_state[f"{pfx}_end_val"]   = date.today()
    with c4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("30D", key=f"{pfx}_30d", use_container_width=True):
            st.session_state[f"{pfx}_start_val"] = date.today() - timedelta(days=30)
            st.session_state[f"{pfx}_end_val"]   = date.today()
    with c1:
        start = st.date_input("From",
                               value=st.session_state[f"{pfx}_start_val"],
                               max_value=date.today(), key=f"{pfx}_start")
        st.session_state[f"{pfx}_start_val"] = start
    with c2:
        end = st.date_input("To",
                             value=st.session_state[f"{pfx}_end_val"],
                             max_value=date.today(), key=f"{pfx}_end")
        st.session_state[f"{pfx}_end_val"] = end
    with c5:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        period = st.selectbox("Group by", ["Day","Week","Month"],
                               key=f"{pfx}_period", label_visibility="collapsed")
    return start, end, period

def render_post(t, rank, color, chain_name=None, is_user=False):
    m    = t.get("public_metrics", {})
    text = t.get("text","")
    brief= text[:200] + ("…" if len(text) > 200 else "")
    ev   = eng(m)
    imp  = m.get("impression_count") or ev * 40
    tid  = t.get("id","")
    if is_user:
        handle = t.get("author_handle","unknown")
        name   = t.get("author_name","User")
        followers = t.get("author_followers",0)
    else:
        handle = CHAINS.get(chain_name or "Mantle",{}).get("handle","")
        name   = chain_name or "Official"
        followers = None
    link = f"https://x.com/{handle}/status/{tid}" if tid else "#"
    ago  = time_ago(t.get("created_at",""))
    narrs= detect_narratives(text)
    badge= f'<span class="chain-badge" style="background:{color}22;color:{color};border:1px solid {color}44">{chain_name}</span>' if chain_name else ""
    pills= " ".join([
        f'<span class="narrative-pill" style="background:{NARRATIVE_COLORS.get(n,"#333")}22;color:{NARRATIVE_COLORS.get(n,"#888")};border:1px solid {NARRATIVE_COLORS.get(n,"#333")}44">{n}</span>'
        for n in narrs
    ])
    fstr = f" · {fmt(followers)} followers" if followers else ""
    st.markdown(f"""
    <div class="post-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
        <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0">
          <span style="font-size:16px;font-weight:700;color:#333;min-width:24px">#{rank}</span>
          <div>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              {badge}<span class="post-handle">@{handle}</span>
              <span class="post-meta">{ago}{fstr}</span>
            </div>
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:13px;font-weight:600;color:{color}">{fmt(imp)}</div>
          <div style="font-size:10px;color:#444">impressions</div>
        </div>
      </div>
      <div class="post-text">{brief}</div>
      <div style="margin-bottom:8px">{pills}</div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="post-stats">
          ♥ {fmt(m.get("like_count",0))} &nbsp;·&nbsp;
          ↺ {fmt(m.get("retweet_count",0))} &nbsp;·&nbsp;
          💬 {fmt(m.get("reply_count",0))} &nbsp;·&nbsp;
          <span style="color:#555">eng: {fmt(ev)}</span>
        </div>
        <a href="{link}" target="_blank" style="font-size:11px;color:{color};
           text-decoration:none;padding:4px 12px;border:1px solid {color}44;
           border-radius:6px;white-space:nowrap;background:{color}11">
          View post ↗
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)

def kpi_card(col, label, value, delta=None, sub=None, color="#7c5cbf"):
    d = ""
    if delta is not None:
        cls = "kpi-delta-up" if delta >= 0 else "kpi-delta-dn"
        arrow = "▲" if delta >= 0 else "▼"
        d = f'<div class="{cls}">{arrow} {abs(delta):.1f}% vs prev period</div>'
    elif sub:
        d = f'<div class="kpi-neutral">{sub}</div>'
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color}">{value}</div>
      {d}
    </div>""", unsafe_allow_html=True)

# ── TAB 1 ────────────────────────────────────────────────────────────────────
def tab_mantle(token):
    st.markdown("### Mantle — Performance Deep Dive")
    start, end, period = date_controls("t1")
    start_iso, end_iso = iso_range(start, end)
    days = (end - start).days + 1
    prev_s_iso, prev_e_iso = iso_range(start - timedelta(days=days), start - timedelta(days=1))

    color = CHAINS["Mantle"]["color"]
    handle = CHAINS["Mantle"]["handle"]

    with st.spinner("Fetching Mantle data…"):
        user    = get_user(handle, token)
        uid     = user.get("id","")
        tweets  = get_tweets(uid, token, start_iso, end_iso) if uid else []
        prev_tw = get_tweets(uid, token, prev_s_iso, prev_e_iso) if uid else []

    followers  = user.get("public_metrics",{}).get("followers_count",0) or 0
    total_eng  = sum(eng(t.get("public_metrics",{})) for t in tweets)
    prev_eng   = sum(eng(t.get("public_metrics",{})) for t in prev_tw)
    total_likes= sum(t.get("public_metrics",{}).get("like_count",0) or 0 for t in tweets)
    total_rts  = sum(t.get("public_metrics",{}).get("retweet_count",0) or 0 for t in tweets)
    total_imps = sum(t.get("public_metrics",{}).get("impression_count",0) or 0 for t in tweets)
    post_count = len(tweets)
    prev_posts = len(prev_tw)
    eng_delta  = ((total_eng - prev_eng) / prev_eng * 100) if prev_eng else 0
    post_delta = ((post_count - prev_posts) / prev_posts * 100) if prev_posts else 0
    eng_rate   = round(total_eng / total_imps * 100, 2) if total_imps else 0

    k1,k2,k3,k4,k5 = st.columns(5)
    kpi_card(k1, "Followers",        fmt(followers),    sub="current total",         color=color)
    kpi_card(k2, "Posts published",  str(post_count),   delta=post_delta,            color=color)
    kpi_card(k3, "Total engagement", fmt(total_eng),    delta=eng_delta,             color=color)
    kpi_card(k4, "Total likes",      fmt(total_likes),  sub=f"Retweets: {fmt(total_rts)}", color=color)
    kpi_card(k5, "Eng. rate",        f"{eng_rate:.2f}%",sub="engagement / impressions" if total_imps else "based on interactions", color=color)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    df = group_by(tweets, period)
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["period"], y=df["impressions"],
            name="Impressions", marker_color=color, opacity=0.85,
            hovertemplate="%{x}: %{y:,}<extra>Impressions</extra>"
        ))
        fig.add_trace(go.Scatter(
            x=df["period"], y=df["eng_val"],
            name="Engagement", mode="lines+markers",
            line=dict(color="#f59e0b", width=2), marker=dict(size=5),
            yaxis="y2", hovertemplate="%{x}: %{y:,}<extra>Engagement</extra>"
        ))
        fig.update_layout(
            **CHART_LAYOUT, height=280,
            xaxis=AXIS_STYLE,
            yaxis=dict(**AXIS_STYLE, title="Impressions"),
            yaxis2=dict(title="Engagement", overlaying="y", side="right",
                        showgrid=False, zeroline=False, color="#f59e0b"),
            title=dict(text=f"Impressions & Engagement by {period} — @{handle}",
                       font_size=12, x=0, font_color="#aaa")
        )
        st.plotly_chart(fig, use_container_width=True)

    all_nar = []
    for t in tweets:
        all_nar.extend(detect_narratives(t.get("text","")))
    nar_counts = Counter(all_nar)

    if nar_counts:
        st.markdown('<div class="section-title">Narrative breakdown</div>', unsafe_allow_html=True)
        nc1, nc2 = st.columns([1, 2])
        with nc1:
            labels = list(nar_counts.keys())
            values = list(nar_counts.values())
            colors = [NARRATIVE_COLORS.get(l,"#666") for l in labels]
            fig_pie = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color="#080810", width=2)),
                textfont_size=11, hole=0.55,
                hovertemplate="%{label}: %{value} posts<extra></extra>"
            ))
            pie_layout = {k:v for k,v in CHART_LAYOUT.items() if k not in ("margin","hovermode")}
            fig_pie.update_layout(**pie_layout, height=220, showlegend=False,
                                   margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        with nc2:
            total_n = sum(nar_counts.values()) or 1
            for nm, cnt in sorted(nar_counts.items(), key=lambda x: -x[1]):
                c   = NARRATIVE_COLORS.get(nm,"#666")
                pct = cnt/total_n*100
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                  <div style="width:10px;height:10px;border-radius:2px;background:{c};flex-shrink:0"></div>
                  <div style="flex:1;font-size:13px;color:#ccc">{nm}</div>
                  <div style="font-size:12px;color:#666">{cnt} posts · {pct:.0f}%</div>
                  <div style="width:80px;background:#1e1e3a;border-radius:4px;height:6px">
                    <div style="width:{pct}%;background:{c};border-radius:4px;height:6px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

    sorted_tw = sorted(tweets, key=lambda t: eng(t.get("public_metrics",{})), reverse=True)
    st.markdown('<div class="section-title">Top 5 posts by engagement — Mantle Official</div>',
                unsafe_allow_html=True)
    if sorted_tw:
        for i, t in enumerate(sorted_tw[:5], 1):
            render_post(t, i, color, chain_name="Mantle", is_user=False)
    else:
        st.info("No posts found for this time range.")

    st.markdown('<div class="section-title">Keyword search — Mantle context</div>',
                unsafe_allow_html=True)
    kw = st.text_input("Enter keyword (e.g. RWA, mETH, DeFi…)",
                        placeholder="Type and press Enter", key="t1_kw")
    if kw:
        q = f'("{kw}" (@Mantle_Official OR #Mantle) (blockchain OR crypto OR web3)) OR ("{kw}" #Mantle) -is:retweet lang:en'
        with st.spinner(f"Searching '{kw}'…"):
            results = search_tweets(q, token, start_iso, end_iso, max_results=20)
        st.caption(f"{len(results)} results for **{kw}**")
        for i, t in enumerate(sorted(results, key=lambda t: eng(t.get("public_metrics",{})), reverse=True)[:5], 1):
            render_post(t, i, color, is_user=True)

# ── TAB 2 ────────────────────────────────────────────────────────────────────
def tab_competitive(token):
    st.markdown("### Competitive Analysis — Mantle vs Solana vs Base")
    start, end, period = date_controls("t2")
    start_iso, end_iso = iso_range(start, end)
    days = (end - start).days + 1
    prev_s_iso, prev_e_iso = iso_range(start - timedelta(days=days), start - timedelta(days=1))

    all_data = {}
    with st.spinner("Fetching all chains…"):
        for name, info in CHAINS.items():
            u   = get_user(info["handle"], token)
            uid = u.get("id","")
            tw  = get_tweets(uid, token, start_iso, end_iso) if uid else []
            ptw = get_tweets(uid, token, prev_s_iso, prev_e_iso) if uid else []
            all_data[name] = {"user": u, "tweets": tw, "prev": ptw, "info": info}

    st.markdown('<div class="section-title">Performance snapshot</div>', unsafe_allow_html=True)
    cols = st.columns(len(CHAINS))
    for col, (name, d) in zip(cols, all_data.items()):
        color     = d["info"]["color"]
        followers = d["user"].get("public_metrics",{}).get("followers_count",0) or 0
        total_e   = sum(eng(t.get("public_metrics",{})) for t in d["tweets"])
        prev_e    = sum(eng(t.get("public_metrics",{})) for t in d["prev"])
        delta     = ((total_e - prev_e) / prev_e * 100) if prev_e else 0
        arrow     = "▲" if delta >= 0 else "▼"
        dcls      = "color:#4ade80" if delta >= 0 else "color:#f87171"
        col.markdown(f"""
        <div class="kpi-card">
          <div style="font-size:11px;font-weight:700;color:{color};text-transform:uppercase;
               letter-spacing:.1em;margin-bottom:10px">{name}</div>
          <div style="font-size:11px;color:#555;margin-bottom:2px">Followers</div>
          <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px">{fmt(followers)}</div>
          <div style="font-size:11px;color:#555;margin-bottom:2px">Engagement</div>
          <div style="font-size:18px;font-weight:700;color:{color}">{fmt(total_e)}</div>
          <div style="font-size:12px;{dcls};margin-top:4px">{arrow} {abs(delta):.1f}% vs prev</div>
          <div style="font-size:11px;color:#555;margin-top:8px">{len(d['tweets'])} posts</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    fig = go.Figure()
    for name, d in all_data.items():
        df = group_by(d["tweets"], period)
        if not df.empty:
            fig.add_trace(go.Scatter(
                x=df["period"], y=df["impressions"], name=name,
                mode="lines+markers",
                line=dict(color=d["info"]["color"], width=2),
                marker=dict(size=5),
                hovertemplate=f"{name}: %{{y:,}}<extra></extra>"
            ))
    fig.update_layout(
        **CHART_LAYOUT, height=280,
        xaxis=AXIS_STYLE,
        yaxis=AXIS_STYLE,
        title=dict(text=f"Impressions by {period} — all chains",
                   font_size=12, x=0, font_color="#aaa")
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Top 3 official posts by engagement</div>',
                unsafe_allow_html=True)
    pcols = st.columns(len(CHAINS))
    for col, (name, d) in zip(pcols, all_data.items()):
        color = d["info"]["color"]
        stw   = sorted(d["tweets"], key=lambda t: eng(t.get("public_metrics",{})), reverse=True)
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:600;color:{color};'
                        f'margin-bottom:10px;text-transform:uppercase">{name}</div>',
                        unsafe_allow_html=True)
            if stw:
                for i, t in enumerate(stw[:3], 1):
                    render_post(t, i, color, chain_name=name, is_user=False)
            else:
                st.markdown('<div style="font-size:12px;color:#555">No data</div>',
                            unsafe_allow_html=True)

    st.markdown('<div class="section-title">Top user / KOL mentions — blockchain context only</div>',
                unsafe_allow_html=True)
    BKCHAIN_KW = ["crypto","blockchain","web3","defi","nft","token","chain","onchain",
                  "l2","layer2","wallet","protocol","dao","dapp","eth","btc","sol","bnb"]
    mcols = st.columns(len(CHAINS))
    for col, (name, d) in zip(mcols, all_data.items()):
        color  = d["info"]["color"]
        handle = d["info"]["handle"]
        if name == "Base":
            q = '("@base" OR "#Base" OR "Base blockchain" OR "Base chain" OR "build on Base") (crypto OR blockchain OR web3 OR DeFi OR onchain OR L2) -from:base -is:retweet lang:en'
        else:
            q = f'(@{handle} OR #{name}) (crypto OR blockchain OR web3 OR DeFi OR onchain) -from:{handle} -is:retweet lang:en'
        with st.spinner(f"Fetching {name} mentions…"):
            mentions = search_tweets(q, token, start_iso, end_iso, max_results=30)
        mentions = [t for t in mentions if any(k in t.get("text","").lower() for k in BKCHAIN_KW)]
        sm = sorted(mentions, key=lambda t: eng(t.get("public_metrics",{})), reverse=True)
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:600;color:{color};'
                        f'margin-bottom:10px;text-transform:uppercase">{name} mentions</div>',
                        unsafe_allow_html=True)
            if sm:
                for i, t in enumerate(sm[:3], 1):
                    render_post(t, i, color, chain_name=name, is_user=True)
            else:
                st.markdown('<div style="font-size:12px;color:#555">No mentions found</div>',
                            unsafe_allow_html=True)

    st.markdown('<div class="section-title">Narrative share by chain</div>',
                unsafe_allow_html=True)
    nfig = go.Figure()
    for name, d in all_data.items():
        all_n = []
        for t in d["tweets"]:
            all_n.extend(detect_narratives(t.get("text","")))
        counts = Counter(all_n)
        total  = sum(counts.values()) or 1
        nfig.add_trace(go.Bar(
            name=name,
            x=list(NARRATIVES.keys()) + ["Other"],
            y=[counts.get(k,0)/total*100 for k in list(NARRATIVES.keys())+["Other"]],
            marker_color=d["info"]["color"],
            hovertemplate="%{x}: %{y:.1f}%<extra>" + name + "</extra>"
        ))
    nfig.update_layout(
        **CHART_LAYOUT, barmode="group", height=260,
        xaxis=AXIS_STYLE,
        yaxis=dict(**AXIS_STYLE, ticksuffix="%"),
        title=dict(text="Narrative distribution % by chain", font_size=12, x=0, font_color="#aaa")
    )
    st.plotly_chart(nfig, use_container_width=True)

    st.markdown('<div class="section-title">Keyword search — across all chains</div>',
                unsafe_allow_html=True)
    kw = st.text_input("Search keyword", placeholder="e.g. RWA, institutional, partnership…",
                        key="t2_kw")
    if kw:
        q = f'"{kw}" (Mantle OR Solana OR Base) (blockchain OR crypto OR web3) -is:retweet lang:en'
        with st.spinner(f"Searching '{kw}'…"):
            results = search_tweets(q, token, start_iso, end_iso, max_results=30)
        st.caption(f"{len(results)} results for **{kw}**")
        for i, t in enumerate(sorted(results, key=lambda t: eng(t.get("public_metrics",{})), reverse=True)[:6], 1):
            render_post(t, i, "#7c5cbf", is_user=True)

# ── TAB 3 ────────────────────────────────────────────────────────────────────
def tab_industry(token):
    st.markdown("### Industry Overview — Blockchain Twitter Pulse")
    c1, c2 = st.columns([4, 1])
    with c1:
        start, end, _ = date_controls("t3")
    with c2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        kw = st.text_input("Filter by keyword", placeholder="e.g. RWA, AI…", key="t3_kw")

    start_iso, end_iso = iso_range(start, end)
    base_terms = "(blockchain OR crypto OR web3 OR DeFi OR L2 OR layer2 OR onchain)"
    q = f'"{kw}" {base_terms} -is:retweet lang:en' if kw else \
        f'{base_terms} (Mantle OR Solana OR Base OR Ethereum OR Arbitrum) -is:retweet lang:en'

    with st.spinner("Fetching industry data…"):
        industry = search_tweets(q, token, start_iso, end_iso, max_results=100)

    st.caption(f"Analysing {len(industry)} posts")

    if not industry:
        st.info("No data found. Try widening the date range.")
        return

    all_nar = []
    for t in industry:
        all_nar.extend(detect_narratives(t.get("text","")))
    nar_counts = Counter(all_nar)
    nar_counts.pop("Other", None)

    if nar_counts:
        st.markdown('<div class="section-title">Narrative trends — post volume</div>',
                    unsafe_allow_html=True)
        nc1, nc2 = st.columns([2, 1])
        with nc1:
            sn = sorted(nar_counts.items(), key=lambda x: -x[1])
            fb = go.Figure(go.Bar(
                x=[n for n,_ in sn], y=[c for _,c in sn],
                marker_color=[NARRATIVE_COLORS.get(n,"#666") for n,_ in sn],
                hovertemplate="%{x}: %{y} posts<extra></extra>"
            ))
            fb.update_layout(
                **CHART_LAYOUT, height=220, showlegend=False,
                xaxis=AXIS_STYLE,
                yaxis=AXIS_STYLE,
                title=dict(text="Posts by narrative", font_size=12, x=0, font_color="#aaa")
            )
            st.plotly_chart(fb, use_container_width=True)
        with nc2:
            total_n = sum(nar_counts.values()) or 1
            for nm, cnt in sorted(nar_counts.items(), key=lambda x: -x[1])[:6]:
                c = NARRATIVE_COLORS.get(nm,"#666")
                pct = cnt/total_n*100
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                  <div style="width:8px;height:8px;border-radius:2px;background:{c}"></div>
                  <div style="flex:1;font-size:12px;color:#ccc">{nm}</div>
                  <div style="font-size:11px;color:#666">{cnt} · {pct:.0f}%</div>
                </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Top content by engagement — industry wide</div>',
                unsafe_allow_html=True)
    sorted_all = sorted(industry, key=lambda t: eng(t.get("public_metrics",{})), reverse=True)
    for i, t in enumerate(sorted_all[:8], 1):
        tl = t.get("text","").lower()
        if "mantle" in tl:
            c, cn = CHAINS["Mantle"]["color"], "Mantle"
        elif "solana" in tl or "@solana" in tl:
            c, cn = CHAINS["Solana"]["color"], "Solana"
        elif "base" in tl and any(k in tl for k in ["blockchain","l2","onchain","coinbase"]):
            c, cn = CHAINS["Base"]["color"], "Base"
        else:
            c, cn = "#6b7280", None
        render_post(t, i, c, chain_name=cn, is_user=True)

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    token = get_token()
    st.markdown(f"""
    <div class="header-bar">
      <div>
        <div style="font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.3px">
          📡 Blockchain Social Intelligence
        </div>
        <div style="font-size:12px;color:#555;margin-top:2px">
          Mantle · Solana · Base &nbsp;·&nbsp; X API v2 &nbsp;·&nbsp; Real-time
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <span class="live-pill">● Live · {datetime.now().strftime('%H:%M UTC')}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not token:
        st.error("Missing TWITTER_BEARER_TOKEN — add in Streamlit → Settings → Secrets")
        st.code('TWITTER_BEARER_TOKEN = "your_token_here"')
        st.stop()

    col_r, _ = st.columns([1, 6])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    t1, t2, t3 = st.tabs([
        "📊  Mantle Deep Dive",
        "⚔️  Competitive Analysis",
        "🌐  Industry Overview",
    ])
    with t1: tab_mantle(token)
    with t2: tab_competitive(token)
    with t3: tab_industry(token)

if __name__ == "__main__":
    main()
