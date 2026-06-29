#include "sprite3d.hpp"

#ifdef ENGINE_STORAGE_INCLUDE
#include ENGINE_STORAGE_INCLUDE
#endif

#ifdef ENGINE_LOG_INCLUDE
#include ENGINE_LOG_INCLUDE
#endif

// Shade an RGB565 color by a factor (< 1.0 darkens, > 1.0 lightens)
static uint16_t shadeColor565(uint16_t color, float factor)
{
    uint8_t r = (uint8_t)(((color >> 11) & 0x1F) * factor);
    uint8_t g = (uint8_t)(((color >> 5) & 0x3F) * factor);
    uint8_t b = (uint8_t)((color & 0x1F) * factor);
    if (r > 0x1F)
        r = 0x1F;
    if (g > 0x3F)
        g = 0x3F;
    if (b > 0x1F)
        b = 0x1F;
    return ((uint16_t)r << 11) | ((uint16_t)g << 5) | b;
}

Sprite3D::Sprite3D() : triangle_count(0), position(Vector(0, 0)), rotation_y(0),
                       scale_factor(1.0f), type(SPRITE_CUSTOM), active(false)
{
    memset(triangles, 0, sizeof(triangles));
}

Sprite3D::~Sprite3D()
{
    clearTriangles();
}

bool Sprite3D::addTriangle(const Triangle3D &triangle)
{
    if (triangle_count < ENGINE_MAX_TRIANGLES_PER_SPRITE)
    {
        triangles[triangle_count] = ENGINE_MEM_NEW Triangle3D(triangle);
        if (triangles[triangle_count] != nullptr)
        {
            triangle_count++;
            return true;
        }
    }
    return false;
}

bool Sprite3D::addTriangle(float x1, float y1, float z1,
                           float x2, float y2, float z2,
                           float x3, float y3, float z3, uint16_t color, bool wireframe)
{
    if (triangle_count < ENGINE_MAX_TRIANGLES_PER_SPRITE)
    {
        triangles[triangle_count] = ENGINE_MEM_NEW Triangle3D(x1, y1, z1, x2, y2, z2, x3, y3, z3, color, wireframe);
        if (triangles[triangle_count] != nullptr)
        {
            triangle_count++;
            return true;
        }
    }
    return false;
}

void Sprite3D::clearTriangles()
{
    for (uint16_t i = 0; i < triangle_count; i++)
    {
        ENGINE_MEM_DELETE triangles[i];
        triangles[i] = nullptr;
    }
    triangle_count = 0;
}

bool Sprite3D::createCube(float x, float y, float z, float width, float height, float depth, uint16_t color, bool wireframe)
{
    float hw = width * 0.5f;
    float hh = height * 0.5f;
    float hd = depth * 0.5f;

    // Render 4 most important faces (skip top and bottom to save triangles)
    // This gives 8 triangles per cube instead of 12

    // Front face (2 triangles)
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z + hd,
            x + hw, y - hh, z + hd,
            x + hw, y + hh, z + hd, color, wireframe)))
        return false;

    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z + hd,
            x + hw, y + hh, z + hd,
            x - hw, y + hh, z + hd, color, wireframe)))
        return false;

    // Back face (2 triangles)
    if (!addTriangle(Triangle3D(
            x + hw, y - hh, z - hd,
            x - hw, y - hh, z - hd,
            x - hw, y + hh, z - hd, color, wireframe)))
        return false;

    if (!addTriangle(Triangle3D(
            x + hw, y - hh, z - hd,
            x - hw, y + hh, z - hd,
            x + hw, y + hh, z - hd, color, wireframe)))
        return false;

    // Right face (2 triangles)
    if (!addTriangle(Triangle3D(
            x + hw, y - hh, z + hd,
            x + hw, y - hh, z - hd,
            x + hw, y + hh, z - hd, color, wireframe)))
        return false;

    if (!addTriangle(Triangle3D(
            x + hw, y - hh, z + hd,
            x + hw, y + hh, z - hd,
            x + hw, y + hh, z + hd, color, wireframe)))
        return false;

    // Left face (2 triangles)
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z - hd,
            x - hw, y - hh, z + hd,
            x - hw, y + hh, z + hd, color, wireframe)))
        return false;

    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z - hd,
            x - hw, y + hh, z + hd,
            x - hw, y + hh, z - hd, color, wireframe)))
        return false;

    return true;
}

