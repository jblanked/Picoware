"""Streaming HTML parser for Picoware MicroBrowser."""

from .textcodec import UTF8StreamDecoder, display_text

_ENTITIES = {"amp":"&", "lt":"<", "gt":">", "quot":'"', "apos":"'", "nbsp":" ", "middot":"-"}

_BLOCKED_LINK_PARTS = (
    "mailto:", "tel:", "javascript:",
    "/account", "/login", "/log-in", "/signin", "/sign-in", "/register",
    "/subscribe", "/newsletter", "/email", "/mail/",
    "/donate", "/donation", "/sustine",
    "/video", "/audio", "/podcast", "/watch", "/listen",
    "facebook.com", "instagram.com", "twitter.com", "x.com/", "tiktok.com",
    "youtube.com", "youtu.be", "linkedin.com", "whatsapp.com", "t.me/",
    "telegram.me", "discord.com", "discord.gg",
    "/privacy", "/cookie", "/advert", "/careers", "/jobs/",
    "jobs.",
    "doubleclick.net", "googlesyndication.com", "adservice.",
)

_BLOCKED_LINK_TEXT = (
    "account", "my account", "log in", "login", "sign in", "register",
    "subscribe", "newsletter", "email", "e-mail", "donate", "donation",
    "video", "videos", "audio", "podcast", "podcasts", "watch", "listen",
    "facebook", "instagram", "twitter", "x", "tiktok", "youtube",
    "linkedin", "whatsapp", "telegram", "discord",
    "advertisement", "privacy policy", "cookie policy", "manage cookies",
    "share", "print", "careers", "jobs",
    "search jobs",
)

_NOISE_TEXT = (
    "advertisement", "skip advertisement", "cookie settings", "manage cookies",
    "accept cookies", "reject cookies", "all rights reserved", "share this article",
    "follow us", "sign up", "read more",
)

_NOISE_ATTR_PARTS = (
    "advert", " ad-", "-ad ", "cookie-banner", "cookie-consent", "social-share",
    "share-tools", "newsletter", "subscribe", "login", "account", "paywall",
    "promo-banner", "video-player", "audio-player",
)


def is_readable_link(href, text=""):
    """Return False for account, communication, donation, and media links."""
    target=(href or "").strip().lower(); label=(text or "").strip().lower()
    if not target or target.startswith("#"): return False
    for part in _BLOCKED_LINK_PARTS:
        if part in target: return False
    if label in _BLOCKED_LINK_TEXT: return False
    return True


def decode_entities(text):
    if "&" not in text: return text
    out=[]; i=0
    while i < len(text):
        if text[i] != "&": out.append(text[i]); i += 1; continue
        end=text.find(";", i+1)
        if end < 0 or end-i > 12: out.append("&"); i += 1; continue
        name=text[i+1:end]; value=None
        if name.startswith(("#x", "#X")):
            try: value=chr(int(name[2:],16))
            except Exception: pass
        elif name.startswith("#"):
            try: value=chr(int(name[1:]))
            except Exception: pass
        else: value=_ENTITIES.get(name)
        out.append(text[i:end+1] if value is None else value); i=end+1
    return "".join(out)


def collapse_spaces(text):
    out=[]; spaced=False
    for ch in text:
        if ch in " \t\r\n":
            if not spaced: out.append(" ")
            spaced=True
        else: out.append(ch); spaced=False
    return "".join(out).strip()


def parse_attributes(raw):
    attrs={}; i=0; n=len(raw)
    while i<n and not raw[i].isspace(): i+=1
    while i<n:
        while i<n and raw[i].isspace(): i+=1
        if i>=n: break
        start=i
        while i<n and not raw[i].isspace() and raw[i] != "=": i+=1
        key=raw[start:i].lower()
        while i<n and raw[i].isspace(): i+=1
        value=""
        if i<n and raw[i] == "=":
            i+=1
            while i<n and raw[i].isspace(): i+=1
            if i<n and raw[i] in ("'", '"'):
                quote=raw[i]; i+=1; start=i
                while i<n and raw[i] != quote: i+=1
                value=raw[start:i]
                if i<n: i+=1
            else:
                start=i
                while i<n and not raw[i].isspace(): i+=1
                value=raw[start:i]
        if key: attrs[key]=decode_entities(value)
    return attrs


