#pragma once

#include <math.h>

namespace EngineProjection
{
struct Vertex
{
    float x, y, z;
};

struct Point
{
    float x, y;
};

struct Plane
{
    float x, y, z, offset;

    float distance(const Vertex &v) const
    {
        return x * v.x + y * v.y + z * v.z + offset;
    }
};

// A triangle clipped against five planes has at most eight vertices.
static constexpr int MAX_VERTICES = 8;

inline int clip(const Vertex *input, int count, Vertex *output, const Plane &plane)
{
    if (count == 0)
        return 0;
    int written = 0;
    Vertex previous = input[count - 1];
    float previous_distance = plane.distance(previous);
    for (int i = 0; i < count; ++i)
    {
        const Vertex current = input[i];
        const float distance = plane.distance(current);
        if ((distance > 0 && previous_distance < 0) || (distance < 0 && previous_distance > 0))
        {
            const float t = previous_distance / (previous_distance - distance);
            output[written++] = {
                previous.x + t * (current.x - previous.x),
                previous.y + t * (current.y - previous.y),
                previous.z + t * (current.z - previous.z)};
        }
        if (distance >= 0)
            output[written++] = current;
        previous = current;
        previous_distance = distance;
    }
    return written;
}

inline float bound(float value, float maximum)
{
    return value < 0 ? 0 : (value > maximum ? maximum : value);
}

// Clip in camera space before perspective division or unsigned LCD conversion.
// clamp=true retains the preview API's vertex-pinning behavior at screen edges.
inline int project(const Vertex triangle[3], float width, float height,
                   bool clamp, Point output[MAX_VERTICES])
{
    if (width < 1 || height < 1)
        return 0;
    Vertex buffers[2][MAX_VERTICES];
    for (int i = 0; i < 3; ++i)
    {
        if (!isfinite(triangle[i].x) || !isfinite(triangle[i].y) || !isfinite(triangle[i].z))
            return 0;
        buffers[0][i] = triangle[i];
    }
    const float half_width = width * 0.5f, half_height = height * 0.5f;
    const Plane planes[] = {
        {0, 0, 1, -0.1f},
        {height, 0, half_width, 0},
        {-height, 0, width - 1 - half_width, 0},
        {0, -height, half_height, 0},
        {0, height, height - 1 - half_height, 0}};
    int count = 3, active = 0;
    for (int plane = 0; plane < (clamp ? 1 : 5); ++plane)
    {
        count = clip(buffers[active], count, buffers[1 - active], planes[plane]);
        active = 1 - active;
        if (count < 3)
            return 0;
    }
    for (int i = 0; i < count; ++i)
    {
        const Vertex &v = buffers[active][i];
        // Intersections on the near plane may round very slightly below it.
        const float scale = height / (v.z < 0.1f ? 0.1f : v.z);
        output[i] = {bound(v.x * scale + half_width, width - 1),
                     bound(-v.y * scale + half_height, height - 1)};
    }
    return count;
}
} // namespace EngineProjection
