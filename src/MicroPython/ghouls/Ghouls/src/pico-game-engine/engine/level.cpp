#include "entity.hpp"
#include "game.hpp"
#include "level.hpp"
#include "sprite3d.hpp"
#include "../engine_config.hpp"
#include ENGINE_LCD_INCLUDE
#include <math.h>
#ifdef ENGINE_LOG_INCLUDE
#include ENGINE_LOG_INCLUDE
#endif

// Default Constructor
Level::Level()
    : name(""),
      size(Vector(0, 0)),
      clearAllowed(true),
      gameRef(nullptr),
      entity_count(0),
      entities(nullptr),
      lightDirection(Vector(0.577f, 0.577f, 0.577f)),
      renderOrder(nullptr),
      shadowColor(0),
      _start{},
      _stop{}
{
}

// Parameterized Constructor
Level::Level(const char *name, const Vector &size, Game *game, CallbackLevel start, CallbackLevel stop)
    : name(name),
      size(size),
      clearAllowed(true),
      gameRef(game),
      entity_count(0),
      entities(nullptr),
      lightDirection(Vector(0.577f, 0.577f, 0.577f)),
      renderOrder(nullptr),
      shadowColor(0),
      _start(start),
      _stop(stop)
{
}

// Destructor
Level::~Level()
{
    clear();
}

// Clear all entities
void Level::clear()
{
    for (int i = 0; i < entity_count; i++)
    {
        if (entities[i] != nullptr)
        {
            entities[i]->stop(this->gameRef);
            // Only delete entities that are not players (players are managed externally)
            if (!entities[i]->is_player)
            {
                ENGINE_MEM_DELETE entities[i];
            }
            entities[i] = nullptr;
        }
    }
    // Free the dynamic array
    ENGINE_MEM_DELETE[] entities;
    entities = nullptr;
    entity_count = 0;
    ENGINE_MEM_FREE(renderOrder);
    renderOrder = nullptr;
}

// Get list of collisions for a given entity
Entity **Level::collision_list(Entity *entity, int &count) const
{
    count = 0;
    if (entity_count == 0)
    {
        ENGINE_LOG_INFO("Level::collision_list called but no entities are present\n");
        return nullptr;
    }

    Entity **result = ENGINE_MEM_NEW Entity *[entity_count];
    for (int i = 0; i < entity_count; i++)
    {
        if (entities[i] != nullptr &&
            entities[i] != entity && // Skip self
            is_collision(entity, entities[i]))
        {
            result[count++] = entities[i];
        }
    }
    return result;
}

void Level::drawProjectedTriangle(Draw *draw, const Vector vertices[3], const Vector &screen, uint16_t color, bool wireframe, bool clamp, uint8_t alpha)
{
    Vector polygon[ENGINE_MAX_PROJECTION_VERTICES];
    const int count = projectionProject(vertices, screen.x, screen.y, clamp, polygon);
    uint16_t x[ENGINE_MAX_PROJECTION_VERTICES], y[ENGINE_MAX_PROJECTION_VERTICES];
    for (int i = 0; i < count; ++i)
    {
        x[i] = static_cast<uint16_t>(polygon[i].x);
        y[i] = static_cast<uint16_t>(polygon[i].y);
    }
    if (alpha == 255)
        draw->fillPolygon(x, y, count, color);
    else
        draw->fillPolygonAlpha(x, y, count, color, alpha);
    if (wireframe)
    {
        uint8_t r = (color >> 11) & 0x1F;
        uint8_t g = (color >> 5) & 0x3F;
        uint8_t b = color & 0x1F;
        r += (0x1F - r) >> 1;
        g += (0x3F - g) >> 1;
        b += (0x1F - b) >> 1;
        const uint16_t outline = ((uint16_t)r << 11) | ((uint16_t)g << 5) | b;
        draw->polygon(x, y, count, outline);
    }
}

