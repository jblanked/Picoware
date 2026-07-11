# VibesMP library database.

# ---- vibes_library.py ----

import json
from vibesmp_lib.utils import mkdir_p

# ---- scanner helpers ----

def _perf_set(library, name, value):
    counters = getattr(library, "perf_counters", None)
    if counters is not None:
        counters[name] = value

def _normalize_scan_path(path):
    if not path:
        return ""
    path = str(path).replace("\\", "/").strip()
    while "//" in path:
        path = path.replace("//", "/")
    if path in ("/", "/sd", "/sd/", "/sdcard", "/sdcard/"):
        return ""
    if path.startswith("/sd/"):
        path = path[4:]
    elif path.startswith("/sdcard/"):
        path = path[8:]
    elif path.startswith("/"):
        path = path[1:]
    if path.startswith("sd/"):
        path = path[3:]
    elif path.startswith("sdcard/"):
        path = path[7:]
    return path.strip("/")

def _scan_skip_dir(path):
    path = _normalize_scan_path(path)
    if not path:
        return False
    parts = path.split("/")
    name = parts[-1]
    if name.startswith(".") or name in ("__pycache__", "System Volume Information"):
        return True
    if len(parts) == 1 and name in ("sd", "sdcard"):
        return True
    skip_prefixes = (
        "picoware/apps",
        "picoware/vibesmp",
        "picoware/settings",
        "picoware/wifi",
        "picoware/bluetooth",
        "picoware/keyboard",
    )
    for prefix in skip_prefixes:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False

def scan(library, path=None, loading=None, progress_callback=None, quick=False, remove_missing=False):
    from gc import collect
    import time
    collect()
    start = time.ticks_ms()
    scan_path = _normalize_scan_path(path)
    print(f"[DEBUG] library: scanning SD root")
    old_tracks = [library._normalize_track_path(p) for p in getattr(library, "tracks", [])]
    old_set = set(old_tracks)
    found = []
    added = []
    if not quick:
        library.tracks = []
    library._tree_structure = None
    library._flat_tree_cache = None
    library._flat_tree_cache_auto_expand = None
    library._count = 0
    library._scan_dirs = 0
    library._scan_last_path = scan_path
    library._scan_progress_force = False

    try:
        _recursive_scan(library, scan_path, loading, progress_callback, found, old_set, added, quick)
        if quick:
            library.tracks = old_tracks + added
        elif remove_missing:
            library.tracks = found
        if progress_callback:
            library._scan_progress_force = True
            try:
                progress_callback(getattr(library, "_scan_last_path", scan_path), library._count)
            finally:
                library._scan_progress_force = False
        library.save()
        if hasattr(library, "_sync_state_with_tracks"):
            library._sync_state_with_tracks(save=True)
        deferred = 0
        if hasattr(library, "queue_metadata_for_tracks"):
            deferred = library.queue_metadata_for_tracks(library.tracks)
        found_set = set(found)
        removed = len([p for p in old_tracks if p not in found_set])
        if remove_missing:
            before = len(library.tracks)
            library.tracks = [p for p in library.tracks if p in found_set]
            if quick:
                removed = before - len(library.tracks)
        new_tracks = len([p for p in library.tracks if p not in old_set])
        unchanged = len([p for p in library.tracks if p in old_set])
        library.last_scan_summary = {
            "total": len(library.tracks),
            "found": len(found),
            "added": new_tracks,
            "removed": removed,
            "unchanged": unchanged,
            "failed": 0,
        }
        _perf_set(library, "scan_ms", time.ticks_diff(time.ticks_ms(), start))
        _perf_set(library, "scan_tracks", len(library.tracks))
        _perf_set(library, "scan_dirs", getattr(library, "_scan_dirs", 0))
        _perf_set(library, "scan_metadata_deferred", deferred)
        print(f"[DEBUG] library: found {len(library.tracks)} tracks, {new_tracks} new, {removed} removed")
        return new_tracks if new_tracks > 0 else 0
    except OSError as e:
        print(f"[ERROR] library.scan fail:", e)
        library.last_scan_summary = {
            "total": len(library.tracks),
            "found": 0,
            "added": 0,
            "removed": 0,
            "unchanged": 0,
            "failed": 1,
        }
        return 0

