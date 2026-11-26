#include "game.hpp"
#include "pico-game-engine/engine/camera.hpp"
#include "pico-game-engine/engine/engine.hpp"
#include "pico-game-engine/engine/sprite3d.hpp"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include HTTP_INCLUDE
#include JSON_INCLUDE

#ifndef PICO_GTA_WS_PORT
#define PICO_GTA_WS_PORT 80
#endif

float PicoGTA::absoluteFloat(float value) const
{
    return value < 0.0f ? -value : value;
}

bool PicoGTA::addEntityToLevel(Level *level, Entity *entity) const
{
    if (!level || !entity)
        return false;
    const int oldCount = level->getEntityCount();
    level->entity_add(entity);
    if (level->getEntityCount() != oldCount + 1)
    {
        ENGINE_MEM_DELETE entity;
        return false;
    }
    return true;
}

bool PicoGTA::appendJsonQuoted(char *output, size_t capacity, size_t &position,
                               const char *text) const
{
    if (!output || !text || position >= capacity || capacity - position < 2)
        return false;
    output[position++] = '"';
    for (size_t i = 0; text[i]; ++i)
    {
        const unsigned char value = (unsigned char)text[i];
        if (value < 0x20)
            return false;
        if (value == '"' || value == '\\')
        {
            if (position + 2 >= capacity)
                return false;
            output[position++] = '\\';
        }
        else if (position + 1 >= capacity)
        {
            return false;
        }
        output[position++] = (char)value;
    }
    if (position + 1 >= capacity)
        return false;
    output[position++] = '"';
    output[position] = '\0';
    return true;
}

float PicoGTA::clampFloat(float value, float lower, float upper) const
{
    if (value < lower)
        return lower;
    if (value > upper)
        return upper;
    return value;
}

int PicoGTA::clampInt(int value, int lower, int upper) const
{
    if (value < lower)
        return lower;
    if (value > upper)
        return upper;
    return value;
}

bool PicoGTA::copyText(char *destination, size_t capacity, const char *source) const
{
    if (!destination || capacity == 0)
        return false;
    if (!source)
        source = "";

    size_t index = 0;
    while (index + 1 < capacity && source[index])
    {
        destination[index] = source[index];
        ++index;
    }
    destination[index] = '\0';
    return source[index] == '\0';
}

bool PicoGTA::getJsonInt(const char *key, const char *json, int &value) const
{
    char text[24];
    if (!getJsonString(key, json, text, sizeof(text)))
        return false;
    return parseDecimalInt(text, value);
}

bool PicoGTA::getJsonString(const char *key, const char *json, char *output,
                            size_t capacity) const
{
    if (!key || !json || !output || capacity == 0)
        return false;
    char *value = JSON_GET_VALUE(key, json);
    if (!value)
        return false;
    const bool copied = copyText(output, capacity, value);
    ENGINE_MEM_FREE(value);
    return copied;
}

void PicoGTA::getServerError(const char *json, char *error, size_t capacity)
{
    char value[96];
    if (getJsonString("error", json, value, sizeof(value)) &&
        value[0] && strcmp(value, "false") != 0 && strcmp(value, "null") != 0)
    {
        copyText(error, capacity, value);
    }
    else if (getJsonString("detail", json, value, sizeof(value)) && value[0])
    {
        copyText(error, capacity, value);
    }
}

bool PicoGTA::hasJsonObjectShape(const char *text) const
{
    if (!text)
        return false;
    while (*text == ' ' || *text == '\t' || *text == '\r' || *text == '\n')
        ++text;
    if (*text != '{')
        return false;
    const char *end = text + strlen(text);
    while (end > text && (end[-1] == ' ' || end[-1] == '\t' ||
                          end[-1] == '\r' || end[-1] == '\n'))
        --end;
    return end > text + 1 && end[-1] == '}';
}

float PicoGTA::maxFloat(float left, float right) const
{
    return left > right ? left : right;
}

float PicoGTA::minFloat(float left, float right) const
{
    return left < right ? left : right;
}

bool PicoGTA::packMultiplayerMessage(const char *playerId, const char *type,
                                     float x, float z, float headingValue, bool inCarState,
                                     char *output, size_t capacity) const
{
    if (!playerId || !type || !output || capacity == 0)
        return false;
    char xText[24];
    char zText[24];
    char headingText[24];
    if (!formatFloatAscii(xText, sizeof(xText), x) ||
        !formatFloatAscii(zText, sizeof(zText), z) ||
        !formatFloatAscii(headingText, sizeof(headingText), headingValue))
        return false;
    const int length = snprintf(output, capacity, "%s,%s,%s,%s,%s,%d",
                                playerId, type, xText, zText, headingText,
                                inCarState ? 1 : 0);
    return length > 0 && (size_t)length < capacity && length <= 160;
}

bool PicoGTA::parseDecimalInt(const char *text, int &value) const
{
    if (!text || !text[0])
        return false;
    int sign = 1;
    size_t index = 0;
    if (text[index] == '-')
    {
        sign = -1;
        ++index;
    }
    if (!text[index])
        return false;

    int result = 0;
    for (; text[index]; ++index)
    {
        if (text[index] < '0' || text[index] > '9')
            return false;
        const int digit = text[index] - '0';
        if (result > 1000000)
            return false;
        result = result * 10 + digit;
    }
    value = result * sign;
    return true;
}

bool PicoGTA::parseFloatAscii(const char *text, float &value) const
{
    if (!text || !text[0])
        return false;
    const size_t length = strlen(text);
    if (length > 16)
        return false;

    int sign = 1;
    size_t index = 0;
    if (text[index] == '-')
    {
        sign = -1;
        ++index;
    }
    if (index == length)
        return false;

    float integer = 0.0f;
    float fraction = 0.0f;
    float place = 0.1f;
    bool decimalSeen = false;
    bool digitSeen = false;
    for (; index < length; ++index)
    {
        const char character = text[index];
        if (character == '.' && !decimalSeen)
        {
            decimalSeen = true;
            continue;
        }
        if (character < '0' || character > '9')
            return false;
        digitSeen = true;
        const int digit = character - '0';
        if (decimalSeen)
        {
            fraction += digit * place;
            place *= 0.1f;
        }
        else
        {
            integer = integer * 10.0f + digit;
            if (integer > 1000000.0f)
                return false;
        }
    }
    if (!digitSeen)
        return false;
    value = sign * (integer + fraction);
    return true;
}

bool PicoGTA::parseMultiplayerMessage(const char *message,
                                      ParsedMultiplayerMessage &parsed) const
{
    if (!message)
        return false;
    const size_t length = strlen(message);
    if (length == 0 || length > 160)
        return false;

    char buffer[161];
    if (!copyText(buffer, sizeof(buffer), message))
        return false;
    char *fields[6] = {buffer, nullptr, nullptr, nullptr, nullptr, nullptr};
    int fieldCount = 1;
    for (size_t i = 0; i < length; ++i)
    {
        if (buffer[i] == ',')
        {
            if (fieldCount >= 6)
                return false;
            buffer[i] = '\0';
            fields[fieldCount++] = &buffer[i + 1];
        }
    }
    if (fieldCount != 6 || !fields[0][0] || strlen(fields[0]) > 100)
        return false;
    if (!copyText(parsed.playerId, sizeof(parsed.playerId), fields[0]))
        return false;

    if (strcmp(fields[1], "leave") == 0)
    {
        parsed.leave = true;
        parsed.x = 0.0f;
        parsed.z = 0.0f;
        parsed.heading = 0.0f;
        parsed.inCar = false;
        return true;
    }
    if (strcmp(fields[1], "state") != 0)
        return false;

    if (!parseFloatAscii(fields[2], parsed.x) ||
        !parseFloatAscii(fields[3], parsed.z) ||
        !parseFloatAscii(fields[4], parsed.heading))
        return false;
    if (strcmp(fields[5], "0") == 0)
        parsed.inCar = false;
    else if (strcmp(fields[5], "1") == 0)
        parsed.inCar = true;
    else
        return false;
    parsed.leave = false;
    return true;
}

bool PicoGTA::formatFloatAscii(char *output, size_t capacity, float value) const
{
    const uint32_t scale = 1000;
    const bool negative = value < 0.0f;
    const uint32_t scaled = (uint32_t)(absoluteFloat(value) * scale + 0.5f);
    const int length = snprintf(output, capacity, "%s%lu.%03lu",
                                negative && scaled ? "-" : "",
                                (unsigned long)(scaled / scale),
                                (unsigned long)(scaled % scale));
    return length > 0 && (size_t)length < capacity;
}

int PicoGTA::scaleX(Draw *canvas, float value) const
{
    if (!canvas)
        return (int)value;
    return (int)(value * canvas->getDisplaySize().x / 320.0f);
}

int PicoGTA::scaleY(Draw *canvas, float value) const
{
    if (!canvas)
        return (int)value;
    return (int)(value * canvas->getDisplaySize().y / 320.0f);
}

int PicoGTA::textWidth(Draw *canvas, const char *text) const
{
    if (!canvas || !text)
        return 0;
#ifdef ENGINE_FONT_STRING_WIDTH
    return (int)ENGINE_FONT_STRING_WIDTH(canvas->getCurrentFontSize(), text);
#else
    return (int)strlen(text) * 6;
#endif
}

int PicoGTA::fontHeight() const
{
#ifdef ENGINE_FONT_STRING_WIDTH
    return Font12.height;
#else
    return 8;
#endif
}

void PicoGTA::drawText(Draw *canvas, int x, int y, const char *text, uint16_t color) const
{
    if (!canvas || !text)
        return;
    const Vector size = canvas->getDisplaySize();
    x = clampInt(x, 0, (int)size.x);
    y = clampInt(y, 0, (int)size.y);
    canvas->text((uint16_t)x, (uint16_t)y, text, color);
}

void PicoGTA::drawCenteredText(Draw *canvas, int y, const char *text,
                               uint16_t color) const
{
    if (!canvas || !text)
        return;
    const int width = (int)canvas->getDisplaySize().x;
    drawText(canvas, (width - textWidth(canvas, text)) / 2, y, text, color);
}

void PicoGTA::drawFillRect(Draw *canvas, int x, int y, int width, int height,
                           uint16_t color) const
{
    if (!canvas || width <= 0 || height <= 0)
        return;
    const Vector size = canvas->getDisplaySize();
    if (x < 0)
    {
        width += x;
        x = 0;
    }
    if (y < 0)
    {
        height += y;
        y = 0;
    }
    if (x >= (int)size.x || y >= (int)size.y)
        return;
    if (x + width > (int)size.x)
        width = (int)size.x - x;
    if (y + height > (int)size.y)
        height = (int)size.y - y;
    if (width > 0 && height > 0)
        canvas->fillRectangle((uint16_t)x, (uint16_t)y, (uint16_t)width, (uint16_t)height, color);
}

void PicoGTA::drawOutlineRect(Draw *canvas, int x, int y, int width, int height,
                              uint16_t color) const
{
    if (!canvas || width <= 0 || height <= 0)
        return;
    const Vector size = canvas->getDisplaySize();
    x = clampInt(x, 0, (int)size.x);
    y = clampInt(y, 0, (int)size.y);
    width = clampInt(width, 0, (int)size.x - x);
    height = clampInt(height, 0, (int)size.y - y);
    if (width > 0 && height > 0)
        canvas->rectangle((uint16_t)x, (uint16_t)y, (uint16_t)width, (uint16_t)height, color);
}

