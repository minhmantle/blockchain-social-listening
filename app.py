import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from collections import Counter
import re

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
    "Ondo":    "#FF6B35",
}

CHAIN_HANDLES = {
    "Mantle": "Mantle_Official",
    "Solana": "solana",
    "Base":   "base",
    "Ondo":   "OndoFinance",
}

NARRATIVES = {
    "RWA":           ["rwa","real world asset","real-world asset","tokenized asset","tokenized bond",
                      "tokenization","tokenise","tokenize","treasury","t-bill","t-bond","tbill",
                      "ondo","usdy","ousg","blackrock buidl","security token","tokenized fund",
                      "on-chain treasury","on-chain yield","institutional yield","real asset"],
    "DeFi":          ["defi","dex","liquidity","yield","swap","lending","amm","tvl","staking",
                      "vault","protocol","borrow","collateral","perpetual","perp","margin"],
    "AI":            ["ai","artificial intelligence","machine learning","llm","agent","gpt",
                      "ai agent","inference","model","neural","openai","claude","gemini"],
    "Infrastructure":["infrastructure","layer2","l2","rollup","scalability","tps","validator",
                      "node","zk","zkp","zkvm","op stack","sequencer","data availability","da",
                      "modular","restaking","eigenlayer","avs","interop","bridge"],
    "Institutional": ["institution","institutional","blackrock","fidelity","bank","fund","etf",
                      "investment","hedge fund","enterprise","corporate","adoption","tradfi",
                      "regulated","compliance","custody","prime broker","asset manager"],
    "NFT":           ["nft","collectible","mint","opensea","marketplace","pfp","digital art"],
    "Gaming":        ["gaming","gamefi","game","play to earn","p2e","metaverse","onchain game"],
}

NARRATIVE_COLORS = {
    "RWA":"#f59e0b","DeFi":"#3b82f6","AI":"#8b5cf6",
    "Infrastructure":"#10b981","Institutional":"#06b6d4",
    "NFT":"#ec4899","Gaming":"#f97316","Other":"#6b7280",
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

RESEARCH_KW = [
    "research","analysis","report","thread","deep dive","breakdown",
    "insight","data","metrics","onchain","on-chain","study","findings",
    "trends","outlook","review","alpha","thesis","framework","explained",
    "chart","graph","stat","billion","million","growth","decline","market","protocol",
]

RESEARCH_ACCOUNTS = ["a16zcrypto","MessariCrypto","TheBlockCo","Delphi_Digital","glassnode"]

STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","by","from",
    "is","are","was","were","be","been","have","has","had","do","does","did","will",
    "would","could","should","may","might","this","that","these","those","it","its",
    "we","our","you","your","they","their","he","she","his","her","i","my","me","us",
    "not","no","so","if","as","up","out","about","into","than","then","when","where",
    "who","how","what","which","all","just","can","new","more","also","get","got",
    "via","amp","rt","https","http","co","t","s","re","ll","ve","d","m",
    "twitter","tweet","like","follow","check","see","one","two","three","going",
    "now","today","yesterday","week","month","year","next","last","first",
}

ALERT_THRESHOLDS = {
    "views_spike": 500_000,
    "eng_spike": 5_000,
}

def get_anthropic_key():
    try: return st.secrets["ANTHROPIC_API_KEY"]
    except: return None

@st.cache_data(ttl=1800)
def ai_content_summary(chain_name, tweets_text_list, anthropic_key):
    """Call Claude API to summarize content themes and narratives"""
    if not anthropic_key or not tweets_text_list:
        return None
    sample = tweets_text_list[:30]
    combined = "\n---\n".join(sample)
    prompt = f"""Analyze these {len(sample)} tweets from {chain_name}'s official account.

TWEETS:
{combined}

Provide a concise analysis in this exact JSON format:
{{
  "main_themes": ["theme1", "theme2", "theme3"],
  "top_narrative": "name of dominant narrative",
  "top_narrative_reason": "1-2 sentences explaining why this narrative dominates",
  "content_summary": "2-3 sentences summarizing overall content strategy and topics",
  "high_attention_topic": "the specific topic/announcement that got most engagement",
  "high_attention_reason": "1-2 sentences explaining why it resonated"
}}

Respond with JSON only, no markdown, no extra text."""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if r.status_code == 200:
            import json
            text = r.json()["content"][0]["text"]
            return json.loads(text)
    except:
        pass
    return None

def get_token():
    try: return st.secrets["TWITTER_BEARER_TOKEN"]
    except: return None

def hdrs(t): return {"Authorization": f"Bearer {t}"}

@st.cache_data(ttl=600)
def get_user(handle, token):
    r = requests.get(f"https://api.twitter.com/2/users/by/username/{handle}",
        headers=hdrs(token), params={"user.fields": "public_metrics,description"})
    return r.json().get("data", {}) if r.status_code == 200 else {}

@st.cache_data(ttl=600)
def get_tweets(uid, token, start_iso, end_iso, max_results=100):
    params = {"max_results": min(max_results, 100), "start_time": start_iso, "end_time": end_iso,
              "tweet.fields": "public_metrics,created_at,text",
              "exclude": "retweets,replies"}
    r = requests.get(f"https://api.twitter.com/2/users/{uid}/tweets", headers=hdrs(token), params=params)
    if r.status_code != 200: return []
    return r.json().get("data", []) or []

