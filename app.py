import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Blockchain Social Listening",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f0f0f; }
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }

    /* Hide streamlit default elements */
    #MainMenu, footer, header { visibility: hidden; }

    /* Metric cards */
    .metric-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 20px 24px;
    }
    .metric-label {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 600;
        color: #ffffff;
        letter-spacing: -0.5px;
    }
    .metric-delta-up { font-size: 12px; color: #4ade80; margin-top: 4px; }
    .metric-delta-dn { font-size: 12px; color: #f87171; margin-top: 4px; }
    .metric-sub { font-size: 12px; color: #666; margin-top: 4px; }

    /* Post cards */
    .post-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        transition: border-color 0.2s;
    }
    .post-card:hover { border-color: #444; }
    .post-rank { font-size: 18px; font-weight: 600; color: #444; margin-right: 8px; }
    .post-author { font-size: 14px; font-weight: 500; color: #fff; }
    .post-handle { font-size: 12px; color: #666; }
    .post-text { font-size: 13px; color: #aaa; line-height: 1.5; margin: 8px 0; }
    .post-stats { font-size: 12px; color: #666; }
    .imp-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 12px;
        font-weight: 500;
    }

    /* Section headers */
    .section-header {
        font-size: 13px;
        font-weight: 500;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Chain buttons */
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 99px !important;
    }

    /* Live badge */
    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #0d2e0d;
        color: #4ade80;
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 12px;
        font-weight: 500;
    }
    .live-dot {
        width: 6px; height: 6px;
        background: #4ade80;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

    /* Divider */
    hr { border-color: #2a2a2a !important; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #111 !important; }
    section[data-testid="stSidebar"] .stSelectbox label { color: #888 !important; }

    /* Plotly chart bg */
    .js-plotly-plot { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
CHAINS = {
    "Mantle":   {"handle": "Mantle_Official", "color": "#534AB7", "badge_bg": "#1a1535"},
    "Solana":   {"handle": "solana",           "color": "#9945FF", "badge_bg": "#1e0f35"},
    "BNB Chain":{"handle": "BNBCHAIN",         "color": "#F0B90B", "badge_bg": "#2e2500"},
    "Arbitrum": {"handle": "arbitrum",         "color": "#378ADD", "badge_bg": "#0d1e35"},
    "Base":     {"handle": "base",             "color": "#0052FF", "badge_bg": "#00103a"},
}

RANGE_OPTIONS = {
    "24 giờ": 1,
    "7 ngày": 7,
    "30 ngày": 30,
}

# ── Twitter API ───────────────────────────────────────────────────────────────
def get_bearer_token():
    try:
        return st.secrets["TWITTER_BEARER_TOKEN"]
    except:
        return None

def twitter_headers(token):
    return {"Authorization": f"Bearer {token}"}

@st.cache_data(ttl=300)  # cache 5 phút
def fetch_user_id(handle, token):
    url = f"https://api.twitter.com/2/users/by/username/{handle}"
    params = {"user.fields": "public_metrics,description"}
    r = requests.get(url, headers=twitter_headers(token), params=params)
    if r.status_code == 200:
        return r.json().get("data", {})
    return {}

@st.cache_data(ttl=300)  # cache 5 phút
def fetch_user_tweets(user_id, token, days=7, max_results=20):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    start_time = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "max_results": min(max_results, 100),
        "start_time": start_time,
        "tweet.fields": "public_metrics,created_at,text",
        "exclude": "retweets,replies"
    }
    r = requests.get(url, headers=twitter_headers(token), params=params)
    if r.status_code == 200:
        return r.json().get("data", [])
    return []

@st.cache_data(ttl=300)
def fetch_mentions(handle, token, days=7, max_results=20):
    url = "https://api.twitter.com/2/tweets/search/recent"
    # search tweets mentioning the chain (không phải từ official account)
    query = f"#{handle} OR @{handle} OR \"{handle}\" -from:{handle} -is:retweet lang:en"
    start_time = (datetime.utcnow() - timedelta(days=min(days, 7))).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "start_time": start_time,
        "tweet.fields": "public_metrics,created_at,author_id,text",
        "expansions": "author_id",
        "user.fields": "username,name"
    }
    r = requests.get(url, headers=twitter_headers(token), params=params)
    if r.status_code == 200:
        data = r.json()
        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        for t in tweets:
            u = users.get(t.get("author_id"), {})
            t["author_name"] = u.get("name", "Unknown")
            t["author_handle"] = u.get("username", "unknown")
        return tweets
    return []

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_number(n):
    if n is None: return "—"
    n = int(n)
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:     return f"{n/1_000_000:.1f}M"
    if n >= 1_000:         return f"{n/1_000:.0f}K"
    return str(n)

def calc_engagement(metrics):
    likes = metrics.get("like_count", 0) or 0
    rts   = metrics.get("retweet_count", 0) or 0
    reps  = metrics.get("reply_count", 0) or 0
    imps  = metrics.get("impression_count", 0) or 0
    if imps > 0:
        return round((likes + rts + reps) / imps * 100, 2)
    # fallback: weighted score
    return likes + rts * 3 + reps * 2

def get_engagement_score(tweet):
    m = tweet.get("public_metrics", {})
    return (m.get("like_count", 0) or 0) * 1 + \
           (m.get("retweet_count", 0) or 0) * 3 + \
           (m.get("reply_count", 0) or 0) * 2 + \
           (m.get("impression_count", 0) or 0) * 0.001

def parse_tweet_date(created_at):
    try:
        return datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        try:
            return datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        except:
            return datetime.utcnow()

def time_ago(created_at):
    dt = parse_tweet_date(created_at)
    diff = datetime.utcnow() - dt
    if diff.days > 0:   return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours > 0:       return f"{hours}h ago"
    mins = diff.seconds // 60
    return f"{mins}m ago"

def render_post_card(tweet, rank, chain_color, badge_bg, is_user=False):
    m    = tweet.get("public_metrics", {})
    text = tweet.get("text", "")[:160] + ("…" if len(tweet.get("text","")) > 160 else "")
    imp  = m.get("impression_count") or (m.get("like_count",0)*50)
    likes= m.get("like_count", 0) or 0
    rts  = m.get("retweet_count", 0) or 0
    reps = m.get("reply_count", 0) or 0
    ago  = time_ago(tweet.get("created_at",""))
    tid  = tweet.get("id","")

    if is_user:
        author  = tweet.get("author_name", "User")
        handle  = tweet.get("author_handle", "user")
        initials= author[:2].upper()
    else:
        handle  = tweet.get("_handle","")
        author  = handle
        initials= handle[:2].upper() if handle else "??"

    link = f"https://x.com/{handle}/status/{tid}" if tid else "#"

    st.markdown(f"""
    <div class="post-card">
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">
            <span class="post-rank">#{rank}</span>
            <div style="width:30px;height:30px;border-radius:50%;background:{badge_bg};
                        border:1px solid {chain_color}44;display:flex;align-items:center;
                        justify-content:center;font-size:10px;font-weight:600;
                        color:{chain_color};flex-shrink:0">{initials}</div>
            <div style="flex:1;min-width:0">
                <div class="post-author">{author}</div>
                <div class="post-handle">@{handle} · {ago}</div>
            </div>
            <span class="imp-badge" style="background:{badge_bg};color:{chain_color}">
                {fmt_number(imp)}
            </span>
        </div>
        <div class="post-text">{text}</div>
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div class="post-stats">
                ♥ {fmt_number(likes)} &nbsp;·&nbsp;
                ↺ {fmt_number(rts)} &nbsp;·&nbsp;
                💬 {fmt_number(reps)}
            </div>
            <a href="{link}" target="_blank"
               style="font-size:11px;color:{chain_color};text-decoration:none;
                      padding:3px 10px;border:1px solid {chain_color}44;
                      border-radius:6px;white-space:nowrap">
                Xem post ↗
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    token = get_bearer_token()

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_live = st.columns([4, 1])
    with col_title:
        st.markdown("## 📡 Blockchain Social Listening")
    with col_live:
        now = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"""
        <div style="text-align:right;padding-top:10px">
            <span class="live-badge">
                <span class="live-dot"></span>
                Live · {now}
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    if not token:
        st.error("⚠️ Chưa có Bearer Token. Vào Settings → Secrets → thêm TWITTER_BEARER_TOKEN.")
        st.code("""
# .streamlit/secrets.toml
TWITTER_BEARER_TOKEN = "your_bearer_token_here"
        """)
        st.stop()

    # ── Sidebar controls ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Filters")
        st.markdown("---")

        selected_chain = st.selectbox(
            "Chain",
            list(CHAINS.keys()),
            index=0
        )

        selected_range_label = st.selectbox(
            "Time range",
            list(RANGE_OPTIONS.keys()),
            index=1
        )
        days = RANGE_OPTIONS[selected_range_label]

        st.markdown("---")
        auto_refresh = st.toggle("Auto-refresh (5 phút)", value=False)
        if st.button("🔄 Refresh now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("**Chains đang monitor:**")
        for name, info in CHAINS.items():
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;
                        padding:6px 0;font-size:13px;color:#aaa">
                <div style="width:8px;height:8px;border-radius:50%;
                            background:{info['color']}"></div>
                {name} · @{info['handle']}
            </div>
            """, unsafe_allow_html=True)

    chain_info = CHAINS[selected_chain]
    color      = chain_info["color"]
    badge_bg   = chain_info["badge_bg"]
    handle     = chain_info["handle"]

    # ── Fetch data ────────────────────────────────────────────────────────────
    with st.spinner(f"Đang fetch data từ @{handle}..."):
        user_data = fetch_user_id(handle, token)

    if not user_data:
        st.error(f"Không fetch được data cho @{handle}. Kiểm tra lại Bearer Token.")
        st.stop()

    user_id   = user_data.get("id")
    followers = user_data.get("public_metrics", {}).get("followers_count", 0)
    tweet_cnt = user_data.get("public_metrics", {}).get("tweet_count", 0)

    with st.spinner("Đang load tweets..."):
        official_tweets = fetch_user_tweets(user_id, token, days=days, max_results=50)
        user_mentions   = fetch_mentions(handle, token, days=min(days,7), max_results=50)

    # Tag tweets với handle
    for t in official_tweets:
        t["_handle"] = handle

    # Sort by engagement
    official_sorted = sorted(official_tweets, key=get_engagement_score, reverse=True)
    mentions_sorted = sorted(user_mentions,   key=get_engagement_score, reverse=True)

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    total_likes = sum(t.get("public_metrics",{}).get("like_count",0) or 0 for t in official_tweets)
    total_rts   = sum(t.get("public_metrics",{}).get("retweet_count",0) or 0 for t in official_tweets)
    total_reps  = sum(t.get("public_metrics",{}).get("reply_count",0) or 0 for t in official_tweets)
    total_imps  = sum(t.get("public_metrics",{}).get("impression_count",0) or 0 for t in official_tweets)
    post_count  = len(official_tweets)

    # Engagement rate
    if total_imps > 0:
        eng_rate = round((total_likes + total_rts + total_reps) / total_imps * 100, 2)
        imp_display = fmt_number(total_imps)
        imp_note = "từ X API"
    else:
        eng_rate = 0
        imp_display = "N/A"
        imp_note = "Pay-per-use plan không trả impression"

    # ── Metric cards ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-size:18px;font-weight:500;color:#fff;margin-bottom:16px">
        <span style="color:{color}">@{handle}</span>
        &nbsp;·&nbsp;
        <span style="font-size:14px;color:#666">{selected_range_label}</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">👥 Followers</div>
            <div class="metric-value" style="color:{color}">{fmt_number(followers)}</div>
            <div class="metric-sub">total account followers</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📝 Số bài đăng</div>
            <div class="metric-value" style="color:{color}">{post_count}</div>
            <div class="metric-sub">trong {selected_range_label}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">❤️ Tổng likes</div>
            <div class="metric-value" style="color:{color}">{fmt_number(total_likes)}</div>
            <div class="metric-sub">trong {selected_range_label}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🔁 Tổng retweets</div>
            <div class="metric-value" style="color:{color}">{fmt_number(total_rts)}</div>
            <div class="metric-sub">trong {selected_range_label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # ── Engagement chart theo ngày ────────────────────────────────────────────
    if official_tweets:
        df = pd.DataFrame([{
            "date": parse_tweet_date(t["created_at"]).date(),
            "likes": t.get("public_metrics",{}).get("like_count",0) or 0,
            "retweets": t.get("public_metrics",{}).get("retweet_count",0) or 0,
            "replies": t.get("public_metrics",{}).get("reply_count",0) or 0,
        } for t in official_tweets])

        df_daily = df.groupby("date").sum().reset_index()
        df_daily["engagement"] = df_daily["likes"] + df_daily["retweets"]*3 + df_daily["replies"]*2

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_daily["date"],
            y=df_daily["likes"],
            name="Likes",
            marker_color=color,
        ))
        fig.add_trace(go.Bar(
            x=df_daily["date"],
            y=df_daily["retweets"],
            name="Retweets",
            marker_color=color,
        ))
        fig.add_trace(go.Bar(
            x=df_daily["date"],
            y=df_daily["replies"],
            name="Replies",
            marker_color=color,
        ))
        fig.update_layout(
            barmode="stack",
            paper_bgcolor="#1a1a1a",
            plot_bgcolor="#1a1a1a",
            font_color="#aaa",
            font_size=12,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
            margin=dict(l=10, r=10, t=30, b=10),
            height=240,
            xaxis=dict(gridcolor="#2a2a2a", showgrid=False),
            yaxis=dict(gridcolor="#2a2a2a"),
            title=dict(text=f"Engagement theo ngày — @{handle}", font_size=13, x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Comparison chart ──────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 📊 So sánh engagement — tất cả chains")

    with st.spinner("Đang fetch data tất cả chains để so sánh..."):
        comparison_data = []
        for chain_name, cinfo in CHAINS.items():
            u = fetch_user_id(cinfo["handle"], token)
            if u:
                m = u.get("public_metrics", {})
                comparison_data.append({
                    "chain": chain_name,
                    "followers": m.get("followers_count", 0) or 0,
                    "tweet_count": m.get("tweet_count", 0) or 0,
                    "color": cinfo["color"],
                })

    if comparison_data:
        df_comp = pd.DataFrame(comparison_data)

        tab1, tab2 = st.tabs(["👥 Followers", "📝 Total tweets"])

        with tab1:
            fig2 = go.Figure(go.Bar(
                x=df_comp["chain"],
                y=df_comp["followers"],
                marker_color=df_comp["color"].tolist(),
                text=[fmt_number(v) for v in df_comp["followers"]],
                textposition="outside",
                textfont=dict(size=12, color="#aaa"),
            ))
            fig2.update_layout(
                paper_bgcolor="#1a1a1a", plot_bgcolor="#1a1a1a",
                font_color="#aaa", font_size=12,
                margin=dict(l=10, r=10, t=20, b=10), height=300,
                showlegend=False,
                xaxis=dict(gridcolor="#2a2a2a", showgrid=False),
                yaxis=dict(gridcolor="#2a2a2a", tickformat=".2s"),
            )
            st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            fig3 = go.Figure(go.Bar(
                x=df_comp["chain"],
                y=df_comp["tweet_count"],
                marker_color=df_comp["color"].tolist(),
                text=[fmt_number(v) for v in df_comp["tweet_count"]],
                textposition="outside",
                textfont=dict(size=12, color="#aaa"),
            ))
            fig3.update_layout(
                paper_bgcolor="#1a1a1a", plot_bgcolor="#1a1a1a",
                font_color="#aaa", font_size=12,
                margin=dict(l=10, r=10, t=20, b=10), height=300,
                showlegend=False,
                xaxis=dict(gridcolor="#2a2a2a", showgrid=False),
                yaxis=dict(gridcolor="#2a2a2a", tickformat=".2s"),
            )
            st.plotly_chart(fig3, use_container_width=True)

    # ── Top posts ─────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)

    col_off, col_usr = st.columns(2)

    with col_off:
        st.markdown(f"""
        <div class="section-header">
            <div style="width:20px;height:20px;border-radius:6px;
                        background:{badge_bg};border:1px solid {color}44;
                        display:flex;align-items:center;justify-content:center;
                        font-size:11px">🏢</div>
            Official account — top 3 posts
        </div>
        """, unsafe_allow_html=True)

        if official_sorted:
            for i, tweet in enumerate(official_sorted[:3], 1):
                render_post_card(tweet, i, color, badge_bg, is_user=False)
        else:
            st.markdown("<div style='color:#666;font-size:13px'>Không có data</div>", unsafe_allow_html=True)

    with col_usr:
        st.markdown(f"""
        <div class="section-header">
            <div style="width:20px;height:20px;border-radius:6px;
                        background:#0d2e1a;border:1px solid #1D9E7544;
                        display:flex;align-items:center;justify-content:center;
                        font-size:11px">👥</div>
            Users / KOL — top 3 posts
        </div>
        """, unsafe_allow_html=True)

        if mentions_sorted:
            for i, tweet in enumerate(mentions_sorted[:3], 1):
                render_post_card(tweet, i, "#1D9E75", "#0d2e1a", is_user=True)
        else:
            st.markdown("""
            <div style='color:#666;font-size:13px'>
                Không tìm thấy mentions trong 7 ngày qua.<br>
                <span style='font-size:11px;color:#444'>
                Search API chỉ trả về 7 ngày gần nhất.
                </span>
            </div>
            """, unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;
                font-size:11px;color:#444;padding:4px 0">
        <span>Data từ X API v2 · Pay-per-use</span>
        <span>Cache 5 phút · Updated {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</span>
    </div>
    """, unsafe_allow_html=True)

    # Auto refresh
    if auto_refresh:
        time.sleep(300)
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
