import streamlit as st
import streamlit.components.v1 as components
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

MANTLE_GREEN   = "#00A572"
MANTLE_DARK    = "#F0FAF5"
MANTLE_SURFACE = "#FFFFFF"
MANTLE_BORDER  = "#C8EAD8"
MANTLE_TEXT    = "#0D3320"
MANTLE_MUTED   = "#4A7A5A"

CHAIN_COLORS = {
    "Mantle":   MANTLE_GREEN,
    "Solana":   "#9945FF",
    "Base":     "#2563EB",
    "Ondo":     "#FF6B35",
    "Plume":    "#E84142",
    "Arbitrum": "#12AAFF",
    "Optimism": "#FF0420",
    "Plasma":   "#7B2FBE",
    "BNBChain": "#F0B90B",
    "Stellar":  "#7D00FF",
    "Avax":     "#E84142",
}

CHAIN_HANDLES = {
    "Mantle":   "Mantle_Official",
    "Solana":   "solana",
    "Base":     "base",
    "Ondo":     "OndoFinance",
    "Plume":    "plumenetwork",
    "Arbitrum": "arbitrum",
    "Optimism": "Optimism",
    "Plasma":   "Plasma",
    "BNBChain": "BNBCHAIN",
    "Stellar":  "StellarOrg",
    "Avax":     "avax",
}

DEFAULT_CHAINS = ["Mantle", "Solana", "Base", "Ondo"]

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

AXIS = dict(gridcolor="#C8EAD8",showgrid=True,zeroline=False,color="#2D6A4F",tickfont=dict(color="#2D6A4F",size=11))
BASE_LAYOUT = dict(
    paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
    font=dict(color="#2D6A4F",size=11,family="Inter"),
    legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=13,color="#0D3320",family="Inter"),
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
    if not anthropic_key or not tweets_text_list: return None
    sample = list(tweets_text_list)[:20]
    combined = "\n---\n".join(sample)
    prompt = f"""Analyze these tweets from {chain_name}'s official account and respond with JSON only:
{{"main_themes":["theme1","theme2","theme3"],"top_narrative":"narrative name","top_narrative_reason":"1-2 sentences","content_summary":"2-3 sentences","high_attention_topic":"topic","high_attention_reason":"1-2 sentences"}}

TWEETS:
{combined}"""
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        if r.status_code == 200:
            import json, re as re2
            raw = r.json()["content"][0]["text"].strip()
            raw = re2.sub(r'^```(?:json)?\s*', '', raw)
            raw = re2.sub(r'\s*```$', '', raw).strip()
            return json.loads(raw)
        return {"_error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"_error": str(e)}

@st.cache_data(ttl=1800)
def ai_content_comparison(chains_data_tuple, anthropic_key):
    """Compare content quality across chains and give Mantle actionable lessons"""
    if not anthropic_key: return None
    chains_data = dict(chains_data_tuple)

    chain_summaries = []
    for name, data in chains_data.items():
        tweets = data.get("tweets", [])[:10]
        top = sorted(tweets, key=lambda t: (t.get("public_metrics",{}).get("impression_count") or 0) or
                     ((t.get("public_metrics",{}).get("like_count",0) or 0)*100), reverse=True)[:3]
        samples = "\n".join([f"- [{t.get('narrative','?')}] {t.get('text','')[:100]}" for t in top])
        followers = data.get("followers", 0)
        total_views = data.get("total_views", 0)
        chain_summaries.append(f"=={name}== ({fmt(followers)} followers, {fmt(total_views)} views)\n{samples}")

    prompt = f"""Senior crypto social media strategist. Compare these chains briefly:

{chr(10).join(chain_summaries)}

JSON only (max 15 words per field). IMPORTANT: mantle_lessons must include one entry for EVERY non-Mantle chain listed above:
{{"winner":"chain","winner_reason":"why","ranking":[{{"chain":"name","score":"Excellent/Good/Average/Weak","summary":"brief"}}],"market_momentum_leader":"chain — why","mantle_lessons":[{{"from_chain":"name","lesson":"what to learn","example":"brief example"}}]}}"""

    import time, json, re as re2
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1200,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=40
            )
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code == 200:
                raw = r.json()["content"][0]["text"].strip()
                raw = re2.sub(r'^```(?:json)?\s*', '', raw)
                raw = re2.sub(r'\s*```$', '', raw)
                return json.loads(raw.strip())
            return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            if attempt == 2: return {"_error": str(e)}
            time.sleep(10)
    return {"_error": "Rate limit — wait 1 min and refresh"}

@st.cache_data(ttl=1800)
def ai_chains_swot_batch(chains_data_tuple, anthropic_key):
    """Batch SWOT for all chains in one API call"""
    if not anthropic_key: return {}
    chains_data = list(chains_data_tuple)

    summaries = []
    for name, tweets, metrics in chains_data:
        m = dict(metrics)
        top = sorted(tweets, key=lambda t: get_imp(t), reverse=True)[:5]
        samples = " | ".join([f"[{t.get('narrative','?')}] {t.get('text','')[:80]}" for t in top])
        summaries.append(f"=={name}== {fmt(m.get('followers',0))} followers, {fmt(m.get('total_views',0))} views, eng:{m.get('eng_rate',0):.1f}%, top_nar:{m.get('top_narrative','?')}\nPosts: {samples}")

    prompt = f"""Crypto social media strategist. Analyze content for each chain below.

{chr(10).join(summaries)}

Return JSON with one entry per chain (max 15 words per item):
{{"chains":[{{"name":"chain","content_style":"1 sentence","strengths":["s1","s2","s3"],"weaknesses":["w1","w2","w3"],"improvements":["i1","i2","i3"]}}]}}
JSON only."""

    import time, json, re as re5
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2000,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=45
            )
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code == 200:
                raw = r.json()["content"][0]["text"].strip()
                raw = re5.sub(r'^```(?:json)?\s*', '', raw)
                raw = re5.sub(r'\s*```$', '', raw)
                data = json.loads(raw.strip())
                # Return as dict keyed by chain name
                return {item["name"]: item for item in data.get("chains", [])}
            return {}
        except Exception as e:
            if attempt == 2: return {}
            time.sleep(10)
    return {}
    """Compare content quality across chains and give Mantle actionable lessons"""
    if not anthropic_key: return None
    chains_data = dict(chains_data_tuple)

    chain_summaries = []
    for name, data in chains_data.items():
        tweets = data.get("tweets", [])[:15]
        top = sorted(tweets, key=lambda t: (t.get("public_metrics",{}).get("impression_count") or 0) or
                     ((t.get("public_metrics",{}).get("like_count",0) or 0)*100), reverse=True)[:5]
        samples = "\n".join([f"- [{t.get('narrative','?')}] {t.get('text','')[:120]} (views:{fmt(t.get('public_metrics',{}).get('impression_count') or 0)})" for t in top])
        followers = data.get("followers", 0)
        total_views = data.get("total_views", 0)
        chain_summaries.append(f"=={name}== ({followers:,} followers, {total_views:,} total views)\nTop posts:\n{samples}")

    prompt = f"""You are a senior crypto social media strategist. Compare content performance across these chains:

{chr(10).join(chain_summaries)}

Provide analysis in this exact JSON (keep each string under 120 words):
{{"winner":"chain name with best content quality","winner_reason":"why they win — specific content strategies, narrative alignment, format choices",
"ranking":[{{"chain":"name","score":"Excellent/Good/Average/Weak","summary":"2-3 sentences on their content approach and what works"}}],
"market_momentum_leader":"which chain best captures current market narratives and why",
"mantle_lessons":[{{"from_chain":"chain name","lesson":"specific actionable thing Mantle should copy or adapt","example":"concrete example from their posts"}}]}}

Be specific, reference actual post content. JSON only."""

    import time, json, re as re2
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1500,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=40
            )
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code == 200:
                raw = r.json()["content"][0]["text"].strip()
                raw = re2.sub(r'^```(?:json)?\s*', '', raw)
                raw = re2.sub(r'\s*```$', '', raw)
                return json.loads(raw.strip())
            return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            if attempt == 2:
                return {"_error": str(e)}
            time.sleep(10)
    return {"_error": "Rate limit — please wait 1 min and refresh"}

