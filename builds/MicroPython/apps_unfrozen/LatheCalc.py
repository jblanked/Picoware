# ==========================================
# LATHE-CALC v1.5
# ==========================================
# Help Text: Use UP/DOWN to move the cursor. 
# Use LEFT/RIGHT to toggle bracketed settings or adjust numbers.
# Press CENTER on a number to manually type exact values.
# Results update instantly on the lower panel!
# Press BACK to exit the application.
# ==========================================

import json
import gc

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

# Constants - Field States (Main)
FIELD_UNIT = 0; FIELD_TYPE = 1; FIELD_WORK = 2; FIELD_CUTTER = 3
FIELD_PROC = 4; FIELD_PASS = 5; FIELD_DIAM = 6; FIELD_LEN = 7
FIELD_VC = 8; FIELD_FEED = 9; FIELD_MAIN_TOOLBOX = 10; FIELD_MAIN_HELP = 11

# Constants - Field States (Toolbox)
TB_CHART = 0; TB_TAP = 1; TB_DRILL = 2; TB_CENTER = 3; TB_MORSE = 4
TB_CLEAR = 5; TB_SURFACE = 6; TB_FITS = 7; TB_TAPER = 8; TB_THREAD = 9
TB_CONVERT = 10; TB_KNURL = 11; TB_OPTIONS = 12; TB_BACK = 13

# Constants - Field States (Sub-Tools)
TP_D = 0; TP_d = 1; TP_L = 2; TP_BACK = 3
TH_TYPE = 0; TH_DIAM = 1; TH_PITCH = 2; TH_BACK = 3
CV_UNIT = 0; CV_VAL = 1; CV_BACK = 2
OPT_THEME = 0; OPT_BACK = 1

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
        self.sel_tb = TB_CHART
        self.sel_tp = TP_D
        self.sel_th = TH_TYPE
        self.sel_cv = CV_UNIT
        self.sel_opt = OPT_THEME
        
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
        self.val_cutter = CUT_HSS
        self.val_work = WORK_MILD
        self.val_type = TYPE_HOBBY
        self.val_proc = PROC_TURN
        self.val_pass = PASS_ROUGH
        
        self.val_diam = 20.0
        self.val_len = 50.0 
        self.val_vc = 18.0
        self.val_feed = 0.15
        
        self.rpm_result = 0.0
        self.feed_m_result = 0.0
        self.time_result = "0m 0s"
        self.rec_doc = ""
        self.warn_coolant = False
        self.warn_rpm_cap = False
        self.warn_carbide_spd = False
        
        # Sub-Tools
        self.tp_D = 20.0; self.tp_d = 15.0; self.tp_L = 50.0; self.tp_angle = 0.0
        self.th_type = TH_METRIC; self.th_diam = 12.0; self.th_pitch = 1.75; self.th_minor = 0.0; self.th_infeed = 0.0
        self.th_pass_1 = 0.0; self.th_pass_n = 0.0
        self.cv_unit = UNIT_METRIC; self.cv_val = 10.0; self.cv_mm = 0.0; self.cv_inch = 0.0; self.cv_frac = ""
        
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