bool Sprite3D::createCylinder(float x, float y, float z, float radius, float height, uint8_t segments, uint16_t color, bool wireframe)
{
    float hh = height * 0.5f;

    // Limit segments to prevent too many triangles
    if (segments > 6)
        segments = 6;

    // Only side faces - no caps to save triangles
    for (uint8_t i = 0; i < segments; i++)
    {
        float angle1 = (float)i * 2.0f * M_PI / segments;
        float angle2 = (float)(i + 1) * 2.0f * M_PI / segments;

        float x1 = x + radius * cosf(angle1);
        float z1 = z + radius * sinf(angle1);
        float x2 = x + radius * cosf(angle2);
        float z2 = z + radius * sinf(angle2);

        // Side face triangles only
        if (!addTriangle(Triangle3D(
                x1, y - hh, z1,
                x2, y - hh, z2,
                x2, y + hh, z2, color, wireframe)))
            return false;

        if (!addTriangle(Triangle3D(
                x1, y - hh, z1,
                x2, y + hh, z2,
                x1, y + hh, z1, color, wireframe)))
            return false;
    }

    return true;
}

bool Sprite3D::createHouse(float width, float height, uint16_t color, bool wireframe)
{
    clearTriangles();
    type = SPRITE_HOUSE;

    float wall_height = height * 0.7f;
    float roof_height = height * 0.3f;
    float house_width = width * 1.3f;
    float house_depth = width * 1.1f;

    // House base (cube)
    if (!createCube(0, wall_height / 2, 0, house_width, wall_height, house_depth, color, wireframe))
        return false;

    // Roof (triangular prism)
    return createTriangularPrism(0, wall_height + roof_height / 2, 0, house_width, roof_height, house_depth, shadeColor565(color, 0.6f), wireframe);
}

bool Sprite3D::createHumanoid(float height, uint16_t color, bool wireframe)
{
    clearTriangles();
    type = SPRITE_HUMANOID;

    float head_radius = height * 0.12f;
    float torso_width = height * 0.20f;
    float torso_height = height * 0.35f;
    float leg_height = height * 0.45f;
    float arm_length = height * 0.25f;

    // Head (sphere) - positioned at top
    if (!createSphere(0, height - head_radius, 0, head_radius, 4, shadeColor565(color, 1.25f), wireframe))
        return false;

    // Torso - positioned in middle, wider and deeper
    if (!createCube(0, leg_height + torso_height / 2, 0, torso_width, torso_height, torso_width * 0.8f, color, wireframe))
        return false;

    // Arms - positioned at shoulder level
    float arm_width = torso_width * 0.35f;
    float arm_y = leg_height + torso_height - arm_length / 2;
    const uint16_t arm_color = shadeColor565(color, 0.75f);
    if (!createCube(-torso_width * 0.8f, arm_y, 0, arm_width, arm_length, arm_width, arm_color, wireframe))
        return false;
    if (!createCube(torso_width * 0.8f, arm_y, 0, arm_width, arm_length, arm_width, arm_color, wireframe))
        return false;

    // Legs - positioned so their bottoms touch ground (y=0)
    float leg_width = torso_width * 0.45f;
    const uint16_t leg_color = shadeColor565(color, 0.55f);
    if (!createCube(-leg_width * 0.7f, leg_height / 2, 0, leg_width, leg_height, leg_width, leg_color, wireframe))
        return false;
    if (!createCube(leg_width * 0.7f, leg_height / 2, 0, leg_width, leg_height, leg_width, leg_color, wireframe))
        return false;

    return true;
}

bool Sprite3D::createPillar(float height, float radius, uint16_t color, bool wireframe)
{
    clearTriangles();
    type = SPRITE_PILLAR;
    float pillar_radius = radius * 1.5f;

    // Main cylinder - 6 segments = 12 triangles
    if (!createCylinder(0, height / 2, 0, pillar_radius, height, 6, color, wireframe))
        return false;

    // Base - 4 segments = 8 triangles
    if (!createCylinder(0, pillar_radius * 0.4f, 0, pillar_radius * 1.4f, pillar_radius * 0.8f, 4, color, wireframe))
        return false;

    // Top - 4 segments = 8 triangles
    return createCylinder(0, height - pillar_radius * 0.4f, 0, pillar_radius * 1.4f, pillar_radius * 0.8f, 4, color, wireframe);
}

