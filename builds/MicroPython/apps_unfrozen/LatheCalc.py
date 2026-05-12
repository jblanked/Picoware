from micropython import const
import json
import gc
import math
from picoware.system.vector import Vector
KC_MAP = (700, 600, 1600, 2000, 1100, 200, 1800, 700, 1800, 2200, 2600)
N_GRADES = (0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.3, 12.5, 25.0, 50.0)
SCREEN_CALC = const(0)
SCREEN_TOOLBOX = const(1)
SCREEN_TAPER = const(2)
SCREEN_CHART = const(3)
SCREEN_TAP = const(4)
SCREEN_HELP = const(5)
SCREEN_THREAD = const(6)
SCREEN_CONVERT = const(7)
SCREEN_OPTIONS = const(8)
SCREEN_KNURL = const(9)
SCREEN_DRILL = const(10)
SCREEN_CENTER = const(11)
SCREEN_MORSE = const(12)
SCREEN_CLEAR = const(13)
SCREEN_SURFACE = const(14)
SCREEN_FITS = const(15)
SCREEN_TOOL_MGR = const(16)
SCREEN_WIRE = const(17)
SCREEN_WEIGHT = const(18)
SCREEN_HARDNESS = const(19)
SCREEN_SPEED = const(20)
SCREEN_GEARS = const(22)
SCREEN_BOLT_CIRCLE = const(23)
SCREEN_TRIANGLE = const(24)
SCREEN_ARC = const(25)
SCREEN_DRILL_PT = const(26)
SCREEN_GRAPH = const(27)
SCREEN_TAP_HOLE = const(28)
FIELD_UNIT = const(0)
FIELD_TYPE = const(1)
FIELD_WORK = const(2)
FIELD_CUTTER = const(3)
FIELD_PROC = const(4)
FIELD_PASS = const(5)
FIELD_APPLY_DOC = const(6)
FIELD_DIAM = const(7)
FIELD_LEN = const(8)
FIELD_VC = const(9)
FIELD_FEED = const(10)
FIELD_DOC = const(11)
FIELD_MAIN_TOOLBOX = const(12)
FIELD_MAIN_HELP = const(13)
PROC_NAMES = ('TURN', 'FACE', 'PART', 'CHAMF', 'BORE', 'DRILL')
WORK_NAMES = ('ALUM', 'BRASS', 'MILD ST', 'STAINLS', 'CST IRN', 'PLASTIC',
    'TITAN', 'COPPER', 'HI-C ST', 'TOOL ST', 'SUPERAL')
TOOLBOX_MENU = [('Charts & Refs', [('Vc Ref Charts', SCREEN_CHART), (
    'Tap Sizes', SCREEN_TAP), ('Drill Sizes', SCREEN_DRILL), (
    'Center Drills', SCREEN_CENTER), ('Morse Tapers', SCREEN_MORSE), (
    'SHCS Clearances', SCREEN_CLEAR), ('Surface Finishes', SCREEN_SURFACE),
    ('ISO Fits', SCREEN_FITS), ('Knurling Guide', SCREEN_KNURL), (
    'Hardness Chart', SCREEN_HARDNESS), ('RPM Bar Chart', SCREEN_GRAPH)]),
    ('Calculators', [('Taper Angle', SCREEN_TAPER), ('Threading Assist',
    SCREEN_THREAD), ('Unit Converter', SCREEN_CONVERT), ('3-Wire Thread',
    SCREEN_WIRE), ('Stock Weight', SCREEN_WEIGHT), ('Speeds & Feeds',
    SCREEN_SPEED), ('Change Gears', SCREEN_GEARS), ('Bolt Circle',
    SCREEN_BOLT_CIRCLE), ('Drill Pt Depth', SCREEN_DRILL_PT), (
    'Tap Drill Calc', SCREEN_TAP_HOLE), ('Right Triangle', SCREEN_TRIANGLE),
    ('Arc & Chord', SCREEN_ARC)]), ('Management', [('Options & Themes',
    SCREEN_OPTIONS), ('Tool Manager', SCREEN_TOOL_MGR)])]
TP_D = const(0)
TP_d = 1
TP_L = const(2)
TP_BACK = const(3)
TH_TYPE = const(0)
TH_DIAM = const(1)
TH_PITCH = const(2)
TH_BACK = const(3)
CV_UNIT = const(0)
CV_VAL = const(1)
CV_BACK = const(2)
WR_TYPE = const(0)
WR_DIAM = const(1)
WR_PITCH = const(2)
WR_WIRE = const(3)
WR_BACK = const(4)
WT_MATL = const(0)
WT_DIAM = const(1)
WT_LEN = const(2)
WT_BACK = const(3)
SP_DIAM = const(0)
SP_VC = const(1)
SP_BACK = const(2)
OPT_THEME = const(0)
OPT_FEED_CAP = const(1)
OPT_RPM_CAP = const(2)
OPT_RA_DISP = const(3)
OPT_MOTOR_PWR = const(4)
OPT_MOTOR_EFF = const(5)
OPT_AUTO_DOC = const(6)
OPT_BACK = const(7)
TM_BACK = const(0)
TM_NEW = const(1)
TM_DEL = const(2)
TM_SELECT = const(3)
TM_RENAME = const(4)
TM_TYPE = const(5)
TM_RAD = const(6)
TM_ANGLE = const(7)
GR_PITCH_CUT = const(0)
GR_PITCH_LS = const(1)
GR_GEARS = const(2)
GR_BACK = const(3)
BC_DIAM = const(0)
BC_HOLES = const(1)
BC_BACK = const(2)
TR_MODE = const(0)
TR_V1 = const(1)
TR_V2 = const(2)
TR_BACK = const(3)
AR_RADIUS = const(0)
AR_ANGLE = const(1)
AR_BACK = const(2)
DP_DIAM = const(0)
DP_ANGLE = const(1)
DP_BACK = const(2)
TD_DIAM = const(0)
TD_PITCH = const(1)
TD_BACK = const(2)
UNIT_METRIC = const(0)
UNIT_IMP = const(1)
CUT_HSS = const(0)
CUT_CARB = const(1)
WORK_ALU = const(0)
WORK_BRASS = const(1)
WORK_MILD = const(2)
WORK_STAIN = const(3)
WORK_CAST = const(4)
WORK_PLAST = const(5)
WORK_TITAN = const(6)
WORK_COPPER = const(7)
WORK_MED_C = const(8)
WORK_TOOL_ST = const(9)
WORK_SUPER = const(10)
TYPE_HOBBY = const(0)
TYPE_INDUST = const(1)
PROC_TURN = const(0)
PROC_FACE = const(1)
PROC_PART = const(2)
PROC_CHAMFER = const(3)
PROC_BORE = const(4)
PROC_DRILL = const(5)
PASS_ROUGH = const(0)
PASS_FINISH = const(1)
TH_METRIC = const(0)
TH_UNIFIED = const(1)
MAX_LATHE_RPM_HOBBY = 2500.0
MAX_LATHE_RPM_INDUST = 6000.0
_SETTINGS_FILE = 'picoware/settings/lathecalc_settings.json'
storage = None
dirty_save = False
save_timer = 0
_last_saved_json = ''


class AppState:
    __slots__ = ("active_tool_idx", "ar_angle", "ar_arc_len", "ar_chord", "ar_radius", "auto_rec_doc", "bc_diam", "bc_holes", "bc_results", "bc_rows", "bc_scroll_pos", "c_bg", "c_err", "c_fg", "c_hlt", "c_ok", "c_sec", "c_warn", "current_screen", "cv_frac", "cv_inch", "cv_mm", "cv_unit", "cv_val", "dp_angle", "dp_diam", "dp_result", "feed_m_result", "gr_gears", "gr_pitch_cut", "gr_pitch_ls", "gr_results", "is_typing", "kb_force", "last_mode", "max_feed_i", "max_feed_m", "max_rpm_hobby", "max_rpm_indust", "motor_eff", "motor_kw_hobby", "motor_kw_indust", "pwr_result_str", "ra_as_ngrade", "ra_result_str", "rec_doc", "rpm_result", "scroll_pos", "sel_ar", "sel_bc", "sel_cv", "sel_dp", "sel_gr", "sel_main", "sel_opt", "sel_sp", "sel_tb_cat", "sel_tb_col", "sel_tb_item", "sel_td", "sel_th", "sel_tm", "sel_tp", "sel_tr", "sel_wr", "sel_wt", "sp_diam", "sp_rpm", "sp_vc", "td_diam", "td_pitch", "td_result", "text_lines", "th_diam", "th_infeed", "th_minor", "th_pass_1", "th_pass_n", "th_pitch", "th_type", "theme_id", "time_result", "tool_profiles", "tp_D", "tp_L", "tp_angle", "tp_d", "tr_A", "tr_B", "tr_C", "tr_ang_a", "tr_ang_b", "tr_mode", "tr_v1", "tr_v2", "ui_feed_m", "ui_left", "ui_max_doc", "ui_pwr", "ui_ra", "ui_res", "ui_right", "ui_rows", "ui_rpm", "ui_rpm_warn", "ui_time", "val_diam", "val_doc", "val_feed", "val_len", "val_pass", "val_proc", "val_type", "val_unit", "val_vc", "val_work", "warn_carbide_spd", "warn_coolant", "warn_high_feed", "warn_poor_finish", "warn_power_cap", "warn_rpm_cap", "wr_best", "wr_diam", "wr_pitch", "wr_result", "wr_type", "wr_wire", "wt_diam", "wt_len", "wt_matl", "wt_result", "x", "y")
    """Encapsulates all application variables to avoid global namespace pollution"""

    def __init__(self):
        self.current_screen = SCREEN_CALC
        self.sel_main = FIELD_UNIT
        self.sel_tb_col = 0
        self.sel_tb_cat = 0
        self.sel_tb_item = 0
        self.sel_tp = TP_D
        self.sel_th = TH_TYPE
        self.sel_cv = CV_UNIT
        self.sel_wr = WR_TYPE
        self.sel_wt = WT_MATL
        self.sel_sp = SP_DIAM
        self.sel_opt = OPT_THEME
        self.sel_tm = TM_SELECT
        self.sel_gr = GR_PITCH_CUT
        self.sel_bc = BC_DIAM
        self.sel_tr = TR_MODE
        self.sel_ar = AR_RADIUS
        self.sel_dp = DP_DIAM
        self.sel_td = TD_DIAM
        self.theme_id = 0
        self.c_bg = 0
        self.c_fg = 0
        self.c_hlt = 0
        self.c_ok = 0
        self.c_warn = 0
        self.c_err = 0
        self.c_sec = 0
        self.val_unit = UNIT_METRIC
        self.val_work = WORK_MILD
        self.val_type = TYPE_HOBBY
        self.val_proc = PROC_TURN
        self.val_pass = PASS_ROUGH
        self.val_diam = 20.0
        self.val_len = 50.0
        self.val_vc = 18.0
        self.val_feed = 0.15
        self.val_doc = 1.0
        self.rpm_result = 0.0
        self.feed_m_result = 0.0
        self.time_result = '0m 0s'
        self.ra_result_str = ''
        self.pwr_result_str = ''
        self.rec_doc = ''
        self.warn_coolant = False
        self.warn_rpm_cap = False
        self.warn_carbide_spd = False
        self.warn_high_feed = False
        self.warn_poor_finish = False
        self.warn_power_cap = False
        self.max_feed_m = 300.0
        self.max_feed_i = 12.0
        self.max_rpm_hobby = 2500.0
        self.max_rpm_indust = 6000.0
        self.ra_as_ngrade = False
        self.auto_rec_doc = False
        self.motor_kw_hobby = 0.5
        self.motor_kw_indust = 5.0
        self.motor_eff = 0.8
        self.tool_profiles = [{'name': 'Gen HSS', 'type': CUT_HSS, 'rad_m':
            0.4, 'rad_i': 0.015, 'angle': 0.0}, {'name': 'Gen CARB', 'type':
            CUT_CARB, 'rad_m': 0.8, 'rad_i': 0.031, 'angle': 0.0}]
        self.active_tool_idx = 0
        self.tp_D = 20.0
        self.tp_d = 15.0
        self.tp_L = 50.0
        self.tp_angle = 0.0
        self.th_type = TH_METRIC
        self.th_diam = 12.0
        self.th_pitch = 1.75
        self.th_minor = 0.0
        self.th_infeed = 0.0
        self.th_pass_1 = 0.0
        self.th_pass_n = 0.0
        self.cv_unit = UNIT_METRIC
        self.cv_val = 10.0
        self.cv_mm = 0.0
        self.cv_inch = 0.0
        self.cv_frac = ''
        self.wr_type = TH_METRIC
        self.wr_diam = 12.0
        self.wr_pitch = 1.75
        self.wr_wire = 1.0
        self.wr_result = 0.0
        self.wr_best = 0.0
        self.wt_matl = 0
        self.wt_diam = 25.4
        self.wt_len = 100.0
        self.wt_result = 0.0
        self.sp_diam = 25.4
        self.sp_vc = 30.0
        self.sp_rpm = 0.0
        self.gr_pitch_cut = 1.75
        self.gr_pitch_ls = 2.0
        self.gr_gears = '20,24,30,32,36,40,44,48,50,52,56,60,64,80,100,120,127'
        self.gr_results = []
        self.bc_diam = 50.0
        self.bc_holes = 6
        self.bc_results = []
        self.bc_scroll_pos = 0
        self.tr_mode = 0
        self.tr_v1 = 10.0
        self.tr_v2 = 10.0
        self.tr_A = 0.0
        self.tr_B = 0.0
        self.tr_C = 0.0
        self.tr_ang_a = 0.0
        self.tr_ang_b = 0.0
        self.ar_radius = 50.0
        self.ar_angle = 90.0
        self.ar_arc_len = 0.0
        self.ar_chord = 0.0
        self.dp_diam = 10.0
        self.dp_angle = 118.0
        self.dp_result = 0.0
        self.td_diam = 6.0
        self.td_pitch = 1.0
        self.td_result = 5.0
        self.ui_left = []
        self.ui_right = []
        self.ui_rpm = ''
        self.ui_feed_m = ''
        self.ui_pwr = ''
        self.ui_time = ''
        self.ui_ra = ''
        self.ui_max_doc = ''
        self.ui_rpm_warn = ''
        self.ui_res = ''
        self.ui_rows = []
        self.bc_rows = []

        self.is_typing = False
        self.kb_force = False
        self.text_lines = []
        self.scroll_pos = 0


state = None


def queue_save():
    """Flags the system to save data after a brief period of user inactivity"""
    global dirty_save, save_timer
    dirty_save = True
    save_timer = 60


