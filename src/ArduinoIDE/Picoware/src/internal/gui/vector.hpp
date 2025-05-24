#pragma once

namespace Picoware
{
    class Vector
    {
    public:
        float x;
        float y;

        Vector() {};

        Vector(float x, float y)
        {
            this->x = x;
            this->y = y;
        }

        Vector add(Vector a, Vector b);
        Vector sub(Vector a, Vector b);
        Vector mul(Vector a, Vector b);
        Vector div(Vector a, Vector b);
        Vector addf(Vector a, float b);
        Vector subf(Vector a, float b);
        Vector mulf(Vector a, float b);
        Vector divf(Vector a, float b);

        bool operator!=(const Vector &other) const
        {
            return (x != other.x) || (y != other.y);
        }
    };

}