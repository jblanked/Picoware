# ==========================================
# LATHE-CALC v2.1
# ==========================================
# Help Text: Use UP/DOWN to move the cursor.
# Use LEFT/RIGHT to toggle bracketed settings or adjust numbers.
# Press CENTER on a number to manually type exact values.
# Results update instantly on the lower panel!
# Press BACK to exit the application.
# ==========================================

import json
import gc
import math
from picoware.system.vector import Vector

# Constants - Screen States
SCREEN_CALC = 0
SCREEN_TOOLBOX = 1
SCREEN_TAPER = 2
SCREEN_CHART = 3
SCREEN_TAP = 4
SCREEN_HELP = 5
SCREEN_THREAD = 6
SCREEN_CONVERT = 7
SCREEN_OPTIONS = 8
SCREEN_KNURL = 9
SCREEN_DRILL = 10
SCREEN_CENTER = 11
SCREEN_MORSE = 12
SCREEN_CLEAR = 13
SCREEN_SURFACE = 14
SCREEN_FITS = 15
SCREEN_TOOL_MGR = 16
SCREEN_WIRE = 17
SCREEN_WEIGHT = 18
SCREEN_HARDNESS = 19
SCREEN_SPEED = 20
SCREEN_GEARS = 22
SCREEN_BOLT_CIRCLE = 23
SCREEN_TRIANGLE = 24
SCREEN_ARC = 25
SCREEN_DRILL_PT = 26
SCREEN_GRAPH = 27
SCREEN_TAP_HOLE = 28

# Constants - Field States (Main)
FIELD_UNIT = 0; FIELD_TYPE = 1; FIELD_WORK = 2; FIELD_CUTTER = 3; FIELD_PROC = 4; FIELD_PASS = 5; FIELD_APPLY_DOC = 6
FIELD_DIAM = 7; FIELD_LEN = 8; FIELD_VC = 9; FIELD_FEED = 10; FIELD_DOC = 11; FIELD_MAIN_TOOLBOX = 12; FIELD_MAIN_HELP = 13

PROC_NAMES = ["TURN", "FACE", "PART", "CHAMF", "BORE", "DRILL"]
WORK_NAMES = ["ALUM", "BRASS", "MILD ST", "STAINLS", "CST IRN", "PLASTIC", "TITAN", "COPPER", "HI-C ST", "TOOL ST", "SUPERAL"]

# New Toolbox Structure
TOOLBOX_MENU = [
    ("Charts & Refs", [
        ("Vc Ref Charts", SCREEN_CHART),
        ("Tap Sizes", SCREEN_TAP),
        ("Drill Sizes", SCREEN_DRILL),
        ("Center Drills", SCREEN_CENTER),
        ("Morse Tapers", SCREEN_MORSE),
        ("SHCS Clearances", SCREEN_CLEAR),
        ("Surface Finishes", SCREEN_SURFACE),
        ("ISO Fits", SCREEN_FITS),
        ("Knurling Guide", SCREEN_KNURL),
        ("Hardness Chart", SCREEN_HARDNESS),
        ("RPM Bar Chart", SCREEN_GRAPH),
    ]),
    ("Calculators", [
        ("Taper Angle", SCREEN_TAPER),
        ("Threading Assist", SCREEN_THREAD),
        ("Unit Converter", SCREEN_CONVERT),
        ("3-Wire Thread", SCREEN_WIRE),
        ("Stock Weight", SCREEN_WEIGHT),
        ("Speeds & Feeds", SCREEN_SPEED),
        ("Change Gears", SCREEN_GEARS),
        ("Bolt Circle", SCREEN_BOLT_CIRCLE),
        ("Drill Pt Depth", SCREEN_DRILL_PT),
        ("Tap Drill Calc", SCREEN_TAP_HOLE),
        ("Right Triangle", SCREEN_TRIANGLE),
        ("Arc & Chord", SCREEN_ARC),
    ]),
    ("Management", [
        ("Options & Themes", SCREEN_OPTIONS),
        ("Tool Manager", SCREEN_TOOL_MGR),
    ]),
]

# Constants - Field States (Sub-Tools)
TP_D = 0; TP_d = 1; TP_L = 2; TP_BACK = 3
TH_TYPE = 0; TH_DIAM = 1; TH_PITCH = 2; TH_BACK = 3
CV_UNIT = 0; CV_VAL = 1; CV_BACK = 2
WR_TYPE = 0; WR_DIAM = 1; WR_PITCH = 2; WR_WIRE = 3; WR_BACK = 4
WT_MATL = 0; WT_DIAM = 1; WT_LEN = 2; WT_BACK = 3
SP_DIAM = 0; SP_VC = 1; SP_BACK = 2
OPT_THEME = 0; OPT_FEED_CAP = 1; OPT_RPM_CAP = 2; OPT_RA_DISP = 3; OPT_MOTOR_PWR = 4; OPT_MOTOR_EFF = 5; OPT_AUTO_DOC = 6; OPT_BACK = 7
TM_BACK = 0; TM_NEW = 1; TM_DEL = 2; TM_SELECT = 3; TM_RENAME = 4; TM_TYPE = 5; TM_RAD = 6; TM_ANGLE = 7
GR_PITCH_CUT = 0; GR_PITCH_LS = 1; GR_GEARS = 2; GR_BACK = 3
BC_DIAM = 0; BC_HOLES = 1; BC_BACK = 2
TR_MODE = 0; TR_V1 = 1; TR_V2 = 2; TR_BACK = 3
AR_RADIUS = 0; AR_ANGLE = 1; AR_BACK = 2
DP_DIAM = 0; DP_ANGLE = 1; DP_BACK = 2
TD_DIAM = 0; TD_PITCH = 1; TD_BACK = 2

# Constants - Toggles
UNIT_METRIC = 0; UNIT_IMP = 1
CUT_HSS = 0; CUT_CARB = 1
WORK_ALU = 0; WORK_BRASS = 1; WORK_MILD = 2; WORK_STAIN = 3; WORK_CAST = 4; WORK_PLAST = 5; WORK_TITAN = 6; WORK_COPPER = 7; WORK_MED_C = 8; WORK_TOOL_ST = 9; WORK_SUPER = 10
TYPE_HOBBY = 0; TYPE_INDUST = 1
PROC_TURN = 0; PROC_FACE = 1; PROC_PART = 2; PROC_CHAMFER = 3; PROC_BORE = 4; PROC_DRILL = 5
PASS_ROUGH = 0; PASS_FINISH = 1
TH_METRIC = 0; TH_UNIFIED = 1

MAX_LATHE_RPM_HOBBY = 2500.0
MAX_LATHE_RPM_INDUST = 6000.0

# Storage Constants
_SETTINGS_FILE = "picoware/settings/lathecalc_settings.json"
storage = None
dirty_save = False
save_timer = 0
_last_saved_json = ""

class AppState:
    '''Encapsulates all application variables to avoid global namespace pollution'''
    def __init__(self):
        self.current_screen = SCREEN_CALC
        
        self.sel_main = FIELD_UNIT
        self.sel_tb_col = 0 # 0=Category, 1=Item
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
        
        # UI Themes
        self.theme_id = 0
        self.c_bg = 0
        self.c_fg = 0
        self.c_hlt = 0
        self.c_ok = 0
        self.c_warn = 0
        self.c_err = 0
        self.c_sec = 0
        
        # Main Calc
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
        self.time_result = "0m 0s"
        self.ra_result_str = ""
        self.pwr_result_str = ""
        self.rec_doc = ""
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
        
        self.tool_profiles = [
            {"name": "Gen HSS", "type": CUT_HSS, "rad_m": 0.4, "rad_i": 0.015, "angle": 0.0},
            {"name": "Gen CARB", "type": CUT_CARB, "rad_m": 0.8, "rad_i": 0.031, "angle": 0.0}
        ]
        self.active_tool_idx = 0
        
        # Sub-Tools
        self.tp_D = 20.0; self.tp_d = 15.0; self.tp_L = 50.0; self.tp_angle = 0.0
        self.th_type = TH_METRIC; self.th_diam = 12.0; self.th_pitch = 1.75; self.th_minor = 0.0; self.th_infeed = 0.0
        self.th_pass_1 = 0.0; self.th_pass_n = 0.0
        self.cv_unit = UNIT_METRIC; self.cv_val = 10.0; self.cv_mm = 0.0; self.cv_inch = 0.0; self.cv_frac = ""
        self.wr_type = TH_METRIC; self.wr_diam = 12.0; self.wr_pitch = 1.75; self.wr_wire = 1.0; self.wr_result = 0.0; self.wr_best = 0.0
        self.wt_matl = 0; self.wt_diam = 25.4; self.wt_len = 100.0; self.wt_result = 0.0
        self.sp_diam = 25.4; self.sp_vc = 30.0; self.sp_rpm = 0.0
        self.gr_pitch_cut = 1.75; self.gr_pitch_ls = 2.0; self.gr_gears = "20,24,30,32,36,40,44,48,50,52,56,60,64,80,100,120,127"
        self.gr_results = []
        self.bc_diam = 50.0; self.bc_holes = 6; self.bc_results = []; self.bc_scroll_pos = 0
        self.tr_mode = 0; self.tr_v1 = 10.0; self.tr_v2 = 10.0
        self.tr_A = 0.0; self.tr_B = 0.0; self.tr_C = 0.0
        self.tr_ang_a = 0.0; self.tr_ang_b = 0.0
        self.ar_radius = 50.0; self.ar_angle = 90.0; self.ar_arc_len = 0.0; self.ar_chord = 0.0
        self.dp_diam = 10.0; self.dp_angle = 118.0; self.dp_result = 0.0
        self.td_diam = 6.0; self.td_pitch = 1.0; self.td_result = 5.0
        
        # System
        self.is_typing = False
        self.kb_force = False
        self.text_lines = []
        self.scroll_pos = 0

state = None

def queue_save():
    '''Flags the system to save data after a brief period of user inactivity'''
    global dirty_save, save_timer
    dirty_save = True
    save_timer = 60

def save_settings(view_manager=None, force=False):
    '''Serializes the user's setup and writes it directly to the SD card'''
    global storage, dirty_save, _last_saved_json
    s = state
    if not storage or not s: return
    if not dirty_save and not force: return
    try:
        save_dict = {
            "theme_id": s.theme_id,
            "val_unit": s.val_unit, "val_work": s.val_work,
            "val_type": s.val_type, "val_proc": s.val_proc, "val_pass": s.val_pass,
            "val_diam": s.val_diam, "val_len": s.val_len, "val_vc": s.val_vc, "val_feed": s.val_feed, "val_doc": s.val_doc,
            "max_feed_m": s.max_feed_m, "max_feed_i": s.max_feed_i,
            "max_rpm_hobby": s.max_rpm_hobby, "max_rpm_indust": s.max_rpm_indust,
            "ra_as_ngrade": s.ra_as_ngrade,
            "auto_rec_doc": s.auto_rec_doc,
            "motor_kw_hobby": s.motor_kw_hobby, "motor_kw_indust": s.motor_kw_indust, "motor_eff": s.motor_eff,
            "tp_D": s.tp_D, "tp_d": s.tp_d, "tp_L": s.tp_L,
            "th_type": s.th_type, "th_diam": s.th_diam, "th_pitch": s.th_pitch,
            "cv_unit": s.cv_unit, "cv_val": s.cv_val,
            "wr_type": s.wr_type, "wr_diam": s.wr_diam, "wr_pitch": s.wr_pitch, "wr_wire": s.wr_wire,
            "wt_matl": s.wt_matl, "wt_diam": s.wt_diam, "wt_len": s.wt_len,
            "sp_diam": s.sp_diam, "sp_vc": s.sp_vc,
            "gr_pitch_cut": s.gr_pitch_cut, "gr_pitch_ls": s.gr_pitch_ls, "gr_gears": s.gr_gears,
            "bc_diam": s.bc_diam, "bc_holes": s.bc_holes,
            "tr_mode": s.tr_mode, "tr_v1": s.tr_v1, "tr_v2": s.tr_v2,
            "ar_radius": s.ar_radius, "ar_angle": s.ar_angle,
            "dp_diam": s.dp_diam, "dp_angle": s.dp_angle,
            "td_diam": s.td_diam, "td_pitch": s.td_pitch,
            "tool_profiles": s.tool_profiles, "active_tool_idx": s.active_tool_idx
        }
        json_str = json.dumps(save_dict)
        if json_str != _last_saved_json:
            
            if view_manager:
                _draw = view_manager.draw
                _draw.fill_rectangle(Vector(255, 2), Vector(60, 16), s.c_hlt)
                _draw.text(Vector(260, 5), "SAVING", s.c_bg)
                _draw.swap()
                
            storage.write(_SETTINGS_FILE, json_str, "w")
            _last_saved_json = json_str
            if view_manager and not force:
                _draw_ui(view_manager)
        dirty_save = False
        del json_str
        gc.collect()
    except Exception: pass

def load_settings():
    '''Reads persistent memory and loads it back into the AppState'''
    global storage, _last_saved_json
    s = state
    if storage and storage.exists(_SETTINGS_FILE):
        try:
            raw_data = storage.read(_SETTINGS_FILE, "r")
            _last_saved_json = raw_data
            loaded = json.loads(raw_data)
            for key in loaded:
                if hasattr(s, key):
                    setattr(s, key, loaded[key])
                    
            if "tool_profiles" in loaded:
                s.tool_profiles = []
                for tp in loaded["tool_profiles"]:
                    if "angle" not in tp: tp["angle"] = 0.0
                    s.tool_profiles.append(tp)
                s.active_tool_idx = loaded.get("active_tool_idx", 0)
            elif "val_cutter" in loaded:
                _type = int(loaded["val_cutter"])
                _rad_m = float(loaded.get("nose_radius_m", 0.4))
                _rad_i = float(loaded.get("nose_radius_i", 0.015))
                s.tool_profiles = [{"name": "Legacy Tool", "type": _type, "rad_m": _rad_m, "rad_i": _rad_i, "angle": 0.0}]
                s.active_tool_idx = 0
                
            # Sanitize indices to repair any float corruption in the save file
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
            s.wt_matl = int(s.wt_matl) if hasattr(s, "wt_matl") else 0
            s.bc_holes = int(s.bc_holes) if hasattr(s, "bc_holes") else 6
            s.gr_gears = str(s.gr_gears) if hasattr(s, "gr_gears") else "20,24,30,32,36,40,44,48,50,52,56,60,64,80,100,120,127"
            s.tr_mode = int(s.tr_mode) if hasattr(s, "tr_mode") else 0
            s.dp_diam = float(s.dp_diam) if hasattr(s, "dp_diam") else 10.0
            s.dp_angle = float(s.dp_angle) if hasattr(s, "dp_angle") else 118.0
            s.td_diam = float(s.td_diam) if hasattr(s, "td_diam") else 6.0
            s.td_pitch = float(s.td_pitch) if hasattr(s, "td_pitch") else 1.0
            if hasattr(s, "auto_rec_doc"): s.auto_rec_doc = bool(s.auto_rec_doc)
            
            return True
        except Exception: pass
    return False

