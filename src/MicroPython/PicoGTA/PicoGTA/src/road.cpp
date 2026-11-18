#include "road.hpp"
#include "landscape.hpp"
#include <math.h>

bool Road::addLine(Landscape &landscape, float line, float begin, float end, bool vertical) const
{
    const float length = end - begin;
    if (length <= 0.0f)
        return false;

    const float middle = (begin + end) * 0.5f;
    bool success = true;
    if (vertical)
    {
        if (!landscape.addGroundRect(line, middle, Landscape::ROAD_WIDTH, length,
                                     Landscape::ROAD_HEIGHT, Landscape::COLOR_ROAD,
                                     Landscape::ROAD_SEGMENT))
            success = false;
        if (!landscape.addGroundRect(line - Landscape::SIDEWALK_OFFSET, middle,
                                     Landscape::SIDEWALK_WIDTH, length,
                                     Landscape::SIDEWALK_HEIGHT, Landscape::COLOR_SIDEWALK,
                                     Landscape::SIDEWALK_SEGMENT))
            success = false;
        if (!landscape.addGroundRect(line + Landscape::SIDEWALK_OFFSET, middle,
                                     Landscape::SIDEWALK_WIDTH, length,
                                     Landscape::SIDEWALK_HEIGHT, Landscape::COLOR_SIDEWALK,
                                     Landscape::SIDEWALK_SEGMENT))
            success = false;
    }
    else
    {
        if (!landscape.addGroundRect(middle, line, length, Landscape::ROAD_WIDTH,
                                     Landscape::ROAD_HEIGHT, Landscape::COLOR_ROAD,
                                     Landscape::ROAD_SEGMENT))
            success = false;
        if (!landscape.addGroundRect(middle, line - Landscape::SIDEWALK_OFFSET,
                                     length, Landscape::SIDEWALK_WIDTH,
                                     Landscape::SIDEWALK_HEIGHT, Landscape::COLOR_SIDEWALK,
                                     Landscape::SIDEWALK_SEGMENT))
            success = false;
        if (!landscape.addGroundRect(middle, line + Landscape::SIDEWALK_OFFSET,
                                     length, Landscape::SIDEWALK_WIDTH,
                                     Landscape::SIDEWALK_HEIGHT, Landscape::COLOR_SIDEWALK,
                                     Landscape::SIDEWALK_SEGMENT))
            success = false;
    }

    float remainder = fmodf(Landscape::MARK_OFFSET - begin, Landscape::MARK_SPACING);
    if (remainder < 0.0f)
        remainder += Landscape::MARK_SPACING;
    float position = begin + remainder;
    while (position <= end)
    {
        if (vertical)
        {
            if (!landscape.addGroundRect(line, position, Landscape::MARK_WIDTH,
                                         Landscape::MARK_LENGTH, Landscape::MARK_HEIGHT,
                                         Landscape::COLOR_LINE, Landscape::MARK_LENGTH))
                success = false;
        }
        else if (!landscape.addGroundRect(position, line, Landscape::MARK_LENGTH,
                                          Landscape::MARK_WIDTH, Landscape::MARK_HEIGHT,
                                          Landscape::COLOR_LINE, Landscape::MARK_LENGTH))
        {
            success = false;
        }
        position += Landscape::MARK_SPACING;
    }

    return success;
}