PicoGTA::PicoGTA(const char *username, const char *password)
    : dayJustSwitched(true),
      draw(nullptr),
      engine(nullptr),
      frameClock(0),
      gameTime(nullptr),
      heading(cityPi * 0.5f),
      httpAction(REQUEST_NONE),
      httpRequestActive(false),
      inCar(false),
      inputPressed(false),
      isGameRunning(false),
      lastInput(-1),
      lastWalkKey(-1),
      landscape(),
      messageTimer(0),
      multiplayerConnectionState(CONNECTION_IDLE),
      multiplayerExitAfterLeave(false),
      multiplayerExitReady(false),
      multiplayerIdCounter(0),
      multiplayerLastSendFrame(0),
      multiplayerLobbyCount(0),
      multiplayerLobbyIndex(0),
      multiplayerMenuOriginTitle(false),
      multiplayerSelection(0),
      multiplayerView(VIEW_TITLE),
      player(nullptr),
      playerCar(nullptr),
      remotePlayerCount(0),
      shouldExit(false),
      speed(0.0f),
      steering(0.0f),
      walkAimPending(0.0f)
{
    multiplayerStatus[0] = '\0';
    multiplayerPlayerId[0] = '\0';
    multiplayerTargetLobbyId[0] = '\0';
    multiplayerLobbyId[0] = '\0';
    multiplayerLeaveNotice[0] = '\0';
    message[0] = '\0';
    for (int i = 0; i < TRAFFIC_COUNT; ++i)
        traffic[i] = nullptr;
    for (int i = 0; i < PERSON_COUNT; ++i)
    {
        people[i] = nullptr;
        peopleSpeeds[i] = 0.0f;
    }
    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        remotePlayers[i].active = false;
        remotePlayers[i].id[0] = '\0';
        remotePlayers[i].player = nullptr;
        remotePlayers[i].car = nullptr;
        remotePlayers[i].color = 0;
        remotePlayers[i].lastSeenFrame = 0;
    }
    for (int i = 0; i < MAX_LOBBIES; ++i)
    {
        multiplayerLobbies[i].id[0] = '\0';
        multiplayerLobbies[i].playerCount = 0;
        multiplayerLobbies[i].maxPlayers = 0;
    }

    player = ENGINE_MEM_NEW Player(username, password);
    if (!player)
    {
        ENGINE_LOG_INFO("[PicoGTA:PicoGTA] Failed to create Player instance\n");
        return;
    }
    player->setCity(this);

    gameTime = ENGINE_MEM_NEW Time();
    if (!gameTime)
    {
        ENGINE_LOG_INFO("[PicoGTA:PicoGTA] Failed to create Time instance\n");
        ENGINE_MEM_DELETE player;
        player = nullptr;
    }
}

PicoGTA::~PicoGTA()
{
    shouldExit = true;
    if (HTTP_WEBSOCKET_IS_CONNECTED())
        HTTP_WEBSOCKET_STOP();
    stopGame();
    if (player)
    {
        ENGINE_MEM_DELETE player;
        player = nullptr;
    }
    if (gameTime)
    {
        ENGINE_MEM_DELETE gameTime;
        gameTime = nullptr;
    }
    if (draw)
    {
        ENGINE_MEM_DELETE draw;
        draw = nullptr;
    }
}

Game *PicoGTA::getGame() const
{
    return engine ? engine->getGame() : nullptr;
}

void PicoGTA::endGame()
{
    shouldExit = true;
    isGameRunning = false;
}

bool PicoGTA::initDraw()
{
    if (!draw)
    {
        draw = ENGINE_MEM_NEW Draw();
        if (!draw)
        {
            ENGINE_LOG_INFO("[PicoGTA:initDraw] Failed to create Draw instance\n");
            return false;
        }
    }
    return true;
}

void PicoGTA::resetInput()
{
    lastInput = -1;
    lastWalkKey = -1;
    walkAimPending = 0.0f;
    inputPressed = false;
    if (engine)
        engine->updateGameInput(-1);
}

void PicoGTA::run()
{
    if (shouldExit)
        return;
    if (!draw && !initDraw())
    {
        endGame();
        return;
    }
    if (!engine && !startGame())
    {
        ENGINE_LOG_INFO("[PicoGTA:run] Failed to start game\n");
        endGame();
        return;
    }

    engine->runAsync(false, false);
    if (shouldExit)
        return;
    if (multiplayerView != VIEW_GAME)
        drawFullScreenMenu();
    else
        engine->render();
}

bool PicoGTA::startGame()
{
    if (engine)
        return true;
    if (!draw || !player)
        return false;

    Camera *camera = ENGINE_MEM_NEW Camera(
        Vector(0.0f, 0.0f), Vector(0.0f, 1.0f), Vector(-0.72f, 0.0f),
        2.2f, 8.2f, CAMERA_THIRD_PERSON);
    if (!camera)
        return false;

    Game *game = ENGINE_MEM_NEW Game(
        "Pico City", draw->getDisplaySize(), draw,
        Landscape::COLOR_LINE, Landscape::COLOR_SKY, camera);
    if (!game)
    {
        ENGINE_MEM_DELETE camera;
        return false;
    }

    auto failStart = [this, &game]() -> bool
    {
        landscape.release();
        ENGINE_MEM_DELETE game;
        game = nullptr;
        playerCar = nullptr;
        for (int i = 0; i < TRAFFIC_COUNT; ++i)
            traffic[i] = nullptr;
        for (int i = 0; i < PERSON_COUNT; ++i)
            people[i] = nullptr;
        isGameRunning = false;
        return false;
    };

    Level *level = ENGINE_MEM_NEW Level("Downtown", draw->getDisplaySize(), game);
    if (!level)
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to create city level\n");
        return failStart();
    }
    game->level_add(level);
    level->setLightDirection(-0.35f, 1.0f, -0.5f);
    level->setShadowColor(0);

    CallbackEntityDrawGame backgroundCallback;
    backgroundCallback.fn = &PicoGTA::backgroundRender;
    backgroundCallback.ctx = this;
    Entity *background = ENGINE_MEM_NEW Entity(
        "Background", ENTITY_3D_SPRITE, Vector(0.0f, 2000.0f), Vector(1.0f, 1.0f),
        nullptr, nullptr, nullptr, CallbackEntityGame(), CallbackEntityGame(),
        CallbackEntityGame(), backgroundCallback, CallbackEntityEntityGame(),
        false, SPRITE_3D_NONE, Landscape::COLOR_BLACK);
    if (!addEntityToLevel(level, background))
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to add background entity\n");
        return failStart();
    }

    if (!landscape.create(level))
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to create city landscape\n");
        return failStart();
    }

    player->setCity(this);
    player->position.x = Landscape::SIDEWALK_OFFSET;
    player->position.y = -10.0f;
    player->direction.x = 0.0f;
    player->direction.y = 1.0f;
    player->plane.x = -0.72f;
    player->plane.y = 0.0f;
    player->set3DSpriteRotation(0.0f);
    player->is_visible = true;
    const int oldPlayerCount = level->getEntityCount();
    level->entity_add(player);
    if (level->getEntityCount() != oldPlayerCount + 1)
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to add player to city level\n");
        return failStart();
    }

    playerCar = ENGINE_MEM_NEW Vehicle(
        this, "PlayerCar", Vector(Landscape::SIDEWALK_OFFSET, -10.0f),
        Landscape::COLOR_PLAYER, VEHICLE_PLAYER_CAR);
    if (!playerCar || !playerCar->sprite_3d)
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to create player car\n");
        return failStart();
    }
    playerCar->is_visible = false;
    if (!addEntityToLevel(level, playerCar))
    {
        playerCar = nullptr;
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to add player car\n");
        return failStart();
    }

    for (int i = 0; i < TRAFFIC_COUNT; ++i)
    {
        traffic[i] = ENGINE_MEM_NEW Vehicle(
            this, trafficNames[i], Vector(0.0f, 0.0f),
            carColors[i % 6], VEHICLE_TRAFFIC);
        if (!traffic[i] || !traffic[i]->sprite_3d)
        {
            ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to create traffic car\n");
            return failStart();
        }
        if (!addEntityToLevel(level, traffic[i]))
        {
            traffic[i] = nullptr;
            ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to add traffic car\n");
            return failStart();
        }
        spawnTraffic(i);
    }

    for (int i = 0; i < PERSON_COUNT; ++i)
    {
        peopleSpeeds[i] = 0.020f + (i % 4) * 0.004f;
        people[i] = ENGINE_MEM_NEW Pedestrian(
            this, i, personNames[i], Vector(0.0f, 0.0f), personColors[i]);
        if (!people[i] || !people[i]->has3DSprite())
        {
            ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to create pedestrian\n");
            return failStart();
        }
        people[i]->setWalkSpeed(peopleSpeeds[i]);
        if (!addEntityToLevel(level, people[i]))
        {
            people[i] = nullptr;
            ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to add pedestrian\n");
            return failStart();
        }
        spawnPerson(i);
    }

    landscape.buildAround(player->position.x, player->position.y);
    if (landscape.hasGeometryError())
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] City geometry could not be built completely\n");
        return failStart();
    }

    engine = ENGINE_MEM_NEW GameEngine(game, 30.0f);
    if (!engine)
    {
        ENGINE_LOG_INFO("[PicoGTA:startGame] Failed to create game engine\n");
        return failStart();
    }
    inCar = false;
    speed = 0.0f;
    heading = cityPi * 0.5f;
    isGameRunning = true;
    return true;
}

void PicoGTA::stopGame()
{
    removeAllRemotePlayers();
    if (engine)
    {
        landscape.release();
        engine->stop();
        ENGINE_MEM_DELETE engine;
        engine = nullptr;
    }
    landscape.release();
    playerCar = nullptr;
    for (int i = 0; i < TRAFFIC_COUNT; ++i)
        traffic[i] = nullptr;
    for (int i = 0; i < PERSON_COUNT; ++i)
        people[i] = nullptr;
    if (player)
    {
        player->is_active = false;
        player->is_visible = true;
    }
    inCar = false;
    speed = 0.0f;
    isGameRunning = false;
}

void PicoGTA::update()
{
    if (!engine || getGame() == nullptr || !draw || shouldExit)
        return;

    int key = getGame()->input;

    if (key < 0)
    {
        lastInput = -1;
        inputPressed = false;
    }
    else
    {
        lastInput = key;
        inputPressed = true;
    }

    if (gameTime)
        gameTime->tick();
    ++frameClock;

    pollMultiplayerHttp();
    pollMultiplayerWebSocket();
    updateMultiplayer();
    if (multiplayerExitReady)
    {
        multiplayerExitReady = false;
        endGame();
        return;
    }

    if (multiplayerView != VIEW_GAME)
    {
        handleMenuInput();
        ENGINE_DELAY_MS(33);
        resetInput();
        return;
    }

    if (wasInputPressed(INPUT_KEY_BACK))
    {
        multiplayerMenuOriginTitle = false;
        multiplayerView = VIEW_MENU;
        multiplayerSelection = 0;
        ENGINE_DELAY_MS(33);
        resetInput();
        return;
    }

    if (!engine)
    {
        multiplayerView = VIEW_TITLE;
        multiplayerSelection = 0;
        ENGINE_DELAY_MS(33);
        resetInput();
        return;
    }

    updateMultiplayer();
}