def save_settings(view_manager=None, force=False):
    """Serializes the user's setup and writes it directly to the SD card"""
    global storage, dirty_save, _last_saved_json
    s = state
    if not storage or not s:
        return
    if not dirty_save and not force:
        return
    try:
        save_dict = {'theme_id': s.theme_id, 'val_unit': s.val_unit,
            'val_work': s.val_work, 'val_type': s.val_type, 'val_proc': s.
            val_proc, 'val_pass': s.val_pass, 'val_diam': s.val_diam,
            'val_len': s.val_len, 'val_vc': s.val_vc, 'val_feed': s.
            val_feed, 'val_doc': s.val_doc, 'max_feed_m': s.max_feed_m,
            'max_feed_i': s.max_feed_i, 'max_rpm_hobby': s.max_rpm_hobby,
            'max_rpm_indust': s.max_rpm_indust, 'ra_as_ngrade': s.
            ra_as_ngrade, 'auto_rec_doc': s.auto_rec_doc, 'motor_kw_hobby':
            s.motor_kw_hobby, 'motor_kw_indust': s.motor_kw_indust,
            'motor_eff': s.motor_eff, 'tp_D': s.tp_D, 'tp_d': s.tp_d,
            'tp_L': s.tp_L, 'th_type': s.th_type, 'th_diam': s.th_diam,
            'th_pitch': s.th_pitch, 'cv_unit': s.cv_unit, 'cv_val': s.
            cv_val, 'wr_type': s.wr_type, 'wr_diam': s.wr_diam, 'wr_pitch':
            s.wr_pitch, 'wr_wire': s.wr_wire, 'wt_matl': s.wt_matl,
            'wt_diam': s.wt_diam, 'wt_len': s.wt_len, 'sp_diam': s.sp_diam,
            'sp_vc': s.sp_vc, 'gr_pitch_cut': s.gr_pitch_cut, 'gr_pitch_ls':
            s.gr_pitch_ls, 'gr_gears': s.gr_gears, 'bc_diam': s.bc_diam,
            'bc_holes': s.bc_holes, 'tr_mode': s.tr_mode, 'tr_v1': s.tr_v1,
            'tr_v2': s.tr_v2, 'ar_radius': s.ar_radius, 'ar_angle': s.
            ar_angle, 'dp_diam': s.dp_diam, 'dp_angle': s.dp_angle,
            'td_diam': s.td_diam, 'td_pitch': s.td_pitch, 'tool_profiles':
            s.tool_profiles, 'active_tool_idx': s.active_tool_idx}
        json_str = json.dumps(save_dict)
        if json_str != _last_saved_json:
            storage.write(_SETTINGS_FILE, json_str, 'w')
            _last_saved_json = json_str
        dirty_save = False
        del json_str
        gc.collect()
    except Exception:
        pass


def load_settings():
    """Reads persistent memory and loads it back into the AppState"""
    global storage, _last_saved_json
    s = state
    if storage and storage.exists(_SETTINGS_FILE):
        try:
            raw_data = storage.read(_SETTINGS_FILE, 'r')
            _last_saved_json = raw_data
            loaded = json.loads(raw_data)
            for key in loaded:
                if hasattr(s, key):
                    setattr(s, key, loaded[key])
            if 'tool_profiles' in loaded:
                s.tool_profiles = []
                for tp in loaded['tool_profiles']:
                    if 'angle' not in tp:
                        tp['angle'] = 0.0
                    s.tool_profiles.append(tp)
                s.active_tool_idx = loaded.get('active_tool_idx', 0)
            elif 'val_cutter' in loaded:
                _type = int(loaded['val_cutter'])
                _rad_m = float(loaded.get('nose_radius_m', 0.4))
                _rad_i = float(loaded.get('nose_radius_i', 0.015))
                s.tool_profiles = [{'name': 'Legacy Tool', 'type': _type,
                    'rad_m': _rad_m, 'rad_i': _rad_i, 'angle': 0.0}]
                s.active_tool_idx = 0
            s.val_unit = int(s.val_unit)
            s.val_work = int(s.val_work)
            s.val_type = int(s.val_type)
            s.val_proc = int(s.val_proc)
            s.val_pass = int(s.val_pass)
            s.theme_id = int(s.theme_id)
            s.active_tool_idx = int(s.active_tool_idx)
            s.th_type = int(s.th_type)
            s.cv_unit = int(s.cv_unit)
            s.wr_type = int(s.wr_type)
            s.wt_matl = int(s.wt_matl) if hasattr(s, 'wt_matl') else 0
            s.bc_holes = int(s.bc_holes) if hasattr(s, 'bc_holes') else 6
            s.gr_gears = str(s.gr_gears) if hasattr(s, 'gr_gears') else '20,24,30,32,36,40,44,48,50,52,56,60,64,80,100,120,127'
            s.tr_mode = int(s.tr_mode) if hasattr(s, 'tr_mode') else 0
            s.dp_diam = float(s.dp_diam) if hasattr(s, 'dp_diam') else 10.0
            s.dp_angle = float(s.dp_angle) if hasattr(s, 'dp_angle') else 118.0
            s.td_diam = float(s.td_diam) if hasattr(s, 'td_diam') else 6.0
            s.td_pitch = float(s.td_pitch) if hasattr(s, 'td_pitch') else 1.0
            if hasattr(s, 'auto_rec_doc'):
                s.auto_rec_doc = bool(s.auto_rec_doc)
            return True
        except Exception:
            pass
    return False


def _apply_theme():
    s = state
    from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_BLUE, TFT_GREEN, TFT_YELLOW, TFT_RED, TFT_CYAN
    if s.theme_id == 0:
        s.c_bg = TFT_BLACK
        s.c_fg = TFT_WHITE
        s.c_hlt = TFT_YELLOW
        s.c_ok = TFT_GREEN
        s.c_warn = TFT_YELLOW
        s.c_err = TFT_RED
        s.c_sec = TFT_BLUE
    elif s.theme_id == 1:
        s.c_bg = TFT_BLACK
        s.c_fg = TFT_GREEN
        s.c_hlt = TFT_WHITE
        s.c_ok = TFT_CYAN
        s.c_warn = TFT_YELLOW
        s.c_err = TFT_RED
        s.c_sec = TFT_GREEN
    elif s.theme_id == 2:
        s.c_bg = TFT_BLUE
        s.c_fg = TFT_WHITE
        s.c_hlt = TFT_YELLOW
        s.c_ok = TFT_CYAN
        s.c_warn = TFT_YELLOW
        s.c_err = TFT_RED
        s.c_sec = TFT_WHITE
    elif s.theme_id == 3:
        s.c_bg = TFT_WHITE
        s.c_fg = TFT_BLACK
        s.c_hlt = TFT_BLUE
        s.c_ok = TFT_GREEN
        s.c_warn = TFT_RED
        s.c_err = TFT_RED
        s.c_sec = TFT_BLACK


def _load_text(mode):
    s = state
    if mode == 'CHART':
        if s.val_unit == UNIT_METRIC:
            text = """--- HSS REFERENCE Vc (m/min) ---

MATERIAL  | INDUST | HOBBY
PLASTICS  | 90-150 | 70-100
ALUMINUM  | 60-90  | 50-70
BRASS/BRZ | 45-60  | 40-50
COPPER    | 30-45  | 25-35
MILD ST.  | 25-30  | 15-20
MED/HI C. | 18-25  | 10-15
TOOL ST.  | 12-18  | 8-12
STAINLESS | 15-20  | 10-15
CAST IRON | 15-25  | 10-15
TITANIUM  | 10-15  | 8-12
SUPERALLOY| 3-6    | 2-4

--- CARBIDE REFERENCE Vc (m/min) ---

MATERIAL  | INDUST | HOBBY
PLASTICS  | 200+   | 150+
ALUMINUM  | 200+   | 150-250
BRASS/BRZ | 150+   | 100-150
COPPER    | 120+   | 80-120
MILD ST.  | 100+   | 60-80
MED/HI C. | 80+    | 50-70
TOOL ST.  | 50-80  | 30-50
STAINLESS | 80+    | 40-60
CAST IRON | 80-120 | 50-70
TITANIUM  | 40-60  | 30-40
SUPERALLOY| 20-40  | 15-25
"""
        else:
            text = """--- HSS REFERENCE SFM (ft/min) ---

MATERIAL  | INDUST | HOBBY
PLASTICS  | 300-500| 230-330
ALUMINUM  | 200-300| 160-230
BRASS/BRZ | 150-200| 130-160
COPPER    | 100-150| 80-115
MILD ST.  | 80-100 | 50-65
MED/HI C. | 60-80  | 30-50
TOOL ST.  | 40-60  | 25-40
STAINLESS | 50-65  | 30-50
CAST IRON | 50-80  | 30-50
TITANIUM  | 30-50  | 25-40
SUPERALLOY| 10-20  | 6-13

--- CARBIDE REF SFM (ft/min) ---

MATERIAL  | INDUST | HOBBY
PLASTICS  | 650+   | 500+
ALUMINUM  | 650+   | 500-800
BRASS/BRZ | 500+   | 330-500
COPPER    | 400+   | 260-400
MILD ST.  | 330+   | 200-260
MED/HI C. | 260+   | 160-230
TOOL ST.  | 160-260| 100-160
STAINLESS | 260+   | 130-200
CAST IRON | 260-400| 160-230
TITANIUM  | 130-200| 100-130
SUPERALLOY| 65-130 | 50-80
"""
    elif mode == 'TAP':
        text = """--- METRIC COARSE ---

THREAD    | PITCH | DRILL(mm)
M3        | 0.50  | 2.50
M4        | 0.70  | 3.30
M5        | 0.80  | 4.20
M6        | 1.00  | 5.00
M8        | 1.25  | 6.80
M10       | 1.50  | 8.50
M12       | 1.75  | 10.20
M14       | 2.00  | 12.00
M16       | 2.00  | 14.00

--- METRIC FINE ---

M8 x 1.0  | 1.00  | 7.00
M10 x 1.0 | 1.00  | 9.00
M10 x 1.25| 1.25  | 8.80
M12 x 1.25| 1.25  | 10.80
M12 x 1.5 | 1.50  | 10.50

--- IMPERIAL UNC (COARSE) ---

THREAD    | DRILL | DEC(in)
4 - 40    | #43   | .0890
6 - 32    | #36   | .1065
8 - 32    | #29   | .1360
10 - 24   | #25   | .1495
1/4 - 20  | #7    | .2010
5/16 - 18 | F     | .2570
3/8 - 16  | 5/16  | .3125
1/2 - 13  | 27/64 | .4219

--- IMPERIAL UNF (FINE) ---

10 - 32   | #21   | .1590
1/4 - 28  | #3    | .2130
5/16 - 24 | I     | .2770
3/8 - 24  | Q     | .3320
1/2 - 20  | 29/64 | .4531
"""
    elif mode == 'DRILL':
        text = """--- FRACTIONAL DRILLS ---

FRAC   | DEC(in)| METRIC
1/16   | 0.0625 | 1.59mm
1/8    | 0.1250 | 3.18mm
3/16   | 0.1875 | 4.76mm
1/4    | 0.2500 | 6.35mm
5/16   | 0.3125 | 7.94mm
3/8    | 0.3750 | 9.53mm
7/16   | 0.4375 | 11.11mm
1/2    | 0.5000 | 12.70mm
9/16   | 0.5625 | 14.29mm
5/8    | 0.6250 | 15.88mm
3/4    | 0.7500 | 19.05mm
7/8    | 0.8750 | 22.23mm
1.0    | 1.0000 | 25.40mm

--- COMMON WIRE/LETTER ---

SIZE   | DEC(in)| METRIC
#43    | 0.0890 | 2.26mm
#36    | 0.1065 | 2.71mm
#29    | 0.1360 | 3.45mm
#25    | 0.1495 | 3.80mm
#21    | 0.1590 | 4.04mm
#7     | 0.2010 | 5.11mm
#3     | 0.2130 | 5.41mm
F      | 0.2570 | 6.53mm
I      | 0.2770 | 7.04mm
Q      | 0.3320 | 8.43mm
"""
    elif mode == 'KNURL':
        text = """--- KNURLING REFERENCE ---

PITCH | TPI  | USE CASE
1.2mm | 21   | Coarse (Lrg Diam)
0.8mm | 33   | Medium (Gen Purp)
0.5mm | 50   | Fine (Sml Diam)

--- BLANK PREPARATION ---

Form knurls displace metal
outward. Turn your blank
undersize before knurling.

FORMULA:
Blank Diam = Finished Diam
minus (Pitch / 3)

EXAMPLE:
To get a 20mm finish with
a 0.8mm pitch wheel:
20 - (0.8 / 3) = 19.73mm

--- PRO TIPS ---

* Always chamfer blank edges
  first to prevent flaking.
* Flood with cutting fluid.
* Use power feed if possible.
"""
    elif mode == 'CENTER':
        text = """--- CENTER DRILL SIZES ---

SIZE | BODY  | DRILL DIA
#1   | 1/8"  | 3/64"
#2   | 3/16" | 5/64"
#3   | 1/4"  | 7/64"
#4   | 5/16" | 1/8"
#5   | 7/16" | 3/16"
#6   | 1/2"  | 7/32"
#7   | 5/8"  | 1/4"
#8   | 3/4"  | 5/16"

PRO TIP: Never drill past
the 60-degree taper section.
"""
    elif mode == 'MORSE':
        text = """--- MORSE TAPERS (MT) ---

SIZE| LRG DIA | TAPER/FOOT
MT0 | 0.356"  | 0.624"
MT1 | 0.475"  | 0.598"
MT2 | 0.700"  | 0.599"
MT3 | 0.938"  | 0.602"
MT4 | 1.231"  | 0.623"
MT5 | 1.748"  | 0.631"
MT6 | 2.494"  | 0.625"

To cut an MT on the lathe:
Set compound to ~1.43 deg
and use a dial indicator to
sweep a known good taper.
"""
    elif mode == 'CLEAR':
        text = """--- FASTENER CLEARANCES ---
       (Metric SHCS)

SIZE| CLEAR  | C-BORE DIA
M3  | 3.4mm  | 6.0mm
M4  | 4.5mm  | 8.0mm
M5  | 5.5mm  | 10.0mm
M6  | 6.6mm  | 11.0mm
M8  | 9.0mm  | 15.0mm
M10 | 11.0mm | 18.0mm
M12 | 13.5mm | 20.0mm
M16 | 17.5mm | 26.0mm

NOTE: Clearance hole sizes
are 'Standard/Normal' fit.
"""
    elif mode == 'SURFACE':
        text = """--- SURFACE FINISHES ---

ISO | Ra(µm) | Ra(µin)| CLASS
N10 | 12.5   | 500    | Rough
N9  | 6.3    | 250    | Rough
N8  | 3.2    | 125    | Medium
N7  | 1.6    | 63     | Good
N6  | 0.8    | 32     | Fine
N5  | 0.4    | 16     | X-Fine
N4  | 0.2    | 8      | X-Fine

Turning usually achieves
N6 to N9 depending on feed
rate and tool nose radius.
"""
    elif mode == 'FITS':
        text = """--- ISO SHAFT/HOLE FITS ---

Using H7 Base Hole System:

H7 / g6 : Sliding Fit
  (Spools, light movement)

H7 / h6 : Locating Clearance
  (Snug assembly by hand)

H7 / k6 : Locating Transition
  (Light tap with mallet)

H7 / p6 : Medium Press Fit
  (Standard bearing press)

H7 / s6 : Heavy Press Fit
  (Permanent, heat shrink)
"""
    elif mode == 'HARDNESS':
        text = """--- HARDNESS CONVERSION ---

HRC | Brinell(HB)| Tens(MPa)
20  | 226        | 760
25  | 253        | 850
30  | 286        | 960
35  | 327        | 1090
40  | 371        | 1240
45  | 425        | 1420
50  | 481        | 1620
55  | 546        | 1880
60  | 601        | 2180
65  | 682        | N/A
68  | 739        | N/A

Note: Conversions are approx
for non-austenitic steels.
"""
    elif mode == 'HELP':
        text = """=== LATHE-CALC v2.1 ===

=== ABBREVIATIONS GLOSSARY ===
Vc/SFM: Cutting Speed
DOC   : Depth of Cut
LEN   : Length of Cut
DIAM  : Workpiece Diameter
FEED  : Tool travel/revolution
RPM   : Spindle Revolutions/Min
TOOL  : Active Tool Profile
SYS   : Machine Rigidity/Power
PROC  : Machining Process
PASS  : Roughing vs Finishing
Ra    : Surface Roughness Avg.
PWR   : Est. Motor Power
EFF   : Motor Efficiency

=== DETAILED USAGE GUIDE ===

1. NAVIGATION:
   Use UP and DOWN buttons to
   move the yellow cursor `>`.

2. TOGGLES & BUMPING:
   Press LEFT/RIGHT on the [ ]
   fields to cycle options.
   The app auto-updates Vc/Feed
   to safe starting points.
   Press LEFT/RIGHT on number
   fields to bump them up/dwn.

3. MANUAL ENTRY:
   To type exact values, place
   cursor over DIAM, LEN, Vc,
   FEED, or DOC. Press CENTER
   for the on-screen keyboard.

4. APPLY REC DOC:
   Press CENTER on this option
   to manually apply the app's
   recommended DOC limit. Can
   be automated via Options.

5. TIME ESTIMATOR:
   Enter the cut Length (LEN)
   to see the estimated time.

6. TOOL MANAGER:
   Create custom tool profiles
   with unique nose radii for
   HSS and Carbide tools.

7. SHOP TOOLBOX:
   [CHARTS & REFS]
   Quick reference tables for
   speeds, taps, drills, fits,
   surface finish & hardness.

   [CALCULATORS]
   - Taper: Compound angles.
   - Threading: Infeed depths.
   - Convert: mm/in/fractions.
   - 3-Wire: Pitch diam check.
   - Stock Wgt: Material mass.
   - Spd/Feed: Solves for RPM.
   - Gears: Threading trains.
   - Bolt Circle: X/Y coords.

   - Drill Pt: Tip depth calc.
   - Tap Drill: Hole size calc.
   - Arc/Chord: Circle math.
   - Triangle: Solve right
     triangles automatically.

   [MANAGEMENT]
   UI Themes, App Settings,
   and Custom Tool Profiles.

* All settings save automatically

=== CREDITS ===

Made by Slasher006
with the help of Gemini
"""
    if not hasattr(s, 'last_mode') or s.last_mode != mode:
        s.text_lines = text.split('\n')
        s.last_mode = mode
    s.scroll_pos = 0