def _apply_theme():
    s = state
    from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_BLUE, TFT_GREEN, TFT_YELLOW, TFT_RED, TFT_CYAN
    
    if s.theme_id == 0:   # DARK THEME
        s.c_bg = TFT_BLACK; s.c_fg = TFT_WHITE; s.c_hlt = TFT_YELLOW
        s.c_ok = TFT_GREEN; s.c_warn = TFT_YELLOW; s.c_err = TFT_RED; s.c_sec = TFT_BLUE
    elif s.theme_id == 1: # TERMINAL
        s.c_bg = TFT_BLACK; s.c_fg = TFT_GREEN; s.c_hlt = TFT_WHITE
        s.c_ok = TFT_CYAN; s.c_warn = TFT_YELLOW; s.c_err = TFT_RED; s.c_sec = TFT_GREEN
    elif s.theme_id == 2: # BLUEPRINT
        s.c_bg = TFT_BLUE; s.c_fg = TFT_WHITE; s.c_hlt = TFT_YELLOW
        s.c_ok = TFT_CYAN; s.c_warn = TFT_YELLOW; s.c_err = TFT_RED; s.c_sec = TFT_WHITE
    elif s.theme_id == 3: # LIGHT MODE
        s.c_bg = TFT_WHITE; s.c_fg = TFT_BLACK; s.c_hlt = TFT_BLUE
        s.c_ok = TFT_GREEN; s.c_warn = TFT_RED; s.c_err = TFT_RED; s.c_sec = TFT_BLACK

def _load_text(mode):
    s = state
    if mode == "CHART":
        if s.val_unit == UNIT_METRIC:
            text = (
                "--- HSS REFERENCE Vc (m/min) ---\n\n"
                "MATERIAL  | INDUST | HOBBY\n"
                "PLASTICS  | 90-150 | 70-100\n"
                "ALUMINUM  | 60-90  | 50-70\n"
                "BRASS/BRZ | 45-60  | 40-50\n"
                "COPPER    | 30-45  | 25-35\n"
                "MILD ST.  | 25-30  | 15-20\n"
                "MED/HI C. | 18-25  | 10-15\n"
                "TOOL ST.  | 12-18  | 8-12\n"
                "STAINLESS | 15-20  | 10-15\n"
                "CAST IRON | 15-25  | 10-15\n"
                "TITANIUM  | 10-15  | 8-12\n"
                "SUPERALLOY| 3-6    | 2-4\n\n"
                "--- CARBIDE REFERENCE Vc (m/min) ---\n\n"
                "MATERIAL  | INDUST | HOBBY\n"
                "PLASTICS  | 200+   | 150+\n"
                "ALUMINUM  | 200+   | 150-250\n"
                "BRASS/BRZ | 150+   | 100-150\n"
                "COPPER    | 120+   | 80-120\n"
                "MILD ST.  | 100+   | 60-80\n"
                "MED/HI C. | 80+    | 50-70\n"
                "TOOL ST.  | 50-80  | 30-50\n"
                "STAINLESS | 80+    | 40-60\n"
                "CAST IRON | 80-120 | 50-70\n"
                "TITANIUM  | 40-60  | 30-40\n"
                "SUPERALLOY| 20-40  | 15-25\n"
            )
        else:
            text = (
                "--- HSS REFERENCE SFM (ft/min) ---\n\n"
                "MATERIAL  | INDUST | HOBBY\n"
                "PLASTICS  | 300-500| 230-330\n"
                "ALUMINUM  | 200-300| 160-230\n"
                "BRASS/BRZ | 150-200| 130-160\n"
                "COPPER    | 100-150| 80-115\n"
                "MILD ST.  | 80-100 | 50-65\n"
                "MED/HI C. | 60-80  | 30-50\n"
                "TOOL ST.  | 40-60  | 25-40\n"
                "STAINLESS | 50-65  | 30-50\n"
                "CAST IRON | 50-80  | 30-50\n"
                "TITANIUM  | 30-50  | 25-40\n"
                "SUPERALLOY| 10-20  | 6-13\n\n"
                "--- CARBIDE REF SFM (ft/min) ---\n\n"
                "MATERIAL  | INDUST | HOBBY\n"
                "PLASTICS  | 650+   | 500+\n"
                "ALUMINUM  | 650+   | 500-800\n"
                "BRASS/BRZ | 500+   | 330-500\n"
                "COPPER    | 400+   | 260-400\n"
                "MILD ST.  | 330+   | 200-260\n"
                "MED/HI C. | 260+   | 160-230\n"
                "TOOL ST.  | 160-260| 100-160\n"
                "STAINLESS | 260+   | 130-200\n"
                "CAST IRON | 260-400| 160-230\n"
                "TITANIUM  | 130-200| 100-130\n"
                "SUPERALLOY| 65-130 | 50-80\n"
            )
    elif mode == "TAP":
        text = (
            "--- METRIC COARSE ---\n\n"
            "THREAD    | PITCH | DRILL(mm)\n"
            "M3        | 0.50  | 2.50\n"
            "M4        | 0.70  | 3.30\n"
            "M5        | 0.80  | 4.20\n"
            "M6        | 1.00  | 5.00\n"
            "M8        | 1.25  | 6.80\n"
            "M10       | 1.50  | 8.50\n"
            "M12       | 1.75  | 10.20\n"
            "M14       | 2.00  | 12.00\n"
            "M16       | 2.00  | 14.00\n\n"
            "--- METRIC FINE ---\n\n"
            "M8 x 1.0  | 1.00  | 7.00\n"
            "M10 x 1.0 | 1.00  | 9.00\n"
            "M10 x 1.25| 1.25  | 8.80\n"
            "M12 x 1.25| 1.25  | 10.80\n"
            "M12 x 1.5 | 1.50  | 10.50\n\n"
            "--- IMPERIAL UNC (COARSE) ---\n\n"
            "THREAD    | DRILL | DEC(in)\n"
            "4 - 40    | #43   | .0890\n"
            "6 - 32    | #36   | .1065\n"
            "8 - 32    | #29   | .1360\n"
            "10 - 24   | #25   | .1495\n"
            "1/4 - 20  | #7    | .2010\n"
            "5/16 - 18 | F     | .2570\n"
            "3/8 - 16  | 5/16  | .3125\n"
            "1/2 - 13  | 27/64 | .4219\n\n"
            "--- IMPERIAL UNF (FINE) ---\n\n"
            "10 - 32   | #21   | .1590\n"
            "1/4 - 28  | #3    | .2130\n"
            "5/16 - 24 | I     | .2770\n"
            "3/8 - 24  | Q     | .3320\n"
            "1/2 - 20  | 29/64 | .4531\n"
        )
    elif mode == "DRILL":
        text = (
            "--- FRACTIONAL DRILLS ---\n\n"
            "FRAC   | DEC(in)| METRIC\n"
            "1/16   | 0.0625 | 1.59mm\n"
            "1/8    | 0.1250 | 3.18mm\n"
            "3/16   | 0.1875 | 4.76mm\n"
            "1/4    | 0.2500 | 6.35mm\n"
            "5/16   | 0.3125 | 7.94mm\n"
            "3/8    | 0.3750 | 9.53mm\n"
            "7/16   | 0.4375 | 11.11mm\n"
            "1/2    | 0.5000 | 12.70mm\n"
            "9/16   | 0.5625 | 14.29mm\n"
            "5/8    | 0.6250 | 15.88mm\n"
            "3/4    | 0.7500 | 19.05mm\n"
            "7/8    | 0.8750 | 22.23mm\n"
            "1.0    | 1.0000 | 25.40mm\n\n"
            "--- COMMON WIRE/LETTER ---\n\n"
            "SIZE   | DEC(in)| METRIC\n"
            "#43    | 0.0890 | 2.26mm\n"
            "#36    | 0.1065 | 2.71mm\n"
            "#29    | 0.1360 | 3.45mm\n"
            "#25    | 0.1495 | 3.80mm\n"
            "#21    | 0.1590 | 4.04mm\n"
            "#7     | 0.2010 | 5.11mm\n"
            "#3     | 0.2130 | 5.41mm\n"
            "F      | 0.2570 | 6.53mm\n"
            "I      | 0.2770 | 7.04mm\n"
            "Q      | 0.3320 | 8.43mm\n"
        )
    elif mode == "KNURL":
        text = (
            "--- KNURLING REFERENCE ---\n\n"
            "PITCH | TPI  | USE CASE\n"
            "1.2mm | 21   | Coarse (Lrg Diam)\n"
            "0.8mm | 33   | Medium (Gen Purp)\n"
            "0.5mm | 50   | Fine (Sml Diam)\n\n"
            "--- BLANK PREPARATION ---\n\n"
            "Form knurls displace metal \n"
            "outward. Turn your blank \n"
            "undersize before knurling.\n\n"
            "FORMULA:\n"
            "Blank Diam = Finished Diam\n"
            "minus (Pitch / 3)\n\n"
            "EXAMPLE:\n"
            "To get a 20mm finish with\n"
            "a 0.8mm pitch wheel:\n"
            "20 - (0.8 / 3) = 19.73mm\n\n"
            "--- PRO TIPS ---\n\n"
            "* Always chamfer blank edges \n"
            "  first to prevent flaking.\n"
            "* Flood with cutting fluid.\n"
            "* Use power feed if possible.\n"
        )
    elif mode == "CENTER":
        text = (
            "--- CENTER DRILL SIZES ---\n\n"
            "SIZE | BODY  | DRILL DIA\n"
            "#1   | 1/8\"  | 3/64\"\n"
            "#2   | 3/16\" | 5/64\"\n"
            "#3   | 1/4\"  | 7/64\"\n"
            "#4   | 5/16\" | 1/8\"\n"
            "#5   | 7/16\" | 3/16\"\n"
            "#6   | 1/2\"  | 7/32\"\n"
            "#7   | 5/8\"  | 1/4\"\n"
            "#8   | 3/4\"  | 5/16\"\n\n"
            "PRO TIP: Never drill past \n"
            "the 60-degree taper section.\n"
        )
    elif mode == "MORSE":
        text = (
            "--- MORSE TAPERS (MT) ---\n\n"
            "SIZE| LRG DIA | TAPER/FOOT\n"
            "MT0 | 0.356\"  | 0.624\"\n"
            "MT1 | 0.475\"  | 0.598\"\n"
            "MT2 | 0.700\"  | 0.599\"\n"
            "MT3 | 0.938\"  | 0.602\"\n"
            "MT4 | 1.231\"  | 0.623\"\n"
            "MT5 | 1.748\"  | 0.631\"\n"
            "MT6 | 2.494\"  | 0.625\"\n\n"
            "To cut an MT on the lathe:\n"
            "Set compound to ~1.43 deg\n"
            "and use a dial indicator to\n"
            "sweep a known good taper.\n"
        )
    elif mode == "CLEAR":
        text = (
            "--- FASTENER CLEARANCES ---\n"
            "       (Metric SHCS)\n\n"
            "SIZE| CLEAR  | C-BORE DIA\n"
            "M3  | 3.4mm  | 6.0mm\n"
            "M4  | 4.5mm  | 8.0mm\n"
            "M5  | 5.5mm  | 10.0mm\n"
            "M6  | 6.6mm  | 11.0mm\n"
            "M8  | 9.0mm  | 15.0mm\n"
            "M10 | 11.0mm | 18.0mm\n"
            "M12 | 13.5mm | 20.0mm\n"
            "M16 | 17.5mm | 26.0mm\n\n"
            "NOTE: Clearance hole sizes\n"
            "are 'Standard/Normal' fit.\n"
        )
    elif mode == "SURFACE":
        text = (
            "--- SURFACE FINISHES ---\n\n"
            "ISO | Ra(µm) | Ra(µin)| CLASS\n"
            "N10 | 12.5   | 500    | Rough\n"
            "N9  | 6.3    | 250    | Rough\n"
            "N8  | 3.2    | 125    | Medium\n"
            "N7  | 1.6    | 63     | Good\n"
            "N6  | 0.8    | 32     | Fine\n"
            "N5  | 0.4    | 16     | X-Fine\n"
            "N4  | 0.2    | 8      | X-Fine\n\n"
            "Turning usually achieves\n"
            "N6 to N9 depending on feed\n"
            "rate and tool nose radius.\n"
        )
    elif mode == "FITS":
        text = (
            "--- ISO SHAFT/HOLE FITS ---\n\n"
            "Using H7 Base Hole System:\n\n"
            "H7 / g6 : Sliding Fit\n"
            "  (Spools, light movement)\n\n"
            "H7 / h6 : Locating Clearance\n"
            "  (Snug assembly by hand)\n\n"
            "H7 / k6 : Locating Transition\n"
            "  (Light tap with mallet)\n\n"
            "H7 / p6 : Medium Press Fit\n"
            "  (Standard bearing press)\n\n"
            "H7 / s6 : Heavy Press Fit\n"
            "  (Permanent, heat shrink)\n"
        )
    elif mode == "HARDNESS":
        text = (
            "--- HARDNESS CONVERSION ---\n\n"
            "HRC | Brinell(HB)| Tens(MPa)\n"
            "20  | 226        | 760\n"
            "25  | 253        | 850\n"
            "30  | 286        | 960\n"
            "35  | 327        | 1090\n"
            "40  | 371        | 1240\n"
            "45  | 425        | 1420\n"
            "50  | 481        | 1620\n"
            "55  | 546        | 1880\n"
            "60  | 601        | 2180\n"
            "65  | 682        | N/A\n"
            "68  | 739        | N/A\n\n"
            "Note: Conversions are approx\n"
            "for non-austenitic steels.\n"
        )
    elif mode == "HELP":
        text = (
            "=== LATHE-CALC v2.1 ===\n\n"
            "=== ABBREVIATIONS GLOSSARY ===\n"
            "Vc/SFM: Cutting Speed\n"
            "DOC   : Depth of Cut\n"
            "LEN   : Length of Cut\n"
            "DIAM  : Workpiece Diameter\n"
            "FEED  : Tool travel/revolution\n"
            "RPM   : Spindle Revolutions/Min\n"
            "TOOL  : Active Tool Profile\n"
            "SYS   : Machine Rigidity/Power\n"
            "PROC  : Machining Process\n"
            "PASS  : Roughing vs Finishing\n"
            "Ra    : Surface Roughness Avg.\n"
            "PWR   : Est. Motor Power\n"
            "EFF   : Motor Efficiency\n\n"
            "=== DETAILED USAGE GUIDE ===\n\n"
            "1. NAVIGATION:\n"
            "   Use UP and DOWN buttons to\n"
            "   move the yellow cursor `>`.\n\n"
            "2. TOGGLES & BUMPING:\n"
            "   Press LEFT/RIGHT on the [ ]\n"
            "   fields to cycle options.\n"
            "   The app auto-updates Vc/Feed\n"
            "   to safe starting points.\n"
            "   Press LEFT/RIGHT on number\n"
            "   fields to bump them up/dwn.\n\n"
            "3. MANUAL ENTRY:\n"
            "   To type exact values, place\n"
            "   cursor over DIAM, LEN, Vc,\n"
            "   FEED, or DOC. Press CENTER\n"
            "   for the on-screen keyboard.\n\n"
            "4. APPLY REC DOC:\n"
            "   Press CENTER on this option\n"
            "   to manually apply the app's\n"
            "   recommended DOC limit. Can\n"
            "   be automated via Options.\n\n"
            "5. TIME ESTIMATOR:\n"
            "   Enter the cut Length (LEN)\n"
            "   to see the estimated time.\n\n"
            "6. TOOL MANAGER:\n"
            "   Create custom tool profiles\n"
            "   with unique nose radii for\n"
            "   HSS and Carbide tools.\n\n"
            "7. SHOP TOOLBOX:\n"
            "   [CHARTS & REFS]\n"
            "   Quick reference tables for\n"
            "   speeds, taps, drills, fits,\n"
            "   surface finish & hardness.\n\n"
            "   [CALCULATORS]\n"
            "   - Taper: Compound angles.\n"
            "   - Threading: Infeed depths.\n"
            "   - Convert: mm/in/fractions.\n"
            "   - 3-Wire: Pitch diam check.\n"
            "   - Stock Wgt: Material mass.\n"
            "   - Spd/Feed: Solves for RPM.\n"
            "   - Gears: Threading trains.\n"
            "   - Bolt Circle: X/Y coords.\n\n"
            "   - Drill Pt: Tip depth calc.\n"
            "   - Tap Drill: Hole size calc.\n"
            "   - Arc/Chord: Circle math.\n"
            "   - Triangle: Solve right \n"
            "     triangles automatically.\n\n"
            "   [MANAGEMENT]\n"
            "   UI Themes, App Settings,\n"
            "   and Custom Tool Profiles.\n\n"
            "* All settings save automatically\n\n"
            "=== CREDITS ===\n\n"
            "Made by Slasher006\n"
            "with the help of Gemini\n"
        )
    
    s.text_lines = text.split('\n')
    s.scroll_pos = 0