class ParsedPage:
    def __init__(self):
        self.title=""; self.blocks=[]; self.links=[]; self.feeds=[]; self.truncated=False


class StreamingHTMLParser:
    BLOCK_PREFIX={"p":"", "div":"", "section":"", "article":"", "header":"", "footer":"",
                  "blockquote":"> ", "h1":"# ", "h2":"## ", "h3":"### ",
                  "h4":"#### ", "h5":"##### ", "h6":"###### "}

    def __init__(self, config):
        self.config=config
        self.page=ParsedPage(); self._text=[]; self._tag=[]; self._in_tag=False; self._quote=None; self._discard_tag=False
        self._prefix=""; self._href=None; self._anchor_link_number=0; self._ignore_anchor=False; self._in_title=False; self._in_pre=False; self._skip_tag=None; self._skip_depth=0; self._raw_tail=""
        self._text_chars=0; self._decoder=UTF8StreamDecoder(); self._list_stack=[]
        self._table_row=[]; self._in_cell=False

    def feed(self, data):
        data=self._decoder.feed(data)
        for ch in data:
            if self.page.truncated: return
            if self._skip_tag in ("script","style") and not self._in_tag:
                marker="</"+self._skip_tag+">"
                self._raw_tail=(self._raw_tail+ch.lower())[-len(marker):]
                if self._raw_tail==marker:
                    self._skip_tag=None; self._skip_depth=0; self._raw_tail=""
                continue
            if self._in_tag:
                if self._discard_tag:
                    if ch == ">": self._tag=[]; self._in_tag=False; self._discard_tag=False
                elif self._quote:
                    self._tag.append(ch)
                    if ch == self._quote: self._quote=None
                elif ch in ("'", '"'): self._quote=ch; self._tag.append(ch)
                elif ch == ">": self._handle_tag("".join(self._tag).strip()); self._tag=[]; self._in_tag=False
                else: self._tag.append(ch)
                if not self._discard_tag and len(self._tag)>=self.config.max_tag_chars:
                    self._handle_oversized_tag()
                    self._tag=[]; self._quote=None; self._discard_tag=True
            elif ch == "<": self._flush_text(); self._in_tag=True; self._tag=[]
            elif self._skip_tag is None and not self._ignore_anchor:
                self._text.append(ch)
                if len(self._text)>=self.config.max_text_node_chars: self._flush_text()

    def finish(self):
        tail=self._decoder.finish()
        if tail: self.feed(tail)
        if self._in_tag and self._tag: self._text.append("<"); self._text.extend(self._tag)
        self._flush_text(); self._flush_table_row()
        if not self.page.title: self.page.title="MicroBrowser"
        return self.page

    def _add_block(self, value):
        if len(self.page.blocks) >= self.config.max_blocks: self.page.truncated=True; return
        self.page.blocks.append(value)

    def _handle_oversized_tag(self):
        """Recognize raw-text tags even when their attributes are enormous."""
        probe="".join(self._tag[:32]).lstrip().lower()
        for name in ("script","style","noscript","video","audio","iframe","svg","picture","canvas","object","form"):
            if probe==name or probe.startswith(name+" "):
                self._skip_tag=name; self._skip_depth=1; return

    def _flush_text(self):
        if not self._text: return
        value="".join(self._text); self._text=[]
        if self._skip_tag is not None: return
        if not self._in_pre: value=collapse_spaces(value)
        value=display_text(decode_entities(value), self.config.character_mode)
        if not value: return
        if value.strip().lower() in _NOISE_TEXT: return
        self._text_chars += len(value)
        if self._text_chars > self.config.max_text_chars: self.page.truncated=True; return
        if self._in_title: self.page.title=(self.page.title+" "+value).strip(); return
        if self._href and len(self.page.links) < self.config.max_links:
            if is_readable_link(self._href,value):
                if not self._anchor_link_number:
                    self._anchor_link_number=len(self.page.links)+1
                    self.page.links.append((self._href,value)); value="[{}] {}".format(self._anchor_link_number,value)
            else: return
        if self._in_cell: self._table_row.append(value); return
        self._add_block(self._prefix+value)

    def _flush_table_row(self):
        if self._table_row:
            self._add_block(" | ".join(self._table_row)); self._table_row=[]

    def _handle_tag(self, raw):
        if not raw: return
        lower=raw.lower()
        if lower.startswith("!--") or lower.startswith("!doctype"): return
        closing=lower.startswith("/"); clean=lower[1:].lstrip() if closing else lower
        name=clean.split(None,1)[0].rstrip("/") if clean else ""
        if not name: return
        if self._skip_tag:
            # Only matching tags affect depth. Script/style bodies often contain
            # strings such as "<div>"; treating those as real descendants can
            # accidentally suppress the rest of the document.
            if name==self._skip_tag:
                if closing:
                    self._skip_depth-=1
                    if self._skip_depth<=0: self._skip_tag=None; self._skip_depth=0
                elif self._skip_tag not in ("script","style") and not clean.endswith("/"):
                    self._skip_depth+=1
            return
        if name in ("script","style","noscript","video","audio","iframe","svg","picture","canvas","object","form","button","select","textarea"):
            if not closing: self._skip_tag=name; self._skip_depth=1
            return
        if closing:
            if name == "title": self._in_title=False
            elif name == "a": self._href=None; self._anchor_link_number=0; self._ignore_anchor=False
            elif name == "pre": self._in_pre=False
            elif name in ("ul","ol"):
                if self._list_stack: self._list_stack.pop()
            elif name in ("td","th"): self._flush_text(); self._in_cell=False
            elif name == "tr": self._flush_text(); self._flush_table_row()
            elif name in self.BLOCK_PREFIX or name == "li":
                self._prefix=""
                if self.page.blocks and self.page.blocks[-1] != "": self._add_block("")
            return
        attrs=parse_attributes(raw) if name in ("a","link","div","section","aside","footer") else {}
        noise=(attrs.get("class","")+" "+attrs.get("id","")+" "+attrs.get("role","")).lower()
        if name in ("div","section","aside","footer") and any(part in noise for part in _NOISE_ATTR_PARTS):
            self._skip_tag=name; self._skip_depth=1; return
        if name == "title": self._in_title=True
        elif name == "a":
            self._href=attrs.get("href","")
            self._anchor_link_number=0
            self._ignore_anchor=not is_readable_link(self._href)
            if not self._ignore_anchor:
                for target,label in self.page.links:
                    if target==self._href: self._ignore_anchor=True; break
        elif name == "link":
            rel=attrs.get("rel","").lower(); kind=attrs.get("type","").lower(); href=attrs.get("href","")
            feed_title=attrs.get("title","") or "RSS/Atom feed"
            if href and "alternate" in rel and ("rss" in kind or "atom" in kind) and is_readable_link(href,feed_title):
                self.page.feeds.append((href,feed_title))
                found=False
                for target,label in self.page.links:
                    if target==href: found=True; break
                if not found and len(self.page.links)<self.config.max_links:
                    label=display_text(decode_entities(feed_title),self.config.character_mode)
                    number=len(self.page.links)+1; self.page.links.append((href,label)); self._add_block("[{}] {}".format(number,label))
        elif name == "pre": self._in_pre=True; self._prefix=""
        elif name == "br": self._add_block("")
        elif name == "hr": self._add_block("--------------------------------")
        # Images are intentionally omitted. Their alt text is often verbose,
        # duplicated by nearby captions, and not useful in this text browser.
        elif name in ("ul","ol"): self._list_stack.append(name)
        elif name == "li":
            depth=max(0,len(self._list_stack)-1); marker="* "
            self._prefix=("  "*depth)+marker
        elif name == "tr": self._flush_table_row()
        elif name in ("td","th"): self._in_cell=True
        elif name in self.BLOCK_PREFIX: self._prefix=self.BLOCK_PREFIX[name]