def _apply_safe_defaults():
    s = state
    _active_type = s.tool_profiles[s.active_tool_idx]['type']
    if s.val_type == TYPE_HOBBY:
        vc_map = [60.0, 45.0, 18.0, 12.0, 12.0, 85.0, 10.0, 30.0, 12.0,
            10.0, 3.0] if _active_type == CUT_HSS else [150.0, 100.0, 70.0,
            50.0, 60.0, 150.0, 35.0, 100.0, 60.0, 40.0, 20.0]
    else:
        vc_map = [75.0, 50.0, 27.0, 17.0, 20.0, 120.0, 12.0, 37.0, 21.0,
            15.0, 4.0] if _active_type == CUT_HSS else [200.0, 150.0, 100.0,
            80.0, 100.0, 200.0, 50.0, 120.0, 80.0, 65.0, 30.0]
    base_vc = vc_map[s.val_work]
    _f_mod = 1.0
    if s.val_proc not in (PROC_PART, PROC_CHAMFER):
        if s.val_work == WORK_SUPER:
            _f_mod = 1.25
        elif s.val_work == WORK_TOOL_ST:
            _f_mod = 0.85
        elif s.val_work == WORK_COPPER and s.val_pass == PASS_FINISH:
            _f_mod = 1.5
    _nose_radius_i = s.tool_profiles[s.active_tool_idx]['rad_i']
    _nose_radius_m = s.tool_profiles[s.active_tool_idx]['rad_m']

    # Calculate recommended DOC
    if s.val_unit == UNIT_IMP:
        if s.val_pass == PASS_FINISH:
            _rec_v = round(_nose_radius_i, 3)
        elif s.val_work in (WORK_SUPER, WORK_TOOL_ST):
            _rec_v = 0.02 if _active_type == CUT_HSS else 0.008
        else:
            _rec_v = 0.04 if _active_type == CUT_HSS else 0.02
    else:
        if s.val_pass == PASS_FINISH:
            _rec_v = round(_nose_radius_m, 2)
        elif s.val_work in (WORK_SUPER, WORK_TOOL_ST):
            _rec_v = 0.5 if _active_type == CUT_HSS else 0.2
        else:
            _rec_v = 1.0 if _active_type == CUT_HSS else 0.5

    if s.val_unit == UNIT_IMP:
        base_vc = base_vc * 3.28084
        if s.val_proc in (PROC_PART, PROC_CHAMFER):
            s.val_vc = base_vc * 0.5
            s.val_feed = 0.002
        else:
            s.val_vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            _base_feed = ((0.006 if _active_type == CUT_HSS else 0.008) if
                s.val_pass == PASS_ROUGH else 0.002 if _active_type ==
                CUT_HSS else 0.003)
            s.val_feed = _base_feed * _f_mod
            s.val_vc = int(s.val_vc)
            s.val_feed = int(s.val_feed * 10000) / 10000.0
            if s.auto_rec_doc or s.val_doc <= 0:
                s.val_doc = _rec_v
    elif s.val_proc in (PROC_PART, PROC_CHAMFER):
        s.val_vc = base_vc * 0.5
        s.val_feed = 0.05
    else:
        s.val_vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
        _base_feed = ((0.15 if _active_type == CUT_HSS else 0.2) if s.
            val_pass == PASS_ROUGH else 0.05 if _active_type == CUT_HSS else
            0.08)
        s.val_feed = _base_feed * _f_mod
        s.val_vc = int(s.val_vc * 10) / 10.0
        s.val_feed = int(s.val_feed * 1000) / 1000.0
        if s.auto_rec_doc or s.val_doc <= 0:
            s.val_doc = _rec_v






def _calc_main(s, _pi):
    _max_rpm = MAX_LATHE_RPM_HOBBY if s.val_type == TYPE_HOBBY else MAX_LATHE_RPM_INDUST
    _active_type = s.tool_profiles[s.active_tool_idx]['type']
    _nose_radius_m = s.tool_profiles[s.active_tool_idx]['rad_m']
    _nose_radius_i = s.tool_profiles[s.active_tool_idx]['rad_i']
    if s.val_diam > 0:
        theoretical_rpm = s.val_vc * 1000.0 / (_pi * s.val_diam) if s.val_unit == UNIT_METRIC else s.val_vc * 12.0 / (_pi * s.val_diam)
        s.rpm_result = theoretical_rpm
        if s.rpm_result > _max_rpm:
            s.rpm_result = _max_rpm
            s.warn_rpm_cap = True
            if _active_type == CUT_CARB:
                s.warn_carbide_spd = True
        if _active_type == CUT_HSS or s.val_proc in (PROC_PART, PROC_CHAMFER, PROC_DRILL) or s.val_work in (WORK_STAIN, WORK_TITAN, WORK_SUPER):
            s.warn_coolant = True
        if s.val_proc == PROC_PART:
            s.rec_doc = 'FULL BLD'
        elif s.val_proc == PROC_CHAMFER:
            s.rec_doc = 'MANUAL'
        elif s.val_proc == PROC_DRILL:
            s.rec_doc = 'PECK'
        elif s.val_proc == PROC_BORE:
            if s.val_pass == PASS_FINISH:
                _n = _nose_radius_m if s.val_unit == UNIT_METRIC else _nose_radius_i
                _rnd = 2 if s.val_unit == UNIT_METRIC else 4
                s.rec_doc = "{}-{}mm".format(round(_n * 0.5, _rnd), round(_n * 1.5, _rnd)) if s.val_unit == UNIT_METRIC else "{}-{}in".format(round(_n * 0.5, _rnd), round(_n * 1.5, _rnd))
            elif s.val_type == TYPE_INDUST:
                s.rec_doc = 'SEE SPEC' if _active_type == CUT_CARB else '1.0mm+' if s.val_unit == UNIT_METRIC else '0.04in+'
            else:
                s.rec_doc = '0.2-0.5mm' if s.val_unit == UNIT_METRIC else '0.01-0.02in'
        elif s.val_pass == PASS_FINISH:
            _n = _nose_radius_m if s.val_unit == UNIT_METRIC else _nose_radius_i
            _rnd = 2 if s.val_unit == UNIT_METRIC else 4
            s.rec_doc = "{}-{}mm".format(round(_n * 0.5, _rnd), round(_n * 1.5, _rnd)) if s.val_unit == UNIT_METRIC else "{}-{}in".format(round(_n * 0.5, _rnd), round(_n * 1.5, _rnd))
        elif s.val_type == TYPE_INDUST:
            s.rec_doc = 'SEE SPEC' if _active_type == CUT_CARB else '2.0mm+' if s.val_unit == UNIT_METRIC else '0.08in+'
        elif s.val_work in (WORK_SUPER, WORK_TOOL_ST):
            s.rec_doc = ('0.5mm' if _active_type == CUT_HSS else '0.2mm') if s.val_unit == UNIT_METRIC else '0.02in' if _active_type == CUT_HSS else '0.008in'
        else:
            s.rec_doc = ('1.0mm' if _active_type == CUT_HSS else '0.5mm') if s.val_unit == UNIT_METRIC else '0.04in' if _active_type == CUT_HSS else '0.02in'
        _feed_limit = s.max_feed_m if s.val_unit == UNIT_METRIC else s.max_feed_i
        s.feed_m_result = s.rpm_result * s.val_feed
        if s.feed_m_result > _feed_limit:
            s.warn_high_feed = True
        s.feed_m_result = round(s.feed_m_result, 1) if s.val_unit == UNIT_METRIC else round(s.feed_m_result, 3)
        if s.val_feed > 0 and s.rpm_result > 0 and s.val_len > 0:
            time_mins = s.val_len / (s.val_feed * s.rpm_result)
            _m = int(time_mins)
            _s = int((time_mins - _m) * 60)
            s.time_result = "{}m {}s".format(_m, _s)
        if s.val_unit == UNIT_IMP:
            _nose_r = _nose_radius_i
            _ra = s.val_feed ** 2 / (32.0 * _nose_r) * 1000000.0 if _nose_r > 0 else 0.0
            _ra_um = _ra * 0.0254
            if not s.ra_as_ngrade: s.ra_result_str = "{} uin".format(int(_ra))
            if _ra > (250.0 if s.val_pass == PASS_ROUGH else 63.0): s.warn_poor_finish = True
        else:
            _nose_r = _nose_radius_m
            _ra = s.val_feed ** 2 / (32.0 * _nose_r) * 1000.0 if _nose_r > 0 else 0.0
            _ra_um = _ra
            if not s.ra_as_ngrade: s.ra_result_str = "{} um".format(round(_ra, 2))
            if _ra > (6.3 if s.val_pass == PASS_ROUGH else 1.6): s.warn_poor_finish = True
        if s.ra_as_ngrade:
            _n_idx = 0
            while _n_idx < 11 and _ra_um > N_GRADES[_n_idx]: _n_idx += 1
            s.ra_result_str = "N{}".format(_n_idx + 1)
        _kc = KC_MAP[s.val_work] if s.val_work < 11 else 1000
        _vc_m = s.val_vc if s.val_unit == UNIT_METRIC else s.val_vc * 0.3048
        _feed_mm = s.val_feed if s.val_unit == UNIT_METRIC else s.val_feed * 25.4
        _doc_mm = s.val_doc if s.val_unit == UNIT_METRIC else s.val_doc * 25.4
        _pc_kw = _vc_m * _doc_mm * _feed_mm * _kc / 60000.0
        _req_motor_kw = _pc_kw / s.motor_eff if s.motor_eff > 0 else 0.0
        _motor_limit_kw = s.motor_kw_hobby if s.val_type == TYPE_HOBBY else s.motor_kw_indust
        if _req_motor_kw > _motor_limit_kw: s.warn_power_cap = True
        s.pwr_result_str = "{} HP".format(round(_req_motor_kw * 1.34102, 2)) if s.val_unit == UNIT_IMP else "{} kW".format(round(_req_motor_kw, 2))

    # Pre-format UI strings
    _str_unit = 'METRIC' if s.val_unit == UNIT_METRIC else 'IMPERL'
    _active_tool_name = s.tool_profiles[s.active_tool_idx]['name'][:5]
    _r_val = s.tool_profiles[s.active_tool_idx]['rad_m'] if s.val_unit == UNIT_METRIC else s.tool_profiles[s.active_tool_idx]['rad_i']
    _r_str = str(_r_val).lstrip('0') if str(_r_val).startswith('0.') else str(_r_val)
    _str_tool = "{}]R{}".format("[{}".format(_active_tool_name), _r_str)
    _str_type = 'HOBBY' if s.val_type == TYPE_HOBBY else 'INDUST'
    _str_proc = PROC_NAMES[s.val_proc]
    _str_pass = 'ROUGH' if s.val_pass == PASS_ROUGH else 'FINISH'
    _str_work = WORK_NAMES[s.val_work]
    _u_d = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    _u_v = 'm/m' if s.val_unit == UNIT_METRIC else 'SFM'
    _u_f = 'mm/r' if s.val_unit == UNIT_METRIC else 'in/r'
    _l_v = 'Vc  :' if s.val_unit == UNIT_METRIC else 'SFM :'
    _diam_label = 'D-DIA:' if s.val_proc == PROC_DRILL else 'DIAM: '

    s.ui_left = [
        "UNIT: [{}]".format(_str_unit),
        "SYS : [{}]".format(_str_type),
        "WORK: [{}]".format(_str_work),
        "TOOL: {}".format(_str_tool),
        "PROC: [{}]".format(_str_proc),
        "PASS: [{}]".format(_str_pass),
        "[=] APPLY REC DOC"
    ]
    s.ui_right = [
        "{} {} {}".format(_diam_label, s.val_diam, _u_d),
        "LEN : {} {}".format(s.val_len, _u_d),
        "{} {} {}".format(_l_v, s.val_vc, _u_v),
        "FEED: {} {}".format(s.val_feed, _u_f),
        "DOC : {} {}".format(s.val_doc, _u_d),
        "[>] TOOLBOX",
        "[?] HELP"
    ]
    s.ui_rpm = str(int(s.rpm_result))
    s.ui_feed_m = str(s.feed_m_result)
    s.ui_pwr = "EST PWR: {}".format(s.pwr_result_str)
    s.ui_time = "TIME: {}".format(s.time_result)
    s.ui_ra = "EST Ra : {}".format(s.ra_result_str)
    s.ui_max_doc = "MAX DOC: {}".format(s.rec_doc)
    s.ui_rpm_warn = "! RPM CAPPED (MAX {})".format(int(_max_rpm))

