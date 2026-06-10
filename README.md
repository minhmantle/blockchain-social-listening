# Blockchain Social Listening Dashboard

Dashboard realtime theo dõi Twitter/X của các blockchain chains: Mantle, Solana, BNB Chain, Arbitrum, Base.

## Features
- Metric cards: followers, post count, likes, retweets
- Engagement chart theo ngày
- So sánh tất cả chains cùng 1 biểu đồ
- Top 3 official posts + top 3 user/KOL posts
- Filter theo chain và time range
- Auto-refresh mỗi 5 phút

## Deploy lên Streamlit Cloud

1. Fork/push repo này lên GitHub
2. Vào [streamlit.io](https://streamlit.io) → New app → chọn repo này
3. Vào Settings → Secrets → paste:

```toml
TWITTER_BEARER_TOKEN = "your_bearer_token_here"
```

4. Click Deploy → share link cho team

## Data source
X API v2 · Pay-per-use · Cache 5 phút
