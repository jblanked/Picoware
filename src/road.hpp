#pragma once

class Landscape;

class Road
{
public:
    bool addLine(Landscape &landscape, float line, float begin, float end, bool vertical) const;
};