"""Turn-based trading, guild, and fleet model for Pico Hanse."""

from micropython import const


SCREEN_TITLE = const(0)
SCREEN_PORT = const(1)
SCREEN_MARKET = const(2)
SCREEN_MAP = const(3)
SCREEN_CARGO = const(4)
SCREEN_SHIPYARD = const(5)
SCREEN_LEDGER = const(6)
SCREEN_HELP = const(7)
SCREEN_EVENT = const(8)
SCREEN_END = const(9)
SCREEN_CONTRACTS = const(10)
SCREEN_OFFICE = const(11)
SCREEN_FLEET = const(12)
SCREEN_TAVERN = const(13)
SCREEN_RIVALS = const(14)
SCREEN_WAIT = const(15)
SCREEN_MODE = const(16)
SCREEN_OVERVIEW = const(17)
SCREEN_CITY = const(18)
SCREEN_LOG = const(19)
SCREEN_ADVISER = const(20)
SCREEN_ROUTE = const(21)
SCREEN_BUSINESS = const(22)
SCREEN_DECISION = const(23)
SCREEN_COUNCIL = const(24)
SCREEN_BANK = const(25)
SCREEN_AUDIO = const(26)
SCREEN_SAVES = const(27)

CAMPAIGN_DAYS = const(240)
WEALTH_GOAL = const(6000)
STARTING_CASH = const(600)
STARTING_CAPACITY = const(30)
MAX_CAPACITY = const(50)
MAX_SHIPS = const(3)
MAX_ACTIVE_CONTRACTS = const(3)
SAVE_VERSION = const(8)

MODE_CAREER = const(0)
MODE_QUICK = const(1)

RANK_MERCHANT = const(0)
RANK_COUNCILLOR = const(1)
RANK_MAYOR = const(2)
RANK_ALDERMAN = const(3)
RANK_NAMES = ("MERCHANT", "COUNCILLOR", "MAYOR", "ALDERMAN")
COUNCILLOR_REPUTATION = const(6)
COUNCILLOR_WEALTH = const(1200)
MAYOR_REPUTATION = const(12)
MAYOR_WEALTH = const(2500)
ALDERMAN_REPUTATION = const(20)
ALDERMAN_WEALTH = const(5000)
MAYOR_ELECTION_DAYS = const(60)
HANSE_ELECTION_DAYS = const(120)

EVENT_NONE = const(0)
EVENT_SHORTAGE = const(1)
EVENT_FAIR = const(2)
EVENT_FIRE = const(3)
EVENT_FESTIVAL = const(4)
EVENT_BLOCKADE = const(5)
EVENT_SICKNESS = const(6)
EVENT_NAMES = (
    "CALM", "SHORTAGE", "FAIR", "WAREHOUSE FIRE",
    "GUILD FESTIVAL", "BLOCKADE", "SICKNESS",
)

DECISION_NONE = const(0)
DECISION_STORM = const(1)
DECISION_PIRATES = const(2)
DECISION_RESCUE = const(3)
DECISION_WRECK = const(4)
DECISION_BLOCKADE = const(5)
DECISION_FIRE = const(6)

SAVE_MODE_LOAD = const(0)
SAVE_MODE_NEW = const(1)

MAX_LOAN = const(2000)
LOAN_STEP = const(250)
INSURANCE_PREMIUM = const(1)

SHIP_NAME = const(0)
SHIP_CAPTAIN = const(1)
SHIP_HULL = const(2)
SHIP_CAPACITY = const(3)
SHIP_CARGO = const(4)
SHIP_PORT = const(5)
SHIP_EARNINGS = const(6)
SHIP_READY_DAY = const(7)
SHIP_DEST = const(8)
SHIP_ORDER = const(9)

ORDER_READY = const(0)
ORDER_SAIL = const(1)
ORDER_WAIT = const(2)

ROUTE_OFF = const(0)
ROUTE_RUNNING = const(1)
ROUTE_PAUSED = const(2)
ROUTE_ATTENTION = const(3)
ROUTE_STATE = const(0)
ROUTE_CURSOR = const(1)
ROUTE_RESERVE = const(2)
ROUTE_REPAIR = const(3)
ROUTE_PORTS = const(4)
ROUTE_RULES = const(5)
ROUTE_PROFIT = const(6)
ROUTE_NOTE = const(7)
MAX_ROUTE_PORTS = const(4)
MAX_ROUTE_GOODS = const(3)
AUTO_CARGO_TARGET = const(6)

LEDGER_REVENUE = const(0)
LEDGER_COST = const(1)
LEDGER_VISITS = const(2)
LEDGER_PORTS = const(3)

SHIP_COG = const(0)
SHIP_KRAIER = const(1)
SHIP_HULK = const(2)
SHIP_TYPE_NAMES = ("COG", "KRAIER", "HULK")
SHIP_TYPE_CAPACITY = (30, 30, 40)
SHIP_TYPE_COST = (0, 900, 1300)
# Sailing-day modifiers: the kraier is quick; the broad hulk is deliberate.
SHIP_TYPE_SPEED = (0, -1, 1)

WEATHER_CLEAR = const(0)
WEATHER_RAIN = const(1)
WEATHER_STORM = const(2)
WEATHER_SNOW = const(3)
WEATHER_ICE = const(4)
WEATHER_NAMES = ("CLEAR", "RAIN", "STORM", "SNOW", "SEA ICE")
SEASON_NAMES = ("SPRING", "SUMMER", "AUTUMN", "WINTER")

PROJECT_GOOD_A = const(0)
PROJECT_NEED_A = const(1)
PROJECT_HAVE_A = const(2)
PROJECT_GOOD_B = const(3)
PROJECT_NEED_B = const(4)
PROJECT_HAVE_B = const(5)
PROJECT_DEADLINE = const(6)
PROJECT_COMPLETE = const(7)

MISSION_ID = const(0)
MISSION_STATE = const(1)
MISSION_GOOD = const(2)
MISSION_QTY = const(3)
MISSION_ORIGIN = const(4)
MISSION_DEST = const(5)
MISSION_DEADLINE = const(6)
MISSION_REWARD = const(7)
MISSION_OFFERED = const(0)
MISSION_ACTIVE = const(1)

SOUND_TRADE = const(1)
SOUND_SAIL = const(2)
SOUND_NOTIFY = const(4)
SOUND_BUILD = const(8)
SOUND_MISSION = const(16)
SOUND_WARNING = const(32)
SOUND_ELECTION = const(64)

CONTRACT_GOOD = const(0)
CONTRACT_QTY = const(1)
CONTRACT_ORIGIN = const(2)
CONTRACT_DEST = const(3)
CONTRACT_DEADLINE = const(4)
CONTRACT_REWARD = const(5)

PORT_NAMES = (
    "LUBECK", "HAMBURG", "BREMEN", "ROSTOCK",
    "DANZIG", "RIGA", "VISBY", "STOCKHOLM",
)

PORT_POSITIONS = (
    (81, 220), (48, 226), (22, 246), (107, 203),
    (160, 207), (183, 127), (143, 125), (158, 74),
)

GOOD_NAMES = (
    "GRAIN", "FISH", "TIMBER", "SALT",
    "CLOTH", "IRON", "BEER", "WAX",
)
GOOD_BASE_PRICES = (18, 14, 12, 24, 38, 34, 20, 42)

PORT_TARGET_SUPPLY = (
    (55, 45, 40, 55, 65, 45, 70, 40),
    (45, 50, 50, 40, 55, 60, 65, 45),
    (65, 40, 45, 50, 55, 45, 70, 35),
    (60, 70, 55, 45, 40, 35, 60, 45),
    (75, 55, 70, 35, 35, 45, 50, 55),
    (65, 60, 75, 40, 30, 50, 35, 75),
    (45, 80, 45, 70, 35, 30, 45, 55),
    (35, 60, 80, 30, 55, 75, 30, 65),
)

PORT_MOTTO = (
    "QUEEN OF THE HANSE", "GATE TO THE ELBE", "MARKET OF THE WESER",
    "SAILS OF THE WARNOW", "GRAIN PORT OF PRUSSIA",
    "WAREHOUSES OF LIVONIA", "ISLAND CROSSROADS", "CROWN OF THE NORTH",
)

HARBOR_LOCATIONS = (
    "COUNTING HOUSE", "GUILD HALL", "SHIPYARD",
    "MARKET SQUARE", "TAVERN", "HARBOUR GATE",
)

HARBOR_PRIMARY = (
    "HOUSE OVERVIEW", "GUILD CONTRACTS", "REPAIR OR EXPAND",
    "TRADE GOODS", "HEAR RUMOURS", "OPEN SEA CHART",
)

HARBOR_SECONDARY = (
    "TRADING OFFICE", "ASK ADVISER", "MANAGE FLEET",
    "CITY NEEDS", "RIVAL HOUSES", "WAIT IN PORT",
)

SHIP_NAMES = ("SEA LARK", "GOLDEN COG", "NORTH STAR")
CAPTAIN_NAMES = ("ANNA", "HINRIK", "MARTA")
CAPTAIN_TRADE_BONUS = (0, 2, 4)
CAPTAIN_STORM_GUARD = (0, 2, 4)
CAPTAIN_TRAITS = ("BROKER", "NAVIGATOR", "STORMWISE")
RIVAL_NAMES = ("HOUSE KRUZE", "HOUSE VOSS", "HOUSE DAHL")
CITY_PROJECT_NAMES = (
    "NEW QUAY", "GUILD WAREHOUSE", "WESER MARKET", "SHIP BASIN",
    "GRAIN CRANE", "STONE WHARF", "CITY GRANARY", "ROYAL PIER",
)
CITY_PROJECT_GOODS = (
    (2, 20, 5, 10), (2, 18, 6, 12), (0, 18, 2, 12), (2, 22, 5, 8),
    (2, 16, 5, 12), (2, 20, 3, 10), (0, 16, 2, 14), (2, 18, 4, 10),
)

BUSINESS_NAMES = (
    "GRAIN FARM", "FISHERY", "SAWMILL", "SALT WORKS",
    "WEAVING HALL", "IRON WORKS", "BREWERY", "APIARY",
)
BUSINESS_INPUT = (-1, -1, -1, -1, -1, 2, 0, -1)
BUSINESS_COST = (240, 260, 250, 310, 360, 430, 330, 290)
PORT_BUSINESSES = (
    (6, 4, 2, 5), (6, 1, 4, 3), (0, 6, 5, 2), (1, 2, 6, 4),
    (0, 2, 6, 5), (7, 2, 4, 5), (1, 3, 7, 4), (5, 2, 1, 7),
)
MAX_BUSINESS_LEVEL = const(3)
MAX_BUSINESS_TYPES = const(3)

STORY_NAMES = (
    "WINTER RELIEF", "GUILD TIMBERS", "HERRING FEAST",
    "COUNCIL CLOTH", "IRON FOR THE WALL", "SALT FOR RIGA",
    "BEER FOR THE HANSETAG", "WAX FOR THE CHAPEL",
    "GRAIN FOR VISBY", "ROPEYARD IRON",
)
STORY_GOODS = (0, 2, 1, 4, 5, 3, 6, 7, 0, 5)
STORY_QTY = (10, 12, 10, 8, 9, 11, 12, 7, 14, 10)

COUNCIL_ISSUES = (
    "WINTER GRAIN", "QUAY REPAIRS", "CONVOY LEVY",
    "GUILD CHARTER", "CITY WALLS", "MARKET TOLLS",
)
COUNCIL_OPTIONS = (
    ("FUND RELIEF", "SHARE COST", "PROTECT TREASURY"),
    ("REBUILD NOW", "PATCH THE QUAY", "DELAY WORK"),
    ("ARM CONVOYS", "HIRE ESCORTS", "REFUSE LEVY"),
    ("BACK SMALL HOUSES", "SEEK COMPROMISE", "BACK OLD GUILDS"),
    ("RAISE STONE WALLS", "REPAIR GATES", "TRUST THE WATCH"),
    ("LOWER TOLLS", "KEEP TOLLS", "RAISE TOLLS"),
)


def _clamp(value, low, high):
    return low if value < low else high if value > high else value


