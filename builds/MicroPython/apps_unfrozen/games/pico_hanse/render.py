"""Original period-inspired renderer for Pico Hanse."""

from picoware.system.colors import (
    TFT_BLACK,
    TFT_DARKGREY,
    TFT_GREEN,
    TFT_LIGHTGREY,
    TFT_RED,
    TFT_WHITE,
    TFT_YELLOW,
)

from .model import (
    ALDERMAN_REPUTATION,
    ALDERMAN_WEALTH,
    CAPTAIN_NAMES,
    BUSINESS_INPUT,
    BUSINESS_NAMES,
    CITY_PROJECT_NAMES,
    CAMPAIGN_DAYS,
    COUNCILLOR_REPUTATION,
    COUNCILLOR_WEALTH,
    COUNCIL_ISSUES,
    COUNCIL_OPTIONS,
    CONTRACT_DEADLINE,
    CONTRACT_DEST,
    CONTRACT_GOOD,
    CONTRACT_QTY,
    CONTRACT_REWARD,
    EVENT_FAIR,
    GOOD_NAMES,
    HARBOR_LOCATIONS,
    HARBOR_PRIMARY,
    HARBOR_SECONDARY,
    MAYOR_REPUTATION,
    MAYOR_WEALTH,
    MODE_CAREER,
    MISSION_DEADLINE,
    MISSION_DEST,
    MISSION_GOOD,
    MISSION_ID,
    MISSION_ORIGIN,
    MISSION_QTY,
    MISSION_REWARD,
    MISSION_STATE,
    MISSION_OFFERED,
    ORDER_READY,
    ORDER_SAIL,
    ORDER_WAIT,
    ROUTE_ATTENTION,
    ROUTE_NOTE,
    ROUTE_PAUSED,
    ROUTE_PORTS,
    ROUTE_PROFIT,
    ROUTE_REPAIR,
    ROUTE_RESERVE,
    ROUTE_RULES,
    ROUTE_RUNNING,
    ROUTE_STATE,
    LEDGER_COST,
    LEDGER_PORTS,
    LEDGER_REVENUE,
    LEDGER_VISITS,
    PROJECT_COMPLETE,
    PROJECT_DEADLINE,
    PROJECT_GOOD_A,
    PROJECT_GOOD_B,
    PROJECT_HAVE_A,
    PROJECT_HAVE_B,
    PROJECT_NEED_A,
    PROJECT_NEED_B,
    PORT_MOTTO,
    PORT_NAMES,
    PORT_POSITIONS,
    RANK_NAMES,
    SAVE_MODE_LOAD,
    SCREEN_AUDIO,
    SCREEN_BANK,
    SCREEN_CARGO,
    SCREEN_BUSINESS,
    SCREEN_CITY,
    SCREEN_COUNCIL,
    SCREEN_CONTRACTS,
    SCREEN_END,
    SCREEN_DECISION,
    SCREEN_EVENT,
    SCREEN_FLEET,
    SCREEN_HELP,
    SCREEN_ADVISER,
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
    SHIP_CAPACITY,
    SHIP_CAPTAIN,
    SHIP_CARGO,
    SHIP_DEST,
    SHIP_EARNINGS,
    SHIP_HULL,
    SHIP_NAME,
    SHIP_NAMES,
    SHIP_TYPE_COST,
    SHIP_TYPE_NAMES,
    SHIP_PORT,
    SHIP_ORDER,
    WEATHER_CLEAR,
    WEATHER_ICE,
    WEATHER_RAIN,
    WEATHER_SNOW,
    WEATHER_STORM,
    RIVAL_NAMES,
    STORY_NAMES,
    WEALTH_GOAL,
)


# RGB565 colors chosen to evoke parchment, timber, oxidized brass, and sea.
COLOR_WOOD = 0x5962
COLOR_WOOD_DARK = 0x30E1
COLOR_WOOD_LIGHT = 0x8A64
COLOR_PARCHMENT = 0xEECB
COLOR_PARCHMENT_DARK = 0xC5A6
COLOR_INK = 0x28E2
COLOR_BRASS = 0xD568
COLOR_GOLD = 0xF5C4
COLOR_SEA = 0x1B6D
COLOR_SEA_DARK = 0x1269
COLOR_SEA_LIGHT = 0x44D4
COLOR_LAND = 0x7B85
COLOR_LAND_LIGHT = 0xA4A8
COLOR_HARBOR = 0x8B43
COLOR_GREEN_DARK = 0x34A4
COLOR_RED_DARK = 0x9022
COLOR_BLUE_INK = 0x214B