bool Sprite3D::createSphere(float x, float y, float z, float radius, uint8_t segments, uint16_t color, bool wireframe)
{
    // limit segments for sphere to prevent triangle explosion
    if (segments > 4)
        segments = 4;

    for (uint8_t lat = 0; lat < segments / 2; lat++)
    {
        float theta1 = (float)lat * M_PI / (segments / 2);
        float theta2 = (float)(lat + 1) * M_PI / (segments / 2);

        for (uint8_t lon = 0; lon < segments; lon++)
        {
            float phi1 = (float)lon * 2.0f * M_PI / segments;
            float phi2 = (float)(lon + 1) * 2.0f * M_PI / segments;

            // Calculate vertices
            float x1 = x + radius * sinf(theta1) * cosf(phi1);
            float y1 = y + radius * cosf(theta1);
            float z1 = z + radius * sinf(theta1) * sinf(phi1);
            //
            float x2 = x + radius * sinf(theta1) * cosf(phi2);
            float y2 = y + radius * cosf(theta1);
            float z2 = z + radius * sinf(theta1) * sinf(phi2);
            //
            float x3 = x + radius * sinf(theta2) * cosf(phi1);
            float y3 = y + radius * cosf(theta2);
            float z3 = z + radius * sinf(theta2) * sinf(phi1);
            //
            float x4 = x + radius * sinf(theta2) * cosf(phi2);
            float y4 = y + radius * cosf(theta2);
            float z4 = z + radius * sinf(theta2) * sinf(phi2);

            // Add triangles
            if (lat > 0)
            {
                if (!addTriangle(Triangle3D(x1, y1, z1, x2, y2, z2, x3, y3, z3, color, wireframe)))
                    return false;
            }
            if (lat < segments / 2 - 1)
            {
                if (!addTriangle(Triangle3D(x2, y2, z2, x4, y4, z4, x3, y3, z3, color, wireframe)))
                    return false;
            }
        }
    }
    return true;
}

bool Sprite3D::createTree(float height, uint16_t color, bool wireframe)
{
    clearTriangles();
    type = SPRITE_TREE;

    float trunk_width = height * 0.18f;
    float trunk_height = height * 0.4f;
    float crown_width = height * 0.65f;
    float crown_height = height * 0.6f;

    // Trunk (simple cube) - positioned so bottom touches ground (y=0) - brown
    if (!createCube(0, trunk_height / 2, 0, trunk_width, trunk_height, trunk_width, 0x9A60, wireframe))
        return false;

    // Crown (simple cube representing foliage) - positioned on top of trunk
    return createCube(0, trunk_height + crown_height / 2, 0, crown_width, crown_height, crown_width, color, wireframe);
}

bool Sprite3D::createTriangularPrism(float x, float y, float z, float width, float height, float depth, uint16_t color, bool wireframe)
{
    float hw = width * 0.5f;
    float hh = height * 0.5f;
    float hd = depth * 0.5f;

    // Front triangle
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z + hd,
            x + hw, y - hh, z + hd,
            x, y + hh, z + hd, color, wireframe)))
        return false;

    // Back triangle
    if (!addTriangle(Triangle3D(
            x + hw, y - hh, z - hd,
            x - hw, y - hh, z - hd,
            x, y + hh, z - hd, color, wireframe)))
        return false;

    // Bottom face
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z - hd,
            x + hw, y - hh, z - hd,
            x + hw, y - hh, z + hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z - hd,
            x + hw, y - hh, z + hd,
            x - hw, y - hh, z + hd, color, wireframe)))
        return false;

    // Side faces
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z + hd,
            x, y + hh, z + hd,
            x, y + hh, z - hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(
            x - hw, y - hh, z + hd,
            x, y + hh, z - hd,
            x - hw, y - hh, z - hd, color, wireframe)))
        return false;

    if (!addTriangle(Triangle3D(
            x, y + hh, z + hd,
            x + hw, y - hh, z + hd,
            x + hw, y - hh, z - hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(
            x, y + hh, z + hd,
            x + hw, y - hh, z - hd,
            x, y + hh, z - hd, color, wireframe)))
        return false;

    return true;
}

