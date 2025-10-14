#pragma once
#include "../gui/vector.hpp"
#include "../engine/camera.hpp"

// Forward declarations
class Game;
class Entity;

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
