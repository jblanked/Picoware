#include "billboard.hpp"
#include <math.h>

Billboard::Billboard() : dirs{}, num_dirs(8), num_poses(1) {}

Billboard::~Billboard()
{
    for (int dir = 0; dir < MAX_DIRS; ++dir)
        for (int pose = 0; pose < MAX_POSES; ++pose)
            ENGINE_MEM_DELETE dirs[dir][pose];
}

bool Billboard::setDirectionPose(int dir, int pose, Image *image)
{
    if (dir < 0 || dir >= num_dirs || pose < 0 || pose >= num_poses)
        return false;
    if (image && (!image->getPixels() || !(image->size.x >= 1 && image->size.x <= 1024 && image->size.y >= 1 && image->size.y <= 1024) ||
                  uint16_t(image->size.x) != image->size.x || uint16_t(image->size.y) != image->size.y))
        return false;
    if (dirs[dir][pose] == image)
        return true;
    if (image)
        for (int d = 0; d < MAX_DIRS; ++d)
            for (int p = 0; p < MAX_POSES; ++p)
                if (dirs[d][p] == image)
                    return false;
    ENGINE_MEM_DELETE dirs[dir][pose];
    dirs[dir][pose] = image;
    return true;
}

void Billboard::setCounts(int directions, int poses)
{
    num_dirs = directions < 1 ? 1 : (directions > MAX_DIRS ? MAX_DIRS : directions);
    num_poses = poses < 1 ? 1 : (poses > MAX_POSES ? MAX_POSES : poses);
}

Image *Billboard::viewForFacing(float angle, int pose) const
{
    if (!isfinite(angle))
        return nullptr;
    angle = fmodf(angle, 6.283185307179586f);
    int dir = int(floorf(angle * num_dirs / 6.283185307179586f + 0.5f));
    dir = (dir % num_dirs + num_dirs) % num_dirs;
    pose = pose < 0 ? 0 : (pose >= num_poses ? num_poses - 1 : pose);
    return dirs[dir][pose];
}
