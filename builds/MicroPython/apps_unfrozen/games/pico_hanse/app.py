"""Picoware lifecycle adapter for Pico Hanse."""

from gc import collect
from utime import ticks_add, ticks_diff, ticks_ms

from picoware.system.buttons import (
    BUTTON_B,
    BUTTON_BACK,
    BUTTON_CENTER,
    BUTTON_DOWN,
    BUTTON_ENTER,
    BUTTON_LEFT,
    BUTTON_P,
    BUTTON_RIGHT,
    BUTTON_S,
    BUTTON_SPACE,
    BUTTON_UP,
)

from .model import (
    HARBOR_LOCATIONS,
    MODE_CAREER,
    MODE_QUICK,
    PORT_NAMES,
    SAVE_MODE_LOAD,
    SAVE_MODE_NEW,
    SCREEN_AUDIO,
    SCREEN_BANK,
    SCREEN_CARGO,
    SCREEN_CITY,
    SCREEN_COUNCIL,
    SCREEN_CONTRACTS,
    SCREEN_END,
    SCREEN_DECISION,
    SCREEN_EVENT,
    SCREEN_FLEET,
    SCREEN_HELP,
    SCREEN_ADVISER,
    SCREEN_BUSINESS,
    SCREEN_LEDGER,
    SCREEN_MAP,
    SCREEN_MARKET,
    SCREEN_MODE,
    SCREEN_OFFICE,
    SCREEN_OVERVIEW,
    SCREEN_PORT,
    SCREEN_RIVALS,
    SCREEN_ROUTE,
    SCREEN_LOG,
    SCREEN_SHIPYARD,
    SCREEN_SAVES,
    SCREEN_TAVERN,
    SCREEN_TITLE,
    SCREEN_WAIT,
    SHIP_PORT,
    GameModel,
)
from .persistence import SaveStore
from .render import Renderer
from .sound import SoundController


_game = None
_renderer = None
_store = None
_sound = None
_key_repeat_enabled = False
_animation_phase = 0
_next_animation = 0
_last_screen = -1
ANIMATION_MS = 350
PORT_ANIMATION_MS = 700
MAP_ANIMATION_MS = 900
SCENE_ANIMATION_MS = 500
ANIMATED_SCREENS = (
    SCREEN_TITLE,
    SCREEN_PORT,
    SCREEN_MARKET,
    SCREEN_MAP,
    SCREEN_OFFICE,
    SCREEN_EVENT,
    SCREEN_TAVERN,
    SCREEN_SHIPYARD,
    SCREEN_WAIT,
    SCREEN_CITY,
    SCREEN_ADVISER,
    SCREEN_DECISION,
    SCREEN_ROUTE,
)


def _animation_interval(screen):
    if screen in (SCREEN_MAP, SCREEN_ROUTE):
        return MAP_ANIMATION_MS
    if screen in (SCREEN_PORT, SCREEN_CITY, SCREEN_WAIT):
        return PORT_ANIMATION_MS
    if screen in (SCREEN_TITLE, SCREEN_SHIPYARD):
        return SCENE_ANIMATION_MS
    return ANIMATION_MS


def _set_key_repeat(view_manager, enabled, force=False):
    global _key_repeat_enabled
    enabled = bool(enabled)
    if not force and enabled == _key_repeat_enabled:
        return
    setter = getattr(view_manager.input_manager, "set_key_repeat", None)
    if setter is not None:
        setter(enabled)
    _key_repeat_enabled = enabled


def _new_game(game_mode=MODE_CAREER, slot=0):
    global _game
    _game = GameModel(ticks_ms(), game_mode)
    _game.save_slot = slot
    _game.save_available = _store.exists()
    _game.menu_selection = 3
    _game.screen = SCREEN_PORT
    _game.status = "CHOOSE A PLACE IN THE HARBOUR"
    _sync_audio_flags()
    _store.save(_game, slot)


def _load_game(slot=0):
    global _game
    loaded = _store.load(slot)
    if loaded is None:
        _game.status = "SAVE COULD NOT BE READ"
        _game.title_selection = 0
        return False
    _game = loaded
    _sync_audio_flags()
    return True