def _calc_taper(s, _pi):
    if s.tp_L > 0:
        _rads = math.atan(abs(s.tp_D - s.tp_d) / (2.0 * s.tp_L))
        s.tp_angle = round(_rads * (180.0 / _pi), 2)
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    s.ui_rows = ['LARGE DIAM (D):  {} {}'.format(round(s.tp_D, 3), _u), 'SMALL DIAM (d):  {} {}'.format(round(s.tp_d, 3), _u), 'TAPER LEN  (L):  {} {}'.format(round(s.tp_L, 3), _u), '< RETURN TO TOOLBOX']
    s.ui_res = '{} DEGREES'.format(s.tp_angle)

def _calc_thread(s):
    _th_p = s.th_pitch if s.th_type == TH_METRIC else 1.0 / max(0.001, s.th_pitch)
    _th_h = 0.61343 * _th_p
    s.th_minor = s.th_diam - 2.0 * _th_h
    s.th_infeed = _th_h / 0.87035
    if s.th_type == TH_METRIC:
        s.th_pass_1 = min(0.3, max(0.1, _th_p * 0.15))
        s.th_pass_n = min(0.15, max(0.05, _th_p * 0.05))
    else:
        s.th_pass_1 = min(0.012, max(0.004, _th_p * 0.15))
        s.th_pass_n = min(0.006, max(0.002, _th_p * 0.05))
    _u = 'mm' if s.th_type == TH_METRIC else 'in'
    s.ui_rows = ['NOMINAL DIAM :  {} {}'.format(s.th_diam, _u), 'PITCH/TPI    :  {}'.format(s.th_pitch), '< RETURN TO TOOLBOX']
    s.ui_res = 'MINOR: {:.3f} | INFEED: {:.3f}'.format(s.th_minor, s.th_infeed)

def _calc_convert(s):
    if s.cv_unit == UNIT_METRIC:
        s.cv_mm, s.cv_inch = s.cv_val, s.cv_val / 25.4
    else:
        s.cv_mm, s.cv_inch = s.cv_val * 25.4, s.cv_val
    _whole = int(s.cv_inch)
    _rem = s.cv_inch - _whole
    _num, _den = int(_rem * 64.0 + 0.5), 64
    if _num == 64: _whole += 1; _num = 0
    while _num > 0 and _num % 2 == 0 and _den > 1: _num //= 2; _den //= 2
    if _num == 0: s.cv_frac = '{} "'.format(_whole) if _whole > 0 else '0"'
    else: s.cv_frac = '{} {}/{}"'.format(str(_whole) + ' ' if _whole > 0 else '', _num, _den)
    s.ui_rows = ['CONVERT VALUE:  {}'.format(s.cv_val), 'FROM UNIT    :  {}'.format('METRIC (mm)' if s.cv_unit == UNIT_METRIC else 'IMPERIAL (in)'), '< RETURN TO TOOLBOX']
    s.ui_res = '{} mm | {:.4f} in'.format(s.cv_mm, s.cv_inch)

def _calc_wire(s):
    _wr_p = s.wr_pitch if s.wr_type == TH_METRIC else 1.0 / max(0.001, s.wr_pitch)
    s.wr_best = 0.57735 * _wr_p
    s.wr_result = s.wr_diam - 0.866025 * _wr_p + 3.0 * s.wr_wire
    _u = 'mm' if s.wr_type == TH_METRIC else 'in'
    s.ui_rows = ['NOMINAL DIAM :  {} {}'.format(s.wr_diam, _u), 'PITCH/TPI    :  {}'.format(s.wr_pitch), 'WIRE SIZE    :  {} {}'.format(s.wr_wire, _u), '< RETURN TO TOOLBOX']
    s.ui_res = 'M-MEAS: {:.4f} | BEST: {:.4f}'.format(s.wr_result, s.wr_best)

def _calc_weight(s, _pi):
    _wt_densities = (7.85, 2.7, 8.53, 7.93, 7.2, 4.5, 8.96, 1.2)
    _d = _wt_densities[s.wt_matl]
    if s.val_unit == UNIT_METRIC: s.wt_result = _pi * (s.wt_diam / 20.0) ** 2 * (s.wt_len / 10.0) * _d / 1000.0
    else: s.wt_result = _pi * (s.wt_diam / 2.0) ** 2 * s.wt_len * (_d * 0.0361273)
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    _mat = ('STEEL', 'ALUMINUM', 'BRASS', 'STAINLESS', 'CAST IRON', 'TITANIUM', 'COPPER', 'PLASTIC')[s.wt_matl]
    s.ui_rows = ['MATL : [ {} ]'.format(_mat), 'DIAM :   {} {}'.format(round(s.wt_diam, 3), _u), 'LEN  :   {} {}'.format(round(s.wt_len, 3), _u), '< RETURN TO TOOLBOX']
    s.ui_res = '{:.3f} {}'.format(s.wt_result, 'kg' if s.val_unit == UNIT_METRIC else 'lbs')
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    _mat = ['STEEL', 'ALUM', 'BRASS', 'STAIN', 'IRON', 'TITAN', 'COPPER', 'PLAST'][s.wt_matl]
    s.ui_rows = ['MATERIAL     :  {}'.format(_mat), 'DIAMETER     :  {} {}'.format(s.wt_diam, _u), 'LENGTH       :  {} {}'.format(s.wt_len, _u), '< RETURN TO TOOLBOX']
    s.ui_res = 'TOTAL WEIGHT: {:.3f} {}'.format(s.wt_result, 'kg' if s.val_unit == UNIT_METRIC else 'lb')

def _calc_speed(s, _pi):
    if s.sp_diam > 0: s.sp_rpm = s.sp_vc * 1000.0 / (_pi * s.sp_diam) if s.val_unit == UNIT_METRIC else s.sp_vc * 12.0 / (_pi * s.sp_diam)
    else: s.sp_rpm = 0.0
    _u_d, _u_v = ('mm', 'm/min') if s.val_unit == UNIT_METRIC else ('in', 'SFM')
    _v_lbl = 'Vc  :    ' if s.val_unit == UNIT_METRIC else 'SFM :    '
    s.ui_rows = ['DIAM:    {} {}'.format(round(s.sp_diam, 3), _u_d), '{}{} {}'.format(_v_lbl, round(s.sp_vc, 2), _u_v), '< RETURN TO TOOLBOX']
    s.ui_res = '{} RPM'.format(int(s.sp_rpm))

def _calc_gears(s):
    s.gr_results = []
    available_gears = sorted(list(set([int(g.strip()) for g in s.gr_gears.split(',') if g.strip().isdigit()])))
    if not available_gears: s.gr_results = ['Error: No valid gears']; return
    is_metric, pitch_cut, pitch_ls = s.val_unit == UNIT_METRIC, s.gr_pitch_cut, s.gr_pitch_ls
    if pitch_cut <= 0 or pitch_ls <= 0: s.gr_results = ['Error: Pitches must be > 0']; return
    target_ratio = pitch_cut / pitch_ls if is_metric else pitch_ls / pitch_cut
    for g1 in available_gears:
        for g2 in available_gears:
            if g1 == g2: continue
            if abs((g1/g2) - target_ratio) < 0.0001:
                s.gr_results.append('{} / {}'.format(g1, g2))
                if len(s.gr_results) >= 10: break
    if len(s.gr_results) < 10:
        r_map = {}
        for g1 in available_gears:
            for g2 in available_gears:
                if g1 == g2: continue
                r = g1 / g2
                if r not in r_map: r_map[r] = (g1, g2)
        for r1 in r_map:
            if len(s.gr_results) >= 10: break
            try: r2_target = target_ratio / r1
            except ZeroDivisionError: continue
            for r2 in r_map:
                if abs(r2 - r2_target) < 0.0001:
                    a, b = r_map[r1]; c, d = r_map[r2]; used = [a, b, c, d]
                    if all(used.count(g) <= available_gears.count(g) for g in used):
                        sol = '({}/{}) * ({}/{})'.format(a, b, c, d)
                        if sol not in s.gr_results:
                            s.gr_results.append(sol)
                            if len(s.gr_results) >= 10: break
    _u = 'mm' if is_metric else 'TPI'
    s.ui_rows = ['PITCH TO CUT: {} {}'.format(s.gr_pitch_cut, _u), 'LEADSCREW   : {} {}'.format(s.gr_pitch_ls, _u), 'AVAIL GEARS : {}...'.format(s.gr_gears[:20]), '< RETURN TO TOOLBOX']

def _calc_bolt_circle(s, _pi):
    s.bc_results = []
    if s.bc_holes > 1:
        radius, angle_step = s.bc_diam / 2.0, 360.0 / s.bc_holes
        for i in range(s.bc_holes):
            angle_rad = (i * angle_step) * (_pi / 180.0)
            s.bc_results.append((round(radius * math.sin(angle_rad), 4), round(radius * math.cos(angle_rad), 4)))
    s.bc_rows = []
    for j, (rx, ry) in enumerate(s.bc_results):
        s.bc_rows.append('{}: ({}, {})'.format(j + 1, rx, ry))
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    s.ui_rows = ['CIRCLE DIAM: {} {}'.format(s.bc_diam, _u), 'NUM HOLES  : {}'.format(s.bc_holes), '< RETURN TO TOOLBOX']

def _calc_triangle(s):
    s.tr_A = s.tr_B = s.tr_C = s.tr_ang_a = s.tr_ang_b = 0.0
    try:
        m, v1, v2 = s.tr_mode, s.tr_v1, s.tr_v2
        rad, deg = math.pi / 180.0, 180.0 / math.pi
        if m == 0: s.tr_A, s.tr_B = v1, v2; s.tr_C = math.sqrt(v1*v1 + v2*v2); s.tr_ang_a = math.atan2(v1, v2) * deg if v2 != 0 else 90.0
        elif m == 1: s.tr_A, s.tr_C = v1, v2; s.tr_B = math.sqrt(v2*v2 - v1*v1) if v2 > v1 else 0; s.tr_ang_a = math.asin(v1/v2)*deg if v2 > v1 else 0
        elif m == 2: s.tr_B, s.tr_C = v1, v2; s.tr_A = math.sqrt(v2*v2 - v1*v1) if v2 > v1 else 0; s.tr_ang_a = math.acos(v1/v2)*deg if v2 > v1 else 0
        elif m == 3: s.tr_A, s.tr_ang_a = v1, v2; s.tr_B, s.tr_C = (v1 / math.tan(v2*rad), v1 / math.sin(v2*rad)) if 0 < v2 < 90 else (0,0)
        elif m == 4: s.tr_B, s.tr_ang_a = v1, v2; s.tr_A, s.tr_C = (v1 * math.tan(v2*rad), v1 / math.cos(v2*rad)) if 0 < v2 < 90 else (0,0)
        elif m == 5: s.tr_C, s.tr_ang_a = v1, v2; s.tr_A, s.tr_B = (v1 * math.sin(v2*rad), v1 * math.cos(v2*rad)) if 0 < v2 < 90 else (0,0)
        if s.tr_ang_a > 0: s.tr_ang_b = 90.0 - s.tr_ang_a
    except: pass
    _modes = ('A & B', 'A & C', 'B & C', 'A & Ang(a)', 'B & Ang(a)', 'C & Ang(a)')
    _v1_lbls = ('SIDE A', 'SIDE A', 'SIDE B', 'SIDE A', 'SIDE B', 'SIDE C')
    _v2_lbls = ('SIDE B', 'SIDE C', 'SIDE C', 'ANGLE a', 'ANGLE a', 'ANGLE a')
    s.ui_rows = ['GIVEN: < {} >'.format(_modes[s.tr_mode]), '{}: {}'.format(_v1_lbls[s.tr_mode], round(s.tr_v1, 4)), '{}: {}'.format(_v2_lbls[s.tr_mode], round(s.tr_v2, 4)), '< RETURN TO TOOLBOX']

def _calc_arc(s):
    s.ar_arc_len = s.ar_chord = 0.0
    if s.ar_radius > 0 and s.ar_angle > 0:
        _rad = s.ar_angle * (math.pi / 180.0)
        s.ar_arc_len, s.ar_chord = s.ar_radius * _rad, 2.0 * s.ar_radius * math.sin(_rad / 2.0)
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    s.ui_rows = ['ARC RADIUS   :  {} {}'.format(s.ar_radius, _u), 'INCL. ANGLE  :  {} DEG'.format(s.ar_angle), '< RETURN TO TOOLBOX']
    s.ui_res = 'LEN: {:.3f} | CHORD: {:.3f}'.format(s.ar_arc_len, s.ar_chord)

def _calc_drill_pt(s):
    if s.dp_diam > 0 and s.dp_angle > 0:
        s.dp_result = s.dp_diam / 2.0 / math.tan((s.dp_angle / 2.0) * (math.pi / 180.0))
    else: s.dp_result = 0.0
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    s.ui_rows = ['DRILL DIAM   :  {} {}'.format(s.dp_diam, _u), 'POINT ANGLE  :  {} DEG'.format(s.dp_angle), '< RETURN TO TOOLBOX']
    s.ui_res = 'TIP DEPTH: {:.3f} {}'.format(s.dp_result, _u)

def _calc_tap_hole(s):
    if s.td_diam > 0 and s.td_pitch > 0:
        s.td_result = max(0.0, s.td_diam - (s.td_pitch if s.val_unit == UNIT_METRIC else 1.0 / s.td_pitch))
    else: s.td_result = 0.0
    _u = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    s.ui_rows = ['THREAD DIAM  :  {} {}'.format(s.td_diam, _u), 'PITCH/TPI    :  {}'.format(s.td_pitch), '< RETURN TO TOOLBOX']
    s.ui_res = 'TAP DRILL: {:.3f} {}'.format(s.td_result, _u)