def render_chain_swot(name, swot, color):
    if not swot: return
    if "_error" in swot:
        st.error(f"AI Error: {swot['_error']}")
        return
    style = swot.get("content_style","")
    st.markdown(f"""
    <div style="background:#FFFFFF;border:1px solid {color}33;border-left:3px solid {color};border-radius:8px;padding:10px 14px;margin-bottom:6px">
      <div style="font-size:10px;font-weight:800;color:{color};text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">{name}</div>
      <div style="font-size:11px;color:#4A7A5A;font-style:italic;margin-bottom:10px">{style}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
        <div>
          <div style="font-size:10px;font-weight:700;color:#00A572;margin-bottom:4px">✅ Strengths</div>
          {''.join([f'<div style="font-size:11px;color:#0D3320;padding:3px 0;border-bottom:1px solid #E8F5EE">• {s}</div>' for s in swot.get('strengths',[])])}
        </div>
        <div>
          <div style="font-size:10px;font-weight:700;color:#f87171;margin-bottom:4px">⚠️ Weaknesses</div>
          {''.join([f'<div style="font-size:11px;color:#0D3320;padding:3px 0;border-bottom:1px solid #FEE2E2">• {w}</div>' for w in swot.get('weaknesses',[])])}
        </div>
        <div>
          <div style="font-size:10px;font-weight:700;color:#f59e0b;margin-bottom:4px">💡 Improvements</div>
          {''.join([f'<div style="font-size:11px;color:#0D3320;padding:3px 0;border-bottom:1px solid #FEF3C7">• {i}</div>' for i in swot.get('improvements',[])])}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

def render_content_comparison(analysis):
    if not analysis: return
    if "_error" in analysis:
        st.error(f"AI Error: {analysis['_error']}")
        return

    winner = analysis.get("winner","—")
    winner_color = CHAIN_COLORS.get(winner, MANTLE_GREEN)

    st.markdown(f"""
    <div style="background:{winner_color}11;border:1px solid {winner_color}44;border-radius:10px;padding:14px 18px;margin-bottom:14px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <span style="font-size:12px;font-weight:800;color:{MANTLE_TEXT}">🏆 Content Quality Winner</span>
        <span style="background:{winner_color}22;color:{winner_color};border:1px solid {winner_color}44;padding:2px 12px;border-radius:99px;font-size:11px;font-weight:700">{winner}</span>
      </div>
      <div style="font-size:13px;color:{MANTLE_TEXT};line-height:1.6;margin-bottom:10px">{analysis.get("winner_reason","")}</div>
      <div style="font-size:11px;color:{MANTLE_MUTED}">📈 Market momentum leader: <b style="color:{MANTLE_TEXT}">{analysis.get("market_momentum_leader","—")}</b></div>
    </div>""", unsafe_allow_html=True)

    # Chain rankings
    ranking = analysis.get("ranking", [])
    if ranking:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Content Quality Ranking</div>', unsafe_allow_html=True)
        score_colors = {"Excellent": MANTLE_GREEN, "Good": "#06b6d4", "Average": "#f59e0b", "Weak": "#f87171"}
        for i, item in enumerate(ranking, 1):
            chain = item.get("chain","")
            score = item.get("score","")
            summary = item.get("summary","")
            c = CHAIN_COLORS.get(chain, MANTLE_MUTED)
            sc = score_colors.get(score, MANTLE_MUTED)
            st.markdown(f"""
            <div style="display:flex;gap:10px;align-items:flex-start;padding:10px;background:{MANTLE_SURFACE};border:1px solid {c}33;border-radius:8px;margin-bottom:6px">
              <span style="font-size:14px;font-weight:800;color:#555;min-width:20px">#{i}</span>
              <span style="color:{c};font-weight:700;font-size:12px;min-width:60px">{chain}</span>
              <span style="background:{sc}22;color:{sc};border:1px solid {sc}44;padding:1px 8px;border-radius:99px;font-size:10px;font-weight:700;white-space:nowrap">{score}</span>
              <span style="font-size:12px;color:{MANTLE_TEXT};line-height:1.5;flex:1">{summary}</span>
            </div>""", unsafe_allow_html=True)

    # Lessons for Mantle
    lessons = analysis.get("mantle_lessons", [])
    if lessons:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:.08em;margin:12px 0 8px">📚 What Mantle Should Learn</div>', unsafe_allow_html=True)
        for lesson in lessons:
            from_chain = lesson.get("from_chain","")
            lc = CHAIN_COLORS.get(from_chain, MANTLE_MUTED)
            st.markdown(f"""
            <div style="background:{MANTLE_SURFACE};border:1px solid {lc}33;border-left:3px solid {lc};border-radius:8px;padding:10px 14px;margin-bottom:8px">
              <div style="font-size:10px;color:{lc};font-weight:700;margin-bottom:4px">FROM {from_chain.upper()}</div>
              <div style="font-size:12px;color:{MANTLE_TEXT};font-weight:600;margin-bottom:4px">{lesson.get("lesson","")}</div>
              <div style="font-size:11px;color:{MANTLE_MUTED};line-height:1.5">💡 {lesson.get("example","")}</div>
            </div>""", unsafe_allow_html=True)

@st.cache_data(ttl=1800)
def ai_social_expert_analysis(tweets_tuple, metrics_data, anthropic_key):
    """Claude as social media expert analyzing Mantle's content performance"""
    if not anthropic_key or not tweets_tuple:
        return None
    tweets_data = list(tweets_tuple)
    metrics_data = dict(metrics_data)  # convert back from tuple of items
    # Prepare tweet samples with metrics
    samples = []
    for t in tweets_data[:30]:
        m = t.get("public_metrics", {})
        imp = m.get("impression_count") or 0
        if not imp:
            e_val = (m.get("like_count",0) or 0) + (m.get("retweet_count",0) or 0)*3 + (m.get("reply_count",0) or 0)*2
            imp = e_val * 100
        samples.append({
            "text": t.get("text","")[:200],
            "views": imp,
            "likes": m.get("like_count",0),
            "retweets": m.get("retweet_count",0),
            "narrative": t.get("narrative","Other")
        })

    # Only send top 10 posts to keep prompt short
    samples_str = "\n".join([f"- [{s['narrative']}] {s['text'][:120]} (views:{s['views']:,} likes:{s['likes']})" for s in samples[:10]])

    prompt = f"""You are a senior crypto social media strategist. Analyze @Mantle_Official's Twitter performance.

METRICS:
- Posts: {metrics_data['post_count']} | Views: {metrics_data['total_views']:,} | Likes: {metrics_data['total_likes']:,} | Eng.rate: {metrics_data['eng_rate']:.2f}% | Followers: {metrics_data['followers']:,}
- vs prev period: views {metrics_data['view_delta']:+.1f}%, posts {metrics_data['post_delta']:+.1f}%
- Narratives: {metrics_data['narratives']}

TOP POSTS:
{samples_str}

Return ONLY this JSON (no markdown, keep each string under 100 words):
{{"overall_score":"Good or Average or Needs Improvement","overall_assessment":"assessment here","engagement_analysis":"analysis here","content_quality":"quality here","narrative_fit":"fit here","strengths":["s1","s2","s3"],"weaknesses":["w1","w2","w3"],"recommendations":["r1","r2","r3"]}}"""

    import time, json, re as re3
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1500,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=30
            )
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code == 200:
                raw = r.json()["content"][0]["text"].strip()
                raw = re3.sub(r'^```(?:json)?\s*', '', raw)
                raw = re3.sub(r'\s*```$', '', raw)
                return json.loads(raw.strip())
            return {"_error": f"HTTP {r.status_code}: {r.text[:300]}"}
        except Exception as e:
            if attempt == 2:
                return {"_error": str(e)}
            time.sleep(10)
    return {"_error": "Rate limit — please wait 1 min and refresh"}