def _open_saves(mode):
    _game.save_mode = mode
    _game.save_summaries = _store.summaries()
    _game.save_confirm = False
    if mode == SAVE_MODE_LOAD:
        for index in range(3):
            if _game.save_summaries[index] is not None:
                _game.save_selection = index
                break
    else:
        _game.save_selection = _game.save_slot
        for index in range(3):
            if _game.save_summaries[index] is None:
                _game.save_selection = index
                break
    _game.screen = SCREEN_SAVES


def _sync_audio_flags():
    if _game is None or _sound is None:
        return
    _game.audio_files_missing = not _sound.assets_complete
    _game.music_enabled = _sound.music_enabled if _sound.enabled else False
    _game.effects_enabled = _sound.effects_enabled if _sound.enabled else False
    _game.audio_volume = _sound.volume


def _save_game(announce=True):
    if _store.save(_game):
        if announce:
            _game.status = "VOYAGE SAVED"
        return True
    _game.status = "SAVE FAILED"
    return False


def _return_to_port():
    _game.screen = SCREEN_PORT
    _game.status = "MOORED AT " + PORT_NAMES[_game.current_port]


def start(view_manager):
    """Open Pico Hanse at its title screen."""
    global _game, _renderer, _store, _sound, _animation_phase, _next_animation, _last_screen
    _set_key_repeat(view_manager, False, True)
    _store = SaveStore(view_manager.storage)
    _game = GameModel(ticks_ms())
    _game.save_available = _store.exists()
    _renderer = Renderer(view_manager.draw)
    _sound = SoundController(view_manager.audio, view_manager.storage)
    _sync_audio_flags()
    _animation_phase = 0
    _last_screen = _game.screen
    _next_animation = ticks_add(ticks_ms(), _animation_interval(_game.screen))
    _renderer.draw_frame(_game, _animation_phase)
    _sound.update(_game, ticks_ms())
    return True


def _move_title(delta):
    selection = _game.title_selection
    for _attempt in range(3):
        selection = (selection + delta) % 3
        if selection != 1 or _game.save_available:
            break
    _game.title_selection = selection


def _handle_title(view_manager, button):
    if button == BUTTON_BACK:
        view_manager.back()
        return False
    if button == BUTTON_UP:
        _move_title(-1)
    elif button == BUTTON_DOWN:
        _move_title(1)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.title_selection == 0:
            _game.mode_selection = 0
            _game.screen = SCREEN_MODE
        elif _game.title_selection == 1:
            _open_saves(SAVE_MODE_LOAD)
        else:
            _game.return_screen = SCREEN_TITLE
            _game.help_page = 0
            _game.screen = SCREEN_HELP
    return True


def _handle_mode(button):
    if button == BUTTON_BACK:
        _game.screen = SCREEN_TITLE
    elif button == BUTTON_B:
        _game.audio_selection = 0
        _game.screen = SCREEN_AUDIO
    elif button in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT):
        _game.mode_selection = 1 - _game.mode_selection
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _open_saves(SAVE_MODE_NEW)


def _handle_saves(button):
    if button == BUTTON_BACK:
        _game.save_confirm = False
        _game.screen = SCREEN_TITLE if _game.save_mode == SAVE_MODE_LOAD else SCREEN_MODE
    elif button == BUTTON_UP:
        _game.save_selection = (_game.save_selection - 1) % 3
        _game.save_confirm = False
    elif button == BUTTON_DOWN:
        _game.save_selection = (_game.save_selection + 1) % 3
        _game.save_confirm = False
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        slot = _game.save_selection
        occupied = _game.save_summaries[slot] is not None
        if _game.save_mode == SAVE_MODE_LOAD:
            if occupied:
                _load_game(slot)
            else:
                _game.status = "THIS LEDGER IS EMPTY"
        elif occupied and not _game.save_confirm:
            _game.save_confirm = True
            _game.status = "PRESS CENTER AGAIN TO REPLACE"
        else:
            mode = MODE_CAREER if _game.mode_selection == 0 else MODE_QUICK
            _new_game(mode, slot)