bool Sprite3D::createWall(float x, float y, float z, float width, float height, float depth, uint16_t color, bool wireframe)
{
    // Wall segment using raw triangles, offset by (x, y, z)
    const float hw = width / 2, hh = height / 2, hd = depth / 2;
    // Front face
    if (!addTriangle(Triangle3D(x - hw, y - hh, z + hd, x + hw, y - hh, z + hd, x + hw, y + hh, z + hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x - hw, y - hh, z + hd, x + hw, y + hh, z + hd, x - hw, y + hh, z + hd, color, wireframe)))
        return false;
    // Back face
    if (!addTriangle(Triangle3D(x + hw, y - hh, z - hd, x - hw, y - hh, z - hd, x - hw, y + hh, z - hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x + hw, y - hh, z - hd, x - hw, y + hh, z - hd, x + hw, y + hh, z - hd, color, wireframe)))
        return false;
    // Left, right, top caps
    if (!addTriangle(Triangle3D(x - hw, y - hh, z - hd, x - hw, y - hh, z + hd, x - hw, y + hh, z + hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x - hw, y - hh, z - hd, x - hw, y + hh, z + hd, x - hw, y + hh, z - hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x + hw, y - hh, z + hd, x + hw, y - hh, z - hd, x + hw, y + hh, z - hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x + hw, y - hh, z + hd, x + hw, y + hh, z - hd, x + hw, y + hh, z + hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x - hw, y + hh, z + hd, x + hw, y + hh, z + hd, x + hw, y + hh, z - hd, color, wireframe)))
        return false;
    if (!addTriangle(Triangle3D(x - hw, y + hh, z + hd, x + hw, y + hh, z - hd, x - hw, y + hh, z - hd, color, wireframe)))
        return false;
    return true;
}

bool Sprite3D::fromPath(const char *path, bool wireframe)
{
#ifdef ENGINE_STORAGE_READ
    clearTriangles();
    Triangle3D *buf = ENGINE_MEM_NEW Triangle3D[ENGINE_MAX_TRIANGLES_PER_SPRITE];
    if (!buf)
    {
        ENGINE_LOG_INFO("Sprite3D::fromPath failed to allocate memory for triangle data\n");
        return false;
    }
    size_t bytes = ENGINE_STORAGE_READ(path, buf, sizeof(Triangle3D) * ENGINE_MAX_TRIANGLES_PER_SPRITE);
    if (bytes == 0)
    {
        ENGINE_MEM_DELETE[] buf;
        ENGINE_LOG_INFO("Sprite3D::fromPath failed to read triangle data from path: %s\n", path);
        return false;
    }
    uint16_t count = bytes / sizeof(Triangle3D);
    for (uint16_t i = 0; i < count; i++)
    {
        buf[i].wireframe = wireframe;
        if (!addTriangle(buf[i]))
        {
            ENGINE_MEM_DELETE[] buf;
            return false;
        }
    }
    ENGINE_MEM_DELETE[] buf;
    return true;
#else
    return false;
#endif
}