def render_social_expert_analysis(analysis):
    if not analysis:
        st.info("AI analysis unavailable. Check Anthropic API key.")
        return
    if "_error" in analysis:
        st.error(f"API Error: {analysis['_error']}")
        return

    score = analysis.get("overall_score", "—")
    score_color = {"Good": MANTLE_GREEN, "Average": "#f59e0b", "Needs Improvement": "#f87171"}.get(score, MANTLE_MUTED)

    st.markdown(f"""
    <div style="background:{MANTLE_SURFACE};border:1px solid {score_color}44;border-radius:12px;padding:20px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:800;color:{MANTLE_TEXT}">🧠 AI Social Expert Analysis</div>
        <span style="background:{score_color}22;color:{score_color};border:1px solid {score_color}44;padding:3px 12px;border-radius:99px;font-size:11px;font-weight:700">{score}</span>
      </div>
      <div style="font-size:13px;color:{MANTLE_TEXT};line-height:1.7;margin-bottom:14px">{analysis.get("overall_assessment","")}</div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">📊 Engagement Analysis</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;color:{MANTLE_TEXT};line-height:1.7;margin-bottom:14px">{analysis.get("engagement_analysis","")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">🎯 Narrative Fit</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;color:{MANTLE_TEXT};line-height:1.7">{analysis.get("narrative_fit","")}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">✍️ Content Quality</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;color:{MANTLE_TEXT};line-height:1.7">{analysis.get("content_quality","")}</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
    c3, c4, c5 = st.columns(3)
    with c3:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:{MANTLE_GREEN};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">✅ Strengths</div>', unsafe_allow_html=True)
        for s in analysis.get("strengths", []):
            st.markdown(f'<div style="font-size:12px;color:{MANTLE_TEXT};padding:6px 10px;background:#E0F5EC;border:1px solid #00A57233;border-radius:6px;margin-bottom:6px;line-height:1.5">• {s}</div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:#f87171;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">⚠️ Weaknesses</div>', unsafe_allow_html=True)
        for w in analysis.get("weaknesses", []):
            st.markdown(f'<div style="font-size:12px;color:{MANTLE_TEXT};padding:6px 10px;background:#FEE2E2;border:1px solid #f8717133;border-radius:6px;margin-bottom:6px;line-height:1.5">• {w}</div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div style="font-size:12px;font-weight:700;color:#f59e0b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">💡 Recommendations</div>', unsafe_allow_html=True)
        for rec in analysis.get("recommendations", []):
            st.markdown(f'<div style="font-size:12px;color:{MANTLE_TEXT};padding:6px 10px;background:#FEF3C7;border:1px solid #f59e0b33;border-radius:6px;margin-bottom:6px;line-height:1.5">• {rec}</div>', unsafe_allow_html=True)

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

def detect_nar_keyword(text):
    """Fallback keyword-based narrative detection"""
    tl = text.lower()
    found = [n for n, kws in NARRATIVES.items() if any(k in tl for k in kws)]
    return found[0] if found else "Other"

@st.cache_data(ttl=1800)
def classify_narratives_batch(texts_tuple, anthropic_key):
    """Use Claude to classify tweets into narratives — free-form labels"""
    if not anthropic_key:
        return {}
    texts = list(texts_tuple)
    numbered = "\n".join([f"{i+1}. {t[:200]}" for i,t in enumerate(texts)])
    prompt = f"""You are a crypto analyst. Classify each tweet into a single narrative label.

Rules:
- Use existing crypto narratives when clearly applicable: RWA, DeFi, AI, Infrastructure, Institutional, NFT, Gaming
- If the tweet doesn't fit those, create a short descriptive label (1-3 words max): e.g. "Community", "Partnership", "Market Update", "Meme", "Product Launch", "Ecosystem", "Stablecoin", "Restaking", "Tokenomics", "Regulatory"
- Each tweet gets exactly ONE label
- Be specific — don't default to "Other" unless truly uncategorizable
- Context matters: a tweet about SpaceX token = "Meme", not "DeFi"

Tweets:
{numbered}

Respond with ONLY a JSON object. Example:
{{"1":"RWA","2":"DeFi","3":"Meme","4":"Community","5":"Infrastructure"}}
No explanation, no markdown, just JSON."""

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
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if r.status_code == 200:
            import json
            raw = r.json()["content"][0]["text"].strip()
            result = json.loads(raw)
            return {int(k)-1: v for k,v in result.items()}
    except:
        pass
    return {}

def classify_tweets_narratives(tweets, anthropic_key):
    """Classify all tweets, batch by 50, cache results on tweet objects"""
    if not anthropic_key:
        for t in tweets:
            if "narrative" not in t:
                t["narrative"] = detect_nar_keyword(t.get("text",""))
        return tweets

    # Only classify tweets that haven't been classified yet
    unclassified = [t for t in tweets if "narrative" not in t]
    if not unclassified:
        return tweets

    # Process in batches of 50
    batch_size = 50
    for i in range(0, len(unclassified), batch_size):
        batch = unclassified[i:i+batch_size]
        texts = tuple(t.get("text","") for t in batch)
        results = classify_narratives_batch(texts, anthropic_key)
        for j, t in enumerate(batch):
            t["narrative"] = results.get(j, detect_nar_keyword(t.get("text","")))

    return tweets

def get_nar_color(label):
    """Get color for a narrative label — fixed for known ones, generated for dynamic ones"""
    fixed = {
        "RWA":"#f59e0b","DeFi":"#3b82f6","AI":"#8b5cf6",
        "Infrastructure":"#10b981","Institutional":"#06b6d4",
        "NFT":"#ec4899","Gaming":"#f97316","Other":"#6b7280",
        "Community":"#84cc16","Partnership":"#22d3ee","Market Update":"#fb923c",
        "Meme":"#f43f5e","Product Launch":"#a78bfa","Ecosystem":"#34d399",
        "Stablecoin":"#fbbf24","Restaking":"#60a5fa","Tokenomics":"#c084fc",
        "Regulatory":"#94a3b8",
    }
    if label in fixed:
        return fixed[label]
    # generate consistent color from label hash
    h = abs(hash(label)) % 360
    return f"hsl({h},65%,55%)"

def get_narrative(t):
    """Get narrative for a tweet — single label"""
    return t.get("narrative", detect_nar_keyword(t.get("text","")))

def detect_nar(text):
    """Legacy compatibility — returns list for render_post pills"""
    result = detect_nar_keyword(text)
    return [result]

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
    brief = text[:120] + ("…" if len(text) > 120 else "")
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
    badge = f'<span class="narrative-pill" style="background:{color}22;color:{color};border:1px solid {color}44;font-size:9px;padding:1px 6px;border-radius:99px">{chain_name}</span>' if chain_name else ""
    pills = " ".join([f'<span class="narrative-pill" style="background:{get_nar_color(n)}22;color:{get_nar_color(n)};border:1px solid {get_nar_color(n)}33;font-size:9px;padding:1px 6px">{n}</span>' for n in narrs])
    fstr = f" · {fmt(followers)} flw" if followers else ""
    st.markdown(f"""
    <div class="post-card" style="padding:10px 12px;margin-bottom:6px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:4px">
        <div style="display:flex;align-items:center;gap:6px;min-width:0;flex:1">
          <span style="font-size:13px;font-weight:800;color:#aaa;min-width:20px">#{rank}</span>
          {badge}
          <span style="font-size:12px;font-weight:700;color:{MANTLE_TEXT};white-space:nowrap">@{handle}</span>
          <span style="font-size:10px;color:{MANTLE_MUTED};white-space:nowrap">{ago}{fstr}</span>
          {pills}
        </div>
        <div style="text-align:right;flex-shrink:0">
          <span style="font-size:13px;font-weight:800;color:{color}">{fmt(imp)}</span>
          <span style="font-size:9px;color:{MANTLE_MUTED}"> views</span>
        </div>
      </div>
      <div style="font-size:11px;color:#4A7A5A;line-height:1.45;margin-bottom:6px">{brief}</div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="font-size:10px;color:{MANTLE_MUTED}">
          ♥ {fmt(m.get("like_count",0))} &nbsp;·&nbsp;
          ↺ {fmt(m.get("retweet_count",0))} &nbsp;·&nbsp;
          💬 {fmt(m.get("reply_count",0))}
        </div>
        <a href="{link}" target="_blank" style="font-size:10px;color:{color};text-decoration:none;padding:2px 8px;border:1px solid {color}44;border-radius:5px;background:{color}11;font-weight:600">View ↗</a>
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
    if not alerts: return
    rows = []
    for alert_type, t, val in alerts[:5]:
        raw_text = t.get("text","")[:70].replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("\n"," ") + "…"
        metric = f"{fmt(val)} views" if alert_type == "views" else f"{fmt(val)} eng"
        icon = "👁" if alert_type == "views" else "⚡"
        tid = t.get("id","")
        handle = {"Mantle":"Mantle_Official","Solana":"solana","Base":"base","Ondo":"OndoFinance"}.get(chain_name, chain_name)
        link = f"https://x.com/{handle}/status/{tid}"
        rows.append(f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid {color}22;overflow:hidden"><span style="font-size:10px;font-weight:700;color:#f59e0b;white-space:nowrap">{icon} {metric}</span><span style="font-size:11px;color:{MANTLE_MUTED};flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{raw_text}</span><a href="{link}" target="_blank" style="color:{color};font-size:10px;font-weight:700;white-space:nowrap;flex-shrink:0;text-decoration:none">↗ X</a></div>')

    rows_html = "".join(rows)
    html_content = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
*{{font-family:'Inter',sans-serif;box-sizing:border-box;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.2}}}}
.alert-title{{animation:blink 1.2s ease infinite;font-size:10px;font-weight:800;color:{color};margin-bottom:4px;letter-spacing:.08em;}}
body{{margin:0;padding:0;background:transparent;}}
</style>
<div style="background:{color}18;border:1px solid {color}44;border-radius:8px;padding:6px 10px;">
  <div class="alert-title">🔔 {chain_name.upper()} — HIGH PERFORMANCE</div>
  {rows_html}