def _handle_audio(button, now):
    if button == BUTTON_BACK:
        _game.screen = SCREEN_MODE
    elif button == BUTTON_UP:
        _game.audio_selection = (_game.audio_selection - 1) % 3
    elif button == BUTTON_DOWN:
        _game.audio_selection = (_game.audio_selection + 1) % 3
    elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _sound is None:
            return
        if _game.audio_selection == 0:
            _sound.toggle_music(_game, now)
        elif _game.audio_selection == 1:
            _sound.toggle_effects(_game)
        else:
            _sound.cycle_volume(_game, -1 if button == BUTTON_LEFT else 1)


def _handle_bank(button):
    if button == BUTTON_BACK:
        _game.screen = SCREEN_OVERVIEW
    elif button == BUTTON_UP:
        _game.bank_selection = (_game.bank_selection - 1) % 4
    elif button == BUTTON_DOWN:
        _game.bank_selection = (_game.bank_selection + 1) % 4
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.bank_action(_game.bank_selection)


def _handle_council(button):
    if button == BUTTON_BACK:
        _game.screen = SCREEN_ADVISER
    elif button == BUTTON_UP:
        _game.council_selection = (_game.council_selection - 1) % 3
    elif button == BUTTON_DOWN:
        _game.council_selection = (_game.council_selection + 1) % 3
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.resolve_council(_game.council_selection)


def _handle_decision(button):
    options = _game.decision_options()
    if button == BUTTON_UP:
        _game.decision_selection = (_game.decision_selection - 1) % len(options)
    elif button == BUTTON_DOWN:
        _game.decision_selection = (_game.decision_selection + 1) % len(options)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.resolve_decision(_game.decision_selection) and _game.screen != SCREEN_END:
            _return_to_port()


def _handle_port(button):
    if button == BUTTON_BACK:
        _save_game()
        _game.screen = SCREEN_TITLE
        _game.save_available = _store.exists()
    elif button == BUTTON_LEFT:
        row = _game.menu_selection // 3
        _game.menu_selection = row * 3 + (_game.menu_selection - 1) % 3
    elif button == BUTTON_RIGHT:
        row = _game.menu_selection // 3
        _game.menu_selection = row * 3 + (_game.menu_selection + 1) % 3
    elif button in (BUTTON_UP, BUTTON_DOWN):
        _game.menu_selection = (_game.menu_selection + 3) % len(HARBOR_LOCATIONS)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        selected = _game.menu_selection
        if selected == 0:
            _game.overview_selection = 0
            _game.screen = SCREEN_OVERVIEW
        elif selected == 1:
            _game.contract_tab = 0
            _game.contract_selection = 0
            _game.screen = SCREEN_CONTRACTS
        elif selected == 2:
            _game.screen = SCREEN_SHIPYARD
        elif selected == 3:
            _game.screen = SCREEN_MARKET
        elif selected == 4:
            _game.screen = SCREEN_TAVERN
        else:
            _game.map_selection = (_game.current_port + 1) % len(PORT_NAMES)
            _game.screen = SCREEN_MAP
    elif button == BUTTON_B:
        selected = _game.menu_selection
        if selected == 0:
            _game.office_selection = 0
            _game.screen = SCREEN_OFFICE
        elif selected == 1:
            _game.screen = SCREEN_ADVISER
        elif selected == 2:
            _game.fleet_selection = _game.active_ship
            _game.screen = SCREEN_FLEET
        elif selected == 3:
            _game.screen = SCREEN_CITY
        elif selected == 4:
            _game.screen = SCREEN_RIVALS
        else:
            _game.wait_days = 1
            _game.screen = SCREEN_WAIT
    elif button == BUTTON_S:
        saved = _save_game(False)
        _game.screen = SCREEN_LEDGER
        if saved:
            _game.status = "VOYAGE SAVED"


