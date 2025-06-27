#pragma once
#include "../../../../internal/gui/draw.hpp"
using namespace Picoware;
#define MAX_MAP_WIDTH 64
#define MAX_MAP_HEIGHT 64
#define MAX_WALLS 100

#ifndef ColorWhite
#define ColorWhite TFT_WHITE
#endif

#ifndef ColorBlack
#define ColorBlack TFT_BLACK
#endif

enum TileType
{
    TILE_EMPTY = 0,
    TILE_WALL = 1,
    TILE_DOOR = 2,
    TILE_TELEPORT = 3,
    TILE_ENEMY_SPAWN = 4,
    TILE_ITEM_SPAWN = 5
};

// Wall structure for dynamic walls
struct Wall
{
    Vector start;
    Vector end;
    TileType type;
    uint8_t height;
    bool is_solid;
};

class DynamicMap
{
private:
    uint8_t width;
    uint8_t height;
    // eventually we'll add a color property to each tile
    // and turn it in to a struct
    // but obviously redundant for the Flipper Zero
    // save for the fillIn option,
    // it doesnt look that well on the Flipper Zero
    TileType tiles[MAX_MAP_HEIGHT][MAX_MAP_WIDTH];
    Wall walls[MAX_WALLS];
    uint8_t wall_count;
    const char *name;
    bool fillIn;

public:
    // Constructor
    DynamicMap(const char *name, uint8_t w, uint8_t h, bool addBorder = true, bool fillIn = false) : width(w), height(h), wall_count(0), name(name), fillIn(fillIn)
    {
        memset(tiles, 0, sizeof(tiles));
        if (addBorder)
        {
            this->addBorderWalls();
        }
    }

    // Methods in alphabetical order
    void addBorderWalls()
    {
        // Add walls around the entire map border
        addHorizontalWall(0, width - 1, 0, TILE_WALL);          // Top border
        addHorizontalWall(0, width - 1, height - 1, TILE_WALL); // Bottom border
        addVerticalWall(0, 0, height - 1, TILE_WALL);           // Left border
        addVerticalWall(width - 1, 0, height - 1, TILE_WALL);   // Right border
    }

    void addCorridor(uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2)
    {
        // Simple L-shaped corridor
        if (x1 == x2)
        {
            // Vertical corridor
            uint8_t start_y = (y1 < y2) ? y1 : y2;
            uint8_t end_y = (y1 < y2) ? y2 : y1;
            for (uint8_t y = start_y; y <= end_y; y++)
            {
                setTile(x1, y, TILE_EMPTY);
            }
        }
        else if (y1 == y2)
        {
            // Horizontal corridor
            uint8_t start_x = (x1 < x2) ? x1 : x2;
            uint8_t end_x = (x1 < x2) ? x2 : x1;
            for (uint8_t x = start_x; x <= end_x; x++)
            {
                setTile(x, y1, TILE_EMPTY);
            }
        }
        else
        {
            // L-shaped corridor (horizontal then vertical)
            uint8_t start_x = (x1 < x2) ? x1 : x2;
            uint8_t end_x = (x1 < x2) ? x2 : x1;
            for (uint8_t x = start_x; x <= end_x; x++)
            {
                setTile(x, y1, TILE_EMPTY);
            }

            uint8_t start_y = (y1 < y2) ? y1 : y2;
            uint8_t end_y = (y1 < y2) ? y2 : y1;
            for (uint8_t y = start_y; y <= end_y; y++)
            {
                setTile(x2, y, TILE_EMPTY);
            }
        }
    }

    void addDoor(uint8_t x, uint8_t y)
    {
        setTile(x, y, TILE_DOOR);
    }

    void addHorizontalWall(uint8_t x1, uint8_t x2, uint8_t y, TileType type = TILE_WALL)
    {
        for (uint8_t x = x1; x <= x2; x++)
        {
            setTile(x, y, type);
        }
    }

    void addRoom(uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2, bool add_walls = true)
    {
        // Clear the room area
        for (uint8_t y = y1; y <= y2; y++)
        {
            for (uint8_t x = x1; x <= x2; x++)
            {
                setTile(x, y, TILE_EMPTY);
            }
        }

        // Add walls around the room
        if (add_walls)
        {
            addHorizontalWall(x1, x2, y1, TILE_WALL); // Top wall
            addHorizontalWall(x1, x2, y2, TILE_WALL); // Bottom wall
            addVerticalWall(x1, y1, y2, TILE_WALL);   // Left wall
            addVerticalWall(x2, y1, y2, TILE_WALL);   // Right wall
        }
    }

    void addVerticalWall(uint8_t x, uint8_t y1, uint8_t y2, TileType type = TILE_WALL)
    {
        for (uint8_t y = y1; y <= y2; y++)
        {
            setTile(x, y, type);
        }
    }

    void addWall(Vector start, Vector end, TileType type = TILE_WALL, uint8_t height = 255, bool solid = true)
    {
        if (wall_count < MAX_WALLS)
        {
            walls[wall_count].start = start;
            walls[wall_count].end = end;
            walls[wall_count].type = type;
            walls[wall_count].height = height;
            walls[wall_count].is_solid = solid;
            wall_count++;
        }
    }

