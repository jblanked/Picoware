#include "../../internal/gui/vector.hpp"

namespace Picoware
{
    Vector Vector::add(Vector a, Vector b)
    {
        return (Vector){this->x = a.x + b.x, this->y = a.y + b.y};
    }
    Vector Vector::sub(Vector a, Vector b)
    {
        return (Vector){this->x = a.x - b.x, this->y = a.y - b.y};
    }

    Vector Vector::mul(Vector a, Vector b)
    {
        return (Vector){this->x = a.x * b.x, this->y = a.y * b.y};
    }

    Vector Vector::div(Vector a, Vector b)
    {
        return (Vector){this->x = a.x / b.x, this->y = a.y / b.y};
    }

    Vector Vector::addf(Vector a, float b)
    {
        return (Vector){this->x = a.x + b, this->y = a.y + b};
    }

    Vector Vector::subf(Vector a, float b)
    {
        return (Vector){this->x = a.x - b, this->y = a.y - b};
    }

    Vector Vector::mulf(Vector a, float b)
    {
        return (Vector){this->x = a.x * b, this->y = a.y * b};
    }

    Vector Vector::divf(Vector a, float b)
    {
        return (Vector){this->x = a.x / b, this->y = a.y / b};
    }
}