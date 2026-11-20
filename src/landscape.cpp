#include "landscape.hpp"
#include "map.hpp"
#include "road.hpp"
#include "pico-game-engine/engine/game.hpp"
#include "pico-game-engine/engine/sprite3d.hpp"
#include <math.h>
#include <stdio.h>

Landscape::Landscape()
    : anchorX(0.0f),
      anchorZ(0.0f),
      boxEast(0.0f),
      boxNorth(0.0f),
      boxSouth(0.0f),
      boxWest(0.0f),
      buildingCount(0),
      buildingSpecCount(0),
      buildingChunkCount(0),
      activeMesh(nullptr),
      activeBoundsActive(false),
      activeBoundsValid(false),
      activeBoundsMin(),
      activeBoundsMax(),
      city(nullptr),
      geometryError(false),
      level(nullptr)
{
}

float Landscape::minFloat(float left, float right) const
{
    return left < right ? left : right;
}

bool Landscape::create(Level *level)
{
    if (!level)
        return false;
    if (city != nullptr)
        return this->level == level;

    this->level = level;
    CallbackEntityDrawGame cityRender;
    cityRender.fn = &Landscape::renderCallback;
    cityRender.ctx = this;
    Entity *entity = ENGINE_MEM_NEW Entity(
        "Downtown", ENTITY_3D_SPRITE, Vector(0.0f, SCENE_ANCHOR_Z),
        Vector(WORLD_SIZE, WORLD_SIZE), nullptr, nullptr, nullptr,
        CallbackEntityGame(), CallbackEntityGame(), CallbackEntityGame(),
        cityRender, CallbackEntityEntityGame(), false,
        SPRITE_3D_NONE, COLOR_BLACK);
    if (!entity)
    {
        ENGINE_LOG_INFO("[Landscape:create] Failed to create city entity\n");
        release();
        return false;
    }

    roadChunk.mesh = ENGINE_MEM_NEW Sprite3D();
    if (!roadChunk.mesh)
    {
        ENGINE_LOG_INFO("[Landscape:create] Failed to create road mesh\n");
        ENGINE_MEM_DELETE entity;
        release();
        return false;
    }
    if (!roadChunk.mesh->reserveTriangles(ENGINE_MAX_TRIANGLES_PER_SPRITE))
    {
        ENGINE_LOG_INFO("[Landscape:create] Failed to reserve road mesh\n");
        ENGINE_MEM_DELETE roadChunk.mesh;
        roadChunk = RenderChunk();
        ENGINE_MEM_DELETE entity;
        release();
        return false;
    }
    roadChunk.mesh->setWireframe(false);
    roadChunk.mesh->setPosition(entity->position);
    activeMesh = roadChunk.mesh;
    entity->is_visible = false;

    const int oldCount = level->getEntityCount();
    level->entity_add(entity);
    if (level->getEntityCount() != oldCount + 1)
    {
        ENGINE_MEM_DELETE roadChunk.mesh;
        roadChunk = RenderChunk();
        activeMesh = nullptr;
        ENGINE_MEM_DELETE entity;
        ENGINE_LOG_INFO("[Landscape:create] Failed to add city mesh to level\n");
        release();
        return false;
    }

    city = entity;
    return true;
}

void Landscape::renderCallback(Entity *entity, Draw *draw, Game *game, void *context)
{
    (void)entity;
    Landscape *landscape = static_cast<Landscape *>(context);
    if (landscape)
        landscape->renderCity(draw, game);
}

