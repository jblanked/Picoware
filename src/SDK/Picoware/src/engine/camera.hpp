#pragma once
#include "../gui/vector.hpp"

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