def _apply_safe_defaults():
    s = state 
    _active_type = s.tool_profiles[s.active_tool_idx]["type"]
    
    if s.val_type == TYPE_HOBBY:
        vc_map = [60.0, 45.0, 18.0, 12.0, 12.0, 85.0, 10.0, 30.0, 12.0, 10.0, 3.0] if _active_type == CUT_HSS else [150.0, 100.0, 70.0, 50.0, 60.0, 150.0, 35.0, 100.0, 60.0, 40.0, 20.0]
    else:
        vc_map = [75.0, 50.0, 27.0, 17.0, 20.0, 120.0, 12.0, 37.0, 21.0, 15.0, 4.0] if _active_type == CUT_HSS else [200.0, 150.0, 100.0, 80.0, 100.0, 200.0, 50.0, 120.0, 80.0, 65.0, 30.0]
    base_vc = vc_map[s.val_work]
    
    # Local variable feed modifier to prevent RAM clutter
    _f_mod = 1.0 
    
    # Feed overrides for specific challenging materials
    if s.val_proc not in (PROC_PART, PROC_CHAMFER):
        if s.val_work == WORK_SUPER:
            _f_mod = 1.25  # +25% feed to force tool under the work-hardened layer
        elif s.val_work == WORK_TOOL_ST:
            _f_mod = 0.85  # -15% feed to protect tool life in hard alloys
        elif s.val_work == WORK_COPPER and s.val_pass == PASS_FINISH:
            _f_mod = 1.50  # +50% finish feed to prevent copper from tearing
            
    _nose_radius_i = s.tool_profiles[s.active_tool_idx]["rad_i"]
    _nose_radius_m = s.tool_profiles[s.active_tool_idx]["rad_m"]
    
    if s.val_unit == UNIT_IMP:
        base_vc = base_vc * 3.28084
        if s.val_proc in (PROC_PART, PROC_CHAMFER):
            s.val_vc = base_vc * 0.5
            s.val_feed = 0.002
        else:
            s.val_vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            # Apply the modifier to the standard imperial feeds
            _base_feed = (0.006 if _active_type == CUT_HSS else 0.008) if s.val_pass == PASS_ROUGH else (0.002 if _active_type == CUT_HSS else 0.003)
            s.val_feed = _base_feed * _f_mod
            
            s.val_vc = int(s.val_vc)
            s.val_feed = int(s.val_feed * 10000) / 10000.0
            s.val_doc = round(_nose_radius_i, 3) if s.val_pass == PASS_FINISH else 0.04
    else:
        if s.val_proc in (PROC_PART, PROC_CHAMFER):
            s.val_vc = base_vc * 0.5
            s.val_feed = 0.05
        else:
            s.val_vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            # Apply the modifier to the standard metric feeds
            _base_feed = (0.15 if _active_type == CUT_HSS else 0.20) if s.val_pass == PASS_ROUGH else (0.05 if _active_type == CUT_HSS else 0.08)
            s.val_feed = _base_feed * _f_mod
            
            s.val_vc = int(s.val_vc * 10) / 10.0
            s.val_feed = int(s.val_feed * 1000) / 1000.0 
            s.val_doc = round(_nose_radius_m, 2) if s.val_pass == PASS_FINISH else 1.0
        
def _calculate():
    s = state 
    _pi = 3.14159
    s.warn_coolant = False; s.warn_rpm_cap = False; s.warn_carbide_spd = False; s.warn_high_feed = False; s.warn_poor_finish = False; s.warn_power_cap = False; s.time_result = "0m 0s"
    
    _max_rpm = MAX_LATHE_RPM_HOBBY if s.val_type == TYPE_HOBBY else MAX_LATHE_RPM_INDUST
    _active_type = s.tool_profiles[s.active_tool_idx]["type"]
    _nose_radius_m = s.tool_profiles[s.active_tool_idx]["rad_m"]
    _nose_radius_i = s.tool_profiles[s.active_tool_idx]["rad_i"]
    
    # 1. Main Spindle Math
    if s.val_diam > 0:
        theoretical_rpm = (s.val_vc * 1000.0) / (_pi * s.val_diam) if s.val_unit == UNIT_METRIC else (s.val_vc * 12.0) / (_pi * s.val_diam)
        s.rpm_result = theoretical_rpm
        if s.rpm_result > _max_rpm:
            s.rpm_result = _max_rpm
            s.warn_rpm_cap = True
            if _active_type == CUT_CARB: s.warn_carbide_spd = True
        
        if _active_type == CUT_HSS or s.val_proc in (PROC_PART, PROC_CHAMFER, PROC_DRILL) or s.val_work in (WORK_STAIN, WORK_TITAN, WORK_SUPER): s.warn_coolant = True
            
        if s.val_proc == PROC_PART:
            s.rec_doc = "FULL BLD"
        elif s.val_proc == PROC_CHAMFER:
            s.rec_doc = "MANUAL"
        elif s.val_proc == PROC_DRILL:
            s.rec_doc = "PECK"
        elif s.val_proc == PROC_BORE:
            if s.val_pass == PASS_FINISH:
                _n = _nose_radius_m if s.val_unit == UNIT_METRIC else _nose_radius_i
                _rnd = 2 if s.val_unit == UNIT_METRIC else 4
                s.rec_doc = str(round(_n * 0.5, _rnd)) + "-" + str(round(_n * 1.5, _rnd)) + ("mm" if s.val_unit == UNIT_METRIC else "in")
            elif s.val_type == TYPE_INDUST:
                s.rec_doc = "SEE SPEC" if _active_type == CUT_CARB else ("1.0mm+" if s.val_unit == UNIT_METRIC else "0.04in+")
            else:
                s.rec_doc = "0.2-0.5mm" if s.val_unit == UNIT_METRIC else "0.01-0.02in"
        else:
            if s.val_pass == PASS_FINISH:
                _n = _nose_radius_m if s.val_unit == UNIT_METRIC else _nose_radius_i
                _rnd = 2 if s.val_unit == UNIT_METRIC else 4
                s.rec_doc = str(round(_n * 0.5, _rnd)) + "-" + str(round(_n * 1.5, _rnd)) + ("mm" if s.val_unit == UNIT_METRIC else "in")
            elif s.val_type == TYPE_INDUST:
                s.rec_doc = "SEE SPEC" if _active_type == CUT_CARB else ("2.0mm+" if s.val_unit == UNIT_METRIC else "0.08in+")
            else:
                if s.val_work in (WORK_SUPER, WORK_TOOL_ST):
                    # 50% DOC reduction for extremely hard materials on hobby machines
                    s.rec_doc = ("0.5mm" if _active_type == CUT_HSS else "0.2mm") if s.val_unit == UNIT_METRIC else ("0.02in" if _active_type == CUT_HSS else "0.008in")
                else:
                    s.rec_doc = ("1.0mm" if _active_type == CUT_HSS else "0.5mm") if s.val_unit == UNIT_METRIC else ("0.04in" if _active_type == CUT_HSS else "0.02in")
        
        _feed_limit = s.max_feed_m if s.val_unit == UNIT_METRIC else s.max_feed_i
        
        s.feed_m_result = s.rpm_result * s.val_feed
        
        if s.feed_m_result > _feed_limit:
            s.warn_high_feed = True

        s.feed_m_result = round(s.feed_m_result, 1) if s.val_unit == UNIT_METRIC else round(s.feed_m_result, 3)
            
        if s.val_feed > 0 and s.rpm_result > 0 and s.val_len > 0:
            time_mins = s.val_len / (s.val_feed * s.rpm_result)
            _m = int(time_mins)
            _s = int((time_mins - _m) * 60)
            s.time_result = str(_m) + "m " + str(_s) + "s"
            
        if s.val_unit == UNIT_IMP:
            _nose_r = _nose_radius_i
            _ra = ((s.val_feed ** 2) / (32.0 * _nose_r)) * 1000000.0 if _nose_r > 0 else 0.0
            _ra_um = _ra * 0.0254
            if not s.ra_as_ngrade: s.ra_result_str = str(int(_ra)) + " uin"
            if _ra > (250.0 if s.val_pass == PASS_ROUGH else 63.0):
                s.warn_poor_finish = True
        else:
            _nose_r = _nose_radius_m
            _ra = ((s.val_feed ** 2) / (32.0 * _nose_r)) * 1000.0 if _nose_r > 0 else 0.0
            _ra_um = _ra
            if not s.ra_as_ngrade: s.ra_result_str = str(round(_ra, 2)) + " um"
            if _ra > (6.3 if s.val_pass == PASS_ROUGH else 1.6):
                s.warn_poor_finish = True
                
        if s.ra_as_ngrade:
            _n_grades = [0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.3, 12.5, 25.0, 50.0]
            _n_idx = 0
            while _n_idx < 11 and _ra_um > _n_grades[_n_idx]:
                _n_idx += 1
            s.ra_result_str = "N" + str(_n_idx + 1)
            
        # Power Estimation Math
        _kc_map = [700, 600, 1600, 2000, 1100, 200, 1800, 700, 1800, 2200, 2600]
        _kc = _kc_map[s.val_work] if s.val_work < 11 else 1000
        _vc_m = s.val_vc if s.val_unit == UNIT_METRIC else s.val_vc * 0.3048
        _feed_mm = s.val_feed if s.val_unit == UNIT_METRIC else s.val_feed * 25.4
        _doc_mm = s.val_doc if s.val_unit == UNIT_METRIC else s.val_doc * 25.4
        
        _pc_kw = (_vc_m * _doc_mm * _feed_mm * _kc) / 60000.0
        _req_motor_kw = _pc_kw / s.motor_eff if s.motor_eff > 0 else 0.0
        
        _motor_limit_kw = s.motor_kw_hobby if s.val_type == TYPE_HOBBY else s.motor_kw_indust
        if _req_motor_kw > _motor_limit_kw: s.warn_power_cap = True
            
        if s.val_unit == UNIT_IMP: s.pwr_result_str = str(round(_req_motor_kw * 1.34102, 2)) + " HP"
        else: s.pwr_result_str = str(round(_req_motor_kw, 2)) + " kW"
            
    # 2. Taper Math
    if s.current_screen == SCREEN_TAPER:
        if s.tp_L > 0:
            _rads = math.atan(abs(s.tp_D - s.tp_d) / (2.0 * s.tp_L))
            s.tp_angle = int((_rads * (180.0 / _pi)) * 100) / 100.0

    # 3. Threading Math (60 Degree Standards)
    if s.current_screen == SCREEN_THREAD:
        _th_p = s.th_pitch if s.th_type == TH_METRIC else (1.0 / max(0.001, s.th_pitch))
        _th_h = 0.61343 * _th_p
        s.th_minor = s.th_diam - (2.0 * _th_h)
        s.th_infeed = _th_h / 0.87035 # cos(29.5 degrees) for compound sliding
        
        if s.th_type == TH_METRIC:
            s.th_pass_1 = min(0.3, max(0.1, _th_p * 0.15))
            s.th_pass_n = min(0.15, max(0.05, _th_p * 0.05))
        else:
            s.th_pass_1 = min(0.012, max(0.004, _th_p * 0.15))
            s.th_pass_n = min(0.006, max(0.002, _th_p * 0.05))
    
    # 4. Converter Math
    if s.current_screen == SCREEN_CONVERT:
        if s.cv_unit == UNIT_METRIC:
            s.cv_mm = s.cv_val
            s.cv_inch = s.cv_val / 25.4
        else:
            s.cv_mm = s.cv_val * 25.4
            s.cv_inch = s.cv_val
            
        _whole = int(s.cv_inch)
        _rem = s.cv_inch - _whole
        _num = int((_rem * 64.0) + 0.5)
        if _num == 64:
            _whole += 1
            _num = 0
        _den = 64
        while _num > 0 and _num % 2 == 0 and _den > 1:
            _num //= 2
            _den //= 2
            
        if _num == 0:
            s.cv_frac = str(_whole) + '"' if _whole > 0 else '0"'
        else:
            _w_str = str(_whole) + " " if _whole > 0 else ""
            s.cv_frac = _w_str + str(_num) + "/" + str(_den) + '"'

    # 5. 3-Wire Math
    if s.current_screen == SCREEN_WIRE:
        _wr_p = s.wr_pitch if s.wr_type == TH_METRIC else (1.0 / max(0.001, s.wr_pitch))
        s.wr_best = 0.57735 * _wr_p
        s.wr_result = s.wr_diam - (0.866025 * _wr_p) + (3.0 * s.wr_wire)

    # 6. Weight Math
    if s.current_screen == SCREEN_WEIGHT:
        _wt_densities = [7.85, 2.70, 8.53, 7.93, 7.20, 4.50, 8.96, 1.20] # Steel, Alu, Brass, Stain, Cast, Titan, Copper, Plast
        _d = _wt_densities[s.wt_matl]
        if s.val_unit == UNIT_METRIC:
            s.wt_result = (_pi * ((s.wt_diam / 20.0) ** 2) * (s.wt_len / 10.0) * _d) / 1000.0 # kg
        else:
            s.wt_result = (_pi * ((s.wt_diam / 2.0) ** 2) * s.wt_len) * (_d * 0.0361273) # lbs

    # 7. Speeds & Feeds Math
    if s.current_screen == SCREEN_SPEED:
        if s.sp_diam > 0:
            if s.val_unit == UNIT_METRIC:
                s.sp_rpm = (s.sp_vc * 1000.0) / (_pi * s.sp_diam)
            else:
                s.sp_rpm = (s.sp_vc * 12.0) / (_pi * s.sp_diam)
        else:
            s.sp_rpm = 0.0

    # 8. Change Gear Math
    if s.current_screen == SCREEN_GEARS:
        s.gr_results = []
        try:
            available_gears = sorted(list(set([int(g.strip()) for g in s.gr_gears.split(',') if g.strip().isdigit()])))
            
            is_metric = (s.val_unit == UNIT_METRIC)
            pitch_cut = s.gr_pitch_cut
            pitch_ls = s.gr_pitch_ls
    
            if pitch_cut <= 0 or pitch_ls <= 0:
                raise ValueError("Pitches must be > 0")
    
            target_ratio = pitch_cut / pitch_ls if is_metric else pitch_ls / pitch_cut
    
            # Simple train (A/B)
            for a in available_gears:
                for b in available_gears:
                    if a == b: continue
                    if abs((a / b) - target_ratio) < 0.0001:
                        s.gr_results.append(f"{a} / {b}")
                        if len(s.gr_results) >= 10: break
                if len(s.gr_results) >= 10: break
            
            # Compound train (A/B * C/D)
            if len(s.gr_results) < 10:
                ratio_map = {}
                for g1 in available_gears:
                    for g2 in available_gears:
                        if g1 == g2: continue
                        ratio = g1 / g2
                        if ratio not in ratio_map: ratio_map[ratio] = []
                        ratio_map[ratio].append((g1, g2))
    
                for a, b in ((g1, g2) for g1 in available_gears for g2 in available_gears if g1 != g2):
                    if len(s.gr_results) >= 10: break
                    ratio1 = a / b
                    if ratio1 == 0: continue
                    required_ratio2 = target_ratio / ratio1
                    for r_key in ratio_map:
                        if abs(r_key - required_ratio2) < 0.0001:
                            for c, d in ratio_map[r_key]:
                                gears_needed = {g: [a, b, c, d].count(g) for g in set([a, b, c, d])}
                                if all(available_gears.count(g) >= count for g, count in gears_needed.items()):
                                    sol_str = f"({a}/{b}) * ({c}/{d})"
                                    if sol_str not in s.gr_results:
                                        s.gr_results.append(sol_str)
                                        if len(s.gr_results) >= 10: break
                            if len(s.gr_results) >= 10: break
        except Exception as e:
            s.gr_results = [f"Error: {e}"][:1]

    # 9. Bolt Circle Math
    if s.current_screen == SCREEN_BOLT_CIRCLE:
        s.bc_results = []
        if s.bc_holes > 1:
            radius = s.bc_diam / 2.0
            angle_step = 360.0 / s.bc_holes
            for i in range(s.bc_holes):
                angle_deg = i * angle_step
                angle_rad = angle_deg * (_pi / 180.0)
                # Start at 12 o'clock (0, R) and go clockwise
                x = radius * math.sin(angle_rad)
                y = radius * math.cos(angle_rad)
                s.bc_results.append((round(x, 4), round(y, 4)))
            
    # 10. Right Triangle Math
    if s.current_screen == SCREEN_TRIANGLE:
        s.tr_A = s.tr_B = s.tr_C = s.tr_ang_a = s.tr_ang_b = 0.0
        try:
            m = s.tr_mode
            v1 = s.tr_v1
            v2 = s.tr_v2
            rad = math.pi / 180.0
            deg = 180.0 / math.pi
            
            if m == 0: # A & B
                s.tr_A = v1; s.tr_B = v2
                s.tr_C = math.sqrt(v1*v1 + v2*v2)
                s.tr_ang_a = math.atan2(v1, v2) * deg if v2 != 0 else 90.0
            elif m == 1: # A & C
                s.tr_A = v1; s.tr_C = v2
                if v2 > v1:
                    s.tr_B = math.sqrt(v2*v2 - v1*v1)
                    s.tr_ang_a = math.asin(v1/v2) * deg
            elif m == 2: # B & C
                s.tr_B = v1; s.tr_C = v2
                if v2 > v1:
                    s.tr_A = math.sqrt(v2*v2 - v1*v1)
                    s.tr_ang_a = math.acos(v1/v2) * deg
            elif m == 3: # A & Ang(a)
                s.tr_A = v1; s.tr_ang_a = v2
                if 0 < v2 < 90:
                    s.tr_B = v1 / math.tan(v2 * rad)
                    s.tr_C = v1 / math.sin(v2 * rad)
            elif m == 4: # B & Ang(a)
                s.tr_B = v1; s.tr_ang_a = v2
                if 0 < v2 < 90:
                    s.tr_A = v1 * math.tan(v2 * rad)
                    s.tr_C = v1 / math.cos(v2 * rad)
            elif m == 5: # C & Ang(a)
                s.tr_C = v1; s.tr_ang_a = v2
                if 0 < v2 < 90:
                    s.tr_A = v1 * math.sin(v2 * rad)
                    s.tr_B = v1 * math.cos(v2 * rad)
                
            if s.tr_ang_a > 0.0:
                s.tr_ang_b = 90.0 - s.tr_ang_a
        except Exception:
            pass

    # 11. Arc & Chord Math
    if s.current_screen == SCREEN_ARC:
        s.ar_arc_len = s.ar_chord = 0.0
        if s.ar_radius > 0 and s.ar_angle > 0:
            _rad = s.ar_angle * (math.pi / 180.0)
            s.ar_arc_len = s.ar_radius * _rad
            s.ar_chord = 2.0 * s.ar_radius * math.sin(_rad / 2.0)

    # 12. Drill Point Depth Math
    if s.current_screen == SCREEN_DRILL_PT:
        if s.dp_diam > 0 and s.dp_angle > 0:
            _rad_half = (s.dp_angle / 2.0) * (math.pi / 180.0)
            s.dp_result = (s.dp_diam / 2.0) / math.tan(_rad_half)
        else:
            s.dp_result = 0.0

    # 13. Tap Drill Math
    if s.current_screen == SCREEN_TAP_HOLE:
        if s.td_diam > 0 and s.td_pitch > 0:
            _td_p = s.td_pitch if s.val_unit == UNIT_METRIC else (1.0 / s.td_pitch)
            s.td_result = max(0.0, s.td_diam - _td_p)
        else:
            s.td_result = 0.0

