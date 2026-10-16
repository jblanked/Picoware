#pragma once
#include "image.hpp"

class Billboard
{
public:
    static const int MAX_DIRS = 8;
    static const int MAX_POSES = 8;
    Image *dirs[MAX_DIRS][MAX_POSES];
    int num_dirs;
    int num_poses;

    Billboard();
    ~Billboard();
    Billboard(const Billboard &) = delete;
    Billboard &operator=(const Billboard &) = delete;
    bool setDirectionPose(int dir, int pose, Image *image);
    bool setDirectionPoseData(int dir, int pose, uint16_t width, uint16_t height,
                              const uint8_t *pixels, size_t pixels_length,
                              const uint8_t *mask, size_t mask_length);
    void setCounts(int directions, int poses);
    Image *viewForFacing(float angle, int pose) const;
};
