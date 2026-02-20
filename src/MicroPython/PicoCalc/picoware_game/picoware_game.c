/*
 * Picoware Game - Fast game rendering module for MicroPython
 * Handles raycasting, 3D sprite rendering, and game optimizations
 * Copyright © 2025 JBlanked
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "picoware_lcd.h"
#include <math.h>
#include <stdbool.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Map constants
#define MAX_RENDER_DEPTH 12
#define TILE_EMPTY 0
#define TILE_WALL 1
#define TILE_DOOR 2

// 3D rendering constants
#define MAX_TRIANGLES 100

// Static tile buffer
static uint8_t tile_buffer[64 * 64];

// PSRAM instance for framebuffer access
static psram_qspi_inst_t *psram_inst = NULL;

// Initialize or clear the tile buffer
STATIC mp_obj_t picoware_init_tile_buffer(mp_obj_t clear_value_obj)
{
    uint8_t clear_value = mp_obj_get_int(clear_value_obj);
    for (int i = 0; i < 64 * 64; i++)
    {
        tile_buffer[i] = clear_value;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_init_tile_buffer_obj, picoware_init_tile_buffer);

// Set a single tile
STATIC mp_obj_t picoware_set_tile(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, tile_value
    if (n_args != 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("set_tile requires 3 arguments: x, y, tile_value"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    uint8_t tile_value = mp_obj_get_int(args[2]);

    // Bounds check
    if (x >= 0 && x < 64 && y >= 0 && y < 64)
    {
        tile_buffer[y * 64 + x] = tile_value;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_set_tile_obj, 3, 3, picoware_set_tile);

// Get a single tile
STATIC mp_obj_t picoware_get_tile(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("get_tile requires 2 arguments: x, y"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);

    // Bounds check
    if (x >= 0 && x < 64 && y >= 0 && y < 64)
    {
        return mp_obj_new_int(tile_buffer[y * 64 + x]);
    }

    return mp_obj_new_int(TILE_EMPTY);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_get_tile_obj, 2, 2, picoware_get_tile);

// Convert RGB565 to RGB332 index
static inline uint8_t color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

// Fast vertical line drawing in PSRAM framebuffer
static inline void draw_vline(int x, int start_y, int end_y, uint8_t color_index, int screen_width, int screen_height, bool fill_in)
{
    // Get PSRAM instance if not already cached
    if (!psram_inst)
    {
        psram_inst = picoware_get_psram_instance();
        if (!psram_inst)
            return; // PSRAM not initialized
    }

    // Clamp to screen bounds
    if (start_y < 0)
        start_y = 0;
    if (end_y >= screen_height)
        end_y = screen_height - 1;
    if (x < 0 || x >= screen_width)
        return;

    // Draw vertical line using PSRAM writes
    for (int y = start_y; y <= end_y; y++)
    {
        picoware_write_pixel_fb(psram_inst, x, y, color_index);

        // Fill in adjacent pixel if requested
        if (fill_in && x + 1 < screen_width)
        {
            picoware_write_pixel_fb(psram_inst, x + 1, y, color_index);
        }
    }
}

// Main rendering function
STATIC mp_obj_t picoware_render_map(size_t n_args, const mp_obj_t *args)
{
    // Arguments: map_width, map_height, player_x, player_y,
    //            dir_x, dir_y, plane_x, plane_y, view_height,
    //            screen_width, screen_height, fill_in, wall_color
    if (n_args != 13)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("render_map requires 13 arguments"));
    }

    // Use static tile buffer (no need to pass it)
    int map_width = mp_obj_get_int(args[0]);
    int map_height = mp_obj_get_int(args[1]);

    // Player position and direction
    float player_x = mp_obj_get_float(args[2]);
    float player_y = mp_obj_get_float(args[3]);
    float dir_x = mp_obj_get_float(args[4]);
    float dir_y = mp_obj_get_float(args[5]);
    float plane_x = mp_obj_get_float(args[6]);
    float plane_y = mp_obj_get_float(args[7]);

    // Rendering parameters
    float view_height = mp_obj_get_float(args[8]);
    int screen_width = mp_obj_get_int(args[9]);
    int screen_height = mp_obj_get_int(args[10]);
    bool fill_in = mp_obj_is_true(args[11]);
    uint16_t wall_color = mp_obj_get_int(args[12]);

    uint8_t color_index = color565_to_332(wall_color);

    // Raycasting loop - iterate through screen columns with step of 2
    for (int x = 0; x < screen_width; x += 2)
    {
        // Calculate camera x position (from -1 to 1)
        float camera_x = 2.0f * x / screen_width - 1.0f;

        // Calculate ray direction
        float ray_x = dir_x + plane_x * camera_x;
        float ray_y = dir_y + plane_y * camera_x;

        // Current map position
        int map_x = (int)player_x;
        int map_y = (int)player_y;

        // Prevent division by zero
        if (ray_x == 0.0f)
            ray_x = 0.00001f;
        if (ray_y == 0.0f)
            ray_y = 0.00001f;

        // Calculate delta distances
        float delta_x = fabsf(1.0f / ray_x);
        float delta_y = fabsf(1.0f / ray_y);

        // Calculate step and initial side distances
        int step_x, step_y;
        float side_x, side_y;

        if (ray_x < 0)
        {
            step_x = -1;
            side_x = (player_x - map_x) * delta_x;
        }
        else
        {
            step_x = 1;
            side_x = (map_x + 1.0f - player_x) * delta_x;
        }

        if (ray_y < 0)
        {
            step_y = -1;
            side_y = (player_y - map_y) * delta_y;
        }
        else
        {
            step_y = 1;
            side_y = (map_y + 1.0f - player_y) * delta_y;
        }

        // Wall detection using DDA algorithm
        int depth = 0;
        bool hit = false;
        int side = 0;

        while (!hit && depth < MAX_RENDER_DEPTH)
        {
            // Cast the ray forward
            if (side_x < side_y)
            {
                side_x += delta_x;
                map_x += step_x;
                side = 0;
            }
            else
            {
                side_y += delta_y;
                map_y += step_y;
                side = 1;
            }

            // Check if we hit a wall
            if (map_x >= 0 && map_x < map_width && map_y >= 0 && map_y < map_height)
            {
                // Access tile from static buffer
                uint8_t tile = tile_buffer[map_y * 64 + map_x];
                if (tile == TILE_WALL || tile == TILE_DOOR)
                {
                    hit = true;
                }
            }

            depth++;
        }

        if (hit)
        {
            // Calculate distance to wall
            float distance;
            if (side == 0)
            {
                distance = (map_x - player_x + (1 - step_x) / 2.0f) / ray_x;
            }
            else
            {
                distance = (map_y - player_y + (1 - step_y) / 2.0f) / ray_y;
            }

            // Ensure minimum distance
            if (distance < 1.0f)
                distance = 1.0f;

            // Calculate line height
            int render_height = screen_height * 56 / 64;
            int line_height = (int)(render_height / distance);
            int start_y = (int)(view_height / distance - line_height / 2 + render_height / 2);
            int end_y = (int)(view_height / distance + line_height / 2 + render_height / 2);

            // Draw vertical line
            draw_vline(x, start_y, end_y, color_index, screen_width, screen_height, fill_in);
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_render_map_obj, 13, 13, picoware_render_map);

// 3D Sprite rendering function - transforms and renders raw triangles
STATIC mp_obj_t picoware_render_sprite3d(size_t n_args, const mp_obj_t *args)
{
    // Arguments: raw_triangles (bytearray of floats), triangle_count,
    //            sprite_x, sprite_y, sprite_rotation_y, sprite_scale, sprite_color,
    //            player_x, player_y, player_dir_x, player_dir_y,
    //            view_height, screen_width, screen_height
    if (n_args != 14)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("render_sprite3d requires 14 arguments"));
    }

    // Get triangle data (raw model space: flat array of 9 floats per triangle: x1,y1,z1, x2,y2,z2, x3,y3,z3)
    mp_buffer_info_t tri_info;
    mp_get_buffer_raise(args[0], &tri_info, MP_BUFFER_READ);
    float *raw_triangles = (float *)tri_info.buf;

    int triangle_count = mp_obj_get_int(args[1]);

    // Sprite transform
    float sprite_x = mp_obj_get_float(args[2]);
    float sprite_y = mp_obj_get_float(args[3]);
    float sprite_rotation_y = mp_obj_get_float(args[4]);
    float sprite_scale = mp_obj_get_float(args[5]);
    uint16_t sprite_color = mp_obj_get_int(args[6]);

    // Player/camera info
    float player_x = mp_obj_get_float(args[7]);
    float player_y = mp_obj_get_float(args[8]);
    float player_dir_x = mp_obj_get_float(args[9]);
    float player_dir_y = mp_obj_get_float(args[10]);
    float view_height = mp_obj_get_float(args[11]);

    // Screen info
    int screen_width = mp_obj_get_int(args[12]);
    int screen_height = mp_obj_get_int(args[13]);

    uint8_t color_index = color565_to_332(sprite_color);

    // Precompute rotation matrices
    float cos_rot = cosf(sprite_rotation_y);
    float sin_rot = sinf(sprite_rotation_y);

    // Camera vectors for projection
    float forward_x = player_dir_x;
    float forward_z = player_dir_y;
    float right_x = player_dir_y; // Perpendicular
    float right_z = -player_dir_x;
    float fov_scale = (float)screen_height;
    float half_width = screen_width / 2.0f;
    float half_height = screen_height / 2.0f;

    // Process each triangle
    for (int t = 0; t < triangle_count; t++)
    {
        int tri_offset = t * 9; // 9 floats per triangle (raw model space)

        // Get raw triangle vertices (model space)
        float raw_v[3][3]; // 3 vertices x 3 components (x,y,z)
        for (int v = 0; v < 3; v++)
        {
            raw_v[v][0] = raw_triangles[tri_offset + v * 3 + 0]; // x
            raw_v[v][1] = raw_triangles[tri_offset + v * 3 + 1]; // y
            raw_v[v][2] = raw_triangles[tri_offset + v * 3 + 2]; // z
        }

        // Transform vertices: Scale -> Rotate -> Translate
        float world_v[3][3]; // World space vertices
        for (int v = 0; v < 3; v++)
        {
            // Scale
            float sx = raw_v[v][0] * sprite_scale;
            float sy = raw_v[v][1] * sprite_scale;
            float sz = raw_v[v][2] * sprite_scale;

            // Rotate around Y axis
            float rx = sx * cos_rot - sz * sin_rot;
            float ry = sy;
            float rz = sx * sin_rot + sz * cos_rot;

            // Translate to world position
            world_v[v][0] = rx + sprite_x;
            world_v[v][1] = ry; // No Y offset (already at correct height)
            world_v[v][2] = rz + sprite_y;
        }

        // Backface culling - calculate normal in world space
        float edge1x = world_v[1][0] - world_v[0][0];
        float edge1y = world_v[1][1] - world_v[0][1];
        float edge1z = world_v[1][2] - world_v[0][2];
        float edge2x = world_v[2][0] - world_v[0][0];
        float edge2y = world_v[2][1] - world_v[0][1];
        float edge2z = world_v[2][2] - world_v[0][2];

        // Cross product for normal
        float normalx = edge1y * edge2z - edge1z * edge2y;
        float normaly = edge1z * edge2x - edge1x * edge2z;
        float normalz = edge1x * edge2y - edge1y * edge2x;

        // Triangle center
        float centerx = (world_v[0][0] + world_v[1][0] + world_v[2][0]) / 3.0f;
        float centery = (world_v[0][1] + world_v[1][1] + world_v[2][1]) / 3.0f;
        float centerz = (world_v[0][2] + world_v[1][2] + world_v[2][2]) / 3.0f;

        // Vector to camera
        float to_cam_x = player_x - centerx;
        float to_cam_y = view_height - centery;
        float to_cam_z = player_y - centerz;

        // Dot product - skip if facing away
        float dot = normalx * to_cam_x + normaly * to_cam_y + normalz * to_cam_z;
        if (dot <= 0.0f)
            continue;

        // Project all 3 vertices
        int screen_x[3], screen_y[3];
        bool all_visible = true;

        for (int i = 0; i < 3; i++)
        {
            // Transform to camera space
            float world_dx = world_v[i][0] - player_x;
            float world_dz = world_v[i][2] - player_y;
            float world_dy = world_v[i][1] - view_height;

            float cam_x = world_dx * right_x + world_dz * right_z;
            float cam_z = world_dx * forward_x + world_dz * forward_z;
            float cam_y = world_dy;

            // Behind camera check
            if (cam_z <= 0.1f)
            {
                all_visible = false;
                break;
            }

            // Project to screen
            float sx = (cam_x / cam_z) * fov_scale + half_width;
            float sy = (-cam_y / cam_z) * fov_scale + half_height;

            screen_x[i] = (int)sx;
            screen_y[i] = (int)sy;

            // Bounds check
            if (screen_x[i] < 0 || screen_x[i] >= screen_width ||
                screen_y[i] < 0 || screen_y[i] >= screen_height)
            {
                all_visible = false;
                break;
            }
        }

        if (!all_visible)
            continue;

        // Rasterize triangle using scanline algorithm
        // Sort vertices by Y coordinate (bubble sort for 3 elements)
        for (int i = 0; i < 2; i++)
        {
            for (int j = 0; j < 2 - i; j++)
            {
                if (screen_y[j] > screen_y[j + 1])
                {
                    // Swap Y
                    int temp = screen_y[j];
                    screen_y[j] = screen_y[j + 1];
                    screen_y[j + 1] = temp;
                    // Swap X
                    temp = screen_x[j];
                    screen_x[j] = screen_x[j + 1];
                    screen_x[j + 1] = temp;
                }
            }
        }

        // Fill triangle using scanlines
        int y0 = screen_y[0], y1 = screen_y[1], y2 = screen_y[2];
        int x0 = screen_x[0], x1 = screen_x[1], x2 = screen_x[2];

        // Handle degenerate case
        if (y0 == y2)
            continue;

        for (int y = y0; y <= y2; y++)
        {
            if (y < 0 || y >= screen_height)
                continue;

            int x_left, x_right;
            bool has_bounds = false;

            // Calculate left and right bounds for this scanline
            if (y2 != y0)
            {
                x_left = x0 + (x2 - x0) * (y - y0) / (y2 - y0);
                has_bounds = true;
            }

            if (y <= y1)
            {
                if (y1 != y0)
                    x_right = x0 + (x1 - x0) * (y - y0) / (y1 - y0);
                else
                    x_right = x_left;
            }
            else
            {
                if (y2 != y1)
                    x_right = x1 + (x2 - x1) * (y - y1) / (y2 - y1);
                else
                    x_right = x_left;
            }

            if (!has_bounds)
                continue;

            // Ensure x_left < x_right
            if (x_left > x_right)
            {
                int temp = x_left;
                x_left = x_right;
                x_right = temp;
            }

            // Clamp to screen bounds
            if (x_left < 0)
                x_left = 0;
            if (x_right >= screen_width)
                x_right = screen_width - 1;

            // Draw horizontal line using PSRAM writes
            for (int x = x_left; x <= x_right; x++)
            {
                picoware_write_pixel_fb(psram_inst, x, y, color_index);
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_render_sprite3d_obj, 14, 14, picoware_render_sprite3d);

// Module globals table
STATIC const mp_rom_map_elem_t picoware_game_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_game)},
    {MP_ROM_QSTR(MP_QSTR_init_tile_buffer), MP_ROM_PTR(&picoware_init_tile_buffer_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_tile), MP_ROM_PTR(&picoware_set_tile_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_tile), MP_ROM_PTR(&picoware_get_tile_obj)},
    {MP_ROM_QSTR(MP_QSTR_render_map), MP_ROM_PTR(&picoware_render_map_obj)},
    {MP_ROM_QSTR(MP_QSTR_render_sprite3d), MP_ROM_PTR(&picoware_render_sprite3d_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_game_module_globals, picoware_game_module_globals_table);

// Module definition
const mp_obj_module_t picoware_game_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_game_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_picoware_game, picoware_game_user_cmodule);