def looks_like_feed(data):
    """Identify RSS, Atom, and RDF feeds from a small file prefix."""
    try: probe=bytes(data).lower()
    except Exception: return False
    return b"<rss" in probe or b"<feed" in probe or b"<rdf:rdf" in probe


class StreamingFeedParser:
    """Bounded streaming parser for RSS 2.0, Atom, and RSS/RDF feeds."""
    FIELDS=("title","link","description","summary","content","pubdate","published","updated")

    def __init__(self, config):
        self.config=config
        self.page=ParsedPage(); self._decoder=UTF8StreamDecoder(); self._tag=[]; self._text=[]
        self._in_tag=False; self._quote=None; self._discard_tag=False; self._in_item=False
        self._field=None; self._item={}; self._feed_title=""; self._items=0

    def feed(self,data):
        data=self._decoder.feed(data)
        for ch in data:
            if self.page.truncated: return
            if self._in_tag:
                if self._discard_tag:
                    if ch==">": self._tag=[]; self._in_tag=False; self._discard_tag=False
                elif self._quote:
                    self._tag.append(ch)
                    if ch==self._quote: self._quote=None
                elif ch in ("'",'"'): self._quote=ch; self._tag.append(ch)
                elif ch==">": self._handle_tag("".join(self._tag).strip()); self._tag=[]; self._in_tag=False
                else: self._tag.append(ch)
                if not self._discard_tag and len(self._tag)>=self.config.max_tag_chars:
                    self._tag=[]; self._quote=None; self._discard_tag=True
            elif ch=="<": self._flush_text(); self._in_tag=True; self._tag=[]
            elif self._field:
                self._text.append(ch)
                if len(self._text)>=self.config.max_text_node_chars: self._flush_text()

    def finish(self):
        tail=self._decoder.finish()
        if tail: self.feed(tail)
        self._flush_text()
        if self._in_item: self._finish_item()
        self.page.title=self._feed_title or "RSS/Atom feed"
        if not self.page.blocks: self.page.blocks=["No feed entries found."]
        return self.page

    def _flush_text(self):
        if not self._text: return
        value=display_text(decode_entities(collapse_spaces("".join(self._text))),self.config.character_mode).replace("]]>",""); self._text=[]
        if not value or not self._field: return
        if self._in_item:
            old=self._item.get(self._field,"")
            limit=self.config.max_feed_summary_chars if self._field in ("description","summary","content") else 1024
            if len(old)<limit: self._item[self._field]=(old+" "+value).strip()[:limit]
        elif self._field=="title" and not self._feed_title: self._feed_title=value[:160]

    def _handle_tag(self,raw):
        if not raw or raw.startswith(("!","?")): return
        lower=raw.lower(); closing=lower.startswith("/"); clean=lower[1:].lstrip() if closing else lower
        name=clean.split(None,1)[0].rstrip("/").split(":")[-1] if clean else ""
        if not name: return
        if closing:
            self._flush_text()
            if name in ("item","entry"): self._finish_item()
            elif name==self._field: self._field=None
            return
        if name in ("item","entry"):
            self._in_item=True; self._item={}; self._field=None; return
        if name in self.FIELDS:
            self._field=name
            if self._in_item and name=="link":
                href=parse_attributes(raw).get("href","")
                if href: self._item["link"]=href; self._field=None

    def _finish_item(self):
        self._flush_text(); self._in_item=False; self._field=None
        if self._items>=self.config.max_feed_items: self.page.truncated=True; self._item={}; return
        title=self._item.get("title","").strip() or "Untitled entry"; link=self._item.get("link","").strip()
        date=(self._item.get("pubdate","") or self._item.get("published","") or self._item.get("updated","")).strip()
        summary=(self._item.get("description","") or self._item.get("summary","") or self._item.get("content","")).strip()
        if link and is_readable_link(link,title) and len(self.page.links)<self.config.max_links:
            number=len(self.page.links)+1; self.page.links.append((link,title)); self.page.blocks.append("## [{}] {}".format(number,title))
        else: self.page.blocks.append("## "+title)
        if date: self.page.blocks.append(date)
        if summary: self.page.blocks.append(summary)
        self.page.blocks.append(""); self._items+=1; self._item={}
