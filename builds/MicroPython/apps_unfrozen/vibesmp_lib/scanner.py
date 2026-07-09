def _perf_set(library, name, value):
    counters = getattr(library, "perf_counters", None)
    if counters is not None:
        counters[name] = value

def scan(library, path=None, loading=None, progress_callback=None, quick=False, remove_missing=False):
    from gc import collect
    import time
    collect()
    start = time.ticks_ms()
    scan_path = ""
    print(f"[DEBUG] library: scanning SD root")
    old_tracks = [library._normalize_track_path(p) for p in getattr(library, "tracks", [])]
    old_set = set(old_tracks)
    found = []
    added = []
    if not quick:
        library.tracks = []
    library._tree_structure = None
    library._flat_tree_cache = None
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
    stack = [start_path]
    skip_dirs = ("__pycache__", ".git", "System Volume Information", "picoware/apps/vibesmp_lib")

    while stack:
        path = stack.pop()
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
                if not item or item.startswith(".") or item in skip_dirs:
                    continue

                if not path:
                    full_path = item
                else:
                    full_path = path.rstrip("/") + "/" + item

                if entry.get("is_directory"):
                    if full_path not in skip_dirs:
                        stack.append(full_path)
                elif item.lower().endswith(".mp3"):
                    library._count += 1
                    library._scan_last_path = full_path
                    if progress_callback: progress_callback(full_path, library._count)

                    save_path = "/sd/" + full_path
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
