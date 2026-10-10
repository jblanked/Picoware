"""Cooperative model/view staging; publish only a fully prepared transaction."""
from math import pi
from .meshes import MeshBuffer,prepare_mesh_steps,apply_updates,discard_updates


def view_key(e):
    return (e.four_view,e.angle,e.pitch,e.four_pitch,e.distance,e.shading,e.backface_culling,
            tuple(e.center),tuple(e.pane_targets),tuple(e.pane_radii),tuple(e.pane_zooms),
            e.active_pane,e.perspective_scale(),e.basis)


class Prepared:
    def __init__(self,editor,records):
        self.records=records;self.updates=[];self.committed=False
        self.mesh=None;self.rendered=None;self.panes=None;self.buffers=None
        self.visibility={};self.labels={};self.superseded=[];self.bounds=None;self.quads=None
    def discard(self):
        if not self.committed:discard_updates(self.updates)
        self.updates.clear()
    def commit(self,e):
        from .rendercache import clear
        clear(e)
        apply_updates(self.updates)
        old=e.mesh;e.mesh=self.mesh;e.records=self.records;e.bounds=self.bounds
        if self.quads is not None:e.quads=self.quads
        e._quad_display_mode=e.selection_mode=="Quads"
        e.islands=None;e.vertex_visibility_cache=self.visibility;e.edge_label_cache=self.labels
        e._edge_reps=None;e._preview_angles=None
        if self.panes is not None:
            e.panes=self.panes;e._pane_buffers=self.buffers;e._pane_centers=tuple(e.pane_targets)
        elif self.rendered is not None:
            e.render_mesh=self.rendered;e.entity.sprite_3d=self.rendered;e._preview_angles=self.angles
        self.committed=True
        if old is not self.mesh:old.clear_triangles()
        for mesh in self.superseded:mesh.clear_triangles()
        self.updates.clear()


def view_steps(e,job):
    from .viewport import view_basis,preview_records_steps
    records=job.records
    if not e.four_view:
        if e.shading!='Wireframe':
            output=yield from preview_records_steps(records,e.center,e.basis,
                ortho_distance=e.distance if e.is_ortho() else None,wireframe=e.shading_wireframe(),
                perspective_scale=e.perspective_scale(),culling=e.backface_culling,camera_distance=e.distance)
            job.rendered=yield from prepare_mesh_steps(e._preview_buffer,output,job.updates,False)
            if e.render_mesh is not job.rendered:job.superseded=[e.render_mesh]
        job.angles=(e.angle,e.pitch,e.distance,e.shading,e.perspective_scale(),e.backface_culling)
        return
    width,height=int(e.vm.draw.size.x),int(e.vm.draw.size.y)
    half_width,half_height=width//2,(height-78)//2
    specs=(("Top",-pi/2,pi/2),("Perspective",e.angle,e.four_pitch),("Front",-pi/2,0),("Side",pi,0))
    buffers=e._pane_buffers if len(e._pane_buffers)==4 else [MeshBuffer() for _ in range(4)]
    previous=getattr(job,'previous',e.panes);panes=[]
    centers=getattr(job,'centers',None)
    for i,(label,yaw,pitch) in enumerate(specs):
        x,y=(i%2)*half_width,48+(i//2)*half_height
        w=half_width if i%2==0 else width-half_width
        h=half_height if i<2 else height-30-y
        box=(x,y,w,h);viewport=(x+2,y+16,w-4,h-18);px,py,pw,ph=viewport
        radius=e.pane_radii[i];distance=radius*(1+ph/max(4,min(pw*.42,ph*.42)))*e.pane_zooms[i]
        if label=='Perspective':distance=max(radius+.15/e.perspective_scale(),distance)
        basis=view_basis(yaw,pitch)
        transform=(ph/height,(px+pw/2-width/2)/height,(height/2-py-ph/2)/height,distance,(pw/2-1)/ph,(ph/2-1)/ph)
        if (centers is not None and len(previous)==4 and centers[i]==e.pane_targets[i]
                and previous[i][2]==viewport and previous[i][3]==basis and previous[i][5]==distance):
            panes.append(previous[i]);yield None;continue
        if e.shading=='Wireframe' and len(previous)==4:mesh=previous[i][4]
        else:
            output=yield from preview_records_steps(records,e.pane_targets[i],basis,transform,
                distance if label!='Perspective' else None,e.shading_wireframe(),e.perspective_scale(),e.backface_culling,distance)
            mesh=yield from prepare_mesh_steps(buffers[i],output,job.updates,False)
        panes.append((label,box,viewport,basis,mesh,distance));yield None
    job.panes=panes;job.buffers=buffers
    job.superseded=[p[4] for p in previous if not any(p[4] is q[4] for q in panes)]


def prepare_steps(e,records):
    from struct import unpack_from
    from gc import collect
    job=Prepared(e,records);transferred=False
    try:
        low,high=[float('inf')]*3,[-float('inf')]*3
        for offset in range(0,len(records),40):
            values=unpack_from('<9f',records,offset)
            for j in (0,3,6):
                for k in range(3):low[k]=min(low[k],values[j+k]);high[k]=max(high[k],values[j+k])
            if offset%320==0:yield None
        job.bounds=(low,high) if records else ([-.5,0,-.5],[.5,1,.5])
        job.mesh=yield from prepare_mesh_steps(e._model_buffer,records,job.updates)
        while True:
            key=view_key(e);worker=view_steps(e,job)
            try:
                for progress in worker:
                    yield progress
                    if key!=view_key(e):break
                else:
                    transferred=True;return job
            finally:worker.close()
            discard_updates(job.updates[1:]);del job.updates[1:]
            job.rendered=None;job.panes=None;job.buffers=None;job.superseded=[]
            collect()
    finally:
        if not transferred:job.discard()
