#pragma once
#include <stddef.h>
#include "config.hpp"
#include "pico-game-engine/engine/engine.hpp"
#include "general.hpp"
#include "landscape.hpp"
#include "map.hpp"
#include "pedestrian.hpp"
#include "player.hpp"
#include "sound.hpp"
#include "time.hpp"
#include "vehicle.hpp"

using namespace picogta;

class PicoGTA
{
public:
    PicoGTA(const char *username, const char *password);
    ~PicoGTA();

    void drawBackground(Draw *canvas);
    void drawHud(Draw *canvas);
    void endGame();
    int getCurrentInput() const { return lastInput; }
    Draw *getDraw() const { return draw; }
    GameEngine *getEngine() const { return engine; }
    Game *getGame() const;
    Time *getGameTime() const { return gameTime; }
    Player *getPlayer() const { return player; }
    bool initDraw();
    bool isActive() const { return shouldExit == false; }
    bool isRunning() const { return isGameRunning; }
    void resetInput();
    void run();
    void update();
    void updatePerson(Pedestrian *person);
    void updatePlayer(Player *player, Game *game);
    void updateTraffic(Vehicle *car);
    bool wasInputPressed(int key) const { return inputPressed && lastInput == key; }

private:
    enum
    {
        CITY_GRID_LIMIT = 5,
        HTTP_RESPONSE_SIZE = 2048,
        MAX_LOBBIES = 4,
        MAX_LOBBY_ID_LENGTH = 100,
        MAX_PLAYER_ID_LENGTH = 100,
        MAX_REMOTE_PLAYERS = 3,
        MULTIPLAYER_REMOTE_TIMEOUT_FRAMES = 900,
        MULTIPLAYER_SEND_INTERVAL_FRAMES = 6,
        PERSON_COUNT = 6,
        TRAFFIC_COUNT = 6
    };

    enum HttpAction
    {
        REQUEST_NONE,
        REQUEST_LIST,
        REQUEST_CREATE,
        REQUEST_JOIN,
        REQUEST_REMOVE
    };

    struct Lobby
    {
        char id[MAX_LOBBY_ID_LENGTH + 1];
        int maxPlayers;
        int playerCount;
    };

    enum MultiplayerConnectionState
    {
        CONNECTION_IDLE,
        CONNECTION_CONNECTING,
        CONNECTION_ACTIVE,
        CONNECTION_LOST,
        CONNECTION_LEAVING,
        CONNECTION_ERROR
    };

    enum MultiplayerView
    {
        VIEW_TITLE,
        VIEW_MENU,
        VIEW_LOBBIES,
        VIEW_PENDING,
        VIEW_ERROR,
        VIEW_GAME
    };

    struct ParsedMultiplayerMessage
    {
        float heading;
        bool inCar;
        bool leave;
        char playerId[MAX_PLAYER_ID_LENGTH + 1];
        float x;
        float z;
    };

    struct RemotePlayer
    {
        bool active;
        Vehicle *car;
        uint16_t color;
        char id[MAX_PLAYER_ID_LENGTH + 1];
        uint32_t lastSeenFrame;
        Entity *player;
    };

    float absoluteFloat(float value) const;
    bool addEntityToLevel(Level *level, Entity *entity) const;
    bool appendJsonQuoted(char *output, size_t capacity, size_t &position,
                          const char *text) const;
    static void backgroundRender(Entity *entity, Draw *canvas, Game *game, void *context);
    bool beginMultiplayerRequest(HttpAction action, const char *payload = nullptr);
    bool carBlocked(float x, float z, int skipIndex) const;
    float clampFloat(float value, float lower, float upper) const;
    int clampInt(int value, int lower, int upper) const;
    void connectMultiplayer();
    bool copyText(char *destination, size_t capacity, const char *source) const;
    void createMultiplayerLobby();
    RemotePlayer *createRemotePlayer(const char *playerId);
    void drawCenteredText(Draw *canvas, int y, const char *text, uint16_t color) const;
    void drawFillRect(Draw *canvas, int x, int y, int width, int height,
                      uint16_t color) const;
    void drawFullScreenMenu();
    void drawMinimap(Draw *canvas);
    void drawOptions(const char *const *options, int count, int selection,
                     int firstY, int lineHeight);
    void drawOutlineRect(Draw *canvas, int x, int y, int width, int height,
                         uint16_t color) const;
    void drawText(Draw *canvas, int x, int y, const char *text, uint16_t color) const;
    void driveCar(Player *player, Game *game);
    bool ensureMultiplayerPlayerId();
    void fetchMultiplayerLobbies();
    void finishMultiplayerLeave(const char *error = nullptr);
    int fontHeight() const;
    bool formatFloatAscii(char *output, size_t capacity, float value) const;
    bool getJsonInt(const char *key, const char *json, int &value) const;
    bool getJsonString(const char *key, const char *json, char *output,
                       size_t capacity) const;
    void getServerError(const char *json, char *error, size_t capacity);
    void handleMenuInput();
    bool hasJsonObjectShape(const char *text) const;
    void joinMultiplayerLobby(const char *lobbyId);
    void leaveMultiplayer(bool exitAfter, const char *notice = nullptr);
    float maxFloat(float left, float right) const;
    float minFloat(float left, float right) const;
    bool packMultiplayerMessage(const char *playerId, const char *type,
                                float x, float z, float heading, bool inCar,
                                char *output, size_t capacity) const;
    bool parseDecimalInt(const char *text, int &value) const;
    bool parseFloatAscii(const char *text, float &value) const;
    bool parseMultiplayerMessage(const char *message,
                                 ParsedMultiplayerMessage &parsed) const;
    void pollMultiplayerHttp();
    void pollMultiplayerWebSocket();
    void processMultiplayerMessage(const char *message);
    void removeAllRemotePlayers();
    void removeRemotePlayer(const char *playerId);
    int scaleX(Draw *canvas, float value) const;
    int scaleY(Draw *canvas, float value) const;
    void setMessage(const char *message, int frames);
    void setMultiplayerError(const char *message);
    void spawnPerson(int index);
    void spawnTraffic(int index);
    bool startGame();
    void stopGame();
    void syncPlayerCar(Player *player);
    int textWidth(Draw *canvas, const char *text) const;
    void toggleCar(Player *player);
    void updateCameraDistance();
    void updateMessage();
    void updateMultiplayer();
    void walkPlayer(Player *player, Game *game);

