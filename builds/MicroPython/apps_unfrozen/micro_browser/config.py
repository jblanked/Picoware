APP_NAME = "MicroBrowser"
APP_VERSION = "1.0.0"

HOME_URL = ""
USER_AGENT = "MicroBrowser/{} (Picoware; Pico 2 W)".format(APP_VERSION)

TEMP_FILE = "picoware/browser.tmp"
CACHE_DIR = "picoware/browser_cache"
CACHE_INDEX_FILE = "picoware/browser_cache.json"
CUSTOM_FEEDS_FILE = "picoware/browser_feeds.json"

MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_BLOCKS = 600
MAX_LINKS = 120
MAX_TEXT_CHARS = 36000
MAX_CACHE_FILES = 4
MAX_CACHE_PAGE_BYTES = 256 * 1024
READ_CHUNK_SIZE = 1024
MAX_TAG_CHARS = 512
MAX_TEXT_NODE_CHARS = 2048
MAX_FEED_ITEMS = 40
MAX_FEED_SUMMARY_CHARS = 600
MAX_CUSTOM_FEEDS = 30

TEXT_MARGIN = 6
HEADER_HEIGHT = 18
FOOTER_HEIGHT = 18
LINE_GAP = 2

CHARACTER_MODE = "ascii"

HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,text/plain,application/xhtml+xml",
    "Accept-Encoding": "identity",
    "Connection": "close",
}

SEARCH_URL = "https://lite.duckduckgo.com/lite/?q={}"

START_FEEDS = (
    ("BBC Europe", "https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    ("DW Europe", "https://rss.dw.com/rdf/rss-en-eu"),
    ("Euronews Europe", "https://www.euronews.com/rss?level=vertical&name=my-europe"),
    ("POLITICO Europe", "https://www.politico.eu/feed/"),
    ("DER SPIEGEL", "https://www.spiegel.de/schlagzeilen/index.rss"),
    ("France 24 Europe", "https://www.france24.com/en/europe/rss"),
    ("G4Media Romania", "https://www.g4media.ro/feed"),
    ("HotNews Romania", "https://hotnews.ro/feed"),
    ("Digi24 Romania", "https://www.digi24.ro/rss"),
    ("Biziday Romania", "https://www.biziday.ro/feed/"),
)
