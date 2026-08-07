"""Picoware MicroBrowser v1.0.0."""

from gc import collect
from micropython import const
from config import HOME_URL, HTTP_HEADERS, SEARCH_URL, TEMP_FILE, MAX_PAGE_BYTES, MAX_CACHE_PAGE_BYTES, READ_CHUNK_SIZE, TEXT_MARGIN, HEADER_HEIGHT, FOOTER_HEIGHT, LINE_GAP
from htmlparser import StreamingHTMLParser, StreamingFeedParser, looks_like_feed
from urltools import resolve_url, unwrap_search_redirect
from browser_store import PageCache, FeedStore

STATE_VIEW=const(0); STATE_KEYBOARD=const(1); STATE_LOADING=const(2); STATE_START_MENU=const(3); STATE_RSS_MENU=const(4); STATE_FEED_LIST=const(5); STATE_MODIFY_MENU=const(6); STATE_ITEM_MENU=const(7); STATE_CONFIRM=const(8)
PURPOSE_URL=const(0); PURPOSE_SEARCH=const(1); PURPOSE_FEED_NAME=const(2); PURPOSE_FEED_URL=const(3); PURPOSE_EDIT_NAME=const(4); PURPOSE_EDIT_URL=const(5)
STYLE_NORMAL=const(0); STYLE_H1=const(1); STYLE_H2=const(2); STYLE_QUOTE=const(3); STYLE_RULE=const(4)

_HTTP_PATCHED=False
_HTTP_ORIGINAL_REQUEST=None
_HTTP_BASE_URL=""


class ParseCancelled(Exception):
    pass


def install_relative_redirect_fix(http_class):
    """Resolve relative redirects before older frozen HTTP clients parse them."""
    global _HTTP_PATCHED,_HTTP_ORIGINAL_REQUEST
    if _HTTP_PATCHED: return
    _HTTP_ORIGINAL_REQUEST=http_class.request
    def request(client,method,url,*args,**kwargs):
        global _HTTP_BASE_URL
        if url.startswith("http://") or url.startswith("https://"): _HTTP_BASE_URL=url
        elif _HTTP_BASE_URL: url=resolve_url(_HTTP_BASE_URL,url)
        return _HTTP_ORIGINAL_REQUEST(client,method,url,*args,**kwargs)
    http_class.request=request
    _HTTP_PATCHED=True