def start(view_manager):
    global state, storage
    state = AppState()
    storage = view_manager.storage
    
    # Check SD Card for saved settings
    if not load_settings():
        # Fall back to calculating standard safe machining defaults if no save exists
        _apply_safe_defaults()
        
    _apply_theme()
    _calculate()
    _draw_ui(view_manager)
    return True

def _draw_ui(view_manager):
    if state.current_screen == SCREEN_CALC: _draw_calc(view_manager)
    elif state.current_screen == SCREEN_TOOLBOX: _draw_toolbox(view_manager)
    elif state.current_screen == SCREEN_TAPER: _draw_taper(view_manager)
    elif state.current_screen == SCREEN_THREAD: _draw_thread(view_manager)
    elif state.current_screen == SCREEN_CONVERT: _draw_convert(view_manager)
    elif state.current_screen == SCREEN_OPTIONS: _draw_options(view_manager)
    elif state.current_screen == SCREEN_TOOL_MGR: _draw_tool_mgr(view_manager)
    elif state.current_screen == SCREEN_WIRE: _draw_wire(view_manager)
    elif state.current_screen == SCREEN_WEIGHT: _draw_weight(view_manager)
    elif state.current_screen == SCREEN_SPEED: _draw_speed(view_manager)
    elif state.current_screen == SCREEN_GEARS: _draw_gears(view_manager)
    elif state.current_screen == SCREEN_BOLT_CIRCLE: _draw_bolt_circle(view_manager)
    elif state.current_screen == SCREEN_TRIANGLE: _draw_triangle(view_manager)
    elif state.current_screen == SCREEN_ARC: _draw_arc(view_manager)
    elif state.current_screen == SCREEN_DRILL_PT: _draw_drill_pt(view_manager)
    elif state.current_screen == SCREEN_GRAPH: _draw_graph(view_manager)
    elif state.current_screen == SCREEN_TAP_HOLE: _draw_tap_hole(view_manager)
    elif state.current_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL, SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE, SCREEN_FITS, SCREEN_HELP, SCREEN_KNURL, SCREEN_HARDNESS): _draw_text_screen(view_manager, state.current_screen)

def _draw_text_screen(view_manager, mode):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    
    if mode == SCREEN_CHART: _draw.text(Vector(5, 5), "SYSTEM DATA CHARTS", s.c_fg)
    elif mode == SCREEN_TAP: _draw.text(Vector(5, 5), "TAP & CLEARANCE SIZES", s.c_fg)
    elif mode == SCREEN_DRILL: _draw.text(Vector(5, 5), "DRILL SIZE CHART", s.c_fg)
    elif mode == SCREEN_CENTER: _draw.text(Vector(5, 5), "CENTER DRILL SIZES", s.c_fg)
    elif mode == SCREEN_MORSE: _draw.text(Vector(5, 5), "MORSE TAPER DIMS", s.c_fg)
    elif mode == SCREEN_CLEAR: _draw.text(Vector(5, 5), "SHCS CLEARANCES", s.c_fg)
    elif mode == SCREEN_SURFACE: _draw.text(Vector(5, 5), "SURFACE FINISHES", s.c_fg)
    elif mode == SCREEN_FITS: _draw.text(Vector(5, 5), "ISO FITS (H7 BASE)", s.c_fg)
    elif mode == SCREEN_KNURL: _draw.text(Vector(5, 5), "KNURLING REFERENCE", s.c_fg)
    elif mode == SCREEN_HARDNESS: _draw.text(Vector(5, 5), "HARDNESS CONVERSION", s.c_fg)
    else: _draw.text(Vector(5, 5), "HELP & ABBREVIATIONS", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _vis = 16; _lh = 15; _sy = 30        
    v_pos = Vector(5, 0)
    for i in range(_vis):
        _idx = s.scroll_pos + i
        if _idx < len(s.text_lines):
            v_pos.y = _sy + i * _lh; _draw.text(v_pos, s.text_lines[_idx], s.c_fg)
            
    _tot = len(s.text_lines)
    if _tot > _vis:
        _draw.line(Vector(313, _sy), Vector(313, 275), s.c_sec)
        _th = max(int((_vis / _tot) * 245), 10)
        _ms = _tot - _vis
        _ty = _sy + int((s.scroll_pos / _ms) * (245 - _th)) if _ms > 0 else _sy
        _draw.fill_rectangle(Vector(311, _ty), Vector(4, _th), s.c_hlt)
    
    _draw.fill_rectangle(Vector(0, 282), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 295), "[UP/DOWN] SCROLL | [BACK] EXIT", s.c_sec)
    _draw.swap()

def _draw_graph(view_manager):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "RPM vs MATERIAL", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
    _draw.text(Vector(5, 28), "Diam: " + str(s.val_diam) + _u_d + " | Tool: " + ("HSS" if s.tool_profiles[s.active_tool_idx]["type"] == CUT_HSS else "CARB"), s.c_ok)
    
    _active_type = s.tool_profiles[s.active_tool_idx]["type"]
    if s.val_type == TYPE_HOBBY:
        vc_map = [60.0, 45.0, 18.0, 12.0, 12.0, 85.0, 10.0, 30.0, 12.0, 10.0, 3.0] if _active_type == CUT_HSS else [150.0, 100.0, 70.0, 50.0, 60.0, 150.0, 35.0, 100.0, 60.0, 40.0, 20.0]
    else:
        vc_map = [75.0, 50.0, 27.0, 17.0, 20.0, 120.0, 12.0, 37.0, 21.0, 15.0, 4.0] if _active_type == CUT_HSS else [200.0, 150.0, 100.0, 80.0, 100.0, 200.0, 50.0, 120.0, 80.0, 65.0, 30.0]
    
    _pi = 3.14159
    _max_rpm = s.max_rpm_hobby if s.val_type == TYPE_HOBBY else s.max_rpm_indust
    
    rpms = []
    for i in range(11):
        base_vc = vc_map[i]
        if s.val_unit == UNIT_IMP:
            vc = (base_vc * 3.28084) if s.val_pass == PASS_ROUGH else (base_vc * 3.28084) * 1.3
            rpm = (vc * 12.0) / (_pi * s.val_diam) if s.val_diam > 0 else 0
        else:
            vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            rpm = (vc * 1000.0) / (_pi * s.val_diam) if s.val_diam > 0 else 0
        
        rpms.append(min(rpm, _max_rpm))
        
    _max_plotted = max(rpms) if rpms and max(rpms) > 0 else 1.0
    plot_max = _max_plotted * 1.15
    labels = ["AL", "BR", "MS", "SS", "CI", "PL", "TI", "CU", "HC", "TS", "SA"]
    bar_w = 22; spacing = 6; start_x = 8; base_y = 250; max_h = 180
    
    v_pos = Vector(0,0); v_size = Vector(0,0)
    for i in range(11):
        h = int((rpms[i] / plot_max) * max_h)
        x = start_x + i * (bar_w + spacing)
        c = s.c_hlt if i == s.val_work else s.c_fg
        if h > 0:
            v_pos.x = x; v_pos.y = base_y - h
            v_size.x = bar_w; v_size.y = h
            _draw.fill_rectangle(v_pos, v_size, c)
        v_pos.x = x + 2; v_pos.y = base_y + 5
        _draw.text(v_pos, labels[i], c)
        if i == s.val_work:
            v_pos.x = x - 4; v_pos.y = base_y - h - 15
            _draw.text(v_pos, str(int(rpms[i])), s.c_ok)
            
    # Draw Limit Line if visible
    limit_h = int((_max_rpm / plot_max) * max_h)
    if limit_h <= max_h:
        limit_y = base_y - limit_h
        v_size.x = 4; v_size.y = 1
        for x_dot in range(0, 320, 8):
            v_pos.x = x_dot; v_pos.y = limit_y
            _draw.fill_rectangle(v_pos, v_size, s.c_err)
        v_pos.x = 180; v_pos.y = limit_y - 12
        _draw.text(v_pos, "LIMIT: " + str(int(_max_rpm)), s.c_err)
        
    _draw.fill_rectangle(Vector(0, 282), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 295), "[BACK] RETURN TO TOOLBOX", s.c_sec)
    _draw.swap()