class Renderer:
    """Draw complete game screens with low-cost LCD primitives."""

    __slots__ = ("draw", "width", "height", "phase")

    def __init__(self, draw):
        self.draw = draw
        self.width = draw.size.x
        self.height = draw.size.y
        self.phase = 0

    def _x(self, value):
        return value * self.width // 320

    def _y(self, value):
        return value * self.height // 320

    def _w(self, value):
        return max(1, value * self.width // 320)

    def _h(self, value):
        return max(1, value * self.height // 320)

    def _rect(self, x, y, w, h, color):
        self.draw._rectangle(self._x(x), self._y(y), self._w(w), self._h(h), color)

    def _fill(self, x, y, w, h, color):
        self.draw._fill_rectangle(self._x(x), self._y(y), self._w(w), self._h(h), color)

    def _line(self, x1, y1, x2, y2, color):
        self.draw._line(self._x(x1), self._y(y1), self._x(x2), self._y(y2), color)

    def _circle(self, x, y, radius, color, fill=False):
        radius = max(1, self._w(radius))
        if fill:
            self.draw._fill_circle(self._x(x), self._y(y), radius, color)
        else:
            self.draw._circle(self._x(x), self._y(y), radius, color)

    def _text(self, x, y, text, color=COLOR_INK, font=0):
        self.draw._text(self._x(x), self._y(y), str(text), color, font)

    def _center(self, text, y, color=COLOR_INK, font=0):
        text = str(text)
        width = self.draw.len(text, font)
        self.draw._text(max(0, (self.width - width) // 2), self._y(y), text, color, font)

    def _panel(self, x, y, w, h, fill=COLOR_PARCHMENT):
        self._fill(x, y, w, h, COLOR_WOOD_DARK)
        self._rect(x, y, w, h, COLOR_BRASS)
        self._fill(x + 3, y + 3, w - 6, h - 6, fill)
        self._rect(x + 3, y + 3, w - 6, h - 6, COLOR_WOOD_LIGHT)
        for px, py in ((x + 7, y + 7), (x + w - 7, y + 7), (x + 7, y + h - 7), (x + w - 7, y + h - 7)):
            self._circle(px, py, 2, COLOR_BRASS, True)

    def _header(self, title, game):
        self._fill(0, 0, 320, 30, COLOR_WOOD_DARK)
        self._line(0, 28, 320, 28, COLOR_BRASS)
        self._text(9, 3, str(title)[:19], COLOR_GOLD, 1)
        self._circle(5, 14, 2, COLOR_BRASS, True)
        right = "D%03d  %dS" % (game.day, game.cash)
        right_width = self.draw.len(right, 0)
        self.draw._text(max(0, self.width - right_width - self._x(8)), self._y(5), right, COLOR_PARCHMENT, 0)
        self._text(9, 19, game.command_line()[:38], COLOR_SEA_LIGHT, 0)

    def _footer(self, text):
        self._fill(0, 300, 320, 20, COLOR_WOOD_DARK)
        self._line(0, 299, 320, 299, COLOR_BRASS)
        clipped = str(text)[:38]
        self._center(clipped, 306, COLOR_PARCHMENT, 0)
        self._circle(7, 309, 2, COLOR_BRASS, True)
        self._circle(313, 309, 2, COLOR_BRASS, True)

    def _wrap(self, text, width=31):
        words = str(text).split()
        lines = []
        line = ""
        for word in words:
            candidate = word if not line else line + " " + word
            if len(candidate) <= width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _draw_shield(self, x, y, color, letter):
        self._fill(x, y, 20, 16, color)
        self._line(x, y + 16, x + 10, y + 23, color)
        self._line(x + 20, y + 16, x + 10, y + 23, color)
        self._text(x + 7, y + 5, letter, TFT_WHITE, 0)

    def _draw_good_icon(self, x, y, good, selected=False):
        """Draw a distinct 20px commodity emblem instead of a letter tile."""
        bg = COLOR_BRASS if selected else COLOR_PARCHMENT_DARK
        self._circle(x + 10, y + 10, 10, COLOR_INK, True)
        self._circle(x + 10, y + 10, 9, bg, True)
        if good == 0:  # grain stalk
            self._line(x + 10, y + 3, x + 10, y + 18, COLOR_GOLD)
            for step in (5, 9, 13):
                self._line(x + 10, y + step, x + 5, y + step - 3, COLOR_GOLD)
                self._line(x + 10, y + step + 1, x + 15, y + step - 2, COLOR_GOLD)
        elif good == 1:  # fish
            self._circle(x + 9, y + 10, 5, COLOR_SEA_LIGHT, True)
            self._line(x + 14, y + 10, x + 18, y + 6, COLOR_SEA_LIGHT)
            self._line(x + 14, y + 10, x + 18, y + 14, COLOR_SEA_LIGHT)
            self._circle(x + 7, y + 8, 1, TFT_WHITE, True)
        elif good == 2:  # timber
            self._fill(x + 4, y + 6, 13, 4, COLOR_WOOD)
            self._fill(x + 3, y + 12, 13, 4, COLOR_WOOD_DARK)
            self._circle(x + 16, y + 8, 2, COLOR_PARCHMENT, False)
            self._circle(x + 15, y + 14, 2, COLOR_PARCHMENT, False)
        elif good == 3:  # salt sack
            self._line(x + 7, y + 4, x + 13, y + 4, COLOR_BLUE_INK)
            self._line(x + 7, y + 4, x + 5, y + 16, COLOR_BLUE_INK)
            self._line(x + 13, y + 4, x + 15, y + 16, COLOR_BLUE_INK)
            self._line(x + 5, y + 16, x + 15, y + 16, COLOR_BLUE_INK)
            self._circle(x + 9, y + 10, 1, TFT_WHITE, True)
            self._circle(x + 12, y + 12, 1, TFT_WHITE, True)
        elif good == 4:  # folded cloth
            self._fill(x + 4, y + 5, 13, 12, COLOR_RED_DARK)
            self._line(x + 7, y + 5, x + 7, y + 17, COLOR_GOLD)
            self._line(x + 12, y + 5, x + 12, y + 17, COLOR_PARCHMENT)
        elif good == 5:  # iron ingot
            self._fill(x + 4, y + 8, 13, 8, TFT_DARKGREY)
            self._line(x + 4, y + 8, x + 7, y + 5, TFT_LIGHTGREY)
            self._line(x + 17, y + 8, x + 14, y + 5, TFT_LIGHTGREY)
            self._line(x + 7, y + 5, x + 14, y + 5, TFT_LIGHTGREY)
        elif good == 6:  # beer mug
            self._fill(x + 5, y + 6, 9, 11, COLOR_GOLD)
            self._line(x + 14, y + 8, x + 18, y + 8, COLOR_GOLD)
            self._line(x + 18, y + 8, x + 18, y + 14, COLOR_GOLD)
            self._line(x + 18, y + 14, x + 14, y + 14, COLOR_GOLD)
            self._line(x + 5, y + 6, x + 14, y + 6, TFT_WHITE)
        else:  # wax candle
            self._fill(x + 7, y + 8, 7, 10, COLOR_GOLD)
            self._line(x + 9, y + 11, x + 12, y + 9, COLOR_PARCHMENT)
            flame_y = y + (4 if self.phase & 1 else 3)
            self._circle(x + 10, flame_y, 2, TFT_RED, True)
            self._circle(x + 10, flame_y, 1, TFT_YELLOW, True)

    def _draw_ship(self, x, y, scale=1, ship_type=0):
        # Three original silhouettes: balanced cog, fast kraier, broad hulk.
        bob = (0, 1, 1, 0, -1, -1, 0, 0)[self.phase] * scale
        y += bob
        hull_w = (42 if ship_type == 1 else 54 if ship_type == 2 else 48) * scale
        mast_x = (20 if ship_type == 1 else 27 if ship_type == 2 else 24) * scale
        self._fill(x, y + 18 * scale, hull_w, 8 * scale, COLOR_WOOD_DARK)
        self._line(x, y + 26 * scale, x + 9 * scale, y + 33 * scale, COLOR_WOOD_DARK)
        self._line(x + hull_w, y + 26 * scale, x + hull_w - 9 * scale, y + 33 * scale, COLOR_WOOD_DARK)
        self._line(x + 9 * scale, y + 33 * scale, x + hull_w - 9 * scale, y + 33 * scale, COLOR_WOOD_DARK)
        if ship_type == 2:
            self._fill(x + 4 * scale, y + 13 * scale, hull_w - 8 * scale, 5 * scale, COLOR_WOOD)
        self._line(x + mast_x, y - 8 * scale, x + mast_x, y + 20 * scale, COLOR_INK)
        sail_w = ((16 if ship_type == 1 else 21) + (self.phase & 1)) * scale
        sail_color = COLOR_GOLD if ship_type == 1 else COLOR_PARCHMENT if ship_type == 2 else COLOR_RED_DARK
        self._fill(x + mast_x + scale, y - 5 * scale, sail_w, 17 * scale, sail_color)
        self._line(x + mast_x + scale, y - 5 * scale, x + mast_x + scale + sail_w, y + 12 * scale, COLOR_BRASS)
        wave = (self.phase * 3) % 12
        self._line(x - 5 * scale + wave, y + 36 * scale, x + 28 * scale + wave, y + 36 * scale, COLOR_SEA_LIGHT)
        self._line(x + 19 * scale - wave, y + 39 * scale, x + 54 * scale - wave, y + 39 * scale, COLOR_SEA_LIGHT)

    def _draw_weather(self, game, top=36, bottom=134):
        if game.weather == WEATHER_CLEAR:
            return
        if game.weather in (WEATHER_RAIN, WEATHER_STORM):
            color = COLOR_BLUE_INK if game.weather == WEATHER_RAIN else TFT_DARKGREY
            count = 8 if game.weather == WEATHER_RAIN else 14
            for index in range(count):
                x = (index * 29 + self.phase * 7) % 310 + 5
                y = top + (index * 19 + self.phase * 5) % max(8, bottom - top)
                self._line(x, y, x - 4, y + 8, color)
        elif game.weather == WEATHER_SNOW:
            for index in range(13):
                x = (index * 41 + self.phase * 5) % 310 + 5
                y = top + (index * 17 + self.phase * 4) % max(8, bottom - top)
                self._circle(x, y, 1, TFT_WHITE, True)
        elif game.weather == WEATHER_ICE:
            for x in range(12, 312, 38):
                self._line(x, bottom - 8, x + 12, bottom - 13, TFT_LIGHTGREY)
                self._line(x + 12, bottom - 13, x + 22, bottom - 7, TFT_LIGHTGREY)

    def _draw_market_row(self, game, index):
        y = 61 + index * 26
        selected = index == game.market_selection
        self._fill(15, y, 290, 23, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT)
        if selected:
            self._rect(15, y, 290, 23, COLOR_GOLD if self.phase & 1 else COLOR_BRASS)
        color = COLOR_GOLD if selected else COLOR_INK
        self._draw_good_icon(19, y + 2, index, selected)
        self._text(46, y + 7, GOOD_NAMES[index], color, 0)
        self._text(145, y + 7, game.buy_price(index), color, 0)
        self._text(198, y + 7, game.sell_price(index), color, 0)
        need = game.city_need_level(game.current_port, index)
        label = "U" if need == "URGENT" else "H" if need == "HIGH" else "M" if need == "MED" else "L"
        need_color = COLOR_RED_DARK if need in ("URGENT", "HIGH") else COLOR_GOLD if need == "MED" else COLOR_GREEN_DARK
        self._text(239, y + 7, label, need_color, 0)
        self._text(280, y + 7, game.cargo[index], color, 0)
        if selected and (game.status.startswith("BOUGHT") or game.status.startswith("SOLD")):
            coin_y = y + 5 + (self.phase & 3)
            self._circle(129, coin_y, 3, COLOR_GOLD, True)
            self._circle(129, coin_y, 3, COLOR_INK, False)

    def _draw_office_row(self, game, index):
        y = 61 + index * 26
        selected = index == game.office_selection
        self._fill(15, y, 290, 23, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT)
        if selected:
            self._rect(15, y, 290, 23, COLOR_GOLD if self.phase & 1 else COLOR_BRASS)
        color = COLOR_GOLD if selected else COLOR_INK
        self._draw_good_icon(19, y + 2, index, selected)
        self._text(47, y + 7, GOOD_NAMES[index], color, 0)
        self._text(174, y + 7, game.cargo[index], color, 0)
        self._text(220, y + 7, game.warehouses[game.current_port][index], color, 0)
        forecast = game.market_forecast(game.current_port, index)
        forecast_color = COLOR_RED_DARK if forecast == "UP" else COLOR_GREEN_DARK if forecast == "DOWN" else color
        self._text(270, y + 7, forecast, forecast_color if not selected else COLOR_GOLD, 0)

    def _draw_tavern_candles(self):
        flame_y = 58 + (self.phase & 1)
        for candle_x in (39, 274):
            self._fill(candle_x - 6, 52, 13, 34, COLOR_PARCHMENT)
            self._fill(candle_x - 3, 63, 7, 18, COLOR_GOLD)
            self._rect(candle_x - 3, 63, 7, 18, COLOR_INK)
            self._line(candle_x, 63, candle_x, 58, COLOR_INK)
            self._circle(candle_x, flame_y, 3, TFT_RED, True)
            self._circle(candle_x, flame_y, 1, TFT_YELLOW, True)
            self._circle(candle_x, flame_y, 5 + (self.phase & 1), COLOR_GOLD, False)

    def draw_title(self, game):
        draw = self.draw
        draw.fill_screen(COLOR_WOOD_DARK)
        self._fill(5, 5, 310, 310, COLOR_WOOD)
        self._rect(5, 5, 310, 310, COLOR_BRASS)
        self._rect(10, 10, 300, 300, COLOR_WOOD_DARK)
        self._fill(14, 14, 292, 292, COLOR_SEA_DARK)

        # Old chart lines and coast fragments establish the trading-map mood.
        for y in (54, 91, 128, 165, 202, 239):
            self._line(15, y, 305, y, COLOR_SEA)
        for x in (48, 93, 138, 183, 228, 273):
            self._line(x, 15, x, 305, COLOR_SEA)
        self._fill(15, 15, 42, 132, COLOR_LAND)
        self._fill(15, 220, 105, 85, COLOR_LAND)
        self._fill(260, 15, 45, 117, COLOR_LAND)
        self._line(57, 147, 85, 173, COLOR_LAND_LIGHT)
        self._line(85, 173, 120, 184, COLOR_LAND_LIGHT)
        self._line(120, 184, 136, 212, COLOR_LAND_LIGHT)
        self._line(260, 132, 235, 160, COLOR_LAND_LIGHT)
        gull_x = 205 + self.phase * 2
        self._line(gull_x, 121, gull_x + 4, 118, COLOR_PARCHMENT)
        self._line(gull_x + 4, 118, gull_x + 8, 121, COLOR_PARCHMENT)

        self._panel(38, 27, 244, 76)
        self._center("PICO HANSE", 43, COLOR_INK, 3)
        self._center("MERCHANT GUILD OF THE NORTH", 80, COLOR_RED_DARK, 0)
        self._draw_ship(136, 125, 1)

        options = ["NEW VOYAGE", "CONTINUE", "HOW TO PLAY"]
        top = 208
        for index in range(len(options)):
            enabled = index != 1 or game.save_available
            selected = index == game.title_selection
            color = COLOR_GOLD if selected else COLOR_PARCHMENT if enabled else TFT_DARKGREY
            marker = ">" if selected else " "
            self._center(marker + " " + options[index], top + index * 24, color, 1 if selected else 0)
        self._center("ARROWS + CENTER", 292, COLOR_SEA_LIGHT, 0)
        draw.swap()

    def draw_mode(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._panel(18, 25, 284, 270)
        self._draw_shield(142, 42, COLOR_RED_DARK, "H")
        self._center("CHOOSE YOUR LEDGER", 82, COLOR_RED_DARK, 2)
        options = (
            ("HANSEATIC CAREER", "RISE TO ALDERMAN THROUGH ELECTIONS"),
            ("QUICK GAME", "REACH %dS BEFORE DAY %d" % (WEALTH_GOAL, CAMPAIGN_DAYS)),
        )
        for index in range(2):
            y = 126 + index * 68
            selected = index == game.mode_selection
            self._fill(36, y, 248, 54, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(36, y, 248, 54, COLOR_GOLD if selected else COLOR_BRASS)
            color = COLOR_GOLD if selected else COLOR_INK
            self._center(("> " if selected else "  ") + options[index][0], y + 9, color, 1)
            self._center(options[index][1], y + 34, COLOR_PARCHMENT if selected else COLOR_BLUE_INK, 0)
        if game.audio_files_missing:
            self._center("OPTIONAL MULTIMEDIA PACK NOT INSTALLED", 262, COLOR_RED_DARK, 0)
            self._center("GAME RUNS SILENTLY", 276, COLOR_BLUE_INK, 0)
        else:
            self._center(
                "MUSIC %s  EFFECTS %s  VOL %d%%" % (
                    "ON" if game.music_enabled else "OFF",
                    "ON" if game.effects_enabled else "OFF", game.audio_volume,
                ),
                269, COLOR_GREEN_DARK if game.music_enabled else COLOR_BLUE_INK, 0,
            )
        self._footer("ARROWS CHOOSE CENTER BEGIN  B AUDIO")
        self.draw.swap()

    def draw_saves(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._panel(20, 24, 280, 272)
        self._draw_shield(142, 40, COLOR_RED_DARK, "L")
        title = "OPEN A LEDGER" if game.save_mode == SAVE_MODE_LOAD else "CHOOSE A LEDGER"
        self._center(title, 78, COLOR_RED_DARK, 2)
        for index in range(3):
            y = 111 + index * 52
            selected = index == game.save_selection
            self._fill(38, y, 244, 43, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(38, y, 244, 43, COLOR_GOLD if selected else COLOR_BRASS)
            summary = game.save_summaries[index]
            label = ("> " if selected else "  ") + "LEDGER %d" % (index + 1)
            self._text(50, y + 7, label, COLOR_GOLD if selected else COLOR_RED_DARK, 1)
            if summary is None:
                detail = "EMPTY - READY FOR A NEW HOUSE"
            elif summary[0] == 0:
                detail = "DAMAGED LEDGER"
            else:
                detail = "DAY %d  %dS  %s  %d SHIP%s" % (
                    summary[0], summary[1], RANK_NAMES[min(summary[2], len(RANK_NAMES) - 1)],
                    summary[3], "" if summary[3] == 1 else "S",
                )
            self._text(52, y + 26, detail[:37], COLOR_PARCHMENT if selected else COLOR_INK, 0)
        if game.save_confirm:
            self._center("REPLACE THIS LEDGER? CENTER CONFIRMS", 275, COLOR_RED_DARK, 0)
        else:
            self._center("YOUR OTHER LEDGERS STAY UNTOUCHED", 275, COLOR_BLUE_INK, 0)
        self._footer("UP/DOWN CHOOSE  CENTER OPEN  BACK")
        self.draw.swap()

    def draw_audio(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._panel(26, 31, 268, 255)
        self._draw_shield(142, 48, COLOR_RED_DARK, "A")
        self._center("MUSIC AND SOUND", 87, COLOR_RED_DARK, 2)
        values = (
            "ON" if game.music_enabled else "OFF",
            "ON" if game.effects_enabled else "OFF",
            "%d%%" % game.audio_volume,
        )
        names = ("MUSIC", "EFFECTS", "VOLUME")
        for index in range(3):
            y = 125 + index * 43
            selected = index == game.audio_selection
            self._fill(48, y, 224, 34, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(48, y, 224, 34, COLOR_GOLD if selected else COLOR_BRASS)
            self._text(61, y + 10, ("> " if selected else "  ") + names[index],
                       COLOR_GOLD if selected else COLOR_INK, 1)
            self._text(220, y + 10, values[index],
                       COLOR_PARCHMENT if selected else COLOR_BLUE_INK, 1)
        note = "PACK MISSING - SILENT FALLBACK" if game.audio_files_missing else "P TOGGLES MUSIC DURING PLAY"
        self._center(note, 263, COLOR_RED_DARK if game.audio_files_missing else COLOR_BLUE_INK, 0)
        self._footer("UP/DOWN CHOOSE  LEFT/RIGHT CHANGE")
        self.draw.swap()

    def _harbor_house(self, x, base, width, height, color, stepped=False):
        """Draw one compact Hanseatic facade for a port skyline."""
        top = base - height
        self._fill(x, top, width, height, color)
        if stepped:
            inset = max(2, width // 5)
            self._fill(x + inset, top - 5, width - inset * 2, 5, color)
            self._fill(x + inset * 2, top - 9, width - inset * 4, 4, color)
        else:
            self._line(x, top, x + width // 2, top - 7, COLOR_INK)
            self._line(x + width, top, x + width // 2, top - 7, COLOR_INK)
        self._rect(x, top, width, height, COLOR_INK)
        window_y = max(top + 6, base - 16)
        self._fill(x + 4, window_y, 4, 6, COLOR_INK)
        if width >= 17:
            self._fill(x + width - 8, window_y, 4, 6, COLOR_INK)

    def _harbor_tower(self, x, base, width, height, color, roof=True):
        top = base - height
        self._fill(x, top, width, height, color)
        self._rect(x, top, width, height, COLOR_INK)
        if roof:
            self._line(x, top, x + width // 2, top - 10, COLOR_INK)
            self._line(x + width, top, x + width // 2, top - 10, COLOR_INK)
            self._line(x + width // 2, top - 10, x + width // 2, top - 14, COLOR_INK)
        self._fill(x + width // 2 - 2, top + 7, 4, 8, COLOR_INK)

    def _draw_lubeck_skyline(self):
        # Merchant houses and the twin-towered Holsten gate.
        self._harbor_house(13, 101, 25, 24, COLOR_WOOD_LIGHT, True)
        self._harbor_house(41, 101, 23, 30, COLOR_HARBOR, True)
        self._harbor_house(67, 101, 25, 21, COLOR_WOOD_LIGHT)
        self._harbor_tower(220, 101, 18, 40, COLOR_HARBOR, False)
        self._harbor_tower(269, 101, 18, 40, COLOR_HARBOR, False)
        self._line(220, 61, 229, 51, COLOR_INK)
        self._line(238, 61, 229, 51, COLOR_INK)
        self._line(269, 61, 278, 51, COLOR_INK)
        self._line(287, 61, 278, 51, COLOR_INK)
        self._fill(238, 72, 31, 29, COLOR_WOOD_LIGHT)
        self._rect(238, 72, 31, 29, COLOR_INK)
        self._circle(253, 91, 7, COLOR_INK, True)
        self._fill(246, 91, 15, 10, COLOR_INK)
        self._line(238, 72, 253, 64, COLOR_INK)
        self._line(269, 72, 253, 64, COLOR_INK)

    def _draw_hamburg_skyline(self):
        # Long warehouse quay, St Michael's spire, and working dock cranes.
        for index in range(5):
            self._harbor_house(11 + index * 35, 101, 31, 19 + (index & 1) * 6,
                               COLOR_HARBOR if index & 1 else COLOR_WOOD_LIGHT, True)
        self._harbor_tower(284, 101, 15, 38, COLOR_WOOD_LIGHT)
        hook = 84 + (self.phase & 1) * 3
        for x in (203, 243):
            self._line(x, 100, x, 61, COLOR_WOOD_DARK)
            self._line(x, 61, x + 30, 67, COLOR_WOOD_DARK)
            self._line(x + 30, 67, x + 30, hook, COLOR_INK)
            self._circle(x + 30, hook + 2, 2, COLOR_INK, False)

    def _draw_bremen_skyline(self):
        # Stepped town-hall fronts and Roland watching the market quay.
        for index in range(4):
            self._harbor_house(13 + index * 36, 101, 30, 23 + index * 3,
                               COLOR_WOOD_LIGHT if index & 1 else COLOR_HARBOR, True)
        self._harbor_house(215, 101, 52, 32, COLOR_WOOD_LIGHT, True)
        for x in (224, 239, 254):
            self._fill(x, 78, 5, 13, COLOR_INK)
        self._circle(287, 68, 4, COLOR_PARCHMENT, True)
        self._line(287, 72, 287, 91, COLOR_INK)
        self._line(287, 76, 280, 83, COLOR_INK)
        self._line(287, 76, 294, 80, COLOR_INK)
        self._fill(282, 91, 11, 10, COLOR_WOOD_DARK)

    def _draw_rostock_skyline(self):
        # Brick gate on the old town side and open shipyard frames.
        self._harbor_house(13, 101, 28, 24, COLOR_HARBOR, True)
        self._harbor_house(45, 101, 31, 30, COLOR_WOOD_LIGHT, True)
        self._harbor_house(80, 101, 27, 20, COLOR_HARBOR)
        self._fill(208, 62, 50, 39, COLOR_HARBOR)
        self._rect(208, 62, 50, 39, COLOR_INK)
        for x in (208, 250):
            self._fill(x, 54, 8, 47, COLOR_WOOD_LIGHT)
            self._rect(x, 54, 8, 47, COLOR_INK)
        self._circle(233, 91, 7, COLOR_INK, True)
        self._fill(226, 91, 15, 10, COLOR_INK)
        for x in (273, 294):
            self._line(x, 101, x, 56, COLOR_WOOD_DARK)
            self._line(x, 64, x + 14, 101, COLOR_WOOD_DARK)
        pennant = 5 + (self.phase & 1) * 3
        self._fill(273, 57, pennant, 4, COLOR_RED_DARK)

    def _draw_danzig_skyline(self):
        # Riverside granaries and the great timber harbour crane.
        for index in range(5):
            self._harbor_house(12 + index * 34, 101, 29, 22 + (index % 3) * 5,
                               COLOR_HARBOR if index & 1 else COLOR_WOOD_LIGHT, True)
        self._fill(226, 59, 39, 42, COLOR_WOOD_DARK)
        self._rect(226, 59, 39, 42, COLOR_INK)
        self._line(226, 59, 245, 48, COLOR_INK)
        self._line(265, 59, 245, 48, COLOR_INK)
        self._fill(239, 84, 13, 17, COLOR_INK)
        self._line(265, 61, 297, 51, COLOR_WOOD_DARK)
        self._line(265, 67, 297, 51, COLOR_WOOD_DARK)
        hook_y = 75 + (self.phase & 1) * 3
        self._line(292, 53, 292, hook_y, COLOR_INK)
        self._circle(292, hook_y + 2, 2, COLOR_INK, False)

    def _draw_riga_skyline(self):
        # Slender guild houses beneath Riga's cluster of church spires.
        for index in range(6):
            self._harbor_house(12 + index * 29, 101, 24, 21 + (index & 1) * 7,
                               COLOR_WOOD_LIGHT if index % 3 else COLOR_HARBOR, True)
        for x, height in ((215, 34), (250, 45), (284, 29)):
            self._harbor_tower(x, 101, 14, height, COLOR_HARBOR)
            top = 101 - height - 14
            self._line(x + 7, top, x + 7, top - 8, COLOR_INK)
            self._circle(x + 7, top - 9, 2, COLOR_GOLD, True)

    def _draw_visby_skyline(self):
        # Low stone city wall with crenellations and watch towers.
        self._harbor_house(13, 101, 28, 22, COLOR_WOOD_LIGHT)
        self._harbor_house(44, 101, 25, 27, COLOR_HARBOR)
        self._fill(181, 77, 117, 24, COLOR_LAND_LIGHT)
        self._rect(181, 77, 117, 24, COLOR_INK)
        for x in range(184, 298, 13):
            self._fill(x, 72, 7, 6, COLOR_LAND_LIGHT)
        for x in (190, 267):
            self._fill(x, 57, 22, 44, COLOR_LAND_LIGHT)
            self._rect(x, 57, 22, 44, COLOR_INK)
            self._fill(x - 3, 52, 7, 7, COLOR_LAND_LIGHT)
            self._fill(x + 8, 52, 7, 7, COLOR_LAND_LIGHT)
            self._fill(x + 19, 52, 7, 7, COLOR_LAND_LIGHT)
            self._fill(x + 8, 69, 5, 9, COLOR_INK)
        self._circle(240, 92, 6, COLOR_INK, True)
        self._fill(234, 92, 13, 9, COLOR_INK)

    def _draw_stockholm_skyline(self):
        # Island quays, a royal waterfront block, bridge, and flag tower.
        self._fill(10, 91, 94, 10, COLOR_LAND)
        self._fill(114, 95, 72, 6, COLOR_LAND_LIGHT)
        self._fill(198, 88, 102, 13, COLOR_LAND)
        self._harbor_house(18, 91, 23, 21, COLOR_HARBOR, True)
        self._harbor_house(45, 91, 25, 27, COLOR_WOOD_LIGHT, True)
        self._harbor_house(121, 95, 24, 22, COLOR_HARBOR)
        self._fill(213, 61, 60, 27, COLOR_WOOD_LIGHT)
        self._rect(213, 61, 60, 27, COLOR_INK)
        self._harbor_tower(276, 88, 15, 38, COLOR_HARBOR)
        flag_width = 7 + (self.phase & 1) * 3
        self._fill(284, 34, flag_width, 5, COLOR_RED_DARK)
        self._line(283, 34, 283, 51, COLOR_INK)
        self._line(90, 91, 122, 83, COLOR_WOOD_DARK)
        self._line(90, 95, 122, 87, COLOR_WOOD_DARK)
        self._line(174, 95, 207, 83, COLOR_WOOD_DARK)
        self._line(174, 99, 207, 87, COLOR_WOOD_DARK)

    def _draw_port_skyline(self, port):
        if port == 0:
            self._draw_lubeck_skyline()
        elif port == 1:
            self._draw_hamburg_skyline()
        elif port == 2:
            self._draw_bremen_skyline()
        elif port == 3:
            self._draw_rostock_skyline()
        elif port == 4:
            self._draw_danzig_skyline()
        elif port == 5:
            self._draw_riga_skyline()
        elif port == 6:
            self._draw_visby_skyline()
        else:
            self._draw_stockholm_skyline()

    def _draw_harbor(self, game):
        self._fill(8, 36, 304, 98, COLOR_SEA)
        self._rect(8, 36, 304, 98, COLOR_BRASS)
        self._fill(8, 36, 304, 34, COLOR_PARCHMENT_DARK)
        cloud_x = 206 + (self.phase * 3) % 22
        self._circle(cloud_x, 48, 7, COLOR_PARCHMENT, True)
        self._circle(cloud_x + 8, 46, 9, COLOR_PARCHMENT, True)
        self._circle(cloud_x + 17, 49, 6, COLOR_PARCHMENT, True)
        self._draw_port_skyline(game.current_port)
        if game.city_projects[game.current_port][PROJECT_COMPLETE]:
            crane_x = 190 + (game.current_port % 3) * 9
            self._line(crane_x, 101, crane_x, 73, COLOR_WOOD_DARK)
            self._line(crane_x, 73, crane_x + 27, 78, COLOR_WOOD_DARK)
            self._line(crane_x + 27, 78, crane_x + 27, 91 + (self.phase & 1) * 2, COLOR_INK)
        industry = sum(game.businesses[game.current_port])
        for index in range(min(3, industry)):
            chimney_x = 124 + index * 17
            self._fill(chimney_x, 83, 6, 18, COLOR_WOOD_DARK)
            smoke_y = 76 - ((self.phase + index) & 3) * 2
            self._circle(chimney_x + 3, smoke_y, 3 + (index & 1), TFT_LIGHTGREY, True)
        self._fill(8, 101, 304, 9, COLOR_WOOD_DARK)
        wave_shift = (self.phase * 7) % 26
        for x in range(-20 + wave_shift, 320, 52):
            self._line(x, 118, x + 18, 118, COLOR_SEA_LIGHT)
            self._line(x + 12, 127, x + 36, 127, COLOR_BLUE_INK)
        self._draw_ship(220, 94, 1, game.ship_types[game.active_ship])
        self._draw_weather(game, 38, 133)
        self._text(17, 43, PORT_NAMES[game.current_port], COLOR_INK, 2)
        self._fill(14, 63, 194, 13, COLOR_PARCHMENT_DARK)
        self._rect(14, 63, 194, 13, COLOR_WOOD_LIGHT)
        self._text(18, 66, PORT_MOTTO[game.current_port], COLOR_BLUE_INK, 0)

    def draw_port(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._header(PORT_NAMES[game.current_port] + " HARBOUR", game)
        self._draw_harbor_map(game)
        self._footer("MOVE  CENTER VISIT  B OTHER  S BOOK")
        self.draw.swap()

    def _draw_hub_building(self, index, x, y, selected):
        labels = ("HOUSE", "GUILD", "YARD", "MARKET", "TAVERN", "SAIL")
        if selected:
            glow = COLOR_GOLD if self.phase & 1 else COLOR_BRASS
            self._rect(x - 4, y - 5, 88, 51, glow)
            for px, py in ((x - 4, y - 5), (x + 84, y - 5), (x - 4, y + 46), (x + 84, y + 46)):
                self._circle(px, py, 2, glow, True)

        if index == 0:  # Counting house
            self._fill(x + 13, y + 10, 53, 26, COLOR_WOOD_LIGHT)
            self._rect(x + 13, y + 10, 53, 26, COLOR_INK)
            self._line(x + 13, y + 10, x + 39, y, COLOR_INK)
            self._line(x + 66, y + 10, x + 39, y, COLOR_INK)
            self._draw_shield(x + 30, y + 11, COLOR_RED_DARK, "H")
        elif index == 1:  # Guild hall
            self._fill(x + 10, y + 13, 58, 23, COLOR_HARBOR)
            self._rect(x + 10, y + 13, 58, 23, COLOR_INK)
            self._harbor_tower(x + 31, y + 36, 17, 34, COLOR_WOOD_LIGHT)
            self._draw_shield(x + 29, y + 17, COLOR_RED_DARK, "G")
        elif index == 2:  # Shipyard
            for frame_x in (x + 12, x + 58):
                self._line(frame_x, y + 35, frame_x, y + 3, COLOR_WOOD_DARK)
                self._line(frame_x, y + 3, frame_x + 16, y + 35, COLOR_WOOD_DARK)
            self._fill(x + 18, y + 25, 45, 7, COLOR_WOOD_DARK)
            self._line(x + 18, y + 32, x + 28, y + 37, COLOR_INK)
            self._line(x + 63, y + 32, x + 53, y + 37, COLOR_INK)
        elif index == 3:  # Market square
            for stall in range(3):
                stall_x = x + 7 + stall * 24
                self._fill(stall_x, y + 12, 20, 20, COLOR_PARCHMENT_DARK)
                self._fill(stall_x, y + 7, 20, 7, COLOR_RED_DARK if stall & 1 else COLOR_GOLD)
                self._line(stall_x, y + 14, stall_x, y + 34, COLOR_INK)
                self._line(stall_x + 20, y + 14, stall_x + 20, y + 34, COLOR_INK)
        elif index == 4:  # Tavern
            self._fill(x + 14, y + 11, 51, 25, COLOR_HARBOR)
            self._rect(x + 14, y + 11, 51, 25, COLOR_INK)
            self._line(x + 14, y + 11, x + 39, y + 1, COLOR_INK)
            self._line(x + 65, y + 11, x + 39, y + 1, COLOR_INK)
            self._circle(x + 59, y + 18, 5, COLOR_GOLD, True)
            self._text(x + 57, y + 15, "R", COLOR_INK, 0)
        else:  # Harbour gate and quay
            self._fill(x + 8, y + 7, 17, 29, COLOR_WOOD_LIGHT)
            self._fill(x + 55, y + 7, 17, 29, COLOR_WOOD_LIGHT)
            self._rect(x + 8, y + 7, 17, 29, COLOR_INK)
            self._rect(x + 55, y + 7, 17, 29, COLOR_INK)
            self._line(x + 8, y + 7, x + 16, y, COLOR_INK)
            self._line(x + 25, y + 7, x + 16, y, COLOR_INK)
            self._line(x + 55, y + 7, x + 63, y, COLOR_INK)
            self._line(x + 72, y + 7, x + 63, y, COLOR_INK)
            self._line(x + 25, y + 19, x + 55, y + 19, COLOR_WOOD_DARK)

        plaque = COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK
        self._fill(x + 8, y + 38, 64, 12, plaque)
        self._rect(x + 8, y + 38, 64, 12, COLOR_BRASS)
        self._center_at(labels[index], x + 40, y + 41, COLOR_GOLD if selected else COLOR_INK)

    def _center_at(self, text, center_x, y, color=COLOR_INK, font=0):
        width = self.draw.len(str(text), font)
        self.draw._text(self._x(center_x) - width // 2, self._y(y), str(text), color, font)

    def _draw_harbor_map(self, game):
        """Interactive city view: buildings are the harbour's main menu."""
        self._fill(8, 34, 304, 265, COLOR_PARCHMENT_DARK)
        self._rect(8, 34, 304, 265, COLOR_BRASS)
        self._fill(9, 35, 302, 66, COLOR_PARCHMENT_DARK)
        cloud_x = 204 + (self.phase * 3) % 28
        self._circle(cloud_x, 48, 7, COLOR_PARCHMENT, True)
        self._circle(cloud_x + 9, 46, 9, COLOR_PARCHMENT, True)
        self._circle(cloud_x + 18, 49, 6, COLOR_PARCHMENT, True)
        self._draw_port_skyline(game.current_port)
        if game.city_projects[game.current_port][PROJECT_COMPLETE]:
            self._fill(183, 88, 54, 8, COLOR_WOOD_DARK)
            self._line(190, 88, 190, 63, COLOR_WOOD_DARK)
            self._line(190, 63, 218, 69, COLOR_WOOD_DARK)
            self._fill(218, 69, 5 + (self.phase & 1) * 3, 4, COLOR_RED_DARK)
        industry = sum(game.businesses[game.current_port])
        for index in range(min(3, industry)):
            chimney_x = 145 + index * 15
            self._fill(chimney_x, 84, 6, 17, COLOR_WOOD_DARK)
            self._circle(chimney_x + 3, 77 - ((self.phase + index) & 3), 3, TFT_LIGHTGREY, True)
        self._draw_weather(game, 36, 101)

        # Cobble streets lead from the old town to the working waterfront.
        self._fill(9, 102, 302, 120, COLOR_LAND_LIGHT)
        self._line(10, 158, 310, 166, COLOR_WOOD_LIGHT)
        self._line(108, 102, 101, 222, COLOR_WOOD_LIGHT)
        self._line(210, 102, 217, 222, COLOR_WOOD_LIGHT)
        for x in range(18, 310, 28):
            self._line(x, 216, x + 16, 209, COLOR_PARCHMENT_DARK)

        # Water and a wooden landing stage anchor the view as a harbour.
        self._fill(9, 222, 302, 41, COLOR_SEA)
        wave_shift = (self.phase * 7) % 24
        for x in range(-12 + wave_shift, 320, 48):
            self._line(x, 234, x + 18, 234, COLOR_SEA_LIGHT)
            self._line(x + 9, 254, x + 31, 254, COLOR_BLUE_INK)
        self._fill(220, 204, 74, 9, COLOR_WOOD_DARK)
        self._fill(253, 204, 8, 34, COLOR_WOOD_DARK)
        self._draw_ship(258, 214, 1, game.ship_types[game.active_ship])
        if game.weather == WEATHER_ICE:
            self._draw_weather(game, 222, 263)

        positions = ((16, 108), (118, 101), (220, 109), (16, 166), (118, 172), (220, 164))
        for index in range(len(positions)):
            point = positions[index]
            self._draw_hub_building(index, point[0], point[1], index == game.menu_selection)

        # A cart and townsman move subtly while the player is idle.
        cart_x = 76 + (self.phase * 5) % 28
        self._fill(cart_x, 153, 12, 6, COLOR_WOOD)
        self._circle(cart_x + 2, 160, 2, COLOR_INK, True)
        self._circle(cart_x + 10, 160, 2, COLOR_INK, True)
        walker_x = 177 + (self.phase * 3) % 18
        self._circle(walker_x, 157, 2, COLOR_RED_DARK, True)
        self._line(walker_x, 159, walker_x, 166, COLOR_INK)

        selected = game.menu_selection
        self._fill(9, 264, 302, 34, COLOR_WOOD_DARK)
        self._line(9, 264, 311, 264, COLOR_BRASS)
        self._text(17, 269, HARBOR_LOCATIONS[selected], COLOR_GOLD, 1)
        self._text(17, 286, "CENTER " + HARBOR_PRIMARY[selected], COLOR_PARCHMENT, 0)
        alternate = "B " + HARBOR_SECONDARY[selected]
        width = self.draw.len(alternate, 0)
        self.draw._text(self.width - self._x(17) - width, self._y(286), alternate, COLOR_SEA_LIGHT, 0)

    def draw_overview(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("HOUSE OVERVIEW", game)
        needs = game.city_needs(game.current_port, 2)
        cards = (
            ("COMMAND", game.ship_order_label(game.active_ship), "C"),
            ("OBJECTIVE", game.objective_text(), "O"),
            ("CITY NEEDS", "%s %s  %s %s" % (
                GOOD_NAMES[needs[0]], game.city_need_level(game.current_port, needs[0]),
                GOOD_NAMES[needs[1]], game.city_need_level(game.current_port, needs[1]),
            ), "N"),
            ("RECENT EVENTS", game.recent_log[-1] if game.recent_log else "NO NEWS", "!"),
        )
        for index in range(4):
            y = 39 + index * 62
            selected = index == game.overview_selection
            fill = COLOR_WOOD_DARK if selected else COLOR_PARCHMENT
            self._fill(17, y, 286, 55, fill)
            self._rect(17, y, 286, 55, COLOR_GOLD if selected else COLOR_BRASS)
            self._draw_shield(27, y + 11, COLOR_RED_DARK if index != 2 else COLOR_GREEN_DARK, cards[index][2])
            color = COLOR_GOLD if selected else COLOR_RED_DARK
            self._text(58, y + 7, ("> " if selected else "  ") + cards[index][0], color, 1)
            lines = self._wrap(cards[index][1], 36)
            for line_index in range(min(2, len(lines))):
                self._text(59, y + 29 + line_index * 13, lines[line_index], COLOR_PARCHMENT if selected else COLOR_INK, 0)
            if index == 0:
                ordered, total = game.order_progress()
                self._fill(239, y + 12, 48, 7, COLOR_PARCHMENT_DARK)
                self._fill(239, y + 12, 48 * ordered // max(1, total), 7, COLOR_GREEN_DARK)
                self._rect(239, y + 12, 48, 7, COLOR_BRASS)
        self._footer("ARROWS CHOOSE CENTER OPEN  B BANK")
        self.draw.swap()

    def draw_bank(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._header("MERCHANT BANK", game)
        self._panel(20, 42, 280, 242)
        self._draw_shield(142, 55, COLOR_BLUE_INK, "B")
        self._center("CREDIT OF THE GUILD", 92, COLOR_RED_DARK, 1)
        self._center("CASH %dS   DEBT %dS" % (game.cash, game.loan), 116, COLOR_BLUE_INK, 0)
        names = ("BORROW 250S", "REPAY UP TO 250S", "FLEET INSURANCE", "DECLARE INSOLVENCY")
        details = (
            "LIMIT 2000S - INTEREST EACH 30 DAYS",
            "DEBT IS DEDUCTED FROM HOUSE WEALTH",
            "ON - 1S DAILY" if game.insured else "OFF - REDUCES MAJOR LOSSES",
            "MAX DEBT + LOW CASH - RESETS THE HOUSE",
        )
        for index in range(4):
            y = 127 + index * 36
            selected = index == game.bank_selection
            self._fill(37, y, 246, 31, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(37, y, 246, 31, COLOR_GOLD if selected else COLOR_BRASS)
            self._text(48, y + 4, ("> " if selected else "  ") + names[index],
                       COLOR_GOLD if selected else COLOR_RED_DARK, 0)
            self._text(50, y + 17, details[index][:37],
                       COLOR_PARCHMENT if selected else COLOR_INK, 0)
        self._footer("UP/DOWN CHOOSE CENTER ACT  BACK")
        self.draw.swap()

    def draw_city(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("CITY INFORMATION", game)
        self._draw_harbor(game)
        self._panel(14, 142, 292, 144)
        port = game.current_port
        prosperity = game.city_prosperity[port]
        condition_color = COLOR_GREEN_DARK if prosperity >= 65 else COLOR_RED_DARK if prosperity < 45 else COLOR_BLUE_INK
        self._text(27, 151, "CITY %s  %d/100" % (game.city_condition(port), prosperity), condition_color, 1)
        self._fill(27, 169, 266, 7, COLOR_WOOD_DARK)
        self._fill(27, 169, 266 * prosperity // 100, 7, condition_color)
        project = game.city_projects[port]
        self._text(27, 184, CITY_PROJECT_NAMES[port], COLOR_RED_DARK, 1)
        if project[PROJECT_COMPLETE]:
            self._text(206, 187, "BUILT", COLOR_GREEN_DARK, 0)
            self._text(27, 207, "PERMANENT QUAY IMPROVEMENT", COLOR_BLUE_INK, 0)
        else:
            self._text(221, 187, "D%d" % project[PROJECT_DEADLINE], COLOR_BLUE_INK, 0)
            self._draw_good_icon(27, 202, project[PROJECT_GOOD_A])
            self._text(53, 209, "%s %d/%d" % (
                GOOD_NAMES[project[PROJECT_GOOD_A]], project[PROJECT_HAVE_A], project[PROJECT_NEED_A],
            ), COLOR_INK, 0)
            self._draw_good_icon(165, 202, project[PROJECT_GOOD_B])
            self._text(191, 209, "%s %d/%d" % (
                GOOD_NAMES[project[PROJECT_GOOD_B]], project[PROJECT_HAVE_B], project[PROJECT_NEED_B],
            ), COLOR_INK, 0)
        needs = game.city_needs(port, 2)
        self._text(27, 236, "NEEDS", COLOR_RED_DARK, 0)
        self._text(70, 236, "%s %s / %s %s" % (
            GOOD_NAMES[needs[0]], game.city_need_level(port, needs[0]),
            GOOD_NAMES[needs[1]], game.city_need_level(port, needs[1]),
        ), COLOR_INK, 0)
        self._text(27, 254, "%s - %s / %s" % (
            game.season_name, game.weather_name, game.city_event_text(port),
        )[:43], COLOR_BLUE_INK, 0)
        self._fill(27, 269, 266, 11, COLOR_WOOD_DARK)
        action = "PROJECT COMPLETE" if project[PROJECT_COMPLETE] else "B DONATE CARGO  CENTER RETURN"
        self._center(action, 271, COLOR_GOLD, 0)
        self._footer(game.status)
        self.draw.swap()

    def draw_log(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._header("RECENT EVENTS", game)
        self._panel(19, 39, 282, 246)
        self._fill(31, 51, 258, 15, COLOR_WOOD_LIGHT)
        self._circle(37, 58, 7, COLOR_BRASS, True)
        self._circle(283, 58, 7, COLOR_BRASS, True)
        self._center("HOUSE CHRONICLE", 77, COLOR_RED_DARK, 1)
        items = game.recent_log
        visible = min(8, len(items))
        for row in range(visible):
            text = items[len(items) - 1 - row]
            y = 105 + row * 21
            if row % 2:
                self._fill(31, y - 4, 258, 19, COLOR_PARCHMENT_DARK)
            self._circle(40, y + 3, 2, COLOR_BRASS, True)
            self._text(49, y, text[:39], COLOR_INK, 0)
        self._fill(31, 268, 258, 10, COLOR_WOOD_LIGHT)
        self._footer("NEWEST FIRST  CENTER/BACK HARBOUR")
        self.draw.swap()

    def draw_adviser(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._header("GUILD ADVISER", game)
        self._panel(20, 40, 280, 244)
        self._draw_tavern_candles()
        self._draw_shield(142, 58, COLOR_RED_DARK, "?")
        self._center("A WORD FROM THE FACTOR", 93, COLOR_RED_DARK, 1)
        self._fill(37, 122, 246, 86, COLOR_PARCHMENT_DARK)
        self._rect(37, 122, 246, 86, COLOR_BRASS)
        lines = self._wrap(game.advice(), 31)
        for index in range(min(4, len(lines))):
            self._center(lines[index], 139 + index * 18, COLOR_INK, 0)
        self._text(39, 225, "CURRENT OBJECTIVE", COLOR_BLUE_INK, 0)
        objective = self._wrap(game.objective_text(), 36)
        for index in range(min(2, len(objective))):
            self._text(39, 242 + index * 15, objective[index], COLOR_RED_DARK, 0)
        self._footer("CENTER/BACK HARBOUR  B COUNCIL")
        self.draw.swap()

    def draw_council(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._header("CITY COUNCIL", game)
        self._panel(17, 40, 286, 246)
        self._draw_shield(142, 52, COLOR_RED_DARK, "C")
        self._center(COUNCIL_ISSUES[game.council_issue], 88, COLOR_RED_DARK, 2)
        self._center("ELECTION SUPPORT %d/100" % game.council_favor,
                     109, COLOR_BLUE_INK, 0)
        self._center(game.council_status()[:38], 124, COLOR_BLUE_INK, 0)
        options = COUNCIL_OPTIONS[game.council_issue]
        costs = ("120S - HIGH SUPPORT", "45S - MODEST SUPPORT", "0S - SUPPORT FALLS")
        for index in range(3):
            y = 145 + index * 40
            selected = index == game.council_selection
            self._fill(35, y, 250, 33, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(35, y, 250, 33, COLOR_GOLD if selected else COLOR_BRASS)
            self._text(47, y + 5, ("> " if selected else "  ") + options[index],
                       COLOR_GOLD if selected else COLOR_RED_DARK, 0)
            self._text(49, y + 18, costs[index], COLOR_PARCHMENT if selected else COLOR_INK, 0)
        self._footer("UP/DOWN CHOOSE CENTER VOTE  BACK")
        self.draw.swap()

    def draw_market(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("MARKET - " + PORT_NAMES[game.current_port], game)
        self._panel(8, 36, 304, 251)
        self._text(19, 45, "WARE", COLOR_BLUE_INK, 0)
        self._text(143, 45, "BUY", COLOR_BLUE_INK, 0)
        self._text(193, 45, "SELL", COLOR_BLUE_INK, 0)
        self._text(225, 45, "NEED", COLOR_BLUE_INK, 0)
        self._text(270, 45, "HOLD", COLOR_BLUE_INK, 0)
        self._line(17, 57, 303, 57, COLOR_WOOD_LIGHT)
        for index in range(len(GOOD_NAMES)):
            self._draw_market_row(game, index)
        self._text(19, 273, "LEFT SELL  RIGHT BUY  B/S x5", COLOR_BLUE_INK, 0)
        self._footer("HOLD %d/%d  %s" % (game.cargo_used, game.capacity, game.status))
        self.draw.swap()

    def _draw_map_chart(self, game):
        self._fill(8, 36, 205, 251, COLOR_SEA_DARK)
        self._rect(8, 36, 205, 251, COLOR_BRASS)
        for y in (74, 112, 150, 188, 226, 264):
            self._line(9, y, 212, y, COLOR_SEA)
        for x in (48, 88, 128, 168, 208):
            self._line(x, 37, x, 286, COLOR_SEA)
        # Abstract coastlines, intentionally original rather than traced.
        self._fill(9, 37, 31, 149, COLOR_LAND)
        self._fill(9, 242, 76, 44, COLOR_LAND)
        self._fill(184, 37, 28, 77, COLOR_LAND)
        self._line(40, 186, 64, 206, COLOR_LAND_LIGHT)
        self._line(64, 206, 85, 246, COLOR_LAND_LIGHT)
        self._line(184, 114, 172, 146, COLOR_LAND_LIGHT)
        self._line(172, 146, 179, 176, COLOR_LAND_LIGHT)

        # Standing routes remain visible while the player commands another cog.
        for ship_index in range(len(game.ships)):
            route = game.ship_routes[ship_index]
            ports = route[ROUTE_PORTS]
            if route[ROUTE_STATE] != ROUTE_RUNNING or len(ports) < 2:
                continue
            for stop in range(len(ports)):
                route_start = PORT_POSITIONS[ports[stop]]
                route_end = PORT_POSITIONS[ports[(stop + 1) % len(ports)]]
                self._line(route_start[0], route_start[1], route_end[0], route_end[1], COLOR_SEA_LIGHT)
            route_ship = game.ships[ship_index]
            if route_ship[SHIP_ORDER] == ORDER_SAIL:
                route_start = PORT_POSITIONS[route_ship[SHIP_PORT]]
                route_end = PORT_POSITIONS[route_ship[SHIP_DEST]]
                route_phase = (self.phase + ship_index * 2) & 7
                route_x = route_start[0] + (route_end[0] - route_start[0]) * (route_phase + 1) // 9
                route_y = route_start[1] + (route_end[1] - route_start[1]) * (route_phase + 1) // 9
                self._circle(route_x, route_y, 3, COLOR_SEA_LIGHT, True)
                self._line(route_x - 3, route_y + 3, route_x + 3, route_y + 3, TFT_WHITE)

        # Rival houses travel on persistent red lanes rather than teleporting.
        for rival_index in range(len(game.rival_routes)):
            rival_route = game.rival_routes[rival_index]
            rival_start = PORT_POSITIONS[rival_route[0]]
            rival_end = PORT_POSITIONS[rival_route[1]]
            self._line(rival_start[0], rival_start[1], rival_end[0], rival_end[1], COLOR_RED_DARK)
            rival_phase = (self.phase + rival_index * 2) & 7
            rival_x = rival_start[0] + (rival_end[0] - rival_start[0]) * (rival_phase + 1) // 9
            rival_y = rival_start[1] + (rival_end[1] - rival_start[1]) * (rival_phase + 1) // 9
            self._circle(rival_x, rival_y, 3, COLOR_RED_DARK, True)
            self._line(rival_x, rival_y - 5, rival_x, rival_y + 3, TFT_WHITE)

        start = PORT_POSITIONS[game.current_port]
        selected = PORT_POSITIONS[game.map_selection]
        self._line(start[0], start[1], selected[0], selected[1], COLOR_GOLD)
        progress = self.phase + 1
        ship_x = start[0] + (selected[0] - start[0]) * progress // 9
        ship_y = start[1] + (selected[1] - start[1]) * progress // 9
        self._circle(ship_x, ship_y, 3, TFT_WHITE, True)
        self._line(ship_x - 4, ship_y + 3, ship_x + 4, ship_y + 3, COLOR_BLUE_INK)
        for index in range(len(PORT_NAMES)):
            point = PORT_POSITIONS[index]
            if index == game.current_port:
                color = TFT_GREEN
                radius = 5
            elif index == game.map_selection:
                color = COLOR_GOLD
                radius = 5 + (1 if self.phase in (1, 2, 5, 6) else 0)
            elif any(
                route[ROUTE_STATE] == ROUTE_RUNNING and index in route[ROUTE_PORTS]
                for route in game.ship_routes
            ):
                color = COLOR_SEA_LIGHT
                radius = 4
            else:
                color = COLOR_PARCHMENT
                radius = 3
            self._circle(point[0], point[1], radius, color, True)
            self._circle(point[0], point[1], radius + 1, COLOR_INK, False)
        for index in range(len(game.active_contracts)):
            contract = game.active_contracts[index]
            point = PORT_POSITIONS[contract[CONTRACT_DEST]]
            self._fill(point[0] + 5, point[1] - 8, 5, 5, COLOR_RED_DARK)
            if index == game.pinned_contract:
                self._circle(point[0], point[1], 9 + (self.phase & 1), COLOR_RED_DARK, False)
        self._draw_weather(game, 37, 286)

    def draw_map(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("SEA CHART", game)
        self._draw_map_chart(game)
        self._panel(218, 36, 94, 251)
        self._text(227, 48, "DESTINATION", COLOR_BLUE_INK, 0)
        name = PORT_NAMES[game.map_selection]
        self._text(227, 67, name[:11], COLOR_RED_DARK, 1 if len(name) < 9 else 0)
        self._text(227, 101, "SAILING", COLOR_BLUE_INK, 0)
        self._text(227, 117, "%d DAYS" % game.route_days(game.map_selection), COLOR_INK, 1)
        self._text(227, 137, game.season_name, COLOR_RED_DARK, 0)
        self._text(227, 150, game.weather_name, COLOR_BLUE_INK, 0)
        self._text(227, 169, "CREW COST", COLOR_BLUE_INK, 0)
        self._text(227, 184, "%d SILVER" % (game.route_days(game.map_selection) * 3), COLOR_INK, 0)
        slack = game.contract_slack(game.map_selection)
        if slack is None:
            self._text(227, 202, "GREEN HOME", COLOR_GREEN_DARK, 0)
            self._text(227, 215, "GOLD TARGET", COLOR_RED_DARK, 0)
            self._text(227, 228, "CYAN AUTO", COLOR_SEA_LIGHT, 0)
            self._text(227, 241, "RED RIVALS", COLOR_RED_DARK, 0)
        else:
            self._text(227, 198, "CONTRACT ETA", COLOR_BLUE_INK, 0)
            self._text(227, 214, "%+d DAYS" % slack, COLOR_RED_DARK if slack < 2 else COLOR_GREEN_DARK, 1)
            self._text(227, 233, "AFTER ARRIVAL", COLOR_BLUE_INK, 0)
        self._text(227, 254, "CENTER", COLOR_BLUE_INK, 0)
        self._text(227, 268, "SET SAIL", COLOR_RED_DARK, 0)
        self._footer("ARROWS CHOOSE PORT  BACK CANCEL")
        self.draw.swap()

    def _draw_route_chart(self, game):
        route = game.ship_routes[game.route_ship]
        ship = game.ships[game.route_ship]
        self._fill(8, 36, 205, 251, COLOR_SEA_DARK)
        self._rect(8, 36, 205, 251, COLOR_BRASS)
        for y in (74, 112, 150, 188, 226, 264):
            self._line(9, y, 212, y, COLOR_SEA)
        for x in (48, 88, 128, 168, 208):
            self._line(x, 37, x, 286, COLOR_SEA)
        self._fill(9, 37, 31, 149, COLOR_LAND)
        self._fill(9, 242, 76, 44, COLOR_LAND)
        self._fill(184, 37, 28, 77, COLOR_LAND)
        self._line(40, 186, 64, 206, COLOR_LAND_LIGHT)
        self._line(64, 206, 85, 246, COLOR_LAND_LIGHT)
        self._line(184, 114, 172, 146, COLOR_LAND_LIGHT)
        self._line(172, 146, 179, 176, COLOR_LAND_LIGHT)

        ports = route[ROUTE_PORTS]
        if len(ports) > 1:
            for index in range(len(ports)):
                start = PORT_POSITIONS[ports[index]]
                end = PORT_POSITIONS[ports[(index + 1) % len(ports)]]
                self._line(start[0], start[1], end[0], end[1], COLOR_GOLD)

        for index in range(len(PORT_NAMES)):
            point = PORT_POSITIONS[index]
            if index == game.map_selection:
                color = COLOR_GOLD
                radius = 6 if self.phase & 1 else 5
            elif index == ship[SHIP_PORT]:
                color = COLOR_GREEN_DARK
                radius = 5
            elif index in ports:
                color = COLOR_RED_DARK
                radius = 5
            else:
                color = COLOR_PARCHMENT
                radius = 3
            self._circle(point[0], point[1], radius, color, True)
            self._circle(point[0], point[1], radius + 1, COLOR_INK, False)
            if index in ports:
                self._text(point[0] - 2, point[1] - 3, ports.index(index) + 1, TFT_WHITE, 0)

        if ship[SHIP_ORDER] == ORDER_SAIL:
            start = PORT_POSITIONS[ship[SHIP_PORT]]
            end = PORT_POSITIONS[ship[SHIP_DEST]]
            progress = self.phase + 1
            ship_x = start[0] + (end[0] - start[0]) * progress // 9
            ship_y = start[1] + (end[1] - start[1]) * progress // 9
            self._circle(ship_x, ship_y, 3, TFT_WHITE, True)
            self._line(ship_x - 4, ship_y + 3, ship_x + 4, ship_y + 3, COLOR_BLUE_INK)

    def draw_route(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("CAPTAIN ROUTE", game)
        self._draw_route_chart(game)
        route = game.ship_routes[game.route_ship]
        ship = game.ships[game.route_ship]
        self._panel(218, 36, 94, 251)
        self._text(226, 47, SHIP_NAMES[ship[SHIP_NAME]][:11], COLOR_RED_DARK, 1)
        self._text(226, 65, SHIP_TYPE_NAMES[game.ship_types[game.route_ship]], COLOR_BLUE_INK, 0)
        self._text(226, 77, "C %s L%d" % (
            CAPTAIN_NAMES[ship[SHIP_CAPTAIN]], game.captain_level(game.route_ship),
        ), COLOR_BLUE_INK, 0)
        state = game.route_status(game.route_ship)
        state_color = (
            COLOR_GREEN_DARK if route[ROUTE_STATE] == ROUTE_RUNNING
            else COLOR_RED_DARK if route[ROUTE_STATE] == ROUTE_ATTENTION
            else COLOR_GOLD if route[ROUTE_STATE] == ROUTE_PAUSED
            else COLOR_BLUE_INK
        )
        self._text(226, 90, state, state_color, 0)
        self._text(226, 102, str(route[ROUTE_NOTE])[:13], COLOR_INK, 0)
        self._text(226, 114, "STOPS", COLOR_BLUE_INK, 0)
        for index in range(4):
            y = 127 + index * 16
            if index < len(route[ROUTE_PORTS]):
                name = PORT_NAMES[route[ROUTE_PORTS][index]][:9]
                self._text(226, y, "%d %s" % (index + 1, name), COLOR_INK, 0)
            else:
                self._text(226, y, "%d ---" % (index + 1), COLOR_WOOD_LIGHT, 0)
        self._text(226, 194, "RES %dS" % route[ROUTE_RESERVE], COLOR_BLUE_INK, 0)
        self._text(226, 209, "FIX <%d%%" % route[ROUTE_REPAIR], COLOR_BLUE_INK, 0)
        ledger = game.route_ledgers[game.route_ship]
        net = ledger[LEDGER_REVENUE] - ledger[LEDGER_COST]
        self._text(226, 223, "R%d C%d" % (
            ledger[LEDGER_REVENUE], ledger[LEDGER_COST],
        ), COLOR_BLUE_INK, 0)
        self._text(226, 236, "NET %+d V%d" % (net, ledger[LEDGER_VISITS]), COLOR_RED_DARK, 0)
        self._text(226, 249, "%s %+d" % (
            PORT_NAMES[game.map_selection][:7], ledger[LEDGER_PORTS][game.map_selection],
        ), COLOR_BLUE_INK, 0)
        if game.map_selection in route[ROUTE_PORTS]:
            stop_index = route[ROUTE_PORTS].index(game.map_selection)
            goods = route[ROUTE_RULES][stop_index]
        else:
            goods = game._default_route_goods(game.map_selection)
        self._text(226, 263, "AUTO LOAD", COLOR_BLUE_INK, 0)
        self._text(226, 276, "/".join(GOOD_NAMES[good][:3] for good in goods), COLOR_INK, 0)
        self._footer("L/R CITY OK STOP B GOODS U$ D% S RUN")
        self.draw.swap()

    def draw_wait(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("HARBOUR ORDERS", game)
        self._draw_harbor(game)
        self._panel(28, 148, 264, 137)
        self._center("KEEP %s IN PORT" % game.ship_name, 163, COLOR_RED_DARK, 1)
        self._center("UNTIL DAY %d" % (game.day + game.wait_days), 190, COLOR_BLUE_INK, 0)
        self._center("<   %d DAY%s   >" % (
            game.wait_days, "" if game.wait_days == 1 else "S",
        ), 211, COLOR_RED_DARK, 2)
        urgent = game.urgent_contract_index()
        if urgent >= 0:
            deadline = game.active_contracts[urgent][CONTRACT_DEADLINE]
            margin = deadline - game.day - game.wait_days
            preview = "DEADLINE MARGIN %+d DAYS" % margin
            color = COLOR_RED_DARK if margin < 2 else COLOR_GREEN_DARK
        else:
            preview = "NO CONTRACT DEADLINE AT RISK"
            color = COLOR_BLUE_INK
        self._center(preview, 242, color, 0)
        self._center("CENTER SEALS THE ORDER", 263, COLOR_INK, 0)
        self._footer("LEFT/RIGHT 1-7 DAYS  BACK CANCEL")
        self.draw.swap()

    def draw_cargo(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("CARGO MANIFEST", game)
        self._panel(13, 39, 294, 246)
        self._text(27, 50, "SEAL", COLOR_BLUE_INK, 0)
        self._text(69, 50, "WARE", COLOR_BLUE_INK, 0)
        self._text(213, 50, "CRATES", COLOR_BLUE_INK, 0)
        self._line(23, 63, 297, 63, COLOR_WOOD_LIGHT)
        for index in range(len(GOOD_NAMES)):
            y = 70 + index * 24
            self._draw_good_icon(27, y + 1, index)
            self._text(69, y + 7, GOOD_NAMES[index], COLOR_INK, 0)
            self._text(238, y + 7, game.cargo[index], COLOR_INK, 0)
        self._text(27, 267, "TOTAL %d   FREE %d" % (game.cargo_used, game.cargo_free), COLOR_RED_DARK, 0)
        self._footer("BACK TO RETURN TO PORT")
        self.draw.swap()

    def draw_shipyard(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("MASTER SHIPWRIGHT", game)
        self._panel(18, 42, 284, 235)
        self._draw_ship(52, 76, 2, game.ship_types[game.active_ship])
        self._text(34, 156, "HULL", COLOR_BLUE_INK, 0)
        self._fill(82, 154, 190, 13, COLOR_WOOD_DARK)
        self._fill(84, 156, 186 * game.hull // 100, 9, COLOR_GREEN_DARK if game.hull > 35 else COLOR_RED_DARK)
        self._text(277, 156, "%d" % game.hull, COLOR_INK, 0)
        repair_cost = min(10, 100 - game.hull) * 3
        expand_cost = 180 + (game.capacity - 30) * 12
        options = (
            "REPAIR 10%%  %dS" % repair_cost,
            "EXPAND HOLD +5  %dS" % expand_cost,
        )
        for index in range(2):
            y = 190 + index * 38
            selected = index == game.shipyard_selection
            self._fill(34, y, 252, 29, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(34, y, 252, 29, COLOR_BRASS)
            self._text(46, y + 10, ("> " if selected else "  ") + options[index], COLOR_GOLD if selected else COLOR_INK, 0)
        self._footer(game.status)
        self.draw.swap()

    def draw_ledger(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("GUILD LEDGER", game)
        self._panel(26, 42, 268, 241)
        if game.game_mode == MODE_CAREER:
            if game.rank == 0:
                vote = "COUNCIL"
            elif game.rank == 1:
                vote = "MAYOR D%d" % game.next_mayor_election()
            elif game.rank == 2:
                vote = "HANSE D%d" % game.next_hanse_election()
            else:
                vote = "VICTORY"
            rows = (
                ("CURRENT PORT", PORT_NAMES[game.current_port]),
                ("RANK", game.rank_name),
                ("NEXT STEP", vote),
                ("SILVER", str(game.cash)),
                ("EST. WEALTH", str(game.wealth())),
                ("DAY", str(game.day)),
                ("REPUTATION", str(game.reputation)),
                ("FLEET / OFFICES", "%d / %d" % (len(game.ships), sum(game.offices))),
                ("HULL", "%d%%" % game.hull),
                ("CARGO", "%d / %d" % (game.cargo_used, game.capacity)),
            )
        else:
            rows = (
                ("CURRENT PORT", PORT_NAMES[game.current_port]),
                ("SILVER", str(game.cash)),
                ("EST. WEALTH", str(game.wealth())),
                ("GOAL", str(WEALTH_GOAL)),
                ("DAY", "%d / %d" % (game.day, CAMPAIGN_DAYS)),
                ("VOYAGES", str(game.voyages)),
                ("REPUTATION", str(game.reputation)),
                ("FLEET / OFFICES", "%d / %d" % (len(game.ships), sum(game.offices))),
                ("HULL", "%d%%" % game.hull),
                ("CARGO", "%d / %d" % (game.cargo_used, game.capacity)),
            )
        for index in range(len(rows)):
            y = 50 + index * 21
            if index % 2:
                self._fill(36, y - 3, 248, 20, COLOR_PARCHMENT_DARK)
            self._text(42, y, rows[index][0], COLOR_BLUE_INK, 0)
            value = rows[index][1]
            width = self.draw.len(value, 0)
            self.draw._text(self.width - self._x(43) - width, self._y(y), value, COLOR_RED_DARK, 0)
        self._footer(
            "WIN THE HANSEATIC ELECTION"
            if game.game_mode == MODE_CAREER
            else "BUILD WEALTH BEFORE DAY %d" % CAMPAIGN_DAYS
        )
        self.draw.swap()

    def draw_help(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("CAPTAIN'S HANDBOOK", game)
        self._panel(18, 40, 284, 245)
        if game.help_page == 0:
            title = "TRADE"
            lines = (
                "HARBOUR BUILDINGS ARE YOUR MENU.",
                "ARROWS MOVE; CENTER VISITS.",
                "B OPENS THE SECOND SERVICE.",
                "S SAVES THE CURRENT OF THREE LEDGERS.",
                "MARKET: LEFT SELLS, RIGHT BUYS.",
                "B AND S TRADE FIVE CRATES.",
                "MARKET NEED: U/H/M/L.",
            )
        elif game.help_page == 1:
            title = "VOYAGE"
            lines = (
                "GIVE EVERY READY SHIP AN ORDER.",
                "SET SAIL OR WAIT ONE TO SEVEN DAYS.",
                "TIME JUMPS TO THE NEXT ARRIVAL.",
                "THE GUILD SCROLL REPORTS THE ROUND.",
                "CREW AND OFFICE COSTS ARE LISTED.",
                "STORMS AND PIRATES MAY STRIKE.",
            )
        elif game.help_page == 2:
            title = "GUILD"
            lines = (
                "ACCEPT UP TO THREE CONTRACTS.",
                "ON ACTIVE TAB, B PINS A GOAL.",
                "LOAD THE NAMED GOODS YOURSELF.",
                "DELIVER BEFORE THE DEADLINE.",
                "RED MAP MARKS SHOW DESTINATIONS.",
                "OFFICES UNLOCK LOCAL STORAGE.",
                "RECENT EVENTS RETAINS YOUR TRAIL.",
            )
        elif game.help_page == 3:
            title = "FLEET"
            lines = (
                "OWN UP TO THREE TRADING COGS.",
                "FLEET: B OPENS CAPTAIN ROUTES.",
                "ADD TWO TO FOUR PORTS.",
                "S STARTS OR PAUSES THE ROUTE.",
                "B CHANGES THREE GOODS PER STOP.",
                "UP SETS RESERVE; DOWN REPAIRS.",
                "KEEP ONE READY SHIP MANUAL.",
            )
        elif game.help_page == 4:
            title = "ECONOMY"
            lines = (
                "OFFICE: B OPENS CITY WORKSHOPS.",
                "BUILD THREE INDUSTRY TYPES PER CITY.",
                "OUTPUT ENTERS THE LOCAL WAREHOUSE.",
                "BREWERIES AND IRON WORKS USE INPUTS.",
                "ROUTE BOOKS SHOW REVENUE AND COSTS.",
                "OVERVIEW: B OPENS BANK AND INSURANCE.",
                "GUILD: S HANDLES STORY MISSIONS.",
            )
        else:
            title = "POLITICS"
            lines = (
                "CAREER MODE ENDS AS ALDERMAN.",
                "COUNCIL: %d REP, %d WEALTH, OFFICE." % (
                    COUNCILLOR_REPUTATION, COUNCILLOR_WEALTH,
                ),
                "MAYOR: %d REP, %d WEALTH, 2 OFFICES." % (
                    MAYOR_REPUTATION, MAYOR_WEALTH,
                ),
                "ALDERMAN: %d REP, %d WEALTH." % (
                    ALDERMAN_REPUTATION, ALDERMAN_WEALTH,
                ),
                "COUNCIL VOTES BUILD ELECTION SUPPORT.",
                "QUICK GAME USES WEALTH AND DAY 240.",
                "B IN SETUP OPENS FULL AUDIO OPTIONS.",
            )
        self._draw_shield(43, 58, COLOR_RED_DARK, "H")
        self._text(77, 63, title, COLOR_RED_DARK, 2)
        for index in range(len(lines)):
            self._text(34, 111 + index * 25, lines[index], COLOR_INK, 0)
        self._center("<  PAGE %d / 6  >" % (game.help_page + 1), 269, COLOR_BLUE_INK, 0)
        self._footer("LEFT/RIGHT PAGE  BACK RETURN")
        self.draw.swap()

    def draw_contracts(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("GUILD CONTRACTS", game)
        self._panel(10, 38, 300, 249)
        offers_selected = game.contract_tab == 0
        self._fill(21, 47, 132, 23, COLOR_WOOD_DARK if offers_selected else COLOR_PARCHMENT_DARK)
        self._fill(167, 47, 132, 23, COLOR_WOOD_DARK if not offers_selected else COLOR_PARCHMENT_DARK)
        self._center("OFFERS             ACTIVE", 54, COLOR_GOLD if offers_selected else COLOR_BLUE_INK, 0)
        items = game.contract_offers[game.current_port] if offers_selected else game.active_contracts
        if not items:
            self._center("NO CONTRACTS ON THIS PAGE", 145, COLOR_RED_DARK, 0)
        for index in range(min(3, len(items))):
            contract = items[index]
            y = 80 + index * 62
            selected = index == game.contract_selection
            pinned = not offers_selected and index == game.pinned_contract
            self._fill(22, y, 276, 53, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(22, y, 276, 53, COLOR_GOLD if selected else COLOR_RED_DARK if pinned else COLOR_WOOD_LIGHT)
            color = COLOR_GOLD if selected else COLOR_INK
            self._draw_good_icon(29, y + 14, contract[CONTRACT_GOOD], selected)
            self._text(58, y + 7, "%d %s" % (contract[CONTRACT_QTY], GOOD_NAMES[contract[CONTRACT_GOOD]]), color, 0)
            self._text(58, y + 23, "TO " + PORT_NAMES[contract[CONTRACT_DEST]], color, 0)
            self._text(58, y + 39, "BY D%d" % contract[CONTRACT_DEADLINE], color, 0)
            self._text(211, y + 23, "%dS" % contract[CONTRACT_REWARD], COLOR_GOLD if selected else COLOR_RED_DARK, 0)
            if pinned:
                self._text(257, y + 7, "PIN", COLOR_GOLD if selected else COLOR_RED_DARK, 0)
        mission = game.story_mission
        self._fill(22, 263, 276, 19, COLOR_WOOD_DARK)
        mission_action = "OFFER" if mission[MISSION_STATE] == MISSION_OFFERED else "ACTIVE"
        self._text(28, 267, "S %s: %s" % (mission_action, STORY_NAMES[mission[MISSION_ID]]), COLOR_GOLD, 0)
        self._text(211, 267, "%s D%d" % (
            PORT_NAMES[mission[MISSION_DEST]][:6], mission[MISSION_DEADLINE],
        ), COLOR_PARCHMENT, 0)
        self._footer(
            "L/R TAB CENTER CONTRACT S MISSION"
            if offers_selected else "CENTER DELIVER B PIN S MISSION"
        )
        self.draw.swap()

    def draw_office(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("TRADING OFFICE", game)
        port = game.current_port
        if not game.offices[port]:
            self._panel(24, 57, 272, 201)
            self._draw_shield(142, 76, COLOR_RED_DARK, "O")
            self._center("NO OFFICE IN " + PORT_NAMES[port], 121, COLOR_RED_DARK, 1)
            cost = 350 + sum(game.offices) * 100
            self._center("ESTABLISH A COUNTING HOUSE", 159, COLOR_INK, 0)
            self._center("WAREHOUSE INCLUDED", 181, COLOR_BLUE_INK, 0)
            self._center("COST %d SILVER" % cost, 211, COLOR_RED_DARK, 1)
            self._center("PRESS CENTER", 239, COLOR_BLUE_INK, 0)
        else:
            self._panel(8, 36, 304, 251)
            self._text(20, 45, "WARE", COLOR_BLUE_INK, 0)
            self._text(166, 45, "SHIP", COLOR_BLUE_INK, 0)
            self._text(207, 45, "STOCK", COLOR_BLUE_INK, 0)
            self._text(263, 45, "NEXT", COLOR_BLUE_INK, 0)
            self._line(17, 57, 303, 57, COLOR_WOOD_LIGHT)
            for index in range(len(GOOD_NAMES)):
                self._draw_office_row(game, index)
            self._text(18, 273, "L LOAD R STORE  B WORKSHOPS  S LOAD5", COLOR_BLUE_INK, 0)
        self._footer(game.status)
        self.draw.swap()

    def draw_business(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("CITY WORKSHOPS", game)
        self._panel(12, 38, 296, 249)
        choices = game.local_business_choices()
        for index in range(len(choices)):
            good = choices[index]
            level = game.businesses[game.current_port][good]
            selected = index == game.business_selection
            y = 49 + index * 55
            self._fill(23, y, 274, 49, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(23, y, 274, 49, COLOR_GOLD if selected else COLOR_BRASS)
            self._draw_good_icon(31, y + 12, good, selected)
            color = COLOR_GOLD if selected else COLOR_INK
            self._text(59, y + 7, BUSINESS_NAMES[good], color, 1)
            self._text(59, y + 25, "LEVEL %d  MAKES %s" % (level, GOOD_NAMES[good]), color, 0)
            source = BUSINESS_INPUT[good]
            detail = "NO INPUT" if source < 0 else "USES " + GOOD_NAMES[source]
            self._text(181, y + 25, detail, COLOR_PARCHMENT if selected else COLOR_BLUE_INK, 0)
            if level < 3:
                self._text(233, y + 7, "%dS" % game.business_build_cost(good), COLOR_GOLD if selected else COLOR_RED_DARK, 0)
            else:
                self._text(254, y + 7, "MAX", COLOR_GREEN_DARK, 0)
            if level:
                self._fill(59, y + 39, 78, 4, COLOR_WOOD_LIGHT)
                self._fill(59, y + 39, 26 * level, 4, COLOR_GREEN_DARK)
        self._text(26, 272, "PLOTS %d/3  DAILY WAGES %dS" % (
            game.business_slots_used(), game.business_daily_wage(),
        ), COLOR_BLUE_INK, 0)
        self._footer("UP/DOWN CHOOSE CENTER BUILD BACK OFFICE")
        self.draw.swap()

    def draw_fleet(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("FLEET AND CAPTAINS", game)
        self._panel(12, 39, 296, 247)
        for index in range(len(game.ships)):
            ship = game.ships[index]
            y = 51 + index * 62
            selected = index == game.fleet_selection
            active = index == game.active_ship
            order = ship[SHIP_ORDER]
            state_color = (
                COLOR_GREEN_DARK if order == ORDER_READY
                else COLOR_SEA_LIGHT if order == ORDER_SAIL
                else TFT_DARKGREY
            )
            if ship[SHIP_HULL] < 35:
                state_color = COLOR_RED_DARK
            self._fill(23, y, 274, 54, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(23, y, 274, 54, COLOR_GOLD if active else state_color)
            color = COLOR_GOLD if selected else COLOR_INK
            self._text(32, y + 7, ("* " if active else "  ") + SHIP_NAMES[ship[SHIP_NAME]], color, 1)
            route_state = game.ship_routes[index][ROUTE_STATE]
            label = (
                "AUTO" if route_state == ROUTE_RUNNING
                else "PAUSE" if route_state == ROUTE_PAUSED
                else "ALERT" if route_state == ROUTE_ATTENTION
                else "READY" if order == ORDER_READY
                else "SEA" if order == ORDER_SAIL else "WAIT"
            )
            self._fill(252, y + 7, 38, 14, state_color)
            self._text(258, y + 10, label, TFT_WHITE, 0)
            self._text(34, y + 28, "%s  CAPT %s L%d %s" % (
                SHIP_TYPE_NAMES[game.ship_types[index]], CAPTAIN_NAMES[ship[SHIP_CAPTAIN]],
                game.captain_level(index), game.captain_trait(index),
            ), color, 0)
            revenue, cost, route_net = game.route_account(index)
            self._text(34, y + 42, "H%d C%d/%d E%d ROUTE %+d" % (
                ship[SHIP_HULL], sum(ship[SHIP_CARGO]), ship[SHIP_CAPACITY],
                ship[SHIP_EARNINGS], route_net,
            ), state_color if not selected else COLOR_GOLD, 0)
        if len(game.ships) < 3:
            y = 51 + len(game.ships) * 62
            selected = game.fleet_selection == len(game.ships)
            ship_type = len(game.ships)
            cost = SHIP_TYPE_COST[ship_type]
            self._fill(23, y, 274, 44, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(23, y, 274, 44, COLOR_BRASS)
            self._text(35, y + 8, ("> " if selected else "  ") + "COMMISSION " + SHIP_TYPE_NAMES[ship_type], COLOR_GOLD if selected else COLOR_INK, 0)
            self._text(35, y + 25, "%dS - CAPTAIN %s" % (cost, CAPTAIN_NAMES[len(game.ships)]), COLOR_RED_DARK, 0)
        self._footer("CENTER SELECT  B ROUTE  S CARGO")
        self.draw.swap()

    def draw_tavern(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._header("THE SALT HERRING", game)
        self._panel(18, 42, 284, 242)
        self._draw_tavern_candles()
        self._draw_shield(142, 56, COLOR_RED_DARK, "R")
        self._center("MERCHANT RUMOURS", 91, COLOR_RED_DARK, 1)
        lines = game.rumours()
        for index in range(len(lines)):
            y = 125 + index * 29
            self._fill(31, y - 4, 258, 23, COLOR_PARCHMENT_DARK if index % 2 else COLOR_PARCHMENT)
            self._text(39, y + 2, lines[index][:34], COLOR_INK, 0)
        self._footer("RUMOURS MAY CHANGE EACH VOYAGE")
        self.draw.swap()

    def draw_rivals(self, game):
        self.draw.fill_screen(COLOR_WOOD)
        self._header("RIVAL MERCHANT HOUSES", game)
        self._panel(17, 43, 286, 236)
        order = sorted(game.rivals, key=lambda rival: rival[2], reverse=True)
        for index in range(len(order)):
            rival = order[index]
            y = 60 + index * 65
            self._draw_shield(30, y, COLOR_RED_DARK if index == 0 else COLOR_BLUE_INK, str(index + 1))
            self._text(63, y + 2, RIVAL_NAMES[rival[0]], COLOR_RED_DARK, 1)
            self._text(63, y + 24, "PORT " + PORT_NAMES[rival[1]], COLOR_INK, 0)
            self._text(63, y + 40, "ESTATE %dS  PRESS %d" % (
                rival[2], game.rival_pressure[rival[1]],
            ), COLOR_BLUE_INK, 0)
            self._line(30, y + 57, 290, y + 57, COLOR_WOOD_LIGHT)
        self._fill(25, 257, 270, 16, COLOR_WOOD_DARK)
        self._center(game.rival_news[:40], 261, COLOR_GOLD, 0)
        self._footer("RIVALS UNDERCUT CONTRACTS AND PLOTS")
        self.draw.swap()

    def draw_event(self, game):
        self.draw.fill_screen(COLOR_SEA_DARK)
        for y in range(12, 320, 28):
            self._line(0, y, 320, y, COLOR_SEA)
        if "STORM" in game.event_title:
            for index in range(10):
                x = (index * 37 + self.phase * 11) % 330 - 5
                self._line(x, 18, x - 13, 45, COLOR_SEA_LIGHT)
                self._line(x + 8, 273, x - 5, 299, COLOR_SEA_LIGHT)
        elif "PIRATE" in game.event_title:
            for x in (15, 296):
                self._line(x, 24, x, 48, COLOR_PARCHMENT)
                self._fill(x + 1, 25, 12 + (self.phase & 1) * 2, 8, COLOR_RED_DARK)
        else:
            for index in range(6):
                x = 20 + index * 55 + (self.phase * 4) % 18
                self._circle(x, 34 + (index % 2) * 250, 2, COLOR_GOLD, True)
        self._panel(20, 38, 280, 248)
        self._fill(32, 50, 256, 15, COLOR_WOOD_LIGHT)
        self._fill(32, 270, 256, 10, COLOR_WOOD_LIGHT)
        self._circle(38, 57, 7, COLOR_BRASS, True)
        self._circle(282, 57, 7, COLOR_BRASS, True)
        self._draw_shield(142, 51, COLOR_RED_DARK, "S")
        self._center(game.event_title, 82, COLOR_RED_DARK, 1)
        lines = game.round_lines if game.round_lines else self._wrap(game.event_text, 31)
        if len(lines) > 5:
            lines = lines[:3] + lines[-2:]
        for index in range(len(lines)):
            color = COLOR_RED_DARK if "ELECTS" in lines[index] else COLOR_INK
            self._center(lines[index][:38], 106 + index * 17, color, 0)
        actions = (
            "RESOLVE " + game.decision_title if game.decision_type else "COMMAND " + game.ship_name,
            "VIEW URGENT CONTRACT" if game.active_contracts else "VIEW HOUSE OBJECTIVE",
            "HOUSE OVERVIEW",
        )
        for index in range(3):
            y = 195 + index * 23
            selected = index == game.scroll_selection
            self._fill(40, y, 240, 19, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(40, y, 240, 19, COLOR_GOLD if selected else COLOR_WOOD_LIGHT)
            self._center(("> " if selected else "  ") + actions[index], y + 5, COLOR_GOLD if selected else COLOR_INK, 0)
        self._footer("UP/DOWN CHOOSE  CENTER OPEN")
        self.draw.swap()

    def draw_decision(self, game):
        self.draw.fill_screen(COLOR_SEA_DARK)
        for y in range(10, 320, 24):
            self._line(0, y, 320, y, COLOR_SEA)
        for index in range(8):
            x = (index * 43 + self.phase * 7) % 340 - 10
            self._line(x, 18, x - 8, 38, COLOR_SEA_LIGHT)
        self._panel(18, 31, 284, 260)
        self._draw_shield(142, 45, COLOR_RED_DARK, "!")
        self._center(game.decision_title, 82, COLOR_RED_DARK, 2 if len(game.decision_title) < 19 else 1)
        lines = self._wrap(game.decision_text, 35)
        for index in range(min(3, len(lines))):
            self._center(lines[index], 112 + index * 16, COLOR_INK, 0)
        options = game.decision_options()
        for index in range(len(options)):
            y = 174 + index * 35
            selected = index == game.decision_selection
            self._fill(37, y, 246, 28, COLOR_WOOD_DARK if selected else COLOR_PARCHMENT_DARK)
            self._rect(37, y, 246, 28, COLOR_GOLD if selected else COLOR_BRASS)
            self._center(("> " if selected else "  ") + options[index], y + 8,
                         COLOR_GOLD if selected else COLOR_INK, 0)
        self._footer("UP/DOWN CHOOSE  CENTER DECIDE")
        self.draw.swap()

    def draw_end(self, game):
        self.draw.fill_screen(COLOR_WOOD_DARK)
        self._panel(22, 35, 276, 249)
        self._draw_shield(142, 56, COLOR_RED_DARK, "H")
        if game.result_page == 0:
            self._center(game.result_title, 101, COLOR_RED_DARK, 2 if len(game.result_title) < 18 else 1)
            lines = self._wrap(game.result_text, 31)
            for index in range(len(lines)):
                self._center(lines[index], 145 + index * 21, COLOR_INK, 0)
            self._center("FINAL WEALTH %dS" % game.wealth(), 208, COLOR_BLUE_INK, 0)
            self._center("RANK " + game.rank_name, 229, COLOR_BLUE_INK, 0)
        elif game.result_page == 1:
            self._center("HOUSE LEDGER", 101, COLOR_RED_DARK, 2)
            lines = (
                "DAYS %d  VOYAGES %d" % (game.day, game.voyages),
                "BOUGHT %d  SOLD %d CRATES" % (game.goods_bought, game.goods_sold),
                "CONTRACTS %d  MISSIONS %d" % (game.contracts_completed, game.story_completed),
                "EVENTS %d  COUNCIL VOTES %d" % (game.events_resolved, game.council_decisions),
                "INTEREST %dS  CLAIMS %d" % (game.interest_paid, game.insurance_claims),
            )
            for index in range(len(lines)):
                self._center(lines[index], 139 + index * 23, COLOR_INK, 0)
        else:
            best_ship = 0
            for index in range(1, len(game.ships)):
                if game.ships[index][SHIP_EARNINGS] > game.ships[best_ship][SHIP_EARNINGS]:
                    best_ship = index
            best_city = max(range(len(PORT_NAMES)), key=lambda port: game.city_prosperity[port])
            self._center("LEGACY OF THE HOUSE", 101, COLOR_RED_DARK, 1)
            lines = (
                "BEST SHIP: " + SHIP_NAMES[game.ships[best_ship][SHIP_NAME]],
                "EARNINGS: %dS" % game.ships[best_ship][SHIP_EARNINGS],
                "BEST CITY: " + PORT_NAMES[best_city],
                "PROSPERITY: %d/100" % game.city_prosperity[best_city],
                "PROJECTS BUILT: %d" % game.projects_completed,
            )
            for index in range(len(lines)):
                self._center(lines[index], 139 + index * 23, COLOR_INK, 0)
        self._center("<  PAGE %d / 3  >" % (game.result_page + 1), 260, COLOR_RED_DARK, 0)
        self._footer("LEFT/RIGHT SUMMARY CENTER NEW GAME")
        self.draw.swap()

    def draw_animation(self, game, phase):
        """Redraw only the self-contained moving layer for the active screen."""
        self.phase = phase & 7
        if game.screen == SCREEN_TITLE:
            self._fill(108, 108, 125, 82, COLOR_SEA_DARK)
            for y in (128, 165):
                self._line(108, y, 233, y, COLOR_SEA)
            for x in (138, 183, 228):
                self._line(x, 108, x, 190, COLOR_SEA)
            self._line(108, 180, 120, 184, COLOR_LAND_LIGHT)
            self._line(120, 184, 124, 190, COLOR_LAND_LIGHT)
            gull_x = 205 + self.phase * 2
            self._line(gull_x, 121, gull_x + 4, 118, COLOR_PARCHMENT)
            self._line(gull_x + 4, 118, gull_x + 8, 121, COLOR_PARCHMENT)
            self._draw_ship(136, 125, 1)
        elif game.screen == SCREEN_PORT:
            self._draw_harbor_map(game)
        elif game.screen == SCREEN_WAIT:
            self._draw_harbor(game)
        elif game.screen == SCREEN_MARKET:
            self._draw_market_row(game, game.market_selection)
        elif game.screen == SCREEN_MAP:
            self._draw_map_chart(game)
        elif game.screen == SCREEN_ROUTE:
            self._draw_route_chart(game)
        elif game.screen == SCREEN_OFFICE and game.offices[game.current_port]:
            self._draw_office_row(game, game.office_selection)
        elif game.screen == SCREEN_EVENT:
            self._fill(0, 0, 320, 38, COLOR_SEA_DARK)
            self._fill(0, 287, 320, 12, COLOR_SEA_DARK)
            for y in (12, 34, 292):
                self._line(0, y, 320, y, COLOR_SEA)
            if "STORM" in game.event_title:
                for index in range(10):
                    x = (index * 37 + self.phase * 11) % 330 - 5
                    self._line(x, 8, x - 13, 35, COLOR_SEA_LIGHT)
                    self._line(x + 8, 288, x - 5, 298, COLOR_SEA_LIGHT)
            elif "PIRATE" in game.event_title:
                for x in (15, 296):
                    self._line(x, 8, x, 34, COLOR_PARCHMENT)
                    self._fill(x + 1, 10, 12 + (self.phase & 1) * 2, 8, COLOR_RED_DARK)
            else:
                for index in range(6):
                    x = 20 + index * 55 + (self.phase * 4) % 18
                    self._circle(x, 24 + (index % 2) * 268, 2, COLOR_GOLD, True)
        elif game.screen == SCREEN_DECISION:
            self.draw_decision(game)
            return True
        elif game.screen == SCREEN_TAVERN:
            self._draw_tavern_candles()
        elif game.screen == SCREEN_ADVISER:
            self._draw_tavern_candles()
        elif game.screen == SCREEN_CITY:
            self._draw_harbor(game)
        elif game.screen == SCREEN_SHIPYARD:
            self._fill(42, 55, 145, 105, COLOR_PARCHMENT)
            self._draw_ship(52, 76, 2)
        else:
            return False
        self.draw.swap()
        return True

    def draw_frame(self, game, phase=0):
        self.phase = phase & 7
        if game.screen == SCREEN_TITLE:
            self.draw_title(game)
        elif game.screen == SCREEN_MODE:
            self.draw_mode(game)
        elif game.screen == SCREEN_SAVES:
            self.draw_saves(game)
        elif game.screen == SCREEN_AUDIO:
            self.draw_audio(game)
        elif game.screen == SCREEN_PORT:
            self.draw_port(game)
        elif game.screen == SCREEN_OVERVIEW:
            self.draw_overview(game)
        elif game.screen == SCREEN_MARKET:
            self.draw_market(game)
        elif game.screen == SCREEN_MAP:
            self.draw_map(game)
        elif game.screen == SCREEN_ROUTE:
            self.draw_route(game)
        elif game.screen == SCREEN_WAIT:
            self.draw_wait(game)
        elif game.screen == SCREEN_CITY:
            self.draw_city(game)
        elif game.screen == SCREEN_LOG:
            self.draw_log(game)
        elif game.screen == SCREEN_ADVISER:
            self.draw_adviser(game)
        elif game.screen == SCREEN_COUNCIL:
            self.draw_council(game)
        elif game.screen == SCREEN_BANK:
            self.draw_bank(game)
        elif game.screen == SCREEN_CARGO:
            self.draw_cargo(game)
        elif game.screen == SCREEN_SHIPYARD:
            self.draw_shipyard(game)
        elif game.screen == SCREEN_LEDGER:
            self.draw_ledger(game)
        elif game.screen == SCREEN_CONTRACTS:
            self.draw_contracts(game)
        elif game.screen == SCREEN_OFFICE:
            self.draw_office(game)
        elif game.screen == SCREEN_BUSINESS:
            self.draw_business(game)
        elif game.screen == SCREEN_FLEET:
            self.draw_fleet(game)
        elif game.screen == SCREEN_TAVERN:
            self.draw_tavern(game)
        elif game.screen == SCREEN_RIVALS:
            self.draw_rivals(game)
        elif game.screen == SCREEN_HELP:
            self.draw_help(game)
        elif game.screen == SCREEN_EVENT:
            self.draw_event(game)
        elif game.screen == SCREEN_DECISION:
            self.draw_decision(game)
        elif game.screen == SCREEN_END:
            self.draw_end(game)
