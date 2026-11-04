"""Camera navigation shared by the viewport and tool inspection."""
from time import ticks_ms,ticks_us,ticks_diff


def failure(e,exc,context="Camera"):
    from gc import collect
    collect()
    message=context+' failed: '+(str(exc) or 'Not enough memory')
    previous=e.status;e.status=message
    if previous==message:return
    try:
        from io import StringIO
        from sys import print_exception
        detail=StringIO();print_exception(exc,detail)
        e.vm.log('Sprite3D '+message+'\n'+detail.getvalue(),2)
    except Exception:
        # Reporting an exhausted heap or unavailable SD must remain harmless.
        print(message)


def control(e,button):
    from picoware.system.buttons import (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN,
        BUTTON_R,BUTTON_PLUS,BUTTON_EQUAL,BUTTON_MINUS)
    arrows=(BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN)
    if button not in arrows+(BUTTON_R,BUTTON_PLUS,BUTTON_EQUAL,BUTTON_MINUS):return False
    from .workspace import camera_state,restore_camera
    pending=e._camera_job
    original=snapshot(e)
    requested=e._camera_requested
    if requested is not None:restore(e,requested)
    before=camera_state(e)
    # Keep in-flight geometry tied to its camera. New input updates only the
    # requested pose; publish a complete frame before starting that pose.
    defer=e._interactive_visibility and e.shading!='Wireframe' and button!=BUTTON_R
    e._defer_camera=defer
    try:
        if button==BUTTON_R:e.fit_view()
        elif button not in arrows:
            factor=e.zoom_factor() if button==BUTTON_MINUS else 1/e.zoom_factor()
            if e.four_view:e.set_four(zoom=e.four_zoom*factor)
            else:
                minimum=e.fit_distance/128 if e.is_ortho() else e.radius+.15/e.perspective_scale()
                e.distance=max(minimum,min(e.fitted_distance()*8,e.distance*factor))
                e.update_camera()
        elif (e.four_view and e.active_pane!=1) or (not e.four_view and e.is_ortho()):
            # Move the target along the fixed view's screen axes.
            pane=e.panes[e.active_pane] if e.four_view else None
            basis=pane[3] if pane else e.basis
            target=e.pane_targets[e.active_pane] if pane else e.center
            step=(pane[5] if pane else e.distance)*e.orbit_increment()*.5
            axis=basis[0 if button in (BUTTON_LEFT,BUTTON_RIGHT) else 1]
            step*=1 if button in (BUTTON_RIGHT,BUTTON_UP) else -1
            target=tuple(target[i]+axis[i]*step for i in range(3))
            if pane:
                e.pane_targets[e.active_pane]=target;e.set_four()
            else:
                e.center=target;e._preview_angles=None;e.update_camera()
                if e.maximized:e.pane_targets[e.active_pane]=target
        else:
            angle=e.angle;pitch=e.four_pitch if e.four_view else e.pitch
            step=e.orbit_increment()
            if button in (BUTTON_LEFT,BUTTON_RIGHT):angle+=step if button==BUTTON_RIGHT else -step
            else:pitch=max(-1.45,min(1.45,pitch+(step if button==BUTTON_UP else -step)))
            if e.four_view:e.set_four(angle=angle,pitch=pitch)
            else:e.orient(angle,pitch,'Perspective' if e.maximized else 'Orbit',e.distance)
    except (ValueError,OSError,MemoryError) as exc:
        e._defer_camera=False
        if pending is not None:restore(e,original)
        else:restore_camera(e,before)
        failure(e,exc)
        return True
    finally:e._defer_camera=False
    if pending is not None:
        try:e._camera_requested=snapshot(e)
        finally:restore(e,original)
        poll(e)
    elif before!=camera_state(e) or requested is not None:
        e._camera_requested=None
        e._camera_pending,e._camera_finished=True,ticks_ms()
        if defer:
            e._camera_job=(view_steps(e,original[1][2],original[1][3]),original[0],original[1])
            poll(e)
    return True


def snapshot(e):
    from .workspace import camera_state
    return camera_state(e),(e.basis,e._preview_angles,e.panes,e._pane_centers)


def restore(e,state):
    for key,value in state[0].items():setattr(e,key,value)
    e.basis,e._preview_angles,e.panes,e._pane_centers=state[1]


def navigation_key(button):
    from picoware.system.buttons import BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN,BUTTON_PLUS,BUTTON_EQUAL,BUTTON_MINUS
    return button in (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN,BUTTON_PLUS,BUTTON_EQUAL,BUTTON_MINUS)


def cancel(e):
    e._camera_requested=None
    pending=e._camera_job
    if pending is None:return
    e._camera_job=None;pending[0].close()
    for key,value in pending[1].items():setattr(e,key,value)
    e.basis,e._preview_angles,e.panes,e._pane_centers=pending[2]
    e._frame_drawn=False


def poll(e):
    pending=e._camera_job
    if pending is None:
        requested=e._camera_requested
        if requested is None:return
        original=snapshot(e)
        try:
            restore(e,requested)
            e._camera_job=(view_steps(e,original[1][2],original[1][3]),original[0],original[1])
            e._camera_requested=None
        except (ValueError,OSError,MemoryError) as exc:
            restore(e,original);e._camera_requested=None
            failure(e,exc)
            return
        pending=e._camera_job
    start=ticks_us()
    try:
        while ticks_diff(ticks_us(),start)<4000:next(pending[0])
    except StopIteration:
        e._camera_job=None;e._frame_drawn=False
        e._camera_finished=ticks_ms()
    except (ValueError,OSError,MemoryError) as exc:
        cancel(e);failure(e,exc)


def view_steps(e,previous,centers):
    from .previewjobs import Prepared,view_steps as prepare_views
    from .meshes import apply_updates
    from picoware.system.vector import Vector
    job=Prepared(e,e.records);job.previous=previous;job.centers=centers
    try:
        try:
            yield from prepare_views(e,job)
        except MemoryError:
            # Settled overlays can fragment a constrained heap. They are
            # disposable; preserve native views while retrying staging once.
            from gc import collect,mem_free
            if mem_free()>=262144:raise
            job.discard()
            from .rendercache import clear
            clear(e,geometry_only=True)
            e.vertex_visibility_cache.clear();e.edge_label_cache.clear()
            job=Prepared(e,e.records);job.previous=previous;job.centers=centers
            collect()
            yield None
            yield from prepare_views(e,job)
        # Allocate the camera position before the atomic mesh update.
        position=Vector(-e.render_distance(),0)
        yield None
        apply_updates(job.updates)
        if job.panes is not None:
            e.panes=job.panes;e._pane_buffers=job.buffers;e._pane_centers=tuple(e.pane_targets)
        elif job.rendered is not None:
            e.render_mesh=job.rendered;e.entity.sprite_3d=job.rendered;e._preview_angles=job.angles
        e.camera.position=position;e.game.camera=e.camera
        job.committed=True
        for mesh in job.superseded:mesh.clear_triangles()
        job.updates.clear()
    finally:job.discard()