def _draw_toolbox(view_manager):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "SHOP TOOLBOX", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)

    # Draw Categories (Left Pane)
    cat_x = 5
    cat_y_start = 30
    cat_line_h = 20
    v_pos = Vector(0, 0)
    for i, (cat_name, _) in enumerate(TOOLBOX_MENU):
        y = cat_y_start + i * cat_line_h
        color = s.c_hlt if i == s.sel_tb_cat else s.c_fg
        if s.sel_tb_col == 0 and i == s.sel_tb_cat:
            v_pos.x, v_pos.y = cat_x, y; _draw.text(v_pos, "> " + cat_name, color)
        else:
            v_pos.x, v_pos.y = cat_x + 10, y; _draw.text(v_pos, cat_name, color)

    # Draw Separator
    _draw.fill_rectangle(Vector(140, 25), Vector(1, 270), s.c_fg)

    # Draw Items (Right Pane)
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
            v_pos.x, v_pos.y = item_x, y; _draw.text(v_pos, "> " + item_name, color)
        else:
            v_pos.x, v_pos.y = item_x + 10, y; _draw.text(v_pos, item_name, color)

    # Draw Back button at the bottom
    back_y = 295
    back_color = s.c_hlt if s.sel_tb_cat == len(TOOLBOX_MENU) else s.c_fg
    if s.sel_tb_col == 0 and s.sel_tb_cat == len(TOOLBOX_MENU):
        _draw.text(Vector(cat_x, back_y), "> < RETURN TO MAIN", back_color)
    else:
        _draw.text(Vector(cat_x + 10, back_y), "< RETURN TO MAIN", back_color)

    _draw.swap()

def _draw_options(view_manager):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "PERSONALIZATION", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    themes = ["0: DARK THEME", "1: TERMINAL", "2: BLUEPRINT", "3: LIGHT MODE"]
    
    _u = "mm/m" if s.val_unit == UNIT_METRIC else "in/m"
    
    _limit_val = s.max_feed_m if s.val_unit == UNIT_METRIC else s.max_feed_i
    _rpm_cap = s.max_rpm_hobby if s.val_type == TYPE_HOBBY else s.max_rpm_indust
    _ra_disp = "N-GRADE" if s.ra_as_ngrade else ("um" if s.val_unit == UNIT_METRIC else "uin")
    _pwr_kw = s.motor_kw_hobby if s.val_type == TYPE_HOBBY else s.motor_kw_indust
    _pwr_u = "HP" if s.val_unit == UNIT_IMP else "kW"
    _pwr_disp = round(_pwr_kw * 1.34102, 2) if s.val_unit == UNIT_IMP else round(_pwr_kw, 2)
    _auto_doc_str = "ON" if s.auto_rec_doc else "OFF"
    
    opts = [
        "UI THEME: < " + themes[s.theme_id] + " >",
        "MAX FEED:   " + str(round(_limit_val, 3)) + " " + _u,
        "MAX RPM :   " + str(int(_rpm_cap)) + " RPM",
        "Ra DISP : < " + _ra_disp + " >",
        "MTR PWR :   " + str(_pwr_disp) + " " + _pwr_u,
        "MTR EFF :   " + str(int(s.motor_eff * 100)) + " %",
        "AUTO DOC: < " + _auto_doc_str + " >",
        "< RETURN TO TOOLBOX"
    ]
    
    v_pos = Vector(0, 0)
    for i in range(8):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_opt:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)
            
    _draw.swap()

def _draw_tool_mgr(view_manager):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "TOOL MANAGER", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    active_tool = s.tool_profiles[s.active_tool_idx]
    _t_str = "HSS" if active_tool["type"] == CUT_HSS else "CARBIDE"
    _r_str = str(round(active_tool["rad_m"], 3)) + " mm" if s.val_unit == UNIT_METRIC else str(round(active_tool["rad_i"], 4)) + " in"
    _a_str = str(round(active_tool.get("angle", 0.0), 1)) + " DEG"
    
    opts = [
        "< RETURN TO TOOLBOX",
        "+ CREATE NEW TOOL",
        "- DELETE CURR TOOL",
        "SELECT: < " + active_tool["name"] + " >",
        "RENAME: [PRESS CENTER]",
        "TYPE  : < " + _t_str + " >",
        "RADIUS: < " + _r_str + " >",
        "ANGLE : < " + _a_str + " >"
    ]
    
    v_pos = Vector(0, 0)
    for i in range(8):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_tm:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)
            
    _draw.swap()

def _draw_taper(view_manager):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "TAPER ANGLE CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u = "mm" if s.val_unit == UNIT_METRIC else "in"
    opts = [
        "LARGE DIAM (D):  " + str(round(s.tp_D, 3)) + " " + _u,
        "SMALL DIAM (d):  " + str(round(s.tp_d, 3)) + " " + _u,
        "TAPER LEN  (L):  " + str(round(s.tp_L, 3)) + " " + _u,
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(4):
        _y = 40 + i * 25
        if i == s.sel_tp:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 160), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 175), "REQUIRED COMPOUND SETTING:", s.c_ok)
    _draw.text(Vector(5, 205), str(s.tp_angle) + " DEGREES", s.c_fg)
    _draw.text(Vector(5, 235), "(Angle from centerline)", s.c_fg)
    _draw.swap()

def _draw_thread(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "THREADING ASSISTANT (60 DEG)", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_d = "mm" if s.th_type == TH_METRIC else "in"
    _u_p = "mm" if s.th_type == TH_METRIC else "TPI"
    _t_str = "METRIC 60" if s.th_type == TH_METRIC else "UNIFIED 60"
    
    opts = [
        "TYPE : [ " + _t_str + " ]",
        "MAJOR:   " + str(round(s.th_diam, 3)) + " " + _u_d,
        "PITCH:   " + str(round(s.th_pitch, 3)) + " " + _u_p,
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(4):
        _y = 40 + i * 25
        if i == s.sel_th:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 160), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 175), "RECOMMENDED INFEED DATA:", s.c_ok)
    
    _min_str = str(int(s.th_minor * 1000) / 1000.0)
    _inf_str = str(int(s.th_infeed * 1000) / 1000.0)
    _p1_str = str(int(s.th_pass_1 * 1000) / 1000.0)
    _pn_str = str(int(s.th_pass_n * 1000) / 1000.0)
    
    _draw.text(Vector(5, 195), "MINOR DIAM: " + _min_str + " " + _u_d, s.c_fg)
    _draw.text(Vector(5, 215), "TOTAL INFD: " + _inf_str + " " + _u_d, s.c_fg)
    _draw.text(Vector(5, 235), "1ST PASS  : " + _p1_str + " " + _u_d, s.c_warn)
    _draw.text(Vector(5, 255), "NEXT PASS : " + _pn_str + " " + _u_d, s.c_warn)
    _draw.text(Vector(5, 275), "COMP ANGLE: 29.5 DEG", s.c_sec)
    _draw.swap()

def _draw_convert(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "SHOP UNIT CONVERTER", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_str = "MILLIMETERS" if s.cv_unit == UNIT_METRIC else "DEC INCHES"
    
    opts = [
        "INPUT: [ " + _u_str + " ]",
        "VALUE:   " + str(round(s.cv_val, 4)),
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(3):
        _y = 40 + i * 25
        if i == s.sel_cv:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 135), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 150), "EQUIVALENTS:", s.c_ok)
    
    _mm_str = str(int(s.cv_mm * 1000) / 1000.0)
    _in_str = str(int(s.cv_inch * 10000) / 10000.0)
    
    _draw.text(Vector(5, 180), "METRIC : " + _mm_str + " mm", s.c_fg)
    _draw.text(Vector(5, 210), "DECIMAL: " + _in_str + " in", s.c_fg)
    _draw.text(Vector(5, 240), "FRACT  : " + s.cv_frac + " (To 1/64)", s.c_hlt)
    _draw.swap()

def _draw_wire(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "3-WIRE MEASUREMENT (60 DEG)", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_d = "mm" if s.wr_type == TH_METRIC else "in"
    _u_p = "mm" if s.wr_type == TH_METRIC else "TPI"
    _t_str = "METRIC 60" if s.wr_type == TH_METRIC else "UNIFIED 60"
    
    opts = [
        "TYPE : [ " + _t_str + " ]",
        "MAJOR:   " + str(round(s.wr_diam, 3)) + " " + _u_d,
        "PITCH:   " + str(round(s.wr_pitch, 3)) + " " + _u_p,
        "WIRE :   " + str(round(s.wr_wire, 4)) + " " + _u_d,
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(5):
        _y = 40 + i * 25
        if i == s.sel_wr:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 185), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 200), "TARGET MEASUREMENT:", s.c_ok)
    
    _best_str = str(int(s.wr_best * 10000) / 10000.0)
    _res_str = str(int(s.wr_result * 10000) / 10000.0)
    
    _draw.text(Vector(5, 220), "BEST WIRE: " + _best_str + " " + _u_d, s.c_fg)
    _draw.text(Vector(5, 245), "OVER WIRE: " + _res_str + " " + _u_d, s.c_hlt)
    _draw.swap()

def _draw_weight(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "STOCK WEIGHT CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
    _matl_names = ["STEEL", "ALUMINUM", "BRASS", "STAINLESS", "CAST IRON", "TITANIUM", "COPPER", "PLASTIC"]
    
    opts = [
        "MATL : [ " + _matl_names[s.wt_matl] + " ]",
        "DIAM :   " + str(round(s.wt_diam, 3)) + " " + _u_d,
        "LEN  :   " + str(round(s.wt_len, 3)) + " " + _u_d,
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(4):
        _y = 40 + i * 25
        if i == s.sel_wt:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 160), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 175), "ESTIMATED MASS:", s.c_ok)
    
    _u_w = "kg" if s.val_unit == UNIT_METRIC else "lbs"
    _res_str = str(int(s.wt_result * 1000) / 1000.0)
    _draw.text(Vector(5, 205), _res_str + " " + _u_w, s.c_fg)
    _draw.swap()

def _draw_speed(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "SPEEDS & FEEDS CALC", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
    _u_v = "m/min" if s.val_unit == UNIT_METRIC else "SFM"
    _v_lbl = "Vc  :    " if s.val_unit == UNIT_METRIC else "SFM :    "
    
    opts = [
        "DIAM:    " + str(round(s.sp_diam, 3)) + " " + _u_d,
        _v_lbl + str(round(s.sp_vc, 2)) + " " + _u_v,
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(3):
        _y = 40 + i * 25
        if i == s.sel_sp:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 160), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 175), "REQUIRED SPINDLE SPEED:", s.c_ok)
    _draw.text(Vector(5, 205), str(int(s.sp_rpm)) + " RPM", s.c_fg)
    _draw.swap()

def _draw_bolt_circle(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw

    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "BOLT CIRCLE CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)

    _u = "mm" if s.val_unit == UNIT_METRIC else "in"

    opts = [
        "CIRCLE DIAM: " + str(s.bc_diam) + " " + _u,
        "NUM HOLES  : " + str(s.bc_holes),
        "< RETURN TO TOOLBOX"
    ]

    v_pos = Vector(0, 0)
    for i in range(3):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_bc:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)

    _draw.fill_rectangle(Vector(0, 125), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 135), "HOLE COORDINATES (X, Y):", s.c_ok)

    _vis = 6; _lh = 20; _sy = 160
    max_scroll = max(0, len(s.bc_results) - _vis)
    s.bc_scroll_pos = min(s.bc_scroll_pos, max_scroll)

    v_pos.x = 10
    for i in range(_vis):
        _idx = s.bc_scroll_pos + i
        if _idx < len(s.bc_results):
            x, y = s.bc_results[_idx]
            v_pos.y = _sy + i * _lh; _draw.text(v_pos, f"{_idx+1}: ({x}, {y})", s.c_fg)

    _draw.swap()

def _draw_gears(view_manager):
    s = state
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "CHANGE GEAR CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u = "mm" if s.val_unit == UNIT_METRIC else "TPI"
    
    opts = [
        "PITCH TO CUT: " + str(s.gr_pitch_cut) + " " + _u,
        "LEADSCREW   : " + str(s.gr_pitch_ls) + " " + _u,
        "AVAIL GEARS : " + s.gr_gears[:20] + "...",
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(4):
        _y = 40 + i * 25
        if i == s.sel_gr:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 150), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 160), "POSSIBLE GEAR COMBINATIONS:", s.c_ok)
    
    if not s.gr_results:
        _draw.text(Vector(10, 185), "No solutions found.", s.c_warn)
    else:
        for i, res in enumerate(s.gr_results):
            if i < 5: _draw.text(Vector(10, 185 + i * 20), res, s.c_fg)
    _draw.swap()

