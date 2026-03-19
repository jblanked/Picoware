#include "sprite3d_mp.h"
#include "engine/sprite3d.hpp"

static inline Sprite3D *sprite3d_get_context(sprite3d_mp_obj_t *self)
{
    return static_cast<Sprite3D *>(self->context);
}

mp_obj_t sprite3d_mp_init(void)
{
    sprite3d_mp_obj_t *sprite3d = mp_obj_malloc_with_finaliser(sprite3d_mp_obj_t, &sprite3d_mp_type);
    sprite3d->base.type = &sprite3d_mp_type;
    sprite3d->context = new Sprite3D();
    sprite3d->freed = false;
    Sprite3D *ctx = sprite3d_get_context(sprite3d);
    Vector pos = ctx->getPosition();
    sprite3d->position_obj = vector_mp_init(pos.x, pos.y, pos.z, pos.integer);
    return MP_OBJ_FROM_PTR(sprite3d);
}

void sprite3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return;
    Sprite3D *ctx = sprite3d_get_context(self);
    Vector pos = ctx->getPosition();
    mp_print_str(print, "Sprite3D(");
    mp_print_str(print, "type=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->getType()), PRINT_REPR);
    mp_print_str(print, ", position=(");
    mp_obj_print_helper(print, mp_obj_new_float(pos.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(pos.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(pos.z), PRINT_REPR);
    mp_print_str(print, "), rotation_y=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->getRotation()), PRINT_REPR);
    mp_print_str(print, ", scale_factor=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->getScale()), PRINT_REPR);
    mp_print_str(print, ", active=");
    mp_obj_print_helper(print, ctx->isActive() ? mp_const_true : mp_const_false, PRINT_REPR);
    mp_print_str(print, ", triangle_count=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->getTriangleCount()), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t sprite3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    return sprite3d_mp_init();
}

mp_obj_t sprite3d_mp_del(mp_obj_t self_in)
{
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Sprite3D *ctx = sprite3d_get_context(self);
    if (ctx)
        delete ctx;
    self->context = nullptr;
    self->freed = true;
    self->position_obj = MP_OBJ_NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sprite3d_mp_del_obj, sprite3d_mp_del);

void sprite3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attributes
        Sprite3D *ctx = sprite3d_get_context(self);
        switch (attribute)
        {
        case MP_QSTR_position:
        {
            destination[0] = self->position_obj;
            break;
        }
        case MP_QSTR_rotation_y:
            destination[0] = mp_obj_new_float(ctx->getRotation());
            break;
        case MP_QSTR_scale_factor:
            destination[0] = mp_obj_new_float(ctx->getScale());
            break;
        case MP_QSTR_type:
            destination[0] = mp_obj_new_int(ctx->getType());
            break;
        case MP_QSTR_active:
            destination[0] = mp_obj_new_bool(ctx->isActive());
            break;
        case MP_QSTR_triangle_count:
            destination[0] = mp_obj_new_int(ctx->getTriangleCount());
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&sprite3d_mp_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // store attributes
        switch (attribute)
        {
        case MP_QSTR_position:
            sprite3d_mp_set_position(self_in, destination[1]);
            break;
        case MP_QSTR_rotation_y:
            sprite3d_mp_set_rotation_y(self_in, destination[1]);
            break;
        case MP_QSTR_scale_factor:
            sprite3d_mp_set_scale(self_in, destination[1]);
            break;
        case MP_QSTR_active:
            sprite3d_mp_set_active(self_in, destination[1]);
            break;
        default:
            return; // Fail
        };
        destination[0] = MP_OBJ_NULL;
    }
}

mp_obj_t sprite3d_mp_add_triangle(size_t n_args, const mp_obj_t *args)
{
    // sprite3d_mp_obj_t self, float x1, float y1, float z1, float x2, float y2, float z2, float x3, float y3, float z3, uint16_t color (optional)
    if (n_args < 10 || n_args > 11)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("add_triangle requires 10 or 11 arguments"));
    }
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float x1 = mp_obj_get_float(args[1]);
    float y1 = mp_obj_get_float(args[2]);
    float z1 = mp_obj_get_float(args[3]);
    float x2 = mp_obj_get_float(args[4]);
    float y2 = mp_obj_get_float(args[5]);
    float z2 = mp_obj_get_float(args[6]);
    float x3 = mp_obj_get_float(args[7]);
    float y3 = mp_obj_get_float(args[8]);
    float z3 = mp_obj_get_float(args[9]);
    uint16_t color = n_args > 10 ? static_cast<uint16_t>(mp_obj_get_int(args[10])) : 0x0000;
    ctx->addTriangle(x1, y1, z1, x2, y2, z2, x3, y3, z3, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_add_triangle_obj, 10, 11, sprite3d_mp_add_triangle);

mp_obj_t sprite3d_mp_clear_triangles(mp_obj_t self_in)
{
    // Arguments: self
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Sprite3D *ctx = sprite3d_get_context(self);
    ctx->clearTriangles();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sprite3d_mp_clear_triangles_obj, sprite3d_mp_clear_triangles);

mp_obj_t sprite3d_mp_create_humanoid(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, height (optional), color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float height = n_args > 1 ? mp_obj_get_float(args[1]) : 1.8f;
    uint16_t color = n_args > 2 ? static_cast<uint16_t>(mp_obj_get_int(args[2])) : 0x0000;
    ctx->createHumanoid(height, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_humanoid_obj, 1, 3, sprite3d_mp_create_humanoid);

mp_obj_t sprite3d_mp_create_tree(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, height (optional), color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float height = n_args > 1 ? mp_obj_get_float(args[1]) : 2.0f;
    uint16_t color = n_args > 2 ? static_cast<uint16_t>(mp_obj_get_int(args[2])) : 0x0000;
    ctx->createTree(height, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_tree_obj, 1, 3, sprite3d_mp_create_tree);

mp_obj_t sprite3d_mp_create_house(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, width (optional), height (optional), color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float width = n_args > 1 ? mp_obj_get_float(args[1]) : 2.0f;
    float height = n_args > 2 ? mp_obj_get_float(args[2]) : 2.5f;
    uint16_t color = n_args > 3 ? static_cast<uint16_t>(mp_obj_get_int(args[3])) : 0x0000;
    ctx->createHouse(width, height, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_house_obj, 1, 4, sprite3d_mp_create_house);

mp_obj_t sprite3d_mp_create_pillar(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, height (optional), radius (optional), color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float height = n_args > 1 ? mp_obj_get_float(args[1]) : 3.0f;
    float radius = n_args > 2 ? mp_obj_get_float(args[2]) : 0.3f;
    uint16_t color = n_args > 3 ? static_cast<uint16_t>(mp_obj_get_int(args[3])) : 0x0000;
    ctx->createPillar(height, radius, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_pillar_obj, 1, 4, sprite3d_mp_create_pillar);

mp_obj_t sprite3d_mp_create_wall(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, z, width (optional), height (optional), depth (optional), color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float z = mp_obj_get_float(args[3]);
    float width = n_args > 4 ? mp_obj_get_float(args[4]) : 4.0f;
    float height = n_args > 5 ? mp_obj_get_float(args[5]) : 1.5f;
    float depth = n_args > 6 ? mp_obj_get_float(args[6]) : 0.2f;
    uint16_t color = n_args > 7 ? static_cast<uint16_t>(mp_obj_get_int(args[7])) : 0x0000;
    ctx->createWall(x, y, z, width, height, depth, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_wall_obj, 4, 8, sprite3d_mp_create_wall);

mp_obj_t sprite3d_mp_create_cube(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, z, width, height, depth, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float z = mp_obj_get_float(args[3]);
    float width = mp_obj_get_float(args[4]);
    float height = mp_obj_get_float(args[5]);
    float depth = mp_obj_get_float(args[6]);
    uint16_t color = n_args > 7 ? static_cast<uint16_t>(mp_obj_get_int(args[7])) : 0x0000;
    ctx->createCube(x, y, z, width, height, depth, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_cube_obj, 7, 8, sprite3d_mp_create_cube);

mp_obj_t sprite3d_mp_create_cylinder(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, z, radius, height, segments, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float z = mp_obj_get_float(args[3]);
    float radius = mp_obj_get_float(args[4]);
    float height = mp_obj_get_float(args[5]);
    uint8_t segments = static_cast<uint8_t>(mp_obj_get_int(args[6]));
    uint16_t color = n_args > 7 ? static_cast<uint16_t>(mp_obj_get_int(args[7])) : 0x0000;
    ctx->createCylinder(x, y, z, radius, height, segments, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_cylinder_obj, 7, 8, sprite3d_mp_create_cylinder);

mp_obj_t sprite3d_mp_create_sphere(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, z, radius, segments, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float z = mp_obj_get_float(args[3]);
    float radius = mp_obj_get_float(args[4]);
    uint8_t segments = static_cast<uint8_t>(mp_obj_get_int(args[5]));
    uint16_t color = n_args > 6 ? static_cast<uint16_t>(mp_obj_get_int(args[6])) : 0x0000;
    ctx->createSphere(x, y, z, radius, segments, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_sphere_obj, 6, 7, sprite3d_mp_create_sphere);

mp_obj_t sprite3d_mp_create_triangular_prism(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, z, width, height, depth, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float z = mp_obj_get_float(args[3]);
    float width = mp_obj_get_float(args[4]);
    float height = mp_obj_get_float(args[5]);
    float depth = mp_obj_get_float(args[6]);
    uint16_t color = n_args > 7 ? static_cast<uint16_t>(mp_obj_get_int(args[7])) : 0x0000;
    ctx->createTriangularPrism(x, y, z, width, height, depth, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_create_triangular_prism_obj, 7, 8, sprite3d_mp_create_triangular_prism);

mp_obj_t sprite3d_mp_initialize_as_house(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, pos, width, height, rotation, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
    vector_mp_obj_t *pos_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    Vector pos(pos_vec->x, pos_vec->y, pos_vec->z, pos_vec->integer);
    float width = mp_obj_get_float(args[2]);
    float height = mp_obj_get_float(args[3]);
    float rotation = mp_obj_get_float(args[4]);
    uint16_t color = n_args > 5 ? static_cast<uint16_t>(mp_obj_get_int(args[5])) : 0x0000;
    ctx->initializeAsHouse(pos, width, height, rotation, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_initialize_as_house_obj, 5, 6, sprite3d_mp_initialize_as_house);

mp_obj_t sprite3d_mp_initialize_as_humanoid(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, pos, height, rotation, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
    vector_mp_obj_t *pos_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    Vector pos(pos_vec->x, pos_vec->y, pos_vec->z, pos_vec->integer);
    float height = mp_obj_get_float(args[2]);
    float rotation = mp_obj_get_float(args[3]);
    uint16_t color = n_args > 4 ? static_cast<uint16_t>(mp_obj_get_int(args[4])) : 0x0000;
    ctx->initializeAsHumanoid(pos, height, rotation, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_initialize_as_humanoid_obj, 4, 5, sprite3d_mp_initialize_as_humanoid);

mp_obj_t sprite3d_mp_initialize_as_pillar(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, pos, height, radius, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
    vector_mp_obj_t *pos_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    Vector pos(pos_vec->x, pos_vec->y, pos_vec->z, pos_vec->integer);
    float height = mp_obj_get_float(args[2]);
    float radius = mp_obj_get_float(args[3]);
    uint16_t color = n_args > 4 ? static_cast<uint16_t>(mp_obj_get_int(args[4])) : 0x0000;
    ctx->initializeAsPillar(pos, height, radius, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_initialize_as_pillar_obj, 4, 5, sprite3d_mp_initialize_as_pillar);

mp_obj_t sprite3d_mp_initialize_as_tree(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, pos, height, color (optional)
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Sprite3D *ctx = sprite3d_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
    vector_mp_obj_t *pos_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    Vector pos(pos_vec->x, pos_vec->y, pos_vec->z, pos_vec->integer);
    float height = mp_obj_get_float(args[2]);
    uint16_t color = n_args > 3 ? static_cast<uint16_t>(mp_obj_get_int(args[3])) : 0x0000;
    ctx->initializeAsTree(pos, height, color);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sprite3d_mp_initialize_as_tree_obj, 3, 4, sprite3d_mp_initialize_as_tree);

mp_obj_t sprite3d_mp_set_position(mp_obj_t self_in, mp_obj_t position_obj)
{
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Sprite3D *ctx = sprite3d_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(position_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->setPosition(Vector(vec->x, vec->y, vec->z, vec->integer));
    self->position_obj = position_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(sprite3d_mp_set_position_obj, sprite3d_mp_set_position);

mp_obj_t sprite3d_mp_set_rotation_y(mp_obj_t self_in, mp_obj_t rotation_obj)
{
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Sprite3D *ctx = sprite3d_get_context(self);
    ctx->setRotation(mp_obj_get_float(rotation_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(sprite3d_mp_set_rotation_y_obj, sprite3d_mp_set_rotation_y);

mp_obj_t sprite3d_mp_set_scale(mp_obj_t self_in, mp_obj_t scale_obj)
{
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Sprite3D *ctx = sprite3d_get_context(self);
    ctx->setScale(mp_obj_get_float(scale_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(sprite3d_mp_set_scale_obj, sprite3d_mp_set_scale);

mp_obj_t sprite3d_mp_set_active(mp_obj_t self_in, mp_obj_t active_obj)
{
    sprite3d_mp_obj_t *self = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Sprite3D *ctx = sprite3d_get_context(self);
    ctx->setActive(mp_obj_is_true(active_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(sprite3d_mp_set_active_obj, sprite3d_mp_set_active);

static const mp_rom_map_elem_t sprite3d_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_add_triangle), MP_ROM_PTR(&sprite3d_mp_add_triangle_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_triangles), MP_ROM_PTR(&sprite3d_mp_clear_triangles_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_humanoid), MP_ROM_PTR(&sprite3d_mp_create_humanoid_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_tree), MP_ROM_PTR(&sprite3d_mp_create_tree_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_house), MP_ROM_PTR(&sprite3d_mp_create_house_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_pillar), MP_ROM_PTR(&sprite3d_mp_create_pillar_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_wall), MP_ROM_PTR(&sprite3d_mp_create_wall_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_cube), MP_ROM_PTR(&sprite3d_mp_create_cube_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_cylinder), MP_ROM_PTR(&sprite3d_mp_create_cylinder_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_sphere), MP_ROM_PTR(&sprite3d_mp_create_sphere_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_triangular_prism), MP_ROM_PTR(&sprite3d_mp_create_triangular_prism_obj)},
    {MP_ROM_QSTR(MP_QSTR_initialize_as_house), MP_ROM_PTR(&sprite3d_mp_initialize_as_house_obj)},
    {MP_ROM_QSTR(MP_QSTR_initialize_as_humanoid), MP_ROM_PTR(&sprite3d_mp_initialize_as_humanoid_obj)},
    {MP_ROM_QSTR(MP_QSTR_initialize_as_pillar), MP_ROM_PTR(&sprite3d_mp_initialize_as_pillar_obj)},
    {MP_ROM_QSTR(MP_QSTR_initialize_as_tree), MP_ROM_PTR(&sprite3d_mp_initialize_as_tree_obj)},

    {MP_ROM_QSTR(MP_QSTR_set_position), MP_ROM_PTR(&sprite3d_mp_set_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_rotation_y), MP_ROM_PTR(&sprite3d_mp_set_rotation_y_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_scale), MP_ROM_PTR(&sprite3d_mp_set_scale_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_active), MP_ROM_PTR(&sprite3d_mp_set_active_obj)},

    {MP_ROM_QSTR(MP_QSTR_MAX_TRIANGLES_PER_SPRITE), MP_ROM_INT(MAX_TRIANGLES_PER_SPRITE)},

    {MP_ROM_QSTR(MP_QSTR_SPRITE_HUMANOID), MP_ROM_INT(SPRITE_HUMANOID)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_TREE), MP_ROM_INT(SPRITE_TREE)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_HOUSE), MP_ROM_INT(SPRITE_HOUSE)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_PILLAR), MP_ROM_INT(SPRITE_PILLAR)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_CUSTOM), MP_ROM_INT(SPRITE_CUSTOM)},
};
static MP_DEFINE_CONST_DICT(sprite3d_mp_locals_dict, sprite3d_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t sprite3d_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Sprite3D,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)sprite3d_mp_make_new,
            (const void *)sprite3d_mp_print,
            (const void *)sprite3d_mp_attr,
            (const void *)&sprite3d_mp_locals_dict,
        },
    };
}