</div>"""
    components.html(html_content, height=40 + len(rows)*28, scrolling=False)

# ── FEATURE: COMPETITOR GAP ANALYSIS ─────────────────────────────────────────
def render_gap_analysis(all_data):
    st.markdown('<div class="section-title">Competitor Gap Analysis</div>', unsafe_allow_html=True)
    mantle = all_data.get("Mantle", {})
    m_tweets = mantle.get("tweets", [])
    m_views = sum(get_imp(t) for t in m_tweets)
    m_posts = len(m_tweets)
    m_eng = sum(eng(t.get("public_metrics",{})) for t in m_tweets)
    m_eng_rate = round(m_eng / m_views * 100, 2) if m_views else 0
    m_vpp = round(m_views / m_posts) if m_posts else 0  # views per post
    m_nar = Counter(get_narrative(t) for t in m_tweets)
    m_total = sum(m_nar.values()) or 1

    insights = []
    for name, d in all_data.items():
        if name == "Mantle": continue
        color = d["color"]
        c_tweets = d.get("tweets", [])
        c_views = sum(get_imp(t) for t in c_tweets)
        c_posts = len(c_tweets)
        c_eng = sum(eng(t.get("public_metrics",{})) for t in c_tweets)
        c_eng_rate = round(c_eng / c_views * 100, 2) if c_views else 0
        c_vpp = round(c_views / c_posts) if c_posts else 0
        c_nar = Counter(get_narrative(t) for t in c_tweets)
        c_total = sum(c_nar.values()) or 1

        # Views per post comparison
        if c_vpp > 0 and m_vpp > 0:
            if c_vpp > m_vpp:
                ratio = c_vpp / m_vpp
                insights.append((color, "⚠️ Views/Post Gap",
                    f"<b>{name}</b> averages <b>{fmt(c_vpp)}</b> views/post vs Mantle's <b>{fmt(m_vpp)}</b> — <b>{ratio:.1f}x higher</b>. "
                    f"Despite Mantle's {m_posts} posts in the period, content reach per post is significantly lower. "
                    f"Focus on fewer, higher-quality posts rather than volume."))
            else:
                ratio = m_vpp / c_vpp
                insights.append((MANTLE_GREEN, "✅ Views/Post Advantage",
                    f"Mantle achieves <b>{fmt(m_vpp)}</b> views/post vs {name}'s <b>{fmt(c_vpp)}</b> — <b>{ratio:.1f}x better reach per post</b>. "
                    f"Content quality and relevance is clearly outperforming."))

        # Engagement rate comparison
        if c_eng_rate > 0 and m_eng_rate > 0:
            if c_eng_rate > m_eng_rate:
                diff = c_eng_rate - m_eng_rate
                insights.append((color, f"⚠️ Engagement Rate vs {name}",
                    f"<b>{name}</b> engagement rate: <b>{c_eng_rate:.2f}%</b> vs Mantle: <b>{m_eng_rate:.2f}%</b> (gap: <b>{diff:.2f}%</b>). "
                    f"Higher engagement rate indicates stronger community resonance and content relevance. "
                    f"Study {name}'s content format and narrative mix to identify what drives deeper engagement."))
            else:
                diff = m_eng_rate - c_eng_rate
                insights.append((MANTLE_GREEN, f"✅ Engagement Rate vs {name}",
                    f"Mantle's engagement rate <b>{m_eng_rate:.2f}%</b> outperforms {name} <b>{c_eng_rate:.2f}%</b> by <b>{diff:.2f}%</b>. "
                    f"Community engagement quality is stronger — leverage this with more interactive content."))

        # Narrative gap
        for nar in list(NARRATIVES.keys()):
            m_pct = m_nar.get(nar, 0) / m_total * 100
            c_pct = c_nar.get(nar, 0) / c_total * 100
            if c_pct - m_pct > 20:
                insights.append((color, f"⚠️ Narrative Gap — {nar}",
                    f"<b>{name}</b> dedicates <b>{c_pct:.0f}%</b> of content to <b>{nar}</b> vs Mantle's <b>{m_pct:.0f}%</b>. "
                    f"This {c_pct - m_pct:.0f}% gap suggests {name} is capitalizing on the {nar} narrative more aggressively. "
                    f"Mantle should increase {nar}-focused content to capture this market conversation."))
                break

    if not insights:
        st.info("Not enough data for gap analysis. Try a wider date range.")
        return

    for color, title, text in insights[:6]:
        st.markdown(f"""
        <div style="display:flex;gap:10px;align-items:flex-start;background:{MANTLE_SURFACE};
             border:1px solid {color}33;border-left:3px solid {color};
             border-radius:8px;padding:12px 14px;margin-bottom:8px">
          <div style="flex:1">
            <div style="font-size:10px;font-weight:800;color:{color};text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px">{title}</div>
            <div style="font-size:12px;color:{MANTLE_TEXT};line-height:1.6">{text}</div>
          </div>
        </div>""", unsafe_allow_html=True)

# ── FEATURE: EXPORT HTML REPORT ───────────────────────────────────────────────
def generate_html_report(tab_name, date_range, kpis, top_posts, narratives):
    """Generate HTML report matching dashboard style"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # KPI cards
    kpi_cards = "".join([f"""
    <div style="background:#fff;border:1px solid #C8EAD8;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,165,114,0.08)">
      <div style="font-size:11px;color:#4A7A5A;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;font-weight:600">{k}</div>
      <div style="font-size:24px;font-weight:800;color:#00A572">{v}</div>
    </div>""" for k,v in kpis.items()])

    # Narrative pills
    nar_items = sorted(narratives.items(), key=lambda x:-x[1])[:10]
    total_nar = sum(v for _,v in nar_items) or 1
    nar_bars = "".join([f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <div style="width:120px;font-size:12px;color:#0D3320;font-weight:500">{n}</div>
      <div style="flex:1;background:#E8F5EE;border-radius:4px;height:8px">
        <div style="width:{c/total_nar*100:.0f}%;background:#00A572;border-radius:4px;height:8px"></div>
      </div>
      <div style="font-size:12px;color:#4A7A5A;min-width:60px">{c} posts · {c/total_nar*100:.0f}%</div>
    </div>""" for n,c in nar_items])

    # Top posts
    posts_html = ""
    for i, t in enumerate(top_posts[:15], 1):
        m = t.get("public_metrics", {})
        text = t.get("text","")[:250].replace("<","&lt;").replace(">","&gt;").replace("\n"," ")
        handle = t.get("author_handle","") or {"Mantle":"Mantle_Official","Solana":"solana","Base":"base","Ondo":"OndoFinance"}.get(t.get("chain",""), "")
        tid = t.get("id","")
        link = f"https://x.com/{handle}/status/{tid}" if tid else "#"
        views = fmt(get_imp(t))
        likes = fmt(m.get("like_count",0))
        rts = fmt(m.get("retweet_count",0))
        nar = t.get("narrative","")
        nar_color = get_nar_color(nar) if nar else "#6b7280"
        ago = time_ago(t.get("created_at","")) if t.get("created_at") else ""
        posts_html += f"""
        <div style="background:#fff;border:1px solid #C8EAD8;border-radius:10px;padding:16px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:16px;font-weight:800;color:#C8EAD8">#{i}</span>
              <span style="font-size:13px;font-weight:700;color:#0D3320">@{handle}</span>
              <span style="font-size:11px;color:#4A7A5A">{ago}</span>
              {f'<span style="background:{nar_color}22;color:{nar_color};border:1px solid {nar_color}44;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600">{nar}</span>' if nar else ''}
            </div>
            <div style="text-align:right">
              <div style="font-size:14px;font-weight:800;color:#00A572">{views}</div>
              <div style="font-size:10px;color:#4A7A5A">views</div>
            </div>
          </div>
          <div style="font-size:13px;color:#4A7A5A;line-height:1.55;margin-bottom:10px">{text}</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="font-size:12px;color:#4A7A5A">♥ {likes} &nbsp;·&nbsp; ↺ {rts}</div>
            <a href="{link}" target="_blank" style="font-size:11px;color:#00A572;text-decoration:none;padding:4px 12px;border:1px solid #00A57244;border-radius:6px;background:#00A57211;font-weight:600">View on X ↗</a>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mantle Social Intelligence — {tab_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Inter',sans-serif;background:#F0FAF5;color:#0D3320;padding:32px;}}
  .header{{display:flex;align-items:center;gap:16px;margin-bottom:24px;padding-bottom:16px;border-bottom:2px solid #C8EAD8;}}
  .header h1{{font-size:24px;font-weight:800;color:#0D3320;}}
  .header .meta{{font-size:12px;color:#4A7A5A;margin-top:4px;}}
  .section-title{{font-size:13px;font-weight:800;color:#0D3320;text-transform:uppercase;letter-spacing:.12em;margin:20px 0 12px;padding-bottom:8px;border-bottom:2px solid #C8EAD8;}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:8px;}}
  .generated{{font-size:11px;color:#4A7A5A;margin-top:4px;}}
</style>
</head><body>
<div class="header">
  <div>
    <h1>Mantle Social Intelligence</h1>
    <div class="meta">{tab_name} &nbsp;·&nbsp; {date_range}</div>
    <div class="generated">Generated: {now}</div>
  </div>
</div>

<div class="section-title">Key Metrics</div>
<div class="kpi-grid">{kpi_cards}</div>

<div class="section-title">Narrative Breakdown</div>
<div style="background:#fff;border:1px solid #C8EAD8;border-radius:10px;padding:16px;">{nar_bars}</div>

<div class="section-title">Top Posts by Views</div>
{posts_html}

</body></html>"""
    return html
    """Generate a PDF report using reportlab"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    # Colors
    GREEN = colors.HexColor("#00A572")
    DARK  = colors.HexColor("#0D3320")
    MUTED = colors.HexColor("#4A7A5A")
    LIGHT = colors.HexColor("#E8F5EE")
    BORDER= colors.HexColor("#C8EAD8")

    styles = getSampleStyleSheet()
    title_style   = ParagraphStyle("title",   fontSize=20, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=4)
    sub_style     = ParagraphStyle("sub",     fontSize=10, fontName="Helvetica",      textColor=MUTED, spaceAfter=12)
    heading_style = ParagraphStyle("heading", fontSize=12, fontName="Helvetica-Bold", textColor=GREEN, spaceBefore=12, spaceAfter=6)
    body_style    = ParagraphStyle("body",    fontSize=9,  fontName="Helvetica",      textColor=DARK, spaceAfter=4, leading=14)
    small_style   = ParagraphStyle("small",   fontSize=8,  fontName="Helvetica",      textColor=MUTED, spaceAfter=2)

    story = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Header
    story.append(Paragraph("Mantle Social Intelligence", title_style))
    story.append(Paragraph(f"{tab_name} Report &nbsp;·&nbsp; {date_range} &nbsp;·&nbsp; Generated {now}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=12))

    # KPIs table
    story.append(Paragraph("Key Metrics", heading_style))
    kpi_data = [list(kpis.keys()), list(kpis.values())]
    kpi_table = Table(kpi_data, colWidths=[170/len(kpis)*mm]*len(kpis))
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), LIGHT),
        ("TEXTCOLOR",   (0,0), (-1,0), MUTED),
        ("TEXTCOLOR",   (0,1), (-1,1), GREEN),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica"),
        ("FONTNAME",    (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 8),
        ("FONTSIZE",    (0,1), (-1,1), 14),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT, colors.white]),
        ("BOX",         (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID",   (0,0), (-1,-1), 0.3, BORDER),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 8))

    # Narrative breakdown
    if narratives:
        story.append(Paragraph("Narrative Breakdown", heading_style))
        nar_items = sorted(narratives.items(), key=lambda x:-x[1])[:8]
        total_nar = sum(v for _,v in nar_items) or 1
        nar_data = [["Narrative", "Posts", "%"]] + [
            [n, str(c), f"{c/total_nar*100:.0f}%"] for n,c in nar_items
        ]
        nar_table = Table(nar_data, colWidths=[90*mm, 30*mm, 30*mm])
        nar_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), LIGHT),
            ("TEXTCOLOR",   (0,0), (-1,0), MUTED),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("ALIGN",       (1,0), (-1,-1), "CENTER"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FDF9")]),
            ("BOX",         (0,0), (-1,-1), 0.5, BORDER),
            ("INNERGRID",   (0,0), (-1,-1), 0.3, BORDER),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ]))
        story.append(nar_table)
        story.append(Spacer(1, 8))

    # Top posts
    if top_posts:
        story.append(Paragraph("Top Posts by Views", heading_style))
        for i, t in enumerate(top_posts[:10], 1):
            m = t.get("public_metrics", {})
            text = t.get("text","")[:180].replace("<","&lt;").replace(">","&gt;")
            handle = t.get("author_handle","") or {"Mantle":"Mantle_Official","Solana":"solana","Base":"base"}.get(t.get("chain",""), "")
            tid = t.get("id","")
            link = f"https://x.com/{handle}/status/{tid}"
            views = fmt(get_imp(t))
            likes = fmt(m.get("like_count",0))
            nar = t.get("narrative","")
            story.append(Paragraph(
                f'<font color="#00A572"><b>#{i}</b></font> '
                f'<font color="#4A7A5A">@{handle}</font> &nbsp;'
                f'<font color="#0D3320">{views} views · {likes} likes</font>'
                + (f' &nbsp;<font color="#8b5cf6">[{nar}]</font>' if nar else ""),
                body_style))
            story.append(Paragraph(text, small_style))
            story.append(Paragraph(f'<link href="{link}"><font color="#00A572">{link}</font></link>', small_style))
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
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

    nar_html = "".join([f'<span style="display:inline-block;background:{get_nar_color(n)}22;color:{get_nar_color(n)};border:1px solid {get_nar_color(n)}44;padding:4px 12px;border-radius:99px;margin:3px;font-size:12px;font-weight:600">{n}: {c}</span>' for n, c in sorted(narratives.items(), key=lambda x:-x[1])[:8]])

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
.stApp{{background-color:#F0FAF5;}}
.main .block-container{{padding:1.5rem 2rem 3rem;max-width:1400px;}}
#MainMenu,footer,header{{visibility:hidden;}}
section[data-testid="stSidebar"]{{display:none;}}
.stTabs [data-baseweb="tab-list"]{{gap:4px;background:#E8F5EE;border-bottom:2px solid #C8EAD8;padding:0 4px;}}
.stTabs [data-baseweb="tab"]{{background:transparent;border-radius:6px 6px 0 0;color:#4A7A5A;font-size:13px;font-weight:600;padding:10px 22px;border:none;letter-spacing:0.02em;}}
.stTabs [aria-selected="true"]{{background:#FFFFFF !important;color:#00A572 !important;border-bottom:2px solid #00A572 !important;}}
.kpi-card{{background:#FFFFFF;border:1px solid #C8EAD8;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,165,114,0.08);}} .kpi-card *{{user-select:none;}}
.kpi-label{{font-size:11px;color:{MANTLE_MUTED};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;font-weight:600;}}
.kpi-value{{font-size:26px;font-weight:800;color:#0D3320;letter-spacing:-0.5px;}}
.kpi-delta-up{{font-size:12px;color:{MANTLE_GREEN};margin-top:5px;font-weight:500;}}
.kpi-delta-dn{{font-size:12px;color:#f87171;margin-top:5px;font-weight:500;}}
.kpi-neutral{{font-size:12px;color:{MANTLE_MUTED};margin-top:5px;}}
.post-card{{background:#FFFFFF;border:1px solid #C8EAD8;border-radius:10px;padding:16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,165,114,0.06);}}
.post-card:hover{{border-color:#00A57244;box-shadow:0 2px 8px rgba(0,165,114,0.12);}}
.post-handle{{font-size:13px;font-weight:700;color:{MANTLE_TEXT};}}
.post-meta{{font-size:11px;color:{MANTLE_MUTED};}}
.post-text{{font-size:13px;color:#4A7A5A;line-height:1.55;margin:8px 0;}}
.narrative-pill{{display:inline-block;font-size:10px;padding:2px 8px;border-radius:99px;margin:2px;font-weight:600;}}
.section-title{{font-size:13px;font-weight:800;color:#0D3320;text-transform:uppercase;letter-spacing:0.12em;margin:12px 0 10px;border-bottom:2px solid #C8EAD8;padding-bottom:8px;}}
.tab-title{{font-size:22px;font-weight:800;color:#0D3320;letter-spacing:-0.3px;margin-bottom:10px;}}
.header-bar{{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:2px solid #C8EAD8;}}
.live-pill{{background:#E0F5EC;color:#00A572;border:1px solid #00A57244;padding:4px 12px;border-radius:99px;font-size:11px;font-weight:600;}}
.tab-desc{{background:#E8F5EE;border:1px solid #C8EAD8;border-radius:10px;padding:14px 18px;margin-bottom:16px;}}
.tab-desc-title{{font-size:13px;font-weight:700;color:{MANTLE_GREEN};margin-bottom:6px;}}
.tab-desc-body{{font-size:12px;color:{MANTLE_MUTED};line-height:1.6;}}
.tab-desc-body b{{color:#0D3320;}}
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

    # Classify narratives with Claude
    anthropic_key = get_anthropic_key()
    if tweets:
        with st.spinner("Classifying narratives with AI…"):
            tweets = classify_tweets_narratives(tweets, anthropic_key)

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
                                     font=dict(size=13, color="#0D3320"), x=0))
        st.plotly_chart(fig, use_container_width=True)

    # Narrative breakdown
    nar_counts = Counter(get_narrative(t) for t in tweets)
    if nar_counts:
        st.markdown('<div class="section-title">Narrative Breakdown</div>', unsafe_allow_html=True)
        nc1, nc2 = st.columns([1,2])
        with nc1:
            labels = list(nar_counts.keys())
            values = list(nar_counts.values())
            colors = [get_nar_color(l) for l in labels]
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
                c = get_nar_color(nm)
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

    # AI Social Expert Analysis
    st.markdown('<div class="section-title">AI Social Expert Analysis</div>', unsafe_allow_html=True)
    if not anthropic_key:
        st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets to enable AI analysis.")
    else:
        nar_summary = ", ".join([f"{n}: {c} posts" for n,c in sorted(nar_counts.items(), key=lambda x:-x[1])[:5]])
        metrics_data = {
            "post_count": post_count,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_rts": total_rts,
            "eng_rate": eng_rate,
            "followers": followers,
            "view_delta": view_delta,
            "post_delta": post_delta,
            "narratives": nar_summary,
        }
        with st.spinner("Running AI social analysis…"):
            try:
                analysis = ai_social_expert_analysis(
                    tuple(tweets),
                    tuple(sorted(metrics_data.items())),
                    anthropic_key
                )
                if not analysis:
                    st.error(f"API returned None. Key starts with: {anthropic_key[:10] if anthropic_key else 'MISSING'}")
            except Exception as ex:
                st.error(f"Error: {ex}")
                analysis = None
        render_social_expert_analysis(analysis)

    # Export report
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    if st.button("📥 Download HTML Report — Mantle", key="export_t1"):
        html = generate_html_report(
                "Mantle Deep Dive", f"{start} to {end}",
                {"Followers": fmt(followers), "Posts": str(post_count),
                 "Total Views": fmt(total_views), "Eng. Rate": f"{eng_rate:.2f}%"},
                tweets, nar_counts
            )
        st.download_button("💾 Save Report", html, file_name=f"mantle_report_{start}_{end}.html",
                           mime="text/html", key="dl_t1")


# ── TAB 2 ────────────────────────────────────────────────────────────────────
def tab_competitive(token):
    tab_description(
        "Competitive Analysis — Multi-Chain",
        "Compares official post performance across selected chains side by side. Includes AI content summary, gap analysis, narrative breakdown per chain, and top KOL mentions.",
        ["Select chains below"],
        "Official posts: custom date range · KOL mentions: last 7 days"
    )

    # Chain selector
    all_chain_names = list(CHAIN_COLORS.keys())
    st.markdown('<div style="font-size:11px;color:#4A7A5A;margin-bottom:6px">📌 Mantle is always included. Select up to 4 competitors to compare (max 5 chains total).</div>', unsafe_allow_html=True)
    selected_chains = st.multiselect(
        "Select competitors (max 4):",
        options=[c for c in all_chain_names if c != "Mantle"],
        default=[c for c in DEFAULT_CHAINS if c != "Mantle"],
        max_selections=4,
        key="chain_selector"
    )
    # Always include Mantle first
    selected_chains = ["Mantle"] + [c for c in selected_chains if c != "Mantle"]

    if len(selected_chains) < 2:
        st.warning("Please select at least one competitor to compare.")
        return

    # Build active chain config
    active_chains = {name: CHAIN_COLORS[name] for name in selected_chains}

    start, end, period = date_controls("t2")
    start_iso, end_iso = iso_range(start, end)
    days = (end - start).days + 1
    prev_s_iso, prev_e_iso = iso_range(start - timedelta(days=days), start - timedelta(days=1))
    si7, ei7 = search_iso()
    anthropic_key = get_anthropic_key()

    all_data = {}
    with st.spinner("Fetching all chains…"):
        for name, color in active_chains.items():
            handle = CHAIN_HANDLES[name]
            u = get_user(handle, token)
            uid = u.get("id", "")
            tw = get_tweets(uid, token, start_iso, end_iso) if uid else []
            ptw = get_tweets(uid, token, prev_s_iso, prev_e_iso) if uid else []
            all_data[name] = {"user":u, "tweets":tw, "prev":ptw, "color":color, "handle":handle}

    # Classify narratives for all chains
    with st.spinner("Classifying narratives with AI…"):
        for name, d in all_data.items():
            if d["tweets"]:
                d["tweets"] = classify_tweets_narratives(d["tweets"], anthropic_key)

    # Alerts
    for name, d in all_data.items():
        alerts = check_alerts(d["tweets"], name)
        if alerts:
            render_alerts(alerts, name, d["color"])

    # KPI snapshot
    st.markdown('<div class="section-title">Performance Snapshot</div>', unsafe_allow_html=True)
    cols = st.columns(len(active_chains))
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
          <div style="font-size:11px;color:#4A7A5A;font-weight:500;margin-bottom:2px">Followers</div>
          <div style="font-size:20px;font-weight:800;color:#0D3320;margin-bottom:10px">{fmt(followers)}</div>
          <div style="font-size:11px;color:#4A7A5A;font-weight:500;margin-bottom:2px">Total views</div>
          <div style="font-size:20px;font-weight:800;color:{color}">{fmt(total_v)}</div>
          <div style="font-size:12px;{dcls};margin-top:4px;font-weight:600">{arrow} {abs(delta):.1f}% vs prev</div>
          <div style="font-size:11px;color:#4A7A5A;font-weight:500;margin-top:8px">{len(d['tweets'])} posts</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    # Views line chart — RIGHT AFTER KPI
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
                                 font=dict(size=13, color="#0D3320"), x=0))
    st.plotly_chart(fig, use_container_width=True)

    # Narrative Breakdown by Chain — 3 per row
    st.markdown('<div class="section-title">Narrative Breakdown by Chain</div>', unsafe_allow_html=True)
    chain_list = list(all_data.items())
    for row_start in range(0, len(chain_list), 3):
        row_chains = chain_list[row_start:row_start+3]
        cols = st.columns(len(row_chains))
        for col, (name, d) in zip(cols, row_chains):
            color = d["color"]
            counts = Counter(get_narrative(t) for t in d["tweets"])
            sorted_n = sorted(counts.items(), key=lambda x:-x[1])[:6]
            total = sum(counts.values()) or 1
            with col:
                if not sorted_n:
                    st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED}">{name}: no data</div>', unsafe_allow_html=True)
                    continue
                # Pad đến đúng 6 bars để mọi chart đồng đều height
                MAX_BARS = 6
                sorted_n_padded = sorted_n + [("", 0)] * (MAX_BARS - len(sorted_n))
                labels = [n for n,_ in sorted_n_padded]
                values = [c for _,c in sorted_n_padded]
                pcts = [c/total*100 for c in values]
                labels_display = [l[:13]+"…" if len(l) > 14 else l for l in labels]
                fig = go.Figure(go.Bar(
                    x=pcts, y=labels_display, orientation='h',
                    marker_color=[get_nar_color(n) if n else "rgba(0,0,0,0)" for n in labels],
                    text=[f"{p:.0f}%" if p > 0 else "" for p in pcts],
                    textposition="outside",
                    textfont=dict(size=9),
                    hovertemplate="%{y}: %{x:.1f}% (%{customdata} posts)<extra></extra>",
                    customdata=values,
                ))
                fig.update_layout(
                    paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                    font=dict(color="#2D6A4F", size=9, family="Inter"),
                    height=240,
                    showlegend=False,
                    margin=dict(l=0, r=44, t=28, b=0),
                    xaxis=dict(gridcolor="#C8EAD8", showgrid=True, zeroline=False,
                               tickfont=dict(size=8, color="#2D6A4F"),
                               ticksuffix="%", range=[0, max(pcts)*1.45] if max(pcts) > 0 else [0, 100]),
                    yaxis=dict(tickfont=dict(color="#0D3320", size=9),
                               showgrid=False, zeroline=False, autorange="reversed"),
                    title=dict(text=f"<b>{name}</b>",
                               font=dict(size=12, color=color), x=0)
                )
                st.plotly_chart(fig, use_container_width=True)

    # ── AI Content Comparison (single call, covers all chains) ──────────────
    st.markdown('<div class="section-title">🤖 AI Content Analysis & Comparison</div>', unsafe_allow_html=True)
    if not anthropic_key:
        st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets to enable AI analysis.")
    else:
        with st.spinner("Running AI content analysis…"):
            chains_for_ai = {}
            for name, d in all_data.items():
                chains_for_ai[name] = {
                    "tweets": d["tweets"][:15],
                    "followers": d["user"].get("public_metrics",{}).get("followers_count",0) or 0,
                    "total_views": sum(get_imp(t) for t in d["tweets"]),
                }
            comparison = ai_content_comparison(
                tuple((k, {
                    "tweets": [{
                        "text": t.get("text",""),
                        "narrative": t.get("narrative","Other"),
                        "public_metrics": t.get("public_metrics",{})
                    } for t in v["tweets"]],
                    "followers": v["followers"],
                    "total_views": v["total_views"],
                }) for k, v in chains_for_ai.items()),
                anthropic_key
            )
        render_content_comparison(comparison)

    # Per-chain Content SWOT
    st.markdown('<div class="section-title">📋 Content Strengths & Weaknesses by Chain</div>', unsafe_allow_html=True)
    if not anthropic_key:
        st.warning("Add ANTHROPIC_API_KEY to enable AI analysis.")
    else:
        # Build batch data for all chains
        batch_data = []
        for name, d in all_data.items():
            tweets = d["tweets"]
            if not tweets: continue
            total_v = sum(get_imp(t) for t in tweets)
            total_e = sum(eng(t.get("public_metrics",{})) for t in tweets)
            eng_rate = round(total_e / total_v * 100, 2) if total_v else 0
            followers = d["user"].get("public_metrics",{}).get("followers_count",0) or 0
            top_nar = Counter(get_narrative(t) for t in tweets).most_common(1)
            top_nar_name = top_nar[0][0] if top_nar else "—"
            batch_data.append((
                name,
                tuple({"text": t.get("text",""), "narrative": t.get("narrative",""),
                       "public_metrics": t.get("public_metrics",{})} for t in tweets),
                tuple({"followers": followers, "total_views": total_v,
                       "eng_rate": eng_rate, "top_narrative": top_nar_name}.items())
            ))

        with st.spinner("Analyzing content for all chains…"):
            swot_results = ai_chains_swot_batch(tuple(batch_data), anthropic_key)

        for name, d in all_data.items():
            color = d["color"]
            swot = swot_results.get(name)
            if swot:
                render_chain_swot(name, swot, color)
            elif not d["tweets"]:
                st.markdown(f'<div style="font-size:12px;color:{MANTLE_MUTED};margin-bottom:6px">{name}: no data</div>', unsafe_allow_html=True)
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
    mcols = st.columns(len(active_chains))
    for col, (name, d) in zip(mcols, all_data.items()):
        handle = d["handle"]
        if name == "Base":
            q = '"Base chain" OR "Base blockchain" OR "build on Base" (crypto OR blockchain OR web3) -from:base -is:retweet lang:en min_faves:50'
        elif name == "Solana":
            q = '(#Solana OR "Solana network" OR "SOL blockchain") (crypto OR blockchain OR defi OR web3) -from:solana -is:retweet lang:en min_faves:50'
        elif name == "Ondo":
            q = '(#Ondo OR "Ondo Finance" OR USDY OR OUSG) (crypto OR blockchain OR rwa OR defi) -from:OndoFinance -is:retweet lang:en min_faves:20'
        elif name == "Mantle":
            q = '(#Mantle OR "Mantle network" OR "Mantle blockchain" OR mETH) (crypto OR blockchain OR defi OR web3) -from:Mantle_Official -is:retweet lang:en min_faves:20'
        else:
            q = f'(#{name} OR "{name} network" OR "{name} blockchain") (crypto OR blockchain OR defi OR web3) -from:{handle} -is:retweet lang:en min_faves:20'
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
        all_tweets_exp = []
        all_nar_comp = Counter()
        for name, d in all_data.items():
            for t in d["tweets"]: t["chain"] = name
            all_tweets_exp.extend(d["tweets"])
            for t in d["tweets"]: all_nar_comp.update([get_narrative(t)])
        html = generate_html_report(
                "Competitive Analysis", f"{start} to {end}",
                {name: fmt(sum(get_imp(t) for t in d["tweets"])) + " views" for name, d in all_data.items()},
                sorted(all_tweets_exp, key=get_imp, reverse=True),
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

    # Classify narratives
    anthropic_key = get_anthropic_key()
    if filtered:
        with st.spinner("Classifying narratives with AI…"):
            filtered = classify_tweets_narratives(filtered, anthropic_key)

    sorted_posts = sorted(filtered, key=get_imp, reverse=True)

    st.caption(f"Found {len(filtered)} research posts from {len(RESEARCH_ACCOUNTS)} accounts")

    if not filtered:
        st.warning("No research posts found. Try adjusting the date range.")
        return

    # Narrative distribution
    nar_counts = Counter(get_narrative(p) for p in filtered)
    nar_counts.pop("Other", None)

    if nar_counts:
        st.markdown('<div class="section-title">Narrative Distribution — All Research Posts</div>', unsafe_allow_html=True)
        sn = sorted(nar_counts.items(), key=lambda x:-x[1])
        total_n = sum(v for _,v in sn) or 1
        fb = go.Figure(go.Bar(
            x=[n for n,_ in sn],
            y=[c/total_n*100 for _,c in sn],
            marker_color=[get_nar_color(n) for n,_ in sn],
            text=[f"{c/total_n*100:.0f}%" for _,c in sn],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f}% (%{customdata} posts)<extra></extra>",
            customdata=[c for _,c in sn]))
        fb.update_layout(**BASE_LAYOUT, height=240, showlegend=False,
                         xaxis=AXIS, yaxis=dict(**AXIS, ticksuffix="%"),
                         title=dict(text=f"Narrative distribution — {len(filtered)} posts",
                                    font=dict(size=13, color="#0D3320"), x=0))
        st.plotly_chart(fb, use_container_width=True)

    st.markdown('<div class="section-title">Top 15 Research Posts by Views</div>', unsafe_allow_html=True)
    for i, t in enumerate(sorted_posts[:15], 1):
        render_post(t, i, "#A0C8B0", is_user=True)

    # Export
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    if st.button("📥 Download HTML Report — Research", key="export_t3"):
        html = generate_html_report(
                "Industry Research", f"{start} to {end}",
                {"Total Posts": str(len(filtered)),
                 "Top Views": fmt(get_imp(sorted_posts[0])) if sorted_posts else "0",
                 "Accounts": str(len(RESEARCH_ACCOUNTS))},
                sorted_posts, nar_counts
            )
        st.download_button("💾 Save Report", html, file_name=f"research_report_{start}_{end}.html",
                           mime="text/html", key="dl_t3")

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    token = get_token()
    st.markdown(f"""
    <div class="header-bar">
      <div style="display:flex;align-items:center;gap:14px">
        <img src="data:image/jpeg;base64,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" style="width:48px;height:48px;border-radius:10px;object-fit:cover;flex-shrink:0">
        <div>
          <div style="font-size:22px;font-weight:800;color:#0D3320;letter-spacing:-0.5px">Mantle Social Intelligence</div>
          <div style="font-size:12px;color:#4A7A5A;margin-top:2px;font-weight:500">Mantle · Solana · Base · Ondo &nbsp;·&nbsp; X API v2</div>
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



# ── TAB 4 INTELLIGENCE FEED ───────────────────────────────────────────────────

INTEL_ACCOUNTS = {
    "Research & Media": ["a16zcrypto","MessariCrypto","TheBlockCo","Delphi_Digital","glassnode",
                         "WuBlockchain","CoinDesk","Decrypt_Co","Cointelegraph","BitcoinMagazine"],
    "Chains":           ["Mantle_Official","solana","base","OndoFinance","ethereum","arbitrum","0xPolygon"],
    "Institutional":    ["coinbase","circle","Ripple","GrayscaleInvest","paradigm","RealVision","SkyBridge"],
}

IMPACT_KW = [
    "partnership","acquisition","raises","launch","launches","listed","listing",
    "etf","sec","regulation","approved","billion","million","integration",
    "institutional","blackrock","fidelity","jpmorgan","goldman","tokenized",
    "mainnet","upgrade","hack","exploit","vulnerability","airdrop","merge",
    "alliance","collaboration","strategic","invest","fund","backed",
]

@st.cache_data(ttl=600)
def fetch_intel_tweets(token, start_iso, end_iso):
    """Fetch tweets from all intelligence accounts"""
    all_tweets = []
    for category, handles in INTEL_ACCOUNTS.items():
        for handle in handles:
            u = get_user(handle, token)
            uid = u.get("id","")
            if not uid: continue
            tw = get_tweets(uid, token, start_iso, end_iso, max_results=50)
            for t in tw:
                t["author_handle"] = handle
                t["author_category"] = category
                t["author_followers"] = u.get("public_metrics",{}).get("followers_count",0) or 0
            all_tweets.extend(tw)
    return all_tweets

def impact_score(t):
    """Score a tweet by reach + source credibility + content signal"""
    m = t.get("public_metrics", {})
    views = get_imp(t)
    eng_val = eng(m)
    followers = t.get("author_followers", 0)
    text = t.get("text","").lower()

    # Content signal — count impact keywords
    kw_hits = sum(1 for k in IMPACT_KW if k in text)

    # Source credibility — institutional > research > chains
    cat = t.get("author_category","")
    cred = {"Institutional": 3, "Research & Media": 2, "Chains": 1}.get(cat, 1)

    # Normalize and combine
    reach_score = min(views / 100_000, 10)
    eng_score = min(eng_val / 1_000, 5)
    kw_score = min(kw_hits * 2, 6)
    cred_score = cred

    return reach_score + eng_score + kw_score + cred_score

@st.cache_data(ttl=1800)
def ai_market_intelligence(tweets_tuple, anthropic_key):
    """Claude analyzes market-wide intelligence"""
    if not anthropic_key or not tweets_tuple: return None
    tweets = list(tweets_tuple)

    # Prepare sample — top 40 by impact score
    sample = sorted(tweets, key=impact_score, reverse=True)[:40]
    tweets_text = "\n---\n".join([
        f"[{t.get('author_category','?')} @{t.get('author_handle','')}] {t.get('text','')[:200]}"
        for t in sample
    ])

    prompt = f"""You are a crypto market intelligence analyst. Analyze these {len(sample)} tweets from top crypto accounts this week.

TWEETS:
{tweets_text}

Respond ONLY with this JSON (keep each string concise, under 80 words):
{{
  "top_narratives": [
    {{"name": "narrative name", "momentum": "Rising/Stable/Fading", "summary": "why this narrative is moving", "key_accounts": ["account1", "account2"]}}
  ],
  "alpha_signals": [
    {{"signal": "specific alpha signal or early trend", "why_important": "why this matters before mainstream", "source": "@account"}}
  ],
  "institutional_moves": [
    {{"institution_or_signal": "who or what signal", "action": "what they did or said", "implication": "what this means for crypto"}}
  ],
  "top5_news": [
    {{"headline": "concise headline", "source": "@account", "impact": "High/Medium", "why_impactful": "1 sentence"}}
  ],
  "market_summary": "3-4 sentences overall market intelligence summary for the week"
}}

JSON only, no markdown."""

    import time, json, re as re4
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2000,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=45
            )
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code == 200:
                raw = r.json()["content"][0]["text"].strip()
                raw = re4.sub(r'^```(?:json)?\s*', '', raw)
                raw = re4.sub(r'\s*```$', '', raw)
                return json.loads(raw.strip())
            return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            if attempt == 2: return {"_error": str(e)}
            time.sleep(10)
    return {"_error": "Rate limit — wait 1 min and refresh"}

def find_best_match_tweet(text_signal, all_tweets, category_filter=None):
    """Find the tweet that best matches an AI-generated signal text"""
    if not text_signal or not all_tweets:
        return None
    signal_words = set(re.findall(r'\b\w{4,}\b', text_signal.lower()))
    best_tweet = None
    best_score = 0
    for t in all_tweets:
        if category_filter and t.get("author_category") != category_filter:
            continue
        tweet_words = set(re.findall(r'\b\w{4,}\b', t.get("text","").lower()))
        overlap = len(signal_words & tweet_words)
        if overlap > best_score:
            best_score = overlap
            best_tweet = t
    if best_score >= 2:
        return best_tweet
    return None

def tweet_link(t):
    if not t: return "#"
    handle = t.get("author_handle","")
    tid = t.get("id","")
    return f"https://x.com/{handle}/status/{tid}" if tid else "#"

def render_intel_analysis(analysis, all_tweets):
    if not analysis: return
    if "_error" in analysis:
        st.error(f"AI Error: {analysis['_error']}")
        return

    # Market Summary
    st.markdown(f"""
    <div style="background:#E8F5EE;border:1px solid #C8EAD8;border-left:4px solid #00A572;border-radius:10px;padding:16px 18px;margin-bottom:16px">
      <div style="font-size:11px;font-weight:800;color:#00A572;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px">📡 Market Intelligence Summary</div>
      <div style="font-size:13px;color:#0D3320;line-height:1.7">{analysis.get("market_summary","")}</div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1,1])

    # Top Narratives
    with c1:
        st.markdown('<div class="section-title">🔥 Key Narratives & Momentum</div>', unsafe_allow_html=True)
        for n in analysis.get("top_narratives", [])[:5]:
            mom = n.get("momentum","")
            mom_color = {"Rising":"#00A572","Stable":"#f59e0b","Fading":"#f87171"}.get(mom,"#6b7280")
            accounts = " ".join([f'<span style="color:#4A7A5A;font-size:10px">@{a}</span>' for a in n.get("key_accounts",[])])
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #C8EAD8;border-radius:8px;padding:12px;margin-bottom:8px">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <span style="font-size:13px;font-weight:700;color:#0D3320">{n.get("name","")}</span>
                <span style="background:{mom_color}22;color:{mom_color};border:1px solid {mom_color}44;padding:1px 8px;border-radius:99px;font-size:10px;font-weight:700">{mom}</span>
              </div>
              <div style="font-size:12px;color:#4A7A5A;line-height:1.5;margin-bottom:6px">{n.get("summary","")}</div>
              <div>{accounts}</div>
            </div>""", unsafe_allow_html=True)

    # Alpha Signals
    with c2:
        st.markdown('<div class="section-title">⚡ Alpha Signals</div>', unsafe_allow_html=True)
        for s in analysis.get("alpha_signals", [])[:5]:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #C8EAD8;border-left:3px solid #8b5cf6;border-radius:8px;padding:12px;margin-bottom:8px">
              <div style="font-size:12px;font-weight:700;color:#0D3320;margin-bottom:4px">{s.get("signal","")}</div>
              <div style="font-size:11px;color:#4A7A5A;line-height:1.5;margin-bottom:4px">{s.get("why_important","")}</div>
              <div style="font-size:10px;color:#8b5cf6;font-weight:600">via {s.get("source","")}</div>
            </div>""", unsafe_allow_html=True)

    # Institutional Moves
    st.markdown('<div class="section-title">🏦 Institutional Moves</div>', unsafe_allow_html=True)
    inst_list = analysis.get("institutional_moves", [])
    if inst_list:
        icols = st.columns(min(len(inst_list), 3))
        for col, item in zip(icols, inst_list[:3]):
            signal_text = f"{item.get('institution_or_signal','')} {item.get('action','')}"
            matched = find_best_match_tweet(signal_text, all_tweets, "Institutional")
            link = tweet_link(matched)
            matched_handle = f"@{matched.get('author_handle','')}" if matched else ""
            with col:
                st.markdown(f"""
                <div style="background:#FFFFFF;border:1px solid #C8EAD8;border-left:3px solid #06b6d4;border-radius:8px;padding:12px">
                  <div style="font-size:12px;font-weight:700;color:#0D3320;margin-bottom:4px">{item.get("institution_or_signal","")}</div>
                  <div style="font-size:11px;color:#4A7A5A;margin-bottom:6px">{item.get("action","")}</div>
                  <div style="font-size:11px;color:#06b6d4;font-weight:600;margin-bottom:8px">→ {item.get("implication","")}</div>
                  <a href="{link}" target="_blank" style="font-size:10px;color:#06b6d4;text-decoration:none;padding:3px 10px;border:1px solid #06b6d444;border-radius:6px;background:#06b6d411;font-weight:600">{'↗ ' + matched_handle if matched else '↗ View source'}</a>
                </div>""", unsafe_allow_html=True)

    # Top 5 News
    st.markdown('<div class="section-title">📰 Top 5 Impactful News This Week</div>', unsafe_allow_html=True)
    for i, news in enumerate(analysis.get("top5_news", [])[:5], 1):
        impact = news.get("impact","Medium")
        ic = "#f87171" if impact == "High" else "#f59e0b"
        signal_text = f"{news.get('headline','')} {news.get('why_impactful','')}"
        matched = find_best_match_tweet(signal_text, all_tweets)
        link = tweet_link(matched)
        matched_handle = f"@{matched.get('author_handle','')}" if matched else ""
        st.markdown(f"""
        <div style="display:flex;gap:12px;align-items:flex-start;background:#FFFFFF;border:1px solid #C8EAD8;border-radius:8px;padding:12px;margin-bottom:6px">
          <span style="font-size:16px;font-weight:800;color:#C8EAD8;min-width:24px">#{i}</span>
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">
              <span style="font-size:13px;font-weight:700;color:#0D3320">{news.get("headline","")}</span>
              <span style="background:{ic}22;color:{ic};border:1px solid {ic}44;padding:1px 8px;border-radius:99px;font-size:10px;font-weight:700">{impact}</span>
            </div>
            <div style="font-size:11px;color:#4A7A5A;margin-bottom:6px">{news.get("why_impactful","")}</div>
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:10px;color:#00A572;font-weight:600">{news.get("source","")}</span>
              <a href="{link}" target="_blank" style="font-size:10px;color:#00A572;text-decoration:none;padding:2px 8px;border:1px solid #00A57244;border-radius:6px;background:#00A57211;font-weight:600">↗ {'View · ' + matched_handle if matched else 'View source'}</a>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    # Top posts by impact score
    st.markdown('<div class="section-title">🏆 Top Posts by Impact Score</div>', unsafe_allow_html=True)
    top_posts = sorted(all_tweets, key=impact_score, reverse=True)[:9]
    cols = st.columns(3)
    for i, (col, t) in enumerate(zip(cols * 3, top_posts), 1):
        cat = t.get("author_category","")
        cat_color = {"Institutional":"#06b6d4","Research & Media":"#8b5cf6","Chains":MANTLE_GREEN}.get(cat,"#6b7280")
        with col:
            render_post(t, i, cat_color, is_user=True)

def tab_intel(token):
    tab_description(
        "Market Intelligence Feed",
        "Aggregates signals from research firms, chain ecosystems, and institutional accounts. AI analyzes key narratives, alpha signals, institutional moves, and top impactful news of the week.",
        ["Research accounts","Chain officials","Institutional signals"],
        "Custom date range (user-selected, max 7 days due to X API limit)"
    )

    start, end, _ = date_controls("t4")
    start_iso, end_iso = iso_range(start, end)
    anthropic_key = get_anthropic_key()

    # Fetch all intel tweets
    total_accounts = sum(len(v) for v in INTEL_ACCOUNTS.values())
    with st.spinner(f"Fetching data from {total_accounts} accounts across Research, Chains & Institutional…"):
        all_tweets = fetch_intel_tweets(token, start_iso, end_iso)

    st.caption(f"Fetched {len(all_tweets)} posts from {total_accounts} accounts · {start} → {end}")

    if not all_tweets:
        st.warning("No data found. Check API token.")
        return

    # Classify narratives
    if all_tweets:
        with st.spinner("Classifying narratives with AI…"):
            all_tweets = classify_tweets_narratives(all_tweets, anthropic_key)

    # Stats row
    k1, k2, k3, k4 = st.columns(4)
    research_tw = [t for t in all_tweets if t.get("author_category") == "Research & Media"]
    chain_tw = [t for t in all_tweets if t.get("author_category") == "Chains"]
    inst_tw = [t for t in all_tweets if t.get("author_category") == "Institutional"]
    high_impact = [t for t in all_tweets if impact_score(t) >= 5]

    kpi(k1, "Total posts", str(len(all_tweets)), sub="all sources")
    kpi(k2, "Research posts", str(len(research_tw)), sub="a16z, Messari, CoinDesk…")
    kpi(k3, "Institutional signals", str(len(inst_tw)), sub="Coinbase, Circle, Ripple…")
    kpi(k4, "High-impact posts", str(len(high_impact)), sub="impact score ≥ 5", color="#f59e0b")

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    # Narrative distribution chart
    st.markdown('<div class="section-title">Narrative Distribution — All Sources</div>', unsafe_allow_html=True)
    nar_counts = Counter(get_narrative(t) for t in all_tweets)
    sorted_nar = sorted(nar_counts.items(), key=lambda x:-x[1])
    total_nar = sum(v for _,v in sorted_nar) or 1

    nc1, nc2 = st.columns([2,1])
    with nc1:
        fig_nar = go.Figure(go.Bar(
            x=[n for n,_ in sorted_nar],
            y=[c for _,c in sorted_nar],
            marker_color=[get_nar_color(n) for n,_ in sorted_nar],
            text=[f"{c/total_nar*100:.0f}%" for _,c in sorted_nar],
            textposition="outside",
            hovertemplate="%{x}: %{y} posts (%{text})<extra></extra>",
        ))
        fig_nar.update_layout(**BASE_LAYOUT, height=260, showlegend=False,
                              xaxis=AXIS, yaxis=AXIS,
                              title=dict(text="Narrative volume across all intelligence sources",
                                         font=dict(size=13,color="#0D3320"), x=0))
        st.plotly_chart(fig_nar, use_container_width=True)

    with nc2:
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        for name, cnt in sorted_nar[:10]:
            c = get_nar_color(name)
            pct = cnt / total_nar * 100
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
              <div style="width:10px;height:10px;border-radius:2px;background:{c};flex-shrink:0"></div>
              <div style="flex:1;font-size:12px;color:#0D3320;font-weight:500">{name}</div>
              <div style="font-size:11px;color:#4A7A5A">{cnt} posts</div>
              <div style="width:60px;background:#C8EAD8;border-radius:4px;height:5px">
                <div style="width:{pct}%;background:{c};border-radius:4px;height:5px"></div>
              </div>
              <div style="font-size:11px;color:{c};font-weight:700;min-width:32px">{pct:.0f}%</div>
            </div>""", unsafe_allow_html=True)

    # Narrative breakdown by category
    st.markdown('<div class="section-title">Narrative by Source Category</div>', unsafe_allow_html=True)
    cat_cols = st.columns(3)
    for col, (cat_name, cat_tweets) in zip(cat_cols, [
        ("Research & Media", research_tw),
        ("Chains", chain_tw),
        ("Institutional", inst_tw)
    ]):
        cat_color = {"Institutional":"#06b6d4","Research & Media":"#8b5cf6","Chains":MANTLE_GREEN}.get(cat_name,"#6b7280")
        cat_nar = Counter(get_narrative(t) for t in cat_tweets)
        cat_sorted = sorted(cat_nar.items(), key=lambda x:-x[1])[:6]
        cat_total = sum(v for _,v in cat_sorted) or 1
        with col:
            st.markdown(f'<div style="font-size:12px;font-weight:800;color:{cat_color};margin-bottom:4px;text-transform:uppercase">{cat_name}</div>', unsafe_allow_html=True)
            # Show account list
            accs = INTEL_ACCOUNTS.get(cat_name, [])
            accs_str = " · ".join([f"@{a}" for a in accs])
            st.markdown(f'<div style="font-size:10px;color:#4A7A5A;margin-bottom:8px;line-height:1.5">{accs_str}</div>', unsafe_allow_html=True)
            if cat_sorted:
                fp = go.Figure(go.Pie(
                    labels=[n for n,_ in cat_sorted],
                    values=[c for _,c in cat_sorted],
                    marker=dict(colors=[get_nar_color(n) for n,_ in cat_sorted],
                                line=dict(color="#FFFFFF", width=2)),
                    textfont_size=10, textfont_color="#0D3320", hole=0.5,
                    hovertemplate="%{label}: %{value} posts (%{percent})<extra></extra>"))
                pl = {k:v for k,v in BASE_LAYOUT.items() if k not in ("margin","legend")}
                fp.update_layout(**pl, height=200, showlegend=False,
                                 margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fp, use_container_width=True)
                top = cat_sorted[0]
                tc = get_nar_color(top[0])
                st.markdown(f'<div style="text-align:center;font-size:11px;color:{tc};font-weight:700">#1 {top[0]} · {top[1]/cat_total*100:.0f}%</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:#4A7A5A">No data</div>', unsafe_allow_html=True)

    # AI Analysis
    st.markdown('<div class="section-title">🤖 AI Market Intelligence Analysis</div>', unsafe_allow_html=True)
    if not anthropic_key:
        st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets to enable AI analysis.")
    else:
        with st.spinner("Running AI market intelligence analysis… (may take 15-30s)"):
            tweets_for_ai = tuple(
                {"text": t.get("text",""), "author_handle": t.get("author_handle",""),
                 "author_category": t.get("author_category",""),
                 "author_followers": t.get("author_followers",0),
                 "public_metrics": t.get("public_metrics",{})}
                for t in all_tweets
            )
            analysis = ai_market_intelligence(tweets_for_ai, anthropic_key)
        render_intel_analysis(analysis, all_tweets)

    # Export
    st.markdown('<div class="section-title">Export Report</div>', unsafe_allow_html=True)
    if st.button("📥 Download HTML Report — Market Intelligence", key="export_t4"):
        nar_counts_intel = Counter(get_narrative(t) for t in all_tweets)
        html = generate_html_report(
            "Market Intelligence Feed", f"{start} to {end}",
            {"Total Posts": str(len(all_tweets)),
             "High Impact": str(len(high_impact)),
             "Research & Media": str(len(research_tw)),
             "Institutional": str(len(inst_tw))},
            sorted(all_tweets, key=impact_score, reverse=True),
            nar_counts_intel
        )
        st.download_button("💾 Save Report", html, file_name=f"intel_report_{start}_{end}.html",
                           mime="text/html", key="dl_t4")

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    token = get_token()
    logo_b64 = "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"
    st.markdown(f"""
    <div class="header-bar">
      <div style="display:flex;align-items:center;gap:14px">
        <img src="data:image/jpeg;base64,{logo_b64}" style="width:48px;height:48px;border-radius:10px;object-fit:cover;flex-shrink:0">
        <div>
          <div style="font-size:22px;font-weight:800;color:#0D3320;letter-spacing:-0.5px">Mantle Social Intelligence</div>
          <div style="font-size:12px;color:#4A7A5A;margin-top:2px;font-weight:500">Mantle · Solana · Base · Ondo &nbsp;·&nbsp; X API v2</div>
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

    t1, t2, t3 = st.tabs(["📊  Mantle Deep Dive","⚔️  Competitive Analysis","🧠  Market Intelligence"])
    with t1: tab_mantle(token)
    with t2: tab_competitive(token)
    with t3: tab_intel(token)

if __name__ == "__main__":
    main()