def _draw_triangle(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "RIGHT TRIANGLE SOLVER", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _modes = ["A & B", "A & C", "B & C", "A & Ang(a)", "B & Ang(a)", "C & Ang(a)"]
    _v1_lbls = ["SIDE A", "SIDE A", "SIDE B", "SIDE A", "SIDE B", "SIDE C"]
    _v2_lbls = ["SIDE B", "SIDE C", "SIDE C", "ANGLE a", "ANGLE a", "ANGLE a"]
    
    opts = [
        "GIVEN: < " + _modes[s.tr_mode] + " >",
        _v1_lbls[s.tr_mode] + ": " + str(round(s.tr_v1, 4)),
        _v2_lbls[s.tr_mode] + ": " + str(round(s.tr_v2, 4)),
        "< RETURN TO TOOLBOX"
    ]
    
    v_pos = Vector(0, 0)
    for i in range(4):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_tr:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 150), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 160), "RESULTS:", s.c_ok)
    _draw.text(Vector(10, 185), "Side A : " + str(round(s.tr_A, 4)), s.c_fg)
    _draw.text(Vector(10, 205), "Side B : " + str(round(s.tr_B, 4)), s.c_fg)
    _draw.text(Vector(10, 225), "Side C : " + str(round(s.tr_C, 4)), s.c_fg)
    _draw.text(Vector(160, 185), "Ang(a): " + str(round(s.tr_ang_a, 3)) + " DEG", s.c_fg)
    _draw.text(Vector(160, 205), "Ang(b): " + str(round(s.tr_ang_b, 3)) + " DEG", s.c_fg)
    _draw.text(Vector(160, 225), "Ang(c): 90 DEG", s.c_fg)
    _draw.swap()

def _draw_arc(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "ARC & CHORD CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u = "mm" if s.val_unit == UNIT_METRIC else "in"
    
    opts = [
        "RADIUS:  " + str(round(s.ar_radius, 4)) + " " + _u,
        "ANGLE :  " + str(round(s.ar_angle, 3)) + " DEG",
        "< RETURN TO TOOLBOX"
    ]
    
    v_pos = Vector(0, 0)
    for i in range(3):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_ar:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 135), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 145), "RESULTS:", s.c_ok)
    
    _draw.text(Vector(10, 170), "ARC LEN : " + str(round(s.ar_arc_len, 4)) + " " + _u, s.c_fg)
    _draw.text(Vector(10, 195), "CHORD   : " + str(round(s.ar_chord, 4)) + " " + _u, s.c_fg)
    _draw.swap()

def _draw_drill_pt(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "DRILL POINT DEPTH CALC", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u = "mm" if s.val_unit == UNIT_METRIC else "in"
    
    opts = [
        "DIAM :   " + str(round(s.dp_diam, 4)) + " " + _u,
        "ANGLE:   " + str(round(s.dp_angle, 1)) + " DEG",
        "< RETURN TO TOOLBOX"
    ]
    
    v_pos = Vector(0, 0)
    for i in range(3):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_dp:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 135), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 145), "EXTRA POINT DEPTH:", s.c_ok)
    
    _draw.text(Vector(10, 170), "DEPTH: " + str(round(s.dp_result, 4)) + " " + _u, s.c_fg)
    _draw.swap()

def _draw_tap_hole(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "TAP DRILL CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
    _u_p = "mm" if s.val_unit == UNIT_METRIC else "TPI"
    
    opts = [
        "MAJOR DIAM:  " + str(round(s.td_diam, 4)) + " " + _u_d,
        "PITCH     :  " + str(round(s.td_pitch, 3)) + " " + _u_p,
        "< RETURN TO TOOLBOX"
    ]
    
    v_pos = Vector(0, 0)
    for i in range(3):
        _y = 40 + i * 25
        v_pos.y = _y
        if i == s.sel_td:
            v_pos.x = 5; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_hlt)
        else:
            v_pos.x = 20; _draw.text(v_pos, opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 135), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 145), "REQUIRED DRILL SIZE (75%):", s.c_ok)
    
    _draw.text(Vector(10, 170), "DRILL: " + str(round(s.td_result, 4)) + " " + _u_d, s.c_fg)
    _draw.swap()

def _draw_calc(view_manager):
    '''Draws the main calculator interface (Dual-Column Dashboard)'''
    s = state 
    _draw = view_manager.draw
    v_pos = Vector(0, 0); v_size = Vector(0, 0)
    
    _draw.clear(color=s.c_bg)
    v_pos.x = 5; v_pos.y = 5; _draw.text(v_pos, "LATHE-CALC v2.1", s.c_fg)
    v_pos.x = 0; v_pos.y = 22; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)

    _str_unit = "METRIC" if s.val_unit == UNIT_METRIC else "IMPERL"
    _active_tool_name = s.tool_profiles[s.active_tool_idx]["name"][:5]
    _r_val = s.tool_profiles[s.active_tool_idx]["rad_m"] if s.val_unit == UNIT_METRIC else s.tool_profiles[s.active_tool_idx]["rad_i"]
    _r_str = str(_r_val).lstrip('0') if str(_r_val).startswith('0.') else str(_r_val)
    _str_tool = "[" + _active_tool_name + "]R" + _r_str
    _str_type = "HOBBY" if s.val_type == TYPE_HOBBY else "INDUST"
    _str_proc = PROC_NAMES[s.val_proc]
    _str_pass = "ROUGH" if s.val_pass == PASS_ROUGH else "FINISH"
    
    _str_work = WORK_NAMES[s.val_work]
    
    _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
    _u_v = "m/m" if s.val_unit == UNIT_METRIC else "SFM"
    _u_f = "mm/r" if s.val_unit == UNIT_METRIC else "in/r"
    _l_v = "Vc  :" if s.val_unit == UNIT_METRIC else "SFM :"

    _diam_label = "D-DIA:" if s.val_proc == PROC_DRILL else "DIAM: "

    left_fields = [
        "UNIT: [" + _str_unit + "]",
        "SYS : [" + _str_type + "]",
        "WORK: [" + _str_work + "]",
        "TOOL: " + _str_tool,
        "PROC: [" + _str_proc + "]",
        "PASS: [" + _str_pass + "]",
        "[=] APPLY REC DOC"
    ]
    
    right_fields = [
        _diam_label + " " + str(s.val_diam) + " " + _u_d,
        "LEN : " + str(s.val_len) + " " + _u_d,
        _l_v + " " + str(s.val_vc) + " " + _u_v,
        "FEED: " + str(s.val_feed) + " " + _u_f,
        "DOC : " + str(s.val_doc) + " " + _u_d,
        "[>] TOOLBOX",
        "[?] HELP"
    ]

    v_pos.x = 155; v_pos.y = 30; v_size.x = 1; v_size.y = 150; _draw.fill_rectangle(v_pos, v_size, s.c_fg)

    for i in range(7):
        _y = 32 + i * 21
        v_pos.y = _y
        if i == s.sel_main:
            v_pos.x = 2; _draw.text(v_pos, ">", s.c_hlt)
            v_pos.x = 12; _draw.text(v_pos, left_fields[i], s.c_hlt)
        else:
            v_pos.x = 12; _draw.text(v_pos, left_fields[i], s.c_fg)
            
        r_idx = i + 7
        if r_idx < 14:
            _rf_color = s.c_err if (r_idx == FIELD_FEED and s.warn_high_feed) else (s.c_hlt if r_idx == s.sel_main else s.c_fg)
            if r_idx == s.sel_main:
                v_pos.x = 160; _draw.text(v_pos, ">", _rf_color)
                v_pos.x = 170; _draw.text(v_pos, right_fields[i], _rf_color)
            else:
                v_pos.x = 170; _draw.text(v_pos, right_fields[i], _rf_color)

    v_pos.x = 0; v_pos.y = 182; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    
    _f_l = "FEED(mm/m)" if s.val_unit == UNIT_METRIC else "FEED(in/m)"
    v_pos.x = 5; v_pos.y = 186; _draw.text(v_pos, "SPINDLE (RPM)", s.c_ok)
    if s.warn_coolant:
        v_pos.x = 108; v_pos.y = 184; v_size.x = 44; v_size.y = 11; _draw.fill_round_rectangle(v_pos, v_size, 4, s.c_sec)
        v_pos.x = 112; v_pos.y = 186; _draw.text(v_pos, "FLUID", s.c_bg)
        
    v_pos.x = 160; v_pos.y = 186; _draw.text(v_pos, _f_l, s.c_ok)
    
    _rpm_color = s.c_warn if s.warn_rpm_cap else s.c_fg
    v_pos.x = 5; v_pos.y = 202; _draw.text(v_pos, str(int(s.rpm_result)), _rpm_color)
    _feed_color = s.c_err if s.warn_high_feed else s.c_fg
    v_pos.x = 160; v_pos.y = 202; _draw.text(v_pos, str(s.feed_m_result), _feed_color)
    
    v_pos.x = 0; v_pos.y = 216; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    
    _pwr_color = s.c_err if s.warn_power_cap else s.c_fg
    v_pos.x = 5; v_pos.y = 221; _draw.text(v_pos, "EST PWR: " + s.pwr_result_str, _pwr_color)
    _time_color = s.c_err if s.warn_high_feed else s.c_hlt
    v_pos.x = 160; v_pos.y = 221; _draw.text(v_pos, "TIME: " + s.time_result, _time_color)
    
    _ra_color = s.c_warn if s.warn_poor_finish else s.c_fg
    v_pos.x = 5; v_pos.y = 237; _draw.text(v_pos, "EST Ra : " + s.ra_result_str, _ra_color)
    v_pos.x = 160; v_pos.y = 237; _draw.text(v_pos, "MAX DOC: " + s.rec_doc, s.c_fg)
    
    v_pos.x = 0; v_pos.y = 253; v_size.x = 320; v_size.y = 1; _draw.fill_rectangle(v_pos, v_size, s.c_fg)
    _y_warn = 259
    _max_rpm = MAX_LATHE_RPM_HOBBY if s.val_type == TYPE_HOBBY else MAX_LATHE_RPM_INDUST
    
    if s.warn_rpm_cap:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, "! RPM CAPPED (MAX " + str(int(_max_rpm)) + ")", s.c_warn)
        _y_warn += 11
    if s.warn_carbide_spd:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, "! DIAM TOO SML FOR CARBIDE", s.c_err)
        _y_warn += 11
    if s.warn_high_feed:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, "! LINEAR FEED EXCEEDED", s.c_err)
        _y_warn += 11
    if s.warn_poor_finish:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, "! POOR SURFACE FINISH", s.c_warn)
        _y_warn += 11
    if s.warn_power_cap:
        v_pos.x = 5; v_pos.y = _y_warn; _draw.text(v_pos, "! MOTOR POWER EXCEEDED", s.c_err)
        _y_warn += 11
        
    _draw.swap()

