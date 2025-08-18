#pragma once
#include "../gui/vector.hpp"

// Forward declarations
class Game;
class Entity;

// Camera perspective types for 3D rendering
enum CameraPerspective
{
    CAMERA_FIRST_PERSON, // Default - render from player's own position/view
    CAMERA_THIRD_PERSON  // Render from external camera position
};

// Camera parameters for 3D rendering
struct CameraParams
{
    Vector position;  // Camera position
    Vector direction; // Camera direction
    Vector plane;     // Camera plane
    float height;     // Camera height

    CameraParams() : position(0, 0), direction(1, 0), plane(0, 0.66f), height(1.6f) {}
    CameraParams(Vector pos, Vector dir, Vector pl, float h)
        : position(pos), direction(dir), plane(pl), height(h) {}
};

class Level
{
public:
    // Constructors and Destructor
    Level(); // Default constructor
    Level(const char *name,
          const Vector &size,
          Game *game,
          void (*start)(Level &) = nullptr,
          void (*stop)(Level &) = nullptr);
    ~Level();

    // Member Functions
    void clear();
    Entity **collision_list(Entity *entity, int &count) const;
    void entity_add(Entity *entity);
    void entity_remove(Entity *entity);
    bool has_collided(Entity *entity) const;
    bool isClearAllowed() const noexcept { return clearAllowed; }
    bool is_collision(const Entity *a, const Entity *b) const;
    void render(Game *game, CameraPerspective perspective = CAMERA_FIRST_PERSON, const CameraParams *camera_params = nullptr);
    void setClearAllowed(bool status) { clearAllowed = status; }
    void start();
    void stop();
    void update(Game *game);

    // Public accessors for entities (needed for Game::renderSprites)
    int getEntityCount() const { return entity_count; }
    Entity *getEntity(int index) const { return entities[index]; }

    const char *name;
    Vector size;

private:
    bool clearAllowed;
    //
    Game *gameRef;
    int entity_count;
    Entity **entities;
    // Callback Functions
    void (*_start)(Level &);
    void (*_stop)(Level &);
};