def _recursive_scan(library, start_path, loading=None, progress_callback=None, found=None, old_set=None, added=None, quick=False):
    from gc import collect
    stack = [_normalize_scan_path(start_path)]
    visited_dirs = set()
    found_set = set()

    while stack:
        path = _normalize_scan_path(stack.pop())
        if path in visited_dirs or _scan_skip_dir(path):
            continue
        visited_dirs.add(path)
        library._scan_dirs += 1
        library._scan_last_path = path
        if progress_callback: progress_callback(path, library._count)
        try:
            entries = library.storage.read_directory(path)
            if not entries:
                continue

            for entry in entries:
                if loading: loading.animate()
                item = entry.get("filename")
                if not item or item.startswith("."):
                    continue

                if not path:
                    full_path = item
                else:
                    full_path = path.rstrip("/") + "/" + item
                full_path = _normalize_scan_path(full_path)

                if entry.get("is_directory"):
                    if not _scan_skip_dir(full_path):
                        stack.append(full_path)
                elif item.lower().endswith(".mp3"):
                    if _scan_skip_dir(path):
                        continue
                    save_path = "/sd/" + full_path
                    if save_path in found_set:
                        continue
                    found_set.add(save_path)
                    library._count += 1
                    library._scan_last_path = full_path
                    if progress_callback: progress_callback(full_path, library._count)

                    if found is not None:
                        found.append(save_path)
                    if quick:
                        if save_path not in old_set:
                            added.append(save_path)
                    else:
                        library.tracks.append(save_path)

                    if library._count % 50 == 0: collect()
        except OSError: pass
        except ValueError as e:
            print(f"[ERROR] library.scan unexpected {path}:", e)

DEBUG_LIBRARY = False