void Landscape::renderCity(Draw *draw, Game *game)
{
    if (!level || !draw || !game)
        return;

    Camera *camera = game->getCamera();
    if (!camera)
        return;

    Vector cameraPosition = camera->position;
    Vector cameraDirection = camera->direction;
    if (camera->perspective == CAMERA_FIRST_PERSON)
    {
        Entity *player = nullptr;
        for (int i = 0; i < level->getEntityCount(); ++i)
        {
            Entity *candidate = level->getEntity(i);
            if (candidate && candidate->is_player)
            {
                player = candidate;
                break;
            }
        }
        if (!player)
            return;
        cameraPosition = player->position;
        cameraDirection = player->direction;
    }

    const Vector screen = draw->getDisplaySize();
    const bool drawShadow = level->getShadowColor() != 0 && level->getLightDirection().y > 0.01f;
    if (roadChunk.mesh && roadChunk.bounds_valid && roadChunk.mesh->getTriangleCount() > 0 &&
        boundsMayBeVisible(roadChunk.bounds_min, roadChunk.bounds_max, cameraPosition,
                           cameraDirection, camera->height, screen, drawShadow))
    {
        level->render3DSprite(roadChunk.mesh, draw, cameraPosition, cameraDirection,
                              camera->height, false, drawShadow);
    }

    for (int i = 0; i < buildingChunkCount; ++i)
    {
        const RenderChunk &chunk = buildingChunks[i];
        if (!chunk.mesh || !chunk.bounds_valid || chunk.mesh->getTriangleCount() == 0 ||
            !boundsMayBeVisible(chunk.bounds_min, chunk.bounds_max, cameraPosition,
                                cameraDirection, camera->height, screen, drawShadow))
            continue;

        level->render3DSprite(chunk.mesh, draw, cameraPosition, cameraDirection,
                              camera->height, false, drawShadow);
    }
}

bool Landscape::boundsMayBeVisible(const Vector &minimum, const Vector &maximum,
                                   const Vector &cameraPosition, const Vector &cameraDirection,
                                   float cameraHeight, const Vector &screen, bool drawShadow) const
{
    if (screen.x < 1.0f || screen.y < 1.0f)
        return false;

    float minX = minimum.x;
    float maxX = maximum.x;
    float minY = minimum.y;
    float maxY = maximum.y;
    float minZ = minimum.z;
    float maxZ = maximum.z;

    if (drawShadow)
    {
        const Vector &light = level->getLightDirection();
        const float shadowSlopeX = light.x / light.y;
        const float shadowSlopeZ = light.z / light.y;
        const float shadowX0 = -minimum.y * shadowSlopeX;
        const float shadowX1 = -maximum.y * shadowSlopeX;
        const float shadowZ0 = -minimum.y * shadowSlopeZ;
        const float shadowZ1 = -maximum.y * shadowSlopeZ;
        const float shadowMinX = minimum.x + (shadowX0 < shadowX1 ? shadowX0 : shadowX1);
        const float shadowMaxX = maximum.x + (shadowX0 > shadowX1 ? shadowX0 : shadowX1);
        const float shadowMinZ = minimum.z + (shadowZ0 < shadowZ1 ? shadowZ0 : shadowZ1);
        const float shadowMaxZ = maximum.z + (shadowZ0 > shadowZ1 ? shadowZ0 : shadowZ1);
        if (shadowMinX < minX)
            minX = shadowMinX;
        if (shadowMaxX > maxX)
            maxX = shadowMaxX;
        if (shadowMinZ < minZ)
            minZ = shadowMinZ;
        if (shadowMaxZ > maxZ)
            maxZ = shadowMaxZ;
        if (minY > 0.0f)
            minY = 0.0f;
        if (maxY < 0.0f)
            maxY = 0.0f;
    }

    const float centerX = (minX + maxX) * 0.5f - cameraPosition.x;
    const float centerY = (minY + maxY) * 0.5f - cameraHeight;
    const float centerZ = (minZ + maxZ) * 0.5f - cameraPosition.y;
    const float halfX = (maxX - minX) * 0.5f;
    const float halfY = (maxY - minY) * 0.5f;
    const float halfZ = (maxZ - minZ) * 0.5f;
    const float absDirX = cameraDirection.x < 0.0f ? -cameraDirection.x : cameraDirection.x;
    const float absDirY = cameraDirection.y < 0.0f ? -cameraDirection.y : cameraDirection.y;
    const float cameraX = centerX * -cameraDirection.y + centerZ * cameraDirection.x;
    const float cameraZ = centerX * cameraDirection.x + centerZ * cameraDirection.y;
    const float extentX = absDirY * halfX + absDirX * halfZ;
    const float extentZ = absDirX * halfX + absDirY * halfZ;
    const float height = screen.y;
    const float halfWidth = screen.x * 0.5f;
    const float halfHeight = height * 0.5f;
    const float rightExtent = screen.x - 1.0f - halfWidth;
    const float bottomExtent = height - 1.0f - halfHeight;

    return cameraZ + extentZ >= 0.1f &&
           height * (cameraX + extentX) + halfWidth * (cameraZ + extentZ) >= 0.0f &&
           -height * cameraX + rightExtent * cameraZ + height * extentX + rightExtent * extentZ >= 0.0f &&
           -height * centerY + halfHeight * cameraZ + height * halfY + halfHeight * extentZ >= 0.0f &&
           height * centerY + bottomExtent * cameraZ + height * halfY + bottomExtent * extentZ >= 0.0f;
}