// Add an entity to the level
void Level::entity_add(Entity *entity)
{
    if (!entity)
    {
        ENGINE_LOG_INFO("Level::entity_add called with null entity pointer\n");
        return;
    }

    if (!this->gameRef)
    {
        ENGINE_LOG_INFO("Level::entity_add called but level has no reference to game\n");
        return;
    }

    // Allocate a new array with size one greater than the current count
    Entity **newEntities = ENGINE_MEM_NEW Entity * [entity_count + 1];
    if (!newEntities)
    {
        ENGINE_LOG_INFO("Level::entity_add failed to allocate memory for new entity array\n");
        return;
    }

    // Copy the existing entity pointers (if any)
    for (int i = 0; i < entity_count; i++)
    {
        newEntities[i] = entities[i];
    }
    newEntities[entity_count] = entity;

    // Delete the old array
    ENGINE_MEM_DELETE[] entities;
    entities = newEntities;
    entity_count++;

    // Grow the depth-sort scratch buffer to match
    ENGINE_MEM_FREE(renderOrder);
    renderOrder = (int *)ENGINE_MEM_MALLOC(entity_count * sizeof(int));

    // Start the new entity
    entity->start(this->gameRef);
    entity->is_active = true;
}

// Remove an entity from the level
void Level::entity_remove(Entity *entity)
{
    if (entity_count == 0)
    {
        ENGINE_LOG_INFO("Level::entity_remove called but no entities are present\n");
        return;
    }

    int remove_index = -1;
    for (int i = 0; i < entity_count; i++)
    {
        if (entities[i] == entity)
        {
            remove_index = i;
            break;
        }
    }

    if (remove_index == -1)
    {
        ENGINE_LOG_INFO("Level::entity_remove called but entity not found\n");
        return;
    }

    // Stop and delete the entity (only if it's not a player - players are managed externally)
    entities[remove_index]->stop(this->gameRef);
    if (!entities[remove_index]->is_player)
    {
        ENGINE_MEM_DELETE entities[remove_index];
    }

    // Allocate a new array with one fewer slot (if any remain)
    Entity **newEntities = (entity_count - 1 > 0) ? ENGINE_MEM_NEW Entity * [entity_count - 1] : nullptr;
    // Copy over all pointers except the removed one
    for (int i = 0, j = 0; i < entity_count; i++)
    {
        if (i == remove_index)
            continue;
        newEntities[j++] = entities[i];
    }

    // Free the old array and update state
    ENGINE_MEM_DELETE[] entities;
    entities = newEntities;
    entity_count--;

    // Shrink the depth-sort scratch buffer to match
    ENGINE_MEM_FREE(renderOrder);
    renderOrder = entity_count > 0 ? (int *)ENGINE_MEM_MALLOC(entity_count * sizeof(int)) : nullptr;
}

// Check if any entity has collided with the given entity
bool Level::has_collided(Entity *entity) const
{
    for (int i = 0; i < entity_count; i++)
    {
        if (entities[i] != nullptr &&
            entities[i] != entity &&
            is_collision(entity, entities[i]))
        {
            return true;
        }
    }
    return false;
}

// Determine if two entities are colliding
bool Level::is_collision(const Entity *a, const Entity *b) const
{
    return a->position.x < b->position.x + b->size.x &&
           a->position.x + a->size.x > b->position.x &&
           a->position.y < b->position.y + b->size.y &&
           a->position.y + a->size.y > b->position.y;
}

void Level::project3DTo2D(const Vector &vertex, const Vector &player_pos, const Vector &player_dir, float view_height, const Vector &screen_size, Vector &result)
{
    // Transform world coordinates to camera coordinates
    const float world_dx = vertex.x - player_pos.x;
    const float world_dz = vertex.z - player_pos.y; // player_pos.y is actually the Z coordinate in world space
    const float world_dy = vertex.y - view_height;  // Height difference from camera

    // Transform to camera space with camera coordinate system
    const float camera_x = world_dx * -player_dir.y + world_dz * player_dir.x;
    const float camera_z = world_dx * player_dir.x + world_dz * player_dir.y;

    // Prevent division by zero and reject points behind camera
    if (camera_z <= 0.1f)
    {
        result.x = -1;
        result.y = -1;
        result.z = 0.0f;
        return; // Invalid point (behind camera)
    }

    // Project to screen coordinates - scale based on screen size
    const float inv_camera_z = 1.0f / camera_z;
    result.x = camera_x * inv_camera_z * screen_size.y + (screen_size.x * 0.5f);
    result.y = -world_dy * inv_camera_z * screen_size.y + (screen_size.y * 0.5f);
    result.z = camera_z; // Store depth
}

