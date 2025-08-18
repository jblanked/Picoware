#pragma once
#include "../gui/vector.hpp"
#include <math.h>

#define MAX_TRIANGLES_PER_SPRITE 28

// 3D vertex structure
struct Vertex3D
{
    float x, y, z;

    Vertex3D() : x(0), y(0), z(0) {}
    Vertex3D(float x, float y, float z) : x(x), y(y), z(z) {}

    // Rotate vertex around Y axis (for sprite facing)
    Vertex3D rotateY(float angle) const
    {
        float cos_a = cosf(angle);
        float sin_a = sinf(angle);
        return Vertex3D(
            x * cos_a - z * sin_a,
            y,
            x * sin_a + z * cos_a);
    }

    // Translate vertex
    Vertex3D translate(float dx, float dy, float dz) const
    {
        return Vertex3D(x + dx, y + dy, z + dz);
    }

    // Scale vertex
    Vertex3D scale(float sx, float sy, float sz) const
    {
        return Vertex3D(x * sx, y * sy, z * sz);
    }

    // Subtraction operator for vector operations
    Vertex3D operator-(const Vertex3D &other) const
    {
        return Vertex3D(x - other.x, y - other.y, z - other.z);
    }
};

// 3D triangle structure
struct Triangle3D
{
    Vertex3D vertices[3];
    bool visible;
    float distance; // For depth sorting

    Triangle3D() : visible(true), distance(0) {}

    Triangle3D(const Vertex3D &v1, const Vertex3D &v2, const Vertex3D &v3)
        : visible(true), distance(0)
    {
        vertices[0] = v1;
        vertices[1] = v2;
        vertices[2] = v3;
    }

    // Calculate triangle center for distance sorting
    Vertex3D getCenter() const
    {
        return Vertex3D(
            (vertices[0].x + vertices[1].x + vertices[2].x) / 3.0f,
            (vertices[0].y + vertices[1].y + vertices[2].y) / 3.0f,
            (vertices[0].z + vertices[1].z + vertices[2].z) / 3.0f);
    }

    // Check if triangle is facing the camera (basic backface culling)
    bool isFacingCamera(const Vector &camera_pos) const
    {
        // Calculate triangle normal using cross product
        Vertex3D v1 = vertices[1] - vertices[0];
        Vertex3D v2 = vertices[2] - vertices[0];

        // Cross product to get normal (right-hand rule)
        Vertex3D normal = Vertex3D(
            v1.y * v2.z - v1.z * v2.y,
            v1.z * v2.x - v1.x * v2.z,
            v1.x * v2.y - v1.y * v2.x);

        // Vector from triangle center to camera
        Vertex3D center = getCenter();
        Vertex3D to_camera = Vertex3D(
            camera_pos.x - center.x,
            0.5f - center.y,        // Camera height
            camera_pos.y - center.z // camera_pos.y is Z in world space
        );

        // Dot product - if positive, triangle faces camera
        float dot = normal.x * to_camera.x + normal.y * to_camera.y + normal.z * to_camera.z;
        return dot > 0.0f;
    }
};

enum SpriteType
{
    SPRITE_HUMANOID = 0,
    SPRITE_TREE = 1,
    SPRITE_HOUSE = 2,
    SPRITE_PILLAR = 3,
    SPRITE_CUSTOM = 4
};

class Sprite3D
{
private:
    Triangle3D triangles[MAX_TRIANGLES_PER_SPRITE];
    uint8_t triangle_count;
    Vector position;
    float rotation_y;
    float scale_factor;
    SpriteType type;
    bool active;

public:
    Sprite3D() : triangle_count(0), position(Vector(0, 0)), rotation_y(0),
                 scale_factor(1.0f), type(SPRITE_CUSTOM), active(false) {}

    // Basic sprite operations
    void setPosition(Vector pos) { position = pos; }
    Vector getPosition() const { return position; }
    void setRotation(float rot) { rotation_y = rot; }
    float getRotation() const { return rotation_y; }
    void setScale(float scale) { scale_factor = scale; }
    float getScale() const { return scale_factor; }
    void setActive(bool state) { active = state; }
    bool isActive() const { return active; }
    SpriteType getType() const { return type; }

    // Add triangle to sprite
    void addTriangle(const Triangle3D &triangle)
    {
        if (triangle_count < MAX_TRIANGLES_PER_SPRITE)
        {
            triangles[triangle_count] = triangle;
            triangle_count++;
        }
    }

    // Clear all triangles
    void clearTriangles()
    {
        triangle_count = 0;
    }

    // Initialize sprite with specific parameters for Entity class
    void initializeAsHumanoid(Vector pos, float height, float rot)
    {
        position = pos;
        rotation_y = rot;
        clearTriangles();
        type = SPRITE_HUMANOID;
        active = true;
        createHumanoid(height);
    }

    void initializeAsTree(Vector pos, float height)
    {
        position = pos;
        rotation_y = 0;
        clearTriangles();
        type = SPRITE_TREE;
        active = true;
        createTree(height);
    }