void Landscape::release()
{
    for (int i = 0; i < buildingChunkCount; ++i)
    {
        if (buildingChunks[i].mesh)
            ENGINE_MEM_DELETE buildingChunks[i].mesh;
        buildingChunks[i] = RenderChunk();
    }
    buildingChunkCount = 0;
    if (roadChunk.mesh)
        ENGINE_MEM_DELETE roadChunk.mesh;
    roadChunk = RenderChunk();
    activeMesh = nullptr;
    activeBoundsActive = false;
    activeBoundsValid = false;
    level = nullptr;
    city = nullptr;
    buildingCount = 0;
    buildingSpecCount = 0;
    geometryError = false;
}

void Landscape::buildAround(float centerX, float centerZ)
{
    anchorX = centerX;
    anchorZ = centerZ;
    fillCity(centerX, centerZ);
}

void Landscape::update(const Entity *player)
{
    if (!player || !player->hasChangedPosition())
        return;

    const float offsetX = player->position.x - anchorX;
    const float offsetZ = player->position.y - anchorZ;
    if (offsetX > CHUNK_LAG || offsetX < -CHUNK_LAG ||
        offsetZ > CHUNK_LAG || offsetZ < -CHUNK_LAG)
    {
        anchorX = player->position.x;
        anchorZ = player->position.y;
        fillCity(anchorX, anchorZ);
    }
}

bool Landscape::blocked(float x, float z, bool isCar) const
{
    const float limit = WORLD_HALF - CAR_RADIUS;
    if (fabsf(x) > limit || fabsf(z) > limit)
        return true;

    for (int i = 0; i < buildingCount; ++i)
    {
        const Building &building = buildings[i];
        if (!isCar && building.isHouse)
            continue;
        if (building.contains(x, z, CAR_RADIUS))
            return true;
    }
    return false;
}

bool Landscape::insideBuilding(float x, float z) const
{
    for (int i = 0; i < buildingCount; ++i)
    {
        if (buildings[i].contains(x, z))
            return true;
    }
    return false;
}

bool Landscape::crossesBuilding(float x0, float z0, float x1, float z1) const
{
    for (int i = 0; i < buildingCount; ++i)
    {
        if (buildings[i].intersectsSegment(x0, z0, x1, z1))
            return true;
    }
    return false;
}

const Building *Landscape::getBuilding(int index) const
{
    if (index < 0 || index >= buildingCount)
        return nullptr;
    return &buildings[index];
}

bool Landscape::addSpace(uint16_t triangles)
{
    if (!activeMesh ||
        (uint32_t)activeMesh->getTriangleCount() + triangles > ENGINE_MAX_TRIANGLES_PER_SPRITE)
    {
        geometryError = true;
        return false;
    }
    return true;
}

bool Landscape::addTriangle(float x1, float y1, float z1,
                            float x2, float y2, float z2,
                            float x3, float y3, float z3, uint16_t color)
{
    if (!addSpace(1))
        return false;

    if (!activeMesh->addTriangle(x1, y1, z1, x2, y2, z2,
                                 x3, y3, z3, color, false))
    {
        geometryError = true;
        return false;
    }
    includeActivePoint(x1, y1, z1);
    includeActivePoint(x2, y2, z2);
    includeActivePoint(x3, y3, z3);
    city->is_visible = true;
    return true;
}

void Landscape::includeActivePoint(float x, float y, float z)
{
    if (!activeBoundsActive)
        return;

    const Vector &position = city->position;
    const Vector point(x + position.x, y + position.z, z + position.y);
    if (!activeBoundsValid)
    {
        activeBoundsMin = point;
        activeBoundsMax = point;
        activeBoundsValid = true;
        return;
    }

    if (point.x < activeBoundsMin.x)
        activeBoundsMin.x = point.x;
    if (point.y < activeBoundsMin.y)
        activeBoundsMin.y = point.y;
    if (point.z < activeBoundsMin.z)
        activeBoundsMin.z = point.z;
    if (point.x > activeBoundsMax.x)
        activeBoundsMax.x = point.x;
    if (point.y > activeBoundsMax.y)
        activeBoundsMax.y = point.y;
    if (point.z > activeBoundsMax.z)
        activeBoundsMax.z = point.z;
}