def save_settings():
    '''Serializes the user's setup and writes it directly to the SD card'''
    global storage, dirty_save, _last_saved_json
    s = state
    if not storage or not dirty_save or not s: return
    try:
        save_dict = {
            "theme_id": s.theme_id,
            "val_unit": s.val_unit, "val_cutter": s.val_cutter, "val_work": s.val_work,
            "val_type": s.val_type, "val_proc": s.val_proc, "val_pass": s.val_pass,
            "val_diam": s.val_diam, "val_len": s.val_len, "val_vc": s.val_vc, "val_feed": s.val_feed,
            "tp_D": s.tp_D, "tp_d": s.tp_d, "tp_L": s.tp_L,
            "th_type": s.th_type, "th_diam": s.th_diam, "th_pitch": s.th_pitch,
            "cv_unit": s.cv_unit, "cv_val": s.cv_val
        }
        json_str = json.dumps(save_dict)
        if json_str != _last_saved_json:
            storage.write(_SETTINGS_FILE, json_str, "w")
            _last_saved_json = json_str
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
            
            # Sanitize indices to repair any float corruption in the save file
            s.val_unit = int(s.val_unit)
            s.val_cutter = int(s.val_cutter)
            s.val_work = int(s.val_work)
            s.val_type = int(s.val_type)
            s.val_proc = int(s.val_proc)
            s.val_pass = int(s.val_pass)
            s.theme_id = int(s.theme_id)
            s.th_type = int(s.th_type)
            s.cv_unit = int(s.cv_unit)
            
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
    elif mode == "HELP":
        text = (
            "=== ABBREVIATIONS GLOSSARY ===\n\n"
            "Vc : Cutting Vel./Surface Spd\n"
            "     (m/min for Metric)\n"
            "SFM: Surface Feet per Minute\n"
            "     (ft/min for Imperial)\n"
            "DOC: Depth of Cut (per pass).\n"
            "LEN: Total length of the cut.\n"
            "DIAM/D-DIA: Workpiece diameter.\n"
            "     If DRILL is selected, this is\n"
            "     the Drill Bit diameter.\n"
            "f  : Feed Rate. Distance tool\n"
            "     travels per revolution.\n"
            "RPM: Spindle Revs per Minute.\n"
            "HSS: High Speed Steel cutter.\n"
            "CARB: Carbide insert cutter.\n"
            "SYS: Machine type (Hobby/Ind).\n"
            "PROC: Machining Process.\n"
            "PASS: Roughing vs Finishing.\n"
            "CHAMF: Chamfering/Bevel cut.\n"
            "BORE: Internal turning.\n"
            "DRILL: Tailstock drilling.\n"
            "MANUAL: Feed tool by hand.\n"
            "PECK: Clear chips frequently.\n\n"
            "=== DETAILED USAGE GUIDE ===\n\n"
            "1. NAVIGATION:\n"
            "   Use UP and DOWN buttons to\n"
            "   move the yellow cursor `>`.\n\n"
            "2. TOGGLES & BUMPING:\n"
            "   Press LEFT/RIGHT on the [ ]\n"
            "   fields to flip switches.\n"
            "   The app auto-updates the Vc\n"
            "   and Feed to safe defaults.\n"
            "   Press LEFT/RIGHT on number\n"
            "   fields to bump them up/dwn.\n\n"
            "3. MANUAL ENTRY:\n"
            "   To type exact values, place\n"
            "   cursor over DIAM, LEN, Vc,\n"
            "   or FEED. Press CENTER for\n"
            "   keyboard. Type value and \n"
            "   confirm to calculate RPM.\n\n"
            "4. TIME ESTIMATOR:\n"
            "   Enter the Length (LEN) of\n"
            "   your cut to instantly see\n"
            "   the estimated time in the\n"
            "   lower results panel.\n\n"
            "5. SHOP TOOLBOX:\n"
            "   Select OPEN SHOP TOOLBOX to\n"
            "   access Reference Charts, \n"
            "   Taper Calc, Thread Assist,\n"
            "   Converters and UI Themes.\n\n"
            "* All settings save automatically\n\n"
            "=== CREDITS ===\n\n"
            "Made by Slasher006\n"
            "with the help of Gemini\n"
        )
    
    s.text_lines = text.split('\n')
    s.scroll_pos = 0