    uint8_t getBlockAt(uint8_t x, uint8_t y) const
    {
        // Make sure we're checking within bounds of our actual map
        if (x >= width || y >= height)
        {
            return 0x0; // Out of bounds is always empty
        }

        TileType tile = tiles[y][x];
        switch (tile)
        {
        case TILE_WALL:
        case TILE_DOOR:
            return 0xF;
        default:
            return 0x0;
        }
    }

    bool getFillIn() const { return fillIn; }

    uint8_t getHeight() const { return height; }

    const char *getName() const { return name; }

    TileType getTile(uint8_t x, uint8_t y) const
    {
        if (x >= width || y >= height)
        {
            return TILE_EMPTY; // Out of bounds = empty (no walls)
        }
        return tiles[y][x];
    }

    uint8_t getWidth() const { return width; }

    void render(float view_height, Draw *const canvas, Vector player_pos, Vector player_dir, Vector player_plane, Vector size = Vector(128, 64)) const
    {
        // render walls using existing raycasting
        uint16_t screen_width = (uint16_t)size.x;
        uint16_t screen_height = (uint16_t)size.y;

        for (uint16_t x = 0; x < screen_width; x += 2) // Use dynamic screen width with RES_DIVIDER
        {
            float camera_x = 2 * (float)x / screen_width - 1; // Use dynamic screen width
            float ray_x = player_dir.x + player_plane.x * camera_x;
            float ray_y = player_dir.y + player_plane.y * camera_x;
            uint8_t map_x = (uint8_t)player_pos.x;
            uint8_t map_y = (uint8_t)player_pos.y;

            // Prevent division by zero
            if (ray_x == 0)
                ray_x = 0.00001f;
            if (ray_y == 0)
                ray_y = 0.00001f;

            float delta_x = fabs(1 / ray_x);
            float delta_y = fabs(1 / ray_y);

            int8_t step_x;
            int8_t step_y;
            float side_x;
            float side_y;

            if (ray_x < 0)
            {
                step_x = -1;
                side_x = (player_pos.x - map_x) * delta_x;
            }
            else
            {
                step_x = 1;
                side_x = (map_x + (float)1.0 - player_pos.x) * delta_x;
            }

            if (ray_y < 0)
            {
                step_y = -1;
                side_y = (player_pos.y - map_y) * delta_y;
            }
            else
            {
                step_y = 1;
                side_y = (map_y + (float)1.0 - player_pos.y) * delta_y;
            }

            // Wall detection
            uint8_t depth = 0;
            bool hit = 0;
            bool side;

            // Follow the ray until we hit a wall or reach max depth
            while (!hit && depth < 12) // MAX_RENDER_DEPTH
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

                // Always default to empty space
                uint8_t block = 0x0;

                // Check if the coordinates are within the map boundaries
                if (map_x < width && map_y < height)
                {
                    // Use the tile from our actual map data
                    TileType tile = tiles[map_y][map_x];
                    if (tile == TILE_WALL || tile == TILE_DOOR)
                    {
                        block = 0xF;
                    }
                }

                if (block == 0xF) // Hit a wall
                {
                    hit = 1;
                }

                depth++;
            }

            if (hit)
            {
                float distance;

                if (side == 0)
                {
                    distance = fmax(1, (map_x - player_pos.x + (1 - step_x) / 2) / ray_x);
                }
                else
                {
                    distance = fmax(1, (map_y - player_pos.y + (1 - step_y) / 2) / ray_y);
                }

                // rendered line height - scale based on screen height
                uint16_t render_height = screen_height * 56 / 64; // Scale render height proportionally
                uint16_t line_height = render_height / distance;
                int16_t start_y = (int16_t)(view_height / distance - line_height / 2 + render_height / 2);
                int16_t end_y = (int16_t)(view_height / distance + line_height / 2 + render_height / 2);

                // Clamp to screen bounds
                if (start_y < 0)
                    start_y = 0;
                if (end_y >= screen_height)
                    end_y = screen_height - 1;

                // Draw vertical line
                int16_t dots = end_y - start_y;
                if (dots > 0)
                {
                    if (fillIn)
                    {
                        // Fill in walls pixel-by-pixel
                        for (int16_t i = 0; i < dots; i++)
                        {
                            // Draw the outline pixels
                            canvas->drawPixel(Vector(x, start_y + i), ColorBlack);
                            // Fill in the wall by drawing additional pixels to the right
                            if (x + 1 < screen_width) // Make sure we don't go out of bounds
                            {
                                canvas->drawPixel(Vector(x + 1, start_y + i), ColorBlack);
                            }
                        }
                    }
                    else
                    {
                        // draw the outline
                        for (int16_t i = 0; i < dots; i++)
                        {
                            canvas->drawPixel(Vector(x, start_y + i), ColorBlack);
                        }
                    }
                }
            }
        }
    }

    void setFillIn(bool fill) { fillIn = fill; }

    void setTile(uint8_t x, uint8_t y, TileType type)
    {
        if (x < width && y < height)
        {
            tiles[y][x] = type;
        }
    }
};