void PicoGTA::backgroundRender(Entity *entity, Draw *canvas, Game *game, void *context)
{
    (void)entity;
    (void)game;
    PicoGTA *city = (PicoGTA *)context;
    if (city)
        city->drawBackground(canvas);
}

bool PicoGTA::carBlocked(float x, float z, int skipIndex) const
{
    for (int i = 0; i < TRAFFIC_COUNT; ++i)
    {
        Vehicle *car = traffic[i];
        if (i == skipIndex || !car || !car->is_visible)
            continue;
        if (absoluteFloat(x - car->position.x) < 1.05f &&
            absoluteFloat(z - car->position.y) < 1.85f)
            return true;
    }

    if (skipIndex < TRAFFIC_COUNT && player &&
        absoluteFloat(x - player->position.x) < 1.05f &&
        absoluteFloat(z - player->position.y) < 1.85f)
        return true;

    for (int i = 0; i < PERSON_COUNT; ++i)
    {
        Pedestrian *person = people[i];
        if (!person || !person->is_visible)
            continue;
        if (absoluteFloat(x - person->position.x) < 0.825f &&
            absoluteFloat(z - person->position.y) < 1.675f)
            return true;
    }
    return false;
}

bool PicoGTA::personBlocked(float x, float z, int skipIndex) const
{
    for (int i = 0; i < PERSON_COUNT; ++i)
    {
        Pedestrian *person = people[i];
        if (i == skipIndex || !person || !person->is_visible)
            continue;
        if (absoluteFloat(x - person->position.x) < 0.55f &&
            absoluteFloat(z - person->position.y) < 0.75f)
            return true;
    }

    for (int i = 0; i < TRAFFIC_COUNT; ++i)
    {
        Vehicle *car = traffic[i];
        if (!car || !car->is_visible)
            continue;
        if (absoluteFloat(x - car->position.x) < 0.95f &&
            absoluteFloat(z - car->position.y) < 1.30f)
            return true;
    }

    if (player &&
        absoluteFloat(x - player->position.x) < 0.55f &&
        absoluteFloat(z - player->position.y) < 0.75f)
        return true;

    if (playerCar && playerCar->is_visible &&
        absoluteFloat(x - playerCar->position.x) < 0.95f &&
        absoluteFloat(z - playerCar->position.y) < 1.30f)
        return true;

    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        Vehicle *car = remotePlayers[i].car;
        if (!remotePlayers[i].active || !car || !car->is_visible)
            continue;
        if (absoluteFloat(x - car->position.x) < 0.95f &&
            absoluteFloat(z - car->position.y) < 1.30f)
            return true;
    }
    return false;
}

void PicoGTA::spawnTraffic(int index)
{
    if (index < 0 || index >= TRAFFIC_COUNT || !traffic[index] || !player)
        return;

    int axis = 0;
    int line = 0;
    int direction = 1;
    float x = 0.0f;
    float z = 0.0f;
    for (int attempt = 0; attempt < 10; ++attempt)
    {
        axis = (int)cityMap.nextRandom(2);
        line = (int)cityMap.nextRandom((CITY_GRID_LIMIT - 1) * 2 + 1) - (CITY_GRID_LIMIT - 1);
        direction = cityMap.nextRandom(2) == 0 ? 1 : -1;
        const float lane = direction == 1 ? -trafficOffset : trafficOffset;
        if (axis == 0)
        {
            x = line * Landscape::ROAD_SPACING + lane;
            z = player->position.y + (float)cityMap.nextRandom(41) - 20.0f;
        }
        else
        {
            x = player->position.x + (float)cityMap.nextRandom(41) - 20.0f;
            z = line * Landscape::ROAD_SPACING + lane;
        }
        if (!carBlocked(x, z, index))
            break;
    }

    const float edge = Landscape::WORLD_HALF - 4.0f;
    float tx = 0.0f;
    float tz = 0.0f;
    if (axis == 0)
    {
        int j = (int)(direction == 1 ? ceilf(z / Landscape::ROAD_SPACING)
                                     : floorf(z / Landscape::ROAD_SPACING));
        tz = j * Landscape::ROAD_SPACING;
        if (tz < -edge || tz > edge)
        {
            direction = -direction;
            const float lane = direction == 1 ? -trafficOffset : trafficOffset;
            x = line * Landscape::ROAD_SPACING + lane;
            j = (int)(direction == 1 ? ceilf(z / Landscape::ROAD_SPACING)
                                     : floorf(z / Landscape::ROAD_SPACING));
            tz = j * Landscape::ROAD_SPACING;
        }
        tx = x;
    }
    else
    {
        int i = (int)(direction == 1 ? ceilf(x / Landscape::ROAD_SPACING)
                                     : floorf(x / Landscape::ROAD_SPACING));
        tx = i * Landscape::ROAD_SPACING;
        if (tx < -edge || tx > edge)
        {
            direction = -direction;
            const float lane = direction == 1 ? -trafficOffset : trafficOffset;
            z = line * Landscape::ROAD_SPACING + lane;
            i = (int)(direction == 1 ? ceilf(x / Landscape::ROAD_SPACING)
                                     : floorf(x / Landscape::ROAD_SPACING));
            tx = i * Landscape::ROAD_SPACING;
        }
        tz = z;
    }
    x = clampFloat(x, -edge, edge);
    z = clampFloat(z, -edge, edge);
    traffic[index]->setTrafficState(index, axis, line, direction, trafficSpeed);
    traffic[index]->position_set(x, z);
    traffic[index]->setTarget(tx, tz);
    traffic[index]->setTurnCount(0);
    traffic[index]->is_visible = true;
}

void PicoGTA::spawnPerson(int index)
{
    if (index < 0 || index >= PERSON_COUNT || !people[index] || !player)
        return;

    Pedestrian *person = people[index];
    const float offset = (float)cityMap.nextRandom(41) - 20.0f;
    float along = cityMap.nextRandom(2) == 0 ? -1.0f : 1.0f;
    const int roll = (int)cityMap.nextRandom(4);
    const float edge = Landscape::WORLD_HALF - 4.0f;
    float x = 0.0f;
    float z = 0.0f;
    if (roll < 2)
    {
        const int line = cityMap.gridIndex(player->position.x, Landscape::ROAD_SPACING,
                                           CITY_GRID_LIMIT);
        x = line * Landscape::ROAD_SPACING +
            (roll == 0 ? -Landscape::SIDEWALK_OFFSET : Landscape::SIDEWALK_OFFSET);
        z = player->position.y + offset;
        int j = (int)(along > 0.0f ? ceilf(z / Landscape::ROAD_SPACING)
                                   : floorf(z / Landscape::ROAD_SPACING));
        float tz = j * Landscape::ROAD_SPACING;
        if (tz < -edge || tz > edge)
        {
            along = -along;
            j = (int)(along > 0.0f ? ceilf(z / Landscape::ROAD_SPACING)
                                   : floorf(z / Landscape::ROAD_SPACING));
            tz = j * Landscape::ROAD_SPACING;
        }
        person->setDirection(0.0f, along);
        person->setTarget(x, tz);
    }
    else
    {
        const int line = cityMap.gridIndex(player->position.y, Landscape::ROAD_SPACING,
                                           CITY_GRID_LIMIT);
        z = line * Landscape::ROAD_SPACING +
            (roll == 2 ? -Landscape::SIDEWALK_OFFSET : Landscape::SIDEWALK_OFFSET);
        x = player->position.x + offset;
        int i = (int)(along > 0.0f ? ceilf(x / Landscape::ROAD_SPACING)
                                   : floorf(x / Landscape::ROAD_SPACING));
        float tx = i * Landscape::ROAD_SPACING;
        if (tx < -edge || tx > edge)
        {
            along = -along;
            i = (int)(along > 0.0f ? ceilf(x / Landscape::ROAD_SPACING)
                                   : floorf(x / Landscape::ROAD_SPACING));
            tx = i * Landscape::ROAD_SPACING;
        }
        person->setDirection(along, 0.0f);
        person->setTarget(tx, z);
    }

    x = clampFloat(x, -edge, edge);
    z = clampFloat(z, -edge, edge);
    person->position_set(x, z);
    person->setLeg(0);
    person->setTurnCount(0);
    person->set3DSpriteRotation(
        atan2f(person->getDirectionZ(), person->getDirectionX()) - cityPi * 0.5f);
    person->is_visible = true;
}

void PicoGTA::updatePlayer(Player *activePlayer, Game *game)
{
    if (!activePlayer || !game || multiplayerView != VIEW_GAME)
        return;

    updateMessage();
    if (wasInputPressed(INPUT_KEY_CENTER))
        toggleCar(activePlayer);
    if (inCar)
        driveCar(activePlayer, game);
    else
        walkPlayer(activePlayer, game);
    landscape.update(activePlayer);
}

void PicoGTA::walkPlayer(Player *activePlayer, Game *game)
{
    const int input = game->input;
    // Engine camera follows player direction as heading
    float aim_x = activePlayer->direction.x;
    float aim_y = activePlayer->direction.y;
    float aim_length = sqrtf(aim_x * aim_x + aim_y * aim_y);
    if (aim_length >= 0.001f)
    {
        aim_x /= aim_length;
        aim_y /= aim_length;
    }
    else
    {
        aim_x = 0.0f;
        aim_y = 1.0f;
    }

    const int prevWalkKey = lastWalkKey;
    lastWalkKey = input;

    // One rotation queued per key press
    if (input == INPUT_KEY_LEFT && prevWalkKey != INPUT_KEY_LEFT)
        walkAimPending += walkTurn;
    else if (input == INPUT_KEY_RIGHT && prevWalkKey != INPUT_KEY_RIGHT)
        walkAimPending -= walkTurn;

    // Ease rotation, keep pace with movement
    float delta = walkAimPending * turnLerp;
    walkAimPending -= delta;
    if (delta != 0.0f)
    {
        float cos_delta = cosf(delta);
        float sin_delta = sinf(delta);
        float new_x = aim_x * cos_delta + aim_y * sin_delta;
        float new_y = -aim_x * sin_delta + aim_y * cos_delta;
        activePlayer->direction.x = new_x;
        activePlayer->direction.y = new_y;
        aim_x = new_x;
        aim_y = new_y;
    }

    float move_x = 0.0f;
    float move_y = 0.0f;
    if (input == INPUT_KEY_UP)
    {
        move_x = aim_x;
        move_y = aim_y;
    }
    else if (input == INPUT_KEY_DOWN)
    {
        move_x = -aim_x;
        move_y = -aim_y;
    }
    else if (input == INPUT_KEY_LEFT)
    {
        // Walk screen-left, perpendicular to aim
        move_x = aim_y;
        move_y = -aim_x;
    }
    else if (input == INPUT_KEY_RIGHT)
    {
        // Walk screen-right, perpendicular to aim
        move_x = -aim_y;
        move_y = aim_x;
    }
    if (move_x != 0.0f || move_y != 0.0f)
    {
        speed = minFloat(walkSpeed, speed + walkAccel);
        // Ease heading toward move direction
        float targetHeading = atan2f(move_y, move_x);
        float deltaH = targetHeading - heading;
        while (deltaH > cityPi)
            deltaH -= cityPi * 2.0f;
        while (deltaH < -cityPi)
            deltaH += cityPi * 2.0f;
        heading += deltaH * turnLerp;
    }
    else
    {
        if (speed > 0.0f)
            speed = maxFloat(0.0f, speed - walkFriction);
        else
            speed = minFloat(0.0f, speed + walkFriction);
    }

    const float dx = cosf(heading);
    const float dz = sinf(heading);
    const float oldX = activePlayer->position.x;
    const float oldZ = activePlayer->position.y;
    const float nextX = oldX + dx * speed;
    const float nextZ = oldZ + dz * speed;
    if (!landscape.blocked(nextX, nextZ, false) &&
        !carBlocked(nextX, nextZ, TRAFFIC_COUNT))
    {
        activePlayer->position_set(nextX, nextZ);
    }
    else
    {
        if (!landscape.blocked(nextX, oldZ, false) &&
            !carBlocked(nextX, oldZ, TRAFFIC_COUNT))
            activePlayer->position_set(nextX, oldZ);
        else if (!landscape.blocked(oldX, nextZ, false) &&
                 !carBlocked(oldX, nextZ, TRAFFIC_COUNT))
            activePlayer->position_set(oldX, nextZ);
        speed *= 0.25f;
    }

    // Player direction drives the camera heading
    activePlayer->direction.x = aim_x;
    activePlayer->direction.y = aim_y;
    activePlayer->set3DSpriteRotation(atan2f(dz, dx) - cityPi * 0.5f);
    updateCameraDistance();
}