class Library:
    def __init__(self, storage):
        self.storage = storage
        self.db_path = "picoware/vibesmp/library/database.json"
        self.state_path = "picoware/vibesmp/library/state.json"
        self.meta_dir = "picoware/vibesmp/library/meta/"
        self.cover_dir = "picoware/vibesmp/library/covers/"
        if DEBUG_LIBRARY:
            print(f"[DEBUG] Library: Init. Paths: meta={self.meta_dir} cover={self.cover_dir}")
        self.tracks = []
        self.favorites = set()
        self.added_order = {}
        self.next_added_id = 1
        self.expanded_paths = set(["/sd/"]) # Root expanded by default
        self._tree_structure = None # Internal structure
        self._flat_tree_cache = None # Final list of tuples
        self._flat_tree_cache_auto_expand = None
        self._title_cache = {} # path -> ID3 title string
        self._meta_cache = {} # path -> parsed metadata dict
        self._category_cache = {}
        self._child_cache = {}
        self._track_info_cache = {}
        self._display_cache_version = 0
        self._count = 0
        self.perf_counters = None
        self._metadata_queue = []
        self._metadata_queue_idx = 0
        self.last_search = ""
        self.last_scan_summary = {
            "total": 0,
            "found": 0,
            "added": 0,
            "removed": 0,
            "unchanged": 0,
            "failed": 0,
        }
        mkdir_p(self.storage, self.meta_dir)
        mkdir_p(self.storage, self.cover_dir)
        self.load()
        self.load_state()

    def __del__(self):
        self.tracks = []
        self._tree_structure = None
        self._flat_tree_cache = None
        self._flat_tree_cache_auto_expand = None
        self._title_cache = {}
        self._meta_cache = {}
        self._category_cache = {}
        self._child_cache = {}
        self._track_info_cache = {}
        self._metadata_queue = []
        self.storage = None

    def set_perf_counters(self, counters):
        self.perf_counters = counters

    def _perf_inc(self, name):
        if self.perf_counters is not None:
            self.perf_counters[name] = self.perf_counters.get(name, 0) + 1

    def _perf_timing(self, prefix, elapsed):
        counters = self.perf_counters
        if counters is None:
            return
        count_key = prefix + "_count"
        total_key = prefix + "_total_ms"
        max_key = prefix + "_max_ms"
        counters[count_key] = counters.get(count_key, 0) + 1
        counters[total_key] = counters.get(total_key, 0) + elapsed
        if elapsed > counters.get(max_key, 0):
            counters[max_key] = elapsed

    def _invalidate_display_cache(self):
        self._category_cache = {}
        self._child_cache = {}
        self._track_info_cache = {}
        self._display_cache_version += 1

    def _metadata_affects_display(self, md):
        if not isinstance(md, dict):
            return False
        for key in ("title", "artist", "album", "genre", "year", "track", "cover"):
            if md.get(key):
                return True
        return False

    def _normalize_track_path(self, path):
        if not path:
            return ""
        return path if path.startswith("/sd/") else ("/sd/" + path.lstrip("/"))

    def _filename_title(self, path):
        name = path.rsplit("/", 1)[-1]
        if name.lower().endswith(".mp3"):
            name = name[:-4]
        return name

    def _path_parts(self, path):
        path = self._normalize_track_path(path)
        parts = [p for p in path.split("/") if p and p != "sd"]
        return parts

    def _path_fallback_meta(self, path):
        parts = self._path_parts(path)
        title = self._filename_title(path)
        album = ""
        artist = ""
        if len(parts) >= 2:
            album = parts[-2]
        if len(parts) >= 3:
            artist = parts[-3]
        return title, artist, album

    def load_state(self):
        """Load persistent browser state without requiring a database migration."""
        try:
            if self.storage.exists(self.state_path):
                data = self.storage.read(self.state_path)
                if data:
                    state = json.loads(data)
                    fav = state.get("favorites", [])
                    self.favorites = set([self._normalize_track_path(p) for p in fav if p])
                    self.added_order = state.get("added_order", {}) or {}
                    self.next_added_id = int(state.get("next_added_id", 1) or 1)
            self._sync_state_with_tracks(save=False)
        except (OSError, ValueError, TypeError) as e:
            print("[ERROR] library.load_state:", e)
            self.favorites = set()
            self.added_order = {}
            self.next_added_id = 1
            self._sync_state_with_tracks(save=False)

    def save_state(self):
        try:
            parts = self.state_path.split("/")
            base_dir = "/".join(parts[:-1]) + "/"
            mkdir_p(self.storage, base_dir)
            data = json.dumps({
                "favorites": list(self.favorites),
                "added_order": self.added_order,
                "next_added_id": self.next_added_id,
            })
            self.storage.write(self.state_path, data, "w")
            del data
        except (OSError, ValueError, TypeError) as e:
            print("[ERROR] library.save_state:", e)

    def _sync_state_with_tracks(self, save=True):
        """Assign first-seen order to tracks and drop stale favorite/order entries."""
        seen = set()
        changed = False
        for track in self.tracks:
            path = self._normalize_track_path(track)
            seen.add(path)
            if path not in self.added_order:
                self.added_order[path] = self.next_added_id
                self.next_added_id += 1
                changed = True

        for path in list(self.added_order.keys()):
            if path not in seen:
                del self.added_order[path]
                changed = True
        for path in list(self.favorites):
            if path not in seen:
                self.favorites.remove(path)
                changed = True

        if changed and save:
            self.save_state()

    def load(self):
        from gc import collect
        collect()
        try:
            if not self.storage.exists(self.db_path): return
            data = self.storage.read(self.db_path)
            if data:
                self.tracks = json.loads(data)
            del data
            self._tree_structure = None
            self._flat_tree_cache = None
            self._flat_tree_cache_auto_expand = None
            self._title_cache = {}
            self._meta_cache = {}
            self._invalidate_display_cache()
            self.expanded_paths = set(["/sd/"]) # Reset expansion state
            collect()
        except (OSError, ValueError) as e:
            print("[ERROR] library.load OSError/ValueError:", e)
            self.tracks = []
        except TypeError as e:
            print("[ERROR] library.load unexpected:", e)
            self.tracks = []

    def save(self):
        from gc import collect
        collect()
        try:
            parts = self.db_path.split("/")
            base_dir = "/".join(parts[:-1]) + "/"
            mkdir_p(self.storage, base_dir)

            data = json.dumps(self.tracks)
            self.storage.write(self.db_path, data, "w")
            del data
            collect()
        except OSError as e:
            print("[ERROR] library.save OSError:", e)
        except ValueError as e:
            print("[ERROR] library.save unexpected:", e)

    def scan(self, path=None, loading=None, progress_callback=None, quick=False, remove_missing=False, summary=False):
        res = scan(
            self,
            path,
            loading,
            progress_callback=progress_callback,
            quick=quick,
            remove_missing=remove_missing,
        )
        self._title_cache = {}
        self._meta_cache = {}
        self._sync_state_with_tracks(save=True)
        self._invalidate_display_cache()
        from gc import collect
        collect()
        if summary:
            return self.last_scan_summary
        return res

    def get_title(self, path):
        """Return ID3 title for a track path, with caching. Falls back to empty string."""
        if path in self._title_cache:
            return self._title_cache[path]
        title = ""
        try:
            from vibesmp_lib.metadata_engine import get_cached_title
            title = get_cached_title(self.storage, self, path)
        except (ImportError, OSError, ValueError):
            pass
        self._title_cache[path] = title
        return title

    @property
    def display_cache_version(self):
        return self._display_cache_version

    def get_track_display(self, path, allow_io=True):
        """Return (title, artist) for a track path using cached metadata."""
        path = self._normalize_track_path(path)
        if path in self._meta_cache:
            md = self._meta_cache[path]
        else:
            md = {}
            if allow_io:
                md = self.load_track_metadata(path)

        title = ""
        artist = ""
        if isinstance(md, dict):
            title = md.get("title", "") or ""
            artist = md.get("artist", "") or ""
        if not title:
            title = path.rsplit("/", 1)[-1]
            if title.lower().endswith(".mp3"):
                title = title[:-4]
        return title, artist

    def _get_meta(self, path, allow_io=True):
        path = self._normalize_track_path(path)
        if path in self._meta_cache:
            return self._meta_cache[path]
        md = {}
        if allow_io:
            md = self.load_track_metadata(path)
        return md

    def load_track_metadata(self, path):
        """Load cached metadata for one track from SD and update display caches."""
        path = self._normalize_track_path(path)
        if path in self._meta_cache:
            return self._meta_cache[path]
        md = {}
        try:
            from vibesmp_lib.metadata_engine import get_meta_paths
            meta_path, _ = get_meta_paths(self, path)
            n = meta_path
            if n.startswith("/sd/"):
                n = n[4:]
            elif n.startswith("sd/"):
                n = n[3:]
            if self.storage.exists(n):
                data = self.storage.read(n)
                if data:
                    md = json.loads(data)
        except (ImportError, OSError, ValueError, TypeError):
            md = {}
        self._meta_cache[path] = md
        if self._metadata_affects_display(md):
            self._invalidate_display_cache()
            self._perf_inc("library_metadata_display_invalidate")
        else:
            self._perf_inc("library_metadata_empty_cached")
        return md

    def has_track_metadata(self, path):
        return self._normalize_track_path(path) in self._meta_cache

    def _metadata_file_exists(self, path):
        try:
            from vibesmp_lib.metadata_engine import get_meta_paths
            meta_path, _ = get_meta_paths(self, self._normalize_track_path(path))
            if meta_path.startswith("/sd/"):
                meta_path = meta_path[4:]
            elif meta_path.startswith("sd/"):
                meta_path = meta_path[3:]
            return self.storage.exists(meta_path)
        except (ImportError, OSError, ValueError, TypeError):
            return False

    def queue_metadata_for_tracks(self, tracks=None):
        queue = []
        source = tracks if tracks is not None else self.tracks
        for path in source:
            n_path = self._normalize_track_path(path)
            if n_path and not self._metadata_file_exists(n_path):
                queue.append(n_path)
        self._metadata_queue = queue
        self._metadata_queue_idx = 0
        return len(queue)

    def metadata_queue_pending(self):
        return max(0, len(self._metadata_queue) - self._metadata_queue_idx)

    def extract_next_metadata(self):
        import time
        while self._metadata_queue_idx < len(self._metadata_queue):
            path = self._metadata_queue[self._metadata_queue_idx]
            self._metadata_queue_idx += 1
            if self._metadata_file_exists(path):
                self.load_track_metadata(path)
                self._perf_inc("metadata_idle_cached")
                return True
            start = time.ticks_ms() if self.perf_counters is not None else 0
            try:
                from vibesmp_lib.metadata_engine import extract_metadata
                ok = extract_metadata(self.storage, path, self)
                if start:
                    self._perf_timing("metadata_idle_extract", time.ticks_diff(time.ticks_ms(), start))
                self._perf_inc("metadata_idle_extract_ok" if ok else "metadata_idle_extract_fail")
                if path in self._meta_cache:
                    del self._meta_cache[path]
                self.load_track_metadata(path)
                return True
            except (ImportError, OSError, ValueError, TypeError) as e:
                print("[ERROR] library.extract_next_metadata:", e)
                self._perf_inc("metadata_idle_extract_fail")
                return False
        self._metadata_queue = []
        self._metadata_queue_idx = 0
        return False

    def get_track_info(self, path, allow_io=True):
        """Return normalized display metadata for one track."""
        path = self._normalize_track_path(path)
        if not allow_io:
            cached = self._track_info_cache.get(path)
            if cached is not None:
                self._perf_inc("library_track_info_cache_hit")
                return cached
        md = self._get_meta(path, allow_io=allow_io)
        if not isinstance(md, dict):
            md = {}
        f_title, f_artist, f_album = self._path_fallback_meta(path)
        title = md.get("title", "") or f_title
        artist = md.get("artist", "") or f_artist or "Unknown Artist"
        album = md.get("album", "") or f_album or "Unknown Album"
        genre = md.get("genre", "") or "Unknown Genre"
        info = {
            "kind": "track",
            "path": path,
            "label": title,
            "title": title,
            "artist": artist,
            "album": album,
            "genre": genre,
            "year": md.get("year", "") or "",
            "track": md.get("track", "") or "",
            "cover": md.get("cover", False),
            "favorite": path in self.favorites,
        }
        if not allow_io:
            self._track_info_cache[path] = info
            self._perf_inc("library_track_info_cache_miss")
        return info

    def get_categories(self):
        return [
            ("all_songs", "All Songs"),
            ("artists", "Artists"),
            ("albums", "Albums"),
            ("folders", "Folders"),
            ("genres", "Genres"),
            ("recently_added", "Recently Added"),
            ("favorites", "Favorites"),
            ("search", "Search"),
            ("scan_options", "Scan Options"),
            ("sort", "Sort"),
            ("filters", "Filters"),
            ("stats", "Library Stats"),
            ("cleanup", "Cleanup"),
            ("scan", "Scan Library"),
        ]

    def get_sort_modes(self):
        return [
            ("title", "Title"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("recent", "Recently Added"),
            ("folder", "Folder Order"),
        ]

    def _sort_track_items(self, items, sort_mode):
        if sort_mode == "recent":
            items.sort(key=lambda x: self.added_order.get(x["path"], 0), reverse=True)
        elif sort_mode == "artist":
            items.sort(key=lambda x: (x.get("artist", "").lower(), x.get("album", "").lower(), x.get("title", "").lower()))
        elif sort_mode == "album":
            items.sort(key=lambda x: (x.get("album", "").lower(), x.get("track", ""), x.get("title", "").lower()))
        elif sort_mode == "folder":
            items.sort(key=lambda x: x.get("path", "").lower())
        else:
            items.sort(key=lambda x: (x.get("title", "").lower(), x.get("artist", "").lower()))

    def _track_entries(self, tracks, query=None, sort_mode=None, allow_io=False):
        q = query.lower() if query else ""
        items = []
        for path in tracks:
            info = self.get_track_info(path, allow_io=allow_io)
            if q:
                hay = (
                    info["title"] + " " + info["artist"] + " " +
                    info["album"] + " " + info["genre"] + " " + path
                ).lower()
                if q not in hay:
                    continue
            items.append(info)

        self._sort_track_items(items, sort_mode)
        return items

    def _bucket_entries(self, field, category, unknown_label, allow_io=False):
        buckets = {}
        for path in self.tracks:
            info = self.get_track_info(path, allow_io=allow_io)
            key = info.get(field, "") or unknown_label
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(info["path"])
        items = []
        for key in sorted(buckets.keys(), key=lambda x: x.lower()):
            items.append({
                "kind": "bucket",
                "category": category,
                "key": key,
                "label": key,
                "count": len(buckets[key]),
                "tracks": buckets[key],
            })
        return items

    def get_category_items(self, category, query=None, sort_mode=None):
        key = (
            self._display_cache_version,
            category,
            query or "",
            sort_mode or "",
            len(self.tracks),
        )
        cached = self._category_cache.get(key)
        if cached is not None:
            self._perf_inc("library_category_cache_hit")
            return cached
        self._perf_inc("library_category_cache_miss")

        if category == "all_songs":
            items = self._track_entries(self.tracks, query=query, sort_mode=sort_mode, allow_io=False)
        elif category == "recently_added":
            items = self._track_entries(self.tracks, query=query, sort_mode="recent", allow_io=False)
        elif category == "favorites":
            tracks = [p for p in self.tracks if self._normalize_track_path(p) in self.favorites]
            items = self._track_entries(tracks, query=query, sort_mode=sort_mode, allow_io=False)
        elif category == "search":
            items = self._track_entries(self.tracks, query=query, sort_mode=sort_mode, allow_io=False)
        elif category == "filters":
            items = [
                {"kind": "category_filter", "filter": "favorites", "label": "Favorites Only"},
                {"kind": "category_filter", "filter": "unknown_artist", "label": "Unknown Artist"},
                {"kind": "category_filter", "filter": "missing_metadata", "label": "Missing Metadata"},
                {"kind": "category_filter", "filter": "duplicates", "label": "Duplicates"},
                {"kind": "category_filter", "filter": "broken_files", "label": "Missing Files"},
            ]
        elif category == "sort":
            items = [
                {"kind": "sort_mode", "sort_mode": mode, "label": label}
                for mode, label in self.get_sort_modes()
            ]
        elif category == "scan_options":
            items = [
                {"kind": "scan_action", "scan_mode": "quick", "label": "Quick Scan New Files"},
                {"kind": "scan_action", "scan_mode": "missing", "label": "Remove Missing Files"},
                {"kind": "scan_action", "scan_mode": "full", "label": "Full Rescan"},
            ]
        elif category == "stats":
            items = self.get_stats_items()
        elif category == "cleanup":
            items = self.get_cleanup_items()
        elif category == "artists":
            items = self._bucket_entries("artist", "artists", "Unknown Artist", allow_io=False)
        elif category == "albums":
            items = self._bucket_entries("album", "albums", "Unknown Album", allow_io=False)
        elif category == "genres":
            items = self._bucket_entries("genre", "genres", "Unknown Genre", allow_io=False)
        elif category == "folders":
            items = []
            for path, depth, is_dir, is_exp, name in self.get_tree_view():
                items.append({
                    "kind": "folder" if is_dir else "track",
                    "path": path,
                    "label": name,
                    "depth": depth,
                    "expanded": is_exp,
                })
        else:
            items = []

        if len(self._category_cache) > 16:
            self._category_cache.clear()
        self._category_cache[key] = items
        return items

    def get_filtered_items(self, filter_name, sort_mode=None):
        if filter_name == "favorites":
            tracks = [p for p in self.tracks if self._normalize_track_path(p) in self.favorites]
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "unknown_artist":
            tracks = []
            for path in self.tracks:
                md = self._get_meta(path, allow_io=False)
                if not isinstance(md, dict) or not md.get("artist"):
                    tracks.append(path)
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "missing_metadata":
            tracks = [p for p in self.tracks if not self._metadata_file_exists(p)]
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "duplicates":
            tracks = []
            for item in self.get_duplicate_items():
                tracks.extend(item.get("tracks", []))
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "broken_files":
            return self._track_entries(self.find_missing_files(), sort_mode=sort_mode, allow_io=False)
        return []

    def tracks_under_folder(self, folder_path):
        folder_path = self._normalize_track_path(folder_path)
        if not folder_path.endswith("/"):
            folder_path += "/"
        return [p for p in self.tracks if self._normalize_track_path(p).startswith(folder_path)]

    def _track_exists(self, path):
        p = self._normalize_track_path(path)
        rel = p[4:] if p.startswith("/sd/") else p
        try:
            return self.storage.exists(rel)
        except OSError:
            return False

    def find_missing_files(self):
        return [p for p in self.tracks if not self._track_exists(p)]

    def remove_tracks(self, tracks):
        remove = set([self._normalize_track_path(p) for p in tracks if p])
        if not remove:
            return 0
        before = len(self.tracks)
        self.tracks = [p for p in self.tracks if self._normalize_track_path(p) not in remove]
        for path in list(self.favorites):
            if path in remove:
                self.favorites.remove(path)
        for path in list(self.added_order.keys()):
            if path in remove:
                del self.added_order[path]
        removed = before - len(self.tracks)
        if removed:
            self.save()
            self.save_state()
            self._tree_structure = None
            self._flat_tree_cache = None
            self._flat_tree_cache_auto_expand = None
            self._invalidate_display_cache()
        return removed

    def clear_favorites(self):
        count = len(self.favorites)
        self.favorites = set()
        self.save_state()
        self._invalidate_display_cache()
        return count

    def get_duplicate_items(self):
        buckets = {}
        for path in self.tracks:
            info = self.get_track_info(path, allow_io=False)
            key = (
                info.get("title", "").lower(),
                info.get("artist", "").lower(),
            )
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(path)
        items = []
        for key, tracks in buckets.items():
            if len(tracks) > 1:
                label = self.get_track_info(tracks[0], allow_io=False).get("title", "Duplicate")
                items.append({
                    "kind": "collection",
                    "label": label,
                    "tracks": tracks,
                    "count": len(tracks),
                })
        items.sort(key=lambda x: x.get("label", "").lower())
        return items

    def get_cleanup_items(self):
        missing = self.find_missing_files()
        duplicates = self.get_duplicate_items()
        return [
            {"kind": "cleanup_action", "cleanup": "remove_missing", "label": "Remove Missing Files ({})".format(len(missing)), "tracks": missing},
            {"kind": "collection", "label": "Duplicate Tracks ({})".format(len(duplicates)), "tracks": [p for d in duplicates for p in d.get("tracks", [])], "count": len(duplicates)},
            {"kind": "cleanup_action", "cleanup": "clear_favorites", "label": "Clear Favorites ({})".format(len(self.favorites))},
        ]

    def get_stats_items(self):
        artists = set()
        albums = set()
        genres = set()
        for path in self.tracks:
            info = self.get_track_info(path, allow_io=False)
            artists.add(info.get("artist", "Unknown Artist"))
            albums.add(info.get("album", "Unknown Album"))
            genres.add(info.get("genre", "Unknown Genre"))
        missing = len(self.find_missing_files())
        missing_meta = len([p for p in self.tracks if not self._metadata_file_exists(p)])
        summary = self.last_scan_summary or {}
        return [
            {"kind": "info", "label": "Tracks: {}".format(len(self.tracks))},
            {"kind": "info", "label": "Artists: {}".format(len(artists))},
            {"kind": "info", "label": "Albums: {}".format(len(albums))},
            {"kind": "info", "label": "Genres: {}".format(len(genres))},
            {"kind": "info", "label": "Favorites: {}".format(len(self.favorites))},
            {"kind": "info", "label": "Missing files: {}".format(missing)},
            {"kind": "info", "label": "Missing metadata: {}".format(missing_meta)},
            {"kind": "info", "label": "Last scan added: {}".format(summary.get("added", 0))},
            {"kind": "info", "label": "Last scan removed: {}".format(summary.get("removed", 0))},
        ]

    def get_child_items(self, category, item):
        if not item:
            return []
        cache_key = (
            self._display_cache_version,
            category or "",
            item.get("kind", ""),
            item.get("key", ""),
            item.get("label", ""),
            tuple(item.get("tracks", [])),
        )
        cached = self._child_cache.get(cache_key)
        if cached is not None:
            self._perf_inc("library_child_cache_hit")
            return cached
        self._perf_inc("library_child_cache_miss")
        result = []
        if item.get("kind") == "bucket":
            tracks = item.get("tracks", [])
            if category == "artists":
                albums = {}
                for path in tracks:
                    info = self.get_track_info(path, allow_io=False)
                    key = info.get("album", "") or "Unknown Album"
                    if key not in albums:
                        albums[key] = []
                    albums[key].append(path)
                entries = [{
                    "kind": "collection",
                    "label": "All Artist Songs",
                    "tracks": tracks,
                    "count": len(tracks),
                }]
                for album in sorted(albums.keys(), key=lambda x: x.lower()):
                    entries.append({
                        "kind": "collection",
                        "label": album,
                        "tracks": albums[album],
                        "count": len(albums[album]),
                    })
                result = entries
            else:
                label = "All Tracks"
                if category == "albums":
                    label = "All Album Tracks"
                elif category == "genres":
                    label = "All Genre Tracks"
                result = [{
                    "kind": "collection",
                    "label": label,
                    "tracks": tracks,
                    "count": len(tracks),
                }] + self._track_entries(tracks, sort_mode=None, allow_io=False)
        elif item.get("kind") == "collection":
            result = self._track_entries(item.get("tracks", []), sort_mode=None, allow_io=False)
        if len(self._child_cache) > 16:
            self._child_cache.clear()
        self._child_cache[cache_key] = result
        return result

    def toggle_favorite(self, path):
        path = self._normalize_track_path(path)
        if path in self.favorites:
            self.favorites.remove(path)
            fav = False
        else:
            self.favorites.add(path)
            fav = True
        self._invalidate_display_cache()
        self.save_state()
        return fav

    def is_favorite(self, path):
        return self._normalize_track_path(path) in self.favorites

    def toggle_expanded(self, path):
        """Toggle a folder's expanded state."""
        if path in self.expanded_paths:
            self.expanded_paths.remove(path)
            # Recursively collapse all children
            to_remove = [p for p in self.expanded_paths if p.startswith(path)]
            for p in to_remove:
                self.expanded_paths.remove(p)
        else:
            self.expanded_paths.add(path)

        self._flat_tree_cache = None # Invalidate flat view cache
        self._flat_tree_cache_auto_expand = None
        self._invalidate_display_cache()

    def _build_internal_tree(self):
        """Build a compressed tree using only folders that directly contain MP3 files."""
        from gc import collect
        collect()
        # Root is virtual and hidden in view.
        self._tree_structure = {"folders": {}, "files": [], "path": "/sd/", "name": ""}

        # 1) Gather folders that DIRECTLY contain mp3s, and files per folder.
        files_by_dir = {}
        mp3_dirs = set()
        for track in self.tracks:
            t_path = track if track.startswith("/sd/") else ("/sd/" + track.lstrip("/"))
            slash = t_path.rfind("/")
            if slash < 0:
                continue
            d_path = t_path[:slash + 1]
            fname = t_path[slash + 1:]
            mp3_dirs.add(d_path)
            if d_path not in files_by_dir:
                files_by_dir[d_path] = []
            files_by_dir[d_path].append(fname)

        # 2) Build compressed parent links:
        # parent is nearest ancestor that is also an mp3 folder; skip non-mp3 parents.
        parent_map = {}
        for d_path in mp3_dirs:
            parent = "/sd/"
            search = d_path.rstrip("/")
            while True:
                p = search.rfind("/")
                if p <= 3:  # stop at /sd
                    break
                anc = search[:p + 1]
                if anc in mp3_dirs:
                    parent = anc
                    break
                search = anc.rstrip("/")
            parent_map[d_path] = parent

        # 3) Create nodes and attach to compressed parents.
        nodes = {}
        for d_path in mp3_dirs:
            if d_path == "/sd/":
                self._tree_structure["files"] = files_by_dir.get(d_path, [])
                continue
            name = d_path.rstrip("/").split("/")[-1]
            nodes[d_path] = {
                "folders": {},
                "files": files_by_dir.get(d_path, []),
                "path": d_path,
                "name": name
            }

        for d_path, node in nodes.items():
            p_path = parent_map.get(d_path, "/sd/")
            if p_path in nodes and p_path != d_path:
                nodes[p_path]["folders"][node["name"]] = node
            else:
                self._tree_structure["folders"][node["name"]] = node
        collect()

    def get_tree_view(self, auto_expand=True):
        """Return a list of (path, depth, is_dir, is_expanded, name) for the tree."""
        auto_expand = bool(auto_expand)
        if self._flat_tree_cache is not None and self._flat_tree_cache_auto_expand == auto_expand:
            return self._flat_tree_cache

        from gc import collect
        collect()

        if self._tree_structure is None:
            self._build_internal_tree()

        root_node = self._tree_structure
        visible_expanded = None if auto_expand else set(self.expanded_paths)

        self._flat_tree_cache = []
        self._flat_tree_cache_auto_expand = auto_expand
        # Show only MP3-containing folders as top-level entries (no SD/picoware chain).
        stack = []
        for f_name in sorted(root_node["files"], reverse=True):
            full_path = root_node["path"] + f_name
            display_name = f_name
            if display_name.lower().endswith(".mp3"):
                display_name = display_name[:-4]
            stack.append((False, display_name, full_path, 0))
        for f_name in sorted(root_node["folders"].keys(), reverse=True):
            stack.append((True, f_name, root_node["folders"][f_name], 0))

        while stack:
            is_folder, name, data, depth = stack.pop()
            if not is_folder:
                self._flat_tree_cache.append((data, depth, False, False, name))
                continue

            node = data
            path = node.get("path")
            is_expanded = auto_expand or path in visible_expanded
            self._flat_tree_cache.append((path, depth, True, is_expanded, name))

            if is_expanded:
                # Maintain alpha order: Files then Folders (pushed in reverse)
                files = sorted(node["files"], reverse=True)
                for f_name in files:
                    full_path = path + f_name
                    display_name = f_name
                    if display_name.lower().endswith(".mp3"):
                        display_name = display_name[:-4]
                    stack.append((False, display_name, full_path, depth + 1))

                f_keys = sorted(node["folders"].keys(), reverse=True)
                for f_name in f_keys:
                    stack.append((True, f_name, node["folders"][f_name], depth + 1))

        collect()
        return self._flat_tree_cache
