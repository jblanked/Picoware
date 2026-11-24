#pragma once
#include "building.hpp"
#include "general.hpp"
#include "map.hpp"
#include "pico-game-engine/engine/entity.hpp"
#include "pico-game-engine/engine/level.hpp"
#include "road.hpp"

class Landscape
{
public:
    static constexpr float BLOCK_CENTER = 42.0f;
    static constexpr float BLOCK_REACH = 40.0f;
    static constexpr float BUILDING_REACH = 8.0f;
    static constexpr float CAR_RADIUS = 0.72f;
    static constexpr float CHUNK_LAG = 12.0f;
    static constexpr float CITY_FIELD_OF_VIEW = 50.0f;
    static constexpr float MARK_HEIGHT = 0.10f;
    static constexpr float MARK_LENGTH = 2.6f;
    static constexpr float MARK_OFFSET = 7.0f;
    static constexpr float MARK_SPACING = 14.0f;
    static constexpr float MARK_WIDTH = 0.12f;
    static constexpr float ROAD_HEIGHT = 0.06f;
    static constexpr float ROAD_SEGMENT = 4.2f;
    static constexpr float ROAD_SPACING = 84.0f;
    static constexpr float ROAD_WIDTH = 5.5f;
    static constexpr float SCENE_ANCHOR_Z = -1000.0f;
    static constexpr float SIDEWALK_HEIGHT = 0.03f;
    static constexpr float SIDEWALK_OFFSET = 3.35f;
    static constexpr float SIDEWALK_SEGMENT = 6.0f;
    static constexpr float SIDEWALK_WIDTH = 1.2f;
    static constexpr float WORLD_HALF = 420.0f;
    static constexpr float WORLD_SIZE = 840.0f;

    enum Color : uint16_t
    {
        COLOR_BLACK = 0x0000,
        COLOR_CEILING = 0x734E,
        COLOR_DOOR = 0x1080,
        COLOR_FLOOR = 0x9C8A,
        COLOR_GLASS = 0x5D9B,
        COLOR_GROUND = 0xBDF7,
        COLOR_HORIZON = 0x8C71,
        COLOR_LEAF = 0x07E0,
        COLOR_LINE = 0xFFE0,
        COLOR_PLAYER = 0x07FF,
        COLOR_ROAD = 0x39C7,
        COLOR_ROOF = 0x632C,
        COLOR_SIDEWALK = 0xD69A,
        COLOR_SKIN = 0xFD20,
        COLOR_SKY = 0x5D9F,
        COLOR_TRUNK = 0x6B4D,
        COLOR_WINDOW = 0x2A8A
    };

    enum
    {
        MAX_BUILDING_SPECS = 128,
        MAX_BUILDINGS = 128,
        MAX_BUILDING_CHUNKS = 32,
        MAX_BUILDING_TRIANGLES = 64,
        MAX_ROAD_TRIANGLES = 1024
    };

    Landscape();

    bool addGroundRect(float x, float z, float width, float depth, float height,
                       uint16_t color, float segmentSize);
    bool blocked(float x, float z, bool isCar) const;
    void buildAround(float centerX, float centerZ);
    bool create(Level *level);
    bool crossesBuilding(float x0, float z0, float x1, float z1) const;
    const Building *getBuilding(int index) const;
    int getBuildingCount() const { return buildingCount; }
    bool hasGeometryError() const { return geometryError; }
    bool insideBuilding(float x, float z) const;
    void release();
    void update(const Entity *player);

private:
    struct BuildingSpec
    {
        int col;
        int row;
        int slot;
        int chunk_index;
        float depth;
        float distance;
        float height;
        uint16_t roofColor;
        int type;
        uint16_t wallColor;
        float width;
        float x;
        float z;
    };

    struct RenderChunk
    {
        Sprite3D *mesh = nullptr;
        int col = 0;
        int row = 0;
        int slot = 0;
        Vector bounds_min;
        Vector bounds_max;
        bool cache_valid = false;
        bool bounds_valid = false;
        bool active = false;
    };

    void addBlock(int col, int row, float blockX, float blockZ,
                  float centerX, float centerZ);
    void addBlocks(float centerX, float centerZ);
    void addBuilding(const BuildingSpec &spec, int chunkIndex, bool rebuildMesh);
    static void renderCallback(Entity *entity, Draw *draw, Game *game, void *context);
    void renderCity(Draw *draw, Game *game);
    bool boundsMayBeVisible(const Vector &minimum, const Vector &maximum,
                            const Vector &cameraPosition, const Vector &cameraDirection,
                            float cameraHeight, const Vector &screen, bool drawShadow) const;
    void addCarToMesh(float x, float sceneZ, uint16_t color);
    bool addCube(float x, float y, float z, float width, float height, float depth,
                 uint16_t color);
    bool addQuad(float x1, float y1, float z1, float x2, float y2, float z2,
                 float x3, float y3, float z3, float x4, float y4, float z4,
                 uint16_t color);
    bool addSquad(float x1, float y1, float z1, float x2, float y2, float z2,
                  float x3, float y3, float z3, float x4, float y4, float z4,
                  uint16_t color, bool bothSides);
    void addRoadLine(float line, float begin, float end, bool vertical);
    bool addSpace(uint16_t triangles);
    void addStreets();
    bool addTriangle(float x1, float y1, float z1, float x2, float y2, float z2,
                     float x3, float y3, float z3, uint16_t color);
    void includeActivePoint(float x, float y, float z);
    void addTree(float x, float z);
    void addWindow(float x, float y, float z, float halfWidth, float halfHeight);
    void buildGarage(float x, float z, float width, float depth, float height,
                     uint16_t wallColor);
    void buildHouse(float x, float z, float width, float depth, float height,
                    uint16_t wallColor, uint16_t roofColor);
    void fillCity(float centerX, float centerZ);
    float minFloat(float left, float right) const;

    float anchorX;
    float anchorZ;
    const float blockSlots[8][2] = {
        {-30.0f, -20.0f},
        {-30.0f, 20.0f},
        {30.0f, -20.0f},
        {30.0f, 20.0f},
        {-20.0f, -30.0f},
        {20.0f, -30.0f},
        {-20.0f, 30.0f},
        {20.0f, 30.0f}};
    float boxEast;
    float boxNorth;
    float boxSouth;
    float boxWest;
    const uint16_t buildingColors[8][2] = {
        {0xB5B6, 0x7BEF},
        {0xD69A, 0xFBE0},
        {0x6B4D, 0xC618},
        {0xA145, 0xFD20},
        {0x9CB2, 0x5D9B},
        {0xFBE0, 0xFD20},
        {0xC618, 0x9CB2},
        {0xA145, 0xFFE0}};
    int buildingCount;
    Building buildings[MAX_BUILDINGS];
    int buildingSpecCount;
    BuildingSpec buildingSpecs[MAX_BUILDING_SPECS];
    RenderChunk roadChunk;
    RenderChunk buildingChunks[MAX_BUILDING_CHUNKS];
    int activeBuildingChunkIndices[MAX_BUILDING_CHUNKS];
    int buildingChunkCount;
    Sprite3D *activeMesh;
    uint16_t activeTriangleCapacity;
    uint16_t buildingTriangleCapacity;
    uint16_t roadTriangleCapacity;
    bool activeBoundsActive;
    bool activeBoundsValid;
    Vector activeBoundsMin;
    Vector activeBoundsMax;
    Entity *city;
    bool geometryError;
    Level *level;
    Map map;
    Road road;
};