bool Landscape::addQuad(float x1, float y1, float z1, float x2, float y2, float z2,
                        float x3, float y3, float z3, float x4, float y4, float z4,
                        uint16_t color)
{
    const bool firstAdded = addTriangle(x1, y1, z1, x2, y2, z2, x3, y3, z3, color);
    const bool secondAdded = addTriangle(x1, y1, z1, x4, y4, z4, x2, y2, z2, color);
    return firstAdded && secondAdded;
}

bool Landscape::addSquad(float x1, float y1, float z1, float x2, float y2, float z2,
                         float x3, float y3, float z3, float x4, float y4, float z4,
                         uint16_t color, bool bothSides)
{
    bool success = addQuad(x1, y1, z1, x2, y2, z2, x3, y3, z3, x4, y4, z4, color);
    if (bothSides)
    {
        if (!addTriangle(x1, y1, z1, x3, y3, z3, x2, y2, z2, color))
            success = false;
        if (!addTriangle(x1, y1, z1, x2, y2, z2, x4, y4, z4, color))
            success = false;
    }
    return success;
}

bool Landscape::addCube(float x, float y, float z, float width, float height,
                        float depth, uint16_t color)
{
    if (!addSpace(8))
        return false;
    const float halfWidth = width * 0.5f;
    const float halfHeight = height * 0.5f;
    const float halfDepth = depth * 0.5f;
    includeActivePoint(x - halfWidth, y - halfHeight, z - halfDepth);
    includeActivePoint(x + halfWidth, y + halfHeight, z + halfDepth);
    if (!activeMesh->createCube(x, y, z, width, height, depth, color, false))
    {
        geometryError = true;
        return false;
    }
    city->is_visible = true;
    return true;
}

bool Landscape::addGroundRect(float x, float z, float width, float depth,
                              float height, uint16_t color, float segmentSize)
{
    if (width <= 0.0f || depth <= 0.0f || segmentSize <= 0.0f)
        return false;

    const float sceneZ = z - SCENE_ANCHOR_Z;
    int widthSteps = 1;
    int depthSteps = 1;
    if (width >= depth)
    {
        widthSteps = (int)((width + segmentSize - 0.001f) / segmentSize);
        if (widthSteps < 1)
            widthSteps = 1;
    }
    else
    {
        depthSteps = (int)((depth + segmentSize - 0.001f) / segmentSize);
        if (depthSteps < 1)
            depthSteps = 1;
    }

    const float cellWidth = width / widthSteps;
    const float cellDepth = depth / depthSteps;
    const float startX = x - width * 0.5f;
    const float startZ = sceneZ - depth * 0.5f;
    bool success = true;
    for (int widthIndex = 0; widthIndex < widthSteps; ++widthIndex)
    {
        const float cellX = startX + cellWidth * (widthIndex + 0.5f);
        for (int depthIndex = 0; depthIndex < depthSteps; ++depthIndex)
        {
            const float cellZ = startZ + cellDepth * (depthIndex + 0.5f);
            const float halfWidth = cellWidth * 0.5f;
            const float halfDepth = cellDepth * 0.5f;
            const bool added = addQuad(
                cellX - halfWidth, height, cellZ - halfDepth,
                cellX + halfWidth, height, cellZ + halfDepth,
                cellX + halfWidth, height, cellZ - halfDepth,
                cellX - halfWidth, height, cellZ + halfDepth, color);
            if (!added)
                success = false;
        }
    }
    return success;
}

void Landscape::addWindow(float x, float y, float z, float halfWidth, float halfHeight)
{
    const float left = x - halfWidth;
    const float right = x + halfWidth;
    const float bottom = y - halfHeight;
    const float top = y + halfHeight;
    addTriangle(left, bottom, z, right, bottom, z, right, top, z, COLOR_WINDOW);
    addTriangle(left, bottom, z, right, top, z, left, top, z, COLOR_WINDOW);
    addTriangle(right, bottom, z, left, bottom, z, left, top, z, COLOR_WINDOW);
    addTriangle(right, bottom, z, left, top, z, right, top, z, COLOR_WINDOW);
}