@st.cache_data(ttl=600)
def search_tweets(query, token, start_iso, end_iso, max_results=50):
    params = {"query": query, "max_results": min(max_results, 100),
              "start_time": start_iso, "end_time": end_iso,
              "tweet.fields": "public_metrics,created_at,author_id,text",
              "expansions": "author_id", "user.fields": "username,name,public_metrics"}
    r = requests.get("https://api.twitter.com/2/tweets/search/recent", headers=hdrs(token), params=params)
    if r.status_code != 200: return []
    data = r.json()
    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    for t in tweets:
        u = users.get(t.get("author_id"), {})
        t["author_name"] = u.get("name", "Unknown")
        t["author_handle"] = u.get("username", "unknown")
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
    return (m.get("like_count",0) or 0) + (m.get("retweet_count",0) or 0)*3 + (m.get("reply_count",0) or 0)*2

def get_imp(t):
    m = t.get("public_metrics", {})
    v = m.get("impression_count") or 0
    if v > 0: return v
    return eng(m) * 100

def parse_dt(s):
    for f in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
        try: return datetime.strptime(s, f)
        except: pass
    return datetime.utcnow()

def time_ago(s):
    d = datetime.utcnow() - parse_dt(s)
    if d.days >= 1: return f"{d.days}d ago"
    h = d.seconds // 3600
    if h >= 1: return f"{h}h ago"
    return f"{d.seconds//60}m ago"

def detect_nar(text):
    tl = text.lower()
    found = [n for n, kws in NARRATIVES.items() if any(k in tl for k in kws)]
    return found if found else ["Other"]

