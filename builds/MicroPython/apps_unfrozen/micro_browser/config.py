class BrowserConfig:
    """App-owned settings, released together with the app instance on exit."""

    def __init__(self):
        self.home_url = ""
        self.temp_file = "picoware/browser.tmp"
        self.cache_dir = "picoware/browser_cache"
        self.cache_index_file = "picoware/browser_cache.json"
        self.custom_feeds_file = "picoware/browser_feeds.json"
        self.max_page_bytes = 2 * 1024 * 1024
        self.max_blocks = 600
        self.max_links = 120
        self.max_text_chars = 36000
        self.max_cache_files = 4
        self.max_cache_page_bytes = 256 * 1024
        self.read_chunk_size = 1024
        self.max_tag_chars = 512
        self.max_text_node_chars = 2048
        self.max_feed_items = 40
        self.max_feed_summary_chars = 600
        self.max_custom_feeds = 30
        self.text_margin = 6
        self.header_height = 18
        self.footer_height = 18
        self.line_gap = 2
        self.character_mode = "ascii"
        self.search_url = "https://lite.duckduckgo.com/lite/?q={}"
        self.http_headers = {
            "User-Agent": "MicroBrowser/1.0.0 (Picoware; Pico 2 W)",
            "Accept": "text/html,text/plain,application/xhtml+xml",
            "Accept-Encoding": "identity",
            "Connection": "close",
        }
        self.start_feeds = (
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

    def clear(self):
        """Drop the larger containers before the app module is unloaded."""
        self.http_headers = None
        self.start_feeds = None
