#pragma once
#include "triangle3d.hpp"
#include "vector.hpp"
#include "../engine_config.hpp"
#include "math.h"

#ifdef ENGINE_USE_PSRAM
#include "triangle_psram.hpp"
#endif

#include ENGINE_MEM_INCLUDE

#ifndef ENGINE_MAX_TRIANGLES_PER_SPRITE
#define ENGINE_MAX_TRIANGLES_PER_SPRITE 64
#endif

#ifndef ENGINE_SPRITE3D_PSRAM_DEFAULT
#define ENGINE_SPRITE3D_PSRAM_DEFAULT true
#endif

typedef enum
{
    SPRITE_HUMANOID = 0,
    SPRITE_TREE = 1,
    SPRITE_HOUSE = 2,
    SPRITE_PILLAR = 3,
    SPRITE_CUSTOM = 4
} SpriteType;

class Sprite3D
{
private:
    bool active;
    Vector position;
    bool psramAllowed;
    float rotation_y;
    float scale_factor;
    bool depthSortEnabled;
    uint16_t triangle_capacity;
    uint16_t triangle_count;
    Triangle3D *triangles;
#ifdef ENGINE_USE_PSRAM
    TrianglePSRAM psramTriangles;
#endif
    SpriteType type;

    bool loadTriangle(uint16_t index, Triangle3D &out) const;
    bool reserveExtra(uint16_t extra);
    bool storeTriangle(uint16_t index, const Triangle3D &triangle);
    void transformVertex(float x, float y, float z, float cos_a, float sin_a,
                         float &out_x, float &out_y, float &out_z) const;

public:
    Sprite3D(bool psramAllowed = ENGINE_SPRITE3D_PSRAM_DEFAULT);
    ~Sprite3D();

    Sprite3D(const Sprite3D &) = delete;
    Sprite3D &operator=(const Sprite3D &) = delete;

    bool addTriangle(const Triangle3D &triangle);
    bool addTriangle(float x1, float y1, float z1, float x2, float y2, float z2, float x3, float y3, float z3, uint16_t color = 0x0000, bool wireframe = false);
    bool bakeTransform();
    void clear();
    void clearTriangles();
    bool createHumanoid(float height = 1.8f, uint16_t color = 0x0000, bool wireframe = false);
    bool createTree(float height = 2.0f, uint16_t color = 0x0000, bool wireframe = false);
    bool createHouse(float width = 2.0f, float height = 2.5f, uint16_t color = 0x0000, bool wireframe = false);
    bool createPillar(float height = 3.0f, float radius = 0.3f, uint16_t color = 0x0000, bool wireframe = false);
    bool createWall(float x, float y, float z, float width = 4.0f, float height = 1.5f, float depth = 0.2f, uint16_t color = 0x0000, bool wireframe = false);
    bool createCube(float x, float y, float z, float width, float height, float depth, uint16_t color = 0x0000, bool wireframe = false);
    bool createCylinder(float x, float y, float z, float radius, float height, uint8_t segments, uint16_t color = 0x0000, bool wireframe = false);
    bool createSphere(float x, float y, float z, float radius, uint8_t segments, uint16_t color = 0x0000, bool wireframe = false);
    bool createTriangularPrism(float x, float y, float z, float width, float height, float depth, uint16_t color = 0x0000, bool wireframe = false);
    bool fromPath(const char *path, bool wireframe = false);
    Vector getPosition() const { return position; }
    bool getTriangle(uint16_t index, Triangle3D &out) const;
    bool getTriangle(uint16_t index, float &x1, float &y1, float &z1,
                     float &x2, float &y2, float &z2,
                     float &x3, float &y3, float &z3, uint16_t &color, bool &wireframe) const;
    bool getWorldTriangle(uint16_t index, Triangle3D &out) const;
    float getRotation() const { return rotation_y; }
    float getScale() const { return scale_factor; }
    bool getTransformedTriangle(uint16_t index, const Vector &camera_pos, Triangle3D &out, float camera_height = 0.5f) const;
    uint16_t getTriangleCount() const { return triangle_count; }
    SpriteType getType() const { return type; }
    bool initializeAsHouse(Vector pos, float width, float height, float rot, uint16_t color = 0x0000, bool wireframe = false);
    bool initializeAsHumanoid(Vector pos, float height, float rot, uint16_t color = 0x0000, bool wireframe = false);
    bool initializeAsPillar(Vector pos, float height, float radius, uint16_t color = 0x0000, bool wireframe = false);
    bool initializeAsTree(Vector pos, float height, uint16_t color = 0x0000, bool wireframe = false);
    bool isActive() const { return active; }
    bool reserveTriangles(uint16_t count);
    void setActive(bool state) { active = state; }
    void setPosition(Vector pos) { position = pos; }
    void setRotation(float rot) { rotation_y = rot; }
    void setScale(float scale) { scale_factor = scale; }
    void setDepthSortEnabled(bool enabled) { depthSortEnabled = enabled; }
    void setWireframe(bool wireframe);
    bool toPath(const char *path) const;
    bool isDepthSortEnabled() const { return depthSortEnabled; }
    bool updateTriangle(uint16_t index, const Triangle3D &triangle);
    bool updateTriangle(uint16_t index, float x1, float y1, float z1,
                        float x2, float y2, float z2,
                        float x3, float y3, float z3, uint16_t color = 0x0000, bool wireframe = false);
};