    const float cameraDistance = 8.2f;
    const float cameraIndoorDistance = 2.6f;
    const float carAccel = 0.05f;
    const float carBrake = 0.085f;
    const uint16_t carColors[6] = {0xF800, 0xFD20, 0x001F, 0x07FF, 0xF81F, 0x001F};
    const float carFriction = 0.012f;
    const float carMaxReverse = -0.35f;
    const float carMaxSpeed = 2.0f;
    const float carSteer = 0.16f;
    Map cityMap;
    const float cityPi = 3.14159265358979323846f;
    bool dayJustSwitched;
    Draw *draw;
    GameEngine *engine;
    uint32_t frameClock;
    Time *gameTime;
    float heading;
    HttpAction httpAction;
    bool httpRequestActive;
    bool inCar;
    bool inputPressed;
    bool isGameRunning;
    int lastInput;
    Landscape landscape;
    char message[32];
    int messageTimer;
    const float minimapRange = 44.0f;
    const float minimapSize = 60.0f;
    const char *const multiplayerApi =
        "https://www.jblanked.com/picoware/api/picogta/";
    MultiplayerConnectionState multiplayerConnectionState;
    bool multiplayerExitAfterLeave;
    bool multiplayerExitReady;
    const char *const multiplayerHeaders =
        "{\"Content-Type\":\"application/json\",\"HTTP_USER_AGENT\":\"Pico\","
        "\"Setting\":\"X-Flipper-Redirect\",\"User-Agent\":\"Raspberry Pi Pico W\"}";
    uint32_t multiplayerIdCounter;
    uint32_t multiplayerLastSendFrame;
    char multiplayerLeaveNotice[96];
    Lobby multiplayerLobbies[MAX_LOBBIES];
    int multiplayerLobbyCount;
    char multiplayerLobbyId[MAX_LOBBY_ID_LENGTH + 1];
    int multiplayerLobbyIndex;
    bool multiplayerMenuOriginTitle;
    char multiplayerPlayerId[MAX_PLAYER_ID_LENGTH + 1];
    int multiplayerSelection;
    char multiplayerStatus[96];
    char multiplayerTargetLobbyId[MAX_LOBBY_ID_LENGTH + 1];
    MultiplayerView multiplayerView;
    const char *const multiplayerWebSocket =
        "wss://www.jblanked.com/ws/picoware/picogta/";
    Pedestrian *people[PERSON_COUNT];
    float peopleSpeeds[PERSON_COUNT];
    const uint16_t personColors[6] = {0x001F, 0xF800, 0x07E0, 0xFD20, 0xF81F, 0x001F};
    const char *const personNames[6] = {
        "Person 1", "Person 2", "Person 3", "Person 4", "Person 5", "Person 6"};
    Player *player;
    Vehicle *playerCar;
    const float recycleDistance = 56.0f;
    const char *const remoteCarNames[MAX_REMOTE_PLAYERS] = {
        "Online 1 Car", "Online 2 Car", "Online 3 Car"};
    int remotePlayerCount;
    const char *const remotePlayerNames[MAX_REMOTE_PLAYERS] = {
        "Online 1", "Online 2", "Online 3"};
    RemotePlayer remotePlayers[MAX_REMOTE_PLAYERS];
    bool shouldExit;
    float speed;
    float steering;
    Vehicle *traffic[TRAFFIC_COUNT];
    const char *const trafficNames[6] = {
        "Traffic 1", "Traffic 2", "Traffic 3", "Traffic 4", "Traffic 5", "Traffic 6"};
    const float trafficOffset = 1.2f;
    const float trafficSpeed = 0.45f;
    const float turnLerp = 0.3f;
    const float walkAccel = 0.12f;
    const float walkFriction = 0.08f;
    const float walkSpeed = 1.0f;
    const float walkTurn = 0.25f;
};