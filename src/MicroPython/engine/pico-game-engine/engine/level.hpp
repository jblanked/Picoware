#pragma once
#include "vector.hpp"
#include "camera.hpp"
#include "callback.hpp"

#ifndef ENGINE_MAX_PROJECTION_VERTICES
#define ENGINE_MAX_PROJECTION_VERTICES 8
#endif

// Forward declarations
class Game;
class Sprite3D;
class Entity;

class Level
{
public:
    Level(); // Default constructor
    Level(const char *name,
          const Vector &size,
          Game *game,
          CallbackLevel start = {},
          CallbackLevel stop = {});
    virtual ~Level();

    // Member Functions
    void clear();
    Entity **collision_list(Entity *entity, int &count) const;
    void entity_add(Entity *entity);
    void entity_remove(Entity *entity);
    Entity *getEntity(int index) const { return entities[index]; }
    int getEntityCount() const { return entity_count; }
    const Vector &getLightDirection() const { return lightDirection; }
    uint16_t getShadowColor() const { return shadowColor; }
    bool has_collided(Entity *entity) const;
    bool isClearAllowed() const noexcept { return clearAllowed; }
    bool is_collision(const Entity *a, const Entity *b) const;
    void project3DTo2D(const Vector &vertex, const Vector &player_pos, const Vector &player_dir, float view_height, const Vector &screen_size, Vector &result);
    virtual void render(Game *game);
    void render3DSprite(const Sprite3D *sprite3d, Draw *draw, const Vector &player_pos, const Vector &player_dir, float view_height, bool clamp = false);
    void render3DSprite(const char *path, Draw *draw, const Vector &player_pos, const Vector &player_dir, float view_height, bool clamp = false, bool wireframe = true);
    void setClearAllowed(bool status) { clearAllowed = status; }
    void setLightDirection(float x, float y, float z);
    void setShadowColor(uint16_t color) { shadowColor = color; }
    virtual void start();
    virtual void stop();
    virtual void update(Game *game);

    const char *name;
    Vector size;

private:
    void drawProjectedTriangle(Draw *draw, const Vector vertices[3], const Vector &screen, uint16_t color, bool wireframe, bool clamp, uint8_t alpha = 255);
    float projectionBound(float value, float maximum);
    int projectionClip(const Vector *input, int count, Vector *output, const Vector &normal, float offset);
    float projectionDistance(const Vector &vertex, const Vector &normal, float offset);
    int projectionProject(const Vector triangle[3], float width, float height, bool clamp, Vector output[ENGINE_MAX_PROJECTION_VERTICES]);
    bool clearAllowed;
    Game *gameRef;
    int entity_count;
    Entity **entities;
    Vector lightDirection;
    int *renderOrder;
    uint16_t shadowColor;
    // Callback Functions
    CallbackLevel _start;
    CallbackLevel _stop;
};
