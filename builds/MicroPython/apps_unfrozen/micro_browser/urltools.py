def split_url(url):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url

    scheme, rest = url.split("://", 1)
    slash = rest.find("/")

    if slash < 0:
        authority = rest
        path = "/"
    else:
        authority = rest[:slash]
        path = rest[slash:]

    return scheme, authority, path


def normalize_path(path):
    query = ""
    if "?" in path:
        path, query = path.split("?", 1)
        query = "?" + query

    parts = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)

    return "/" + "/".join(parts) + query


def resolve_url(base, href):
    href = href.strip()

    if not href or href.startswith("#"):
        return base

    if href.startswith("?"):
        return base.split("?", 1)[0].split("#", 1)[0] + href

    if href.startswith("http://") or href.startswith("https://"):
        return href

    scheme, authority, path = split_url(base)

    if href.startswith("//"):
        return scheme + ":" + href

    if href.startswith("/"):
        return "{}://{}{}".format(
            scheme,
            authority,
            normalize_path(href)
        )

    directory = path.rsplit("/", 1)[0]
    return "{}://{}{}".format(
        scheme,
        authority,
        normalize_path(directory + "/" + href)
    )


def decode_query_value(value):
    """Decode one percent-encoded query value without allocating large tables."""
    out=bytearray(); index=0
    while index<len(value):
        if value[index]=="%" and index+2<len(value):
            try: out.append(int(value[index+1:index+3],16)); index+=3; continue
            except Exception: pass
        out.append(32 if value[index]=="+" else ord(value[index])); index+=1
    try: return out.decode("utf-8")
    except Exception: return "".join(chr(byte) if byte<128 else "?" for byte in out)


def unwrap_search_redirect(url):
    """Open DuckDuckGo results directly instead of visiting its redirector."""
    if "duckduckgo.com/l/?" not in url: return url
    query=url.split("?",1)[1]
    for part in query.split("&"):
        if part.startswith("uddg="): return decode_query_value(part[5:])
    return url
