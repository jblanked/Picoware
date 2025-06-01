#include <ArduinoJson.h>
#include "../../../applications/games/flipworld/game.hpp"
#include "../../../applications/games/flipworld/assets.hpp"
namespace FlipWorld
{
    typedef enum
    {
        ICON_ID_NONE = -1,            // None
        ICON_ID_HOUSE = 0,            // House
        ICON_ID_MAN,                  // Man
        ICON_ID_PLANT,                // Plant
        ICON_ID_TREE,                 // Tree
        ICON_ID_WOMAN,                // Woman
        ICON_ID_FENCE,                // Fence
        ICON_ID_FENCE_END,            // Fence end
        ICON_ID_FENCE_VERTICAL_END,   // Vertical fence end
        ICON_ID_FENCE_VERTICAL_START, // Vertical fence start
        ICON_ID_FLOWER,               // Flower
        ICON_ID_LAKE_BOTTOM,          // Lake bottom
        ICON_ID_LAKE_BOTTOM_LEFT,     // Lake bottom left
        ICON_ID_LAKE_BOTTOM_RIGHT,    // Lake bottom right
        ICON_ID_LAKE_LEFT,            // Lake left
        ICON_ID_LAKE_RIGHT,           // Lake right
        ICON_ID_LAKE_TOP,             // Lake top
        ICON_ID_LAKE_TOP_LEFT,        // Lake top left
        ICON_ID_LAKE_TOP_RIGHT,       // Lake top right
        ICON_ID_ROCK_LARGE,           // Large rock
        ICON_ID_ROCK_MEDIUM,          // Medium rock
        ICON_ID_ROCK_SMALL,           // Small rock
    } IconID;

    typedef struct
    {
        IconID id;
        const uint8_t *data;
        Vector size;
    } IconContext;

    static IconContext icon_context_get(const char *name)
    {
        if (strcmp(name, "tree") == 0)
            return {ICON_ID_TREE, icon_tree_16x16, Vector(16, 16)};
        if (strcmp(name, "fence") == 0)
            return {ICON_ID_FENCE, icon_fence_16x8px, Vector(16, 8)};
        if (strcmp(name, "fence_end") == 0)
            return {ICON_ID_FENCE_END, icon_fence_end_16x8px, Vector(16, 8)};
        if (strcmp(name, "fence_vertical_end") == 0)
            return {ICON_ID_FENCE_VERTICAL_END, icon_fence_vertical_end_6x8px, Vector(6, 8)};
        if (strcmp(name, "fence_vertical_start") == 0)
            return {ICON_ID_FENCE_VERTICAL_START, icon_fence_vertical_start_6x15px, Vector(6, 15)};
        if (strcmp(name, "rock_small") == 0)
            return {ICON_ID_ROCK_SMALL, icon_rock_small_10x8px, Vector(10, 8)};
        if (strcmp(name, "rock_medium") == 0)
            return {ICON_ID_ROCK_MEDIUM, icon_rock_medium_16x14px, Vector(16, 14)};
        if (strcmp(name, "rock_large") == 0)
            return {ICON_ID_ROCK_LARGE, icon_rock_large_18x19px, Vector(18, 19)};
        if (strcmp(name, "flower") == 0)
            return {ICON_ID_FLOWER, icon_flower_16x16, Vector(16, 16)};
        if (strcmp(name, "plant") == 0)
            return {ICON_ID_PLANT, icon_plant_16x16, Vector(16, 16)};
        if (strcmp(name, "man") == 0)
            return {ICON_ID_MAN, icon_man_7x16, Vector(7, 16)};
        if (strcmp(name, "woman") == 0)
            return {ICON_ID_WOMAN, icon_woman_9x16, Vector(9, 16)};
        if (strcmp(name, "lake_bottom") == 0)
            return {ICON_ID_LAKE_BOTTOM, icon_lake_bottom_31x12px, Vector(31, 12)};
        if (strcmp(name, "lake_bottom_left") == 0)
            return {ICON_ID_LAKE_BOTTOM_LEFT, icon_lake_bottom_left_24x22px, Vector(24, 22)};
        if (strcmp(name, "lake_bottom_right") == 0)
            return {ICON_ID_LAKE_BOTTOM_RIGHT, icon_lake_bottom_right_24x22px, Vector(24, 22)};
        if (strcmp(name, "lake_left") == 0)
            return {ICON_ID_LAKE_LEFT, icon_lake_left_11x31px, Vector(11, 31)};
        if (strcmp(name, "lake_right") == 0)
            return {ICON_ID_LAKE_RIGHT, icon_lake_right_11x31, Vector(11, 31)};
        if (strcmp(name, "lake_top") == 0)
            return {ICON_ID_LAKE_TOP, icon_lake_top_31x12px, Vector(31, 12)};
        if (strcmp(name, "lake_top_left") == 0)
            return {ICON_ID_LAKE_TOP_LEFT, icon_lake_top_left_24x22px, Vector(24, 22)};
        if (strcmp(name, "lake_top_right") == 0)
            return {ICON_ID_LAKE_TOP_RIGHT, icon_lake_top_right_24x22px, Vector(24, 22)};
        if (strcmp(name, "house") == 0)
            return {ICON_ID_HOUSE, icon_house_48x32px, Vector(48, 32)};

        return {ICON_ID_NONE, NULL, Vector(0, 0)};
    }

