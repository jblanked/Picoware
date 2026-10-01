"""Load editor tools on first use, then bind their normal methods to the editor.

The registry lists the public mixin interface; startup tests check it against the
classes so new commands cannot silently miss the lazy dispatch table.
"""

TOOLS = (
    ('viewer', 'ViewerTools', ('begin_viewer', 'end_viewer', 'run_viewer')),
    ('viewport', 'ViewportMixin', ('shading_wireframe', 'set_shading', 'toggle_culling', 'refresh_previews', 'reset_camera', 'fit_view', 'set_view', 'clear_four', 'set_four', 'toggle_active_view', 'pane_control', 'draw_four', 'orient', 'update_camera', 'fitted_distance', 'perspective_scale', 'near_distance', 'render_distance', 'is_ortho', 'view_point', 'grid_line', 'ortho_grid', 'grid', 'orientation', 'draw_gizmo')),
    ('transforms', 'TransformTools', ('transform_axes', 'ensure_transform_axis', 'begin_transform', 'cycle_transform', 'preview_transform', 'commit_transform', 'run_transform')),
    ('selection', 'SelectionTools', ('vertex_groups', 'visible_vertex_mask', 'visible_triangle_mask', 'visible_component_mask', 'active_visibility', 'ensure_visible_vertex', 'get_islands', 'active_island', 'browse_island', 'selection_mode_set', 'cycle_selection', 'has_selection', 'selection_label', 'selection_fill', 'selection_toggle', 'selection_mask', 'selected_bounds', 'selected_triangles', 'selection_projection', 'projected_vertex', 'projected_triangle', 'navigate_vertex', 'navigate_triangle', 'navigate_component', 'vertex_info', 'cycle_vertex_info', 'selection_control', 'draw_selection')),
    ('editing', 'GeometryEditing', ('apply_geometry', 'clean_degenerates', 'clean_duplicates', 'edit_geometry', 'create_geometry', 'begin_edit_prompt', 'run_edit_prompt')),
    ('booleans', 'BooleanTools', ('clear_operands', 'capture_operand', 'select_connected_solid', 'begin_boolean', 'run_boolean_job', 'run_boolean')),
    ('normals', 'NormalTools', ('recalculate_normals', 'draw_normals', '_normal_cache_steps', '_normal_command_steps')),
    ('decimate', 'DecimateTools', ('begin_decimation', 'run_decimation')),
    ('colors', 'ColorTools', ('begin_color_picker', 'run_color_picker', 'draw_color_picker')),
    ('edges', 'EdgeTools', ('edge_labels', '_edge_label_steps', 'draw_edge_lengths')),
    ('edge_selection', 'EdgeSelection', ('get_edges', 'edge_points', 'edge_midpoint', 'visible_edge_mask', 'projected_edge', 'edge_vertex_mask', 'selected_edge_faces', 'draw_selected_edges')),
)


class LazyTools:
    def __getattr__(self, name):
        for module_name, class_name, names in TOOLS:
            if name in names:
                module = __import__('sprite3d_editor.'+module_name, None, None, (class_name,))
                mixin = getattr(module, class_name)
                cls = type(self)
                for method in names:
                    setattr(cls, method, getattr(mixin, method))
                return getattr(self, name)
        raise AttributeError(name)