def _calc_options(s):
    themes = ('0: DARK THEME', '1: TERMINAL', '2: BLUEPRINT', '3: LIGHT MODE')
    _u = 'mm/m' if s.val_unit == UNIT_METRIC else 'in/m'
    _limit_val = s.max_feed_m if s.val_unit == UNIT_METRIC else s.max_feed_i
    _rpm_cap = s.max_rpm_hobby if s.val_type == TYPE_HOBBY else s.max_rpm_indust
    _ra_disp = 'N-GRADE' if s.ra_as_ngrade else 'um' if s.val_unit == UNIT_METRIC else 'uin'
    _pwr_kw = s.motor_kw_hobby if s.val_type == TYPE_HOBBY else s.motor_kw_indust
    _pwr_u = 'HP' if s.val_unit == UNIT_IMP else 'kW'
    _pwr_disp = round(_pwr_kw * 1.34102, 2) if s.val_unit == UNIT_IMP else round(_pwr_kw, 2)
    _auto_doc_str = 'ON' if s.auto_rec_doc else 'OFF'
    s.ui_rows = [
        "UI THEME: < {} >".format(themes[s.theme_id]),
        "MAX FEED:   {} {}".format(round(_limit_val, 3), _u),
        "MAX RPM :   {} RPM".format(int(_rpm_cap)),
        "Ra DISP : < {} >".format(_ra_disp),
        "MTR PWR :   {} {}".format(_pwr_disp, _pwr_u),
        "MTR EFF :   {} %".format(int(s.motor_eff * 100)),
        "AUTO DOC: < {} >".format(_auto_doc_str),
        "< RETURN TO TOOLBOX"
    ]

def _calc_tool_mgr(s):
    active_tool = s.tool_profiles[s.active_tool_idx]
    _t_str = 'HSS' if active_tool['type'] == CUT_HSS else 'CARBIDE'
    _r_str = "{} mm".format(round(active_tool['rad_m'], 3)) if s.val_unit == UNIT_METRIC else "{} in".format(round(active_tool['rad_i'], 4))
    _a_str = "{} DEG".format(round(active_tool.get('angle', 0.0), 1))
    s.ui_rows = [
        "< RETURN TO TOOLBOX",
        "+ CREATE NEW TOOL",
        "- DELETE CURR TOOL",
        "SELECT: < {} >".format(active_tool['name']),
        "RENAME: [PRESS CENTER]",
        "TYPE  : < {} >".format(_t_str),
        "RADIUS: < {} >".format(_r_str),
        "ANGLE : < {} >".format(_a_str)
    ]

def _calculate():
    s = state
    _pi = 3.14159
    s.warn_coolant = s.warn_rpm_cap = s.warn_carbide_spd = s.warn_high_feed = False
    s.warn_poor_finish = s.warn_power_cap = False
    s.time_result = '0m 0s'

    cur = s.current_screen
    if cur == SCREEN_CALC or cur == SCREEN_GRAPH: _calc_main(s, _pi)
    elif cur == SCREEN_TAPER: _calc_taper(s, _pi)
    elif cur == SCREEN_THREAD: _calc_thread(s)
    elif cur == SCREEN_CONVERT: _calc_convert(s)
    elif cur == SCREEN_WIRE: _calc_wire(s)
    elif cur == SCREEN_WEIGHT: _calc_weight(s, _pi)
    elif cur == SCREEN_SPEED: _calc_speed(s, _pi)
    elif cur == SCREEN_GEARS: _calc_gears(s)
    elif cur == SCREEN_BOLT_CIRCLE: _calc_bolt_circle(s, _pi)
    elif cur == SCREEN_TRIANGLE: _calc_triangle(s)
    elif cur == SCREEN_ARC: _calc_arc(s)
    elif cur == SCREEN_DRILL_PT: _calc_drill_pt(s)
    elif cur == SCREEN_TAP_HOLE: _calc_tap_hole(s)
    elif cur == SCREEN_OPTIONS: _calc_options(s)
    elif cur == SCREEN_TOOL_MGR: _calc_tool_mgr(s)


def start(view_manager):
    global state, storage
    state = AppState()
    storage = view_manager.storage
    if not load_settings():
        _apply_safe_defaults()
    _apply_theme()
    _calculate()
    _draw_ui(view_manager)
    return True


def _draw_ui(view_manager):
    _calculate()
    if state.current_screen == SCREEN_CALC:
        _draw_calc(view_manager)
    elif state.current_screen == SCREEN_TOOLBOX:
        _draw_toolbox(view_manager)
    elif state.current_screen == SCREEN_TAPER:
        _draw_taper(view_manager)
    elif state.current_screen == SCREEN_THREAD:
        _draw_thread(view_manager)
    elif state.current_screen == SCREEN_CONVERT:
        _draw_convert(view_manager)
    elif state.current_screen == SCREEN_OPTIONS:
        _draw_options(view_manager)
    elif state.current_screen == SCREEN_TOOL_MGR:
        _draw_tool_mgr(view_manager)
    elif state.current_screen == SCREEN_WIRE:
        _draw_wire(view_manager)
    elif state.current_screen == SCREEN_WEIGHT:
        _draw_weight(view_manager)
    elif state.current_screen == SCREEN_SPEED:
        _draw_speed(view_manager)
    elif state.current_screen == SCREEN_GEARS:
        _draw_gears(view_manager)
    elif state.current_screen == SCREEN_BOLT_CIRCLE:
        _draw_bolt_circle(view_manager)
    elif state.current_screen == SCREEN_TRIANGLE:
        _draw_triangle(view_manager)
    elif state.current_screen == SCREEN_ARC:
        _draw_arc(view_manager)
    elif state.current_screen == SCREEN_DRILL_PT:
        _draw_drill_pt(view_manager)
    elif state.current_screen == SCREEN_GRAPH:
        _draw_graph(view_manager)
    elif state.current_screen == SCREEN_TAP_HOLE:
        _draw_tap_hole(view_manager)
    elif state.current_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL,
        SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE,
        SCREEN_FITS, SCREEN_HELP, SCREEN_KNURL, SCREEN_HARDNESS):
        _draw_text_screen(view_manager, state.current_screen)