float Level::projectionBound(float value, float maximum)
{
    return value < 0 ? 0 : (value > maximum ? maximum : value);
}

int Level::projectionClip(const Vector *input, int count, Vector *output, const Vector &normal, float offset)
{
    int written = 0;
    Vector previous = input[count - 1];
    float previous_distance = projectionDistance(previous, normal, offset);
    for (int i = 0; i < count; ++i)
    {
        const Vector &current = input[i];
        const float current_distance = projectionDistance(current, normal, offset);
        if ((current_distance > 0 && previous_distance < 0) ||
            (current_distance < 0 && previous_distance > 0))
        {
            if (written == ENGINE_MAX_PROJECTION_VERTICES)
                return 0;
            const float t = previous_distance / (previous_distance - current_distance);
            output[written++] = Vector(
                previous.x + t * (current.x - previous.x),
                previous.y + t * (current.y - previous.y),
                previous.z + t * (current.z - previous.z));
        }
        if (current_distance >= 0)
        {
            if (written == ENGINE_MAX_PROJECTION_VERTICES)
                return 0;
            output[written++] = current;
        }
        previous = current;
        previous_distance = current_distance;
    }
    return written;
}

float Level::projectionDistance(const Vector &vertex, const Vector &normal, float offset)
{
    return normal.x * vertex.x + normal.y * vertex.y + normal.z * vertex.z + offset;
}

int Level::projectionProject(const Vector triangle[3], float width, float height, bool clamp, Vector output[ENGINE_MAX_PROJECTION_VERTICES])
{
    if (!isfinite(width) || !isfinite(height) || width < 1 || height < 1)
        return 0;
    for (int i = 0; i < 3; ++i)
    {
        if (!isfinite(triangle[i].x) || !isfinite(triangle[i].y) || !isfinite(triangle[i].z))
            return 0;
        output[i] = triangle[i];
    }

    Vector scratch[ENGINE_MAX_PROJECTION_VERTICES];
    Vector *input = output;
    Vector *target = scratch;
    const float half_width = width * 0.5f;
    const float half_height = height * 0.5f;
    int count = 3;
    for (int plane = 0; plane < (clamp ? 1 : 5); ++plane)
    {
        Vector normal;
        float offset = 0;
        switch (plane)
        {
        case 0:
            normal = Vector(0, 0, 1);
            offset = -0.1f;
            break;
        case 1:
            normal = Vector(height, 0, half_width);
            break;
        case 2:
            normal = Vector(-height, 0, width - 1 - half_width);
            break;
        case 3:
            normal = Vector(0, -height, half_height);
            break;
        default:
            normal = Vector(0, height, height - 1 - half_height);
            break;
        }
        count = projectionClip(input, count, target, normal, offset);
        if (count < 3)
            return 0;
        Vector *previous = input;
        input = target;
        target = previous;
    }

    for (int i = 0; i < count; ++i)
    {
        const Vector &vertex = input[i];
        const float scale = height / (vertex.z < 0.1f ? 0.1f : vertex.z);
        output[i] = Vector(projectionBound(vertex.x * scale + half_width, width - 1),
                           projectionBound(-vertex.y * scale + half_height, height - 1));
    }
    return count;
}