    void initializeAsHouse(Vector pos, float width, float height, float rot)
    {
        position = pos;
        rotation_y = rot;
        clearTriangles();
        type = SPRITE_HOUSE;
        active = true;
        createHouse(width, height);
    }

    void initializeAsPillar(Vector pos, float height, float radius)
    {
        position = pos;
        rotation_y = 0;
        clearTriangles();
        type = SPRITE_PILLAR;
        active = true;
        createPillar(height, radius);
    }

    // Get transformed triangles (with position, rotation, scale applied)
    void getTransformedTriangles(Triangle3D *output_triangles, uint8_t &count, const Vector &camera_pos) const
    {
        count = 0;
        if (!active)
            return;

        for (uint8_t i = 0; i < triangle_count; i++)
        {
            Triangle3D transformed = triangles[i];

            // Apply transformations to each vertex
            for (uint8_t v = 0; v < 3; v++)
            {
                // Scale
                transformed.vertices[v] = transformed.vertices[v].scale(scale_factor, scale_factor, scale_factor);

                // Rotate around Y axis
                transformed.vertices[v] = transformed.vertices[v].rotateY(rotation_y);

                // Translate to world position
                transformed.vertices[v] = transformed.vertices[v].translate(position.x, 0, position.y);
            }

            // Check if triangle should be rendered
            if (transformed.isFacingCamera(camera_pos))
            {
                // Calculate distance for sorting
                Vertex3D center = transformed.getCenter();
                float dx = center.x - camera_pos.x;
                float dz = center.z - camera_pos.y;
                transformed.distance = sqrtf(dx * dx + dz * dz);

                output_triangles[count] = transformed;
                count++;
            }
        }
    }

    // Create a humanoid character
    void createHumanoid(float height = 1.8f)
    {
        clearTriangles();
        type = SPRITE_HUMANOID;

        float head_radius = height * 0.12f;
        float torso_width = height * 0.20f;
        float torso_height = height * 0.35f;
        float leg_height = height * 0.45f;
        float arm_length = height * 0.25f;

        // Head (simplified as a cube) - positioned at top, wider
        createCube(0, height - head_radius, 0, head_radius * 2, head_radius * 2, head_radius * 1.5f);

        // Torso - positioned in middle, wider and deeper
        createCube(0, leg_height + torso_height / 2, 0, torso_width, torso_height, torso_width * 0.8f);

        // Arms - positioned at shoulder level
        float arm_width = torso_width * 0.35f;
        float arm_y = leg_height + torso_height - arm_length / 2;
        createCube(-torso_width * 0.8f, arm_y, 0, arm_width, arm_length, arm_width);
        createCube(torso_width * 0.8f, arm_y, 0, arm_width, arm_length, arm_width);

        // Legs - positioned so their bottoms touch ground (y=0)
        float leg_width = torso_width * 0.45f;
        createCube(-leg_width * 0.7f, leg_height / 2, 0, leg_width, leg_height, leg_width);
        createCube(leg_width * 0.7f, leg_height / 2, 0, leg_width, leg_height, leg_width);
    }

    // Create a simple tree
    void createTree(float height = 2.0f)
    {
        clearTriangles();
        type = SPRITE_TREE;

        float trunk_width = height * 0.18f;
        float trunk_height = height * 0.4f;
        float crown_width = height * 0.65f;
        float crown_height = height * 0.6f;

        // Trunk (simple cube) - positioned so bottom touches ground (y=0)
        createCube(0, trunk_height / 2, 0, trunk_width, trunk_height, trunk_width);

        // Crown (simple cube representing foliage) - positioned on top of trunk
        createCube(0, trunk_height + crown_height / 2, 0, crown_width, crown_height, crown_width);
    }

    // Create a simple house
    void createHouse(float width = 2.0f, float height = 2.5f)
    {
        clearTriangles();
        type = SPRITE_HOUSE;

        float wall_height = height * 0.7f;
        float roof_height = height * 0.3f;
        float house_width = width * 1.3f;
        float house_depth = width * 1.1f;

        // House base (cube)
        createCube(0, wall_height / 2, 0, house_width, wall_height, house_depth);

        // Roof (triangular prism)
        createTriangularPrism(0, wall_height + roof_height / 2, 0, house_width, roof_height, house_depth);
    }