void Landscape::addCarToMesh(float x, float sceneZ, uint16_t color)
{
    addCube(x, 0.36f, sceneZ, 1.05f, 0.34f, 1.85f, color);
    addCube(x, 0.62f, sceneZ + 0.10f, 0.68f, 0.24f, 0.72f, COLOR_GLASS);
    addCube(x, 0.20f, sceneZ - 0.78f, 0.85f, 0.10f, 0.12f, COLOR_LINE);
}

void Landscape::addTree(float x, float z)
{
    const float sceneZ = z - SCENE_ANCHOR_Z;
    addCube(x, 0.50f, sceneZ, 0.24f, 1.00f, 0.24f, COLOR_TRUNK);
    addCube(x, 1.15f, sceneZ, 0.85f, 0.60f, 0.85f, COLOR_LEAF);
    addCube(x, 1.55f, sceneZ, 0.55f, 0.35f, 0.55f, COLOR_LEAF);
}

void Landscape::buildGarage(float x, float z, float width, float depth,
                            float height, uint16_t wallColor)
{
    const float sceneZ = z - SCENE_ANCHOR_Z;
    const float halfWidth = width * 0.5f;
    const float halfDepth = depth * 0.5f;
    const float floorY = 0.05f;
    const float ceilingY = height - 0.15f;
    const float z0 = sceneZ - halfDepth + 0.1f;
    const float z1 = sceneZ + halfDepth - 0.1f;
    const float doorHalf = 1.2f;

    addSquad(x - halfWidth, floorY, z0,
             x + halfWidth, floorY, z1,
             x + halfWidth, floorY, z0,
             x - halfWidth, floorY, z1, COLOR_FLOOR, true);
    addSquad(x - halfWidth, ceilingY, z0,
             x + halfWidth, ceilingY, z1,
             x + halfWidth, ceilingY, z0,
             x - halfWidth, ceilingY, z1, COLOR_CEILING, true);
    addSquad(x - halfWidth, floorY, z0,
             x + halfWidth, ceilingY, z0,
             x + halfWidth, floorY, z0,
             x - halfWidth, ceilingY, z0, wallColor, true);

    if (doorHalf < halfWidth)
    {
        addSquad(x - halfWidth, floorY, z1,
                 x - doorHalf, ceilingY, z1,
                 x - doorHalf, floorY, z1,
                 x - halfWidth, ceilingY, z1, wallColor, true);
        addSquad(x + doorHalf, floorY, z1,
                 x + halfWidth, ceilingY, z1,
                 x + halfWidth, floorY, z1,
                 x + doorHalf, ceilingY, z1, wallColor, true);
    }

    addSquad(x - halfWidth, floorY, z0,
             x - halfWidth, ceilingY, z1,
             x - halfWidth, floorY, z1,
             x - halfWidth, ceilingY, z0, wallColor, true);
    addSquad(x + halfWidth, floorY, z0,
             x + halfWidth, ceilingY, z1,
             x + halfWidth, floorY, z1,
             x + halfWidth, ceilingY, z0, wallColor, true);
    addCarToMesh(x + halfWidth * 0.45f, sceneZ, COLOR_PLAYER);
}

void Landscape::buildHouse(float x, float z, float width, float depth,
                           float height, uint16_t wallColor, uint16_t roofColor)
{
    const float sceneZ = z - SCENE_ANCHOR_Z;
    addCube(x, height - 0.05f, sceneZ, width + 0.10f, 0.10f,
            depth + 0.10f, roofColor);
    buildGarage(x, z, width, depth, height, wallColor);
}