void PicoGTA::driveCar(Player *activePlayer, Game *game)
{
    const int input = game->input;
    // Engine camera follows player direction as heading
    float aim_x = activePlayer->direction.x;
    float aim_y = activePlayer->direction.y;
    float aim_length = sqrtf(aim_x * aim_x + aim_y * aim_y);
    if (aim_length >= 0.001f)
    {
        aim_x /= aim_length;
        aim_y /= aim_length;
    }
    else
    {
        aim_x = 0.0f;
        aim_y = 1.0f;
    }

    const int prevWalkKey = lastWalkKey;
    lastWalkKey = input;

    // One rotation queued per key press
    if (input == INPUT_KEY_LEFT && prevWalkKey != INPUT_KEY_LEFT)
        walkAimPending += walkTurn;
    else if (input == INPUT_KEY_RIGHT && prevWalkKey != INPUT_KEY_RIGHT)
        walkAimPending -= walkTurn;

    // Ease rotation, keep pace with movement
    float delta = walkAimPending * turnLerp;
    walkAimPending -= delta;
    if (delta != 0.0f)
    {
        float cos_delta = cosf(delta);
        float sin_delta = sinf(delta);
        float new_x = aim_x * cos_delta + aim_y * sin_delta;
        float new_y = -aim_x * sin_delta + aim_y * cos_delta;
        activePlayer->direction.x = new_x;
        activePlayer->direction.y = new_y;
        aim_x = new_x;
        aim_y = new_y;
    }

    if (input == INPUT_KEY_UP)
        speed += carAccel;
    else if (input == INPUT_KEY_DOWN)
        speed -= carBrake;
    else if (speed > 0.0f)
        speed = maxFloat(0.0f, speed - carFriction);
    else
        speed = minFloat(0.0f, speed + carFriction);

    // Ease heading toward camera aim
    float targetHeading = atan2f(aim_y, aim_x);
    float deltaH = targetHeading - heading;
    while (deltaH > cityPi)
        deltaH -= cityPi * 2.0f;
    while (deltaH < -cityPi)
        deltaH += cityPi * 2.0f;
    heading += deltaH * turnLerp;
    speed = clampFloat(speed, carMaxReverse, carMaxSpeed);
    const float dx = cosf(heading);
    const float dz = sinf(heading);
    const float oldX = activePlayer->position.x;
    const float oldZ = activePlayer->position.y;
    const float nextX = oldX + dx * speed;
    const float nextZ = oldZ + dz * speed;
    if (!landscape.blocked(nextX, nextZ, true) &&
        !carBlocked(nextX, nextZ, TRAFFIC_COUNT))
    {
        activePlayer->position_set(nextX, nextZ);
    }
    else
    {
        if (!landscape.blocked(nextX, oldZ, true) &&
            !carBlocked(nextX, oldZ, TRAFFIC_COUNT))
            activePlayer->position_set(nextX, oldZ);
        else if (!landscape.blocked(oldX, nextZ, true) &&
                 !carBlocked(oldX, nextZ, TRAFFIC_COUNT))
            activePlayer->position_set(oldX, nextZ);
        speed *= 0.25f;
    }

    // Player direction drives the camera heading
    activePlayer->direction.x = aim_x;
    activePlayer->direction.y = aim_y;
    activePlayer->plane.x = -0.72f;
    activePlayer->plane.y = 0.0f;
    activePlayer->set3DSpriteRotation(atan2f(dz, dx) - cityPi * 0.5f);
    syncPlayerCar(activePlayer);
    updateCameraDistance();
}

void PicoGTA::toggleCar(Player *activePlayer)
{
    if (!activePlayer || !playerCar)
        return;
    if (inCar)
    {
        inCar = false;
        speed = 0.0f;
        activePlayer->is_visible = true;
        activePlayer->set3DSpriteRotation(
            atan2f(sinf(heading), cosf(heading)) - cityPi * 0.5f);
        playerCar->is_visible = false;
        setMessage("Walk mode", 60);
    }
    else
    {
        inCar = true;
        speed = 0.0f;
        activePlayer->is_visible = false;
        playerCar->is_visible = true;
        setMessage("Drive mode", 60);
    }
}

void PicoGTA::syncPlayerCar(Player *activePlayer)
{
    if (!activePlayer || !playerCar)
        return;
    const float dx = cosf(heading);
    const float dz = sinf(heading);
    playerCar->position.x = activePlayer->position.x;
    playerCar->position.y = activePlayer->position.y;
    playerCar->direction.x = dx;
    playerCar->direction.y = dz;
    playerCar->plane.x = -0.72f;
    playerCar->plane.y = 0.0f;
    playerCar->set3DSpriteRotation(atan2f(dz, dx) - cityPi * 0.5f);
}

void PicoGTA::updateCameraDistance()
{
    Game *game = getGame();
    if (!game || !player || !game->getCamera())
        return;
    game->getCamera()->distance =
        landscape.insideBuilding(player->position.x, player->position.y)
            ? cameraIndoorDistance
            : cameraDistance;
}

void PicoGTA::updateTraffic(Vehicle *car)
{
    if (!car || !player)
        return;
    const int index = car->getTrafficIndex();
    if (index < 0 || index >= TRAFFIC_COUNT)
        return;

    int axis = car->getTrafficAxis();
    int direction = car->getTrafficDirection();
    const float trafficSpeed = car->getTrafficSpeed();
    // exact axis vectors; no float epsilon in reached checks
    float dx, dz;
    if (axis == 0)
        dx = 0.0f, dz = direction == 1 ? 1.0f : -1.0f;
    else
        dx = direction == 1 ? 1.0f : -1.0f, dz = 0.0f;
    const float oldX = car->position.x;
    const float oldZ = car->position.y;
    float nextX = oldX + dx * trafficSpeed;
    float nextZ = oldZ + dz * trafficSpeed;
    if (!landscape.blocked(nextX, nextZ, true) && !carBlocked(nextX, nextZ, index))
    {
        car->position_set(nextX, nextZ);
    }
    else
    {
        direction = -direction;
        if (axis == 0)
            dx = 0.0f, dz = direction == 1 ? 1.0f : -1.0f;
        else
            dx = direction == 1 ? 1.0f : -1.0f, dz = 0.0f;
        nextX = oldX + dx * trafficSpeed;
        nextZ = oldZ + dz * trafficSpeed;
        car->position_set(nextX, nextZ);
        // target the intersection behind in the new direction
        const float spacing = Landscape::ROAD_SPACING;
        if (axis == 0)
        {
            const int j = (int)(direction == 1
                                    ? ceilf(nextZ / spacing)
                                    : floorf(nextZ / spacing));
            car->setTarget(nextX, j * spacing);
        }
        else
        {
            const int i = (int)(direction == 1
                                    ? ceilf(nextX / spacing)
                                    : floorf(nextX / spacing));
            car->setTarget(i * spacing, nextZ);
        }
    }

    const float tx = car->end_position.x;
    const float tz = car->end_position.y;
    const bool reached =
        (dx > 0.0f && nextX >= tx) || (dx < 0.0f && nextX <= tx) ||
        (dz > 0.0f && nextZ >= tz) || (dz < 0.0f && nextZ <= tz);

    if (reached)
    {
        const float edge = Landscape::WORLD_HALF - 4.0f;
        const float spacing = Landscape::ROAD_SPACING;
        int newAxis = axis;
        int newDirection = direction;
        int newLine = car->getTrafficLine();
        float nx = nextX;
        float nz = nextZ;
        if (axis == 0)
        {
            // at intersection; pick next leg for this car
            const int v = car->getTrafficLine();
            const int j = (int)(nextZ / spacing + (nextZ > 0.0f ? 0.5f : -0.5f));
            const uint32_t roll = cityMap.cellHash(index, car->getTurnCount(), 5);
            const int choice = (int)(roll % 4);
            if (choice == 0 || choice == 1)
            {
                const int ahead = choice == 0 ? direction : -direction;
                nz = (j + ahead) * spacing;
                nx = v * spacing + (ahead == 1 ? -trafficOffset : trafficOffset);
                newDirection = ahead;
                if (nz < -edge || nz > edge)
                {
                    newDirection = -direction;
                    nz = (j - direction) * spacing;
                    nx = v * spacing + (newDirection == 1 ? -trafficOffset : trafficOffset);
                }
            }
            else
            {
                // turn: switch to perpendicular road
                int ndir = choice == 2 ? (direction == 1 ? 1 : -1)
                                       : (direction == 1 ? -1 : 1);
                nx = (v + ndir) * spacing;
                nz = j * spacing + (ndir == 1 ? -trafficOffset : trafficOffset);
                if (nx < -edge || nx > edge)
                {
                    ndir = -ndir;
                    nx = (v + ndir) * spacing;
                    nz = j * spacing + (ndir == 1 ? -trafficOffset : trafficOffset);
                }
                newAxis = 1;
                newLine = j;
                newDirection = ndir;
            }
        }
        else
        {
            // at intersection; pick next leg for this car
            const int v = car->getTrafficLine();
            const int i = (int)(nextX / spacing + (nextX > 0.0f ? 0.5f : -0.5f));
            const uint32_t roll = cityMap.cellHash(index, car->getTurnCount(), 11);
            const int choice = (int)(roll % 4);
            if (choice == 0 || choice == 1)
            {
                const int ahead = choice == 0 ? direction : -direction;
                nx = (i + ahead) * spacing;
                nz = v * spacing + (ahead == 1 ? -trafficOffset : trafficOffset);
                newDirection = ahead;
                if (nx < -edge || nx > edge)
                {
                    newDirection = -direction;
                    nx = (i - direction) * spacing;
                    nz = v * spacing + (newDirection == 1 ? -trafficOffset : trafficOffset);
                }
            }
            else
            {
                // turn: switch to perpendicular road
                int ndir = choice == 2 ? (direction == 1 ? 1 : -1)
                                       : (direction == 1 ? -1 : 1);
                nx = i * spacing + (ndir == 1 ? -trafficOffset : trafficOffset);
                nz = (v + ndir) * spacing;
                if (nx < -edge || nx > edge)
                {
                    ndir = -ndir;
                    nx = i * spacing + (ndir == 1 ? -trafficOffset : trafficOffset);
                    nz = (v + ndir) * spacing;
                }
                newAxis = 0;
                newLine = i;
                newDirection = ndir;
            }
        }

        car->setTrafficState(index, newAxis, newLine, newDirection, trafficSpeed);
        car->setTarget(nx, nz);
        car->setTurnCount(car->getTurnCount() + 1);
        axis = newAxis;
        direction = newDirection;
        if (axis == 0)
            dx = 0.0f, dz = direction == 1 ? 1.0f : -1.0f;
        else
            dx = direction == 1 ? 1.0f : -1.0f, dz = 0.0f;
    }

    car->setTrafficState(index, axis, car->getTrafficLine(), direction, trafficSpeed);
    car->direction.x = dx;
    car->direction.y = dz;
    car->plane.x = -0.72f;
    car->plane.y = 0.0f;
    car->set3DSpriteRotation(atan2f(dz, dx) - cityPi * 0.5f);

    const float offsetX = absoluteFloat(car->position.x - player->position.x);
    const float offsetZ = absoluteFloat(car->position.y - player->position.y);
    const float edge = Landscape::WORLD_HALF - 4.0f;
    if (offsetX > recycleDistance || offsetZ > recycleDistance ||
        car->position.x < -edge || car->position.x > edge ||
        car->position.y < -edge || car->position.y > edge)
    {
        spawnTraffic(index);
    }
    else if (offsetX > Landscape::CITY_FIELD_OF_VIEW + 8.0f ||
             offsetZ > Landscape::CITY_FIELD_OF_VIEW + 8.0f)
    {
        car->is_visible = false;
    }
    else
    {
        car->is_visible = true;
    }
}