class GameModel:
    """All deterministic campaign state, independent of display and storage."""

    __slots__ = (
        "day", "cash", "reputation", "ships", "active_ship", "markets",
        "price_history", "city_events", "contract_offers", "active_contracts",
        "offices", "warehouses", "rivals", "rng_state", "screen",
        "title_selection", "menu_selection", "market_selection", "map_selection",
        "shipyard_selection", "contract_tab", "contract_selection",
        "office_selection", "fleet_selection", "help_page", "return_screen",
        "status", "event_title", "event_text", "result_title", "result_text",
        "voyages", "trade_profit", "save_available", "game_mode", "rank",
        "home_port", "mode_selection", "wait_days", "round_days",
        "round_cost", "round_lines", "pending_costs", "overview_selection",
        "scroll_selection", "pinned_contract", "recent_log", "tutorial_step",
        "ship_routes", "route_ship", "city_prosperity", "city_projects",
        "captain_xp", "ship_types", "rival_routes", "weather",
        "businesses", "business_selection", "route_ledgers",
        "rival_pressure", "rival_news", "story_mission", "story_completed",
        "sound_events", "audio_files_missing", "music_enabled",
        "effects_enabled", "audio_volume", "audio_selection",
        "decision_type", "decision_selection", "decision_title",
        "decision_text", "decision_ship", "loan", "insured",
        "bank_selection", "council_favor", "council_issue",
        "council_selection", "council_next_day", "council_decisions",
        "save_slot", "save_selection", "save_mode", "save_confirm", "save_summaries",
        "result_page", "goods_bought", "goods_sold",
        "contracts_completed", "projects_completed", "events_resolved",
        "interest_paid", "insurance_claims",
    )

    def __init__(self, seed=0x48A5E, game_mode=MODE_CAREER):
        self.day = 1
        self.cash = STARTING_CASH
        self.reputation = 0
        self.game_mode = MODE_QUICK if game_mode == MODE_QUICK else MODE_CAREER
        self.rank = RANK_MERCHANT
        self.home_port = 0
        self.rng_state = seed & 0x7FFFFFFF
        self.ships = [[
            0, 0, 100, STARTING_CAPACITY, [0] * len(GOOD_NAMES), 0, 0,
            0, -1, ORDER_READY,
        ]]
        self.ship_routes = [self._new_route()]
        self.route_ledgers = [self._new_route_ledger()]
        self.route_ship = 0
        self.active_ship = 0
        self.markets = []
        for port_index in range(len(PORT_NAMES)):
            row = []
            for good_index in range(len(GOOD_NAMES)):
                row.append(_clamp(
                    PORT_TARGET_SUPPLY[port_index][good_index] + self._rand(11) - 5,
                    8, 95,
                ))
            self.markets.append(row)
        self.city_events = [[EVENT_NONE, 0, 0] for _ in PORT_NAMES]
        self.price_history = []
        for port in range(len(PORT_NAMES)):
            self.price_history.append([[self.price(port, good)] for good in range(len(GOOD_NAMES))])
        self.contract_offers = [[] for _ in PORT_NAMES]
        self.active_contracts = []
        self.offices = [0] * len(PORT_NAMES)
        self.warehouses = [[0] * len(GOOD_NAMES) for _ in PORT_NAMES]
        self.rivals = [
            [0, 2, 750, 4],
            [1, 5, 680, 3],
            [2, 7, 820, 5],
        ]
        self.rival_routes = []
        for rival in self.rivals:
            destination = (rival[1] + 2 + rival[0]) % len(PORT_NAMES)
            self.rival_routes.append([rival[1], destination, rival[3]])
        self.rival_pressure = [0] * len(PORT_NAMES)
        self.rival_news = "RIVAL HOUSES WATCH THE MARKET"
        self.city_prosperity = [50] * len(PORT_NAMES)
        self.city_projects = []
        for port in range(len(PORT_NAMES)):
            goods = CITY_PROJECT_GOODS[port]
            self.city_projects.append([
                goods[0], goods[1], 0, goods[2], goods[3], 0,
                55 + port * 3, 0,
            ])
        self.captain_xp = [0]
        self.ship_types = [SHIP_COG]
        self.weather = WEATHER_CLEAR
        self.businesses = [[0] * len(GOOD_NAMES) for _ in PORT_NAMES]
        self.business_selection = 0
        self.story_completed = 0
        self.story_mission = self._new_story_mission(0, 0)
        self.sound_events = 0
        self.audio_files_missing = True
        self.music_enabled = True
        self.effects_enabled = True
        self.audio_volume = 50
        self.audio_selection = 0
        self.decision_type = DECISION_NONE
        self.decision_selection = 0
        self.decision_title = ""
        self.decision_text = ""
        self.decision_ship = 0
        self.loan = 0
        self.insured = False
        self.bank_selection = 0
        self.council_favor = 10
        self.council_issue = 0
        self.council_selection = 0
        self.council_next_day = 1
        self.council_decisions = 0
        self.save_slot = 0
        self.save_selection = 0
        self.save_mode = SAVE_MODE_LOAD
        self.save_confirm = False
        self.save_summaries = [None, None, None]
        self.result_page = 0
        self.goods_bought = 0
        self.goods_sold = 0
        self.contracts_completed = 0
        self.projects_completed = 0
        self.events_resolved = 0
        self.interest_paid = 0
        self.insurance_claims = 0
        for port in range(len(PORT_NAMES)):
            self._refresh_contracts(port)

        self.screen = SCREEN_TITLE
        self.title_selection = 0
        self.menu_selection = 0
        self.market_selection = 0
        self.map_selection = 1
        self.shipyard_selection = 0
        self.contract_tab = 0
        self.contract_selection = 0
        self.office_selection = 0
        self.fleet_selection = 0
        self.help_page = 0
        self.mode_selection = 0
        self.wait_days = 1
        self.overview_selection = 0
        self.scroll_selection = 0
        self.return_screen = SCREEN_PORT
        self.status = "WELCOME, MERCHANT"
        self.event_title = ""
        self.event_text = ""
        self.result_title = ""
        self.result_text = ""
        self.voyages = 0
        self.trade_profit = 0
        self.save_available = False
        self.round_days = 0
        self.round_cost = 0
        self.round_lines = []
        self.pending_costs = 0
        self.pinned_contract = -1
        self.recent_log = ["HOUSE LEDGER OPENED IN LUBECK"]
        self.tutorial_step = 0

    @staticmethod
    def _new_route():
        return [ROUTE_OFF, 0, 100, 40, [], [], 0, "NOT CONFIGURED"]

    @staticmethod
    def _new_route_ledger():
        return [0, 0, 0, [0] * len(PORT_NAMES)]

    def _new_story_mission(self, mission_id, origin):
        mission_id %= len(STORY_NAMES)
        destination = (origin + 2 + mission_id) % len(PORT_NAMES)
        if destination == origin:
            destination = (destination + 1) % len(PORT_NAMES)
        qty = STORY_QTY[mission_id]
        travel = self.route_days_from(origin, destination)
        reward = qty * GOOD_BASE_PRICES[STORY_GOODS[mission_id]] + 120 + travel * 18
        return [
            mission_id, MISSION_OFFERED, STORY_GOODS[mission_id], qty,
            origin, destination, self.day + travel + 16, reward,
        ]

    def _rand(self, limit):
        self.rng_state = (1103515245 * self.rng_state + 12345) & 0x7FFFFFFF
        return 0 if limit <= 0 else (self.rng_state >> 8) % limit

    @property
    def current_port(self):
        return self.ships[self.active_ship][SHIP_PORT]

    @current_port.setter
    def current_port(self, value):
        self.ships[self.active_ship][SHIP_PORT] = int(value)

    @property
    def hull(self):
        return self.ships[self.active_ship][SHIP_HULL]

    @hull.setter
    def hull(self, value):
        self.ships[self.active_ship][SHIP_HULL] = int(value)

    @property
    def capacity(self):
        return self.ships[self.active_ship][SHIP_CAPACITY]

    @capacity.setter
    def capacity(self, value):
        self.ships[self.active_ship][SHIP_CAPACITY] = int(value)

    @property
    def cargo(self):
        return self.ships[self.active_ship][SHIP_CARGO]

    @cargo.setter
    def cargo(self, value):
        self.ships[self.active_ship][SHIP_CARGO] = value

    @property
    def cargo_used(self):
        return sum(self.cargo)

    @property
    def cargo_free(self):
        return self.capacity - self.cargo_used

    @property
    def captain_name(self):
        return CAPTAIN_NAMES[self.ships[self.active_ship][SHIP_CAPTAIN]]

    @property
    def season_index(self):
        return ((self.day - 1) // 30) % len(SEASON_NAMES)

    @property
    def season_name(self):
        return SEASON_NAMES[self.season_index]

    @property
    def weather_name(self):
        return WEATHER_NAMES[self.weather]

    def captain_level(self, ship_index):
        return min(4, 1 + self.captain_xp[ship_index] // 5)

    def captain_trait(self, ship_index):
        return CAPTAIN_TRAITS[self.ships[ship_index][SHIP_CAPTAIN]]

    def captain_trade_bonus(self, ship_index):
        captain = self.ships[ship_index][SHIP_CAPTAIN]
        level = self.captain_level(ship_index)
        return CAPTAIN_TRADE_BONUS[captain] + (level * 2 if captain == 0 else level - 1)

    def captain_storm_guard(self, ship_index):
        captain = self.ships[ship_index][SHIP_CAPTAIN]
        level = self.captain_level(ship_index)
        return CAPTAIN_STORM_GUARD[captain] + (level * 2 if captain == 2 else level - 1)

    def city_condition(self, port=None):
        if port is None:
            port = self.current_port
        value = self.city_prosperity[port]
        if value < 25:
            return "STARVING"
        if value < 45:
            return "STRUGGLING"
        if value < 65:
            return "STABLE"
        if value < 85:
            return "PROSPEROUS"
        return "BOOMING"

    def project_progress(self, port=None):
        if port is None:
            port = self.current_port
        project = self.city_projects[port]
        return (
            project[PROJECT_HAVE_A] + project[PROJECT_HAVE_B],
            project[PROJECT_NEED_A] + project[PROJECT_NEED_B],
        )

    def _complete_project(self, port):
        project = self.city_projects[port]
        if project[PROJECT_COMPLETE]:
            return False
        if (project[PROJECT_HAVE_A] < project[PROJECT_NEED_A]
                or project[PROJECT_HAVE_B] < project[PROJECT_NEED_B]):
            return False
        project[PROJECT_COMPLETE] = 1
        self.city_prosperity[port] = min(100, self.city_prosperity[port] + 15)
        self.cash += 120
        self.reputation += 2
        self.projects_completed += 1
        self.status = CITY_PROJECT_NAMES[port] + " COMPLETED"
        self._log(self.status)
        self.emit_sound(SOUND_BUILD | SOUND_MISSION)
        self._check_goal()
        return True

    def contribute_project(self, ship_index=None, automatic=False):
        if ship_index is None:
            ship_index = self.active_ship
        ship = self.ships[ship_index]
        port = ship[SHIP_PORT]
        project = self.city_projects[port]
        if project[PROJECT_COMPLETE]:
            self.status = CITY_PROJECT_NAMES[port] + " ALREADY COMPLETE"
            return 0
        cargo = ship[SHIP_CARGO]
        moved = 0
        for good_at, need_at, have_at in (
            (PROJECT_GOOD_A, PROJECT_NEED_A, PROJECT_HAVE_A),
            (PROJECT_GOOD_B, PROJECT_NEED_B, PROJECT_HAVE_B),
        ):
            needed = max(0, project[need_at] - project[have_at])
            available = cargo[project[good_at]]
            if automatic:
                protected = 0
                for contract in self.active_contracts:
                    if contract[CONTRACT_GOOD] == project[good_at]:
                        protected += contract[CONTRACT_QTY]
                mission = self.story_mission
                if (mission[MISSION_STATE] == MISSION_ACTIVE
                        and mission[MISSION_GOOD] == project[good_at]):
                    protected += mission[MISSION_QTY]
                available = max(0, available - protected)
            amount = min(available, needed)
            if amount:
                cargo[project[good_at]] -= amount
                project[have_at] += amount
                moved += amount
        if moved:
            self.city_prosperity[port] = min(100, self.city_prosperity[port] + max(1, moved // 4))
            completed = self._complete_project(port)
            if not completed:
                self.status = "DONATED %d CRATES TO %s" % (moved, CITY_PROJECT_NAMES[port])
                if not automatic:
                    self._log(self.status)
        elif not automatic:
            self.status = "BRING %s OR %s" % (
                GOOD_NAMES[project[PROJECT_GOOD_A]], GOOD_NAMES[project[PROJECT_GOOD_B]],
            )
        return moved

    @property
    def ship_name(self):
        return SHIP_NAMES[self.ships[self.active_ship][SHIP_NAME]]

    def _log(self, text):
        self.recent_log.append("D%d %s" % (self.day, str(text)))
        if len(self.recent_log) > 10:
            self.recent_log.pop(0)

    def emit_sound(self, event):
        self.sound_events |= event

    def take_sound_events(self):
        events = self.sound_events
        self.sound_events = 0
        return events

    def local_business_choices(self, port=None):
        if port is None:
            port = self.current_port
        return PORT_BUSINESSES[port]

    def business_build_cost(self, good, port=None):
        if port is None:
            port = self.current_port
        level = self.businesses[port][good]
        return BUSINESS_COST[good] + level * (120 + BUSINESS_COST[good] // 4) + self.rival_pressure[port] * 6

    def business_slots_used(self, port=None):
        if port is None:
            port = self.current_port
        return sum(1 for level in self.businesses[port] if level)

    def build_business(self, choice=None):
        port = self.current_port
        if not self.offices[port]:
            self.status = "OPEN A TRADING OFFICE FIRST"
            return False
        choices = self.local_business_choices(port)
        if choice is None:
            choice = self.business_selection
        choice = _clamp(int(choice), 0, len(choices) - 1)
        good = choices[choice]
        level = self.businesses[port][good]
        if level >= MAX_BUSINESS_LEVEL:
            self.status = BUSINESS_NAMES[good] + " AT MAXIMUM"
            return False
        if level == 0 and self.business_slots_used(port) >= MAX_BUSINESS_TYPES:
            self.status = "THREE WORKSHOP PLOTS ALREADY USED"
            return False
        cost = self.business_build_cost(good, port)
        if self.cash < cost:
            self.status = "%s COSTS %d SILVER" % (BUSINESS_NAMES[good], cost)
            return False
        self.cash -= cost
        self.businesses[port][good] = level + 1
        self.city_prosperity[port] = min(100, self.city_prosperity[port] + 2)
        self.status = "%s LEVEL %d" % (BUSINESS_NAMES[good], level + 1)
        self._log(self.status + " IN " + PORT_NAMES[port])
        self.emit_sound(SOUND_BUILD)
        self._check_goal()
        return True

    def business_daily_wage(self):
        return sum(sum(levels) for levels in self.businesses) * 2

    def market_forecast(self, port, good):
        event = self.city_events[port]
        if event[0] == EVENT_SHORTAGE and event[1] == good:
            return "UP"
        if event[0] == EVENT_FAIR and event[1] == good:
            return "DOWN"
        supply = self.markets[port][good]
        target = PORT_TARGET_SUPPLY[port][good]
        trend = self.price_trend(port, good)
        if supply < target - 8 or trend > 0:
            return "UP"
        if supply > target + 8 or trend < 0:
            return "DOWN"
        return "EVEN"

    def route_account(self, ship_index):
        ledger = self.route_ledgers[ship_index]
        return ledger[LEDGER_REVENUE], ledger[LEDGER_COST], ledger[LEDGER_REVENUE] - ledger[LEDGER_COST]

    def story_status_text(self):
        mission = self.story_mission
        name = STORY_NAMES[mission[MISSION_ID]]
        if mission[MISSION_STATE] == MISSION_OFFERED:
            return "%s OFFER IN %s" % (name, PORT_NAMES[mission[MISSION_ORIGIN]])
        return "%s TO %s BY D%d" % (
            name, PORT_NAMES[mission[MISSION_DEST]], mission[MISSION_DEADLINE],
        )

    def accept_story_mission(self):
        mission = self.story_mission
        if mission[MISSION_STATE] != MISSION_OFFERED:
            self.status = self.story_status_text()
            return False
        if self.current_port != mission[MISSION_ORIGIN]:
            self.status = "GUILD MISSION OFFERED IN " + PORT_NAMES[mission[MISSION_ORIGIN]]
            return False
        mission[MISSION_STATE] = MISSION_ACTIVE
        self.status = STORY_NAMES[mission[MISSION_ID]] + " ACCEPTED"
        self._log(self.status)
        self.emit_sound(SOUND_NOTIFY)
        return True

    def deliver_story_mission(self):
        mission = self.story_mission
        if mission[MISSION_STATE] != MISSION_ACTIVE:
            return self.accept_story_mission()
        if self.current_port != mission[MISSION_DEST]:
            self.status = "MISSION DELIVERS IN " + PORT_NAMES[mission[MISSION_DEST]]
            return False
        good = mission[MISSION_GOOD]
        qty = mission[MISSION_QTY]
        if self.cargo[good] < qty:
            self.status = "MISSION NEEDS %d %s" % (qty, GOOD_NAMES[good])
            return False
        self.cargo[good] -= qty
        self.cash += mission[MISSION_REWARD]
        self.reputation += 3
        self.city_prosperity[self.current_port] = min(100, self.city_prosperity[self.current_port] + 6)
        self.story_completed += 1
        self.status = STORY_NAMES[mission[MISSION_ID]] + " COMPLETED"
        self._log(self.status)
        self.emit_sound(SOUND_MISSION)
        next_id = (mission[MISSION_ID] + 1) % len(STORY_NAMES)
        self.story_mission = self._new_story_mission(next_id, self.current_port)
        self._check_goal()
        return True

    def order_progress(self):
        ordered = 0
        for ship in self.ships:
            if ship[SHIP_ORDER] != ORDER_READY:
                ordered += 1
        return ordered, len(self.ships)

    def command_line(self):
        ordered, total = self.order_progress()
        order = self.ships[self.active_ship][SHIP_ORDER]
        state = "RDY" if order == ORDER_READY else "SEA" if order == ORDER_SAIL else "WAIT"
        return "%s %s %s %d/%d | %s" % (
            self.ship_name, PORT_NAMES[self.current_port], state, ordered, total,
            self.objective_badge(),
        )

    def objective_badge(self):
        index = self.objective_contract_index()
        if index >= 0:
            contract = self.active_contracts[index]
            return "%s D%d" % (PORT_NAMES[contract[CONTRACT_DEST]], contract[CONTRACT_DEADLINE])
        if self.tutorial_step < 4:
            return ("BUY", "SAIL", "ARRIVE", "SELL")[self.tutorial_step]
        if self.game_mode == MODE_QUICK:
            return "GOAL %dS" % WEALTH_GOAL
        return ("COUNCIL", "MAYOR", "HANSE", "ALDERMAN")[self.rank]

    def guidance_text(self):
        steps = (
            "FIRST VOYAGE: BUY ANY CARGO",
            "FIRST VOYAGE: CHOOSE SAIL",
            "FIRST VOYAGE: REACH THE NEXT PORT",
            "FIRST VOYAGE: SELL YOUR CARGO",
            "TRADE, BUILD OFFICES, WIN ELECTIONS",
        )
        return steps[_clamp(self.tutorial_step, 0, 4)]

    def urgent_contract_index(self):
        if not self.active_contracts:
            return -1
        best = 0
        for index in range(1, len(self.active_contracts)):
            if self.active_contracts[index][CONTRACT_DEADLINE] < self.active_contracts[best][CONTRACT_DEADLINE]:
                best = index
        return best

    def objective_contract_index(self):
        if 0 <= self.pinned_contract < len(self.active_contracts):
            return self.pinned_contract
        return self.urgent_contract_index()

    def objective_text(self):
        index = self.objective_contract_index()
        if index >= 0:
            contract = self.active_contracts[index]
            return "%d %s TO %s BY D%d" % (
                contract[CONTRACT_QTY], GOOD_NAMES[contract[CONTRACT_GOOD]],
                PORT_NAMES[contract[CONTRACT_DEST]], contract[CONTRACT_DEADLINE],
            )
        if self.tutorial_step < 4:
            return self.guidance_text()
        if self.game_mode == MODE_QUICK:
            return "REACH %dS BY DAY %d" % (WEALTH_GOAL, CAMPAIGN_DAYS)
        if self.rank == RANK_MERCHANT:
            return "COUNCIL: %d REP, %dS, LUBECK OFFICE" % (
                COUNCILLOR_REPUTATION, COUNCILLOR_WEALTH,
            )
        if self.rank == RANK_COUNCILLOR:
            return "MAYOR: %d REP, %dS, SUPPORT %d/30" % (
                MAYOR_REPUTATION, MAYOR_WEALTH, self.council_favor,
            )
        if self.rank == RANK_MAYOR:
            return "ALDERMAN: %d REP, %dS, SUPPORT %d/60" % (
                ALDERMAN_REPUTATION, ALDERMAN_WEALTH, self.council_favor,
            )
        return "THE HANSE ACKNOWLEDGES YOUR HOUSE"

    def city_need_level(self, port, good):
        event = self.city_events[port]
        if event[0] == EVENT_SHORTAGE and event[1] == good:
            return "URGENT"
        supply = self.markets[port][good]
        if supply <= 28:
            return "HIGH"
        if supply <= 48:
            return "MED"
        return "LOW"

    def city_needs(self, port=None, count=3):
        if port is None:
            port = self.current_port
        scored = []
        for good in range(len(GOOD_NAMES)):
            event = self.city_events[port]
            priority = -100 if event[0] == EVENT_SHORTAGE and event[1] == good else 0
            scored.append((priority + self.markets[port][good], good))
        scored.sort()
        return [item[1] for item in scored[:count]]

    def city_produces(self, port=None, count=3):
        if port is None:
            port = self.current_port
        scored = [(-PORT_TARGET_SUPPLY[port][good], good) for good in range(len(GOOD_NAMES))]
        scored.sort()
        return [item[1] for item in scored[:count]]

    def city_event_text(self, port=None):
        if port is None:
            port = self.current_port
        event = self.city_events[port]
        if event[0] in (EVENT_SHORTAGE, EVENT_FAIR):
            return GOOD_NAMES[event[1]] + " " + EVENT_NAMES[event[0]]
        if event[0] != EVENT_NONE:
            return EVENT_NAMES[event[0]]
        return "NO SPECIAL EVENT"

    def contract_slack(self, destination):
        slack = None
        for contract in self.active_contracts:
            if contract[CONTRACT_DEST] == destination:
                value = contract[CONTRACT_DEADLINE] - self.day - self.route_days(destination)
                if slack is None or value < slack:
                    slack = value
        return slack

    def advice(self):
        index = self.objective_contract_index()
        if index >= 0:
            contract = self.active_contracts[index]
            good = contract[CONTRACT_GOOD]
            if contract[CONTRACT_DEST] == self.current_port and self.cargo[good] >= contract[CONTRACT_QTY]:
                return "DELIVER THE PINNED CONTRACT AT THE GUILD NOW."
            if self.cargo[good] < contract[CONTRACT_QTY]:
                return "FIND %d %s FOR THE CONTRACT TO %s." % (
                    contract[CONTRACT_QTY] - self.cargo[good], GOOD_NAMES[good],
                    PORT_NAMES[contract[CONTRACT_DEST]],
                )
            return "SET SAIL FOR %s. THE CONTRACT IS DUE DAY %d." % (
                PORT_NAMES[contract[CONTRACT_DEST]], contract[CONTRACT_DEADLINE],
            )
        event = self.city_events[self.current_port]
        if event[0] == EVENT_SHORTAGE and self.cargo[event[1]]:
            return "SELL %s HERE. THE CITY HAS AN URGENT SHORTAGE." % GOOD_NAMES[event[1]]
        if self.cargo_used:
            best = None
            for good in range(len(GOOD_NAMES)):
                if not self.cargo[good]:
                    continue
                for port in range(len(PORT_NAMES)):
                    gain = self.price(port, good) - self.price(self.current_port, good)
                    if best is None or gain > best[0]:
                        best = (gain, good, port)
            if best is not None and best[0] > 0:
                return "YOUR %s SHOULD FETCH MORE IN %s." % (
                    GOOD_NAMES[best[1]], PORT_NAMES[best[2]],
                )
        produced = self.city_produces(self.current_port, 1)[0]
        return "CHECK THE MARKET FOR %s, THEN COMPARE DESTINATIONS." % GOOD_NAMES[produced]

    def price(self, port_index, good_index):
        supply = self.markets[port_index][good_index]
        base = GOOD_BASE_PRICES[good_index]
        value = max(3, (base * (150 - supply) + 39) // 80)
        event = self.city_events[port_index]
        if event[0] and event[1] == good_index:
            if event[0] in (EVENT_SHORTAGE, EVENT_FIRE, EVENT_BLOCKADE, EVENT_SICKNESS):
                value = value * 3 // 2
            elif event[0] in (EVENT_FAIR, EVENT_FESTIVAL):
                value = value * 5 // 4
        return max(3, value)

    def buy_price(self, good_index):
        value = self.price(self.current_port, good_index)
        bonus = self.captain_trade_bonus(self.active_ship)
        return max(2, value * (100 - bonus) // 100)

    def sell_price(self, good_index):
        value = self.price(self.current_port, good_index) * 9 // 10
        bonus = self.captain_trade_bonus(self.active_ship)
        return max(1, value * (100 + bonus) // 100)

    def _route_buy_price(self, ship_index, port, good):
        bonus = self.captain_trade_bonus(ship_index)
        return max(2, self.price(port, good) * (100 - bonus) // 100)

    def _route_sell_price(self, ship_index, port, good):
        bonus = self.captain_trade_bonus(ship_index)
        value = self.price(port, good) * 9 // 10
        return max(1, value * (100 + bonus) // 100)

    def price_trend(self, port, good):
        history = self.price_history[port][good]
        if len(history) < 2 or history[-1] == history[-2]:
            return 0
        return 1 if history[-1] > history[-2] else -1

    def wealth(self):
        total = self.cash
        for ship in self.ships:
            total += (ship[SHIP_CAPACITY] - STARTING_CAPACITY) * 18
            for good in range(len(GOOD_NAMES)):
                total += ship[SHIP_CARGO][good] * max(1, self.price(ship[SHIP_PORT], good) * 9 // 10)
        for port in range(len(PORT_NAMES)):
            if self.offices[port]:
                total += 220
            for good in range(len(GOOD_NAMES)):
                total += self.warehouses[port][good] * GOOD_BASE_PRICES[good]
        total += max(0, len(self.ships) - 1) * 600
        return max(0, total - self.loan)

    def route_days(self, destination):
        return self.sailing_days(self.active_ship, destination)

    def weather_penalty(self, origin, destination):
        if origin == destination:
            return 0
        if self.weather == WEATHER_STORM:
            return 2
        if self.weather in (WEATHER_RAIN, WEATHER_SNOW):
            return 1
        if self.weather == WEATHER_ICE:
            return 2 if self.season_index == 3 else 1
        return 0

    def sailing_days(self, ship_index, destination):
        origin = self.ships[ship_index][SHIP_PORT]
        if origin == destination:
            return 0
        days = self.route_days_from(origin, destination)
        days += self.weather_penalty(origin, destination)
        days += SHIP_TYPE_SPEED[self.ship_types[ship_index]]
        if self.ships[ship_index][SHIP_CAPTAIN] == 1 and self.captain_level(ship_index) >= 2:
            days -= 1
        return _clamp(days, 1, 8)

    def buy(self, good, amount=1):
        amount = max(1, amount)
        price = self.buy_price(good)
        amount = min(amount, self.cargo_free, self.markets[self.current_port][good] // 3, self.cash // price)
        if amount <= 0:
            self.status = "NO ROOM, STOCK, OR SILVER"
            return False
        self.cash -= price * amount
        self.goods_bought += amount
        self.cargo[good] += amount
        self.markets[self.current_port][good] = max(4, self.markets[self.current_port][good] - amount * 2)
        self.status = "BOUGHT %d %s" % (amount, GOOD_NAMES[good])
        self._log(self.status)
        self.emit_sound(SOUND_TRADE)
        if self.tutorial_step == 0:
            self.tutorial_step = 1
        return True

    def sell(self, good, amount=1):
        amount = min(max(1, amount), self.cargo[good])
        if amount <= 0:
            self.status = "NONE ABOARD"
            return False
        income = self.sell_price(good) * amount
        self.cash += income
        self.ships[self.active_ship][SHIP_EARNINGS] += income
        self.trade_profit += income
        self.goods_sold += amount
        self.cargo[good] -= amount
        self.markets[self.current_port][good] = min(98, self.markets[self.current_port][good] + amount * 2)
        self.city_prosperity[self.current_port] = min(
            100, self.city_prosperity[self.current_port] + max(1, amount // 3)
        )
        self.captain_xp[self.active_ship] += 1
        event = self.city_events[self.current_port]
        if amount >= 3 and event[0] == EVENT_SHORTAGE and event[1] == good:
            self.reputation += 1
            self.status = "CITY PRAISES YOUR DELIVERY"
        else:
            self.status = "SOLD %d %s" % (amount, GOOD_NAMES[good])
        self._log(self.status)
        self.emit_sound(SOUND_TRADE)
        if self.tutorial_step == 3:
            self.tutorial_step = 4
        self._check_goal()
        return True

    def _record_prices(self):
        for port in range(len(PORT_NAMES)):
            for good in range(len(GOOD_NAMES)):
                history = self.price_history[port][good]
                history.append(self.price(port, good))
                if len(history) > 4:
                    history.pop(0)

    def _advance_city_events(self):
        news = ""
        for event in self.city_events:
            if event[2] > 0:
                event[2] -= 1
                if event[2] <= 0:
                    event[0] = EVENT_NONE
        if self._rand(100) < 12:
            port = self._rand(len(PORT_NAMES))
            if self.city_events[port][0] == EVENT_NONE:
                kind = 1 + self._rand(6)
                if kind == EVENT_FAIR:
                    good = (1, 4, 6)[self._rand(3)]
                elif kind == EVENT_FIRE:
                    good = 2
                    self.city_prosperity[port] = max(0, self.city_prosperity[port] - 4)
                elif kind == EVENT_FESTIVAL:
                    good = (4, 6, 7)[self._rand(3)]
                    self.city_prosperity[port] = min(100, self.city_prosperity[port] + 3)
                elif kind == EVENT_BLOCKADE:
                    good = (0, 3, 5)[self._rand(3)]
                elif kind == EVENT_SICKNESS:
                    good = (0, 1, 7)[self._rand(3)]
                    self.city_prosperity[port] = max(0, self.city_prosperity[port] - 3)
                else:
                    good = self._rand(len(GOOD_NAMES))
                self.city_events[port] = [kind, good, 6 + self._rand(8)]
                news = "%s IN %s" % (EVENT_NAMES[kind], PORT_NAMES[port])
        return news

    def _advance_rivals(self):
        for index in range(len(self.rivals)):
            rival = self.rivals[index]
            route = self.rival_routes[index]
            if self.day < route[2] and self.day < rival[3]:
                continue
            origin = route[0]
            destination = route[1]
            good = self._rand(len(GOOD_NAMES))
            amount = 2 + self._rand(5)
            self.markets[origin][good] = max(5, self.markets[origin][good] - amount)
            self.markets[destination][good] = min(98, self.markets[destination][good] + amount)
            rival[1] = destination
            rival[2] += 8 + self._rand(28)
            next_destination = self._rand(len(PORT_NAMES) - 1)
            if next_destination >= destination:
                next_destination += 1
            ready_day = self.day + self.route_days_from(destination, next_destination) + 1
            route[:] = [destination, next_destination, ready_day]
            rival[3] = ready_day
            self.rival_pressure[destination] = min(20, self.rival_pressure[destination] + 2)
            if self.contract_offers[destination] and self._rand(100) < 24:
                self.contract_offers[destination].pop(0)
                self.rival_news = "%s CLAIMS A %s CONTRACT" % (
                    RIVAL_NAMES[rival[0]], PORT_NAMES[destination],
                )
            elif self._rand(2) == 0:
                self.markets[destination][good] = min(98, self.markets[destination][good] + 4)
                self.rival_news = "%s UNDERCUTS %s IN %s" % (
                    RIVAL_NAMES[rival[0]], GOOD_NAMES[good], PORT_NAMES[destination],
                )
            else:
                self.rival_news = "%s BIDS FOR %s WORKSHOPS" % (
                    RIVAL_NAMES[rival[0]], PORT_NAMES[destination],
                )

    def _advance_weather(self):
        roll = self._rand(100)
        season = self.season_index
        if season == 0:
            self.weather = WEATHER_RAIN if roll < 30 else WEATHER_STORM if roll < 38 else WEATHER_CLEAR
        elif season == 1:
            self.weather = WEATHER_STORM if roll < 12 else WEATHER_RAIN if roll < 22 else WEATHER_CLEAR
        elif season == 2:
            self.weather = WEATHER_RAIN if roll < 34 else WEATHER_STORM if roll < 48 else WEATHER_CLEAR
        else:
            self.weather = WEATHER_ICE if roll < 20 else WEATHER_SNOW if roll < 48 else WEATHER_STORM if roll < 58 else WEATHER_CLEAR

    def _advance_city_projects(self):
        for port in range(len(PORT_NAMES)):
            project = self.city_projects[port]
            if project[PROJECT_COMPLETE]:
                continue
            if project[PROJECT_DEADLINE] < self.day:
                self.city_prosperity[port] = max(0, self.city_prosperity[port] - 8)
                project[PROJECT_HAVE_A] //= 2
                project[PROJECT_HAVE_B] //= 2
                project[PROJECT_DEADLINE] = self.day + 45 + port * 2
                self._log(PORT_NAMES[port] + " PROJECT DELAYED")
            if self.city_events[port][0] == EVENT_SHORTAGE and self._rand(100) < 10:
                self.city_prosperity[port] = max(0, self.city_prosperity[port] - 1)

    def _advance_businesses(self):
        paid_total = 0
        for port in range(len(PORT_NAMES)):
            for good in range(len(GOOD_NAMES)):
                level = self.businesses[port][good]
                if not level:
                    continue
                wage = level * 2 + self.rival_pressure[port] // 5
                if self.cash < wage:
                    continue
                source = BUSINESS_INPUT[good]
                if source >= 0 and self.warehouses[port][source] < level:
                    continue
                self.cash -= wage
                paid_total += wage
                if source >= 0:
                    self.warehouses[port][source] -= level
                produced = level * 2
                self.warehouses[port][good] += produced
                self.markets[port][good] = min(98, self.markets[port][good] + level)
                if self.day % 10 == port:
                    self.city_prosperity[port] = min(100, self.city_prosperity[port] + 1)
        return paid_total

    def _advance_story_mission(self):
        mission = self.story_mission
        if mission[MISSION_STATE] == MISSION_ACTIVE and mission[MISSION_DEADLINE] < self.day:
            self.reputation = max(0, self.reputation - 2)
            self._log(STORY_NAMES[mission[MISSION_ID]] + " FAILED")
            self.emit_sound(SOUND_WARNING)
            next_id = (mission[MISSION_ID] + 1) % len(STORY_NAMES)
            self.story_mission = self._new_story_mission(next_id, mission[MISSION_DEST])

    def _expire_contracts(self):
        kept = []
        expired = 0
        pinned = (
            self.active_contracts[self.pinned_contract]
            if 0 <= self.pinned_contract < len(self.active_contracts)
            else None
        )
        for contract in self.active_contracts:
            if contract[CONTRACT_DEADLINE] < self.day:
                self.reputation = max(0, self.reputation - 2)
                expired += 1
                self._log("CONTRACT EXPIRED")
            else:
                kept.append(contract)
        self.active_contracts = kept
        self.pinned_contract = -1
        if pinned is not None:
            for index in range(len(kept)):
                if kept[index] == pinned:
                    self.pinned_contract = index
                    break
        return expired

    def _advance_world(self, days):
        expired = 0
        news = ""
        office_cost = 0
        for _unused in range(days):
            self.day += 1
            if self.insured:
                if self.cash >= INSURANCE_PREMIUM:
                    self.cash -= INSURANCE_PREMIUM
                    office_cost += INSURANCE_PREMIUM
                else:
                    self.insured = False
                    self._log("INSURANCE LAPSED")
            if self.loan and self.day % 30 == 0:
                interest = max(5, self.loan // 20)
                paid = min(self.cash, interest)
                self.cash -= paid
                self.interest_paid += paid
                office_cost += paid
                if paid < interest:
                    self.loan = min(MAX_LOAN, self.loan + interest - paid)
                self._log("BANK INTEREST %dS" % interest)
            daily_office_cost = sum(self.offices)
            if daily_office_cost:
                paid = min(self.cash, daily_office_cost)
                self.cash -= paid
                office_cost += paid
            office_cost += self._advance_businesses()
            for port in range(len(PORT_NAMES)):
                for good in range(len(GOOD_NAMES)):
                    value = self.markets[port][good]
                    target = PORT_TARGET_SUPPLY[port][good]
                    value += 1 if value < target else -1 if value > target else 0
                    self.markets[port][good] = _clamp(value + self._rand(3) - 1, 5, 98)
            latest_news = self._advance_city_events()
            if latest_news:
                news = latest_news
            self._advance_weather()
            self._advance_city_projects()
            self._advance_rivals()
            self._advance_story_mission()
            if self.day % 5 == 0:
                for port in range(len(PORT_NAMES)):
                    self.rival_pressure[port] = max(0, self.rival_pressure[port] - 1)
            expired += self._expire_contracts()
            self._record_prices()
        return expired, news, office_cost

    def available_ships(self):
        return [
            index for index in range(len(self.ships))
            if self.ships[index][SHIP_ORDER] == ORDER_READY
        ]

    def manual_ready_ships(self):
        return [
            index for index in range(len(self.ships))
            if self.ships[index][SHIP_ORDER] == ORDER_READY
            and self.ship_routes[index][ROUTE_STATE] != ROUTE_RUNNING
        ]

    def route_status(self, index):
        state = self.ship_routes[index][ROUTE_STATE]
        return ("MANUAL", "ON ROUTE", "PAUSED", "ATTENTION")[state]

    @staticmethod
    def _default_route_goods(port):
        ranked = []
        for good in range(len(GOOD_NAMES)):
            ranked.append((PORT_TARGET_SUPPLY[port][good], good))
        ranked.sort(reverse=True)
        return [ranked[index][1] for index in range(MAX_ROUTE_GOODS)]

    def toggle_route_port(self, ship_index, port):
        if ship_index < 0 or ship_index >= len(self.ships):
            return False
        route = self.ship_routes[ship_index]
        ship = self.ships[ship_index]
        if route[ROUTE_STATE] == ROUTE_RUNNING or ship[SHIP_ORDER] != ORDER_READY:
            self.status = "PAUSE THE SHIP IN PORT FIRST"
            return False
        ports = route[ROUTE_PORTS]
        if port in ports:
            position = ports.index(port)
            ports.pop(position)
            route[ROUTE_RULES].pop(position)
            route[ROUTE_CURSOR] = 0
            route[ROUTE_NOTE] = "STOP REMOVED"
            self.status = PORT_NAMES[port] + " REMOVED"
            return True
        if len(ports) >= MAX_ROUTE_PORTS:
            self.status = "ROUTE ALREADY HAS FOUR PORTS"
            return False
        ports.append(port)
        route[ROUTE_RULES].append(self._default_route_goods(port))
        route[ROUTE_NOTE] = "STOP ADDED"
        self.status = PORT_NAMES[port] + " ADDED"
        return True

    def cycle_route_reserve(self, ship_index):
        route = self.ship_routes[ship_index]
        values = (50, 100, 200, 400)
        current = route[ROUTE_RESERVE]
        route[ROUTE_RESERVE] = values[(values.index(current) + 1) % len(values)] if current in values else 100
        self.status = "RESERVE %d SILVER" % route[ROUTE_RESERVE]

    def cycle_route_repair(self, ship_index):
        route = self.ship_routes[ship_index]
        values = (25, 40, 55, 70)
        current = route[ROUTE_REPAIR]
        route[ROUTE_REPAIR] = values[(values.index(current) + 1) % len(values)] if current in values else 40
        self.status = "REPAIR BELOW %d%%" % route[ROUTE_REPAIR]

    def cycle_route_goods(self, ship_index, port):
        route = self.ship_routes[ship_index]
        ship = self.ships[ship_index]
        if route[ROUTE_STATE] == ROUTE_RUNNING or ship[SHIP_ORDER] != ORDER_READY:
            self.status = "PAUSE THE SHIP IN PORT FIRST"
            return False
        if port not in route[ROUTE_PORTS]:
            self.status = "ADD THIS PORT FIRST"
            return False
        ranked = []
        for good in range(len(GOOD_NAMES)):
            ranked.append((PORT_TARGET_SUPPLY[port][good], good))
        ranked.sort(reverse=True)
        ordered = [item[1] for item in ranked]
        stop_index = route[ROUTE_PORTS].index(port)
        current = route[ROUTE_RULES][stop_index]
        offset = (ordered.index(current[0]) + 1) % len(ordered) if current else 0
        route[ROUTE_RULES][stop_index] = [
            ordered[(offset + index) % len(ordered)]
            for index in range(MAX_ROUTE_GOODS)
        ]
        route[ROUTE_NOTE] = "GOODS UPDATED"
        self.status = PORT_NAMES[port] + " GOODS UPDATED"
        return True

    def _route_trade(self, ship_index, stop_index):
        ship = self.ships[ship_index]
        route = self.ship_routes[ship_index]
        ledger = self.route_ledgers[ship_index]
        port = ship[SHIP_PORT]
        cargo = ship[SHIP_CARGO]
        sold = 0
        bought = 0

        # A captain serves an unfinished civic project before selling surplus.
        donated = self.contribute_project(ship_index, True)
        ledger[LEDGER_VISITS] += 1

        # Sell cargo where the city is below its normal supply.
        for good in range(len(GOOD_NAMES)):
            protected = 0
            for contract in self.active_contracts:
                if contract[CONTRACT_GOOD] == good:
                    protected += contract[CONTRACT_QTY]
            mission = self.story_mission
            if mission[MISSION_STATE] == MISSION_ACTIVE and mission[MISSION_GOOD] == good:
                protected += mission[MISSION_QTY]
            amount = max(0, cargo[good] - protected)
            if amount <= 0 or self.markets[port][good] > PORT_TARGET_SUPPLY[port][good] - 3:
                continue
            income = self._route_sell_price(ship_index, port, good) * amount
            self.cash += income
            ship[SHIP_EARNINGS] += income
            self.trade_profit += income
            route[ROUTE_PROFIT] += income
            ledger[LEDGER_REVENUE] += income
            ledger[LEDGER_PORTS][port] += income
            cargo[good] -= amount
            self.markets[port][good] = min(98, self.markets[port][good] + amount * 2)
            self.city_prosperity[port] = min(
                100, self.city_prosperity[port] + max(1, amount // 4)
            )
            sold += amount

        # Load up to three characteristic exports, while preserving cash.
        rules = route[ROUTE_RULES][stop_index]
        for good in rules:
            free = ship[SHIP_CAPACITY] - sum(cargo)
            desired = max(0, AUTO_CARGO_TARGET - cargo[good])
            stored = min(desired, free, self.warehouses[port][good])
            if stored:
                self.warehouses[port][good] -= stored
                cargo[good] += stored
                bought += stored
            free = ship[SHIP_CAPACITY] - sum(cargo)
            desired = max(0, AUTO_CARGO_TARGET - cargo[good])
            price = self._route_buy_price(ship_index, port, good)
            spendable = max(0, self.cash - route[ROUTE_RESERVE])
            amount = min(desired, free, self.markets[port][good] // 3, spendable // price)
            if self.markets[port][good] < PORT_TARGET_SUPPLY[port][good] + 2:
                amount = 0
            if amount <= 0:
                continue
            cost = price * amount
            self.cash -= cost
            route[ROUTE_PROFIT] -= cost
            ledger[LEDGER_COST] += cost
            ledger[LEDGER_PORTS][port] -= cost
            cargo[good] += amount
            self.markets[port][good] = max(4, self.markets[port][good] - amount * 2)
            bought += amount

        if bought or sold or donated:
            message = "%s AUTO %s: +%d/-%d G%d" % (
                SHIP_NAMES[ship[SHIP_NAME]], PORT_NAMES[port], bought, sold, donated,
            )
            self._log(message)
            return message
        return "%s NO TRADE IN %s" % (SHIP_NAMES[ship[SHIP_NAME]], PORT_NAMES[port])

    def _route_repair_ship(self, ship_index):
        ship = self.ships[ship_index]
        route = self.ship_routes[ship_index]
        if ship[SHIP_HULL] >= route[ROUTE_REPAIR]:
            return True
        affordable = max(0, self.cash - route[ROUTE_RESERVE]) // 3
        repair = min(100 - ship[SHIP_HULL], affordable)
        if repair > 0:
            cost = repair * 3
            self.cash -= cost
            route[ROUTE_PROFIT] -= cost
            ledger = self.route_ledgers[ship_index]
            ledger[LEDGER_COST] += cost
            ledger[LEDGER_PORTS][ship[SHIP_PORT]] -= cost
            ship[SHIP_HULL] += repair
        if ship[SHIP_HULL] < route[ROUTE_REPAIR]:
            route[ROUTE_STATE] = ROUTE_ATTENTION
            route[ROUTE_NOTE] = "NEEDS REPAIR"
            return False
        return True

    def _dispatch_route_ship(self, ship_index):
        ship = self.ships[ship_index]
        route = self.ship_routes[ship_index]
        ports = route[ROUTE_PORTS]
        if route[ROUTE_STATE] != ROUTE_RUNNING or ship[SHIP_ORDER] != ORDER_READY:
            return False
        if len(ports) < 2:
            route[ROUTE_STATE] = ROUTE_ATTENTION
            route[ROUTE_NOTE] = "ADD TWO PORTS"
            return False
        if not self._route_repair_ship(ship_index):
            return False

        if ship[SHIP_PORT] in ports:
            stop_index = ports.index(ship[SHIP_PORT])
            self._route_trade(ship_index, stop_index)
            next_index = (stop_index + 1) % len(ports)
        else:
            next_index = _clamp(route[ROUTE_CURSOR], 0, len(ports) - 1)
        destination = ports[next_index]
        days = self.sailing_days(ship_index, destination)
        provisions = days * 3
        if self.cash - route[ROUTE_RESERVE] < provisions:
            route[ROUTE_STATE] = ROUTE_ATTENTION
            route[ROUTE_NOTE] = "LOW CASH"
            return False
        self.cash -= provisions
        route[ROUTE_PROFIT] -= provisions
        ledger = self.route_ledgers[ship_index]
        ledger[LEDGER_COST] += provisions
        ledger[LEDGER_PORTS][ship[SHIP_PORT]] -= provisions
        route[ROUTE_CURSOR] = next_index
        route[ROUTE_NOTE] = "TO " + PORT_NAMES[destination]
        ship[SHIP_DEST] = destination
        ship[SHIP_READY_DAY] = self.day + days
        ship[SHIP_ORDER] = ORDER_SAIL
        self.pending_costs += provisions
        return True

    def toggle_route(self, ship_index):
        if ship_index < 0 or ship_index >= len(self.ships):
            return False
        ship = self.ships[ship_index]
        route = self.ship_routes[ship_index]
        if route[ROUTE_STATE] == ROUTE_RUNNING:
            route[ROUTE_STATE] = ROUTE_PAUSED
            route[ROUTE_NOTE] = "PAUSES AT NEXT PORT" if ship[SHIP_ORDER] != ORDER_READY else "PAUSED"
            self.status = route[ROUTE_NOTE]
            return True
        if len(route[ROUTE_PORTS]) < 2:
            self.status = "ADD AT LEAST TWO PORTS"
            return False
        if ship[SHIP_ORDER] != ORDER_READY:
            route[ROUTE_STATE] = ROUTE_RUNNING
            route[ROUTE_NOTE] = "RESUMED AT SEA"
            self.status = "AUTOMATIC ROUTE RESUMED"
            return True
        other_manual = [
            index for index in self.manual_ready_ships()
            if index != ship_index
        ]
        if not other_manual:
            self.status = "KEEP ONE READY SHIP MANUAL"
            return False
        route[ROUTE_STATE] = ROUTE_RUNNING
        route[ROUTE_NOTE] = "STARTING"
        if not self._dispatch_route_ship(ship_index):
            self.status = route[ROUTE_NOTE]
            return False
        if self.active_ship == ship_index:
            self.active_ship = other_manual[0]
        self.map_selection = self.current_port
        self.status = SHIP_NAMES[ship[SHIP_NAME]] + " ROUTE STARTED"
        self._log(self.status)
        return True

    def ship_order_label(self, index):
        ship = self.ships[index]
        if ship[SHIP_ORDER] == ORDER_SAIL:
            prefix = "AUTO" if self.ship_routes[index][ROUTE_STATE] == ROUTE_RUNNING else "SEA"
            return "%s TO %s D%d" % (prefix, PORT_NAMES[ship[SHIP_DEST]], ship[SHIP_READY_DAY])
        if ship[SHIP_ORDER] == ORDER_WAIT:
            return "WAIT %s D%d" % (PORT_NAMES[ship[SHIP_PORT]], ship[SHIP_READY_DAY])
        return "READY IN " + PORT_NAMES[ship[SHIP_PORT]]

    def _queue_order(self, order, destination, days, cost):
        ship = self.ships[self.active_ship]
        if ship[SHIP_ORDER] != ORDER_READY:
            self.status = "SHIP ALREADY HAS ORDERS"
            return False
        ship[SHIP_DEST] = destination
        ship[SHIP_READY_DAY] = self.day + days
        ship[SHIP_ORDER] = order
        self.pending_costs += cost

        ready = self.manual_ready_ships()
        if ready:
            self.active_ship = ready[0]
            self.map_selection = self.current_port
            self.screen = SCREEN_PORT
            self.status = "GIVE ORDERS TO " + self.ship_name
        else:
            self._advance_to_next_arrival()
        return True

    def order_sail(self, destination):
        if destination == self.current_port:
            self.status = "ALREADY IN PORT"
            return False
        days = self.route_days(destination)
        provisions = days * 3
        if self.cash < provisions:
            self.status = "NEED %d SILVER FOR CREW" % provisions
            return False
        self.cash -= provisions
        self._log("%s ORDERED TO %s" % (self.ship_name, PORT_NAMES[destination]))
        self.emit_sound(SOUND_SAIL)
        if self.tutorial_step == 1:
            self.tutorial_step = 2
        return self._queue_order(ORDER_SAIL, destination, days, provisions)

    def wait_in_port(self, days=1):
        days = _clamp(int(days), 1, 7)
        self._log("%s WAITS UNTIL DAY %d" % (self.ship_name, self.day + days))
        return self._queue_order(ORDER_WAIT, self.current_port, days, 0)

    def bank_action(self, selection):
        """Borrow, repay, or insure the active trading house."""
        selection = _clamp(int(selection), 0, 3)
        if selection == 0:
            amount = min(LOAN_STEP, MAX_LOAN - self.loan)
            if amount <= 0:
                self.status = "CREDIT LIMIT REACHED"
                return False
            self.loan += amount
            self.cash += amount
            self.status = "BORROWED %d SILVER" % amount
        elif selection == 1:
            amount = min(LOAN_STEP, self.loan, self.cash)
            if amount <= 0:
                self.status = "NO LOAN PAYMENT POSSIBLE"
                return False
            self.loan -= amount
            self.cash -= amount
            self.status = "REPAID %d SILVER" % amount
        elif selection == 2:
            self.insured = not self.insured
            self.status = (
                "FLEET INSURED - %dS DAILY" % INSURANCE_PREMIUM
                if self.insured else "FLEET INSURANCE CANCELLED"
            )
        else:
            if self.loan < MAX_LOAN or self.cash >= LOAN_STEP:
                self.status = "INSOLVENCY REQUIRES MAX DEBT AND LOW CASH"
                return False
            self.loan = 0
            self.insured = False
            self.cash = 150
            self.reputation = max(0, self.reputation - 5)
            self.council_favor = max(0, self.council_favor - 15)
            self.offices = [0] * len(PORT_NAMES)
            self.warehouses = [[0] * len(GOOD_NAMES) for _ in PORT_NAMES]
            self.businesses = [[0] * len(GOOD_NAMES) for _ in PORT_NAMES]
            flagship = self.ships[0]
            flagship[SHIP_HULL] = max(60, flagship[SHIP_HULL])
            flagship[SHIP_CAPACITY] = STARTING_CAPACITY
            flagship[SHIP_CARGO] = [0] * len(GOOD_NAMES)
            flagship[SHIP_EARNINGS] = 0
            flagship[SHIP_READY_DAY] = 0
            flagship[SHIP_DEST] = -1
            flagship[SHIP_ORDER] = ORDER_READY
            self.ships = [flagship]
            self.ship_routes = [self._new_route()]
            self.route_ledgers = [self._new_route_ledger()]
            self.captain_xp = [0]
            self.ship_types = [SHIP_COG]
            self.active_ship = 0
            self.route_ship = 0
            self.status = "HOUSE RESTRUCTURED - START AGAIN CAREFULLY"
        self._log(self.status)
        self.emit_sound(SOUND_TRADE if selection < 2 else SOUND_NOTIFY)
        return True

    def council_status(self):
        if self.rank < RANK_COUNCILLOR:
            return "BECOME COUNCILLOR TO TAKE A SEAT"
        if self.day < self.council_next_day:
            return "NEXT SESSION ON DAY %d" % self.council_next_day
        return "THE COUNCIL AWAITS YOUR VOTE"

    def resolve_council(self, selection):
        """Resolve one civic issue and build or lose electoral support."""
        if self.rank < RANK_COUNCILLOR:
            self.status = "ONLY COUNCILLORS MAY VOTE"
            return False
        if self.day < self.council_next_day:
            self.status = "COUNCIL RETURNS ON DAY %d" % self.council_next_day
            return False
        selection = _clamp(int(selection), 0, 2)
        costs = (120, 45, 0)
        favor = (12, 6, -4)
        reputation = (2, 1, 0)
        prosperity = (5, 2, -2)
        cost = costs[selection]
        if self.cash < cost:
            self.status = "NEED %d SILVER FOR THIS POLICY" % cost
            return False
        self.cash -= cost
        self.council_favor = _clamp(self.council_favor + favor[selection], 0, 100)
        self.reputation = max(0, self.reputation + reputation[selection])
        self.city_prosperity[self.home_port] = _clamp(
            self.city_prosperity[self.home_port] + prosperity[selection], 0, 100,
        )
        self.council_decisions += 1
        option = COUNCIL_OPTIONS[self.council_issue][selection]
        self.status = "%s ADOPTED" % option
        self._log("COUNCIL: " + self.status)
        self.council_issue = (self.council_issue + 1 + self._rand(len(COUNCIL_ISSUES) - 1)) % len(COUNCIL_ISSUES)
        self.council_next_day = self.day + 20
        self.emit_sound(SOUND_ELECTION)
        return True

    def decision_options(self):
        if self.decision_type == DECISION_STORM:
            return ("REEF THE SAILS", "RIDE IT OUT", "JETTISON CARGO")
        if self.decision_type == DECISION_PIRATES:
            return ("PAY TRIBUTE", "RUN FOR OPEN SEA", "DEFY THE RAIDERS")
        if self.decision_type == DECISION_RESCUE:
            return ("RESCUE THE CREW", "TAKE THE CARGO", "SAIL ON")
        if self.decision_type == DECISION_WRECK:
            return ("SALVAGE TIMBER", "REPORT TO GUILD", "LEAVE THE WRECK")
        if self.decision_type == DECISION_BLOCKADE:
            return ("PAY THE TOLL", "SLIP THROUGH", "WAIT THEM OUT")
        if self.decision_type == DECISION_FIRE:
            return ("FUND THE BRIGADE", "DONATE TIMBER", "PROTECT YOUR HOUSE")
        return ("CONTINUE",)

    def _prepare_decision(self, kind, ship_index, title, text):
        if self.decision_type != DECISION_NONE:
            return False
        self.decision_type = kind
        self.decision_ship = ship_index
        self.decision_selection = 0
        self.decision_title = title
        self.decision_text = text
        if kind in (DECISION_STORM, DECISION_PIRATES, DECISION_BLOCKADE, DECISION_FIRE):
            self.emit_sound(SOUND_WARNING)
        else:
            self.emit_sound(SOUND_NOTIFY)
        return True

    def _voyage_event(self, ship_index):
        roll = self._rand(100)
        if roll < 9:
            self._prepare_decision(
                DECISION_STORM, ship_index, "NORTH SEA STORM",
                "BLACK WATER BREAKS OVER THE BOW. THE CAPTAIN AWAITS YOUR ORDER.",
            )
            return "STORM DECISION AWAITS"
        if roll < 15:
            self._prepare_decision(
                DECISION_PIRATES, ship_index, "PIRATE SAILS",
                "A LOW BLACK HULK CUTS ACROSS YOUR COURSE AND RAISES A RED FLAG.",
            )
            return "PIRATE DECISION AWAITS"
        if roll < 22:
            self._prepare_decision(
                DECISION_RESCUE, ship_index, "SAILORS IN THE WATER",
                "A SHATTERED MAST DRIFTS BESIDE EXHAUSTED SURVIVORS.",
            )
            return "RESCUE DECISION AWAITS"
        if roll < 29:
            self._prepare_decision(
                DECISION_WRECK, ship_index, "ABANDONED WRECK",
                "A MERCHANT WRECK LIES ADRIFT WITH ITS HOLD BROKEN OPEN.",
            )
            return "SALVAGE DECISION AWAITS"
        if roll < 33:
            self._prepare_decision(
                DECISION_BLOCKADE, ship_index, "BLOCKADED SOUND",
                "ARMED TOLL BOATS BAR THE NARROW APPROACH TO PORT.",
            )
            return "BLOCKADE DECISION AWAITS"
        return ""

    def resolve_decision(self, selection):
        """Apply one visible event choice and record its campaign consequence."""
        if self.decision_type == DECISION_NONE:
            return False
        selection = _clamp(int(selection), 0, len(self.decision_options()) - 1)
        ship = self.ships[_clamp(self.decision_ship, 0, len(self.ships) - 1)]
        kind = self.decision_type
        outcome = ""
        if kind == DECISION_STORM:
            if selection == 0:
                cost = min(self.cash, 18)
                self.cash -= cost
                damage = max(1, 4 - self.captain_storm_guard(self.decision_ship) // 2)
                ship[SHIP_HULL] = max(0, ship[SHIP_HULL] - damage)
                outcome = "SAFE SAILS COST %dS; HULL -%d%%" % (cost, damage)
            elif selection == 1:
                damage = max(2, 8 + self._rand(11) - self.captain_storm_guard(self.decision_ship))
                if self.insured:
                    damage = max(1, damage // 2)
                    self.insurance_claims += 1
                ship[SHIP_HULL] = max(0, ship[SHIP_HULL] - damage)
                outcome = "THE SHIP SURVIVES; HULL -%d%%" % damage
            else:
                lost = 0
                for good in range(len(GOOD_NAMES)):
                    take = min(ship[SHIP_CARGO][good], max(0, 4 - lost))
                    ship[SHIP_CARGO][good] -= take
                    lost += take
                outcome = "THE SEA TAKES %d CRATES" % lost
        elif kind == DECISION_PIRATES:
            if selection == 0:
                loss = min(self.cash, 35 + self._rand(31))
                if self.insured:
                    loss //= 2
                    self.insurance_claims += 1
                self.cash -= loss
                outcome = "THE RAIDERS TAKE %d SILVER" % loss
            elif selection == 1:
                damage = 3 + self._rand(10)
                if self.ships[self.decision_ship][SHIP_CAPTAIN] == 1:
                    damage = max(1, damage - 3)
                ship[SHIP_HULL] = max(0, ship[SHIP_HULL] - damage)
                outcome = "YOU ESCAPE; HULL -%d%%" % damage
            elif self._rand(100) < 55 + self.captain_level(self.decision_ship) * 8:
                prize = 45 + self._rand(56)
                self.cash += prize
                self.reputation += 1
                outcome = "THE RAIDERS FLEE; PRIZE %dS" % prize
            else:
                damage = 8 + self._rand(9)
                ship[SHIP_HULL] = max(0, ship[SHIP_HULL] - damage)
                outcome = "THE RAIDERS PREVAIL; HULL -%d%%" % damage
        elif kind == DECISION_RESCUE:
            if selection == 0:
                cost = min(self.cash, 15)
                self.cash -= cost
                self.reputation += 2
                self.council_favor = min(100, self.council_favor + 2)
                outcome = "THE GUILD PRAISES YOUR MERCY"
            elif selection == 1:
                gain = 35 + self._rand(46)
                self.cash += gain
                self.reputation = max(0, self.reputation - 1)
                outcome = "SALVAGED CARGO BRINGS %dS" % gain
            else:
                outcome = "YOU KEEP YOUR COURSE"
        elif kind == DECISION_WRECK:
            if selection == 0:
                gained = min(5, ship[SHIP_CAPACITY] - sum(ship[SHIP_CARGO]))
                ship[SHIP_CARGO][2] += gained
                outcome = "SALVAGED %d TIMBER" % gained
            elif selection == 1:
                self.reputation += 1
                self.council_favor = min(100, self.council_favor + 1)
                outcome = "THE GUILD RECORDS YOUR HONESTY"
            else:
                outcome = "THE WRECK FADES ASTERN"
        elif kind == DECISION_BLOCKADE:
            if selection == 0:
                toll = min(self.cash, 30 + self._rand(21))
                self.cash -= toll
                outcome = "TOLL PAID: %dS" % toll
            elif selection == 1:
                damage = self._rand(9)
                ship[SHIP_HULL] = max(0, ship[SHIP_HULL] - damage)
                outcome = "YOU SLIP THROUGH; HULL -%d%%" % damage
            else:
                self.pending_costs += 9
                outcome = "ONE COSTLY DAY PASSES AT ANCHOR"
        else:
            port = ship[SHIP_PORT]
            if selection == 0:
                cost = min(self.cash, 80)
                self.cash -= cost
                self.city_prosperity[port] = min(100, self.city_prosperity[port] + 6)
                self.reputation += 2
                outcome = "THE FIRE BRIGADE SAVES THE QUAY"
            elif selection == 1:
                donated = min(6, self.warehouses[port][2])
                self.warehouses[port][2] -= donated
                self.reputation += donated // 2
                outcome = "DONATED %d TIMBER" % donated
            else:
                self.city_prosperity[port] = max(0, self.city_prosperity[port] - 4)
                outcome = "YOUR HOUSE IS SAFE; THE QUAY SUFFERS"
        self.events_resolved += 1
        self.status = outcome
        self._log(outcome)
        self.decision_type = DECISION_NONE
        self.decision_selection = 0
        self.emit_sound(SOUND_NOTIFY)
        self._check_goal()
        return True

    @staticmethod
    def _crossed_interval(old_day, new_day, interval):
        return old_day // interval < new_day // interval

    def _political_progress(self, old_day, new_day):
        if self.game_mode != MODE_CAREER:
            return ""
        previous_rank = self.rank
        if (
            self.rank == RANK_MERCHANT
            and self.reputation >= COUNCILLOR_REPUTATION
            and self.wealth() >= COUNCILLOR_WEALTH
            and self.offices[self.home_port]
        ):
            self.rank = RANK_COUNCILLOR
            self._log("ELECTED COUNCILLOR")
            self.emit_sound(SOUND_ELECTION)
            return "GUILD ELECTS YOU COUNCILLOR"
        if (
            previous_rank >= RANK_MAYOR
            and self._crossed_interval(old_day, new_day, HANSE_ELECTION_DAYS)
            and self.reputation >= ALDERMAN_REPUTATION
            and self.wealth() >= ALDERMAN_WEALTH
            and sum(self.offices) >= 3
            and self.council_favor >= 60
        ):
            self.rank = RANK_ALDERMAN
            self._log("ELECTED ALDERMAN")
            self.emit_sound(SOUND_ELECTION)
            return "HANSETAG ELECTS YOU ALDERMAN"
        if (
            previous_rank >= RANK_COUNCILLOR
            and self._crossed_interval(old_day, new_day, MAYOR_ELECTION_DAYS)
            and self.reputation >= MAYOR_REPUTATION
            and self.wealth() >= MAYOR_WEALTH
            and sum(self.offices) >= 2
            and self.council_favor >= 30
        ):
            self.rank = RANK_MAYOR
            self._log("ELECTED MAYOR")
            self.emit_sound(SOUND_ELECTION)
            return "LUBECK ELECTS YOU MAYOR"
        return ""

    def _advance_to_next_arrival(self):
        arrival_day = min(
            ship[SHIP_READY_DAY] for ship in self.ships
            if ship[SHIP_ORDER] != ORDER_READY
        )
        old_day = self.day
        elapsed = arrival_day - old_day
        expired, news, office_cost = self._advance_world(elapsed)
        arrivals = []
        for index in range(len(self.ships)):
            ship = self.ships[index]
            if ship[SHIP_ORDER] != ORDER_READY and ship[SHIP_READY_DAY] <= self.day:
                arrivals.append((index, ship[SHIP_ORDER], ship[SHIP_PORT], ship[SHIP_DEST]))

        self.round_days = elapsed
        self.round_cost = self.pending_costs + office_cost
        self.pending_costs = 0
        self.round_lines = ["DAY %d TO %d - COST %dS" % (
            old_day, self.day, self.round_cost,
        )]
        voyage_events = []

        for index, order, origin, destination in arrivals:
            ship = self.ships[index]
            ship[SHIP_PORT] = destination
            ship[SHIP_READY_DAY] = 0
            ship[SHIP_DEST] = -1
            ship[SHIP_ORDER] = ORDER_READY
            self._refresh_contracts(destination)
            if order == ORDER_SAIL:
                self.voyages += 1
                self.captain_xp[index] += 2
                self._log("%s ARRIVED %s" % (
                    SHIP_NAMES[ship[SHIP_NAME]], PORT_NAMES[destination],
                ))
                self.emit_sound(SOUND_NOTIFY)
                if self.tutorial_step == 2:
                    self.tutorial_step = 3
                if self.voyages % 3 == 0:
                    self.reputation += 1
                self.round_lines.append("%s ARRIVES %s" % (
                    SHIP_NAMES[ship[SHIP_NAME]], PORT_NAMES[destination],
                ))
                event = self._voyage_event(index)
                if (
                    not event
                    and self.city_events[destination][0] == EVENT_FIRE
                    and self._prepare_decision(
                        DECISION_FIRE, index, "FIRE ON THE QUAY",
                        "FLAMES RACE BETWEEN THE WAREHOUSES AS YOUR SHIP MOORS.",
                    )
                ):
                    event = "QUAYSIDE FIRE DECISION AWAITS"
                if event:
                    voyage_events.append(event)
                    self._log(event)
            else:
                self.round_lines.append("%s READY IN %s" % (
                    SHIP_NAMES[ship[SHIP_NAME]], PORT_NAMES[destination],
                ))

            route = self.ship_routes[index]
            if route[ROUTE_STATE] == ROUTE_RUNNING:
                if self._dispatch_route_ship(index):
                    self.round_lines.append("%s ROUTE CONTINUES" % SHIP_NAMES[ship[SHIP_NAME]])
                else:
                    self.round_lines.append("%s NEEDS ATTENTION" % SHIP_NAMES[ship[SHIP_NAME]])
            elif route[ROUTE_STATE] == ROUTE_PAUSED:
                route[ROUTE_NOTE] = "PAUSED IN " + PORT_NAMES[destination]
                self.round_lines.append("%s ROUTE PAUSED" % SHIP_NAMES[ship[SHIP_NAME]])

        self.round_lines.extend(voyage_events)

        if expired:
            self.round_lines.append("%d CONTRACT%s EXPIRED" % (
                expired, "" if expired == 1 else "S",
            ))
        if news:
            self.round_lines.append(news)
        politics = self._political_progress(old_day, self.day)
        if politics:
            self.round_lines.append(politics)

        ready = self.manual_ready_ships()
        if not ready and any(ship[SHIP_ORDER] != ORDER_READY for ship in self.ships):
            previous_days = self.round_days
            previous_cost = self.round_cost
            previous_lines = self.round_lines[:]
            self._advance_to_next_arrival()
            self.round_days += previous_days
            self.round_cost += previous_cost
            self.round_lines = previous_lines + self.round_lines
            self.event_text = " ".join(self.round_lines)
            return

        self.active_ship = ready[0] if ready else arrivals[0][0]
        self.map_selection = self.current_port
        self.event_title = "GUILD SCROLL"
        self.event_text = " ".join(self.round_lines)
        self.scroll_selection = 0
        self.status = "ARRIVED IN " + PORT_NAMES[self.current_port]
        self.screen = SCREEN_EVENT
        if self.decision_type == DECISION_NONE:
            self._check_goal()

    def travel(self, destination):
        return self.order_sail(destination)

    def _new_contract(self, origin):
        destination = self._rand(len(PORT_NAMES) - 1)
        if destination >= origin:
            destination += 1
        good = self._rand(len(GOOD_NAMES))
        qty = 4 + self._rand(9)
        days = self.route_days_from(origin, destination)
        deadline = self.day + days + 7 + self._rand(10)
        reward = qty * self.price(destination, good) + days * 18 + 35
        return [good, qty, origin, destination, deadline, reward]

    def route_days_from(self, origin, destination):
        here = PORT_POSITIONS[origin]
        there = PORT_POSITIONS[destination]
        return _clamp(1 + (abs(here[0] - there[0]) + abs(here[1] - there[1])) // 46, 1, 5)

    def _refresh_contracts(self, port):
        offers = self.contract_offers[port]
        offers[:] = [offer for offer in offers if offer[CONTRACT_DEADLINE] >= self.day]
        while len(offers) < 2:
            offers.append(self._new_contract(port))

    def accept_contract(self, index):
        offers = self.contract_offers[self.current_port]
        if len(self.active_contracts) >= MAX_ACTIVE_CONTRACTS:
            self.status = "THREE CONTRACTS ALREADY ACTIVE"
            return False
        if index < 0 or index >= len(offers):
            self.status = "NO CONTRACT SELECTED"
            return False
        self.active_contracts.append(offers.pop(index))
        self._refresh_contracts(self.current_port)
        self.status = "CONTRACT SEALED"
        self._log(self.status)
        self.emit_sound(SOUND_NOTIFY)
        return True

    def pin_contract(self, index):
        if index < 0 or index >= len(self.active_contracts):
            self.status = "NO ACTIVE CONTRACT TO PIN"
            return False
        self.pinned_contract = index
        contract = self.active_contracts[index]
        self.status = "OBJECTIVE PINNED: " + PORT_NAMES[contract[CONTRACT_DEST]]
        self._log(self.status)
        return True

    def deliver_contract(self, index):
        if index < 0 or index >= len(self.active_contracts):
            return False
        contract = self.active_contracts[index]
        if contract[CONTRACT_DEST] != self.current_port:
            self.status = "DELIVER IN " + PORT_NAMES[contract[CONTRACT_DEST]]
            return False
        good = contract[CONTRACT_GOOD]
        qty = contract[CONTRACT_QTY]
        if self.cargo[good] < qty:
            self.status = "NEED %d %s" % (qty, GOOD_NAMES[good])
            return False
        self.cargo[good] -= qty
        self.cash += contract[CONTRACT_REWARD]
        self.contracts_completed += 1
        self.reputation += 2
        self.active_contracts.pop(index)
        if self.pinned_contract == index:
            self.pinned_contract = -1
        elif self.pinned_contract > index:
            self.pinned_contract -= 1
        self.status = "CONTRACT PAID %d SILVER" % contract[CONTRACT_REWARD]
        self._log(self.status)
        self.emit_sound(SOUND_MISSION)
        self._check_goal()
        return True

    def buy_office(self):
        port = self.current_port
        if self.offices[port]:
            self.status = "OFFICE ALREADY ESTABLISHED"
            return False
        cost = 350 + sum(self.offices) * 100
        if self.cash < cost:
            self.status = "OFFICE COSTS %d SILVER" % cost
            return False
        self.cash -= cost
        self.offices[port] = 1
        self.status = "TRADING OFFICE OPENED"
        self._log("OFFICE OPENED IN " + PORT_NAMES[port])
        self.emit_sound(SOUND_BUILD)
        self._check_goal()
        return True

    def warehouse_transfer(self, good, amount):
        port = self.current_port
        if not self.offices[port]:
            self.status = "OPEN AN OFFICE FIRST"
            return False
        if amount > 0:
            moved = min(amount, self.cargo[good])
            if moved <= 0:
                self.status = "NONE ABOARD"
                return False
            self.cargo[good] -= moved
            self.warehouses[port][good] += moved
            self.status = "STORED %d %s" % (moved, GOOD_NAMES[good])
            return True
        moved = min(-amount, self.warehouses[port][good], self.cargo_free)
        if moved <= 0:
            self.status = "NO STOCK OR HOLD SPACE"
            return False
        self.warehouses[port][good] -= moved
        self.cargo[good] += moved
        self.status = "LOADED %d %s" % (moved, GOOD_NAMES[good])
        return True

    def buy_ship(self):
        if len(self.ships) >= MAX_SHIPS:
            self.status = "FLEET AT MAXIMUM"
            return False
        ship_type = len(self.ships)
        cost = SHIP_TYPE_COST[ship_type]
        if self.cash < cost:
            self.status = "NEW %s COSTS %d SILVER" % (SHIP_TYPE_NAMES[ship_type], cost)
            return False
        index = len(self.ships)
        self.cash -= cost
        self.ships.append([
            index, index, 100, SHIP_TYPE_CAPACITY[ship_type], [0] * len(GOOD_NAMES), self.current_port, 0,
            0, -1, ORDER_READY,
        ])
        self.ship_routes.append(self._new_route())
        self.route_ledgers.append(self._new_route_ledger())
        self.ship_types.append(ship_type)
        self.captain_xp.append(0)
        self.fleet_selection = index
        self.status = "%s JOINS THE FLEET" % SHIP_NAMES[index]
        self._log(self.status)
        self.emit_sound(SOUND_BUILD)
        return True

    def switch_ship(self, index):
        if index < 0 or index >= len(self.ships):
            return False
        if self.ships[index][SHIP_ORDER] != ORDER_READY:
            self.status = self.ship_order_label(index)
            return False
        self.active_ship = index
        self.map_selection = self.current_port
        self.status = "%s, CAPTAIN %s" % (self.ship_name, self.captain_name)
        return True

    def repair(self):
        if self.hull >= 100:
            self.status = "HULL ALREADY SOUND"
            return False
        repair = min(10, 100 - self.hull)
        cost = repair * 3
        if self.cash < cost:
            self.status = "REPAIR COSTS %d SILVER" % cost
            return False
        self.cash -= cost
        self.hull += repair
        self.status = "HULL REPAIRED %d%%" % repair
        self._log(self.status)
        return True

    def expand_hold(self):
        if self.capacity >= MAX_CAPACITY:
            self.status = "HOLD AT MAXIMUM"
            return False
        cost = 180 + (self.capacity - STARTING_CAPACITY) * 12
        if self.cash < cost:
            self.status = "EXPANSION COSTS %d" % cost
            return False
        self.cash -= cost
        self.capacity += 5
        self.status = "CARGO HOLD NOW %d" % self.capacity
        self._log(self.status)
        return True

    def rumours(self):
        lines = []
        for port in range(len(PORT_NAMES)):
            event = self.city_events[port]
            if event[0]:
                if event[0] in (EVENT_SHORTAGE, EVENT_FAIR):
                    label = GOOD_NAMES[event[1]] + " " + EVENT_NAMES[event[0]]
                else:
                    label = EVENT_NAMES[event[0]]
                lines.append("%s: %s" % (PORT_NAMES[port], label))
        good = (self.day + self.current_port) % len(GOOD_NAMES)
        cheap = 0
        dear = 0
        for port in range(1, len(PORT_NAMES)):
            if self.price(port, good) < self.price(cheap, good):
                cheap = port
            if self.price(port, good) > self.price(dear, good):
                dear = port
        lines.append("%s CHEAP IN %s" % (GOOD_NAMES[good], PORT_NAMES[cheap]))
        lines.append("%s DEAR IN %s" % (GOOD_NAMES[good], PORT_NAMES[dear]))
        needs = self.city_needs(self.current_port, 1)[0]
        lines.append("OFFICE: %s %s IN %s" % (
            GOOD_NAMES[needs], self.market_forecast(self.current_port, needs),
            PORT_NAMES[self.current_port],
        ))
        leader = max(self.rivals, key=lambda rival: rival[2])
        lines.append("%s LEADS WITH %dS" % (RIVAL_NAMES[leader[0]], leader[2]))
        lines.append(self.rival_news)
        return lines[:5]

    def _check_goal(self):
        if self.hull <= 0:
            self.result_title = "LOST AT SEA"
            self.result_text = "YOUR LEDGER CLOSES ON DAY %d" % self.day
            self.screen = SCREEN_END
            return True
        if self.game_mode == MODE_CAREER:
            if self.rank < RANK_COUNCILLOR:
                self._political_progress(self.day, self.day)
            if self.rank >= RANK_ALDERMAN:
                self.result_title = "ALDERMAN OF THE HANSE"
                self.result_text = "THE HANSETAG ENTRUSTS THE LEAGUE TO YOUR HOUSE"
                self.screen = SCREEN_END
                return True
            return False
        if self.wealth() >= WEALTH_GOAL:
            self.result_title = "HANSEATIC PATRON"
            self.result_text = "YOUR HOUSE COMMANDS %d SILVER" % self.wealth()
            self.screen = SCREEN_END
            return True
        if self.day > CAMPAIGN_DAYS:
            self.result_title = "BOOKS ARE CLOSED"
            self.result_text = "FINAL WEALTH: %d / %d" % (self.wealth(), WEALTH_GOAL)
            self.screen = SCREEN_END
            return True
        return False

    def next_mayor_election(self):
        return (self.day // MAYOR_ELECTION_DAYS + 1) * MAYOR_ELECTION_DAYS

    def next_hanse_election(self):
        return (self.day // HANSE_ELECTION_DAYS + 1) * HANSE_ELECTION_DAYS

    @property
    def rank_name(self):
        return RANK_NAMES[self.rank]

    def to_dict(self):
        return {
            "version": SAVE_VERSION, "day": self.day, "cash": self.cash,
            "reputation": self.reputation, "ships": self.ships,
            "active_ship": self.active_ship, "markets": self.markets,
            "price_history": self.price_history, "city_events": self.city_events,
            "contract_offers": self.contract_offers,
            "active_contracts": self.active_contracts, "offices": self.offices,
            "warehouses": self.warehouses, "rivals": self.rivals,
            "rng_state": self.rng_state, "voyages": self.voyages,
            "trade_profit": self.trade_profit, "game_mode": self.game_mode,
            "rank": self.rank, "home_port": self.home_port,
            "pending_costs": self.pending_costs,
            "pinned_contract": self.pinned_contract,
            "recent_log": self.recent_log, "tutorial_step": self.tutorial_step,
            "ship_routes": self.ship_routes,
            "city_prosperity": self.city_prosperity,
            "city_projects": self.city_projects,
            "captain_xp": self.captain_xp, "ship_types": self.ship_types,
            "rival_routes": self.rival_routes, "weather": self.weather,
            "businesses": self.businesses, "route_ledgers": self.route_ledgers,
            "rival_pressure": self.rival_pressure, "rival_news": self.rival_news,
            "story_mission": self.story_mission, "story_completed": self.story_completed,
            "loan": self.loan, "insured": 1 if self.insured else 0,
            "council_favor": self.council_favor,
            "council_issue": self.council_issue,
            "council_next_day": self.council_next_day,
            "council_decisions": self.council_decisions,
            "save_slot": self.save_slot,
            "goods_bought": self.goods_bought, "goods_sold": self.goods_sold,
            "contracts_completed": self.contracts_completed,
            "projects_completed": self.projects_completed,
            "events_resolved": self.events_resolved,
            "interest_paid": self.interest_paid,
            "insurance_claims": self.insurance_claims,
            "decision": [
                self.decision_type, self.decision_selection, self.decision_ship,
                self.decision_title, self.decision_text,
            ],
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("version") not in (1, 2, 3, 4, 5, 6, 7, SAVE_VERSION):
            raise ValueError("unsupported save")
        version = data.get("version")
        default_mode = MODE_QUICK if version in (1, 2) else MODE_CAREER
        game = cls(int(data.get("rng_state", 1)), int(data.get("game_mode", default_mode)))
        game.day = _clamp(int(data["day"]), 1, 9999)
        game.cash = max(0, int(data["cash"]))
        game.reputation = max(0, int(data.get("reputation", 0)))
        if version == 1:
            cargo = [max(0, int(value)) for value in data["cargo"]]
            game.ships = [[0, 0, _clamp(int(data["hull"]), 0, 100),
                _clamp(int(data["capacity"]), STARTING_CAPACITY, MAX_CAPACITY),
                cargo, _clamp(int(data["current_port"]), 0, len(PORT_NAMES) - 1), 0,
                0, -1, ORDER_READY]]
        else:
            ships = data["ships"]
            if not ships or len(ships) > MAX_SHIPS:
                raise ValueError("invalid fleet")
            game.ships = []
            for raw in ships:
                if len(raw) not in (7, 10) or len(raw[SHIP_CARGO]) != len(GOOD_NAMES):
                    raise ValueError("invalid ship")
                ship = [int(raw[0]), int(raw[1]), _clamp(int(raw[2]), 0, 100),
                    _clamp(int(raw[3]), STARTING_CAPACITY, MAX_CAPACITY),
                    [max(0, int(value)) for value in raw[4]],
                    _clamp(int(raw[5]), 0, len(PORT_NAMES) - 1), max(0, int(raw[6]))]
                if len(raw) == 10:
                    order = _clamp(int(raw[SHIP_ORDER]), ORDER_READY, ORDER_WAIT)
                    destination = int(raw[SHIP_DEST])
                    if order == ORDER_READY:
                        destination = -1
                    elif destination < 0 or destination >= len(PORT_NAMES):
                        raise ValueError("invalid destination")
                    ship.extend([
                        max(0, int(raw[SHIP_READY_DAY])), destination, order,
                    ])
                else:
                    ship.extend([0, -1, ORDER_READY])
                if sum(ship[SHIP_CARGO]) > ship[SHIP_CAPACITY]:
                    raise ValueError("cargo exceeds capacity")
                game.ships.append(ship)
            game.active_ship = _clamp(int(data.get("active_ship", 0)), 0, len(game.ships) - 1)
        game.ship_routes = [game._new_route() for _unused in game.ships]
        game.route_ledgers = [game._new_route_ledger() for _unused in game.ships]
        game.ship_types = [min(index, SHIP_HULK) for index in range(len(game.ships))]
        game.captain_xp = [0] * len(game.ships)
        game.route_ship = game.active_ship

        markets = data["markets"]
        if len(markets) != len(PORT_NAMES):
            raise ValueError("invalid market dimensions")
        game.markets = []
        for row in markets:
            if len(row) != len(GOOD_NAMES):
                raise ValueError("invalid market dimensions")
            game.markets.append([_clamp(int(value), 5, 98) for value in row])
        if version in (2, 3, 4, 5, 6, 7, SAVE_VERSION):
            game.price_history = data.get("price_history", game.price_history)
            game.city_events = data.get("city_events", game.city_events)
            game.contract_offers = data.get("contract_offers", game.contract_offers)
            game.active_contracts = data.get("active_contracts", [])
            game.offices = data.get("offices", game.offices)
            game.warehouses = data.get("warehouses", game.warehouses)
            game.rivals = data.get("rivals", game.rivals)
        if version in (3, 4, 5, 6, 7, SAVE_VERSION):
            game.rank = _clamp(int(data.get("rank", RANK_MERCHANT)), RANK_MERCHANT, RANK_ALDERMAN)
            game.home_port = _clamp(int(data.get("home_port", 0)), 0, len(PORT_NAMES) - 1)
            game.pending_costs = max(0, int(data.get("pending_costs", 0)))
        if version in (4, 5, 6, 7, SAVE_VERSION):
            game.tutorial_step = _clamp(int(data.get("tutorial_step", 0)), 0, 4)
            log = data.get("recent_log", [])
            if isinstance(log, list):
                game.recent_log = [str(item)[:52] for item in log[-10:]]
            game.pinned_contract = int(data.get("pinned_contract", -1))
            if game.pinned_contract < 0 or game.pinned_contract >= len(game.active_contracts):
                game.pinned_contract = -1
        if version in (5, 6, 7, SAVE_VERSION):
            routes = data.get("ship_routes", [])
            if len(routes) != len(game.ships):
                raise ValueError("invalid route count")
            game.ship_routes = []
            for index in range(len(routes)):
                raw = routes[index]
                if not isinstance(raw, list) or len(raw) != 8:
                    raise ValueError("invalid route")
                state = _clamp(int(raw[ROUTE_STATE]), ROUTE_OFF, ROUTE_ATTENTION)
                reserve = _clamp(int(raw[ROUTE_RESERVE]), 0, 2000)
                repair = _clamp(int(raw[ROUTE_REPAIR]), 10, 90)
                ports = [int(port) for port in raw[ROUTE_PORTS]]
                if len(ports) > MAX_ROUTE_PORTS or len(set(ports)) != len(ports):
                    raise ValueError("invalid route ports")
                if any(port < 0 or port >= len(PORT_NAMES) for port in ports):
                    raise ValueError("invalid route port")
                raw_rules = raw[ROUTE_RULES]
                if len(raw_rules) != len(ports):
                    raise ValueError("invalid route rules")
                rules = []
                for stop_rules in raw_rules:
                    goods = [int(good) for good in stop_rules]
                    if len(goods) > MAX_ROUTE_GOODS or len(set(goods)) != len(goods):
                        raise ValueError("invalid route goods")
                    if any(good < 0 or good >= len(GOOD_NAMES) for good in goods):
                        raise ValueError("invalid route good")
                    rules.append(goods)
                if state == ROUTE_RUNNING and (
                    len(ports) < 2 or game.ships[index][SHIP_ORDER] == ORDER_READY
                ):
                    state = ROUTE_ATTENTION
                cursor = _clamp(int(raw[ROUTE_CURSOR]), 0, max(0, len(ports) - 1))
                game.ship_routes.append([
                    state, cursor, reserve, repair, ports, rules,
                    int(raw[ROUTE_PROFIT]), str(raw[ROUTE_NOTE])[:32],
                ])
        if version in (6, 7, SAVE_VERSION):
            prosperity = data.get("city_prosperity", [])
            projects = data.get("city_projects", [])
            captain_xp = data.get("captain_xp", [])
            ship_types = data.get("ship_types", [])
            rival_routes = data.get("rival_routes", [])
            if (len(prosperity) != len(PORT_NAMES) or len(projects) != len(PORT_NAMES)
                    or len(captain_xp) != len(game.ships) or len(ship_types) != len(game.ships)
                    or len(rival_routes) != len(game.rivals)):
                raise ValueError("invalid expansion state")
            game.city_prosperity = [_clamp(int(value), 0, 100) for value in prosperity]
            game.city_projects = []
            for raw in projects:
                if not isinstance(raw, list) or len(raw) != 8:
                    raise ValueError("invalid city project")
                project = [int(value) for value in raw]
                if (project[PROJECT_GOOD_A] < 0 or project[PROJECT_GOOD_A] >= len(GOOD_NAMES)
                        or project[PROJECT_GOOD_B] < 0 or project[PROJECT_GOOD_B] >= len(GOOD_NAMES)):
                    raise ValueError("invalid project good")
                project[PROJECT_HAVE_A] = _clamp(project[PROJECT_HAVE_A], 0, project[PROJECT_NEED_A])
                project[PROJECT_HAVE_B] = _clamp(project[PROJECT_HAVE_B], 0, project[PROJECT_NEED_B])
                project[PROJECT_COMPLETE] = 1 if project[PROJECT_COMPLETE] else 0
                game.city_projects.append(project)
            game.captain_xp = [max(0, int(value)) for value in captain_xp]
            game.ship_types = [_clamp(int(value), SHIP_COG, SHIP_HULK) for value in ship_types]
            game.rival_routes = []
            for raw in rival_routes:
                if not isinstance(raw, list) or len(raw) != 3:
                    raise ValueError("invalid rival route")
                origin = _clamp(int(raw[0]), 0, len(PORT_NAMES) - 1)
                destination = _clamp(int(raw[1]), 0, len(PORT_NAMES) - 1)
                game.rival_routes.append([origin, destination, max(game.day, int(raw[2]))])
            game.weather = _clamp(int(data.get("weather", WEATHER_CLEAR)), WEATHER_CLEAR, WEATHER_ICE)
        else:
            # Legacy campaigns keep their fleet and routes, while new world
            # systems begin relative to the restored day and rival positions.
            game.city_prosperity = [50] * len(PORT_NAMES)
            game.city_projects = []
            for port in range(len(PORT_NAMES)):
                goods = CITY_PROJECT_GOODS[port]
                game.city_projects.append([
                    goods[0], goods[1], 0, goods[2], goods[3], 0,
                    game.day + 54 + port * 3, 0,
                ])
            game.rival_routes = []
            for rival in game.rivals:
                destination = (rival[1] + 2 + rival[0]) % len(PORT_NAMES)
                game.rival_routes.append([
                    rival[1], destination, max(game.day + 1, int(rival[3])),
                ])
            game.weather = WEATHER_CLEAR
        if version in (7, SAVE_VERSION):
            businesses = data.get("businesses", [])
            ledgers = data.get("route_ledgers", [])
            pressure = data.get("rival_pressure", [])
            mission = data.get("story_mission", [])
            if (len(businesses) != len(PORT_NAMES) or len(ledgers) != len(game.ships)
                    or len(pressure) != len(PORT_NAMES) or len(mission) != 8):
                raise ValueError("invalid economy state")
            game.businesses = []
            for row in businesses:
                if not isinstance(row, list) or len(row) != len(GOOD_NAMES):
                    raise ValueError("invalid businesses")
                game.businesses.append([
                    _clamp(int(level), 0, MAX_BUSINESS_LEVEL) for level in row
                ])
            game.route_ledgers = []
            for raw in ledgers:
                if not isinstance(raw, list) or len(raw) != 4 or len(raw[LEDGER_PORTS]) != len(PORT_NAMES):
                    raise ValueError("invalid route ledger")
                game.route_ledgers.append([
                    max(0, int(raw[LEDGER_REVENUE])), max(0, int(raw[LEDGER_COST])),
                    max(0, int(raw[LEDGER_VISITS])),
                    [int(value) for value in raw[LEDGER_PORTS]],
                ])
            game.rival_pressure = [_clamp(int(value), 0, 20) for value in pressure]
            game.rival_news = str(data.get("rival_news", "RIVAL HOUSES WATCH THE MARKET"))[:52]
            game.story_mission = [int(value) for value in mission]
            if (game.story_mission[MISSION_ID] < 0
                    or game.story_mission[MISSION_ID] >= len(STORY_NAMES)
                    or game.story_mission[MISSION_STATE] not in (MISSION_OFFERED, MISSION_ACTIVE)
                    or game.story_mission[MISSION_GOOD] < 0
                    or game.story_mission[MISSION_GOOD] >= len(GOOD_NAMES)):
                raise ValueError("invalid story mission")
            game.story_completed = max(0, int(data.get("story_completed", 0)))
        else:
            game.businesses = [[0] * len(GOOD_NAMES) for _ in PORT_NAMES]
            game.route_ledgers = [game._new_route_ledger() for _unused in game.ships]
            game.rival_pressure = [0] * len(PORT_NAMES)
            game.rival_news = "RIVAL HOUSES WATCH THE MARKET"
            game.story_completed = 0
            game.story_mission = game._new_story_mission(0, game.current_port)
        if version == SAVE_VERSION:
            game.loan = _clamp(int(data.get("loan", 0)), 0, MAX_LOAN)
            game.insured = bool(data.get("insured", 0))
            game.council_favor = _clamp(int(data.get("council_favor", 10)), 0, 100)
            game.council_issue = _clamp(int(data.get("council_issue", 0)), 0, len(COUNCIL_ISSUES) - 1)
            game.council_next_day = max(1, int(data.get("council_next_day", game.day)))
            game.council_decisions = max(0, int(data.get("council_decisions", 0)))
            game.save_slot = _clamp(int(data.get("save_slot", 0)), 0, 2)
            game.goods_bought = max(0, int(data.get("goods_bought", 0)))
            game.goods_sold = max(0, int(data.get("goods_sold", 0)))
            game.contracts_completed = max(0, int(data.get("contracts_completed", 0)))
            game.projects_completed = max(0, int(data.get("projects_completed", 0)))
            game.events_resolved = max(0, int(data.get("events_resolved", 0)))
            game.interest_paid = max(0, int(data.get("interest_paid", 0)))
            game.insurance_claims = max(0, int(data.get("insurance_claims", 0)))
            decision = data.get("decision", [DECISION_NONE, 0, 0, "", ""])
            if not isinstance(decision, list) or len(decision) != 5:
                raise ValueError("invalid pending decision")
            game.decision_type = _clamp(int(decision[0]), DECISION_NONE, DECISION_FIRE)
            game.decision_selection = _clamp(int(decision[1]), 0, 2)
            game.decision_ship = _clamp(int(decision[2]), 0, len(game.ships) - 1)
            game.decision_title = str(decision[3])[:40]
            game.decision_text = str(decision[4])[:120]
        else:
            game.loan = 0
            game.insured = False
            game.council_favor = 10
            game.council_issue = 0
            game.council_next_day = game.day
            game.council_decisions = 0
            game.save_slot = 0
            game.goods_bought = 0
            game.goods_sold = 0
            game.contracts_completed = 0
            game.projects_completed = sum(
                1 for project in game.city_projects if project[PROJECT_COMPLETE]
            )
            game.events_resolved = 0
            game.interest_paid = 0
            game.insurance_claims = 0
            game.decision_type = DECISION_NONE
        game.rng_state = int(data.get("rng_state", 1)) & 0x7FFFFFFF
        game.voyages = max(0, int(data.get("voyages", 0)))
        game.trade_profit = max(0, int(data.get("trade_profit", 0)))
        ready = game.manual_ready_ships()
        if game.decision_type != DECISION_NONE:
            game.active_ship = game.decision_ship
            game.map_selection = game.current_port
            game.screen = SCREEN_DECISION
            game.status = "A DECISION AWAITS YOUR HOUSE"
        elif ready:
            game.active_ship = ready[0]
            game.map_selection = game.current_port
            game.screen = SCREEN_PORT
            game.status = "VOYAGE RESTORED"
        elif any(ship[SHIP_ORDER] != ORDER_READY for ship in game.ships):
            game._advance_to_next_arrival()
        else:
            raise ValueError("fleet has no available ship")
        game.save_available = True
        game._check_goal()
        return game