def run(view_manager):  
    global dirty_save, save_timer
    s = state 
    from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER
    _im = view_manager.input_manager
    _btn = _im.button
    _needs_redraw = False
    
    # Delta-Save Background Process
    if dirty_save and _btn == -1:
        if save_timer > 0:
            save_timer -= 1
        else:
            save_settings(view_manager)

    # Handle Text Screen Scrolling
    if s.current_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL, SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE, SCREEN_FITS, SCREEN_HELP, SCREEN_KNURL, SCREEN_HARDNESS):
        if _btn == BUTTON_BACK:
            s.current_screen = SCREEN_TOOLBOX if s.current_screen != SCREEN_HELP else SCREEN_CALC
            s.text_lines = []
            gc.collect()
            _im.reset(); _draw_ui(view_manager)
        elif _btn == BUTTON_UP:
            if s.scroll_pos > 0: s.scroll_pos -= 1; _needs_redraw = True
        elif _btn == BUTTON_DOWN:
            if s.scroll_pos < len(s.text_lines) - 16: s.scroll_pos += 1; _needs_redraw = True
        if _needs_redraw: _im.reset(); _draw_ui(view_manager)
        return
        
    # Handle Keyboard Input (Using Picoware System Keyboard)
    if s.is_typing:
        kb = view_manager.keyboard
        if not kb.is_finished:
            # Pass s.kb_force into kb.run to guarantee it renders on the exact frame it opens
            if kb.run(True, s.kb_force) is False:
                s.is_typing = False
                s.kb_force = False
                kb.reset()
                _im.reset(); _draw_ui(view_manager)
            s.kb_force = False
        else:
            try:
                if s.current_screen == SCREEN_TOOL_MGR and s.sel_tm in (TM_RENAME, TM_NEW):
                    _str_val = kb.response.strip()
                    if _str_val:
                        if s.sel_tm == TM_RENAME:
                            s.tool_profiles[s.active_tool_idx]["name"] = _str_val[:12]
                        else:
                            s.tool_profiles.append({"name": _str_val[:12], "type": CUT_HSS, "rad_m": 0.4, "rad_i": 0.015, "angle": 0.0})
                            s.active_tool_idx = len(s.tool_profiles) - 1
                else:
                    new_val = float(kb.response)
                    if s.current_screen == SCREEN_CALC:
                        if s.sel_main == FIELD_DIAM: s.val_diam = new_val
                        elif s.sel_main == FIELD_LEN: s.val_len = new_val
                        elif s.sel_main == FIELD_VC: s.val_vc = new_val
                        elif s.sel_main == FIELD_FEED: s.val_feed = new_val
                        elif s.sel_main == FIELD_DOC: s.val_doc = new_val
                    elif s.current_screen == SCREEN_TAPER:
                        if s.sel_tp == TP_D: s.tp_D = new_val
                        elif s.sel_tp == TP_d: s.tp_d = new_val
                        elif s.sel_tp == TP_L: s.tp_L = new_val
                    elif s.current_screen == SCREEN_THREAD:
                        if s.sel_th == TH_DIAM: s.th_diam = new_val
                        elif s.sel_th == TH_PITCH: s.th_pitch = new_val
                    elif s.current_screen == SCREEN_CONVERT:
                        if s.sel_cv == CV_VAL: s.cv_val = new_val
                    elif s.current_screen == SCREEN_WIRE:
                        if s.sel_wr == WR_DIAM: s.wr_diam = new_val
                        elif s.sel_wr == WR_PITCH: s.wr_pitch = new_val
                        elif s.sel_wr == WR_WIRE: s.wr_wire = new_val
                    elif s.current_screen == SCREEN_WEIGHT:
                        if s.sel_wt == WT_DIAM: s.wt_diam = new_val
                        elif s.sel_wt == WT_LEN: s.wt_len = new_val
                    elif s.current_screen == SCREEN_SPEED:
                        if s.sel_sp == SP_DIAM: s.sp_diam = new_val
                        elif s.sel_sp == SP_VC: s.sp_vc = new_val
                    elif s.current_screen == SCREEN_BOLT_CIRCLE:
                        if s.sel_bc == BC_DIAM: s.bc_diam = new_val
                        elif s.sel_bc == BC_HOLES: s.bc_holes = int(new_val)
                    elif s.current_screen == SCREEN_GEARS:
                        if s.sel_gr == GR_PITCH_CUT: s.gr_pitch_cut = new_val
                        elif s.sel_gr == GR_PITCH_LS: s.gr_pitch_ls = new_val
                        elif s.sel_gr == GR_GEARS: s.gr_gears = kb.response.strip()
                    elif s.current_screen == SCREEN_TRIANGLE:
                        if s.sel_tr == TR_V1: s.tr_v1 = new_val
                        elif s.sel_tr == TR_V2: s.tr_v2 = new_val
                    elif s.current_screen == SCREEN_ARC:
                        if s.sel_ar == AR_RADIUS: s.ar_radius = new_val
                        elif s.sel_ar == AR_ANGLE: s.ar_angle = new_val
                    elif s.current_screen == SCREEN_DRILL_PT:
                        if s.sel_dp == DP_DIAM: s.dp_diam = new_val
                        elif s.sel_dp == DP_ANGLE: s.dp_angle = new_val
                    elif s.current_screen == SCREEN_TAP_HOLE:
                        if s.sel_td == TD_DIAM: s.td_diam = new_val
                        elif s.sel_td == TD_PITCH: s.td_pitch = new_val

                    elif s.current_screen == SCREEN_OPTIONS:
                        if s.sel_opt == OPT_FEED_CAP:
                            if s.val_unit == UNIT_METRIC: s.max_feed_m = new_val
                            else: s.max_feed_i = new_val
                        elif s.sel_opt == OPT_RPM_CAP:
                            if s.val_type == TYPE_HOBBY: s.max_rpm_hobby = new_val
                            else: s.max_rpm_indust = new_val
                        elif s.sel_opt == OPT_MOTOR_PWR:
                            _new_kw = new_val / 1.34102 if s.val_unit == UNIT_IMP else new_val
                            if s.val_type == TYPE_HOBBY: s.motor_kw_hobby = _new_kw
                            else: s.motor_kw_indust = _new_kw
                        elif s.sel_opt == OPT_MOTOR_EFF:
                            s.motor_eff = max(0.1, min(1.0, new_val / 100.0))
                    elif s.current_screen == SCREEN_TOOL_MGR:
                        if s.sel_tm == TM_RAD:
                            if s.val_unit == UNIT_METRIC:
                                s.tool_profiles[s.active_tool_idx]["rad_m"] = max(0.001, new_val)
                            else:
                                s.tool_profiles[s.active_tool_idx]["rad_i"] = max(0.001, new_val)
                        elif s.sel_tm == TM_ANGLE:
                            s.tool_profiles[s.active_tool_idx]["angle"] = new_val
                _calculate()
                save_settings(view_manager, force=True)
            except Exception: pass
            s.is_typing = False
            s.kb_force = False
            kb.reset()
            _im.reset(); _draw_ui(view_manager)
        return

    if _btn == BUTTON_BACK:
        if s.current_screen == SCREEN_CALC:
            _im.reset() 
            view_manager.back()
        else:
            s.current_screen = SCREEN_TOOLBOX if s.current_screen in (SCREEN_TAPER, SCREEN_THREAD, SCREEN_CONVERT, SCREEN_OPTIONS, SCREEN_TOOL_MGR, SCREEN_WIRE, SCREEN_WEIGHT, SCREEN_SPEED, SCREEN_GEARS, SCREEN_BOLT_CIRCLE, SCREEN_TRIANGLE, SCREEN_ARC, SCREEN_DRILL_PT, SCREEN_GRAPH, SCREEN_TAP_HOLE) else SCREEN_CALC
            _im.reset(); _draw_ui(view_manager)
        return

    # Sub-Menu Routing
    if s.current_screen == SCREEN_TOOLBOX:
        num_cats = len(TOOLBOX_MENU)

        if _btn == BUTTON_DOWN:
            if s.sel_tb_col == 0: # Category column
                s.sel_tb_cat = (s.sel_tb_cat + 1) % (num_cats + 1) # +1 for BACK
                s.sel_tb_item = 0
            else: # Item column
                if s.sel_tb_cat < num_cats:
                    num_items = len(TOOLBOX_MENU[s.sel_tb_cat][1])
                    if num_items > 0: s.sel_tb_item = (s.sel_tb_item + 1) % num_items
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            if s.sel_tb_col == 0: # Category column
                s.sel_tb_cat = (s.sel_tb_cat - 1) % (num_cats + 1)
                s.sel_tb_item = 0
            else: # Item column
                if s.sel_tb_cat < num_cats:
                    num_items = len(TOOLBOX_MENU[s.sel_tb_cat][1])
                    if num_items > 0: s.sel_tb_item = (s.sel_tb_item - 1) % num_items
            _needs_redraw = True
        elif _btn == BUTTON_RIGHT:
            if s.sel_tb_col == 0 and s.sel_tb_cat < num_cats:
                s.sel_tb_col = 1; _needs_redraw = True
        elif _btn == BUTTON_LEFT:
            if s.sel_tb_col == 1: s.sel_tb_col = 0; _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tb_col == 0: # In category column
                if s.sel_tb_cat == num_cats: # Selected BACK
                    s.current_screen = SCREEN_CALC
                else: # Switch to item column
                    s.sel_tb_col = 1
            else: # In item column
                if s.sel_tb_cat < num_cats:
                    num_items = len(TOOLBOX_MENU[s.sel_tb_cat][1])
                    if num_items > 0:
                        target_screen = TOOLBOX_MENU[s.sel_tb_cat][1][s.sel_tb_item][1]
                    if target_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL, SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE, SCREEN_FITS, SCREEN_KNURL, SCREEN_HARDNESS):
                        text_map = {SCREEN_CHART: "CHART", SCREEN_TAP: "TAP", SCREEN_DRILL: "DRILL", SCREEN_CENTER: "CENTER", SCREEN_MORSE: "MORSE", SCREEN_CLEAR: "CLEAR", SCREEN_SURFACE: "SURFACE", SCREEN_FITS: "FITS", SCREEN_KNURL: "KNURL", SCREEN_HARDNESS: "HARDNESS"}
                        s.current_screen = target_screen
                        _load_text(text_map[target_screen])
                    else:
                        s.current_screen = target_screen
            _needs_redraw = True
            
    elif s.current_screen == SCREEN_OPTIONS:
        if _btn == BUTTON_DOWN: s.sel_opt = (s.sel_opt + 1) % 8; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_opt = (s.sel_opt - 1) % 8; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            if s.sel_opt == OPT_THEME:
                _dir = 1 if _btn == BUTTON_RIGHT else -1
                s.theme_id = (s.theme_id + _dir) % 4
                _apply_theme()
                queue_save()
                _needs_redraw = True
            elif s.sel_opt == OPT_FEED_CAP:
                if s.val_unit == UNIT_METRIC:
                    s.max_feed_m = max(10.0, s.max_feed_m + (10.0 if _btn == BUTTON_RIGHT else -10.0))
                else:
                    s.max_feed_i = max(1.0, s.max_feed_i + (1.0 if _btn == BUTTON_RIGHT else -1.0))
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_opt == OPT_RPM_CAP:
                _adj = 100.0 if _btn == BUTTON_RIGHT else -100.0
                if s.val_type == TYPE_HOBBY:
                    s.max_rpm_hobby = max(100.0, s.max_rpm_hobby + _adj)
                else:
                    s.max_rpm_indust = max(100.0, s.max_rpm_indust + _adj)
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_opt == OPT_RA_DISP:
                s.ra_as_ngrade = not s.ra_as_ngrade
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_opt == OPT_MOTOR_EFF:
                s.motor_eff = max(0.1, min(1.0, s.motor_eff + (0.05 if _btn == BUTTON_RIGHT else -0.05)))
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_opt == OPT_AUTO_DOC:
                s.auto_rec_doc = not s.auto_rec_doc
                _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_opt == OPT_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_opt == OPT_FEED_CAP:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "MAX FEED LIMIT"
                kb.response = str(s.max_feed_m if s.val_unit == UNIT_METRIC else s.max_feed_i)
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            elif s.sel_opt == OPT_RPM_CAP:
                kb = view_manager.keyboard
                kb.reset()
                _sys_str = "HOBBY" if s.val_type == TYPE_HOBBY else "INDUST"
                kb.title = "MAX RPM (" + _sys_str + ")"
                kb.response = str(int(s.max_rpm_hobby if s.val_type == TYPE_HOBBY else s.max_rpm_indust))
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            elif s.sel_opt == OPT_MOTOR_PWR:
                kb = view_manager.keyboard
                kb.reset()
                _sys_str = "HOBBY" if s.val_type == TYPE_HOBBY else "INDUST"
                _pwr_u = "HP" if s.val_unit == UNIT_IMP else "kW"
                _pwr_kw = s.motor_kw_hobby if s.val_type == TYPE_HOBBY else s.motor_kw_indust
                _pwr_disp = round(_pwr_kw * 1.34102, 2) if s.val_unit == UNIT_IMP else round(_pwr_kw, 2)
                kb.title = "MOTOR POWER (" + _sys_str + " " + _pwr_u + ")"
                kb.response = str(_pwr_disp)
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            elif s.sel_opt == OPT_MOTOR_EFF:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "MOTOR EFFICIENCY (%)"
                kb.response = str(int(s.motor_eff * 100))
                s.is_typing = True; s.kb_force = True; _im.reset(); return
                
    elif s.current_screen == SCREEN_TOOL_MGR:
        if _btn == BUTTON_DOWN: s.sel_tm = (s.sel_tm + 1) % 8; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_tm = (s.sel_tm - 1) % 8; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1 if _btn == BUTTON_RIGHT else -1
            if s.sel_tm == TM_SELECT:
                s.active_tool_idx = (s.active_tool_idx + _dir) % len(s.tool_profiles)
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_tm == TM_TYPE:
                s.tool_profiles[s.active_tool_idx]["type"] = CUT_CARB if s.tool_profiles[s.active_tool_idx]["type"] == CUT_HSS else CUT_HSS
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_tm == TM_RAD:
                if s.val_unit == UNIT_METRIC:
                    new_rad = s.tool_profiles[s.active_tool_idx]["rad_m"] + (0.1 * _dir)
                    s.tool_profiles[s.active_tool_idx]["rad_m"] = round(max(0.001, new_rad), 3)
                else:
                    new_rad = s.tool_profiles[s.active_tool_idx]["rad_i"] + (0.005 * _dir)
                    s.tool_profiles[s.active_tool_idx]["rad_i"] = round(max(0.001, new_rad), 4)
                _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_tm == TM_ANGLE:
                new_ang = s.tool_profiles[s.active_tool_idx].get("angle", 0.0) + (1.0 * _dir)
                s.tool_profiles[s.active_tool_idx]["angle"] = round(new_ang, 1)
                _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tm == TM_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_tm == TM_NEW:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "NEW TOOL NAME"
                kb.response = "Tool " + str(len(s.tool_profiles) + 1)
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            elif s.sel_tm == TM_RENAME:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "RENAME TOOL"
                kb.response = s.tool_profiles[s.active_tool_idx]["name"]
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            elif s.sel_tm == TM_DEL:
                if len(s.tool_profiles) > 1:
                    s.tool_profiles.pop(s.active_tool_idx)
                    s.active_tool_idx = max(0, s.active_tool_idx - 1)
                    _calculate(); queue_save(); _needs_redraw = True
            elif s.sel_tm == TM_RAD:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "NOSE RADIUS"
                kb.response = str(s.tool_profiles[s.active_tool_idx]["rad_m"] if s.val_unit == UNIT_METRIC else s.tool_profiles[s.active_tool_idx]["rad_i"])
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            elif s.sel_tm == TM_ANGLE:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "TOOL ANGLE (DEG)"
                kb.response = str(s.tool_profiles[s.active_tool_idx].get("angle", 0.0))
                s.is_typing = True; s.kb_force = True; _im.reset(); return
            
    elif s.current_screen == SCREEN_GEARS:
        if _btn == BUTTON_DOWN: s.sel_gr = (s.sel_gr + 1) % 4; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_gr = (s.sel_gr - 1) % 4; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _step = 0.05 if s.val_unit == UNIT_METRIC else 1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_gr == GR_PITCH_CUT: s.gr_pitch_cut = round(max(0.01, s.gr_pitch_cut + (_dir * _step)), _rnd)
            elif s.sel_gr == GR_PITCH_LS: s.gr_pitch_ls = round(max(0.01, s.gr_pitch_ls + (_dir * _step)), _rnd)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_gr == GR_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            else:
                kb = view_manager.keyboard; kb.reset()
                if s.sel_gr == GR_PITCH_CUT:
                    kb.title = "PITCH TO CUT"
                    kb.response = str(s.gr_pitch_cut)
                elif s.sel_gr == GR_PITCH_LS:
                    kb.title = "LEADSCREW PITCH"
                    kb.response = str(s.gr_pitch_ls)
                elif s.sel_gr == GR_GEARS:
                    kb.title = "AVAILABLE GEARS (CSV)"
                    kb.response = s.gr_gears
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_BOLT_CIRCLE:
        if _btn == BUTTON_DOWN:
            if s.sel_bc < 2: s.sel_bc += 1
            else: s.bc_scroll_pos = min(s.bc_scroll_pos + 1, max(0, len(s.bc_results) - 6))
            _needs_redraw = True
        elif _btn == BUTTON_UP:
            if s.sel_bc > 0: s.sel_bc -= 1
            else: s.bc_scroll_pos = max(0, s.bc_scroll_pos - 1)
            _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_bc == BC_DIAM:
                s.bc_diam = round(max(0.001, s.bc_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_bc == BC_HOLES:
                s.bc_holes = max(2, s.bc_holes + int(_dir))
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_bc == BC_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_bc in (BC_DIAM, BC_HOLES):
                kb = view_manager.keyboard; kb.reset()
                if s.sel_bc == BC_DIAM: kb.title = "CIRCLE DIAMETER"; kb.response = str(s.bc_diam)
                else: kb.title = "NUMBER OF HOLES"; kb.response = str(s.bc_holes)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_TRIANGLE:
        if _btn == BUTTON_DOWN: s.sel_tr = (s.sel_tr + 1) % 4; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_tr = (s.sel_tr - 1) % 4; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            if s.sel_tr == TR_MODE: s.tr_mode = int((s.tr_mode + _dir) % 6)
            elif s.sel_tr == TR_V1: s.tr_v1 = max(0.001, s.tr_v1 + (_dir * 1.0))
            elif s.sel_tr == TR_V2: s.tr_v2 = max(0.001, s.tr_v2 + (_dir * 1.0))
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tr == TR_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_tr in (TR_V1, TR_V2):
                kb = view_manager.keyboard; kb.reset()
                _v1_lbls = ["SIDE A", "SIDE A", "SIDE B", "SIDE A", "SIDE B", "SIDE C"]
                _v2_lbls = ["SIDE B", "SIDE C", "SIDE C", "ANGLE a", "ANGLE a", "ANGLE a"]
                if s.sel_tr == TR_V1: kb.title = _v1_lbls[s.tr_mode]; kb.response = str(s.tr_v1)
                else: kb.title = _v2_lbls[s.tr_mode]; kb.response = str(s.tr_v2)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_ARC:
        if _btn == BUTTON_DOWN: s.sel_ar = (s.sel_ar + 1) % 3; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_ar = (s.sel_ar - 1) % 3; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_ar == AR_RADIUS: s.ar_radius = round(max(0.001, s.ar_radius + (_dir * 1.0)), _rnd)
            elif s.sel_ar == AR_ANGLE: s.ar_angle = round(max(0.001, s.ar_angle + (_dir * 1.0)), 3)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_ar == AR_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_ar in (AR_RADIUS, AR_ANGLE):
                kb = view_manager.keyboard; kb.reset()
                if s.sel_ar == AR_RADIUS: kb.title = "RADIUS"; kb.response = str(s.ar_radius)
                else: kb.title = "ANGLE (DEG)"; kb.response = str(s.ar_angle)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_DRILL_PT:
        if _btn == BUTTON_DOWN: s.sel_dp = (s.sel_dp + 1) % 3; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_dp = (s.sel_dp - 1) % 3; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_dp == DP_DIAM: s.dp_diam = round(max(0.001, s.dp_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_dp == DP_ANGLE:
                if s.dp_angle == 118.0 and _dir > 0: s.dp_angle = 135.0
                elif s.dp_angle == 135.0 and _dir < 0: s.dp_angle = 118.0
                else: s.dp_angle = round(max(1.0, min(179.0, s.dp_angle + (_dir * 1.0))), 1)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_dp == DP_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_dp in (DP_DIAM, DP_ANGLE):
                kb = view_manager.keyboard; kb.reset()
                if s.sel_dp == DP_DIAM: kb.title = "DRILL DIAMETER"; kb.response = str(s.dp_diam)
                else: kb.title = "POINT ANGLE (DEG)"; kb.response = str(s.dp_angle)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_TAP_HOLE:
        if _btn == BUTTON_DOWN: s.sel_td = (s.sel_td + 1) % 3; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_td = (s.sel_td - 1) % 3; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_td == TD_DIAM: s.td_diam = round(max(0.001, s.td_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_td == TD_PITCH: s.td_pitch = round(max(0.01, s.td_pitch + (_dir * (0.1 if s.val_unit == UNIT_METRIC else 1.0))), _rnd)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_td == TD_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_td in (TD_DIAM, TD_PITCH):
                kb = view_manager.keyboard; kb.reset()
                if s.sel_td == TD_DIAM: kb.title = "MAJOR DIAMETER"; kb.response = str(s.td_diam)
                else: kb.title = "PITCH / TPI"; kb.response = str(s.td_pitch)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_TAPER:
        if _btn == BUTTON_DOWN: s.sel_tp = (s.sel_tp + 1) % 4; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_tp = (s.sel_tp - 1) % 4; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _st = 1.0 if s.val_unit == UNIT_METRIC else 0.1
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_tp == TP_D: s.tp_D = round(max(0.001, s.tp_D + (_dir * _st)), _rnd)
            elif s.sel_tp == TP_d: s.tp_d = round(max(0.001, s.tp_d + (_dir * _st)), _rnd)
            elif s.sel_tp == TP_L: s.tp_L = round(max(0.001, s.tp_L + (_dir * _st)), _rnd)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tp == TP_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            else:
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_tp == TP_D: 
                    kb.title = "LARGE DIAMETER"
                    kb.response = str(s.tp_D)
                elif s.sel_tp == TP_d: 
                    kb.title = "SMALL DIAMETER"
                    kb.response = str(s.tp_d)
                elif s.sel_tp == TP_L: 
                    kb.title = "TAPER LENGTH"
                    kb.response = str(s.tp_L)
                s.is_typing = True; s.kb_force = True; _im.reset(); return
                
    elif s.current_screen == SCREEN_THREAD:
        if _btn == BUTTON_DOWN: s.sel_th = (s.sel_th + 1) % 4; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_th = (s.sel_th - 1) % 4; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.th_type == TH_METRIC else 4
            if s.sel_th == TH_TYPE:
                s.th_type = TH_UNIFIED if s.th_type == TH_METRIC else TH_METRIC
            elif s.sel_th == TH_DIAM: 
                s.th_diam = round(max(0.001, s.th_diam + (_dir * (1.0 if s.th_type == TH_METRIC else 0.01))), _rnd)
            elif s.sel_th == TH_PITCH: 
                s.th_pitch = round(max(0.01, s.th_pitch + (_dir * (0.05 if s.th_type == TH_METRIC else 1.0))), _rnd)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_th == TH_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_th in (TH_DIAM, TH_PITCH):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_th == TH_DIAM: 
                    kb.title = "MAJOR DIAMETER"
                    kb.response = str(s.th_diam)
                elif s.sel_th == TH_PITCH: 
                    kb.title = "PITCH / TPI"
                    kb.response = str(s.th_pitch)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_CONVERT:
        if _btn == BUTTON_DOWN: s.sel_cv = (s.sel_cv + 1) % 3; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_cv = (s.sel_cv - 1) % 3; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            if s.sel_cv == CV_UNIT:
                s.cv_unit = UNIT_IMP if s.cv_unit == UNIT_METRIC else UNIT_METRIC
            elif s.sel_cv == CV_VAL:
                _step = 1.0 if s.cv_unit == UNIT_METRIC else 0.1
                _rnd = 3 if s.cv_unit == UNIT_METRIC else 4
                s.cv_val = round(max(0.001, s.cv_val + ((1.0 if _btn == BUTTON_RIGHT else -1.0) * _step)), _rnd)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_cv == CV_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_cv == CV_VAL:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "CONVERT VALUE"
                kb.response = str(s.cv_val)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_WIRE:
        if _btn == BUTTON_DOWN: s.sel_wr = (s.sel_wr + 1) % 5; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_wr = (s.sel_wr - 1) % 5; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.wr_type == TH_METRIC else 4
            if s.sel_wr == WR_TYPE:
                s.wr_type = TH_UNIFIED if s.wr_type == TH_METRIC else TH_METRIC
            elif s.sel_wr == WR_DIAM: 
                s.wr_diam = round(max(0.001, s.wr_diam + (_dir * (1.0 if s.wr_type == TH_METRIC else 0.01))), _rnd)
            elif s.sel_wr == WR_PITCH: 
                s.wr_pitch = round(max(0.01, s.wr_pitch + (_dir * (0.05 if s.wr_type == TH_METRIC else 1.0))), _rnd)
            elif s.sel_wr == WR_WIRE:
                s.wr_wire = round(max(0.001, s.wr_wire + (_dir * (0.1 if s.wr_type == TH_METRIC else 0.005))), _rnd + 1)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_wr == WR_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_wr in (WR_DIAM, WR_PITCH, WR_WIRE):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_wr == WR_DIAM: 
                    kb.title = "MAJOR DIAMETER"
                    kb.response = str(s.wr_diam)
                elif s.sel_wr == WR_PITCH: 
                    kb.title = "PITCH / TPI"
                    kb.response = str(s.wr_pitch)
                elif s.sel_wr == WR_WIRE:
                    kb.title = "WIRE DIAMETER"
                    kb.response = str(s.wr_wire)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_WEIGHT:
        if _btn == BUTTON_DOWN: s.sel_wt = (s.sel_wt + 1) % 4; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_wt = (s.sel_wt - 1) % 4; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_wt == WT_MATL:
                s.wt_matl = int((s.wt_matl + _dir) % 8)
            elif s.sel_wt == WT_DIAM: 
                s.wt_diam = round(max(0.001, s.wt_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_wt == WT_LEN: 
                s.wt_len = round(max(0.001, s.wt_len + (_dir * (5.0 if s.val_unit == UNIT_METRIC else 0.5))), _rnd)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_wt == WT_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_wt in (WT_DIAM, WT_LEN):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_wt == WT_DIAM: 
                    kb.title = "STOCK DIAMETER"
                    kb.response = str(s.wt_diam)
                elif s.sel_wt == WT_LEN: 
                    kb.title = "STOCK LENGTH"
                    kb.response = str(s.wt_len)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_SPEED:
        if _btn == BUTTON_DOWN: s.sel_sp = (s.sel_sp + 1) % 3; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_sp = (s.sel_sp - 1) % 3; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _rnd = 3 if s.val_unit == UNIT_METRIC else 4
            if s.sel_sp == SP_DIAM: 
                s.sp_diam = round(max(0.001, s.sp_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_sp == SP_VC: 
                s.sp_vc = round(max(1.0, s.sp_vc + (_dir * (5.0 if s.val_unit == UNIT_METRIC else 10.0))), 2)
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_sp == SP_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_sp in (SP_DIAM, SP_VC):
                kb = view_manager.keyboard
                kb.reset()
                if s.sel_sp == SP_DIAM: 
                    kb.title = "DIAMETER"
                    kb.response = str(s.sp_diam)
                elif s.sel_sp == SP_VC: 
                    kb.title = "CUTTING SPEED"
                    kb.response = str(s.sp_vc)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_CALC:
        if _btn == BUTTON_DOWN: s.sel_main = (s.sel_main + 1) % 14; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_main = (s.sel_main - 1) % 14; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            if s.sel_main == FIELD_UNIT:
                s.val_unit = UNIT_IMP if s.val_unit == UNIT_METRIC else UNIT_METRIC
                if s.val_unit == UNIT_IMP:
                    s.val_diam = round(s.val_diam / 25.4, 4)
                    s.val_len = round(s.val_len / 25.4, 4)
                else:
                    s.val_diam = round(s.val_diam * 25.4, 2)
                    s.val_len = round(s.val_len * 25.4, 2)
            elif s.sel_main == FIELD_CUTTER: 
                s.active_tool_idx = (s.active_tool_idx + int(_dir)) % len(s.tool_profiles)
            elif s.sel_main == FIELD_WORK: s.val_work = (s.val_work + int(_dir)) % 11
            elif s.sel_main == FIELD_TYPE: 
                s.val_type = TYPE_INDUST if s.val_type == TYPE_HOBBY else TYPE_HOBBY
            elif s.sel_main == FIELD_PROC: 
                s.val_proc = (s.val_proc + int(_dir)) % 6
            elif s.sel_main == FIELD_PASS: s.val_pass = PASS_FINISH if s.val_pass == PASS_ROUGH else PASS_ROUGH
            elif s.sel_main == FIELD_DIAM: 
                _rnd = 3 if s.val_unit == UNIT_METRIC else 4
                s.val_diam = round(max(0.001, s.val_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1))), _rnd)
            elif s.sel_main == FIELD_LEN: 
                _rnd = 3 if s.val_unit == UNIT_METRIC else 4
                s.val_len = round(max(0.001, s.val_len + (_dir * (5.0 if s.val_unit == UNIT_METRIC else 0.5))), _rnd)
            elif s.sel_main == FIELD_VC: 
                s.val_vc = round(max(1.0, s.val_vc + (_dir * (5.0 if s.val_unit == UNIT_METRIC else 10.0))), 2)
            elif s.sel_main == FIELD_FEED: 
                s.val_feed = max(0.001, s.val_feed + (_dir * (0.01 if s.val_unit == UNIT_METRIC else 0.001)))
                s.val_feed = round(s.val_feed, 4)
            elif s.sel_main == FIELD_DOC:
                s.val_doc = max(0.001, s.val_doc + (_dir * (0.1 if s.val_unit == UNIT_METRIC else 0.01)))
                s.val_doc = round(s.val_doc, 3)
                
            if s.sel_main in (FIELD_UNIT, FIELD_CUTTER, FIELD_WORK, FIELD_TYPE, FIELD_PROC, FIELD_PASS):
                _apply_safe_defaults()
                
            _calculate(); queue_save(); _needs_redraw = True

        elif _btn == BUTTON_CENTER:
            if s.sel_main == FIELD_MAIN_TOOLBOX:
                s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_main == FIELD_MAIN_HELP:
                s.current_screen = SCREEN_HELP
                _load_text("HELP"); _needs_redraw = True
            elif s.sel_main == FIELD_APPLY_DOC:
                _str = s.rec_doc.replace("mm", "").replace("in", "").replace("+", "")
                try:
                    if "-" in _str:
                        _parts = _str.split("-")
                        s.val_doc = round((float(_parts[0]) + float(_parts[1])) / 2.0, 4)
                    else:
                        s.val_doc = round(float(_str), 4)
                    _calculate(); queue_save(); _needs_redraw = True
                except Exception:
                    pass
            elif s.sel_main in (FIELD_DIAM, FIELD_LEN, FIELD_VC, FIELD_FEED, FIELD_DOC):
                kb = view_manager.keyboard
                kb.reset()
                
                _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
                _u_v = "m/m" if s.val_unit == UNIT_METRIC else "SFM"
                _u_f = "mm/r" if s.val_unit == UNIT_METRIC else "in/r"
                
                if s.sel_main == FIELD_DIAM: 
                    _t_title = "DRILL DIAMETER" if s.val_proc == PROC_DRILL else "DIAMETER"
                    kb.title = _t_title + " (" + _u_d + ")"
                    kb.response = str(s.val_diam)
                elif s.sel_main == FIELD_LEN: 
                    kb.title = "LENGTH (" + _u_d + ")"
                    kb.response = str(s.val_len)
                elif s.sel_main == FIELD_VC: 
                    kb.title = "SPEED (" + _u_v + ")"
                    kb.response = str(s.val_vc)
                elif s.sel_main == FIELD_FEED: 
                    kb.title = "FEED (" + _u_f + ")"
                    kb.response = str(s.val_feed)
                elif s.sel_main == FIELD_DOC: 
                    kb.title = "DEPTH OF CUT (" + _u_d + ")"
                    kb.response = str(s.val_doc)
                    
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    if _needs_redraw:
        _im.reset()
        _draw_ui(view_manager)

def stop(view_manager):
    '''Stop the app, execute a final save, and clear memory'''
    from gc import collect
    global state, storage, dirty_save, save_timer, _last_saved_json
    
    save_settings(view_manager, force=True)
    
    if view_manager.keyboard:
        view_manager.keyboard.reset()
        
    del state; state = None
    storage = None
    dirty_save = False
    save_timer = 0
    _last_saved_json = ""
    
    collect()