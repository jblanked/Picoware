"""Pico-game-engine scene for the board/replay view.

The current 2D Image renderer does not apply masks or scale sprites. The scene
therefore uses its supported render callback and PicoChess's bounded RGB565
compositor. No engine/firmware changes or duplicate game loop are needed.
"""


class BoardScene:
    def __init__(self, draw, render):
        import engine
        self.engine_type = engine.Engine
        from picoware.system.vector import Vector
        self.game = self.level = self.entity = self.engine = None
        self.render_frame = render
        self.app = None
        self.frames = 0
        try:
            # Native Game creates/owns its camera. Do not register the Level in
            # Game's owning level array: the Python wrappers are explicit owners.
            self.game = engine.Game('PicoChess', draw.size, 65535, 0, None, None, None, None, draw)
            self.level = engine.Level('Board', draw.size, self.game)
            self.level.set_clear_allowed(False)
            self.game.set_current_level(self.level)
            self.entity = engine.Entity('Board and notation', 2, Vector(0,0), draw.size,
                                        None,None,None,None,None,None,self.render)
            # Level removes/deletes non-player entities. Keep this callback entity
            # externally owned so wrapper finalizers cannot double-delete it.
            self.entity.set_is_player(True)
            self.entity.set_is_active(True)
            self.level.entity_add(self.entity)
            self.engine = engine.Engine(self.game, 30)
        except Exception:
            self.close()
            raise

    def render(self, draw, game):
        self.frames += 1
        self.render_frame(self.app)

    def draw(self, app):
        self.app = app
        self.engine_type.render(self.engine)

    def close(self):
        if self.engine:
            self.engine.__del__(self.engine)
            self.engine = None
        if self.game: self.game.set_current_level(None)
        if self.entity:
            if self.level: self.level.entity_remove(self.entity)
            self.entity.__del__(self.entity)
            self.entity = None
        if self.level:
            self.level.__del__(self.level)
            self.level = None
        if self.game:
            self.game.__del__(self.game)
            self.game = None
        self.app = None
        self.render_frame = None