def _apply_safe_defaults():
    s = state 
    
    if s.val_type == TYPE_HOBBY:
        vc_map = [60.0, 45.0, 18.0, 12.0, 12.0, 85.0, 10.0, 30.0, 12.0, 10.0, 3.0] if s.val_cutter == CUT_HSS else [150.0, 100.0, 70.0, 50.0, 60.0, 150.0, 35.0, 100.0, 60.0, 40.0, 20.0]
    else:
        vc_map = [75.0, 50.0, 27.0, 17.0, 20.0, 120.0, 12.0, 37.0, 21.0, 15.0, 4.0] if s.val_cutter == CUT_HSS else [200.0, 150.0, 100.0, 80.0, 100.0, 200.0, 50.0, 120.0, 80.0, 65.0, 30.0]
        
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
    
    if s.val_unit == UNIT_IMP:
        base_vc = base_vc * 3.28084
        if s.val_proc in (PROC_PART, PROC_CHAMFER):
            s.val_vc = base_vc * 0.5
            s.val_feed = 0.002
        else:
            s.val_vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            # Apply the modifier to the standard imperial feeds
            _base_feed = (0.006 if s.val_cutter == CUT_HSS else 0.008) if s.val_pass == PASS_ROUGH else (0.002 if s.val_cutter == CUT_HSS else 0.003)
            s.val_feed = _base_feed * _f_mod
            
        s.val_vc = int(s.val_vc)
        s.val_feed = int(s.val_feed * 10000) / 10000.0
    else:
        if s.val_proc in (PROC_PART, PROC_CHAMFER):
            s.val_vc = base_vc * 0.5
            s.val_feed = 0.05
        else:
            s.val_vc = base_vc if s.val_pass == PASS_ROUGH else base_vc * 1.3
            # Apply the modifier to the standard metric feeds
            _base_feed = (0.15 if s.val_cutter == CUT_HSS else 0.20) if s.val_pass == PASS_ROUGH else (0.05 if s.val_cutter == CUT_HSS else 0.08)
            s.val_feed = _base_feed * _f_mod
            
        s.val_vc = int(s.val_vc * 10) / 10.0
        s.val_feed = int(s.val_feed * 1000) / 1000.0 
        
def _calculate():
    s = state 
    _pi = 3.14159
    s.warn_coolant = False; s.warn_rpm_cap = False; s.warn_carbide_spd = False; s.time_result = "0m 0s"
    
    _max_rpm = MAX_LATHE_RPM_HOBBY if s.val_type == TYPE_HOBBY else MAX_LATHE_RPM_INDUST
    
    # 1. Main Spindle Math
    if s.val_diam > 0:
        theoretical_rpm = (s.val_vc * 1000.0) / (_pi * s.val_diam) if s.val_unit == UNIT_METRIC else (s.val_vc * 12.0) / (_pi * s.val_diam)
        s.rpm_result = theoretical_rpm
        if s.rpm_result > _max_rpm:
            s.rpm_result = _max_rpm
            s.warn_rpm_cap = True
            if s.val_cutter == CUT_CARB: s.warn_carbide_spd = True
        
        if s.val_cutter == CUT_HSS or s.val_proc in (PROC_PART, PROC_CHAMFER, PROC_DRILL) or s.val_work in (WORK_STAIN, WORK_TITAN, WORK_SUPER): s.warn_coolant = True
            
        if s.val_proc == PROC_PART:
            s.rec_doc = "FULL BLD"
        elif s.val_proc == PROC_CHAMFER:
            s.rec_doc = "MANUAL"
        elif s.val_proc == PROC_DRILL:
            s.rec_doc = "PECK"
        elif s.val_proc == PROC_BORE:
            if s.val_type == TYPE_INDUST:
                s.rec_doc = "SEE SPEC" if s.val_cutter == CUT_CARB else ("1.0mm+" if s.val_unit == UNIT_METRIC else "0.04in+")
            else:
                s.rec_doc = "0.2-0.5mm" if s.val_unit == UNIT_METRIC else "0.01-0.02in"
        else:
            if s.val_type == TYPE_INDUST:
                s.rec_doc = "SEE SPEC" if s.val_cutter == CUT_CARB else ("2.0mm+" if s.val_unit == UNIT_METRIC else "0.08in+")
            else:
                if s.val_pass == PASS_ROUGH:
                    if s.val_work in (WORK_SUPER, WORK_TOOL_ST):
                        # 50% DOC reduction for extremely hard materials on hobby machines
                        s.rec_doc = ("0.5mm" if s.val_cutter == CUT_HSS else "0.2mm") if s.val_unit == UNIT_METRIC else ("0.02in" if s.val_cutter == CUT_HSS else "0.008in")
                    else:
                        s.rec_doc = ("1.0mm" if s.val_cutter == CUT_HSS else "0.5mm") if s.val_unit == UNIT_METRIC else ("0.04in" if s.val_cutter == CUT_HSS else "0.02in")
                else:
                    s.rec_doc = "0.1-0.2mm" if s.val_unit == UNIT_METRIC else "0.004-0.008in"
        

        s.feed_m_result = s.rpm_result * s.val_feed
        s.feed_m_result = int(s.feed_m_result * 10) / 10.0 if s.val_unit == UNIT_METRIC else int(s.feed_m_result * 1000) / 1000.0
            
        if s.val_feed > 0 and s.rpm_result > 0 and s.val_len > 0:
            time_mins = s.val_len / (s.val_feed * s.rpm_result)
            _m = int(time_mins)
            _s = int((time_mins - _m) * 60)
            s.time_result = str(_m) + "m " + str(_s) + "s"
            
    # 2. Taper Math
    if s.tp_L > 0:
        from math import atan, pi
        _rads = atan(abs(s.tp_D - s.tp_d) / (2.0 * s.tp_L))
        s.tp_angle = int((_rads * (180.0 / pi)) * 100) / 100.0

    # 3. Threading Math (60 Degree Standards)
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
    elif state.current_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL, SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE, SCREEN_FITS, SCREEN_HELP, SCREEN_KNURL): _draw_text_screen(view_manager, state.current_screen)

