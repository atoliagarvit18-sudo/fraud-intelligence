"""
app/config/constants.py

Single source of truth for all constants used by Agent 2.
Import from here — never hardcode these strings elsewhere.
"""

# ---------------------------------------------------------------------------
# MongoDB collection names
# ---------------------------------------------------------------------------

RAW_POSTS:        str = "raw_posts"
PROCESSED_POSTS:  str = "processed_posts"
CLUSTERS:         str = "clusters"
EVENTS:           str = "events"
METADATA:         str = "metadata"
WATCHLIST_SOURCES: str = "watchlist_sources"

# All valid collection names — used by get_collection() to reject typos
VALID_COLLECTIONS: set[str] = {
    RAW_POSTS,
    PROCESSED_POSTS,
    CLUSTERS,
    EVENTS,
    METADATA,
    WATCHLIST_SOURCES,
}

# ---------------------------------------------------------------------------
# Telegram collector
# ---------------------------------------------------------------------------

# Public channel usernames or invite links to monitor.
# Add or remove channels here without touching any other file.
TELEGRAM_CHANNELS: list[str] = [
    "durov",            # example — replace with real fraud-related channels
]

# How long (seconds) to wait between each collection sweep.
POLL_INTERVAL_SECONDS: int = 60

# ---------------------------------------------------------------------------
# Reddit collector
# ---------------------------------------------------------------------------

# Subreddits to monitor for fraud-related posts.
REDDIT_SUBREDDITS: list[str] = [
    "Scams",
    "IndiaInvestments",
    "personalfinanceindia",
    "CryptoCurrency",
]

# Keywords to search for across subreddits.
REDDIT_KEYWORDS: list[str] = [
    "pig butchering",
    "investment scam",
    "fake broker",
    "phishing",
    "ponzi",
    "fraud",
]

# Max posts to collect per keyword per subreddit per run.
REDDIT_LIMIT: int = 50

# ---------------------------------------------------------------------------
# Complaint site collector
# ---------------------------------------------------------------------------

# Each entry: {"name": str, "url": str, "pages": int}
# "pages" controls how many pagination pages to scrape per run.
COMPLAINT_SITES: list[dict] = [
    {
        "name": "mouthshut",
        "url": "https://www.mouthshut.com/search/reviews-sites-925814065-1-{page}.html",
        "pages": 3,
    },
    {
        "name": "complaintsboard",
        "url": "https://www.complaintsboard.com/?search=investment+scam&page={page}",
        "pages": 3,
    },
]

# ---------------------------------------------------------------------------
# Scheduler intervals (seconds)
# Change these to tune how often each job runs.
# ---------------------------------------------------------------------------

INTERVAL_TELEGRAM_SECONDS:   int = 60     # collect Telegram messages
INTERVAL_REDDIT_SECONDS:     int = 300    # collect Reddit posts (5 min)
INTERVAL_COMPLAINTS_SECONDS: int = 1800   # scrape complaint sites (30 min)
INTERVAL_ANALYSIS_SECONDS:   int = 120    # preprocess → classify → embed → cluster → threat

# How many times to retry a failed job before giving up
JOB_MAX_RETRIES: int = 3