    // Create a pillar
    void createPillar(float height = 3.0f, float radius = 0.3f)
    {
        clearTriangles();
        type = SPRITE_PILLAR;
        float pillar_radius = radius * 1.5f;

        // Main cylinder - 6 segments = 12 triangles
        createCylinder(0, height / 2, 0, pillar_radius, height, 6);

        // Base - 4 segments = 8 triangles
        createCylinder(0, pillar_radius * 0.4f, 0, pillar_radius * 1.4f, pillar_radius * 0.8f, 4);

        // Top - 4 segments = 8 triangles
        createCylinder(0, height - pillar_radius * 0.4f, 0, pillar_radius * 1.4f, pillar_radius * 0.8f, 4);
    }

private:
    void createCube(float x, float y, float z, float width, float height, float depth)
    {
        float hw = width * 0.5f;
        float hh = height * 0.5f;
        float hd = depth * 0.5f;

        // Render 4 most important faces (skip top and bottom to save triangles)
        // This gives 8 triangles per cube instead of 12

        // Front face (2 triangles)
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z + hd),
            Vertex3D(x + hw, y - hh, z + hd),
            Vertex3D(x + hw, y + hh, z + hd)));
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z + hd),
            Vertex3D(x + hw, y + hh, z + hd),
            Vertex3D(x - hw, y + hh, z + hd)));

        // Back face (2 triangles)
        addTriangle(Triangle3D(
            Vertex3D(x + hw, y - hh, z - hd),
            Vertex3D(x - hw, y - hh, z - hd),
            Vertex3D(x - hw, y + hh, z - hd)));
        addTriangle(Triangle3D(
            Vertex3D(x + hw, y - hh, z - hd),
            Vertex3D(x - hw, y + hh, z - hd),
            Vertex3D(x + hw, y + hh, z - hd)));

        // Right face (2 triangles)
        addTriangle(Triangle3D(
            Vertex3D(x + hw, y - hh, z + hd),
            Vertex3D(x + hw, y - hh, z - hd),
            Vertex3D(x + hw, y + hh, z - hd)));
        addTriangle(Triangle3D(
            Vertex3D(x + hw, y - hh, z + hd),
            Vertex3D(x + hw, y + hh, z - hd),
            Vertex3D(x + hw, y + hh, z + hd)));

        // Left face (2 triangles)
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z - hd),
            Vertex3D(x - hw, y - hh, z + hd),
            Vertex3D(x - hw, y + hh, z + hd)));
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z - hd),
            Vertex3D(x - hw, y + hh, z + hd),
            Vertex3D(x - hw, y + hh, z - hd)));
    }

    void createCylinder(float x, float y, float z, float radius, float height, uint8_t segments)
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
            addTriangle(Triangle3D(
                Vertex3D(x1, y - hh, z1),
                Vertex3D(x2, y - hh, z2),
                Vertex3D(x2, y + hh, z2)));
            addTriangle(Triangle3D(
                Vertex3D(x1, y - hh, z1),
                Vertex3D(x2, y + hh, z2),
                Vertex3D(x1, y + hh, z1)));
        }
    }

    void createSphere(float x, float y, float z, float radius, uint8_t segments)
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
                Vertex3D v1(
                    x + radius * sinf(theta1) * cosf(phi1),
                    y + radius * cosf(theta1),
                    z + radius * sinf(theta1) * sinf(phi1));
                Vertex3D v2(
                    x + radius * sinf(theta1) * cosf(phi2),
                    y + radius * cosf(theta1),
                    z + radius * sinf(theta1) * sinf(phi2));
                Vertex3D v3(
                    x + radius * sinf(theta2) * cosf(phi1),
                    y + radius * cosf(theta2),
                    z + radius * sinf(theta2) * sinf(phi1));
                Vertex3D v4(
                    x + radius * sinf(theta2) * cosf(phi2),
                    y + radius * cosf(theta2),
                    z + radius * sinf(theta2) * sinf(phi2));

                // Add triangles
                if (lat > 0)
                {
                    addTriangle(Triangle3D(v1, v2, v3));
                }
                if (lat < segments / 2 - 1)
                {
                    addTriangle(Triangle3D(v2, v4, v3));
                }
            }
        }
    }

    void createTriangularPrism(float x, float y, float z, float width, float height, float depth)
    {
        float hw = width * 0.5f;
        float hh = height * 0.5f;
        float hd = depth * 0.5f;

        // Front triangle
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z + hd),
            Vertex3D(x + hw, y - hh, z + hd),
            Vertex3D(x, y + hh, z + hd)));

        // Back triangle
        addTriangle(Triangle3D(
            Vertex3D(x + hw, y - hh, z - hd),
            Vertex3D(x - hw, y - hh, z - hd),
            Vertex3D(x, y + hh, z - hd)));

        // Bottom face
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z - hd),
            Vertex3D(x + hw, y - hh, z - hd),
            Vertex3D(x + hw, y - hh, z + hd)));
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z - hd),
            Vertex3D(x + hw, y - hh, z + hd),
            Vertex3D(x - hw, y - hh, z + hd)));

        // Side faces
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z + hd),
            Vertex3D(x, y + hh, z + hd),
            Vertex3D(x, y + hh, z - hd)));
        addTriangle(Triangle3D(
            Vertex3D(x - hw, y - hh, z + hd),
            Vertex3D(x, y + hh, z - hd),
            Vertex3D(x - hw, y - hh, z - hd)));

        addTriangle(Triangle3D(
            Vertex3D(x, y + hh, z + hd),
            Vertex3D(x + hw, y - hh, z + hd),
            Vertex3D(x + hw, y - hh, z - hd)));
        addTriangle(Triangle3D(
            Vertex3D(x, y + hh, z + hd),
            Vertex3D(x + hw, y - hh, z - hd),
            Vertex3D(x, y + hh, z - hd)));
    }
};