void PicoGTA::updatePerson(Pedestrian *person)
{
    if (!person || !player)
        return;
    const int index = person->getIndex();
    if (index < 0 || index >= PERSON_COUNT)
        return;

    float directionX = person->getDirectionX();
    float directionZ = person->getDirectionZ();
    const float x = person->position.x + directionX * person->getWalkSpeed();
    const float z = person->position.y + directionZ * person->getWalkSpeed();

    const float tx = person->end_position.x;
    const float tz = person->end_position.y;
    const bool reached =
        (directionX > 0.0f && x >= tx) || (directionX < 0.0f && x <= tx) ||
        (directionZ > 0.0f && z >= tz) || (directionZ < 0.0f && z <= tz);

    if (reached)
    {
        float ndx = directionX;
        float ndz = directionZ;
        float nx = x;
        float nz = z;
        int nleg = 0;
        const float edge = Landscape::WORLD_HALF - 4.0f;
        const float spacing = Landscape::ROAD_SPACING;
        if (person->getLeg() == 1)
        {
            // crossing leg finished; begin new walking leg
            const int side = (int)(cityMap.cellHash(index, person->getTurnCount(), 9) % 2) == 0
                                 ? -1
                                 : 1;
            if (directionZ != 0.0f)
            {
                const int v = (int)(x / spacing + (x > 0.0f ? 0.5f : -0.5f));
                ndx = (float)side;
                ndz = 0.0f;
                nx = (v + side) * spacing;
            }
            else
            {
                const int w = (int)(z / spacing + (z > 0.0f ? 0.5f : -0.5f));
                ndz = (float)side;
                ndx = 0.0f;
                nz = (w + side) * spacing;
            }
            if (nx < -edge || nx > edge || nz < -edge || nz > edge)
            {
                ndx = -ndx;
                ndz = -ndz;
                if (directionZ != 0.0f)
                {
                    const int v = (int)(x / spacing + (x > 0.0f ? 0.5f : -0.5f));
                    nx = (v - side) * spacing;
                }
                else
                {
                    const int w = (int)(z / spacing + (z > 0.0f ? 0.5f : -0.5f));
                    nz = (w - side) * spacing;
                }
            }
        }
        else if (directionZ != 0.0f)
        {
            // reached intersection; pick next leg for this person
            const uint32_t roll = cityMap.cellHash(index, person->getTurnCount(), 5);
            const int choice = (int)(roll % 4);
            const int w = (int)(z / spacing + (z > 0.0f ? 0.5f : -0.5f));
            if (choice == 1 || choice == 2)
            {
                // turn: cross to perpendicular sidewalk
                const int side = choice == 1 ? 1 : -1;
                ndz = (float)side;
                nz = w * spacing + side * Landscape::SIDEWALK_OFFSET;
                nleg = 1;
            }
            else
            {
                const int ahead = choice == 0 ? (int)directionZ : -(int)directionZ;
                ndz = (float)ahead;
                nz = (w + ahead) * spacing;
                if (nz < -edge || nz > edge)
                {
                    ndz = -directionZ;
                    nz = (w - (int)directionZ) * spacing;
                }
            }
        }
        else
        {
            // reached intersection; pick next leg for this person
            const uint32_t roll = cityMap.cellHash(index, person->getTurnCount(), 11);
            const int choice = (int)(roll % 4);
            const int v = (int)(x / spacing + (x > 0.0f ? 0.5f : -0.5f));
            if (choice == 1 || choice == 2)
            {
                // turn: cross to perpendicular sidewalk
                const int side = choice == 1 ? 1 : -1;
                ndx = (float)side;
                ndz = 0.0f;
                nx = v * spacing + side * Landscape::SIDEWALK_OFFSET;
                nleg = 1;
            }
            else
            {
                const int ahead = choice == 0 ? (int)directionX : -(int)directionX;
                ndx = (float)ahead;
                nx = (v + ahead) * spacing;
                if (nx < -edge || nx > edge)
                {
                    ndx = -directionX;
                    nx = (v - (int)directionX) * spacing;
                }
            }
        }

        person->setDirection(ndx, ndz);
        person->setTarget(nx, nz);
        person->setLeg(nleg);
        person->setTurnCount(person->getTurnCount() + 1);
        person->set3DSpriteRotation(atan2f(ndz, ndx) - cityPi * 0.5f);
    }

    if (landscape.blocked(x, z, false) || personBlocked(x, z, index))
    {
        person->keepOnSidewalk();
        return;
    }

    person->position_set(x, z);

    const float offsetX = absoluteFloat(x - player->position.x);
    const float offsetZ = absoluteFloat(z - player->position.y);
    const float edge = Landscape::WORLD_HALF - 4.0f;
    if (offsetX > recycleDistance || offsetZ > recycleDistance ||
        x < -edge || x > edge || z < -edge || z > edge)
    {
        spawnPerson(index);
        return;
    }
    if (offsetX > Landscape::CITY_FIELD_OF_VIEW + 8.0f ||
        offsetZ > Landscape::CITY_FIELD_OF_VIEW + 8.0f)
    {
        person->is_visible = false;
        return;
    }
    person->is_visible =
        !landscape.crossesBuilding(player->position.x, player->position.y, x, z);
}

void PicoGTA::updateMessage()
{
    if (messageTimer > 0)
    {
        --messageTimer;
        if (messageTimer == 0)
            message[0] = '\0';
    }
}

void PicoGTA::setMessage(const char *text, int frames)
{
    copyText(message, sizeof(message), text);
    messageTimer = frames > 0 ? frames : 0;
}

void PicoGTA::drawBackground(Draw *canvas)
{
    if (!canvas)
        return;
    const Vector size = canvas->getDisplaySize();
    const int width = (int)size.x;
    const int height = (int)size.y;
    const int horizon = (int)(height * 0.52f);
    const int roofBand = scaleY(canvas, 2.0f);
    drawFillRect(canvas, 0, 0, width, horizon, Landscape::COLOR_SKY);
    drawFillRect(canvas, 0, horizon, width, height - horizon, Landscape::COLOR_GROUND);
    drawFillRect(canvas, 0, horizon - roofBand, width, roofBand, Landscape::COLOR_ROOF);
}

void PicoGTA::drawHud(Draw *canvas)
{
    if (!canvas || !engine || !player)
        return;
    const Vector size = canvas->getDisplaySize();
    const int width = (int)size.x;

    if (messageTimer > 0 && message[0])
    {
        const int x = width / 2 - scaleX(canvas, (float)textWidth(canvas, message) / 2.0f);
        const int y = (int)size.y / 2 - scaleY(canvas, 4.0f);
        drawText(canvas, x, y, message, Landscape::COLOR_LINE);
    }

    drawMinimap(canvas);
    if (multiplayerConnectionState == CONNECTION_ACTIVE)
    {
        char label[32];
        snprintf(label, sizeof(label), "ONLINE %d", remotePlayerCount + 1);
        drawText(canvas, scaleX(canvas, 3.0f), scaleY(canvas, 19.0f), label,
                 Landscape::COLOR_LINE);
    }
}

void PicoGTA::drawMinimap(Draw *canvas)
{
    if (!canvas || !player)
        return;
    const Vector screen = canvas->getDisplaySize();
    const int width = (int)screen.x;
    const int size = scaleY(canvas, minimapSize);
    if (size <= 0)
        return;
    const int left = width - size - scaleX(canvas, 3.0f);
    const int top = scaleY(canvas, 19.0f);
    const float centerX = (float)player->position.x;
    const float centerZ = (float)player->position.y;
    const float step = size / (minimapRange * 2.0f);
    const float middleX = left + size * 0.5f;
    const float middleZ = top + size * 0.5f;
    const int thickness = maxFloat(1.0f, (float)scaleY(canvas, 2.0f));
    drawFillRect(canvas, left, top, size, size, Landscape::COLOR_BLACK);

    int first = (int)ceilf((centerX - minimapRange) / Landscape::ROAD_SPACING);
    int last = (int)floorf((centerX + minimapRange) / Landscape::ROAD_SPACING);
    for (int index = first; index <= last; ++index)
    {
        const float line = index * Landscape::ROAD_SPACING;
        if (line < -Landscape::WORLD_HALF || line > Landscape::WORLD_HALF)
            continue;
        const int x = (int)(middleX + (line - centerX) * step - thickness / 2);
        const int clippedLeft = x < left ? left : x;
        const int right = x + thickness;
        const int clippedRight = right > left + size ? left + size : right;
        if (clippedRight > clippedLeft)
            drawFillRect(canvas, clippedLeft, top, clippedRight - clippedLeft,
                         size, Landscape::COLOR_HORIZON);
    }

    first = (int)ceilf((centerZ - minimapRange) / Landscape::ROAD_SPACING);
    last = (int)floorf((centerZ + minimapRange) / Landscape::ROAD_SPACING);
    for (int index = first; index <= last; ++index)
    {
        const float line = index * Landscape::ROAD_SPACING;
        if (line < -Landscape::WORLD_HALF || line > Landscape::WORLD_HALF)
            continue;
        const int y = (int)(middleZ + (line - centerZ) * step - thickness / 2);
        const int clippedTop = y < top ? top : y;
        const int bottom = y + thickness;
        const int clippedBottom = bottom > top + size ? top + size : bottom;
        if (clippedBottom > clippedTop)
            drawFillRect(canvas, left, clippedTop, size, clippedBottom - clippedTop,
                         Landscape::COLOR_HORIZON);
    }

    for (int i = 0; i < landscape.getBuildingCount(); ++i)
    {
        const Building *building = landscape.getBuilding(i);
        if (!building)
            continue;
        float startX = middleX + (building->x - centerX - building->halfWidth) * step;
        float endX = middleX + (building->x - centerX + building->halfWidth) * step;
        float startZ = middleZ + (building->z - centerZ - building->halfDepth) * step;
        float endZ = middleZ + (building->z - centerZ + building->halfDepth) * step;
        startX = maxFloat(startX, (float)left);
        startZ = maxFloat(startZ, (float)top);
        endX = minFloat(endX, (float)(left + size));
        endZ = minFloat(endZ, (float)(top + size));
        if (endX - startX < 1.0f || endZ - startZ < 1.0f)
            continue;
        drawFillRect(canvas, (int)startX, (int)startZ,
                     (int)(endX - startX), (int)(endZ - startZ),
                     Landscape::COLOR_SIDEWALK);
    }

    drawOutlineRect(canvas, left, top, size, size, Landscape::COLOR_HORIZON);
    const int dot = maxFloat((float)scaleY(canvas, 3.0f), 2.0f);
    const int tip = dot + scaleY(canvas, 3.0f);
    drawFillRect(canvas,
                 (int)(middleX + cosf(heading) * tip - 1.0f),
                 (int)(middleZ + sinf(heading) * tip - 1.0f),
                 2, 2, Landscape::COLOR_LINE);
    drawFillRect(canvas, (int)(middleX - dot / 2.0f),
                 (int)(middleZ - dot / 2.0f), dot, dot, Landscape::COLOR_PLAYER);

    const int remoteDot = maxFloat((float)scaleY(canvas, 2.0f), 2.0f);
    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        const RemotePlayer &remote = remotePlayers[i];
        if (!remote.active || !remote.player)
            continue;
        const float remoteX = middleX + (remote.player->position.x - centerX) * step;
        const float remoteZ = middleZ + (remote.player->position.y - centerZ) * step;
        if (remoteX >= left && remoteX < left + size &&
            remoteZ >= top && remoteZ < top + size)
        {
            drawFillRect(canvas, (int)(remoteX - remoteDot / 2.0f),
                         (int)(remoteZ - remoteDot / 2.0f),
                         remoteDot, remoteDot, remote.color);
        }
    }

    char coordinates[24];
    snprintf(coordinates, sizeof(coordinates), "%d,%d",
             (int)floorf(centerX / Landscape::ROAD_SPACING),
             (int)floorf(centerZ / Landscape::ROAD_SPACING));
    drawText(canvas, left, top + size + scaleY(canvas, 2.0f),
             coordinates, Landscape::COLOR_LINE);
}