// Render all active entities
void Level::render(Game *game)
{
    // clear the screen and render the entities
    if (clearAllowed)
    {
        game->draw->fillScreen(game->bg_color);
    }

    Camera *gameCamera = game->getCamera();

    // If using third person perspective, calculate camera from player
    if (gameCamera->perspective == CAMERA_THIRD_PERSON)
    {
        // Find the player entity to calculate 3rd person camera
        Entity *player = nullptr;
        for (int i = 0; i < entity_count; i++)
        {
            if (entities[i] != nullptr && entities[i]->is_player)
            {
                player = entities[i];
                break;
            }
        }

        if (player != nullptr)
        {
            // Calculate 3rd person camera position behind the player
            // Normalize direction vector to ensure consistent behavior
            float dir_length = sqrtf(player->direction.x * player->direction.x + player->direction.y * player->direction.y);
            if (dir_length < 0.001f)
            {
                // Fallback if direction is zero
                dir_length = 1.0f;
                player->direction.x = 1; // Default forward direction
                player->direction.y = 0; // Default forward direction
            }
            float normalized_dir_x = player->direction.x / dir_length;
            float normalized_dir_y = player->direction.y / dir_length;

            gameCamera->position.x = player->position.x - normalized_dir_x * gameCamera->distance;
            gameCamera->position.y = player->position.y - normalized_dir_y * gameCamera->distance;
            gameCamera->direction.x = normalized_dir_x;
            gameCamera->direction.y = normalized_dir_y;
            gameCamera->plane.x = player->plane.x;
            gameCamera->plane.y = player->plane.y;
        }
    }

    if (entity_count == 0)
    {
        return; // Nothing to render
    }

    // Painter's algorithm (back-to-front) for third-person
    const bool use_depth_order = (gameCamera->perspective == CAMERA_THIRD_PERSON && entity_count > 0);
    if (use_depth_order && renderOrder != nullptr)
    {
        for (int i = 0; i < entity_count; i++)
            renderOrder[i] = i;
        // Insertion sort: furthest entities first so closer ones overdraw them
        for (int i = 1; i < entity_count; i++)
        {
            int key_idx = renderOrder[i];
            float key_dist = 0.0f;
            if (entities[key_idx] != nullptr)
            {
                float dx = entities[key_idx]->position.x - gameCamera->position.x;
                float dy = entities[key_idx]->position.y - gameCamera->position.y;
                key_dist = dx * dx + dy * dy;
            }
            int j = i - 1;
            while (j >= 0)
            {
                int cmp_idx = renderOrder[j];
                float cmp_dist = 0.0f;
                if (entities[cmp_idx] != nullptr)
                {
                    float dx = entities[cmp_idx]->position.x - gameCamera->position.x;
                    float dy = entities[cmp_idx]->position.y - gameCamera->position.y;
                    cmp_dist = dx * dx + dy * dy;
                }
                if (cmp_dist < key_dist)
                {
                    renderOrder[j + 1] = renderOrder[j];
                    j--;
                }
                else
                {
                    break;
                }
            }
            renderOrder[j + 1] = key_idx;
        }
    }

    for (int i = 0; i < entity_count; i++)
    {
        Entity *ent = entities[use_depth_order && renderOrder ? renderOrder[i] : i];

        if (ent != nullptr && ent->is_active)
        {
            ent->render(game->draw, game);

            if (!ent->is_visible)
            {
                continue; // Skip rendering if entity is not visible
            }

            // Only draw the 2D sprite if it exists
            if (ent->sprite != nullptr)
            {
                ent->sprite->render(game->draw, ent->position.x - game->pos.x, ent->position.y - game->pos.y);
            }

            // Render 3D sprite if it exists
            if (ent->has3DSprite())
            {
                if (gameCamera->perspective == CAMERA_FIRST_PERSON)
                {
                    // First person: render from player's own perspective
                    if (ent->is_player)
                    {
                        // Use entity's own direction and plane for rendering
                        render3DSprite(ent->sprite_3d, game->draw, ent->position, ent->direction, gameCamera->height);
                    }
                    else
                    {
                        // For non-player entities, render from the player's perspective
                        // We need to find the player entity to get the view parameters
                        Entity *player = nullptr;
                        for (int j = 0; j < entity_count; j++)
                        {
                            if (entities[j] != nullptr && entities[j]->is_player)
                            {
                                player = entities[j];
                                break;
                            }
                        }

                        if (player != nullptr)
                        {
                            render3DSprite(ent->sprite_3d, game->draw, player->position, player->direction, gameCamera->height);
                        }
                    }
                }
                else if (gameCamera->perspective == CAMERA_THIRD_PERSON)
                {
                    // Third person: render ALL entities (including player) from the external camera perspective
                    render3DSprite(ent->sprite_3d, game->draw, gameCamera->position, gameCamera->direction, gameCamera->height);
                }
            }
        }
    }

    if (clearAllowed)
    {
        // send newly drawn pixels to the display
        game->draw->swap();
    }
}

