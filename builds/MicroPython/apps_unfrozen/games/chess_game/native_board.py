"""One textured box, rendered by the engine without transferring mesh ownership."""
class NativeBoard:
    def __init__(self,renderer):
        import engine
        from picoware.system.vector import Vector
        self.mesh=engine.Sprite3D(False)
        self.renderer=renderer;self.theme=None
        self.position=Vector(0,0,0);self.direction=Vector(0,1,0)
        self.explicit_camera=None
        self.path='picoware/apps/games/chess_game/assets/'
        for _ in range(12):self.mesh.add_triangle(0,0,10,0,0,10,0,0,10,65535,False)
        if not self.mesh.from_uv_path(self.path+'board3d.uv'):raise OSError('Board UVs')

    def draw(self,board,theme):
        mesh=self.mesh;r=self.renderer
        if theme!=self.theme:
            if not mesh.from_texture_path(self.path+'board3d_'+str(theme)+'.rgb565',64,64):raise OSError('Board texture')
            self.theme=theme
        width,height=r.draw.size.x,r.draw.size.y
        corners=[board.project(u,v,h) for h in (0,-.18) for u,v in ((0,0),(8,0),(8,8),(0,8))]
        vertices=[((width*.5-x)*10/height,(height*.5-y)*10/height,10) for x,y in corners]
        # Draw the box sides before the top, sharing the same eight vertices.
        faces=((7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0),(0,1,2,3))
        index=0
        for a,b,c,d in faces:
            for triple in ((a,b,c),(a,c,d)):
                v0,v1,v2=(vertices[i] for i in triple)
                mesh.update_triangle(index,*(v0+v2+v1+(65535,False)));index+=1
        # New bindings take a caller-owned mesh plus explicit camera vectors.
        # Probe once; older mesh bindings still obtain these from the player.
        if self.explicit_camera is not False:
            try:
                r.scene.level.render_3d_sprite(mesh,self.position,self.direction,0,False,False,False)
            except TypeError:
                if self.explicit_camera:raise
                self.explicit_camera=False
                r.scene.entity.direction_set(0,1,0,False)
            else:
                self.explicit_camera=True
                return
        r.scene.level.render_3d_sprite(mesh,0,False,False)

    def close(self):
        if self.mesh:self.mesh.__del__(self.mesh);self.mesh=None
        self.position=self.direction=None