void PicoGTA::drawOptions(const char *const *options, int count, int selection,
                          int firstY, int lineHeight)
{
    if (!draw || !options || count <= 0)
        return;
    const int width = (int)draw->getDisplaySize().x;
    const int rowWidth = width * 3 / 4;
    const int rowX = (width - rowWidth) / 2;
    for (int index = 0; index < count; ++index)
    {
        if (!options[index])
            continue;
        const int rowY = firstY + index * lineHeight;
        uint16_t color = Landscape::COLOR_LINE;
        if (index == selection)
        {
            drawFillRect(draw, rowX, rowY, rowWidth, lineHeight, Landscape::COLOR_LINE);
            color = Landscape::COLOR_BLACK;
        }
        const int centeredX = width / 2 - scaleX(draw, (float)textWidth(draw, options[index]) / 2.0f);
        const int textX = centeredX > rowX + scaleX(draw, 2.0f)
                              ? centeredX
                              : rowX + scaleX(draw, 2.0f);
        drawText(draw, textX, rowY, options[index], color);
    }
}

void PicoGTA::drawFullScreenMenu()
{
    if (!draw)
        return;
    const Vector screen = draw->getDisplaySize();
    const int height = (int)screen.y;
    const int lineHeight = fontHeight() + 1;
    const int footerY = height - lineHeight - scaleY(draw, 2.0f);
    draw->fillScreen(Landscape::COLOR_BLACK);

    const char *title = "MULTIPLAYER";
    if (multiplayerView == VIEW_TITLE)
        title = "PICO CITY";
    else if (multiplayerView == VIEW_LOBBIES)
        title = "OPEN LOBBIES";
    else if (multiplayerView == VIEW_ERROR)
        title = "MULTIPLAYER ERROR";
    drawCenteredText(draw, scaleY(draw, 6.0f), title, Landscape::COLOR_LINE);

    const char *footer = "UP/DOWN OK  BACK";
    if (multiplayerView == VIEW_TITLE)
    {
        const char *options[] = {"Play solo", "Multiplayer"};
        drawOptions(options, 2, multiplayerSelection,
                    height / 2 - lineHeight, lineHeight);
    }
    else if (multiplayerView == VIEW_MENU)
    {
        if (multiplayerLobbyId[0])
        {
            char peers[32];
            snprintf(peers, sizeof(peers), "Online: %d peers", remotePlayerCount);
            drawCenteredText(draw, height / 3, peers, Landscape::COLOR_LINE);
            const char *options[] = {"Leave lobby", "Leave game"};
            drawOptions(options, 2, multiplayerSelection, height / 2, lineHeight);
        }
        else
        {
            const char *back = multiplayerMenuOriginTitle ? "Back" : "Leave game";
            const char *options[] = {"Create lobby (4)", "Join lobby", back};
            drawOptions(options, 3, multiplayerSelection,
                        height / 2 - (3 * lineHeight) / 2, lineHeight);
        }
    }
    else if (multiplayerView == VIEW_LOBBIES)
    {
        if (multiplayerLobbyCount > 0)
        {
            const int visibleCount = multiplayerLobbyCount < 4 ? multiplayerLobbyCount : 4;
            int start = multiplayerLobbyIndex - visibleCount + 1;
            const int maximumStart = multiplayerLobbyCount - visibleCount;
            if (start < 0)
                start = 0;
            if (start > maximumStart)
                start = maximumStart;
            const int count = multiplayerLobbyCount - start < visibleCount
                                  ? multiplayerLobbyCount - start
                                  : visibleCount;
            char labels[MAX_LOBBIES][32];
            const char *options[MAX_LOBBIES];
            for (int i = 0; i < count; ++i)
            {
                const Lobby &lobby = multiplayerLobbies[start + i];
                snprintf(labels[i], sizeof(labels[i]), "%.8s %d/%d",
                         lobby.id, lobby.playerCount, lobby.maxPlayers);
                options[i] = labels[i];
            }
            drawOptions(options, count, multiplayerLobbyIndex - start,
                        height / 3, lineHeight);
        }
        else
        {
            drawCenteredText(draw, height / 2, "No open lobbies", Landscape::COLOR_LINE);
        }
    }
    else if (multiplayerView == VIEW_PENDING)
    {
        char line[23];
        copyText(line, sizeof(line), multiplayerStatus);
        if (strlen(line) > 22)
            line[22] = '\0';
        drawCenteredText(draw, height / 2, line, Landscape::COLOR_LINE);
        footer = "";
    }
    else
    {
        const size_t statusLength = strlen(multiplayerStatus);
        char line[23];
        size_t offset = 0;
        int y = height / 2 - lineHeight;
        do
        {
            size_t count = statusLength - offset;
            if (count > 22)
                count = 22;
            memcpy(line, multiplayerStatus + offset, count);
            line[count] = '\0';
            drawCenteredText(draw, y, line, Landscape::COLOR_LINE);
            offset += count;
            y += lineHeight;
        } while (offset < statusLength && y < footerY);
        footer = "CENTER/BACK MENU";
    }

    if (footer && footer[0])
        drawText(draw, scaleX(draw, 2.0f), footerY, footer, Landscape::COLOR_LINE);
    draw->swap();
}

void PicoGTA::handleMenuInput()
{
    if (!inputPressed)
        return;
    const int key = lastInput;
    if (multiplayerView == VIEW_TITLE)
    {
        if (key == INPUT_KEY_BACK)
        {
            multiplayerExitReady = true;
        }
        else if (key == INPUT_KEY_UP || key == INPUT_KEY_DOWN)
        {
            multiplayerSelection = 1 - multiplayerSelection;
        }
        else if (key == INPUT_KEY_CENTER)
        {
            multiplayerMenuOriginTitle = true;
            if (!startGame())
                setMultiplayerError("Unable to start Pico City");
            else if (multiplayerSelection == 0)
            {
                multiplayerView = VIEW_GAME;
                multiplayerMenuOriginTitle = false;
            }
            else
            {
                multiplayerView = VIEW_MENU;
                multiplayerSelection = 0;
            }
        }
        return;
    }

    if (multiplayerView == VIEW_PENDING)
        return;

    if (multiplayerView == VIEW_ERROR)
    {
        if (key == INPUT_KEY_BACK || key == INPUT_KEY_CENTER)
        {
            multiplayerView = VIEW_MENU;
            multiplayerSelection = 0;
        }
        return;
    }

    if (multiplayerView == VIEW_LOBBIES)
    {
        if (key == INPUT_KEY_BACK)
        {
            multiplayerView = VIEW_MENU;
            multiplayerSelection = 1;
        }
        else if ((key == INPUT_KEY_UP || key == INPUT_KEY_DOWN) &&
                 multiplayerLobbyCount > 0)
        {
            if (key == INPUT_KEY_UP)
                multiplayerLobbyIndex =
                    (multiplayerLobbyIndex + multiplayerLobbyCount - 1) % multiplayerLobbyCount;
            else
                multiplayerLobbyIndex = (multiplayerLobbyIndex + 1) % multiplayerLobbyCount;
        }
        else if (key == INPUT_KEY_CENTER && multiplayerLobbyCount > 0)
        {
            joinMultiplayerLobby(multiplayerLobbies[multiplayerLobbyIndex].id);
        }
        return;
    }

    if (multiplayerView != VIEW_MENU)
        return;

    if (key == INPUT_KEY_BACK)
    {
        if (multiplayerMenuOriginTitle)
        {
            multiplayerView = VIEW_TITLE;
            multiplayerSelection = 1;
            multiplayerMenuOriginTitle = false;
        }
        else
        {
            multiplayerView = VIEW_GAME;
        }
        return;
    }

    if (key == INPUT_KEY_UP || key == INPUT_KEY_DOWN)
    {
        const int optionCount = multiplayerLobbyId[0] ? 2 : 3;
        if (key == INPUT_KEY_UP)
            multiplayerSelection = (multiplayerSelection + optionCount - 1) % optionCount;
        else
            multiplayerSelection = (multiplayerSelection + 1) % optionCount;
        return;
    }

    if (key != INPUT_KEY_CENTER)
        return;
    if (multiplayerLobbyId[0])
    {
        if (multiplayerSelection == 0)
            leaveMultiplayer(false);
        else
            leaveMultiplayer(true);
    }
    else if (multiplayerSelection == 0)
    {
        createMultiplayerLobby();
    }
    else if (multiplayerSelection == 1)
    {
        fetchMultiplayerLobbies();
    }
    else if (multiplayerMenuOriginTitle)
    {
        multiplayerView = VIEW_TITLE;
        multiplayerSelection = 1;
        multiplayerMenuOriginTitle = false;
    }
    else
    {
        endGame();
    }
}

void PicoGTA::setMultiplayerError(const char *text)
{
    copyText(multiplayerStatus, sizeof(multiplayerStatus),
             text && text[0] ? text : "Multiplayer request failed");
    multiplayerView = VIEW_ERROR;
    if (!multiplayerLobbyId[0])
        multiplayerConnectionState = CONNECTION_IDLE;
    ENGINE_LOG_INFO("[PicoGTA:multiplayer] %s\n", multiplayerStatus);
}