def iso_range(s, e):
    si = datetime.combine(s, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
    ei = min(datetime.combine(e, datetime.max.time()), datetime.utcnow()-timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return si, ei

def search_iso():
    e = datetime.utcnow() - timedelta(seconds=30)
    s = e - timedelta(days=6)
    return s.strftime("%Y-%m-%dT%H:%M:%SZ"), e.strftime("%Y-%m-%dT%H:%M:%SZ")

def group_by(tweets, period):
    rows = []
    for t in tweets:
        dt = parse_dt(t["created_at"])
        m = t.get("public_metrics", {})
        if period == "Day": key = dt.date()
        elif period == "Week": key = dt.date() - timedelta(days=dt.weekday())
        else: key = dt.date().replace(day=1)
        rows.append({"period": key, "likes": m.get("like_count",0) or 0,
                     "retweets": m.get("retweet_count",0) or 0,
                     "replies": m.get("reply_count",0) or 0,
                     "eng_val": eng(m), "impressions": get_imp(t)})
    if not rows:
        return pd.DataFrame(columns=["period","likes","retweets","replies","eng_val","impressions"])
    return pd.DataFrame(rows).groupby("period").sum().reset_index().sort_values("period")

def date_controls(pfx):
    if f"{pfx}_sv" not in st.session_state:
        st.session_state[f"{pfx}_sv"] = date.today() - timedelta(days=7)
    if f"{pfx}_ev" not in st.session_state:
        st.session_state[f"{pfx}_ev"] = date.today()
    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        start = st.date_input("From", value=st.session_state[f"{pfx}_sv"], max_value=date.today(), key=f"{pfx}_s")
        st.session_state[f"{pfx}_sv"] = start
    with c2:
        end = st.date_input("To", value=st.session_state[f"{pfx}_ev"], max_value=date.today(), key=f"{pfx}_e")
        st.session_state[f"{pfx}_ev"] = end
    with c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        period = st.selectbox("Group by", ["Day","Week","Month"], key=f"{pfx}_p", label_visibility="collapsed")
    return start, end, period

def kpi(col, label, value, delta=None, sub=None, color=MANTLE_GREEN):
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

def render_post(t, rank, color, chain_name=None, is_user=False):
    m = t.get("public_metrics", {})
    text = t.get("text", "")
    brief = text[:200] + ("…" if len(text) > 200 else "")
    imp = get_imp(t)
    tid = t.get("id", "")
    if is_user:
        handle = t.get("author_handle", "unknown")
        followers = t.get("author_followers", 0)
    else:
        handle = {"Mantle":"Mantle_Official","Solana":"solana","Base":"base"}.get(chain_name, "")
        followers = None
    link = f"https://x.com/{handle}/status/{tid}" if tid else "#"
    ago = time_ago(t.get("created_at", ""))
    narrs = detect_nar(text)
    badge = f'<span class="narrative-pill" style="background:{color}22;color:{color};border:1px solid {color}44;font-size:10px;padding:2px 8px;border-radius:99px">{chain_name}</span>' if chain_name else ""
    pills = " ".join([f'<span class="narrative-pill" style="background:{NARRATIVE_COLORS.get(n,"#333")}22;color:{NARRATIVE_COLORS.get(n,"#888")};border:1px solid {NARRATIVE_COLORS.get(n,"#333")}33">{n}</span>' for n in narrs])
    fstr = f" · {fmt(followers)} followers" if followers else ""
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
    </div>""", unsafe_allow_html=True)

def tab_description(title, description, accounts, data_range):
    accounts_str = " &nbsp;·&nbsp; ".join([f"<b>@{a}</b>" for a in accounts])
    st.markdown(f"""
    <div class="tab-desc">
      <div class="tab-desc-title">{title}</div>
      <div class="tab-desc-body">
        {description}<br>
        <span style="margin-top:4px;display:block">📡 <b>Sources:</b> {accounts_str}</span>
        <span>📅 <b>Data range:</b> {data_range}</span>
      </div>
    </div>""", unsafe_allow_html=True)

def split_top_posts(tweets, n=5):
    by_views = sorted(tweets, key=get_imp, reverse=True)
    top_views = by_views[:n]
    views_ids = {t.get("id") for t in top_views}
    remaining = [t for t in tweets if t.get("id") not in views_ids]
    top_eng = sorted(remaining, key=lambda t: eng(t.get("public_metrics",{})), reverse=True)[:n]
    return top_views, top_eng

# ── FEATURE: ALERTS ───────────────────────────────────────────────────────────
def check_alerts(tweets, chain_name="Mantle"):
    alerts = []
    for t in tweets:
        imp = get_imp(t)
        eng_val = eng(t.get("public_metrics", {}))
        if imp >= ALERT_THRESHOLDS["views_spike"]:
            alerts.append(("views", t, imp))
        elif eng_val >= ALERT_THRESHOLDS["eng_spike"]:
            alerts.append(("eng", t, eng_val))
    return alerts

def render_alerts(alerts, chain_name, color):
    if not alerts:
        return
    st.markdown(f"""
    <div style="background:#1a0a00;border:1px solid #f59e0b44;border-radius:10px;padding:12px 16px;margin-bottom:12px">
      <div style="font-size:12px;font-weight:800;color:#f59e0b;margin-bottom:8px">
        🔔 {len(alerts)} HIGH-PERFORMANCE POST{'S' if len(alerts)>1 else ''} DETECTED — {chain_name.upper()}
      </div>""", unsafe_allow_html=True)
    for alert_type, t, val in alerts[:3]:
        text = t.get("text","")[:120] + "…"
        metric = f"{fmt(val)} views" if alert_type == "views" else f"{fmt(val)} engagement"
        tid = t.get("id","")
        handle = {"Mantle":"Mantle_Official","Solana":"solana","Base":"base"}.get(chain_name, chain_name)
        link = f"https://x.com/{handle}/status/{tid}"
        st.markdown(f"""
      <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:6px;padding:8px;background:{MANTLE_SURFACE};border-radius:6px">
        <span style="color:#f59e0b;font-weight:700">{metric}</span> &nbsp;·&nbsp;
        <span style="color:{MANTLE_TEXT}">{text}</span>
        <a href="{link}" target="_blank" style="color:#f59e0b;margin-left:8px;font-weight:600">View ↗</a>
      </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── FEATURE: COMPETITOR GAP ANALYSIS ─────────────────────────────────────────
def render_gap_analysis(all_data):
    st.markdown('<div class="section-title">Competitor Gap Analysis</div>', unsafe_allow_html=True)
    mantle = all_data.get("Mantle", {})
    m_views = sum(get_imp(t) for t in mantle.get("tweets", []))
    m_posts = len(mantle.get("tweets", []))
    m_eng = sum(eng(t.get("public_metrics",{})) for t in mantle.get("tweets", []))
    m_eng_rate = round(m_eng / m_views * 100, 2) if m_views else 0

    insights = []
    for name, d in all_data.items():
        if name == "Mantle": continue
        c_views = sum(get_imp(t) for t in d.get("tweets", []))
        c_posts = len(d.get("tweets", []))
        c_eng = sum(eng(t.get("public_metrics",{})) for t in d.get("tweets", []))
        c_eng_rate = round(c_eng / c_views * 100, 2) if c_views else 0
        color = d["color"]

        if c_views > 0 and m_views > 0:
            ratio = c_views / m_views
            if ratio > 1:
                insights.append((color, name, f"<b>{name}</b> đạt <b>{fmt(c_views)}</b> views vs Mantle <b>{fmt(m_views)}</b> — gấp <b>{ratio:.1f}x</b>. Mantle cần tăng tần suất hoặc chất lượng content."))
            else:
                insights.append((MANTLE_GREEN, "Mantle", f"Mantle outperform <b>{name}</b> về views: <b>{fmt(m_views)}</b> vs <b>{fmt(c_views)}</b> — dẫn <b>{1/ratio:.1f}x</b>."))

        if c_eng_rate > 0 and m_eng_rate > 0:
            if m_eng_rate > c_eng_rate:
                insights.append((MANTLE_GREEN, "Mantle", f"Mantle có engagement rate cao hơn <b>{name}</b>: <b>{m_eng_rate:.2f}%</b> vs <b>{c_eng_rate:.2f}%</b> — community Mantle engage tốt hơn."))
            else:
                diff = c_eng_rate - m_eng_rate
                insights.append((color, name, f"<b>{name}</b> có engagement rate cao hơn Mantle <b>{diff:.2f}%</b>. Nghiên cứu content format của {name} để tối ưu."))

        # narrative gap
        m_nar = Counter()
        for t in mantle.get("tweets", []): m_nar.update(detect_nar(t.get("text","")))
        c_nar = Counter()
        for t in d.get("tweets", []): c_nar.update(detect_nar(t.get("text","")))
        m_total = sum(m_nar.values()) or 1
        c_total = sum(c_nar.values()) or 1
        for nar in NARRATIVES:
            m_pct = m_nar.get(nar, 0) / m_total * 100
            c_pct = c_nar.get(nar, 0) / c_total * 100
            if c_pct - m_pct > 15:
                insights.append((color, name, f"<b>{name}</b> đang nói về <b>{nar}</b> nhiều hơn Mantle ({c_pct:.0f}% vs {m_pct:.0f}%). Đây là narrative gap Mantle có thể khai thác."))
                break

    if not insights:
        st.info("Not enough data for gap analysis. Try a wider date range.")
        return

    for color, source, text in insights[:5]:
        st.markdown(f"""
        <div style="display:flex;gap:10px;align-items:flex-start;background:{MANTLE_SURFACE};
             border:1px solid {color}33;border-left:3px solid {color};
             border-radius:8px;padding:12px 14px;margin-bottom:8px">
          <div style="font-size:18px;flex-shrink:0">💡</div>
          <div style="font-size:12px;color:{MANTLE_TEXT};line-height:1.6">{text}</div>
        </div>""", unsafe_allow_html=True)

# ── FEATURE: EXPORT HTML REPORT ───────────────────────────────────────────────
def generate_report(tab_name, date_range, kpis, top_posts, narratives):
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    posts_html = ""
    for i, t in enumerate(top_posts[:10], 1):
        m = t.get("public_metrics", {})
        text = t.get("text", "")[:200]
        handle = t.get("author_handle", "") or {"Mantle":"Mantle_Official","Solana":"solana","Base":"base"}.get(t.get("chain",""), "")
        tid = t.get("id","")
        link = f"https://x.com/{handle}/status/{tid}"
        posts_html += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#666;font-size:12px">#{i}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px">@{handle}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px">{text}…</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px;text-align:right">{fmt(get_imp(t))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px;text-align:right">{fmt(m.get("like_count",0))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px"><a href="{link}" target="_blank">View</a></td>
        </tr>"""

    kpi_html = "".join([f'<div style="display:inline-block;background:#f8f9fa;border-radius:8px;padding:12px 20px;margin:6px;text-align:center"><div style="font-size:11px;color:#999;text-transform:uppercase">{k}</div><div style="font-size:22px;font-weight:800;color:#00D395">{v}</div></div>' for k, v in kpis.items()])

    nar_html = "".join([f'<span style="display:inline-block;background:{NARRATIVE_COLORS.get(n,"#666")}22;color:{NARRATIVE_COLORS.get(n,"#666")};border:1px solid {NARRATIVE_COLORS.get(n,"#666")}44;padding:4px 12px;border-radius:99px;margin:3px;font-size:12px;font-weight:600">{n}: {c}</span>' for n, c in sorted(narratives.items(), key=lambda x:-x[1])[:8]])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Mantle Social Intelligence Report — {now}</title>
<style>
  body{{font-family:'Inter',sans-serif;max-width:900px;margin:0 auto;padding:32px;color:#1a1a1a;}}
  h1{{color:#00D395;font-size:24px;margin-bottom:4px;}}
  h2{{color:#333;font-size:16px;margin:24px 0 12px;border-bottom:2px solid #00D39522;padding-bottom:6px;}}
  .meta{{color:#999;font-size:12px;margin-bottom:24px;}}
  table{{width:100%;border-collapse:collapse;}}
  th{{background:#f8f9fa;padding:8px;text-align:left;font-size:11px;text-transform:uppercase;color:#999;}}
</style></head>
<body>
<h1>Mantle Social Intelligence</h1>
<div class="meta">Report: {tab_name} &nbsp;·&nbsp; Period: {date_range} &nbsp;·&nbsp; Generated: {now}</div>
<h2>Key Metrics</h2>
{kpi_html}
<h2>Narrative Breakdown</h2>
{nar_html}
<h2>Top Posts by Views</h2>
<table>
  <tr><th>#</th><th>Account</th><th>Content</th><th>Views</th><th>Likes</th><th>Link</th></tr>
  {posts_html}
</table>
</body></html>"""
    return html


# ── CSS ───────────────────────────────────────────────────────────────────────
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
.tab-desc{{background:#0A1F10;border:1px solid {MANTLE_BORDER};border-radius:10px;padding:14px 18px;margin-bottom:16px;}}
.tab-desc-title{{font-size:13px;font-weight:700;color:{MANTLE_GREEN};margin-bottom:6px;}}
.tab-desc-body{{font-size:12px;color:{MANTLE_MUTED};line-height:1.6;}}
.tab-desc-body b{{color:{MANTLE_TEXT};}}
</style>
""", unsafe_allow_html=True)


# ── TAB 1 ────────────────────────────────────────────────────────────────────
def tab_mantle(token):
    tab_description(
        "Mantle — Performance Deep Dive",
        "Tracks all original posts from the official Mantle account. Shows impressions, engagement trends, narrative breakdown, trending topics, and top-performing content.",
        ["Mantle_Official"],
        "Custom date range (user-selected)"
    )
    start, end, period = date_controls("t1")
    start_iso, end_iso = iso_range(start, end)
    days = (end - start).days + 1
    prev_s_iso, prev_e_iso = iso_range(start - timedelta(days=days), start - timedelta(days=1))

    with st.spinner("Fetching Mantle data…"):
        user = get_user("Mantle_Official", token)
        uid = user.get("id", "")
        tweets = get_tweets(uid, token, start_iso, end_iso) if uid else []
        prev_tw = get_tweets(uid, token, prev_s_iso, prev_e_iso) if uid else []

    followers = user.get("public_metrics", {}).get("followers_count", 0) or 0
    total_eng = sum(eng(t.get("public_metrics",{})) for t in tweets)
    total_likes = sum(t.get("public_metrics",{}).get("like_count",0) or 0 for t in tweets)
    total_rts = sum(t.get("public_metrics",{}).get("retweet_count",0) or 0 for t in tweets)
    total_views = sum(get_imp(t) for t in tweets)
    post_count = len(tweets)
    prev_posts = len(prev_tw)
    post_delta = ((post_count - prev_posts) / prev_posts * 100) if prev_posts else 0
    prev_views = sum(get_imp(t) for t in prev_tw)
    view_delta = ((total_views - prev_views) / prev_views * 100) if prev_views else 0
    eng_rate = round(total_eng / total_views * 100, 2) if total_views else 0

    # Alerts
    alerts = check_alerts(tweets, "Mantle")
    if alerts:
        render_alerts(alerts, "Mantle", MANTLE_GREEN)

    k1,k2,k3,k4,k5 = st.columns(5)
    kpi(k1, "Followers", fmt(followers), sub="current total")
    kpi(k2, "Posts published", str(post_count), delta=post_delta)
    kpi(k3, "Total views", fmt(total_views), delta=view_delta)
    kpi(k4, "Total likes", fmt(total_likes), sub=f"Retweets: {fmt(total_rts)}")
    kpi(k5, "Eng. rate", f"{eng_rate:.2f}%", sub="engagement / views")

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    df = group_by(tweets, period)
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["period"], y=df["impressions"], name="Views",
                             marker_color=MANTLE_GREEN, opacity=0.8,
                             hovertemplate="%{x}: %{y:,}<extra>Views</extra>"))
        fig.add_trace(go.Scatter(x=df["period"], y=df["eng_val"], name="Engagement",
                                 mode="lines+markers", yaxis="y2",
                                 line=dict(color="#f59e0b", width=2), marker=dict(size=5),
                                 hovertemplate="%{x}: %{y:,}<extra>Engagement</extra>"))
        fig.update_layout(**BASE_LAYOUT, height=280,
                          xaxis=AXIS,
                          yaxis=dict(**AXIS, title="Views"),
                          yaxis2=dict(title=dict(text="Engagement", font=dict(color="#f59e0b")),
                                      overlaying="y", side="right", showgrid=False, zeroline=False,
                                      tickfont=dict(color="#f59e0b")),
                          title=dict(text=f"Views & Engagement by {period} — @Mantle_Official",
                                     font=dict(size=13, color="#E0F5EC"), x=0))
        st.plotly_chart(fig, use_container_width=True)

    # Narrative breakdown
    all_nar = []
    for t in tweets: all_nar.extend(detect_nar(t.get("text","")))
    nar_counts = Counter(all_nar)
    if nar_counts:
        st.markdown('<div class="section-title">Narrative Breakdown</div>', unsafe_allow_html=True)
        nc1, nc2 = st.columns([1,2])
        with nc1:
            labels = list(nar_counts.keys())
            values = list(nar_counts.values())
            colors = [NARRATIVE_COLORS.get(l,"#666") for l in labels]
            fp = go.Figure(go.Pie(labels=labels, values=values,
                                  marker=dict(colors=colors, line=dict(color=MANTLE_DARK, width=2)),
                                  textfont_size=11, hole=0.55,
                                  hovertemplate="%{label}: %{value} posts<extra></extra>"))
            pl = {k:v for k,v in BASE_LAYOUT.items() if k != "margin"}
            fp.update_layout(**pl, height=220, showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fp, use_container_width=True)
        with nc2:
            total_n = sum(nar_counts.values()) or 1
            for nm, cnt in sorted(nar_counts.items(), key=lambda x:-x[1]):
                c = NARRATIVE_COLORS.get(nm, "#666")
                pct = cnt / total_n * 100
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                  <div style="width:10px;height:10px;border-radius:2px;background:{c};flex-shrink:0"></div>
                  <div style="flex:1;font-size:13px;color:{MANTLE_TEXT};font-weight:500">{nm}</div>
                  <div style="font-size:12px;color:{MANTLE_MUTED}">{cnt} posts · {pct:.0f}%</div>
                  <div style="width:80px;background:{MANTLE_BORDER};border-radius:4px;height:6px">
                    <div style="width:{pct}%;background:{c};border-radius:4px;height:6px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

    # Top posts split
    top_views, top_eng_list = split_top_posts(tweets, n=5)
    st.markdown('<div class="section-title">Top Posts</div>', unsafe_allow_html=True)
    col_v, col_e = st.columns(2)
    with col_v:
        st.markdown(f'<div style="font-size:12px;font-weight:800;color:{MANTLE_GREEN};margin-bottom:10px;text-transform:uppercase;letter-spacing:.08em">👁 Top 5 by Views</div>', unsafe_allow_html=True)
        if top_views:
            for i, t in enumerate(top_views, 1):
                render_post(t, i, MANTLE_GREEN, chain_name="Mantle", is_user=False)
        else:
            st.info("No posts found.")
    with col_e:
        st.markdown(f'<div style="font-size:12px;font-weight:800;color:#f59e0b;margin-bottom:10px;text-transform:uppercase;letter-spacing:.08em">⚡ Top 5 by Engagement</div>', unsafe_allow_html=True)
        if top_eng_list:
            for i, t in enumerate(top_eng_list, 1):
                render_post(t, i, "#f59e0b", chain_name="Mantle", is_user=False)
        else:
            st.info("No additional posts.")

    # Export report
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    if st.button("📥 Download HTML Report — Mantle", key="export_t1"):
        html = generate_report(
            "Mantle Deep Dive",
            f"{start} to {end}",
            {"Followers": fmt(followers), "Posts": str(post_count),
             "Total Views": fmt(total_views), "Eng. Rate": f"{eng_rate:.2f}%"},
            tweets,
            nar_counts
        )
        st.download_button("💾 Save Report", html, file_name=f"mantle_report_{start}_{end}.html",
                           mime="text/html", key="dl_t1")


# ── TAB 2 ────────────────────────────────────────────────────────────────────
def tab_competitive(token):
    tab_description(
        "Competitive Analysis — Mantle vs Solana vs Base vs Ondo",
        "Compares official post performance across 4 chains side by side. Includes AI content summary, gap analysis, narrative breakdown per chain, and top KOL mentions.",
        ["Mantle_Official","solana","base","OndoFinance"],
        "Official posts: custom date range · KOL mentions: last 7 days"
    )
    start, end, period = date_controls("t2")
    start_iso, end_iso = iso_range(start, end)
    days = (end - start).days + 1
    prev_s_iso, prev_e_iso = iso_range(start - timedelta(days=days), start - timedelta(days=1))
    si7, ei7 = search_iso()
    anthropic_key = get_anthropic_key()

    all_data = {}
    with st.spinner("Fetching all chains…"):
        for name, color in CHAIN_COLORS.items():
            handle = CHAIN_HANDLES[name]
            u = get_user(handle, token)
            uid = u.get("id", "")
            tw = get_tweets(uid, token, start_iso, end_iso) if uid else []
            ptw = get_tweets(uid, token, prev_s_iso, prev_e_iso) if uid else []
            all_data[name] = {"user":u, "tweets":tw, "prev":ptw, "color":color, "handle":handle}

    # Alerts
    for name, d in all_data.items():
        alerts = check_alerts(d["tweets"], name)
        if alerts:
            render_alerts(alerts, name, d["color"])

    # KPI snapshot
    st.markdown('<div class="section-title">Performance Snapshot</div>', unsafe_allow_html=True)
    cols = st.columns(len(CHAIN_COLORS))
    for col, (name, d) in zip(cols, all_data.items()):
        color = d["color"]
        followers = d["user"].get("public_metrics",{}).get("followers_count",0) or 0
        total_v = sum(get_imp(t) for t in d["tweets"])
        prev_v = sum(get_imp(t) for t in d["prev"])
        delta = ((total_v - prev_v) / prev_v * 100) if prev_v else 0
        arrow = "▲" if delta >= 0 else "▼"
        dcls = f"color:{MANTLE_GREEN}" if delta >= 0 else "color:#f87171"
        col.markdown(f"""
        <div class="kpi-card">
          <div style="font-size:12px;font-weight:800;color:{color};text-transform:uppercase;letter-spacing:.1em;margin-bottom:12px">{name}</div>
          <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:2px">Followers</div>
          <div style="font-size:20px;font-weight:800;color:#fff;margin-bottom:10px">{fmt(followers)}</div>
          <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:2px">Total views</div>
          <div style="font-size:20px;font-weight:800;color:{color}">{fmt(total_v)}</div>
          <div style="font-size:12px;{dcls};margin-top:4px;font-weight:600">{arrow} {abs(delta):.1f}% vs prev</div>
          <div style="font-size:11px;color:{MANTLE_MUTED};margin-top:8px">{len(d['tweets'])} posts</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    # ── AI Content Summary ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🤖 AI Content Analysis</div>', unsafe_allow_html=True)
    if not anthropic_key:
        st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets to enable AI analysis.")
    else:
        ai_cols = st.columns(len(CHAIN_COLORS))
        for col, (name, d) in zip(ai_cols, all_data.items()):
            color = d["color"]
            with col:
                st.markdown(f'<div style="font-size:12px;font-weight:800;color:{color};margin-bottom:8px;text-transform:uppercase">{name}</div>', unsafe_allow_html=True)
                if not d["tweets"]:
                    st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No data</div>', unsafe_allow_html=True)
                    continue
                with st.spinner(f"Analyzing {name}…"):
                    texts = [t.get("text","") for t in d["tweets"] if t.get("text","")]
                    summary = ai_content_summary(name, texts, anthropic_key)
                if summary:
                    top_nar = summary.get("top_narrative","—")
                    nar_color = NARRATIVE_COLORS.get(top_nar, color)
                    st.markdown(f"""
                    <div style="background:{MANTLE_SURFACE};border:1px solid {color}33;border-left:3px solid {color};border-radius:8px;padding:12px;margin-bottom:8px">
                      <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:4px">CONTENT OVERVIEW</div>
                      <div style="font-size:12px;color:{MANTLE_TEXT};line-height:1.6;margin-bottom:10px">{summary.get("content_summary","—")}</div>
                      <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:4px">TOP NARRATIVE</div>
                      <div style="margin-bottom:6px">
                        <span style="background:{nar_color}22;color:{nar_color};border:1px solid {nar_color}44;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">{top_nar}</span>
                      </div>
                      <div style="font-size:12px;color:{MANTLE_TEXT};line-height:1.6;margin-bottom:10px">{summary.get("top_narrative_reason","—")}</div>
                      <div style="font-size:11px;color:{MANTLE_MUTED};margin-bottom:4px">HIGH-ATTENTION TOPIC</div>
                      <div style="font-size:12px;color:#f59e0b;font-weight:600;margin-bottom:4px">{summary.get("high_attention_topic","—")}</div>
                      <div style="font-size:12px;color:{MANTLE_TEXT};line-height:1.6">{summary.get("high_attention_reason","—")}</div>
                    </div>""", unsafe_allow_html=True)
                    themes = summary.get("main_themes", [])
                    if themes:
                        pills = " ".join([f'<span style="background:{color}22;color:{color};border:1px solid {color}33;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600">{th}</span>' for th in themes])
                        st.markdown(f'<div style="margin-top:4px">{pills}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">Analysis unavailable</div>', unsafe_allow_html=True)

    # Gap analysis
    render_gap_analysis(all_data)

    # Views line chart
    fig = go.Figure()
    for name, d in all_data.items():
        df = group_by(d["tweets"], period)
        if not df.empty:
            fig.add_trace(go.Scatter(x=df["period"], y=df["impressions"], name=name,
                                     mode="lines+markers",
                                     line=dict(color=d["color"], width=2), marker=dict(size=5),
                                     hovertemplate=f"{name}: " + "%{y:,}<extra></extra>"))
    fig.update_layout(**BASE_LAYOUT, height=280, xaxis=AXIS, yaxis=AXIS,
                      title=dict(text=f"Views by {period} — all chains",
                                 font=dict(size=13, color="#E0F5EC"), x=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── Per-chain narrative breakdown ─────────────────────────────────────────
    st.markdown('<div class="section-title">Narrative Breakdown by Chain</div>', unsafe_allow_html=True)
    nar_cols = st.columns(len(CHAIN_COLORS))
    for col, (name, d) in zip(nar_cols, all_data.items()):
        color = d["color"]
        all_n = []
        for t in d["tweets"]: all_n.extend(detect_nar(t.get("text","")))
        counts = Counter(all_n)
        total = sum(counts.values()) or 1
        sorted_n = sorted(counts.items(), key=lambda x:-x[1])
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:800;color:{color};margin-bottom:10px;text-transform:uppercase">{name}</div>', unsafe_allow_html=True)
            if sorted_n:
                labels = [n for n,_ in sorted_n]
                values = [c for _,c in sorted_n]
                colors = [NARRATIVE_COLORS.get(n,"#666") for n in labels]
                fp = go.Figure(go.Pie(
                    labels=labels, values=values,
                    marker=dict(colors=colors, line=dict(color=MANTLE_DARK, width=2)),
                    textfont_size=10, hole=0.5,
                    hovertemplate="%{label}: %{value} posts (%{percent})<extra></extra>"))
                pl = {k:v for k,v in BASE_LAYOUT.items() if k not in ("margin","legend")}
                fp.update_layout(**pl, height=220, showlegend=True,
                                 margin=dict(l=0,r=0,t=10,b=0),
                                 legend=dict(font=dict(size=10,color="#E0F5EC"),
                                             bgcolor="rgba(0,0,0,0)"))
                st.plotly_chart(fp, use_container_width=True)
                # top narrative label
                top = sorted_n[0]
                tc = NARRATIVE_COLORS.get(top[0],"#666")
                st.markdown(f'<div style="text-align:center;font-size:11px;color:{tc};font-weight:700">#{1} {top[0]} · {top[1]/total*100:.0f}%</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No data</div>', unsafe_allow_html=True)

    # Top posts per chain
    st.markdown('<div class="section-title">Top Official Posts by Chain</div>', unsafe_allow_html=True)
    for name, d in all_data.items():
        color = d["color"]
        top_views, top_eng_list = split_top_posts(d["tweets"], n=3)
        st.markdown(f'<div style="font-size:13px;font-weight:800;color:{color};margin:14px 0 8px;text-transform:uppercase;letter-spacing:.08em">{name}</div>', unsafe_allow_html=True)
        cv, ce = st.columns(2)
        with cv:
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:{color};margin-bottom:8px">👁 Top 3 by Views</div>', unsafe_allow_html=True)
            if top_views:
                for i, t in enumerate(top_views, 1): render_post(t, i, color, chain_name=name, is_user=False)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No data</div>', unsafe_allow_html=True)
        with ce:
            st.markdown(f'<div style="font-size:11px;font-weight:700;color:#f59e0b;margin-bottom:8px">⚡ Top 3 by Engagement</div>', unsafe_allow_html=True)
            if top_eng_list:
                for i, t in enumerate(top_eng_list, 1): render_post(t, i, "#f59e0b", chain_name=name, is_user=False)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No additional posts</div>', unsafe_allow_html=True)

    # KOL mentions
    st.markdown('<div class="section-title">Top KOL Mentions by Views (last 7 days)</div>', unsafe_allow_html=True)
    mcols = st.columns(len(CHAIN_COLORS))
    for col, (name, d) in zip(mcols, all_data.items()):
        if name == "Base":
            q = '"Base chain" OR "Base blockchain" OR "build on Base" (crypto OR blockchain OR web3) -from:base -is:retweet lang:en min_faves:50'
        elif name == "Solana":
            q = '(#Solana OR "Solana network" OR "SOL blockchain") (crypto OR blockchain OR defi OR web3) -from:solana -is:retweet lang:en min_faves:50'
        elif name == "Ondo":
            q = '(#Ondo OR "Ondo Finance" OR USDY OR OUSG) (crypto OR blockchain OR rwa OR defi) -from:OndoFinance -is:retweet lang:en min_faves:20'
        else:
            q = '(#Mantle OR "Mantle network" OR "Mantle blockchain" OR mETH) (crypto OR blockchain OR defi OR web3) -from:Mantle_Official -is:retweet lang:en min_faves:20'
        with st.spinner(f"Fetching {name} mentions…"):
            mentions = search_tweets(q, token, si7, ei7, max_results=100)
        mentions = [t for t in mentions if any(k in t.get("text","").lower() for k in BLOCKCHAIN_KW)]
        sm = sorted(mentions, key=get_imp, reverse=True)
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:800;color:{d["color"]};margin-bottom:10px;text-transform:uppercase">{name} mentions</div>', unsafe_allow_html=True)
            if sm:
                for i, t in enumerate(sm[:3], 1): render_post(t, i, d["color"], chain_name=name, is_user=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">No mentions found</div>', unsafe_allow_html=True)

    # Export
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    if st.button("📥 Download HTML Report — Competitive", key="export_t2"):
        all_tweets = []
        all_nar_comp = Counter()
        for name, d in all_data.items():
            for t in d["tweets"]:
                t["chain"] = name
            all_tweets.extend(d["tweets"])
            for t in d["tweets"]: all_nar_comp.update(detect_nar(t.get("text","")))
        html = generate_report(
            "Competitive Analysis",
            f"{start} to {end}",
            {name: fmt(sum(get_imp(t) for t in d["tweets"])) + " views" for name, d in all_data.items()},
            sorted(all_tweets, key=get_imp, reverse=True),
            all_nar_comp
        )
        st.download_button("💾 Save Report", html, file_name=f"competitive_report_{start}_{end}.html",
                           mime="text/html", key="dl_t2")


# ── TAB 3 ────────────────────────────────────────────────────────────────────
def tab_research(token):
    tab_description(
        "Industry Research — Notable Reads",
        "Aggregates research articles, data threads, and analysis from leading crypto research accounts. Ranked by views within the selected date range.",
        RESEARCH_ACCOUNTS,
        "Custom date range (user-selected)"
    )
    start, end, period = date_controls("t3")
    start_iso, end_iso = iso_range(start, end)

    all_posts = []
    with st.spinner("Fetching research posts…"):
        for handle in RESEARCH_ACCOUNTS:
            u = get_user(handle, token)
            uid = u.get("id", "")
            if not uid: continue
            tw = get_tweets(uid, token, start_iso, end_iso, max_results=100)
            for t in tw:
                t["author_handle"] = handle
                t["author_name"] = u.get("name", handle)
                t["author_followers"] = u.get("public_metrics",{}).get("followers_count", 0)
            all_posts.extend(tw)

    filtered = [p for p in all_posts if any(k in p.get("text","").lower() for k in RESEARCH_KW)]
    sorted_posts = sorted(filtered, key=get_imp, reverse=True)

    st.caption(f"Found {len(filtered)} research posts from {len(RESEARCH_ACCOUNTS)} accounts")

    if not filtered:
        st.warning("No research posts found. Try adjusting the date range.")
        return

    # Narrative distribution
    all_nar = []
    for p in filtered: all_nar.extend(detect_nar(p.get("text","")))
    nar_counts = Counter(all_nar)
    nar_counts.pop("Other", None)

    if nar_counts:
        st.markdown('<div class="section-title">Narrative Distribution — All Research Posts</div>', unsafe_allow_html=True)
        sn = sorted(nar_counts.items(), key=lambda x:-x[1])
        total_n = sum(v for _,v in sn) or 1
        fb = go.Figure(go.Bar(
            x=[n for n,_ in sn],
            y=[c/total_n*100 for _,c in sn],
            marker_color=[NARRATIVE_COLORS.get(n,"#666") for n,_ in sn],
            text=[f"{c/total_n*100:.0f}%" for _,c in sn],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f}% (%{customdata} posts)<extra></extra>",
            customdata=[c for _,c in sn]))
        fb.update_layout(**BASE_LAYOUT, height=240, showlegend=False,
                         xaxis=AXIS, yaxis=dict(**AXIS, ticksuffix="%"),
                         title=dict(text=f"Narrative distribution — {len(filtered)} posts",
                                    font=dict(size=13, color="#E0F5EC"), x=0))
        st.plotly_chart(fb, use_container_width=True)

    st.markdown('<div class="section-title">Top 15 Research Posts by Views</div>', unsafe_allow_html=True)
    for i, t in enumerate(sorted_posts[:15], 1):
        render_post(t, i, "#A0C8B0", is_user=True)

    # Export
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    if st.button("📥 Download HTML Report — Research", key="export_t3"):
        html = generate_report(
            "Industry Research",
            f"{start} to {end}",
            {"Total Posts": str(len(filtered)),
             "Top Views": fmt(get_imp(sorted_posts[0])) if sorted_posts else "0",
             "Accounts": str(len(RESEARCH_ACCOUNTS))},
            sorted_posts,
            nar_counts
        )
        st.download_button("💾 Save Report", html, file_name=f"research_report_{start}_{end}.html",
                           mime="text/html", key="dl_t3")

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    token = get_token()
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
    </div>""", unsafe_allow_html=True)

    if not token:
        st.error("Missing TWITTER_BEARER_TOKEN — add in Streamlit → Settings → Secrets")
        st.code('TWITTER_BEARER_TOKEN = "your_token_here"')
        st.stop()

    col_r, _ = st.columns([1,8])
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    t1, t2, t3 = st.tabs(["📊  Mantle Deep Dive","⚔️  Competitive Analysis","🔬  Industry Research"])
    with t1: tab_mantle(token)
    with t2: tab_competitive(token)
    with t3: tab_research(token)

if __name__ == "__main__":
    main()