void Landscape::addBuilding(const BuildingSpec &spec)
{
    if (buildingCount >= MAX_BUILDINGS || buildingChunkCount >= MAX_BUILDINGS)
    {
        geometryError = true;
        return;
    }

    Sprite3D *mesh = ENGINE_MEM_NEW Sprite3D();
    if (!mesh)
    {
        geometryError = true;
        return;
    }
    const uint16_t meshCapacity = ENGINE_MAX_TRIANGLES_PER_SPRITE < 64
                                      ? ENGINE_MAX_TRIANGLES_PER_SPRITE
                                      : 64;
    if (!mesh->reserveTriangles(meshCapacity))
    {
        ENGINE_MEM_DELETE mesh;
        geometryError = true;
        return;
    }
    mesh->setWireframe(false);
    mesh->setPosition(city->position);

    Sprite3D *previousMesh = activeMesh;
    activeMesh = mesh;
    activeBoundsActive = true;
    activeBoundsValid = false;
    const float sceneZ = spec.z - SCENE_ANCHOR_Z;
    const bool isHouse = spec.type == 1;
    const bool isTower = spec.type == 2;
    if (isHouse)
    {
        buildHouse(spec.x, spec.z, spec.width, spec.depth, spec.height,
                   spec.wallColor, spec.roofColor);
    }
    else
    {
        addCube(spec.x, spec.height * 0.5f, sceneZ,
                spec.width, spec.height, spec.depth, spec.wallColor);
        addCube(spec.x, spec.height + 0.10f, sceneZ,
                spec.width + 0.12f, 0.20f, spec.depth + 0.12f, spec.roofColor);
        const float windowHeight = minFloat(0.14f, spec.height * 0.07f);
        const float windowY = minFloat(spec.height - 0.35f, 1.2f);
        const float front = sceneZ + spec.depth * 0.5f + 0.02f;
        const float halfWidth = spec.width * 0.275f;
        addWindow(spec.x, windowY, front, halfWidth, windowHeight);
        if (spec.height > 4.5f)
            addWindow(spec.x, spec.height * 0.58f, front, halfWidth, windowHeight);
        if (isTower)
            addCube(spec.x, spec.height + 0.5f, sceneZ, 0.10f, 1.0f, 0.10f, COLOR_ROOF);
    }

    activeBoundsActive = false;
    activeMesh = previousMesh;
    if (activeBoundsValid && mesh->getTriangleCount() > 0)
    {
        RenderChunk &chunk = buildingChunks[buildingChunkCount++];
        chunk.mesh = mesh;
        chunk.bounds_min = activeBoundsMin;
        chunk.bounds_max = activeBoundsMax;
        chunk.bounds_valid = true;
    }
    else
        ENGINE_MEM_DELETE mesh;

    if (buildingCount < MAX_BUILDINGS)
        buildings[buildingCount++] = Building(spec.x, spec.z, spec.width, spec.depth, isHouse);
    else
        geometryError = true;
}

void Landscape::fillCity(float centerX, float centerZ)
{
    if (!level)
        return;

    geometryError = false;
    buildingCount = 0;
    buildingSpecCount = 0;
    for (int i = 0; i < buildingChunkCount; ++i)
    {
        if (buildingChunks[i].mesh)
            ENGINE_MEM_DELETE buildingChunks[i].mesh;
        buildingChunks[i] = RenderChunk();
    }
    buildingChunkCount = 0;
    if (!roadChunk.mesh)
        return;
    roadChunk.mesh->clear();
    roadChunk.bounds_valid = false;
    activeMesh = roadChunk.mesh;
    activeBoundsActive = true;
    activeBoundsValid = false;
    city->is_visible = false;

    const float half = CITY_FIELD_OF_VIEW + CHUNK_LAG;
    boxWest = centerX - half;
    boxEast = centerX + half;
    boxNorth = centerZ - half;
    boxSouth = centerZ + half;

    addStreets();
    addBlocks(centerX, centerZ);
    activeBoundsActive = false;
    if (activeBoundsValid)
    {
        roadChunk.bounds_min = activeBoundsMin;
        roadChunk.bounds_max = activeBoundsMax;
        roadChunk.bounds_valid = true;
    }
    for (int i = 1; i < buildingSpecCount; ++i)
    {
        const BuildingSpec key = buildingSpecs[i];
        int j = i - 1;
        while (j >= 0 && buildingSpecs[j].distance < key.distance)
        {
            buildingSpecs[j + 1] = buildingSpecs[j];
            --j;
        }
        buildingSpecs[j + 1] = key;
    }

    for (int i = 0; i < buildingSpecCount; ++i)
        addBuilding(buildingSpecs[i]);

    city->is_visible = roadChunk.mesh->getTriangleCount() > 0 || buildingChunkCount > 0;
    if (geometryError)
        ENGINE_LOG_INFO("[Landscape] City geometry exceeded its fixed mesh capacity\n");
}