bool PicoGTA::ensureMultiplayerPlayerId()
{
    if (multiplayerPlayerId[0])
        return true;

    const uint32_t ticks = (uint32_t)TIME_MILLIS;
    const uint32_t counter = ++multiplayerIdCounter;
    const uint32_t nonce = cityMap.nextRandom(0x7FFFFFFFu) ^ ticks ^
                           (counter * 0x9E3779B9u) ^
                           (uint32_t)(uintptr_t)this;
    const int length = snprintf(multiplayerPlayerId, sizeof(multiplayerPlayerId),
                                "pico-%08lx-%08lx-%08lx",
                                (unsigned long)ticks, (unsigned long)nonce,
                                (unsigned long)counter);
    if (length <= 0 || (size_t)length >= sizeof(multiplayerPlayerId))
    {
        multiplayerPlayerId[0] = '\0';
        setMultiplayerError("Could not create a multiplayer player ID");
        return false;
    }
    return true;
}

bool PicoGTA::beginMultiplayerRequest(HttpAction action, const char *payload)
{
    if (httpRequestActive || !HTTP_REQUEST_IS_FINISHED())
    {
        if (action == REQUEST_REMOVE)
            finishMultiplayerLeave("Another HTTP request is still in progress");
        else
            setMultiplayerError("A request is already in progress");
        return false;
    }

    char url[256];
    char requestPayload[256];
    requestPayload[0] = '\0';
    const char *method = "POST";
    const char *status = nullptr;
    const char *path = nullptr;
    if (action == REQUEST_LIST)
    {
        const int length = snprintf(url, sizeof(url), "%slobbies/%d/%d/",
                                    multiplayerApi, 4, MAX_LOBBIES);
        if (length <= 0 || (size_t)length >= sizeof(url))
        {
            setMultiplayerError("Lobby URL is too long");
            return false;
        }
        method = "GET";
        status = "Fetching lobbies...";
    }
    else if (action == REQUEST_CREATE)
    {
        path = "lobby/create/";
        status = "Creating lobby...";
        const int length = snprintf(requestPayload, sizeof(requestPayload),
                                    "{\"max_players\":4,\"data\":{}}");
        if (length <= 0 || (size_t)length >= sizeof(requestPayload))
        {
            setMultiplayerError("Could not prepare the create request");
            return false;
        }
    }
    else if (action == REQUEST_JOIN)
    {
        path = "lobby/join/";
        status = "Joining lobby...";
    }
    else if (action == REQUEST_REMOVE)
    {
        path = "lobby/remove/";
        status = "Leaving lobby...";
    }
    else
    {
        setMultiplayerError("Unsupported multiplayer request");
        return false;
    }

    if (path)
    {
        const int length = snprintf(url, sizeof(url), "%s%s", multiplayerApi, path);
        if (length <= 0 || (size_t)length >= sizeof(url))
        {
            if (action == REQUEST_REMOVE)
                finishMultiplayerLeave("Lobby URL is too long");
            else
                setMultiplayerError("Lobby URL is too long");
            return false;
        }
        if (!multiplayerPlayerId[0] ||
            (action == REQUEST_JOIN && !multiplayerTargetLobbyId[0]) ||
            (action == REQUEST_REMOVE && !multiplayerLobbyId[0]))
        {
            if (action == REQUEST_REMOVE)
                finishMultiplayerLeave("Missing lobby or player ID");
            else
                setMultiplayerError("Missing lobby or player ID");
            return false;
        }
        if (action == REQUEST_JOIN || action == REQUEST_REMOVE)
        {
            size_t position = 0;
            const char lobbyPrefix[] = "{\"lobby_id\":";
            memcpy(requestPayload, lobbyPrefix, sizeof(lobbyPrefix) - 1);
            position = sizeof(lobbyPrefix) - 1;
            requestPayload[position] = '\0';
            const char *lobbyId = action == REQUEST_REMOVE
                                      ? multiplayerLobbyId
                                      : multiplayerTargetLobbyId;
            if (!lobbyId[0] ||
                !appendJsonQuoted(requestPayload, sizeof(requestPayload), position, lobbyId))
            {
                if (action == REQUEST_REMOVE)
                    finishMultiplayerLeave("Could not encode the lobby ID");
                else
                    setMultiplayerError("Could not encode the lobby ID");
                return false;
            }
            const char playerPrefix[] = ",\"player_id\":";
            if (position + sizeof(playerPrefix) >= sizeof(requestPayload))
            {
                if (action == REQUEST_REMOVE)
                    finishMultiplayerLeave("Multiplayer request is too large");
                else
                    setMultiplayerError("Multiplayer request is too large");
                return false;
            }
            memcpy(requestPayload + position, playerPrefix, sizeof(playerPrefix) - 1);
            position += sizeof(playerPrefix) - 1;
            requestPayload[position] = '\0';
            if (!appendJsonQuoted(requestPayload, sizeof(requestPayload), position,
                                  multiplayerPlayerId) ||
                position + 2 > sizeof(requestPayload))
            {
                if (action == REQUEST_REMOVE)
                    finishMultiplayerLeave("Could not encode the player ID");
                else
                    setMultiplayerError("Could not encode the player ID");
                return false;
            }
            requestPayload[position++] = '}';
            requestPayload[position] = '\0';
        }
    }

    if (!HTTP_SEND_REQUEST(url, method, multiplayerHeaders, requestPayload))
    {
        if (action == REQUEST_REMOVE)
            finishMultiplayerLeave("Could not start the HTTP request");
        else
        {
            if (action == REQUEST_JOIN)
                multiplayerTargetLobbyId[0] = '\0';
            setMultiplayerError("Could not start the HTTP request");
        }
        return false;
    }

    httpRequestActive = true;
    httpAction = action;
    copyText(multiplayerStatus, sizeof(multiplayerStatus), status);
    multiplayerView = VIEW_PENDING;
    return true;
}

void PicoGTA::fetchMultiplayerLobbies()
{
    multiplayerLobbyCount = 0;
    multiplayerLobbyIndex = 0;
    for (int i = 0; i < MAX_LOBBIES; ++i)
    {
        multiplayerLobbies[i].id[0] = '\0';
        multiplayerLobbies[i].playerCount = 0;
        multiplayerLobbies[i].maxPlayers = 0;
    }
    beginMultiplayerRequest(REQUEST_LIST);
}

void PicoGTA::createMultiplayerLobby()
{
    if (!ensureMultiplayerPlayerId())
        return;
    multiplayerTargetLobbyId[0] = '\0';
    beginMultiplayerRequest(REQUEST_CREATE);
}

void PicoGTA::joinMultiplayerLobby(const char *lobbyId)
{
    if (!ensureMultiplayerPlayerId())
        return;
    if (!lobbyId || !lobbyId[0] ||
        !copyText(multiplayerTargetLobbyId, sizeof(multiplayerTargetLobbyId), lobbyId))
    {
        multiplayerTargetLobbyId[0] = '\0';
        setMultiplayerError("Invalid lobby ID");
        return;
    }
    beginMultiplayerRequest(REQUEST_JOIN);
}

void PicoGTA::pollMultiplayerHttp()
{
    if (!httpRequestActive || !HTTP_REQUEST_IS_FINISHED())
        return;

    const HttpAction action = httpAction;
    char response[HTTP_RESPONSE_SIZE];
    response[0] = '\0';
    const bool hasResponse = HTTP_GET_RESPONSE(response, sizeof(response));
    httpRequestActive = false;
    httpAction = REQUEST_NONE;

    char serverError[96];
    serverError[0] = '\0';
    getServerError(response, serverError, sizeof(serverError));
    if (hasResponse)
        printf("Server response: %s\n", response);

    if (action == REQUEST_REMOVE)
    {
        if (serverError[0])
        {
            if (strcmp(serverError, "Lobby not found") == 0)
            {
                // Lobby already gone
                serverError[0] = '\0';
            }
            else
            {
                finishMultiplayerLeave(serverError);
                return;
            }
        }
        if (!hasResponse || !response[0])
        {
            finishMultiplayerLeave(
                "Could not confirm lobby removal; this backend does not expose HTTP status");
            return;
        }
        if (!hasJsonObjectShape(response))
        {
            finishMultiplayerLeave("Invalid lobby removal response");
            return;
        }
        finishMultiplayerLeave();
        return;
    }

    if (!hasResponse || !response[0])
    {
        if (action == REQUEST_JOIN)
            multiplayerTargetLobbyId[0] = '\0';
        setMultiplayerError("No HTTP response body");
        return;
    }

    if (serverError[0])
    {
        if (action == REQUEST_JOIN)
            multiplayerTargetLobbyId[0] = '\0';
        setMultiplayerError(serverError);
        return;
    }

    if (action == REQUEST_LIST)
    {
        char arrayText[HTTP_RESPONSE_SIZE];
        if (!getJsonString("lobbies", response, arrayText, sizeof(arrayText)) ||
            arrayText[0] != '[')
        {
            setMultiplayerError("Invalid lobby list response");
            return;
        }

        for (int i = 0; i < MAX_LOBBIES; ++i)
        {
            char *lobbyJson = JSON_GET_ARRAY_VALUE("lobbies", (uint32_t)i, response);
            if (!lobbyJson)
                break;
            char lobbyId[MAX_LOBBY_ID_LENGTH + 1];
            int playerCount = 0;
            int maxPlayers = 0;
            const bool valid =
                getJsonString("lobby_id", lobbyJson, lobbyId, sizeof(lobbyId)) &&
                lobbyId[0] &&
                getJsonInt("player_count", lobbyJson, playerCount) &&
                getJsonInt("max_players", lobbyJson, maxPlayers) &&
                playerCount >= 0 && maxPlayers > playerCount && maxPlayers > 0;
            ENGINE_MEM_FREE(lobbyJson);
            if (!valid)
                continue;
            Lobby &lobby = multiplayerLobbies[multiplayerLobbyCount++];
            copyText(lobby.id, sizeof(lobby.id), lobbyId);
            lobby.playerCount = playerCount;
            lobby.maxPlayers = maxPlayers;
        }
        multiplayerLobbyIndex = 0;
        multiplayerStatus[0] = '\0';
        multiplayerView = VIEW_LOBBIES;
        return;
    }

    if (action == REQUEST_CREATE)
    {
        char lobbyId[MAX_LOBBY_ID_LENGTH + 1];
        if (!getJsonString("lobby_id", response, lobbyId, sizeof(lobbyId)) ||
            !lobbyId[0])
        {
            setMultiplayerError("Server returned no lobby ID");
            return;
        }
        copyText(multiplayerTargetLobbyId, sizeof(multiplayerTargetLobbyId), lobbyId);
        joinMultiplayerLobby(lobbyId);
        return;
    }

    if (action == REQUEST_JOIN)
    {
        if (!hasJsonObjectShape(response) || !multiplayerTargetLobbyId[0])
        {
            multiplayerTargetLobbyId[0] = '\0';
            setMultiplayerError("Invalid lobby join response");
            return;
        }
        copyText(multiplayerLobbyId, sizeof(multiplayerLobbyId),
                 multiplayerTargetLobbyId);
        multiplayerTargetLobbyId[0] = '\0';
        connectMultiplayer();
        return;
    }

    setMultiplayerError("Unexpected multiplayer response");
}