def _handle_market(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif button == BUTTON_UP:
        _game.market_selection = (_game.market_selection - 1) % len(_game.cargo)
    elif button == BUTTON_DOWN:
        _game.market_selection = (_game.market_selection + 1) % len(_game.cargo)
    elif button == BUTTON_LEFT:
        _game.sell(_game.market_selection, 1)
    elif button in (BUTTON_RIGHT, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.buy(_game.market_selection, 1)
    elif button == BUTTON_B:
        _game.buy(_game.market_selection, 5)
    elif button == BUTTON_S:
        _game.sell(_game.market_selection, 5)


def _handle_map(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif button in (BUTTON_UP, BUTTON_LEFT):
        _game.map_selection = (_game.map_selection - 1) % len(PORT_NAMES)
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _game.map_selection = (_game.map_selection + 1) % len(PORT_NAMES)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.travel(_game.map_selection):
            _save_game(False)


def _handle_wait(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif button in (BUTTON_LEFT, BUTTON_DOWN):
        _game.wait_days = 7 if _game.wait_days <= 1 else _game.wait_days - 1
    elif button in (BUTTON_RIGHT, BUTTON_UP):
        _game.wait_days = 1 if _game.wait_days >= 7 else _game.wait_days + 1
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.wait_in_port(_game.wait_days):
            _save_game(False)


def _handle_shipyard(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif button in (BUTTON_UP, BUTTON_DOWN):
        _game.shipyard_selection = 1 - _game.shipyard_selection
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.shipyard_selection == 0:
            _game.repair()
        else:
            _game.expand_hold()


def _handle_contracts(button):
    items = (
        _game.contract_offers[_game.current_port]
        if _game.contract_tab == 0
        else _game.active_contracts
    )
    if button == BUTTON_BACK:
        _return_to_port()
    elif button in (BUTTON_LEFT, BUTTON_RIGHT):
        _game.contract_tab = 1 - _game.contract_tab
        _game.contract_selection = 0
    elif button == BUTTON_UP and items:
        _game.contract_selection = (_game.contract_selection - 1) % len(items)
    elif button == BUTTON_DOWN and items:
        _game.contract_selection = (_game.contract_selection + 1) % len(items)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.contract_tab == 0:
            _game.accept_contract(_game.contract_selection)
        else:
            _game.deliver_contract(_game.contract_selection)
        current = (
            _game.contract_offers[_game.current_port]
            if _game.contract_tab == 0
            else _game.active_contracts
        )
        if current:
            _game.contract_selection = min(_game.contract_selection, len(current) - 1)
        else:
            _game.contract_selection = 0
    elif button == BUTTON_B and _game.contract_tab == 1:
        _game.pin_contract(_game.contract_selection)
    elif button == BUTTON_S:
        _game.deliver_story_mission()


def _handle_overview(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif button == BUTTON_UP:
        _game.overview_selection = (_game.overview_selection - 1) % 4
    elif button == BUTTON_DOWN:
        _game.overview_selection = (_game.overview_selection + 1) % 4
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        selected = _game.overview_selection
        if selected == 0:
            _game.fleet_selection = _game.active_ship
            _game.screen = SCREEN_FLEET
        elif selected == 1:
            contract = _game.objective_contract_index()
            if contract >= 0:
                _game.contract_tab = 1
                _game.contract_selection = contract
                _game.screen = SCREEN_CONTRACTS
            elif _game.tutorial_step in (0, 3):
                _game.screen = SCREEN_MARKET
            elif _game.tutorial_step in (1, 2):
                _game.map_selection = (_game.current_port + 1) % len(PORT_NAMES)
                _game.screen = SCREEN_MAP
            else:
                _game.screen = SCREEN_LEDGER
        elif selected == 2:
            _game.screen = SCREEN_CITY
        else:
            _game.screen = SCREEN_LOG
    elif button == BUTTON_B:
        _game.bank_selection = 0
        _game.screen = SCREEN_BANK


def _handle_scroll(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif button == BUTTON_UP:
        _game.scroll_selection = (_game.scroll_selection - 1) % 3
    elif button == BUTTON_DOWN:
        _game.scroll_selection = (_game.scroll_selection + 1) % 3
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.scroll_selection == 0:
            if _game.decision_type:
                _game.screen = SCREEN_DECISION
            else:
                _return_to_port()
        elif _game.scroll_selection == 1 and _game.active_contracts:
            _game.contract_tab = 1
            _game.contract_selection = _game.urgent_contract_index()
            _game.screen = SCREEN_CONTRACTS
        else:
            _game.overview_selection = 0
            _game.screen = SCREEN_OVERVIEW


def _handle_office(button):
    if button == BUTTON_BACK:
        _return_to_port()
    elif not _game.offices[_game.current_port]:
        if button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
            _game.buy_office()
    elif button == BUTTON_UP:
        _game.office_selection = (_game.office_selection - 1) % len(_game.cargo)
    elif button == BUTTON_DOWN:
        _game.office_selection = (_game.office_selection + 1) % len(_game.cargo)
    elif button in (BUTTON_RIGHT, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.warehouse_transfer(_game.office_selection, 1)
    elif button == BUTTON_LEFT:
        _game.warehouse_transfer(_game.office_selection, -1)
    elif button == BUTTON_B:
        _game.business_selection = 0
        _game.screen = SCREEN_BUSINESS
    elif button == BUTTON_S:
        _game.warehouse_transfer(_game.office_selection, -5)


def _handle_business(button):
    choices = _game.local_business_choices()
    if button == BUTTON_BACK:
        _game.screen = SCREEN_OFFICE
    elif button == BUTTON_UP:
        _game.business_selection = (_game.business_selection - 1) % len(choices)
    elif button == BUTTON_DOWN:
        _game.business_selection = (_game.business_selection + 1) % len(choices)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.build_business()


def _handle_fleet(button):
    count = len(_game.ships) + (1 if len(_game.ships) < 3 else 0)
    if button == BUTTON_BACK:
        _return_to_port()
    elif button == BUTTON_UP:
        _game.fleet_selection = (_game.fleet_selection - 1) % count
    elif button == BUTTON_DOWN:
        _game.fleet_selection = (_game.fleet_selection + 1) % count
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        if _game.fleet_selection < len(_game.ships):
            _game.switch_ship(_game.fleet_selection)
        else:
            _game.buy_ship()
    elif button == BUTTON_B:
        if _game.fleet_selection < len(_game.ships):
            _game.route_ship = _game.fleet_selection
            _game.map_selection = _game.ships[_game.route_ship][SHIP_PORT]
            _game.screen = SCREEN_ROUTE
    elif button == BUTTON_S:
        if _game.fleet_selection < len(_game.ships):
            if _game.switch_ship(_game.fleet_selection):
                _game.screen = SCREEN_CARGO


def _handle_route(button):
    ship_index = _game.route_ship
    if button == BUTTON_BACK:
        _game.fleet_selection = ship_index
        _game.screen = SCREEN_FLEET
    elif button == BUTTON_LEFT:
        _game.map_selection = (_game.map_selection - 1) % len(PORT_NAMES)
    elif button == BUTTON_RIGHT:
        _game.map_selection = (_game.map_selection + 1) % len(PORT_NAMES)
    elif button == BUTTON_UP:
        _game.cycle_route_reserve(ship_index)
    elif button == BUTTON_DOWN:
        _game.cycle_route_repair(ship_index)
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.toggle_route_port(ship_index, _game.map_selection)
    elif button == BUTTON_B:
        _game.cycle_route_goods(ship_index, _game.map_selection)
    elif button == BUTTON_S:
        _game.toggle_route(ship_index)


def _handle_help(button):
    if button == BUTTON_LEFT:
        _game.help_page = (_game.help_page - 1) % 6
    elif button in (BUTTON_RIGHT, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.help_page = (_game.help_page + 1) % 6
    elif button == BUTTON_BACK:
        _game.screen = _game.return_screen


def _handle_end(view_manager, button):
    if button == BUTTON_BACK:
        view_manager.back()
        return False
    if button in (BUTTON_LEFT, BUTTON_UP):
        _game.result_page = (_game.result_page - 1) % 3
    elif button in (BUTTON_RIGHT, BUTTON_DOWN):
        _game.result_page = (_game.result_page + 1) % 3
    elif button in (BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
        _game.mode_selection = 0
        _game.screen = SCREEN_MODE
    return True


def run(view_manager):
    """Process input and cooperative low-rate ambient animation."""
    global _animation_phase, _next_animation, _last_screen
    if _game is None or _renderer is None:
        return
    now = ticks_ms()
    button = view_manager.button
    if button < 0:
        if _sound is not None:
            _sound.update(_game, now)
        if (
            _game.screen in ANIMATED_SCREENS
            and ticks_diff(now, _next_animation) >= 0
        ):
            _animation_phase = (_animation_phase + 1) & 7
            _renderer.draw_animation(_game, _animation_phase)
            _next_animation = ticks_add(
                now,
                _animation_interval(_game.screen),
            )
        return

    _set_key_repeat(
        view_manager,
        _game.screen in (SCREEN_MARKET, SCREEN_MAP, SCREEN_OFFICE, SCREEN_BUSINESS),
    )
    view_manager.input_manager.reset()
    should_draw = True

    audio_button = button == BUTTON_P
    if audio_button and _sound is not None:
        _sound.toggle_music(_game, now)

    elif _game.screen == SCREEN_TITLE:
        should_draw = _handle_title(view_manager, button)
    elif _game.screen == SCREEN_MODE:
        _handle_mode(button)
    elif _game.screen == SCREEN_SAVES:
        _handle_saves(button)
    elif _game.screen == SCREEN_AUDIO:
        _handle_audio(button, now)
    elif _game.screen == SCREEN_PORT:
        _handle_port(button)
    elif _game.screen == SCREEN_OVERVIEW:
        _handle_overview(button)
    elif _game.screen == SCREEN_MARKET:
        _handle_market(button)
    elif _game.screen == SCREEN_MAP:
        _handle_map(button)
    elif _game.screen == SCREEN_WAIT:
        _handle_wait(button)
    elif _game.screen == SCREEN_CITY:
        if button == BUTTON_B:
            _game.contribute_project()
        elif button in (BUTTON_BACK, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
            _return_to_port()
    elif _game.screen == SCREEN_LOG:
        if button in (BUTTON_BACK, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
            _return_to_port()
    elif _game.screen == SCREEN_ADVISER:
        if button == BUTTON_B:
            _game.council_selection = 0
            _game.screen = SCREEN_COUNCIL
        elif button in (BUTTON_BACK, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
            _return_to_port()
    elif _game.screen == SCREEN_COUNCIL:
        _handle_council(button)
    elif _game.screen == SCREEN_BANK:
        _handle_bank(button)
    elif _game.screen == SCREEN_SHIPYARD:
        _handle_shipyard(button)
    elif _game.screen == SCREEN_CONTRACTS:
        _handle_contracts(button)
    elif _game.screen == SCREEN_OFFICE:
        _handle_office(button)
    elif _game.screen == SCREEN_BUSINESS:
        _handle_business(button)
    elif _game.screen == SCREEN_FLEET:
        _handle_fleet(button)
    elif _game.screen == SCREEN_ROUTE:
        _handle_route(button)
    elif _game.screen == SCREEN_HELP:
        _handle_help(button)
    elif _game.screen in (
        SCREEN_CARGO,
        SCREEN_LEDGER,
        SCREEN_TAVERN,
        SCREEN_RIVALS,
    ):
        if button in (BUTTON_BACK, BUTTON_CENTER, BUTTON_ENTER, BUTTON_SPACE):
            _return_to_port()
    elif _game.screen == SCREEN_EVENT:
        _handle_scroll(button)
    elif _game.screen == SCREEN_DECISION:
        _handle_decision(button)
    elif _game.screen == SCREEN_END:
        should_draw = _handle_end(view_manager, button)

    if should_draw and _renderer is not None:
        if _game.screen != _last_screen:
            _animation_phase = 0
        else:
            _animation_phase = (_animation_phase + 1) & 7
        _last_screen = _game.screen
        _next_animation = ticks_add(now, _animation_interval(_game.screen))
        _renderer.draw_frame(_game, _animation_phase)
    if _sound is not None:
        _sound.update(_game, now)


def stop(view_manager):
    """Persist an active voyage and release all game state."""
    global _game, _renderer, _store, _sound, _animation_phase, _next_animation, _last_screen
    _set_key_repeat(view_manager, False, True)
    if _game is not None and _store is not None and _game.screen not in (
        SCREEN_TITLE,
        SCREEN_END,
        SCREEN_MODE,
        SCREEN_SAVES,
        SCREEN_AUDIO,
    ):
        _store.save(_game)
    if _sound is not None:
        _sound.stop()
    _game = None
    _renderer = None
    _store = None
    _sound = None
    _animation_phase = 0
    _next_animation = 0
    _last_screen = -1
    collect()