class MicroBrowserApp:
    def __init__(self, view_manager):
        self.vm=view_manager; self.http=None; self.loading=None; self.page=None; self.menu=None
        self.lines=[]; self.line_links=[]; self.line_styles=[]; self.top_line=0; self.selected_link=0
        self.current_url=HOME_URL; self.pending_url=None; self.pending_add_history=True; self.history=[]; self.www_retry=False
        self.state=STATE_VIEW; self.keyboard_purpose=PURPOSE_URL; self.keyboard_return_state=STATE_VIEW
        self.cache=None; self.feeds=None; self.menu_items=[]; self.pending_feed_name=""; self.edit_index=-1; self.source_path=TEMP_FILE
        self.return_menu="main"; self.discover_feed=False

    def start(self):
        self.vm.freq(True); storage=self.vm.storage
        if not storage: self.vm.alert("SD storage required",False); return False
        storage.mkdir("picoware/micro_browser"); storage.mkdir("picoware/micro_browser/cache")
        self.cache=PageCache(storage); self.feeds=FeedStore(storage)
        self._show_start_menu(); return True

    def stop(self):
        if self.http:
            try: self.http.close()
            except Exception: pass
        storage=self.vm.storage
        if self.cache: self.cache.clear()
        try:
            if storage and storage.exists(TEMP_FILE): storage.remove(TEMP_FILE)
        except Exception: pass
        self.http=None; self.loading=None; self.menu=None; self.feeds=None; self.cache=None; self.menu_items=[]; self.history=[]; self.vm.keyboard.reset(); self.vm.freq()
        self.page=None; self.lines=[]; self.line_links=[]; self.line_styles=[]; self.current_url=HOME_URL; self.pending_url=None; collect()

    def run(self):
        if self.state in (STATE_START_MENU,STATE_RSS_MENU,STATE_FEED_LIST,STATE_MODIFY_MENU,STATE_ITEM_MENU,STATE_CONFIRM): self._run_menu(); return
        if self.state == STATE_LOADING: self._run_loading(); return
        if self.state == STATE_KEYBOARD: self._run_keyboard(); return
        from picoware.system.buttons import BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,BUTTON_RIGHT,BUTTON_CENTER,BUTTON_BACK,BUTTON_R,BUTTON_H
        inp=self.vm.input_manager; b=inp.button
        if b == BUTTON_UP: inp.reset(); self._scroll(-1)
        elif b == BUTTON_DOWN: inp.reset(); self._scroll(1)
        elif b == BUTTON_LEFT: inp.reset(); self._select_link(-1)
        elif b == BUTTON_RIGHT: inp.reset(); self._select_link(1)
        elif b == BUTTON_CENTER: inp.reset(); self._open_selected()
        elif b == BUTTON_R: inp.reset(); self.open_url(self.current_url,False,False)
        elif b == BUTTON_H: inp.reset(); self._show_start_menu()
        elif b == BUTTON_BACK:
            inp.reset()
            if self.history: self.open_url(self.history.pop(),False,True,False,False)
            else: self._return_to_menu()

    def _show_start_menu(self):
        self._show_menu("MicroBrowser",[("SEARCH THE WEB","search"),("URL SEARCH","url"),("RSS","rss")],STATE_START_MENU)

    def _show_rss_menu(self):
        self._show_menu("RSS",[("RSS FEED LIST","list"),("MODIFY RSS LIST","modify")],STATE_RSS_MENU)

    def _show_feed_list(self):
        items=[]
        if self.feeds:
            for index,item in enumerate(self.feeds.items): items.append((item[0],("feed",index)))
        if not items: items=[("No RSS feeds","none")]
        self._show_menu("RSS FEED LIST",items,STATE_FEED_LIST)

    def _show_modify_menu(self):
        self._show_menu("MODIFY RSS LIST",[("ADD","add"),("EDIT","edit"),("REMOVE","remove")],STATE_MODIFY_MENU)

    def _show_item_menu(self,action):
        items=[]
        if self.feeds:
            for index,item in enumerate(self.feeds.items): items.append((item[0],(action,index)))
        if not items: self.vm.alert("No RSS feeds",False); self._show_modify_menu(); return
        self._show_menu(action.upper()+" RSS FEED",items,STATE_ITEM_MENU)

    def _show_confirm(self,index):
        self.edit_index=index
        self._show_menu("REMOVE " + self.feeds.items[index][0][:22]+"?",[("NO","no"),("YES","yes")],STATE_CONFIRM)

    def _show_menu(self,title,items,state):
        from picoware.gui.menu import Menu
        self._release_page(); self.menu=Menu(self.vm.draw,title,0,self.vm.draw.size.y,self.vm.foreground_color,self.vm.background_color,self.vm.selected_color,self.vm.foreground_color,2)
        self.menu_items=items
        for label,value in items: self.menu.add_item(label)
        self.menu.set_selected(0); self.menu.draw(); self.state=state

    def _run_menu(self):
        from picoware.system.buttons import BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,BUTTON_RIGHT,BUTTON_CENTER,BUTTON_BACK
        inp=self.vm.input_manager; b=inp.button
        if b in (BUTTON_UP,BUTTON_LEFT): inp.reset(); self.menu.scroll_up()
        elif b in (BUTTON_DOWN,BUTTON_RIGHT): inp.reset(); self.menu.scroll_down()
        elif b==BUTTON_BACK: inp.reset(); self._menu_back()
        elif b==BUTTON_CENTER:
            inp.reset(); index=self.menu.selected_index
            if index<0 or index>=len(self.menu_items): return
            value=self.menu_items[index][1]
            if self.state==STATE_START_MENU:
                if value=="search": self._start_keyboard(PURPOSE_SEARCH,STATE_START_MENU,"")
                elif value=="url": self._start_keyboard(PURPOSE_URL,STATE_START_MENU,"")
                else: self._show_rss_menu()
            elif self.state==STATE_RSS_MENU:
                self._show_feed_list() if value=="list" else self._show_modify_menu()
            elif self.state==STATE_FEED_LIST:
                if isinstance(value,tuple):
                    self.return_menu="feed_list"; self.history=[]; self.open_url(self.feeds.items[value[1]][1],False)
            elif self.state==STATE_MODIFY_MENU:
                if value=="add": self._start_keyboard(PURPOSE_FEED_NAME,STATE_MODIFY_MENU,"")
                else: self._show_item_menu(value)
            elif self.state==STATE_ITEM_MENU:
                action,item_index=value
                if action=="edit": self.edit_index=item_index; self._start_keyboard(PURPOSE_EDIT_NAME,STATE_ITEM_MENU,self.feeds.items[item_index][0])
                else: self._show_confirm(item_index)
            elif self.state==STATE_CONFIRM:
                if value=="yes":
                    if self.feeds.remove(self.edit_index): self.vm.alert("RSS feed removed",False)
                    else: self.vm.alert("Could not remove feed",False)
                self._show_modify_menu()

    def _menu_back(self):
        if self.state==STATE_START_MENU: self.vm.back()
        elif self.state==STATE_RSS_MENU: self._show_start_menu()
        elif self.state==STATE_FEED_LIST: self._show_rss_menu()
        elif self.state==STATE_MODIFY_MENU: self._show_rss_menu()
        elif self.state in (STATE_ITEM_MENU,STATE_CONFIRM): self._show_modify_menu()

    def _return_to_menu(self):
        if self.return_menu=="feed_list": self._show_feed_list()
        else: self._show_start_menu()

    def _cancel_to_menu(self):
        self._release_page(); self.loading=None; collect(); self._return_to_menu()

    def open_url(self,url,add_history=True,use_cache=True,www_retry=False,discover_feed=False):
        url=url.strip()
        if "://" not in url: url="https://"+url
        if use_cache and self.cache:
            cached=self.cache.get(url)
            if cached:
                try:
                    self._release_page()
                    self.pending_url=url; self.pending_add_history=add_history; self.source_path=cached; self.discover_feed=discover_feed
                    self.page=self._parse_file(cached)
                    if self._open_discovered_feed(): return True
                    self._finish_open(); return True
                except ParseCancelled:
                    self._cancel_to_menu(); return False
                except Exception: pass
        from picoware.system.http import HTTP
        from picoware.gui.loading import Loading
        install_relative_redirect_fix(HTTP)
        if self.http:
            try: self.http.close()
            except Exception: pass
        self._release_page()
        self.http=HTTP(thread_manager=self.vm.thread_manager); self.loading=Loading(self.vm.draw,self.vm.foreground_color,self.vm.background_color); self.loading.set_text("Loading...")
        self.pending_url=url; self.pending_add_history=add_history; self.source_path=TEMP_FILE; self.www_retry=www_retry; self.discover_feed=discover_feed
        storage=self.vm.storage
        try:
            if storage.exists(TEMP_FILE): storage.remove(TEMP_FILE)
        except Exception: pass
        if not self.http.get_async(url,save_to_file=TEMP_FILE,storage=storage,headers=HTTP_HEADERS,timeout=20):
            self._show_error("Failed to start request"); return False
        self.state=STATE_LOADING; return True

    def _run_loading(self):
        from picoware.system.buttons import BUTTON_BACK,BUTTON_H
        inp=self.vm.input_manager
        if inp.button in (BUTTON_BACK,BUTTON_H):
            inp.reset()
            try: self.http.close()
            except Exception: pass
            self._cancel_to_menu(); return
        if self.http and not self.http.is_request_complete():
            if self.loading: self.loading.animate()
            return
        completed_loading=self.loading
        try:
            error=self.http.error if self.http else ""
            successful=self.http.is_successful if self.http else False
            if self.http: self.http.close()
            storage=self.vm.storage
            empty=not storage.exists(TEMP_FILE) or storage.size(TEMP_FILE)<=0
            if empty:
                fallback=self._www_fallback(self.pending_url)
                if fallback and not self.www_retry:
                    self.open_url(fallback,self.pending_add_history,False,True,self.discover_feed); return
                raise Exception(error or ("Request failed" if not successful else "Empty response"))
            self.page=self._parse_file(TEMP_FILE)
            if self._open_discovered_feed(): return
            if self.cache and storage.size(TEMP_FILE)<=MAX_CACHE_PAGE_BYTES: self.cache.put(self.pending_url,TEMP_FILE)
            self._finish_open()
        except ParseCancelled: self._cancel_to_menu()
        except Exception as error: self._show_error(str(error))
        finally:
            if self.loading is completed_loading: self.loading=None
            collect()

    def _open_discovered_feed(self):
        if not self.discover_feed or not getattr(self.page,"feeds",None): return False
        feed_url=resolve_url(self.pending_url,self.page.feeds[0][0]); self.discover_feed=False
        self.open_url(feed_url,False,True,False,False)
        return True

    def _www_fallback(self,url):
        try:
            scheme,rest=url.split("://",1)
            if rest.startswith("www."): return None
            return scheme+"://www."+rest
        except Exception: return None

    def _finish_open(self):
        if self.pending_add_history and self.current_url and self.pending_url != self.current_url:
            self.history.append(self.current_url)
            if len(self.history)>20: del self.history[0]
        self.current_url=self.pending_url; self._layout(); self.page.blocks=[]; collect()
        self.top_line=0; self.selected_link=0; self.state=STATE_VIEW; self.draw()

    def _release_page(self):
        self.page=None; self.lines=[]; self.line_links=[]; self.line_styles=[]; collect()

    def _parse_file(self,path):
        storage=self.vm.storage
        if not storage.exists(path): raise Exception("Page file not found")
        size=storage.size(path)
        if size<=0: raise Exception("Empty response")
        if size>MAX_PAGE_BYTES: raise Exception("Page too large: {} KB".format(size//1024))
        file=storage.file_open(path)
        if not file: raise Exception("Could not open page")
        buffer=bytearray(READ_CHUNK_SIZE); first=storage.file_readinto(file,buffer)
        parser=StreamingFeedParser() if first>0 and looks_like_feed(buffer[:first]) else StreamingHTMLParser(); done=0
        try:
            if first>0: parser.feed(buffer[:first]); done=first
            while True:
                count=storage.file_readinto(file,buffer)
                if count<=0: break
                parser.feed(buffer[:count]); done += count
                self._check_parse_cancel()
                if parser.page.truncated: break
                if self.loading: self.loading.set_text("Parsing {}% ESC/HOME=stop".format((done*100)//size)); self.loading.animate()
                collect()
        finally: storage.file_close(file)
        return parser.finish()

    def _check_parse_cancel(self):
        from picoware.system.buttons import BUTTON_BACK,BUTTON_H
        inp=self.vm.input_manager
        if inp.button in (BUTTON_BACK,BUTTON_H):
            inp.reset(); raise ParseCancelled()

    def draw(self):
        draw=self.vm.draw; draw.fill_screen(self.vm.background_color)
        title=self.page.title if self.page else "MicroBrowser"
        if len(title)>draw.scale_x(38): title=title[:draw.scale_x(35)]+"..."
        draw._text(TEXT_MARGIN,2,title,self.vm.foreground_color)
        font=draw.get_font(0); line_height=font.height+LINE_GAP; y=HEADER_HEIGHT; visible=self._visible_count(); end=min(len(self.lines),self.top_line+visible)
        for index in range(self.top_line,end):
            selected=self.selected_link>0 and self.line_links[index]==self.selected_link
            style=self.line_styles[index]
            color=self.vm.selected_color if selected else (self.vm.foreground_color)
            draw._text(TEXT_MARGIN,y,self.lines[index],color); y += line_height
        footer="{}/{} L{}/{}".format(min(self.top_line+1,max(1,len(self.lines))),max(1,len(self.lines)),self.selected_link,len(self.page.links) if self.page else 0)
        if self.page and self.page.truncated: footer="TRUNC "+footer
        draw._text(TEXT_MARGIN,draw.size.y-FOOTER_HEIGHT,footer[:draw.scale_x(42)],self.vm.foreground_color); draw.swap()

    def _layout(self):
        draw=self.vm.draw; width=max(12,(draw.size.x-(TEXT_MARGIN*2))//max(1,draw.len("M")))
        self.lines=[]; self.line_links=[]; self.line_styles=[]
        for block in self.page.blocks:
            style,text=self._style_block(block); link=self._link_number(text)
            for line in self._wrap(text,width): self.lines.append(line); self.line_links.append(link); self.line_styles.append(style)
        if not self.lines: self.lines=["Empty page"]; self.line_links=[0]; self.line_styles=[STYLE_NORMAL]

    def _style_block(self,text):
        if text.startswith("# "): return STYLE_H1,text[2:].upper()
        if text.startswith("## "): return STYLE_H2,text[3:]
        if text.startswith("### "): return STYLE_H2,text[4:]
        if text.startswith("> "): return STYLE_QUOTE,text
        if text.startswith("----"): return STYLE_RULE,text
        return STYLE_NORMAL,text

    def _wrap(self,text,width):
        if text=="": return [""]
        lines=[]
        for source in text.split("\n"):
            words=source.split()
            if not words: lines.append(""); continue
            line=""
            for word in words:
                if not line: line=word
                elif len(line)+len(word)+1<=width: line += " "+word
                else: lines.append(line); line=word
            if line: lines.append(line)
        return lines

    def _link_number(self,text):
        pos=text.find("[")
        if pos<0: return 0
        end=text.find("]",pos)
        if end<=pos+1: return 0
        try: return int(text[pos+1:end])
        except Exception: return 0

    def _visible_count(self):
        font=self.vm.draw.get_font(0); return max(1,(self.vm.draw.size.y-HEADER_HEIGHT-FOOTER_HEIGHT)//(font.height+LINE_GAP))
    def _scroll(self,amount):
        self.top_line=min(max(0,len(self.lines)-self._visible_count()),max(0,self.top_line+amount)); self.draw()
    def _select_link(self,amount):
        count=len(self.page.links) if self.page else 0
        if not count: return
        self.selected_link += amount
        if self.selected_link<1: self.selected_link=count
        elif self.selected_link>count: self.selected_link=1
        for i,n in enumerate(self.line_links):
            if n==self.selected_link:
                visible=self._visible_count()
                if i<self.top_line: self.top_line=i
                elif i>=self.top_line+visible: self.top_line=max(0,i-visible+1)
                break
        self.draw()
    def _open_selected(self):
        if not self.page or self.selected_link<1: self._start_keyboard(PURPOSE_URL); return
        if self.selected_link<=len(self.page.links): self.open_url(unwrap_search_redirect(resolve_url(self.current_url,self.page.links[self.selected_link-1][0])))

    def _start_keyboard(self,purpose,return_state=STATE_VIEW,initial=None):
        keyboard=self.vm.keyboard; keyboard.reset(); self.keyboard_purpose=purpose
        self.keyboard_return_state=return_state
        if purpose==PURPOSE_SEARCH: keyboard.title="Search the web"
        elif purpose==PURPOSE_FEED_NAME: keyboard.title="RSS feed name"
        elif purpose==PURPOSE_FEED_URL: keyboard.title="RSS feed URL"
        elif purpose==PURPOSE_EDIT_NAME: keyboard.title="Edit RSS name"
        elif purpose==PURPOSE_EDIT_URL: keyboard.title="Edit RSS URL"
        else: keyboard.title="Enter URL"
        keyboard.response=self.current_url if initial is None else initial
        keyboard.run(force=True); keyboard.run(force=True); self.state=STATE_KEYBOARD
    def _run_keyboard(self):
        keyboard=self.vm.keyboard
        if keyboard.is_finished:
            value=keyboard.response.strip(); keyboard.reset(); self.state=STATE_VIEW
            if self.keyboard_purpose==PURPOSE_SEARCH:
                if value:
                    self.return_menu="main"; self.history=[]; self.menu=None
                    self.open_url(SEARCH_URL.format(self._quote_plus(value)),False,False)
                else: self._show_start_menu()
            elif self.keyboard_purpose==PURPOSE_FEED_NAME:
                if value:
                    self.pending_feed_name=value; self._start_keyboard(PURPOSE_FEED_URL,STATE_MODIFY_MENU,"")
                else: self._show_modify_menu()
            elif self.keyboard_purpose==PURPOSE_FEED_URL:
                if value and self.feeds and self.feeds.add(self.pending_feed_name,value): self.vm.alert("RSS feed saved",False)
                elif value: self.vm.alert("Could not save feed",False)
                self.pending_feed_name=""; self._show_modify_menu()
            elif self.keyboard_purpose==PURPOSE_EDIT_NAME:
                if value and self.feeds and 0<=self.edit_index<len(self.feeds.items):
                    self.pending_feed_name=value
                    self._start_keyboard(PURPOSE_EDIT_URL,STATE_ITEM_MENU,self.feeds.items[self.edit_index][1])
                else:
                    self.pending_feed_name=""; self.edit_index=-1; self._show_modify_menu()
            elif self.keyboard_purpose==PURPOSE_EDIT_URL:
                if value and self.feeds and self.feeds.edit(self.edit_index,self.pending_feed_name,value): self.vm.alert("RSS feed updated",False)
                elif value: self.vm.alert("Could not update feed",False)
                self.pending_feed_name=""; self.edit_index=-1; self._show_modify_menu()
            elif value:
                self.return_menu="main"; self.history=[]; self.menu=None
                known=self._known_feed_for(value)
                self.open_url(known or value,False,True,False,not bool(known))
            elif self.keyboard_return_state==STATE_START_MENU: self._show_start_menu()
            else: self.draw()
            return
        if not keyboard.run():
            keyboard.reset()
            if self.keyboard_purpose in (PURPOSE_EDIT_NAME,PURPOSE_EDIT_URL): self.pending_feed_name=""; self.edit_index=-1
            if self.keyboard_return_state==STATE_START_MENU: self._show_start_menu()
            elif self.keyboard_return_state in (STATE_MODIFY_MENU,STATE_ITEM_MENU): self._show_modify_menu()
            else: self.state=STATE_VIEW; self.draw()
    def _quote_plus(self,text):
        safe="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"; out=[]
        for byte in text.encode("utf-8"):
            ch=chr(byte)
            if ch in safe: out.append(ch)
            elif ch==" ": out.append("+")
            else: out.append("%{:02X}".format(byte))
        return "".join(out)
    def _known_feed_for(self,url):
        """Return a saved feed whose hostname matches a URL Search hostname."""
        try:
            probe=url.strip().lower()
            if "://" not in probe: probe="https://"+probe
            host=probe.split("://",1)[1].split("/",1)[0].split(":",1)[0]
            if host.startswith("www."): host=host[4:]
            for name,feed_url in self.feeds.items:
                feed_host=feed_url.lower().split("://",1)[1].split("/",1)[0].split(":",1)[0]
                if feed_host.startswith("www."): feed_host=feed_host[4:]
                if feed_host==host: return feed_url
        except Exception: pass
        return None
    def _show_error(self,message):
        self.page=type("ErrorPage",(),{})(); self.page.title="Browser error"; self.page.links=[]; self.page.feeds=[]; self.page.truncated=False; self.page.blocks=["# Browser error",message,"Press Back to return."]
        self._layout(); self.top_line=0; self.selected_link=0; self.state=STATE_VIEW; self.draw()