void PicoGTA::connectMultiplayer()
{
    if (!multiplayerLobbyId[0])
    {
        setMultiplayerError("Missing lobby ID");
        return;
    }
    char url[256];
    const int length = snprintf(url, sizeof(url), "%s%s/",
                                multiplayerWebSocket, multiplayerLobbyId);
    if (length <= 0 || (size_t)length >= sizeof(url))
    {
        leaveMultiplayer(false, "WebSocket URL is too long");
        return;
    }

    multiplayerConnectionState = CONNECTION_IDLE;
    copyText(multiplayerStatus, sizeof(multiplayerStatus), "Connecting...");
    multiplayerView = VIEW_PENDING;
    if (!HTTP_WEBSOCKET_START(url, PICO_GTA_WS_PORT))
    {
        leaveMultiplayer(false, "Connection failed: WebSocket could not start");
        return;
    }

    multiplayerConnectionState = CONNECTION_CONNECTING;
}

void PicoGTA::pollMultiplayerWebSocket()
{
    if (multiplayerConnectionState != CONNECTION_ACTIVE)
        return;
    if (!HTTP_WEBSOCKET_IS_CONNECTED())
    {
        multiplayerConnectionState = CONNECTION_LOST;
        copyText(multiplayerStatus, sizeof(multiplayerStatus), "Connection lost");
        return;
    }

    char messageBuffer[161];
    while (HTTP_GET_WEBSOCKET_RESPONSE(messageBuffer, sizeof(messageBuffer)))
    {
        if (strcmp(messageBuffer, "PONG") != 0)
            processMultiplayerMessage(messageBuffer);
    }
}

void PicoGTA::updateMultiplayer()
{
    if (multiplayerConnectionState == CONNECTION_CONNECTING)
    {
        if (HTTP_WEBSOCKET_IS_CONNECTED())
        {
            multiplayerConnectionState = CONNECTION_ACTIVE;
            copyText(multiplayerStatus, sizeof(multiplayerStatus), "Connected");
            multiplayerView = VIEW_MENU;
            multiplayerMenuOriginTitle = false;
            multiplayerSelection = 0;
            multiplayerLastSendFrame = frameClock;
        }
    }
    else if (multiplayerConnectionState == CONNECTION_ACTIVE)
    {
        for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
        {
            RemotePlayer &remote = remotePlayers[i];
            if (remote.active &&
                frameClock - remote.lastSeenFrame > MULTIPLAYER_REMOTE_TIMEOUT_FRAMES)
                removeRemotePlayer(remote.id);
        }

        if (!HTTP_WEBSOCKET_IS_CONNECTED())
        {
            multiplayerConnectionState = CONNECTION_LOST;
            copyText(multiplayerStatus, sizeof(multiplayerStatus), "Connection lost");
        }
        else if (frameClock - multiplayerLastSendFrame >=
                 MULTIPLAYER_SEND_INTERVAL_FRAMES)
        {
            multiplayerLastSendFrame = frameClock;
            char packet[161];
            const float wireHeading = atan2f(sinf(heading), cosf(heading));
            if (!player ||
                !packMultiplayerMessage(multiplayerPlayerId, "state",
                                        player ? player->position.x : 0.0f,
                                        player ? player->position.y : 0.0f,
                                        wireHeading, inCar, packet, sizeof(packet)) ||
                !HTTP_WEBSOCKET_SEND(packet))
            {
                multiplayerConnectionState = CONNECTION_LOST;
                copyText(multiplayerStatus, sizeof(multiplayerStatus),
                         "WebSocket send failed");
            }
        }
    }

    if (multiplayerConnectionState == CONNECTION_LOST)
    {
        char reason[96];
        copyText(reason, sizeof(reason),
                 multiplayerStatus[0] ? multiplayerStatus : "Connection lost");
        leaveMultiplayer(false, reason);
    }
}

void PicoGTA::processMultiplayerMessage(const char *messageText)
{
    ParsedMultiplayerMessage parsed;
    if (!parseMultiplayerMessage(messageText, parsed))
    {
        ENGINE_LOG_INFO("[PicoGTA:multiplayer] Ignored invalid WebSocket packet\n");
        return;
    }
    if (strcmp(parsed.playerId, multiplayerPlayerId) == 0)
        return;
    if (parsed.leave)
    {
        removeRemotePlayer(parsed.playerId);
        return;
    }
    if (parsed.x < -Landscape::WORLD_HALF || parsed.x > Landscape::WORLD_HALF ||
        parsed.z < -Landscape::WORLD_HALF || parsed.z > Landscape::WORLD_HALF ||
        parsed.heading < -1000.0f || parsed.heading > 1000.0f)
        return;

    RemotePlayer *remote = nullptr;
    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        if (remotePlayers[i].active &&
            strcmp(remotePlayers[i].id, parsed.playerId) == 0)
        {
            remote = &remotePlayers[i];
            break;
        }
    }
    if (!remote)
    {
        remote = createRemotePlayer(parsed.playerId);
        if (!remote)
            return;
    }

    const float dx = cosf(parsed.heading);
    const float dz = sinf(parsed.heading);
    const float rotation = atan2f(dz, dx) - cityPi * 0.5f;
    remote->player->position.x = parsed.x;
    remote->player->position.y = parsed.z;
    remote->player->direction.x = dx;
    remote->player->direction.y = dz;
    remote->player->set3DSpriteRotation(rotation);
    remote->player->is_visible = !parsed.inCar;
    remote->car->position.x = parsed.x;
    remote->car->position.y = parsed.z;
    remote->car->direction.x = dx;
    remote->car->direction.y = dz;
    remote->car->set3DSpriteRotation(rotation);
    remote->car->is_visible = parsed.inCar;
    remote->lastSeenFrame = frameClock;
}

void PicoGTA::leaveMultiplayer(bool exitAfter, const char *notice)
{
    multiplayerExitAfterLeave = exitAfter;
    copyText(multiplayerLeaveNotice, sizeof(multiplayerLeaveNotice), notice);
    multiplayerConnectionState = CONNECTION_LEAVING;
    if (!multiplayerLobbyId[0])
    {
        finishMultiplayerLeave();
        return;
    }

    if (HTTP_WEBSOCKET_IS_CONNECTED())
    {
        char packet[161];
        if (packMultiplayerMessage(multiplayerPlayerId, "leave", 0.0f, 0.0f,
                                   0.0f, false, packet, sizeof(packet)) &&
            !HTTP_WEBSOCKET_SEND(packet))
            ENGINE_LOG_INFO("[PicoGTA:multiplayer] Could not relay leave message\n");
        HTTP_WEBSOCKET_STOP();
    }

    beginMultiplayerRequest(REQUEST_REMOVE);
}

void PicoGTA::finishMultiplayerLeave(const char *error)
{
    const bool exitAfter = multiplayerExitAfterLeave;
    char notice[sizeof(multiplayerLeaveNotice)];
    copyText(notice, sizeof(notice), multiplayerLeaveNotice);
    multiplayerExitAfterLeave = false;
    multiplayerLeaveNotice[0] = '\0';
    multiplayerConnectionState = error ? CONNECTION_ERROR : CONNECTION_IDLE;
    if (!error)
        multiplayerLobbyId[0] = '\0';
    multiplayerTargetLobbyId[0] = '\0';
    if (HTTP_WEBSOCKET_IS_CONNECTED())
        HTTP_WEBSOCKET_STOP();
    removeAllRemotePlayers();

    if (error)
    {
        if (notice[0])
            snprintf(multiplayerStatus, sizeof(multiplayerStatus), "%.81s; leave failed", notice);
        else
            snprintf(multiplayerStatus, sizeof(multiplayerStatus), "Leave failed: %s", error);
        multiplayerView = VIEW_ERROR;
        ENGINE_LOG_INFO("[PicoGTA:multiplayer] Leave failed: %s\n", error);
    }
    else if (notice[0])
    {
        copyText(multiplayerStatus, sizeof(multiplayerStatus), notice);
        multiplayerView = VIEW_ERROR;
        ENGINE_LOG_INFO("[PicoGTA:multiplayer] %s\n", notice);
    }
    else
    {
        copyText(multiplayerStatus, sizeof(multiplayerStatus), "Left lobby");
        multiplayerView = VIEW_MENU;
    }

    if (exitAfter)
    {
        multiplayerView = VIEW_GAME;
        multiplayerExitReady = true;
    }
}

PicoGTA::RemotePlayer *PicoGTA::createRemotePlayer(const char *playerId)
{
    if (!playerId || !playerId[0] ||
        remotePlayerCount >= MAX_REMOTE_PLAYERS)
        return nullptr;
    Game *game = getGame();
    Level *level = game
                       ? (game->current_level ? game->current_level : game->levels[0])
                       : nullptr;
    if (!level)
        return nullptr;

    int slot = -1;
    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        if (!remotePlayers[i].active)
        {
            slot = i;
            break;
        }
    }
    if (slot < 0)
        return nullptr;

    const uint16_t color = carColors[(slot + 1) % 6];
    Entity *remote = ENGINE_MEM_NEW Entity(
        remotePlayerNames[slot], ENTITY_3D_SPRITE, Vector(0.0f, 0.0f),
        Vector(0.6f, 1.5f), nullptr, nullptr, nullptr,
        CallbackEntityGame(), CallbackEntityGame(), CallbackEntityGame(),
        CallbackEntityDrawGame(), CallbackEntityEntityGame(), false,
        SPRITE_3D_HUMANOID, color);
    if (!remote || !remote->has3DSprite())
    {
        ENGINE_MEM_DELETE remote;
        return nullptr;
    }
    if (!addEntityToLevel(level, remote))
        return nullptr;

    Vehicle *car = ENGINE_MEM_NEW Vehicle(
        this, remoteCarNames[slot], Vector(0.0f, 0.0f),
        color, VEHICLE_REMOTE_CAR);
    if (!car || !car->sprite_3d)
    {
        ENGINE_MEM_DELETE car;
        level->entity_remove(remote);
        return nullptr;
    }
    car->is_visible = false;
    if (!addEntityToLevel(level, car))
    {
        level->entity_remove(remote);
        return nullptr;
    }

    RemotePlayer &entry = remotePlayers[slot];
    entry.active = true;
    if (!copyText(entry.id, sizeof(entry.id), playerId))
    {
        entry.active = false;
        level->entity_remove(car);
        level->entity_remove(remote);
        return nullptr;
    }
    entry.player = remote;
    entry.car = car;
    entry.color = color;
    entry.lastSeenFrame = frameClock;
    ++remotePlayerCount;
    return &entry;
}

void PicoGTA::removeRemotePlayer(const char *playerId)
{
    if (!playerId || !playerId[0])
        return;
    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        RemotePlayer &remote = remotePlayers[i];
        if (!remote.active || strcmp(remote.id, playerId) != 0)
            continue;

        Game *game = getGame();
        Level *level = game
                           ? (game->current_level ? game->current_level : game->levels[0])
                           : nullptr;
        if (level)
        {
            if (remote.car)
                level->entity_remove(remote.car);
            if (remote.player)
                level->entity_remove(remote.player);
        }
        remote.active = false;
        remote.id[0] = '\0';
        remote.player = nullptr;
        remote.car = nullptr;
        remote.color = 0;
        remote.lastSeenFrame = 0;
        if (remotePlayerCount > 0)
            --remotePlayerCount;
        return;
    }
}

void PicoGTA::removeAllRemotePlayers()
{
    for (int i = 0; i < MAX_REMOTE_PLAYERS; ++i)
    {
        if (remotePlayers[i].active)
            removeRemotePlayer(remotePlayers[i].id);
    }
    remotePlayerCount = 0;
}
