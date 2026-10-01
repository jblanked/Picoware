"""Menu, status, and dialog drawing for the Sprite3D editor."""

from time import ticks_ms, ticks_diff


def display_number(value):
    """Two decimal places without hiding small nonzero values."""
    if value and (abs(value) < .005 or abs(value) >= 1e6):
        return "%.2e" % value
    return "%.2f" % (value if value else 0.0)


class EditorUI:
    """Draw editor controls above the model preview."""

    def menu_items(self, parent=False):
        """Return the active dropdown's labels and enabled state."""
        loaded = self.mesh is not None
        geometry = bool(self.records)
        selected = loaded and self.has_selection()
        faces = selected and self.selection_mode not in ("Vertices","Edges")
        if self.menu == 2 and self.submenu and not parent:
            if self.submenu == "Cleanup":
                return (("Remove degenerates",geometry),("Remove duplicates",geometry))
            return (("Union A + B",geometry),("Difference A - B",geometry),
                    ("Intersection",geometry),("Set operand A",faces),
                    ("Set operand B",faces),("Clear operands",any(self.boolean_operands)))
        if self.menu == 0:
            return (("Open", True), ("Save", geometry),
                    ("Save As", geometry), ("Quit", True), ("New",True))
        if self.menu == 1:
            if parent or not self.submenu:
                return (("Camera >", loaded), ("Shading >", True),
                        ("Overlays >", True), ("Selection >", loaded),
                        ("Model viewer",geometry), ("Isometric viewer",geometry))
            if self.submenu == "Camera":
                return tuple((name, loaded) for name in
                             ("Front", "Side", "Back", "Top", "Bottom", "4 View", "Fit model"))
            if self.submenu == "Shading":
                return tuple((("[x] " if self.shading == mode else "[ ] ")+mode,True)
                             for mode in ("Asset","Solid","Wireframe","Solid + Wireframe")) + (
                             (("[x] " if self.backface_culling else "[ ] ")+"Backface culling",True),)
            if self.submenu == "Selection":
                return ((("[x] " if self.xray_vertices else "[ ] ")+"X-Ray Selection",loaded),)
            return tuple((("[x] " if getattr(self,flag) else "[ ] ")+label,True)
                         for flag,label in (("show_grid","Base grid"),("show_orientation","Orientation"),
                                            ("show_vertex_info","Vertex info"),("show_normals","Normals"),
                                            ("show_edge_lengths","Edge lengths")))
        if self.menu == 2:
            return (("Move", selected), ("Scale", selected), ("Rotate", selected),
                    ("Undo (%d)" % len(self.history.undo), bool(self.history.undo)),
                    ("Redo (%d)" % len(self.history.redo), bool(self.history.redo)),
                    ("Color...",faces),("Duplicate",faces),("Delete",selected),
                    ("Wireframe",faces),("Flip winding",faces),
                    ("Boolean >",geometry or any(self.boolean_operands)),
                    ("Recalculate normals",selected),("Decimate...",faces),
                    ("Cleanup >",geometry))
        if self.menu == 3:
            return (("Model",loaded),("Triangles",geometry),("Vertices",geometry),("Edges",geometry),
                    ("All",bool(self.selection)),("None",bool(self.selection)),
                    ("Invert",bool(self.selection)),
                    (("[x] " if self.linked_vertices else "[ ] ")+"Linked vertices",geometry),
                    ("Connected solid",self.selection_mode == "Triangles" and geometry),
                    ("Islands (automatic)",geometry))
        if self.menu == 4:
            from .creation import PRIMITIVES
            return (("New asset",True),)+tuple((name,True) for name in PRIMITIVES)+(
                    ("Face from vertices",selected and self.selection_mode == "Vertices"),)
        return (("Controls", True), ("About", True), ("Model viewers", True))


    def menu_shortcuts(self, parent=False):
        """Viewport shortcuts in menu order; omit keys unavailable in this mode."""
        components = self.mesh is not None and self.selection_mode != "Model"
        if self.menu == 0:
            return ("", "", "", "Esc")
        if self.menu == 1:
            if parent or not self.submenu:
                return ("", "W cycle")
            if self.submenu == "Camera":
                return ("", "", "", "", "", "F5 toggle", "R")
            if self.submenu == "Overlays" and components and self.selection_mode == "Vertices":
                return ("", "", "B")
        if self.menu == 2 and (parent or not self.submenu):
            return ("G", "", "", "Z", "Y", "", "", "Del" if components else "")
        if self.menu == 3 and components:
            return ("", "", "", "", "A", "N")
        return ()


    def has_submenu(self):
        return (self.menu == 1 and 0 <= self.menu_row < 4) or (self.menu == 2 and self.menu_row in (10,13))

    def hud(self, draw, force=False, footer=True):
        """Repaint only changed menu, document and footer strips."""
        from .framecache import damage
        width,height=int(draw.size.x),int(draw.size.y)
        menu_key=(width,self.menu)
        if force or self._hud_keys[0]!=menu_key:
            draw._fill_rectangle(0,0,width,20,0x2945)
            for index,title in enumerate(("File","View","Model","Select","Create","Help")):
                x=index*52
                if self.menu==index:
                    draw._fill_rectangle(x,0,51,20,0x051F)
                draw._text(x+7,5,title,0xFFFF)
                # Select opens with L; the other headings use their first letter.
                draw._fill_rectangle(x+7+(12 if index==3 else 0),14,5,1,0xFFFF)
            damage(self,(0,0,width,20))
        counts=tuple(len(item[1]) if item else 0 for item in self.boolean_operands)
        operands=any(self.boolean_operands)
        title=self.path.rsplit("/",1)[-1] if self.path else "Sprite3D Editor"
        title=(("* " if self.dirty else "")+title)[:(width-82 if operands else width)//8]
        label=(self.view_name+"  "+self.selection_label())[:width//6] if self.mesh is not None else ""
        document_key=(width,title,label,operands,counts)
        if force or self._hud_keys[1]!=document_key:
            draw._fill_rectangle(0,20,width,28,0x0000)
            if operands:
                draw._text(width-78,23,"A:%d B:%d" % counts,0xFFE0)
            draw._text(3,23,title,0xFFFF)
            if label:
                draw._text(3,36,label,0x07FF)
            damage(self,(0,20,width,28))
        hint="L/R Orbit  U/D Zoom  R Fit"
        if self.four_view:
            hint="1-4 Select  F5 Full  U/D Zoom"
        if self.maximized:
            hint="F5 Four views  U/D Zoom  R Fit"
        if self.selection_mode!="Model":
            hint="Comma Prev Period Next Space Pick"
        if self.selection_mode in ("Vertices","Triangles","Edges","Islands"):
            name={"Vertices":"Vertex","Triangles":"Triangle","Edges":"Edge","Islands":"Island"}[self.selection_mode]
            navigation="L/R " if self.selection_mode=="Islands" else "Arrows "
            hint="Arrows Camera  P "+name if self.selection_camera else navigation+name+" Space Pick P Camera"
        if self._visibility_pending:
            hint="Checking visibility... P Camera"
        if self.menu>=0:
            hint=("L/R Menu  Down/Enter Open  Esc Close" if self.menu_row<0 else
                  "Left/Esc Back  U/D Item  Enter Select" if self.submenu else
                  "U/D Item  Enter Select  Esc Close")
        status=(self.status or ("O Mode G Tool M Edit F5 View" if self.selection_mode!="Model" else
                "L/R Orbit active Perspective  R Fit" if self.four_view else "O Mode G Tool Enter Menu Esc Back"))[:width//6]
        if self.menu>=0:
            status="F File  V View  M Model  L Select  C Create  H Help"
            if self.menu_row>=0:
                if self.menu==1:
                    status=("Viewer: Space Pause/Resume  Esc Back" if not self.submenu and self.menu_row in (4,5)
                            else "W Cycle shading  F5 Full/Four  R Fit")
                elif self.menu==2 and not self.submenu:
                    status="G Move; G again cycles Move/Scale/Rotate"
                elif self.menu==3:
                    status="O Cycle modes"
                    if self.mesh is not None and self.selection_mode!="Model":
                        status+="  P Camera/selection"
        footer_key=(width,height,hint,status) if footer else None
        if footer and (force or self._hud_keys[2]!=footer_key):
            draw._fill_rectangle(0,height-30,width,30,0x0000)
            draw._text(3,height-28,hint,0xFFFF)
            draw._text(3,height-14,status,0xFFFF)
            damage(self,(0,height-30,width,30))
        self._hud_keys[:]=[menu_key,document_key,footer_key]


    def vertex_info_layout(self):
        if (self.mesh is None or not self.show_vertex_info or
                (self._transform_pending or (self._interactive_visibility and self._camera_pending))):
            return None
        info=self.vertex_info()
        if info is None:
            return None
        index,point,linked,total=info
        width,height=int(self.vm.draw.size.x),int(self.vm.draw.size.y)
        if not self.four_view:
            lines=("V%d" % (index+1),)+tuple("%s %s" % ("XYZ"[axis],display_number(value))
                                          for axis,value in enumerate(point))
            pw,ph=max(len(line) for line in lines)*6+8,44
            return info,(width-pw-4,118 if self.show_orientation else 52,pw,ph),lines
        pw,ph=min(150,width-8),100
        x=4 if self.active_pane%2 else width-pw-4
        y=height-34-ph if self.active_pane<2 else 52
        return info,(x,y,pw,ph),None


    def draw_vertex_info(self, draw):
        layout=self.vertex_info_layout()
        if layout is None:
            return
        info,(x,y,pw,ph),lines=layout
        index,point,linked,total=info
        draw._fill_rectangle(x,y,pw,ph,0x18C3)
        draw._rectangle(x,y,pw,ph,0x07FF)
        if lines is not None:
            for row,line in enumerate(lines):
                draw._text(x+4,y+4+row*10,line,0x07FF if row==0 else 0xFFFF)
            return
        draw._text(x+6,y+5,"Selected: %d corners" % total,0xFFE0)
        draw._text(x+6,y+20,"V%d (%d linked)" % (index+1,linked),0x07FF)
        for axis,value in enumerate(point):
            draw._text(x+6,y+36+axis*14,"%s %s" % ("XYZ"[axis],display_number(value)),0xFFFF)
        draw._text(x+6,y+83,"J/K Browse  B Hide",0x7BEF)


    def dropdown(self, draw):
        """Draw a selectable dropdown directly below its menu title."""
        if self.menu < 0:
            return
        screen_width,screen_height = int(draw.size.x),int(draw.size.y)
        def panel(items,shortcuts,selected,x,y,width):
            visible = min(len(items),max(1,(screen_height-y-34)//17))
            first = max(0,selected-visible+1)
            height = visible*17+4
            draw._fill_rectangle(x,y,width,height,0x2945)
            draw._rectangle(x,y,width,height,0x7BEF)
            for row in range(first,first+visible):
                label,enabled = items[row]
                top = y+2+(row-first)*17
                if row == selected:
                    draw._fill_rectangle(x+2,top,width-4,17,0x051F)
                shortcut = shortcuts[row] if row < len(shortcuts) else ""
                label_width = width-12-(len(shortcut)*6+12 if shortcut else 0)
                draw._text(x+6,top+4,label[:label_width//6],0xFFFF if enabled else 0x7BEF)
                if shortcut:
                    draw._text(x+width-6-len(shortcut)*6,top+4,shortcut,0x07FF if enabled else 0x7BEF)
        if self.submenu:
            # Fit the two panels side by side on the 320px PicoCalc screen.
            left_width = screen_width//2-4
            panel(self.menu_items(parent=True),self.menu_shortcuts(parent=True),self.submenu_row,0,20,left_width)
            items = self.menu_items()
            y = min(22+self.submenu_row*17,screen_height-34-(len(items)*17+4))
            panel(items,self.menu_shortcuts(),self.menu_row,left_width,y,screen_width-left_width)
        else:
            width = min(164,screen_width)
            x = min(self.menu*52,screen_width-width)
            panel(self.menu_items(),self.menu_shortcuts(),self.menu_row,x,20,width)


    def draw_transform(self, draw, force=False):
        if self.transform is None:
            return
        t = self.transform
        step = max(t["step"],self.grid_step) if t["snap"] and t["kind"] == "Move" else t["step"]
        w, h = int(draw.size.x), int(draw.size.y)
        key=(t['kind'],tuple(t['values']),t['axis'],t['pivot'],t['uniform'],step,t['snap'],self.status,w,h)
        if not force and self._transform_hud == key:
            return
        from .framecache import damage
        draw._fill_rectangle(0, 0, w, 48, 0x2945)
        if self._transform_hud != key:
            damage(self,(0,0,w,48))
        draw._text(4,3,t["kind"] + " / " + ("XYZ" if t["kind"] == "Scale" and t["uniform"] else "XYZ"[t["axis"]]) + " Step " + display_number(step) + (" Snap GRID" if t["snap"] and t["kind"] == "Move" else " Snap ON" if t["snap"] else " Snap OFF"),0x07FF)
        draw._text(4,18,"X %s  Y %s  Z %s" % tuple(display_number(v) for v in t["values"]),0xFFFF)
        draw._text(4,33,self.status[:w//6] or ("Pivot: " + ("Center","Bottom center","World origin")[t["pivot"]] + (" Linked" if t["kind"] == "Scale" and t["uniform"] else "") + " / G Tool F5 View"),0xFFFF)
        if force or self._transform_hud is None or self._transform_hud[-2:] != (w,h):
            draw._fill_rectangle(0,h-30,w,30,0x2945)
            draw._text(3,h-28,"L/R Axis U/D Adjust E Value T Step",0xFFFF)
            draw._text(3,h-14,"S Snap -/+ Step P Pivot U Link Enter OK Esc Cancel",0xFFFF)
            if self._transform_hud is None or self._transform_hud[-2:] != (w,h):
                damage(self,(0,h-30,w,30))
        self._transform_hud=key


    def draw_dialog(self, draw):
        """Draw help, errors, or an overwrite confirmation above the scene."""
        if self.dialog is None:
            return
        width, height = int(draw.size.x), int(draw.size.y)
        draw._fill_rectangle(8, 55, width - 16, height - 94, 0x2945)
        draw._rectangle(8, 55, width - 16, height - 94, 0x7BEF)
        draw._text(16, 65, self.dialog[0], 0x07FF)
        columns = max(8, (width - 32) // 6)
        y = 88
        for line in self.dialog[1].split("\n"):
            for offset in range(0, max(1, len(line)), columns):
                if y < height - 66:
                    draw._text(16, y, line[offset:offset + columns], 0xFFFF)
                    y += 14
        hint = ("Enter Discard  Esc Cancel" if self.pending_action else
                "Enter Replace  Esc Cancel" if self.pending_save else "Enter/Esc Close")
        draw._text(16, height - 58, hint, 0xFFFF)


    def draw_frame(self):
        """Compose the preview and menus in a single display frame."""
        if self.viewer is not None:
            return
        now = ticks_ms()
        if (self._frame_drawn and (self.boolean_job is not None or self.decimation_job is not None)
                and ticks_diff(now,self._last_frame_ms) < 100):
            return
        if self.color_picker is not None:
            self._scene_keys.clear()
            self.draw_color_picker()
            return
        if self.transform is not None:
            self.ensure_transform_axis()
        draw = self.vm.draw
        from .framecache import pixels,damage,intersects,store_base
        cache=pixels(self)
        cache.regions=[]
        dirty,force,overlays=[],True,[]
        if self.mesh is not None:
            from .framecache import dirty_panes
            dirty,force,overlays = dirty_panes(self)
            if force:
                draw.clear(color=0x1082)
            if self.four_view:
                if dirty:
                    self.draw_four(draw,dirty,overlays)
            elif dirty:
                moving = self._transform_pending or (self._interactive_visibility and self._camera_pending)
                if 0 not in overlays:
                    if not force:
                        draw._fill_rectangle(0,48,int(draw.size.x),int(draw.size.y)-78,0x1082)
                    if self.show_grid and not moving:
                        self.grid(draw)
                    if self.shading == "Wireframe":
                        self.draw_selection(draw,wire_only=True)
                    else:
                        self.engine.run_async(False)
                    store_base(self,self.selection_projection()[0])
                self.draw_selection(draw)
                if not moving:
                    self.draw_normals(draw)
                    self.draw_edge_lengths(draw)
                    if self.show_orientation:
                        self.orientation(draw)
                    self.draw_gizmo(draw)
        else:
            draw.clear(color=0x1082)
            self._scene_keys.clear()
            self._scene_layout = None
            draw._text(20, int(draw.size.y) // 2, "File > Open or Create > Box", 0x7BEF)
        if self.mesh is None:
            damage(self,(0,0,int(draw.size.x),int(draw.size.y)))
        single_base=not self.four_view and dirty and 0 not in overlays
        if self.transform is None:
            self._transform_hud=None
            self.hud(draw,force or single_base or cache.erase_hud,
                     self.boolean_preview is None and self.boolean_job is None and self.decimation_job is None)
        else:
            self._hud_keys=[None,None,None]
        panels_dirty=force or cache.panel_changed or any(intersects(a,b) for a in cache.regions for b in cache.panels)
        if panels_dirty:
            self.draw_vertex_info(draw)
            self.dropdown(draw)
            for box in cache.panels:
                damage(self,box)
        if self.boolean_preview is not None:
            h = int(draw.size.y)
            draw._fill_rectangle(0,h-30,int(draw.size.x),30,0x2945)
            draw._text(3,h-28,(self.boolean_preview[0]+": "+self.status)[:int(draw.size.x)//6],0x07FF)
            draw._text(3,h-14,"Enter Apply Esc Cancel F5 View W Shade",0xFFFF)
        if self.boolean_job is not None:
            h = int(draw.size.y)
            draw._fill_rectangle(0,h-30,int(draw.size.x),30,0x2945)
            draw._text(3,h-28,self.status[:int(draw.size.x)//6],0x07FF)
            draw._text(3,h-14,"Calculating... Esc Cancel",0xFFFF)
        if self.decimation_job is not None:
            h = int(draw.size.y)
            draw._fill_rectangle(0,h-30,int(draw.size.x),30,0x2945)
            draw._text(3,h-28,"Decimate: "+self.status[:int(draw.size.x)//6-10],0x07FF)
            draw._text(3,h-14,"Calculating... Esc Cancel",0xFFFF)
        if self.transform is not None:
            self.draw_transform(draw,force or single_base or cache.erase_hud)
        if panels_dirty:
            self.draw_dialog(draw)
        if self.boolean_preview is not None or self.boolean_job is not None or self.decimation_job is not None:
            damage(self,(0,int(draw.size.y)-30,int(draw.size.x),30))
        cache.present()
        self._frame_drawn = True
        self._drawn_status = self.status
        self._last_frame_ms = ticks_ms()
        if self._transform_pending:
            # Rendering must not consume the quiet period on a slow device.
            self._transform_finished = self._last_frame_ms