def _draw_text_screen(view_manager, mode):
    s = state
    v_pos = Vector(0, 0)
    v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    if mode == SCREEN_CHART:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'SYSTEM DATA CHARTS', s.c_fg)
    elif mode == SCREEN_TAP:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'TAP & CLEARANCE SIZES', s.c_fg)
    elif mode == SCREEN_DRILL:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'DRILL SIZE CHART', s.c_fg)
    elif mode == SCREEN_CENTER:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'CENTER DRILL SIZES', s.c_fg)
    elif mode == SCREEN_MORSE:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'MORSE TAPER DIMS', s.c_fg)
    elif mode == SCREEN_CLEAR:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'SHCS CLEARANCES', s.c_fg)
    elif mode == SCREEN_SURFACE:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'SURFACE FINISHES', s.c_fg)
    elif mode == SCREEN_FITS:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'ISO FITS (H7 BASE)', s.c_fg)
    elif mode == SCREEN_KNURL:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'KNURLING REFERENCE', s.c_fg)
    elif mode == SCREEN_HARDNESS:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'HARDNESS CONVERSION', s.c_fg)
    else:
        v_pos.x = 5
        v_pos.y = 5
        _draw.text(v_pos, 'HELP & ABBREVIATIONS', s.c_fg)
    v_pos.x = 0
    v_pos.y = 22
    v_size.x = 320
    v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    _vis = 16
    _lh = 15
    _sy = 30
    v_pos = Vector(5, 0)
    for i in range(_vis):
        _idx = s.scroll_pos + i
        if _idx < len(s.text_lines):
            v_pos.y = _sy + i * _lh
            _draw.text(v_pos, s.text_lines[_idx], s.c_fg)
    _tot = len(s.text_lines)
    if _tot > _vis:
        v_pos.x = 313
        v_pos.y = _sy
        v_size.x = 313
        v_size.y = 275
        _draw.line(v_pos, v_size, s.c_sec)
        _th = max((_vis  // _tot * 245), 10)
        _ms = _tot - _vis
        _ty = _sy + (s.scroll_pos  // _ms * (245 - _th)) if _ms > 0 else _sy
        v_pos.x = 311
        v_pos.y = _ty
        v_size.x = 4
        v_size.y = _th
        _draw.fill_rectangle(v_pos, v_size, s.c_hlt)
    v_pos.x = 0
    v_pos.y = 282
    v_size.x = 320
    v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5
    v_pos.y = 295
    _draw.text(v_pos, '[UP/DOWN] SCROLL | [BACK] EXIT', s.c_sec)
    _draw.swap()


def _draw_graph(view_manager):
    s = state
    v_pos = Vector(0, 0)
    v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5
    v_pos.y = 5
    _draw.text(v_pos, 'RPM vs MATERIAL', s.c_fg)
    v_pos.x = 0
    v_pos.y = 22
    v_size.x = 320
    v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    _u_d = 'mm' if s.val_unit == UNIT_METRIC else 'in'
    v_pos.x = 5
    v_pos.y = 28
    _draw.text(v_pos, '{}{} | Tool: '.format('Diam: {}'.format(s.val_diam),
        _u_d) + ('HSS' if s.tool_profiles[s.active_tool_idx]['type'] ==
        CUT_HSS else 'CARB'), s.c_ok)
    _active_type = s.tool_profiles[s.active_tool_idx]['type']
    if s.val_type == TYPE_HOBBY:
        vc_map = [60.0, 45.0, 18.0, 12.0, 12.0, 85.0, 10.0, 30.0, 12.0,
            10.0, 3.0] if _active_type == CUT_HSS else [150.0, 100.0, 70.0,
            50.0, 60.0, 150.0, 35.0, 100.0, 60.0, 40.0, 20.0]
    else:
        vc_map = [75.0, 50.0, 27.0, 17.0, 20.0, 120.0, 12.0, 37.0, 21.0,
            15.0, 4.0] if _active_type == CUT_HSS else [200.0, 150.0, 100.0,
            80.0, 100.0, 200.0, 50.0, 120.0, 80.0, 65.0, 30.0]
    _pi = 3.14159
    _max_rpm = (s.max_rpm_hobby if s.val_type == TYPE_HOBBY else s.
        max_rpm_indust)
    rpms = []
    for i in range(11):
        base_vc = vc_map[i]
        if s.val_unit == UNIT_IMP:
            vc = (base_vc * 3.28084 if s.val_pass == PASS_ROUGH else
                base_vc * 3.28084 * 1.3)
            rpm = vc * 12.0 / (_pi * s.val_diam) if s.val_diam > 0 else 0
        else:
            vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            rpm = vc * 1000.0 / (_pi * s.val_diam) if s.val_diam > 0 else 0
        rpms.append(min(rpm, _max_rpm))
    _max_plotted = max(rpms) if rpms and max(rpms) > 0 else 1.0
    plot_max = _max_plotted * 1.15
    labels = ['AL', 'BR', 'MS', 'SS', 'CI', 'PL', 'TI', 'CU', 'HC', 'TS', 'SA']
    bar_w = 22
    spacing = 6
    start_x = 8
    base_y = 250
    max_h = 180
    for i in range(11):
        h = (rpms[i]  // plot_max * max_h)
        x = start_x + i * (bar_w + spacing)
        c = s.c_hlt if i == s.val_work else s.c_fg
        if h > 0:
            v_pos.x = x
            v_pos.y = base_y - h
            v_size.x = bar_w
            v_size.y = h
            _draw.fill_rectangle(v_pos, v_size, c)
        v_pos.x = x + 2
        v_pos.y = base_y + 5
        _draw.text(v_pos, labels[i], c)
        if i == s.val_work:
            v_pos.x = x - 4
            v_pos.y = base_y - h - 15
            _draw.text(v_pos, str(int(rpms[i])), s.c_ok)
    limit_h = (_max_rpm  // plot_max * max_h)
    if limit_h <= max_h:
        limit_y = base_y - limit_h
        v_size.x = 4
        v_size.y = 1
        for x_dot in range(0, 320, 8):
            v_pos.x = x_dot
            v_pos.y = limit_y
            _draw.fill_rectangle(v_pos, v_size, s.c_err)
        v_pos.x = 180
        v_pos.y = limit_y - 12
        _draw.text(v_pos, 'LIMIT: {}'.format(int(_max_rpm)), s.c_err)
    v_pos.x = 0
    v_pos.y = 282
    v_size.x = 320
    v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5
    v_pos.y = 295
    _draw.text(v_pos, '[BACK] RETURN TO TOOLBOX', s.c_sec)
    _draw.swap()


def _draw_toolbox(view_manager):
    s = state
    v_pos = Vector(0, 0)
    v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5
    v_pos.y = 5
    _draw.text(v_pos, 'SHOP TOOLBOX', s.c_fg)
    v_pos.x = 0
    v_pos.y = 22
    v_size.x = 320
    v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    cat_x = 5
    cat_y_start = 30
    cat_line_h = 20
    for i, (cat_name, _) in enumerate(TOOLBOX_MENU):
        y = cat_y_start + i * cat_line_h
        color = s.c_hlt if i == s.sel_tb_cat else s.c_fg
        if s.sel_tb_col == 0 and i == s.sel_tb_cat:
            v_pos.x, v_pos.y = cat_x, y
            _draw.text(v_pos, '> {}'.format(cat_name), color)
        else:
            v_pos.x, v_pos.y = cat_x + 10, y
            _draw.text(v_pos, cat_name, color)
    v_pos.x = 140
    v_pos.y = 25
    v_size.x = 1
    v_size.y = 270
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    item_x = 150
    item_y_start = 30
    item_line_h = 18
    if s.sel_tb_cat < len(TOOLBOX_MENU):
        selected_category_items = TOOLBOX_MENU[s.sel_tb_cat][1]
    else:
        selected_category_items = []
    for i, (item_name, _) in enumerate(selected_category_items):
        y = item_y_start + i * item_line_h
        color = s.c_hlt if i == s.sel_tb_item else s.c_fg
        if s.sel_tb_col == 1 and i == s.sel_tb_item:
            v_pos.x, v_pos.y = item_x, y
            _draw.text(v_pos, '> {}'.format(item_name), color)
        else:
            v_pos.x, v_pos.y = item_x + 10, y
            _draw.text(v_pos, item_name, color)
    back_y = 295
    back_color = s.c_hlt if s.sel_tb_cat == len(TOOLBOX_MENU) else s.c_fg
    if s.sel_tb_col == 0 and s.sel_tb_cat == len(TOOLBOX_MENU):
        v_pos.x = cat_x
        v_pos.y = back_y
        _draw.text(v_pos, '> < RETURN TO MAIN', back_color)
    else:
        v_pos.x = cat_x + 10
        v_pos.y = back_y
        _draw.text(v_pos, '< RETURN TO MAIN', back_color)
    _draw.swap()


def _draw_options(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'PERSONALIZATION', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        v_pos.y = 40 + i * 25
        c = s.c_hlt if i == s.sel_opt else s.c_fg
        if i == s.sel_opt: v_pos.x = 5; _draw.text(v_pos, '>', c)
        v_pos.x = 20; _draw.text(v_pos, row, c)
    _draw.swap()


def _draw_tool_mgr(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'TOOL MANAGER', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        v_pos.y = 40 + i * 25
        c = s.c_hlt if i == s.sel_tm else s.c_fg
        if i == s.sel_tm: v_pos.x = 5; _draw.text(v_pos, '>', c)
        v_pos.x = 20; _draw.text(v_pos, row, c)
    _draw.swap()


def _draw_taper(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'TAPER ANGLE CALCULATOR', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_tp else s.c_fg
        if i == s.sel_tp: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'REQUIRED COMPOUND SETTING:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    v_pos.x = 5; v_pos.y = 235; _draw.text(v_pos, '(Angle from centerline)', s.c_fg)
    _draw.swap()


def _draw_thread(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'THREADING ASSISTANT (60 DEG)', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_th else s.c_fg
        if i == s.sel_th: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'RESULTS:', s.c_ok)
    v_pos.x = 5; v_pos.y = 195; _draw.text(v_pos, s.ui_res, s.c_fg)
    v_pos.x = 5; v_pos.y = 215; _draw.text(v_pos, 'PASS 1: {:.3f} | PASS N: {:.3f}'.format(s.th_pass_1, s.th_pass_n), s.c_fg)
    v_pos.x = 5; v_pos.y = 235; _draw.text(v_pos, 'NOTE: Compound set at 29.5 deg', s.c_fg)
    _draw.swap()


def _draw_convert(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'UNIT CONVERTER', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_cv else s.c_fg
        if i == s.sel_cv: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'RESULT:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    v_pos.x = 5; v_pos.y = 235; _draw.text(v_pos, 'FRAC : {}'.format(s.cv_frac), s.c_fg)
    _draw.swap()


def _draw_wire(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, '3-WIRE PITCH CHECK', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_wr else s.c_fg
        if i == s.sel_wr: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'CALCULATED DIMENSIONS:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    v_pos.x = 5; v_pos.y = 235; _draw.text(v_pos, '(Using 60 deg thread profile)', s.c_fg)
    _draw.swap()


def _draw_weight(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'STOCK WEIGHT CALCULATOR', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_wt else s.c_fg
        if i == s.sel_wt: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'ESTIMATED MASS:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    _draw.swap()


def _draw_speed(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'SPEEDS & FEEDS CALC', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_sp else s.c_fg
        if i == s.sel_sp: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'IDEAL SPEED:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    _draw.swap()


def _draw_bolt_circle(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'BOLT CIRCLE CALCULATOR', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        v_pos.y = 40 + i * 25
        c = s.c_hlt if i == s.sel_bc else s.c_fg
        if i == s.sel_bc: v_pos.x = 5; _draw.text(v_pos, '>', c)
        v_pos.x = 20; _draw.text(v_pos, row, c)
    v_pos.x = 0; v_pos.y = 125; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 135; _draw.text(v_pos, 'HOLE COORDINATES (X, Y):', s.c_ok)
    _vis, _lh, _sy = 6, 20, 160
    s.bc_scroll_pos = min(s.bc_scroll_pos, max(0, len(s.bc_results) - _vis))
    v_pos.x = 10
    for i in range(_vis):
        _idx = s.bc_scroll_pos + i
        if _idx < len(s.bc_rows):
            v_pos.y = _sy + i * _lh; _draw.text(v_pos, s.bc_rows[_idx], s.c_fg)
    _draw.swap()


def _draw_gears(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'CHANGE GEAR CALCULATOR', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        v_pos.y = 40 + i * 25
        c = s.c_hlt if i == s.sel_gr else s.c_fg
        if i == s.sel_gr: v_pos.x = 5; _draw.text(v_pos, '>', c)
        v_pos.x = 20; _draw.text(v_pos, row, c)
    v_pos.x = 0; v_pos.y = 150; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 160; _draw.text(v_pos, 'POSSIBLE GEAR COMBINATIONS:', s.c_ok)
    if not s.gr_results:
        v_pos.x = 10; v_pos.y = 185; _draw.text(v_pos, 'No solutions found.', s.c_warn)
    else:
        for i, res in enumerate(s.gr_results):
            if i < 5: v_pos.x = 10; v_pos.y = 185 + i * 20; _draw.text(v_pos, res, s.c_fg)
    _draw.swap()


def _draw_triangle(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'RIGHT TRIANGLE SOLVER', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        v_pos.y = 40 + i * 25
        c = s.c_hlt if i == s.sel_tr else s.c_fg
        if i == s.sel_tr: v_pos.x = 5; _draw.text(v_pos, '>', c)
        v_pos.x = 20; _draw.text(v_pos, row, c)
    v_pos.x = 0; v_pos.y = 150; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 160; _draw.text(v_pos, 'RESULTS:', s.c_ok)
    v_pos.x = 10; v_pos.y = 185; _draw.text(v_pos, 'Side A : {}'.format(round(s.tr_A, 4)), s.c_fg)
    v_pos.x = 10; v_pos.y = 205; _draw.text(v_pos, 'Side B : {}'.format(round(s.tr_B, 4)), s.c_fg)
    v_pos.x = 10; v_pos.y = 225; _draw.text(v_pos, 'Side C : {}'.format(round(s.tr_C, 4)), s.c_fg)
    v_pos.x = 160; v_pos.y = 185; _draw.text(v_pos, 'Ang(a): {} DEG'.format(round(s.tr_ang_a, 3)), s.c_fg)
    v_pos.x = 160; v_pos.y = 205; _draw.text(v_pos, 'Ang(b): {} DEG'.format(round(s.tr_ang_b, 3)), s.c_fg)
    v_pos.x = 160; v_pos.y = 225; _draw.text(v_pos, 'Ang(c): 90 DEG', s.c_fg)
    _draw.swap()


def _draw_arc(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'ARC / CHORD CALCULATOR', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_ar else s.c_fg
        if i == s.sel_ar: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'RESULTS:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    _draw.swap()


def _draw_drill_pt(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'DRILL POINT DEPTH CALC', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_dp else s.c_fg
        if i == s.sel_dp: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'POINT DEPTH (X):', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    _draw.swap()


def _draw_tap_hole(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0); _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, 'TAP DRILL CALCULATOR', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i, row in enumerate(s.ui_rows):
        _y = 40 + i * 25; v_pos.y = _y
        color = s.c_hlt if i == s.sel_td else s.c_fg
        if i == s.sel_td: v_pos.x = 5; _draw.text(v_pos, '>', color)
        v_pos.x = 20; _draw.text(v_pos, row, color)
    v_pos.x = 0; v_pos.y = 160; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 175; _draw.text(v_pos, 'RECOMMENDED DRILL:', s.c_ok)
    v_pos.x = 5; v_pos.y = 205; _draw.text(v_pos, s.ui_res, s.c_fg)
    _draw.swap()


def _draw_calc(view_manager):
    s = state
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    _draw = view_manager.draw
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5
    _draw.text(v_pos, 'LATHE-CALC v2.1', s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 155; v_pos.y = 30; v_size.x = 1; v_size.y = 150
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    for i in range(7):
        v_pos.y = 32 + i * 21
        if i == s.sel_main:
            v_pos.x = 2; _draw.text(v_pos, '>', s.c_hlt)
            v_pos.x = 12; _draw.text(v_pos, s.ui_left[i], s.c_hlt)
        else:
            v_pos.x = 12; _draw.text(v_pos, s.ui_left[i], s.c_fg)
        r_idx = i + 7
        if r_idx < 14:
            _rf_color = s.c_err if r_idx == FIELD_FEED and s.warn_high_feed else s.c_hlt if r_idx == s.sel_main else s.c_fg
            if r_idx == s.sel_main:
                v_pos.x = 160; _draw.text(v_pos, '>', _rf_color)
                v_pos.x = 170; _draw.text(v_pos, s.ui_right[i], _rf_color)
            else:
                v_pos.x = 170; _draw.text(v_pos, s.ui_right[i], _rf_color)
    v_pos.x = 0; v_pos.y = 182; v_size.x = 320; v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 186
    _draw.text(v_pos, 'SPINDLE (RPM)', s.c_ok)
    if s.warn_coolant:
        v_pos.x = 108; v_pos.y = 184; v_size.x = 44; v_size.y = 11
        _draw.fill_round_rectangle(v_pos, v_size, 4, s.c_sec)
        v_pos.x = 112; v_pos.y = 186; _draw.text(v_pos, 'FLUID', s.c_bg)
    v_pos.x = 160; v_pos.y = 186
    _draw.text(v_pos, 'FEED(mm/m)' if s.val_unit == UNIT_METRIC else 'FEED(in/m)', s.c_ok)
    v_pos.x = 5; v_pos.y = 202
    _draw.text(v_pos, s.ui_rpm, s.c_warn if s.warn_rpm_cap else s.c_fg)
    v_pos.x = 160; v_pos.y = 202
    _draw.text(v_pos, s.ui_feed_m, s.c_err if s.warn_high_feed else s.c_fg)
    v_pos.x = 0; v_pos.y = 216; v_size.x = 320; v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    v_pos.x = 5; v_pos.y = 221
    _draw.text(v_pos, s.ui_pwr, s.c_err if s.warn_power_cap else s.c_fg)
    v_pos.x = 160; v_pos.y = 221
    _draw.text(v_pos, s.ui_time, s.c_err if s.warn_high_feed else s.c_hlt)
    v_pos.x = 5; v_pos.y = 237
    _draw.text(v_pos, s.ui_ra, s.c_warn if s.warn_poor_finish else s.c_fg)
    v_pos.x = 160; v_pos.y = 237
    _draw.text(v_pos, s.ui_max_doc, s.c_fg)
    v_pos.x = 0; v_pos.y = 253; v_size.x = 320; v_size.y = 1
    _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    _y_warn = 259
    if s.warn_rpm_cap:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, s.ui_rpm_warn, s.c_warn)
        _y_warn += 11
    if s.warn_carbide_spd:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, '! DIAM TOO SML FOR CARBIDE', s.c_err)
        _y_warn += 11
    if s.warn_high_feed:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, '! LINEAR FEED EXCEEDED', s.c_err)
        _y_warn += 11
    if s.warn_poor_finish:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, '! POOR SURFACE FINISH', s.c_warn)
        _y_warn += 11
    if s.warn_power_cap:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, '! MOTOR POWER EXCEEDED', s.c_err)
    _draw.swap()


def run(view_manager):
    global dirty_save, save_timer
    s = state
    from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER
    _im = view_manager.input_manager
    _btn = _im.button
    _needs_redraw = False
    if dirty_save and _btn == -1:
        if save_timer > 0:
            save_timer -= 1
        else:
            save_settings(view_manager)
    if s.current_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL,
        SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE,
        SCREEN_FITS, SCREEN_HELP, SCREEN_KNURL, SCREEN_HARDNESS):
        if _btn == BUTTON_BACK:
            s.current_screen = (SCREEN_TOOLBOX if s.current_screen !=
                SCREEN_HELP else SCREEN_CALC)
            _calculate()
            s.text_lines = []
            gc.collect()
            _im.reset()
            _draw_ui(view_manager)
        elif _btn == BUTTON_UP:
            if s.scroll_pos > 0:
                s.scroll_pos -= 1
                _needs_redraw = True
        elif _btn == BUTTON_DOWN:
            if s.scroll_pos < len(s.text_lines) - 16:
                s.scroll_pos += 1
                _needs_redraw = True
        if _needs_redraw:
            _im.reset()
            _draw_ui(view_manager)
        return
    if s.is_typing:
        kb = view_manager.keyboard
        if not kb.is_finished:
            if kb.run(True, s.kb_force) is False:
                s.is_typing = False
                s.kb_force = False
                kb.reset()
                _im.reset()
                _draw_ui(view_manager)
            s.kb_force = False
        else:
            try:
                if s.current_screen == SCREEN_TOOL_MGR and s.sel_tm in (
                    TM_RENAME, TM_NEW):
                    _str_val = kb.response.strip()
                    if _str_val:
                        if s.sel_tm == TM_RENAME:
                            s.tool_profiles[s.active_tool_idx]['name'
                                ] = _str_val[:12]
                        else:
                            s.tool_profiles.append({'name': _str_val[:12],
                                'type': CUT_HSS, 'rad_m': 0.4, 'rad_i':
                                0.015, 'angle': 0.0})
                            s.active_tool_idx = len(s.tool_profiles) - 1
                else:
                    new_val = float(kb.response)
                    if s.current_screen == SCREEN_CALC:
                        if s.sel_main == FIELD_DIAM:
                            s.val_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_main == FIELD_LEN:
                            s.val_len = max(0.001, min(5000.0, new_val))
                        elif s.sel_main == FIELD_VC:
                            s.val_vc = max(1.0, min(5000.0, new_val))
                        elif s.sel_main == FIELD_FEED:
                            s.val_feed = max(0.0001, min(50.0, new_val))
                        elif s.sel_main == FIELD_DOC:
                            s.val_doc = max(0.0, min(100.0, new_val))
                    elif s.current_screen == SCREEN_TAPER:
                        if s.sel_tp == TP_D:
                            s.tp_D = max(0.001, min(5000.0, new_val))
                        elif s.sel_tp == TP_d:
                            s.tp_d = max(0.001, min(5000.0, new_val))
                        elif s.sel_tp == TP_L:
                            s.tp_L = max(0.001, min(5000.0, new_val))
                    elif s.current_screen == SCREEN_THREAD:
                        if s.sel_th == TH_DIAM:
                            s.th_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_th == TH_PITCH:
                            s.th_pitch = max(0.001, min(100.0, new_val))
                    elif s.current_screen == SCREEN_CONVERT:
                        if s.sel_cv == CV_VAL:
                            s.cv_val = max(0.0, min(10000.0, new_val))
                    elif s.current_screen == SCREEN_WIRE:
                        if s.sel_wr == WR_DIAM:
                            s.wr_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_wr == WR_PITCH:
                            s.wr_pitch = max(0.001, min(100.0, new_val))
                        elif s.sel_wr == WR_WIRE:
                            s.wr_wire = max(0.001, min(100.0, new_val))
                    elif s.current_screen == SCREEN_WEIGHT:
                        if s.sel_wt == WT_DIAM:
                            s.wt_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_wt == WT_LEN:
                            s.wt_len = max(0.001, min(5000.0, new_val))
                    elif s.current_screen == SCREEN_SPEED:
                        if s.sel_sp == SP_DIAM:
                            s.sp_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_sp == SP_VC:
                            s.sp_vc = max(1.0, min(5000.0, new_val))
                    elif s.current_screen == SCREEN_BOLT_CIRCLE:
                        if s.sel_bc == BC_DIAM:
                            s.bc_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_bc == BC_HOLES:
                            s.bc_holes = max(2, min(200, int(new_val)))
                    elif s.current_screen == SCREEN_GEARS:
                        if s.sel_gr == GR_PITCH_CUT:
                            s.gr_pitch_cut = max(0.001, min(100.0, new_val))
                        elif s.sel_gr == GR_PITCH_LS:
                            s.gr_pitch_ls = max(0.001, min(100.0, new_val))
                        elif s.sel_gr == GR_GEARS:
                            s.gr_gears = kb.response.strip()
                    elif s.current_screen == SCREEN_TRIANGLE:
                        if s.sel_tr == TR_V1:
                            s.tr_v1 = max(0.001, min(10000.0, new_val))
                        elif s.sel_tr == TR_V2:
                            s.tr_v2 = max(0.001, min(10000.0, new_val))
                    elif s.current_screen == SCREEN_ARC:
                        if s.sel_ar == AR_RADIUS:
                            s.ar_radius = max(0.001, min(10000.0, new_val))
                        elif s.sel_ar == AR_ANGLE:
                            s.ar_angle = max(0.1, min(360.0, new_val))
                    elif s.current_screen == SCREEN_DRILL_PT:
                        if s.sel_dp == DP_DIAM:
                            s.dp_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_dp == DP_ANGLE:
                            s.dp_angle = max(1.0, min(179.0, new_val))
                    elif s.current_screen == SCREEN_TAP_HOLE:
                        if s.sel_td == TD_DIAM:
                            s.td_diam = max(0.001, min(5000.0, new_val))
                        elif s.sel_td == TD_PITCH:
                            s.td_pitch = max(0.001, min(100.0, new_val))
                    elif s.current_screen == SCREEN_OPTIONS:
                        if s.sel_opt == OPT_FEED_CAP:
                            if s.val_unit == UNIT_METRIC:
                                s.max_feed_m = max(0.1, min(10000.0, new_val))
                            else:
                                s.max_feed_i = max(0.01, min(1000.0, new_val))
                        elif s.sel_opt == OPT_RPM_CAP:
                            if s.val_type == TYPE_HOBBY:
                                s.max_rpm_hobby = max(100, min(50000.0, new_val))
                            else:
                                s.max_rpm_indust = max(100, min(50000.0, new_val))
                        elif s.sel_opt == OPT_MOTOR_PWR:
                            _new_kw = (new_val / 1.34102 if s.val_unit ==
                                UNIT_IMP else new_val)
                            if s.val_type == TYPE_HOBBY:
                                s.motor_kw_hobby = max(0.01, min(1000.0, _new_kw))
                            else:
                                s.motor_kw_indust = max(0.01, min(1000.0, _new_kw))
                        elif s.sel_opt == OPT_MOTOR_EFF:
                            s.motor_eff = max(0.1, min(1.0, new_val / 100.0))
                    elif s.current_screen == SCREEN_TOOL_MGR:
                        if s.sel_tm == TM_RAD:
                            if s.val_unit == UNIT_METRIC:
                                s.tool_profiles[s.active_tool_idx]['rad_m'
                                    ] = max(0.001, new_val)
                            else:
                                s.tool_profiles[s.active_tool_idx]['rad_i'
                                    ] = max(0.001, new_val)
                        elif s.sel_tm == TM_ANGLE:
                            s.tool_profiles[s.active_tool_idx]['angle'
                                ] = new_val
                _calculate()
                save_settings(view_manager, force=True)
            except Exception:
                pass
            s.is_typing = False
            s.kb_force = False
            kb.reset()
            _im.reset()
            _draw_ui(view_manager)
        return
    if _btn == BUTTON_BACK:
        if s.current_screen == SCREEN_CALC:
            _im.reset()
            view_manager.back()
        else:
            s.current_screen = SCREEN_TOOLBOX if s.current_screen in (
                SCREEN_TAPER, SCREEN_THREAD, SCREEN_CONVERT, SCREEN_OPTIONS,
                SCREEN_TOOL_MGR, SCREEN_WIRE, SCREEN_WEIGHT, SCREEN_SPEED,
                SCREEN_GEARS, SCREEN_BOLT_CIRCLE, SCREEN_TRIANGLE,
                SCREEN_ARC, SCREEN_DRILL_PT, SCREEN_GRAPH, SCREEN_TAP_HOLE
                ) else SCREEN_CALC
            _calculate()
            _im.reset()
            _draw_ui(view_manager)
        return
    if s.current_screen == SCREEN_TOOLBOX:
        num_cats = len(TOOLBOX_MENU)
        if _btn == BUTTON_DOWN:
            if s.sel_tb_col == 0:
                s.sel_tb_cat = (s.sel_tb_cat + 1) % (num_cats + 1)
                s.sel_tb_item = 0
            elif s.sel_tb_cat < num_cats:
                num_items = len(TOOLBOX_MENU[s.sel_tb_cat][1])
                if num_items > 0:
                    s.sel_tb_item = (s.sel_tb_item + 1) % num_items
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            if s.sel_tb_col == 0:
                s.sel_tb_cat = (s.sel_tb_cat - 1) % (num_cats + 1)
                s.sel_tb_item = 0
            elif s.sel_tb_cat < num_cats:
                num_items = len(TOOLBOX_MENU[s.sel_tb_cat][1])
                if num_items > 0:
                    s.sel_tb_item = (s.sel_tb_item - 1) % num_items
            _needs_redraw = True
        elif _btn == BUTTON_RIGHT:
            if s.sel_tb_col == 0 and s.sel_tb_cat < num_cats:
                s.sel_tb_col = 1
                _needs_redraw = True
        elif _btn == BUTTON_LEFT:
            if s.sel_tb_col == 1:
                s.sel_tb_col = 0
                _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tb_col == 0:
                if s.sel_tb_cat == num_cats:
                    s.current_screen = SCREEN_CALC
                    _calculate()
                else:
                    s.sel_tb_col = 1
            elif s.sel_tb_cat < num_cats:
                num_items = len(TOOLBOX_MENU[s.sel_tb_cat][1])
                if num_items > 0:
                    target_screen = TOOLBOX_MENU[s.sel_tb_cat][1][s.sel_tb_item
                        ][1]
                if target_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL,
                    SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR,
                    SCREEN_SURFACE, SCREEN_FITS, SCREEN_KNURL, SCREEN_HARDNESS
                    ):
                    text_map = {SCREEN_CHART: 'CHART', SCREEN_TAP: 'TAP',
                        SCREEN_DRILL: 'DRILL', SCREEN_CENTER: 'CENTER',
                        SCREEN_MORSE: 'MORSE', SCREEN_CLEAR: 'CLEAR',
                        SCREEN_SURFACE: 'SURFACE', SCREEN_FITS: 'FITS',
                        SCREEN_KNURL: 'KNURL', SCREEN_HARDNESS: 'HARDNESS'}
                    s.current_screen = target_screen
                    _load_text(text_map[target_screen])
                else:
                    s.current_screen = target_screen
            _calculate()
            _needs_redraw = True
    elif s.current_screen == SCREEN_OPTIONS:
        if _btn == BUTTON_DOWN:
            s.sel_opt = (s.sel_opt + 1) % 8
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_opt = (s.sel_opt - 1) % 8
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            if s.sel_opt == OPT_THEME:
                _dir = 1 if _btn == BUTTON_RIGHT else -1
                s.theme_id = (s.theme_id + _dir) % 4
                _apply_theme()
                queue_save()
                _needs_redraw = True
            elif s.sel_opt == OPT_FEED_CAP:
                if s.val_unit == UNIT_METRIC:
                    s.max_feed_m = max(10.0, s.max_feed_m + (10.0 if _btn ==
                        BUTTON_RIGHT else -10.0))
                else:
                    s.max_feed_i = max(1.0, s.max_feed_i + (1.0 if _btn ==
                        BUTTON_RIGHT else -1.0))
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_opt == OPT_RPM_CAP:
                _adj = 100.0 if _btn == BUTTON_RIGHT else -100.0
                if s.val_type == TYPE_HOBBY:
                    s.max_rpm_hobby = max(100.0, s.max_rpm_hobby + _adj)
                else:
                    s.max_rpm_indust = max(100.0, s.max_rpm_indust + _adj)
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_opt == OPT_RA_DISP:
                s.ra_as_ngrade = not s.ra_as_ngrade
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_opt == OPT_MOTOR_EFF:
                s.motor_eff = max(0.1, min(1.0, s.motor_eff + (0.05 if _btn ==
                    BUTTON_RIGHT else -0.05)))
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_opt == OPT_AUTO_DOC:
                s.auto_rec_doc = not s.auto_rec_doc
                _calculate()
                queue_save()
                _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_opt == OPT_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_opt == OPT_FEED_CAP:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'MAX FEED LIMIT'
                kb.response = str(s.max_feed_m if s.val_unit == UNIT_METRIC
                     else s.max_feed_i)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
            elif s.sel_opt == OPT_RPM_CAP:
                kb = view_manager.keyboard
                kb.reset()
                _sys_str = 'HOBBY' if s.val_type == TYPE_HOBBY else 'INDUST'
                kb.title = 'MAX RPM (' + _sys_str + ')'
                kb.response = str(int(s.max_rpm_hobby if s.val_type ==
                    TYPE_HOBBY else s.max_rpm_indust))
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
            elif s.sel_opt == OPT_MOTOR_PWR:
                kb = view_manager.keyboard
                kb.reset()
                _sys_str = 'HOBBY' if s.val_type == TYPE_HOBBY else 'INDUST'
                _pwr_u = 'HP' if s.val_unit == UNIT_IMP else 'kW'
                _pwr_kw = (s.motor_kw_hobby if s.val_type == TYPE_HOBBY else
                    s.motor_kw_indust)
                _pwr_disp = round(_pwr_kw * 1.34102, 2
                    ) if s.val_unit == UNIT_IMP else round(_pwr_kw, 2)
                kb.title = 'MOTOR POWER (' + _sys_str + ' ' + _pwr_u + ')'
                kb.response = str(_pwr_disp)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
            elif s.sel_opt == OPT_MOTOR_EFF:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'MOTOR EFFICIENCY (%)'
                kb.response = str(int(s.motor_eff * 100))
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_TOOL_MGR:
        if _btn == BUTTON_DOWN:
            s.sel_tm = (s.sel_tm + 1) % 8
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_tm = (s.sel_tm - 1) % 8
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1 if _btn == BUTTON_RIGHT else -1
            if s.sel_tm == TM_SELECT:
                s.active_tool_idx = (s.active_tool_idx + _dir) % len(s.
                    tool_profiles)
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_tm == TM_TYPE:
                s.tool_profiles[s.active_tool_idx]['type'
                    ] = CUT_CARB if s.tool_profiles[s.active_tool_idx]['type'
                    ] == CUT_HSS else CUT_HSS
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_tm == TM_RAD:
                if s.val_unit == UNIT_METRIC:
                    new_rad = s.tool_profiles[s.active_tool_idx]['rad_m'
                        ] + 0.1 * _dir
                    s.tool_profiles[s.active_tool_idx]['rad_m'] = round(max
                        (0.001, new_rad), 3)
                else:
                    new_rad = s.tool_profiles[s.active_tool_idx]['rad_i'
                        ] + 0.005 * _dir
                    s.tool_profiles[s.active_tool_idx]['rad_i'] = round(max
                        (0.001, new_rad), 4)
                _calculate()
                queue_save()
                _needs_redraw = True
            elif s.sel_tm == TM_ANGLE:
                new_ang = s.tool_profiles[s.active_tool_idx].get('angle', 0.0
                    ) + 1.0 * _dir
                s.tool_profiles[s.active_tool_idx]['angle'] = round(new_ang, 1)
                _calculate()
                queue_save()
                _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tm == TM_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_tm == TM_NEW:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'NEW TOOL NAME'
                kb.response = 'Tool ' + str(len(s.tool_profiles) + 1)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
            elif s.sel_tm == TM_RENAME:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'RENAME TOOL'
                kb.response = s.tool_profiles[s.active_tool_idx]['name']
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
            elif s.sel_tm == TM_DEL:
                if len(s.tool_profiles) > 1:
                    s.tool_profiles.pop(s.active_tool_idx)
                    s.active_tool_idx = max(0, s.active_tool_idx - 1)
                    _calculate()
                    queue_save()
                    _needs_redraw = True
            elif s.sel_tm == TM_RAD:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'NOSE RADIUS'
                kb.response = str(s.tool_profiles[s.active_tool_idx][
                    'rad_m'] if s.val_unit == UNIT_METRIC else s.
                    tool_profiles[s.active_tool_idx]['rad_i'])
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
            elif s.sel_tm == TM_ANGLE:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'TOOL ANGLE (DEG)'
                kb.response = str(s.tool_profiles[s.active_tool_idx].get(
                    'angle', 0.0))
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_GEARS:
        if _btn == BUTTON_DOWN:
            s.sel_gr = (s.sel_gr + 1) % 4
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_gr = (s.sel_gr - 1) % 4
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _step = 0.05 if s.val_unit == UNIT_METRIC else 1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_gr == GR_PITCH_CUT:
                s.gr_pitch_cut = round(max(0.01, s.gr_pitch_cut + _dir *
                    _step), _rnd)
            elif s.sel_gr == GR_PITCH_LS:
                s.gr_pitch_ls = round(max(0.01, s.gr_pitch_ls + _dir *
                    _step), _rnd)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_gr == GR_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            else:
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_gr == GR_PITCH_CUT:
                    kb.title = 'PITCH TO CUT'
                    kb.response = str(s.gr_pitch_cut)
                elif s.sel_gr == GR_PITCH_LS:
                    kb.title = 'LEADSCREW PITCH'
                    kb.response = str(s.gr_pitch_ls)
                elif s.sel_gr == GR_GEARS:
                    kb.title = 'AVAILABLE GEARS (CSV)'
                    kb.response = s.gr_gears
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_BOLT_CIRCLE:
        if _btn == BUTTON_DOWN:
            if s.sel_bc < 2:
                s.sel_bc += 1
            else:
                s.bc_scroll_pos = min(s.bc_scroll_pos + 1, max(0, len(s.
                    bc_results) - 6))
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            if s.sel_bc > 0:
                s.sel_bc -= 1
            else:
                s.bc_scroll_pos = max(0, s.bc_scroll_pos - 1)
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_bc == BC_DIAM:
                s.bc_diam = round(max(0.001, s.bc_diam + _dir * (1.0 if s.
                    val_unit == UNIT_METRIC else 0.1)), _rnd)
            elif s.sel_bc == BC_HOLES:
                s.bc_holes = max(2, s.bc_holes + int(_dir))
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_bc == BC_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_bc in (BC_DIAM, BC_HOLES):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_bc == BC_DIAM:
                    kb.title = 'CIRCLE DIAMETER'
                    kb.response = str(s.bc_diam)
                else:
                    kb.title = 'NUMBER OF HOLES'
                    kb.response = str(s.bc_holes)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_TRIANGLE:
        if _btn == BUTTON_DOWN:
            s.sel_tr = (s.sel_tr + 1) % 4
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_tr = (s.sel_tr - 1) % 4
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            if s.sel_tr == TR_MODE:
                s.tr_mode = int((s.tr_mode + _dir) % 6)
            elif s.sel_tr == TR_V1:
                s.tr_v1 = max(0.001, s.tr_v1 + _dir * 1.0)
            elif s.sel_tr == TR_V2:
                s.tr_v2 = max(0.001, s.tr_v2 + _dir * 1.0)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tr == TR_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_tr in (TR_V1, TR_V2):
                kb = view_manager.keyboard
                kb.reset()
                _v1_lbls = ['SIDE A', 'SIDE A', 'SIDE B', 'SIDE A',
                    'SIDE B', 'SIDE C']
                _v2_lbls = ['SIDE B', 'SIDE C', 'SIDE C', 'ANGLE a',
                    'ANGLE a', 'ANGLE a']
                if s.sel_tr == TR_V1:
                    kb.title = _v1_lbls[s.tr_mode]
                    kb.response = str(s.tr_v1)
                else:
                    kb.title = _v2_lbls[s.tr_mode]
                    kb.response = str(s.tr_v2)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_ARC:
        if _btn == BUTTON_DOWN:
            s.sel_ar = (s.sel_ar + 1) % 3
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_ar = (s.sel_ar - 1) % 3
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_ar == AR_RADIUS:
                s.ar_radius = round(max(0.001, s.ar_radius + _dir * 1.0), _rnd)
            elif s.sel_ar == AR_ANGLE:
                s.ar_angle = round(max(0.001, s.ar_angle + _dir * 1.0), 3)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_ar == AR_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_ar in (AR_RADIUS, AR_ANGLE):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_ar == AR_RADIUS:
                    kb.title = 'RADIUS'
                    kb.response = str(s.ar_radius)
                else:
                    kb.title = 'ANGLE (DEG)'
                    kb.response = str(s.ar_angle)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_DRILL_PT:
        if _btn == BUTTON_DOWN:
            s.sel_dp = (s.sel_dp + 1) % 3
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_dp = (s.sel_dp - 1) % 3
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_dp == DP_DIAM:
                s.dp_diam = round(max(0.001, s.dp_diam + _dir * (1.0 if s.
                    val_unit == UNIT_METRIC else 0.1)), _rnd)
            elif s.sel_dp == DP_ANGLE:
                if s.dp_angle == 118.0 and _dir > 0:
                    s.dp_angle = 135.0
                elif s.dp_angle == 135.0 and _dir < 0:
                    s.dp_angle = 118.0
                else:
                    s.dp_angle = round(max(1.0, min(179.0, s.dp_angle +
                        _dir * 1.0)), 1)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_dp == DP_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_dp in (DP_DIAM, DP_ANGLE):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_dp == DP_DIAM:
                    kb.title = 'DRILL DIAMETER'
                    kb.response = str(s.dp_diam)
                else:
                    kb.title = 'POINT ANGLE (DEG)'
                    kb.response = str(s.dp_angle)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_TAP_HOLE:
        if _btn == BUTTON_DOWN:
            s.sel_td = (s.sel_td + 1) % 3
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_td = (s.sel_td - 1) % 3
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_td == TD_DIAM:
                s.td_diam = round(max(0.001, s.td_diam + _dir * (1.0 if s.
                    val_unit == UNIT_METRIC else 0.1)), _rnd)
            elif s.sel_td == TD_PITCH:
                s.td_pitch = round(max(0.01, s.td_pitch + _dir * (0.1 if s.
                    val_unit == UNIT_METRIC else 1.0)), _rnd)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_td == TD_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_td in (TD_DIAM, TD_PITCH):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_td == TD_DIAM:
                    kb.title = 'MAJOR DIAMETER'
                    kb.response = str(s.td_diam)
                else:
                    kb.title = 'PITCH / TPI'
                    kb.response = str(s.td_pitch)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_TAPER:
        if _btn == BUTTON_DOWN:
            s.sel_tp = (s.sel_tp + 1) % 4
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_tp = (s.sel_tp - 1) % 4
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _st = 1.0 if s.val_unit == UNIT_METRIC else 0.1
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_tp == TP_D:
                s.tp_D = round(max(0.001, s.tp_D + _dir * _st), _rnd)
            elif s.sel_tp == TP_d:
                s.tp_d = round(max(0.001, s.tp_d + _dir * _st), _rnd)
            elif s.sel_tp == TP_L:
                s.tp_L = round(max(0.001, s.tp_L + _dir * _st), _rnd)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tp == TP_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            else:
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_tp == TP_D:
                    kb.title = 'LARGE DIAMETER'
                    kb.response = str(s.tp_D)
                elif s.sel_tp == TP_d:
                    kb.title = 'SMALL DIAMETER'
                    kb.response = str(s.tp_d)
                elif s.sel_tp == TP_L:
                    kb.title = 'TAPER LENGTH'
                    kb.response = str(s.tp_L)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_THREAD:
        if _btn == BUTTON_DOWN:
            s.sel_th = (s.sel_th + 1) % 4
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_th = (s.sel_th - 1) % 4
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.th_type == TH_METRIC else 4
            if s.sel_th == TH_TYPE:
                s.th_type = TH_UNIFIED if s.th_type == TH_METRIC else TH_METRIC
            elif s.sel_th == TH_DIAM:
                s.th_diam = round(max(0.001, s.th_diam + _dir * (1.0 if s.
                    th_type == TH_METRIC else 0.01)), _rnd)
            elif s.sel_th == TH_PITCH:
                s.th_pitch = round(max(0.01, s.th_pitch + _dir * (0.05 if s
                    .th_type == TH_METRIC else 1.0)), _rnd)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_th == TH_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_th in (TH_DIAM, TH_PITCH):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_th == TH_DIAM:
                    kb.title = 'MAJOR DIAMETER'
                    kb.response = str(s.th_diam)
                elif s.sel_th == TH_PITCH:
                    kb.title = 'PITCH / TPI'
                    kb.response = str(s.th_pitch)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_CONVERT:
        if _btn == BUTTON_DOWN:
            s.sel_cv = (s.sel_cv + 1) % 3
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_cv = (s.sel_cv - 1) % 3
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            if s.sel_cv == CV_UNIT:
                s.cv_unit = (UNIT_IMP if s.cv_unit == UNIT_METRIC else
                    UNIT_METRIC)
            elif s.sel_cv == CV_VAL:
                _step = 1.0 if s.cv_unit == UNIT_METRIC else 0.1
                _rnd = 3 if s.cv_unit == UNIT_METRIC else 4
                s.cv_val = round(max(0.001, s.cv_val + (1.0 if _btn ==
                    BUTTON_RIGHT else -1.0) * _step), _rnd)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_cv == CV_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_cv == CV_VAL:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = 'CONVERT VALUE'
                kb.response = str(s.cv_val)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_WIRE:
        if _btn == BUTTON_DOWN:
            s.sel_wr = (s.sel_wr + 1) % 5
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_wr = (s.sel_wr - 1) % 5
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.wr_type == TH_METRIC else 4
            if s.sel_wr == WR_TYPE:
                s.wr_type = TH_UNIFIED if s.wr_type == TH_METRIC else TH_METRIC
            elif s.sel_wr == WR_DIAM:
                s.wr_diam = round(max(0.001, s.wr_diam + _dir * (1.0 if s.
                    wr_type == TH_METRIC else 0.01)), _rnd)
            elif s.sel_wr == WR_PITCH:
                s.wr_pitch = round(max(0.01, s.wr_pitch + _dir * (0.05 if s
                    .wr_type == TH_METRIC else 1.0)), _rnd)
            elif s.sel_wr == WR_WIRE:
                s.wr_wire = round(max(0.001, s.wr_wire + _dir * (0.1 if s.
                    wr_type == TH_METRIC else 0.005)), _rnd + 1)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_wr == WR_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_wr in (WR_DIAM, WR_PITCH, WR_WIRE):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_wr == WR_DIAM:
                    kb.title = 'MAJOR DIAMETER'
                    kb.response = str(s.wr_diam)
                elif s.sel_wr == WR_PITCH:
                    kb.title = 'PITCH / TPI'
                    kb.response = str(s.wr_pitch)
                elif s.sel_wr == WR_WIRE:
                    kb.title = 'WIRE DIAMETER'
                    kb.response = str(s.wr_wire)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_WEIGHT:
        if _btn == BUTTON_DOWN:
            s.sel_wt = (s.sel_wt + 1) % 4
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_wt = (s.sel_wt - 1) % 4
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_wt == WT_MATL:
                s.wt_matl = int((s.wt_matl + _dir) % 8)
            elif s.sel_wt == WT_DIAM:
                s.wt_diam = round(max(0.001, s.wt_diam + _dir * (1.0 if s.
                    val_unit == UNIT_METRIC else 0.1)), _rnd)
            elif s.sel_wt == WT_LEN:
                s.wt_len = round(max(0.001, s.wt_len + _dir * (5.0 if s.
                    val_unit == UNIT_METRIC else 0.5)), _rnd)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_wt == WT_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_wt in (WT_DIAM, WT_LEN):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_wt == WT_DIAM:
                    kb.title = 'STOCK DIAMETER'
                    kb.response = str(s.wt_diam)
                elif s.sel_wt == WT_LEN:
                    kb.title = 'STOCK LENGTH'
                    kb.response = str(s.wt_len)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_SPEED:
        if _btn == BUTTON_DOWN:
            s.sel_sp = (s.sel_sp + 1) % 3
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_sp = (s.sel_sp - 1) % 3
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_sp == SP_DIAM:
                s.sp_diam = round(max(0.001, s.sp_diam + _dir * (1.0 if s.
                    val_unit == UNIT_METRIC else 0.1)), _rnd)
            elif s.sel_sp == SP_VC:
                s.sp_vc = round(max(1.0, s.sp_vc + _dir * (5.0 if s.
                    val_unit == UNIT_METRIC else 10.0)), 2)
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_sp == SP_BACK:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_sp in (SP_DIAM, SP_VC):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_sp == SP_DIAM:
                    kb.title = 'DIAMETER'
                    kb.response = str(s.sp_diam)
                elif s.sel_sp == SP_VC:
                    kb.title = 'CUTTING SPEED'
                    kb.response = str(s.sp_vc)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    elif s.current_screen == SCREEN_CALC:
        if _btn == BUTTON_DOWN:
            s.sel_main = (s.sel_main + 1) % 14
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            s.sel_main = (s.sel_main - 1) % 14
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            if s.sel_main == FIELD_UNIT:
                s.val_unit = (UNIT_IMP if s.val_unit == UNIT_METRIC else
                    UNIT_METRIC)
                if s.val_unit == UNIT_IMP:
                    s.val_diam = round(s.val_diam / 25.4, 4)
                    s.val_len = round(s.val_len / 25.4, 4)
                else:
                    s.val_diam = round(s.val_diam * 25.4, 2)
                    s.val_len = round(s.val_len * 25.4, 2)
            elif s.sel_main == FIELD_CUTTER:
                s.active_tool_idx = (s.active_tool_idx + int(_dir)) % len(s
                    .tool_profiles)
            elif s.sel_main == FIELD_WORK:
                s.val_work = (s.val_work + int(_dir)) % 11
            elif s.sel_main == FIELD_TYPE:
                s.val_type = (TYPE_INDUST if s.val_type == TYPE_HOBBY else
                    TYPE_HOBBY)
            elif s.sel_main == FIELD_PROC:
                s.val_proc = (s.val_proc + int(_dir)) % 6
            elif s.sel_main == FIELD_PASS:
                s.val_pass = (PASS_FINISH if s.val_pass == PASS_ROUGH else
                    PASS_ROUGH)
            elif s.sel_main == FIELD_DIAM:
                _rnd = 3 if s.val_unit == UNIT_METRIC else 4
                s.val_diam = round(min(5000.0, max(0.001, s.val_diam + _dir * (1.0 if s
                    .val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_main == FIELD_LEN:
                _rnd = 3 if s.val_unit == UNIT_METRIC else 4
                s.val_len = round(min(5000.0, max(0.001, s.val_len + _dir * (5.0 if s.
                    val_unit == UNIT_METRIC else 0.5))), _rnd)
            elif s.sel_main == FIELD_VC:
                s.val_vc = round(max(1.0, s.val_vc + _dir * (5.0 if s.
                    val_unit == UNIT_METRIC else 10.0)), 2)
            elif s.sel_main == FIELD_FEED:
                s.val_feed = min(50.0, max(0.001, s.val_feed + _dir * (0.01 if s.
                    val_unit == UNIT_METRIC else 0.001)))
                s.val_feed = round(s.val_feed, 4)
            elif s.sel_main == FIELD_DOC:
                s.val_doc = min(100.0, max(0.001, s.val_doc + _dir * (0.1 if s.
                    val_unit == UNIT_METRIC else 0.01)))
                s.val_doc = round(s.val_doc, 3)
            if s.sel_main in (FIELD_UNIT, FIELD_CUTTER, FIELD_WORK,
                FIELD_TYPE, FIELD_PROC, FIELD_PASS):
                _apply_safe_defaults()
            _calculate()
            queue_save()
            _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_main == FIELD_MAIN_TOOLBOX:
                s.current_screen = SCREEN_TOOLBOX
                _calculate()
                _needs_redraw = True
            elif s.sel_main == FIELD_MAIN_HELP:
                s.current_screen = SCREEN_HELP
                _load_text('HELP')
                _calculate()
                _needs_redraw = True
            elif s.sel_main == FIELD_APPLY_DOC:
                _str = s.rec_doc.replace('mm', '').replace('in', '').replace(
                    '+', '')
                try:
                    if '-' in _str:
                        _parts = _str.split('-')
                        s.val_doc = round((float(_parts[0]) + float(_parts[
                            1])) / 2.0, 4)
                    else:
                        s.val_doc = round(float(_str), 4)
                    _calculate()
                    queue_save()
                    _needs_redraw = True
                except Exception:
                    pass
            elif s.sel_main in (FIELD_DIAM, FIELD_LEN, FIELD_VC, FIELD_FEED,
                FIELD_DOC):
                kb = view_manager.keyboard
                kb.reset()
                _u_d = 'mm' if s.val_unit == UNIT_METRIC else 'in'
                _u_v = 'm/m' if s.val_unit == UNIT_METRIC else 'SFM'
                _u_f = 'mm/r' if s.val_unit == UNIT_METRIC else 'in/r'
                if s.sel_main == FIELD_DIAM:
                    _t_title = ('DRILL DIAMETER' if s.val_proc ==
                        PROC_DRILL else 'DIAMETER')
                    kb.title = _t_title + ' (' + _u_d + ')'
                    kb.response = str(s.val_diam)
                elif s.sel_main == FIELD_LEN:
                    kb.title = 'LENGTH (' + _u_d + ')'
                    kb.response = str(s.val_len)
                elif s.sel_main == FIELD_VC:
                    kb.title = 'SPEED (' + _u_v + ')'
                    kb.response = str(s.val_vc)
                elif s.sel_main == FIELD_FEED:
                    kb.title = 'FEED (' + _u_f + ')'
                    kb.response = str(s.val_feed)
                elif s.sel_main == FIELD_DOC:
                    kb.title = 'DEPTH OF CUT (' + _u_d + ')'
                    kb.response = str(s.val_doc)
                s.is_typing = True
                s.kb_force = True
                _im.reset()
                return
    if _needs_redraw:
        _im.reset()
        _draw_ui(view_manager)


def stop(view_manager):
    """Stop the app, execute a final save, and clear memory"""
    from gc import collect
    global state, storage, dirty_save, save_timer, _last_saved_json
    save_settings(view_manager, force=True)
    if view_manager.keyboard:
        view_manager.keyboard.reset()
    del state
    state = None
    storage = None
    dirty_save = False
    save_timer = 0
    _last_saved_json = ''
    collect()