def _draw_text_screen(view_manager, mode):
    s = state
    from picoware.system.vector import Vector
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
    else: _draw.text(Vector(5, 5), "HELP & ABBREVIATIONS", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _vis = 16; _lh = 15; _sy = 30        
    for i in range(_vis):
        _idx = s.scroll_pos + i
        if _idx < len(s.text_lines): _draw.text(Vector(5, _sy + i * _lh), s.text_lines[_idx], s.c_fg)
            
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

def _draw_toolbox(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "SHOP TOOLBOX", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    opts = [
        " 1. MATL Vc REF CHARTS",
        " 2. TAP SIZES",
        " 3. DRILL SIZES",
        " 4. CENTER DRILLS",
        " 5. MORSE TAPERS",
        " 6. SHCS CLEARANCES",
        " 7. SURFACE FINISHES",
        " 8. ISO FITS",
        " 9. TAPER ANGLE CALC",
        "10. THREADING ASSIST",
        "11. UNIT CONVERTER",
        "12. KNURLING GUIDE",
        "13. OPTIONS & THEMES",
        "<   RETURN TO MAIN"
    ]
    
    for i in range(14):
        _y = 32 + i * 18
        if i == s.sel_tb:
            _draw.text(Vector(5, _y), ">" + opts[i], s.c_hlt)
        else:
            _draw.text(Vector(15, _y), opts[i], s.c_fg)
    _draw.swap()

def _draw_options(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "PERSONALIZATION", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    themes = ["0: DARK THEME", "1: TERMINAL", "2: BLUEPRINT", "3: LIGHT MODE"]
    
    opts = [
        "UI THEME: < " + themes[s.theme_id] + " >",
        "< RETURN TO TOOLBOX"
    ]
    
    for i in range(2):
        _y = 40 + i * 25
        if i == s.sel_opt:
            _draw.text(Vector(5, _y), ">", s.c_hlt)
            _draw.text(Vector(20, _y), opts[i], s.c_hlt)
        else:
            _draw.text(Vector(20, _y), opts[i], s.c_fg)
            
    _draw.fill_rectangle(Vector(0, 150), Vector(320, 1), s.c_fg)
    _draw.text(Vector(5, 165), "THEME PREVIEW:", s.c_sec)
    _draw.text(Vector(5, 195), "STANDARD TEXT", s.c_fg)
    _draw.text(Vector(5, 215), "> HIGHLIGHT TEXT", s.c_hlt)
    _draw.text(Vector(5, 235), "SUCCESS VALUE", s.c_ok)
    _draw.text(Vector(5, 255), "WARNING VALUE", s.c_warn)
    _draw.text(Vector(5, 275), "ERROR VALUE", s.c_err)
    _draw.swap()

def _draw_taper(view_manager):
    s = state
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "TAPER ANGLE CALCULATOR", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)
    
    _u = "mm" if s.val_unit == UNIT_METRIC else "in"
    opts = [
        "LARGE DIAM (D):  " + str(s.tp_D) + " " + _u,
        "SMALL DIAM (d):  " + str(s.tp_d) + " " + _u,
        "TAPER LEN  (L):  " + str(s.tp_L) + " " + _u,
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
        "MAJOR:   " + str(s.th_diam) + " " + _u_d,
        "PITCH:   " + str(s.th_pitch) + " " + _u_p,
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
        "VALUE:   " + str(s.cv_val),
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

def _draw_calc(view_manager):
    '''Draws the main calculator interface (Dual-Column Dashboard)'''
    s = state 
    from picoware.system.vector import Vector
    _draw = view_manager.draw
    
    _draw.clear(color=s.c_bg)
    _draw.text(Vector(5, 5), "LATHE-CALC v1.5", s.c_fg)
    _draw.fill_rectangle(Vector(0, 22), Vector(320, 1), s.c_fg)

    _str_unit = "METRIC" if s.val_unit == UNIT_METRIC else "IMPERL"
    _str_cut = "HSS" if s.val_cutter == CUT_HSS else "CARBID"
    _str_type = "HOBBY" if s.val_type == TYPE_HOBBY else "INDUST"
    _proc_names = ["TURN", "FACE", "PART", "CHAMF", "BORE", "DRILL"]
    _str_proc = _proc_names[s.val_proc]
    _str_pass = "ROUGH" if s.val_pass == PASS_ROUGH else "FINISH"
    
    work_names = ["ALUM", "BRASS", "MILD ST", "STAINLS", "CST IRN", "PLASTIC", "TITAN", "COPPER", "HI-C ST", "TOOL ST", "SUPERAL"]
    _str_work = work_names[s.val_work]
    
    _u_d = "mm" if s.val_unit == UNIT_METRIC else "in"
    _u_v = "m/m" if s.val_unit == UNIT_METRIC else "SFM"
    _u_f = "mm/r" if s.val_unit == UNIT_METRIC else "in/r"
    _l_v = "Vc  :" if s.val_unit == UNIT_METRIC else "SFM :"

    _diam_label = "D-DIA:" if s.val_proc == PROC_DRILL else "DIAM: "

    left_fields = [
        "UNIT: [" + _str_unit + "]",
        "SYS : [" + _str_type + "]",
        "WORK: [" + _str_work + "]",
        "CUT : [" + _str_cut + "]",
        "PROC: [" + _str_proc + "]",
        "PASS: [" + _str_pass + "]"
    ]
    
    right_fields = [
        _diam_label + " " + str(s.val_diam) + " " + _u_d,
        "LEN : " + str(s.val_len) + " " + _u_d,
        _l_v + " " + str(s.val_vc) + " " + _u_v,
        "FEED: " + str(s.val_feed) + " " + _u_f,
        "[>] TOOLBOX",
        "[?] HELP"
    ]

    _draw.fill_rectangle(Vector(155, 30), Vector(1, 150), s.c_fg)

    for i in range(6):
        _y = 35 + i * 24
        if i == s.sel_main:
            _draw.text(Vector(2, _y), ">", s.c_hlt)
            _draw.text(Vector(12, _y), left_fields[i], s.c_hlt)
        else:
            _draw.text(Vector(12, _y), left_fields[i], s.c_fg)
            
        r_idx = i + 6
        if r_idx == s.sel_main:
            _draw.text(Vector(160, _y), ">", s.c_hlt)
            _draw.text(Vector(170, _y), right_fields[i], s.c_hlt)
        else:
            _draw.text(Vector(170, _y), right_fields[i], s.c_fg)

    _draw.fill_rectangle(Vector(0, 185), Vector(320, 1), s.c_fg)
    
    _f_l = "FEED(mm/m)" if s.val_unit == UNIT_METRIC else "FEED(in/m)"
    _draw.text(Vector(5, 195), "SPINDLE (RPM)", s.c_ok)
    _draw.text(Vector(160, 195), _f_l, s.c_ok)
    
    _rpm_color = s.c_warn if s.warn_rpm_cap else s.c_fg
    _draw.text(Vector(5, 215), str(int(s.rpm_result)), _rpm_color)
    _draw.text(Vector(160, 215), str(s.feed_m_result), s.c_fg)
    
    _draw.text(Vector(5, 235), "MAX DOC: " + s.rec_doc, s.c_fg)
    _draw.text(Vector(160, 235), "TIME: " + s.time_result, s.c_hlt)
    
    _draw.fill_rectangle(Vector(0, 260), Vector(320, 1), s.c_fg)
    _y_warn = 270
    _max_rpm = MAX_LATHE_RPM_HOBBY if s.val_type == TYPE_HOBBY else MAX_LATHE_RPM_INDUST
    
    if s.warn_rpm_cap:
        _draw.text(Vector(5, _y_warn), "! RPM CAPPED (MAX " + str(int(_max_rpm)) + ")", s.c_warn)
        _y_warn += 15
    if s.warn_carbide_spd:
        _draw.text(Vector(5, _y_warn), "! DIAM TOO SML FOR CARBIDE", s.c_err)
        _y_warn += 15
    if s.warn_coolant:
        _draw.text(Vector(5, _y_warn), "* FLUID/COOLANT REQ", s.c_sec)
        
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
            save_settings()

    # Handle Text Screen Scrolling
    if s.current_screen in (SCREEN_CHART, SCREEN_TAP, SCREEN_DRILL, SCREEN_CENTER, SCREEN_MORSE, SCREEN_CLEAR, SCREEN_SURFACE, SCREEN_FITS, SCREEN_HELP, SCREEN_KNURL):
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
                new_val = float(kb.response)
                if s.current_screen == SCREEN_CALC:
                    if s.sel_main == FIELD_DIAM: s.val_diam = new_val
                    elif s.sel_main == FIELD_LEN: s.val_len = new_val
                    elif s.sel_main == FIELD_VC: s.val_vc = new_val
                    elif s.sel_main == FIELD_FEED: s.val_feed = new_val
                elif s.current_screen == SCREEN_TAPER:
                    if s.sel_tp == TP_D: s.tp_D = new_val
                    elif s.sel_tp == TP_d: s.tp_d = new_val
                    elif s.sel_tp == TP_L: s.tp_L = new_val
                elif s.current_screen == SCREEN_THREAD:
                    if s.sel_th == TH_DIAM: s.th_diam = new_val
                    elif s.sel_th == TH_PITCH: s.th_pitch = new_val
                elif s.current_screen == SCREEN_CONVERT:
                    if s.sel_cv == CV_VAL: s.cv_val = new_val
                _calculate()
                queue_save()
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
            s.current_screen = SCREEN_TOOLBOX if s.current_screen in (SCREEN_TAPER, SCREEN_THREAD, SCREEN_CONVERT, SCREEN_OPTIONS) else SCREEN_CALC
            _im.reset(); _draw_ui(view_manager)
        return

    # Sub-Menu Routing
    if s.current_screen == SCREEN_TOOLBOX:
        if _btn == BUTTON_DOWN: s.sel_tb = (s.sel_tb + 1) % 14; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_tb = (s.sel_tb - 1) % 14; _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_tb == TB_CHART:
                s.current_screen = SCREEN_CHART; _load_text("CHART")
            elif s.sel_tb == TB_TAP:
                s.current_screen = SCREEN_TAP; _load_text("TAP")
            elif s.sel_tb == TB_DRILL:
                s.current_screen = SCREEN_DRILL; _load_text("DRILL")
            elif s.sel_tb == TB_CENTER:
                s.current_screen = SCREEN_CENTER; _load_text("CENTER")
            elif s.sel_tb == TB_MORSE:
                s.current_screen = SCREEN_MORSE; _load_text("MORSE")
            elif s.sel_tb == TB_CLEAR:
                s.current_screen = SCREEN_CLEAR; _load_text("CLEAR")
            elif s.sel_tb == TB_SURFACE:
                s.current_screen = SCREEN_SURFACE; _load_text("SURFACE")
            elif s.sel_tb == TB_FITS:
                s.current_screen = SCREEN_FITS; _load_text("FITS")
            elif s.sel_tb == TB_TAPER: s.current_screen = SCREEN_TAPER
            elif s.sel_tb == TB_THREAD: s.current_screen = SCREEN_THREAD
            elif s.sel_tb == TB_CONVERT: s.current_screen = SCREEN_CONVERT
            elif s.sel_tb == TB_KNURL:
                s.current_screen = SCREEN_KNURL; _load_text("KNURL")
            elif s.sel_tb == TB_OPTIONS: s.current_screen = SCREEN_OPTIONS
            elif s.sel_tb == TB_BACK: s.current_screen = SCREEN_CALC
            _needs_redraw = True
            
    elif s.current_screen == SCREEN_OPTIONS:
        if _btn == BUTTON_DOWN: s.sel_opt = (s.sel_opt + 1) % 2; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_opt = (s.sel_opt - 1) % 2; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            if s.sel_opt == OPT_THEME:
                _dir = 1 if _btn == BUTTON_RIGHT else -1
                s.theme_id = (s.theme_id + _dir) % 4
                _apply_theme()
                queue_save()
                _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_opt == OPT_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            
    elif s.current_screen == SCREEN_TAPER:
        if _btn == BUTTON_DOWN: s.sel_tp = (s.sel_tp + 1) % 4; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_tp = (s.sel_tp - 1) % 4; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            _st = 1.0 if s.val_unit == UNIT_METRIC else 0.1
            if s.sel_tp == TP_D: s.tp_D = max(0.001, s.tp_D + (_dir * _st))
            elif s.sel_tp == TP_d: s.tp_d = max(0.001, s.tp_d + (_dir * _st))
            elif s.sel_tp == TP_L: s.tp_L = max(0.001, s.tp_L + (_dir * _st))
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
            if s.sel_th == TH_TYPE:
                s.th_type = TH_UNIFIED if s.th_type == TH_METRIC else TH_METRIC
            elif s.sel_th == TH_DIAM: 
                s.th_diam = max(0.001, s.th_diam + (_dir * (1.0 if s.th_type == TH_METRIC else 0.01)))
            elif s.sel_th == TH_PITCH: 
                s.th_pitch = max(0.01, s.th_pitch + (_dir * (0.05 if s.th_type == TH_METRIC else 1.0)))
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
                s.cv_val = max(0.001, s.cv_val + ((1.0 if _btn == BUTTON_RIGHT else -1.0) * (1.0 if s.cv_unit == UNIT_METRIC else 0.1)))
            _calculate(); queue_save(); _needs_redraw = True
        elif _btn == BUTTON_CENTER:
            if s.sel_cv == CV_BACK: s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_cv == CV_VAL:
                kb = view_manager.keyboard
                kb.reset()
                kb.title = "CONVERT VALUE"
                kb.response = str(s.cv_val)
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    elif s.current_screen == SCREEN_CALC:
        if _btn == BUTTON_DOWN: s.sel_main = (s.sel_main + 1) % 12; _needs_redraw = True
        elif _btn == BUTTON_UP: s.sel_main = (s.sel_main - 1) % 12; _needs_redraw = True
        elif _btn in (BUTTON_LEFT, BUTTON_RIGHT):
            _dir = 1.0 if _btn == BUTTON_RIGHT else -1.0
            if s.sel_main == FIELD_UNIT:
                s.val_unit = UNIT_IMP if s.val_unit == UNIT_METRIC else UNIT_METRIC
                if s.val_unit == UNIT_IMP:
                    s.val_diam = int((s.val_diam / 25.4) * 1000) / 1000.0
                    s.val_len = int((s.val_len / 25.4) * 1000) / 1000.0
                else:
                    s.val_diam = int((s.val_diam * 25.4) * 10) / 10.0
                    s.val_len = int((s.val_len * 25.4) * 10) / 10.0
            elif s.sel_main == FIELD_CUTTER: 
                if s.val_proc == PROC_DRILL and s.val_type == TYPE_HOBBY:
                    pass
                else:
                    s.val_cutter = CUT_CARB if s.val_cutter == CUT_HSS else CUT_HSS
            elif s.sel_main == FIELD_WORK: s.val_work = (s.val_work + int(_dir)) % 11
            elif s.sel_main == FIELD_TYPE: 
                s.val_type = TYPE_INDUST if s.val_type == TYPE_HOBBY else TYPE_HOBBY
                if s.val_type == TYPE_HOBBY and s.val_proc == PROC_DRILL and s.val_cutter == CUT_CARB:
                    s.val_cutter = CUT_HSS
            elif s.sel_main == FIELD_PROC: 
                s.val_proc = (s.val_proc + int(_dir)) % 6
                if s.val_proc == PROC_DRILL and s.val_type == TYPE_HOBBY and s.val_cutter == CUT_CARB:
                    s.val_cutter = CUT_HSS
            elif s.sel_main == FIELD_PASS: s.val_pass = PASS_FINISH if s.val_pass == PASS_ROUGH else PASS_ROUGH
            elif s.sel_main == FIELD_DIAM: 
                s.val_diam = max(0.001, s.val_diam + (_dir * (1.0 if s.val_unit == UNIT_METRIC else 0.1)))
            elif s.sel_main == FIELD_LEN: 
                s.val_len = max(0.001, s.val_len + (_dir * (5.0 if s.val_unit == UNIT_METRIC else 0.5)))
            elif s.sel_main == FIELD_VC: 
                s.val_vc = max(1.0, s.val_vc + (_dir * (5.0 if s.val_unit == UNIT_METRIC else 10.0)))
            elif s.sel_main == FIELD_FEED: 
                s.val_feed = max(0.001, s.val_feed + (_dir * (0.01 if s.val_unit == UNIT_METRIC else 0.001)))
                s.val_feed = int(s.val_feed * 10000) / 10000.0
                
            if s.sel_main in (FIELD_UNIT, FIELD_CUTTER, FIELD_WORK, FIELD_TYPE, FIELD_PROC, FIELD_PASS):
                _apply_safe_defaults()
                
            _calculate(); queue_save(); _needs_redraw = True

        elif _btn == BUTTON_CENTER:
            if s.sel_main == FIELD_MAIN_TOOLBOX:
                s.current_screen = SCREEN_TOOLBOX; _needs_redraw = True
            elif s.sel_main == FIELD_MAIN_HELP:
                s.current_screen = SCREEN_HELP
                _load_text("HELP"); _needs_redraw = True
            elif s.sel_main in (FIELD_DIAM, FIELD_LEN, FIELD_VC, FIELD_FEED):
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
                s.is_typing = True; s.kb_force = True; _im.reset(); return

    if _needs_redraw:
        _im.reset()
        _draw_ui(view_manager)

def stop(view_manager):
    '''Stop the app, execute a final save, and clear memory'''
    from gc import collect
    global state, storage, dirty_save, save_timer, _last_saved_json
    
    save_settings() 
    
    if view_manager.keyboard:
        view_manager.keyboard.reset()
        
    del state; state = None
    storage = None
    dirty_save = False
    save_timer = 0
    _last_saved_json = ""
    
    collect()