bool Sprite3D::getTransformedTriangle(uint16_t index, const Vector &camera_pos, Triangle3D &out) const
{
    if (index >= triangle_count)
        return false;

    out = *triangles[index];

    // compute sin/cos once for all three vertices
    const float cos_a = cosf(rotation_y);
    const float sin_a = sinf(rotation_y);

    // Vertex 1
    out.x1 *= scale_factor;
    out.y1 *= scale_factor;
    out.z1 *= scale_factor;
    float ox = out.x1;
    out.x1 = ox * cos_a - out.z1 * sin_a;
    out.z1 = ox * sin_a + out.z1 * cos_a;
    out.x1 += position.x;
    out.y1 += position.z;
    out.z1 += position.y;

    // Vertex 2
    out.x2 *= scale_factor;
    out.y2 *= scale_factor;
    out.z2 *= scale_factor;
    ox = out.x2;
    out.x2 = ox * cos_a - out.z2 * sin_a;
    out.z2 = ox * sin_a + out.z2 * cos_a;
    out.x2 += position.x;
    out.y2 += position.z;
    out.z2 += position.y;

    // Vertex 3
    out.x3 *= scale_factor;
    out.y3 *= scale_factor;
    out.z3 *= scale_factor;
    ox = out.x3;
    out.x3 = ox * cos_a - out.z3 * sin_a;
    out.z3 = ox * sin_a + out.z3 * cos_a;
    out.x3 += position.x;
    out.y3 += position.z;
    out.z3 += position.y;

    // Back-face culling: check if triangle faces the camera
    {
        // Calculate triangle normal using cross product of two edge vectors
        const float e1x = out.x2 - out.x1;
        const float e1y = out.y2 - out.y1;
        const float e1z = out.z2 - out.z1;
        const float e2x = out.x3 - out.x1;
        const float e2y = out.y3 - out.y1;
        const float e2z = out.z3 - out.z1;

        // Cross product: normal = e1 × e2
        const float nx = e1y * e2z - e1z * e2y;
        const float ny = e1z * e2x - e1x * e2z;
        const float nz = e1x * e2y - e1y * e2x;

        // Vector from triangle center to camera
        const float cx = (out.x1 + out.x2 + out.x3) * (1.0f / 3.0f);
        const float cy = (out.y1 + out.y2 + out.y3) * (1.0f / 3.0f);
        const float cz = (out.z1 + out.z2 + out.z3) * (1.0f / 3.0f);

        const float tox = camera_pos.x - cx;
        const float toy = 0.5f - cy;         // Camera height offset
        const float toz = camera_pos.y - cz; // camera_pos.y is Z in world space

        // Dot product: if positive, triangle faces camera
        out.set = (nx * tox + ny * toy + nz * toz) > 0.0f;
    }
    return out.set;
}

bool Sprite3D::initializeAsHouse(Vector pos, float width, float height, float rot, uint16_t color, bool wireframe)
{
    position = pos;
    rotation_y = rot;
    clearTriangles();
    type = SPRITE_HOUSE;
    active = true;
    return createHouse(width, height, color, wireframe);
}

bool Sprite3D::initializeAsHumanoid(Vector pos, float height, float rot, uint16_t color, bool wireframe)
{
    position = pos;
    rotation_y = rot;
    clearTriangles();
    type = SPRITE_HUMANOID;
    active = true;
    return createHumanoid(height, color, wireframe);
}

bool Sprite3D::initializeAsPillar(Vector pos, float height, float radius, uint16_t color, bool wireframe)
{
    position = pos;
    rotation_y = 0;
    clearTriangles();
    type = SPRITE_PILLAR;
    active = true;
    return createPillar(height, radius, color, wireframe);
}

bool Sprite3D::initializeAsTree(Vector pos, float height, uint16_t color, bool wireframe)
{
    position = pos;
    rotation_y = 0;
    clearTriangles();
    type = SPRITE_TREE;
    active = true;
    return createTree(height, color, wireframe);
}

void Sprite3D::setWireframe(bool wireframe)
{
    for (uint16_t i = 0; i < triangle_count; i++)
    {
        if (triangles[i])
        {
            triangles[i]->wireframe = wireframe;
        }
    }
}

bool Sprite3D::toPath(const char *path) const
{
#ifdef ENGINE_STORAGE_WRITE
    if (triangle_count == 0)
        return false;
    if (triangle_count == ENGINE_MAX_TRIANGLES_PER_SPRITE)
        return ENGINE_STORAGE_WRITE(path, triangles, sizeof(Triangle3D) * triangle_count);
    Triangle3D *buf = ENGINE_MEM_NEW Triangle3D[triangle_count];
    if (!buf)
        return false;
    for (uint16_t i = 0; i < triangle_count; i++)
        buf[i] = *triangles[i];
    const bool ok = ENGINE_STORAGE_WRITE(path, buf, sizeof(Triangle3D) * triangle_count);
    ENGINE_MEM_DELETE[] buf;
    return ok;
#else
    return false;
#endif
}