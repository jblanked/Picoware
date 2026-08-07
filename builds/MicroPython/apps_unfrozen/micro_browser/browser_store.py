"""Small SD-card page cache and persistent RSS/Atom feed store."""

from json import loads, dumps
from config import CACHE_DIR, CACHE_INDEX_FILE, CUSTOM_FEEDS_FILE, MAX_CACHE_FILES, MAX_CUSTOM_FEEDS, START_FEEDS


def fnv1a(text):
    value = 2166136261
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return "%08x" % value


class PageCache:
    def __init__(self, storage):
        self.storage = storage
        self.storage.mkdir(CACHE_DIR)
        self.index = self._read_json(CACHE_INDEX_FILE, [])

    def path_for(self, url):
        return CACHE_DIR + "/" + fnv1a(url) + ".html"

    def get(self, url):
        path = self.path_for(url)
        if self.storage.exists(path):
            self._touch(url, path)
            return path
        return None

    def put(self, url, source_path):
        path = self.path_for(url)
        try:
            if self.storage.exists(path):
                self.storage.remove(path)
            self.storage.copy(source_path, path)
            self._touch(url, path)
            self._trim()
            self._write_json(CACHE_INDEX_FILE, self.index)
            return path
        except Exception:
            return None

    def clear(self):
        """Remove cached pages and their index; keep user RSS data untouched."""
        for item in self.index:
            try:
                if len(item)>1 and self.storage.exists(item[1]): self.storage.remove(item[1])
            except Exception: pass
        self.index=[]
        try:
            if self.storage.exists(CACHE_INDEX_FILE): self.storage.remove(CACHE_INDEX_FILE)
        except Exception: pass

    def _touch(self, url, path):
        for index in range(len(self.index) - 1, -1, -1):
            if self.index[index][0] == url:
                del self.index[index]
        self.index.insert(0, [url, path])

    def _trim(self):
        while len(self.index) > MAX_CACHE_FILES:
            old = self.index.pop()
            try:
                if self.storage.exists(old[1]):
                    self.storage.remove(old[1])
            except Exception:
                pass

    def _read_json(self, path, default):
        try:
            if self.storage.exists(path):
                return loads(self.storage.read(path))
        except Exception:
            pass
        return default

    def _write_json(self, path, value):
        try:
            self.storage.write(path, dumps(value))
        except Exception:
            pass


class FeedStore:
    """Persistent, fully user-managed RSS/Atom feed list."""
    def __init__(self,storage):
        self.storage=storage; self.items=self._load()

    def add(self,name,url):
        name=name.strip(); url=url.strip()
        if not name or not url: return False
        if "://" not in url: url="https://"+url
        for index in range(len(self.items)-1,-1,-1):
            if self.items[index][1]==url: del self.items[index]
        self.items.append([name[:40],url])
        while len(self.items)>MAX_CUSTOM_FEEDS: del self.items[0]
        return self._save()

    def remove(self,index):
        if index<0 or index>=len(self.items): return False
        del self.items[index]; return self._save()

    def edit(self,index,name,url):
        name=name.strip(); url=url.strip()
        if index<0 or index>=len(self.items) or not name or not url: return False
        if "://" not in url: url="https://"+url
        for item_index,item in enumerate(self.items):
            if item_index!=index and item[1]==url: return False
        previous=self.items[index]
        self.items[index]=[name[:40],url]
        if self._save(): return True
        self.items[index]=previous
        return False

    def _load(self):
        try:
            if self.storage.exists(CUSTOM_FEEDS_FILE):
                value=loads(self.storage.read(CUSTOM_FEEDS_FILE))
                if isinstance(value,dict) and value.get("initialized"): return value.get("items",[])[:MAX_CUSTOM_FEEDS]
                if isinstance(value,list):
                    items=[[name,url] for name,url in START_FEEDS]
                    for item in value:
                        if isinstance(item,list) and len(item)>=2: items.append(item[:2])
                    self.items=items[:MAX_CUSTOM_FEEDS]; self._save(); return self.items
        except Exception: pass
        self.items=[[name,url] for name,url in START_FEEDS]; self._save(); return self.items

    def _save(self):
        try: return bool(self.storage.write(CUSTOM_FEEDS_FILE,dumps({"initialized":True,"items":self.items})))
        except Exception: return False