void Landscape::addStreets()
{
    float west = boxWest;
    float east = boxEast;
    float north = boxNorth;
    float south = boxSouth;
    if (west < -WORLD_HALF)
        west = -WORLD_HALF;
    if (east > WORLD_HALF)
        east = WORLD_HALF;
    if (north < -WORLD_HALF)
        north = -WORLD_HALF;
    if (south > WORLD_HALF)
        south = WORLD_HALF;
    if (west >= east || north >= south)
        return;

    int first = (int)ceilf((west - 4.0f) / ROAD_SPACING);
    int last = (int)floorf((east + 4.0f) / ROAD_SPACING);
    if (first < -5)
        first = -5;
    if (last > 5)
        last = 5;
    for (int index = first; index <= last; ++index)
        addRoadLine(index * ROAD_SPACING, north, south, true);

    first = (int)ceilf((north - 4.0f) / ROAD_SPACING);
    last = (int)floorf((south + 4.0f) / ROAD_SPACING);
    if (first < -5)
        first = -5;
    if (last > 5)
        last = 5;
    for (int index = first; index <= last; ++index)
        addRoadLine(index * ROAD_SPACING, west, east, false);
}

void Landscape::addRoadLine(float line, float begin, float end, bool vertical)
{
    if (!road.addLine(*this, line, begin, end, vertical))
        geometryError = true;
}

void Landscape::addBlocks(float centerX, float centerZ)
{
    const int firstCol = (int)floorf((boxWest - BLOCK_REACH) / ROAD_SPACING);
    const int lastCol = (int)floorf((boxEast + BLOCK_REACH) / ROAD_SPACING);
    const int firstRow = (int)floorf((boxNorth - BLOCK_REACH) / ROAD_SPACING);
    const int lastRow = (int)floorf((boxSouth + BLOCK_REACH) / ROAD_SPACING);

    for (int col = firstCol; col <= lastCol; ++col)
    {
        if (col < -5 || col >= 5)
            continue;
        const float blockX = col * ROAD_SPACING + BLOCK_CENTER;
        for (int row = firstRow; row <= lastRow; ++row)
        {
            if (row < -5 || row >= 5)
                continue;
            const float blockZ = row * ROAD_SPACING + BLOCK_CENTER;
            addBlock(col, row, blockX, blockZ, centerX, centerZ);
        }
    }
}

void Landscape::addBlock(int col, int row, float blockX, float blockZ,
                         float centerX, float centerZ)
{
    if (map.cellHash(col, row, 1) % 7 == 0)
    {
        addTree(blockX, blockZ);
        return;
    }

    for (int index = 0; index < 8; ++index)
    {
        const uint32_t detail = map.cellHash(col, row, index + 2);
        const float x = blockX + blockSlots[index][0];
        const float z = blockZ + blockSlots[index][1];
        if (x < boxWest - BUILDING_REACH || x > boxEast + BUILDING_REACH ||
            z < boxNorth - BUILDING_REACH || z > boxSouth + BUILDING_REACH)
            continue;
        if (detail % 5 == 0)
        {
            addTree(x, z);
            continue;
        }

        float width = 9.0f + (detail >> 4) % 5;
        float depth = 9.0f + (detail >> 7) % 5;
        float height = 3.2f + ((detail >> 10) % 5) * 0.9f;
        const int type = (detail >> 12) % 3;
        if (type == 1)
        {
            width = 7.0f;
            depth = 7.0f;
            height = 2.5f;
        }
        else if (type == 2)
        {
            height = 10.0f + (detail >> 10) % 6;
        }

        if (buildingSpecCount >= MAX_BUILDING_SPECS)
        {
            geometryError = true;
            continue;
        }
        BuildingSpec &spec = buildingSpecs[buildingSpecCount++];
        const float dx = x - centerX;
        const float dz = z - centerZ;
        spec.distance = dx * dx + dz * dz;
        spec.x = x;
        spec.z = z;
        spec.width = width;
        spec.depth = depth;
        spec.height = height;
        spec.wallColor = buildingColors[detail % 8][0];
        spec.roofColor = buildingColors[detail % 8][1];
        spec.type = type;
    }
}