"""Native masked billboard blits with explicit, independent resource lifetimes."""
class NativePieces:
    def __init__(self,draw):
        import engine
        if not hasattr(engine,'Billboard') or not hasattr(engine.Billboard,'set_direction_pose_data') or not hasattr(engine.Entity,'set_billboard'):
            raise ImportError('Native masked billboards unavailable')
        from picoware.system.vector import Vector
        self.engine_module=engine;self.assets={};self.game=self.level=self.entity=self.engine=None
        self.width,self.height=draw.size.x,draw.size.y
        self.camera=None
        self.cache={};self.order=[];self.source=None;self.source_path=None;self.side=32
        self.pixels=bytearray(1024);self.mask=bytearray(128)
        self.small_pixels=memoryview(self.pixels)[:256];self.small_mask=memoryview(self.mask)[:32]
        self.frame_buffer=None;self.frame_rows=();self.frame_side=None;self.frame_view=None
        try:
            self.game=engine.Game('Chess sprites',draw.size,65535,0,None,None,None,None,draw)
            self.level=engine.Level('Sprites',draw.size,self.game)
            self.level.set_clear_allowed(False);self.game.set_current_level(self.level)
            self.entity=engine.Entity('Piece',2,Vector(0,0),Vector(32,32))
            self.entity.set_is_active(True);self.level.entity_add(self.entity)
            self.camera=engine.Camera(Vector(0,0),Vector(0,1),Vector(1,0),0,1,0)
            self.game.set_camera(self.camera)
            self.engine=engine.Engine(self.game,30)
            # Three sequential chunk reads avoid small pixel/mask SD reads
            # without retaining a full 14 KB frame. Stream on smaller heaps.
            from gc import mem_free
            if mem_free()>49152:
                try:self.frame_buffer=bytearray(4608)
                except MemoryError:pass
        except Exception:
            self.close();raise

    def release(self,assets):
        for asset in assets.values():asset.__del__(asset)
        assets.clear()

    def clear(self):
        if self.entity:self.entity.set_billboard(None)
        for assets in self.cache.values():self.release(assets)
        self.cache.clear();self.order=[]
        self.release(self.assets)

    def load_frame(self,path,frame,side):
        if path!=self.source_path:
            self.clear()
            if self.source:self.source.close();self.source=None
            self.source_path=path
        key=(frame,side)
        if key in self.cache:
            self.entity.set_billboard(None)
            self.assets=self.cache[key];self.side=side
            self.order.remove(key);self.order.append(key)
            return
        # Recycle the non-visible slot. Keep the displayed frame untouched
        # until all twelve replacements are ready, including on read failure.
        pending={}
        for old in self.order[:]:
            if self.cache[old] is not self.assets:
                pending=self.cache.pop(old);self.order.remove(old)
        from gc import collect
        # Collect at the known frame-change boundary. Deferring this until
        # allocation pressure made the slowest rotation frames worse on device.
        collect()
        pixels=self.pixels if side==32 else self.small_pixels
        mask=self.mask if side==32 else self.small_mask
        offset=8+(110592 if side==32 else 0)+frame*12*(len(pixels)+len(mask))
        for attempt in range(2):
            try:
                if self.source is None:
                    source=open(path,'rb')
                    if source.read(8)!=b'PCS33201':
                        source.close();raise ValueError('Invalid native sprites')
                    self.source=source
                if self.frame_buffer is not None and self.frame_side!=side:
                    view=memoryview(self.frame_buffer);count=side*side;stride=count+count//8
                    rows=tuple((view[i*stride:i*stride+count],view[i*stride+count:(i+1)*stride]) for i in range(4))
                    self.frame_view=view[:4*stride];self.frame_rows=rows;self.frame_side=side
                self.source.seek(offset)
                for item in range(12):
                    if self.frame_buffer is not None:
                        if item%4==0 and self.source.readinto(self.frame_view)!=len(self.frame_view):
                            raise OSError('Incomplete native sprites')
                        pixels,mask=self.frame_rows[item%4]
                    elif self.source.readinto(pixels)!=len(pixels) or self.source.readinto(mask)!=len(mask):
                        raise OSError('Incomplete native sprites')
                    kind=item+1 if item<6 else -(item-5)
                    asset=pending.get(kind)
                    if asset is None:
                        asset=self.engine_module.Billboard(1,1);pending[kind]=asset
                    if not self.engine_module.Billboard.set_direction_pose_data(asset,0,0,side,side,pixels,mask):
                        raise MemoryError('Native sprite')
                break
            except (OSError,ValueError,MemoryError) as error:
                self.release(pending)
                if not isinstance(error,MemoryError) or attempt:raise
                # Fragmentation can matter even with enough total free RAM.
                # Retry once after releasing the incomplete, invisible slot.
                collect()
        self.entity.set_billboard(None)
        self.cache[key]=pending;self.order.append(key)
        self.assets=pending;self.side=side

    def add(self,kind,side,runs):
        pixels=bytearray(side*side);mask=bytearray(side*side//8)
        for x,y,data in runs:
            for i in range(len(data)//2):
                color=data[i*2]|(data[i*2+1]<<8);at=y*side+x+i
                pixels[at]=((color>>8)&224)|((color>>6)&28)|((color>>3)&3)
                mask[at//8]|=128>>(at&7)
        asset=self.engine_module.Billboard(1,1)
        if not self.engine_module.Billboard.set_direction_pose_data(asset,0,0,side,side,pixels,mask):raise MemoryError('Native sprite')
        self.assets[kind]=asset

    def draw(self,kind,cx,cy,side):
        # Convert screen coordinates to the engine's billboard camera plane.
        # A one-item level preserves the caller's back-to-front piece order.
        self.entity.set_billboard(self.assets[kind],1.0)
        self.entity.position_set((self.width*.5-cx)/side,self.height/side,0,False)
        self.camera.set_height((cy+side-int(side*.80)-self.height*.5)/side)
        self.game.set_camera(self.camera)
        self.engine_module.Engine.render(self.engine)

    def close(self):
        self.clear()
        if self.source:self.source.close();self.source=None
        self.source_path=None
        if self.engine:self.engine.__del__(self.engine);self.engine=None
        if self.game:self.game.set_current_level(None)
        if self.entity:
            self.entity.set_is_player(True)
            if self.level:self.level.entity_remove(self.entity)
            self.entity.__del__(self.entity);self.entity=None
        if self.level:self.level.__del__(self.level);self.level=None
        if self.game:self.game.__del__(self.game);self.game=None
        if self.camera:self.camera.__del__(self.camera);self.camera=None
        self.pixels=self.mask=self.small_pixels=self.small_mask=None
        self.frame_buffer=self.frame_view=None;self.frame_rows=();self.frame_side=None