    static void icon_collision(Entity *self, Entity *other, Game *game)
    {
        if (strcmp(other->name, "Player") == 0)
        {
            other->position_set(other->old_position);
        }
    }

    static void icon_spawn(Level *level, const char *name, Vector pos)
    {
        // Get the icon context
        IconContext icon = icon_context_get(name);

        // Check if the icon is valid
        if (icon.data == NULL)
        {
            return;
        }

        // Retrieve shared Image instance
        Image *sharedImage = ImageManager::getInstance().getImage(name, icon.data, icon.size, true, true, level->getBoard());
        if (sharedImage == nullptr)
        {
            return;
        }

        // Add the icon to the level
        Entity *newEntity = new Entity(
            level->getBoard(),
            "icon",
            ENTITY_ICON,
            pos,
            icon.size,
            icon.data,
            NULL,           // sprite_left_data
            NULL,           // sprite_right_data
            NULL,           // start
            NULL,           // stop
            NULL,           // update
            NULL,           // render
            icon_collision, // collision
            true,           // is 8-bit
            true            // is progmem
        );
        // Assign the shared Image to the entity
        newEntity->sprite = sharedImage;

        // Add to level
        level->entity_add(newEntity);
    }

    static void icon_spawn_line(Level *level, const char *name, Vector pos, int amount, bool horizontal, int spacing = 17)
    {
        for (int i = 0; i < amount; i++)
        {
            Vector newPos = pos;
            if (horizontal)
                newPos.x += i * spacing;
            else
                newPos.y += i * spacing;

            icon_spawn(level, name, newPos);
        }
    }

    void icon_spawn_json(Level *level, const char *json)
    {
        // Check heap
        size_t freeHeap = rp2040.getFreeHeap();
        if (freeHeap < 1024)
        {
            return;
        }

        // Parse the json
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, json);

        // Check heap
        freeHeap = rp2040.getFreeHeap();
        if (freeHeap < 1024)
        {
            return;
        }

        // Check for errors
        if (error)
        {
            return;
        }

        // Loop through the json data
        int index = 0;
        while (doc["json_data"][index]["icon"])
        {
            const char *icon = doc["json_data"][index]["icon"];
            float x = doc["json_data"][index]["x"];
            float y = doc["json_data"][index]["y"];
            int amount = doc["json_data"][index]["amount"];
            bool horizontal = doc["json_data"][index]["horizontal"];

            // Check the amount
            if (amount > 1)
            {
                icon_spawn_line(level, icon, Vector(x, y), amount, horizontal);
            }
            else
            {
                icon_spawn(level, icon, Vector(x, y));
            }

            index++;
        }
    }
} // namespace FlipWorld