void Level::render3DSprite(const Sprite3D *sprite3d, Draw *draw, const Vector &player_pos, const Vector &player_dir, float view_height, bool clamp)
{
    if (!sprite3d)
        return;

    const Vector screenSize = draw->getDisplaySize();
    const float camA = -player_dir.y;
    const float camB = player_dir.x;
    const float camC = player_dir.x;
    const float camD = player_dir.y;
    const bool doShadow = shadowColor != 0 && lightDirection.y > 0.01f;
    const float slx = doShadow ? lightDirection.x / lightDirection.y : 0.0f;
    const float slz = doShadow ? lightDirection.z / lightDirection.y : 0.0f;

    const uint16_t triangle_count = sprite3d->getTriangleCount();
    for (uint16_t i = 0; i < triangle_count; ++i)
    {
        Triangle3D triangle;
        if (!sprite3d->getTransformedTriangle(i, player_pos, triangle))
            continue;

        const float xs[] = {triangle.x1, triangle.x2, triangle.x3};
        const float ys[] = {triangle.y1, triangle.y2, triangle.y3};
        const float zs[] = {triangle.z1, triangle.z2, triangle.z3};
        Vector vertices[3];
        if (doShadow)
        {
            for (int j = 0; j < 3; ++j)
            {
                const float sx = xs[j] - player_pos.x - ys[j] * slx;
                const float sz = zs[j] - player_pos.y - ys[j] * slz;
                vertices[j] = Vector(sx * camA + sz * camB, -view_height, sx * camC + sz * camD);
            }
            drawProjectedTriangle(draw, vertices, screenSize, shadowColor, false, clamp, 128);
        }
        for (int j = 0; j < 3; ++j)
        {
            const float wx = xs[j] - player_pos.x;
            const float wz = zs[j] - player_pos.y;
            vertices[j] = Vector(wx * camA + wz * camB, ys[j] - view_height, wx * camC + wz * camD);
        }
        drawProjectedTriangle(draw, vertices, screenSize, triangle.color, triangle.wireframe, clamp);
    }
}

void Level::render3DSprite(const char *path, Draw *draw, const Vector &player_pos, const Vector &player_dir, float view_height, bool clamp, bool wireframe)
{
    if (!path)
        return;

    Sprite3D *sprite3d = ENGINE_MEM_NEW Sprite3D();
    if (!sprite3d)
    {
        ENGINE_LOG_INFO("Level::render3DSprite failed to allocate memory for Sprite3D\n");
        return;
    }
    if (!sprite3d->fromPath(path, wireframe))
    {
        ENGINE_LOG_INFO("Level::render3DSprite failed to load Sprite3D from path: %s\n", path);
        ENGINE_MEM_DELETE sprite3d;
        sprite3d = nullptr;
        return;
    }

    render3DSprite(sprite3d, draw, player_pos, player_dir, view_height, clamp);

    ENGINE_MEM_DELETE sprite3d;
    sprite3d = nullptr;
}

void Level::setLightDirection(float x, float y, float z)
{
    float len = sqrtf(x * x + y * y + z * z);
    if (len > 0.0001f)
    {
        lightDirection.x = x / len;
        lightDirection.y = y / len;
        lightDirection.z = z / len;
    }
}

// Start the level
void Level::start()
{
    if (_start)
    {
        _start(*this);
    }
}

// Stop the level
void Level::stop()
{
    if (_stop)
    {
        _stop(*this);
    }
}

// Update all active entities
void Level::update(Game *game)
{
    for (int i = entity_count - 1; i >= 0; i--)
    {
        Entity *ent = getEntity(i);
        if (!ent)
            continue;

        if (!ent->is_active)
        {
            entity_remove(ent);
            continue;
        }

        ent->update(game);

        for (int j = entity_count - 1; j > i; j--)
        {
            Entity *other = getEntity(j);
            if (!other || !other->is_active || !is_collision(ent, other))
                continue;

            ent->collision(other, game);
            if (!ent->is_active)
                break;

            other->collision(ent, game);
        }
    }
}
