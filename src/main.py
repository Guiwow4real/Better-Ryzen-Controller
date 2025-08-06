import os
import subprocess
import threading
import pyglet
import imgui
from imgui.integrations.pyglet import PygletRenderer
import psutil
from array import array
import configparser
from tools.ryzenadj import PARAMETERS as RA_PARAMS
import ctypes
import sys
import time

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    script = os.path.abspath(sys.argv[0])
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
    sys.exit()

# Configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'settings.ini')
DEFAULT_SETTINGS = {
    'start_with_system': 'False',
    'language': '0',
    'theme': '2',
    'ra_path': 'ryzenadj.exe',
    'refresh_interval': '5'
}
config = configparser.ConfigParser()
config.read_dict({'Settings': DEFAULT_SETTINGS})
if os.path.exists(CONFIG_PATH):
    config.read(CONFIG_PATH)
    if 'Settings' not in config:
        config['Settings'] = DEFAULT_SETTINGS
else:
    config['Settings'] = DEFAULT_SETTINGS
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

def str2bool(s): return s.lower() in ('1', 'true', 'yes', 'on')

class AppState:
    def __init__(self):
        s = config['Settings']
        self.page = 'welcome'
        self.start_with_system = str2bool(s.get('start_with_system', 'False'))
        self.language = int(s.get('language', '0'))
        self.theme = int(s.get('theme', '2'))
        self.ra_path = s.get('ra_path', 'ryzenadj.exe')
        self.refresh_interval = int(s.get('refresh_interval', '5'))
        self.cpu_history = []
        self.ra_args = {}
        self.metrics = {}
        self.last_error = None
        self.last_update = 0
        self.is_loading = False
        self.fetch_metrics()

    def fetch_metrics(self):
        if self.is_loading:
            return
            
        self.is_loading = True
        
        OFFSET_NAME_MAP = {
            "0x0018": "ppt-apu",
            "0x0020": "tdc-vdd",
            "0x0028": "tdc-soc",
            "0x0030": "edc-vdd",
            "0x0038": "edc-soc",
            "0x0144": "stapm-value",
            "0x0150": "ppt-fast",
            "0x0154": "ppt-slow",
            "0x02a4": "thm-core",
            "0x0294": "stt-apu",
            "0x0060": "stt-dgpu",
            "0x0068": "max-freq",
            "0x006c": "base-freq"
        }

        def run():
            try:
                proc = subprocess.run([self.ra_path, '--dump-table'], 
                                     capture_output=True, text=True, check=True)
                metrics = {}
                lines = proc.stdout.splitlines()
                
                for line in lines[3:]:  # Skip header
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3:
                        offset = parts[0].lower()
                        hexdata = parts[1]
                        try:
                            value = float(parts[2])
                        except ValueError:
                            value = float('nan')
                        
                        # Apply scaling factors
                        if offset in ["0x0144", "0x0150", "0x0154"]:  # Power values
                            value = value / 10  # Assume original is 10x actual
                        elif offset in ["0x0068", "0x006c"]:  # Frequency values
                            value = value  # Keep as is (MHz)
                        
                        name = OFFSET_NAME_MAP.get(offset, offset)
                        metrics[name] = {
                            "offset": offset,
                            "hexdata": hexdata,
                            "value": value,
                            "unit": self.get_unit_for_param(name)
                        }
                
                self.metrics = metrics
                self.last_error = None
                self.last_update = time.time()
            except subprocess.CalledProcessError as e:
                self.last_error = e.stderr or str(e)
            except Exception as e:
                self.last_error = f"Unexpected error: {str(e)}"
            finally:
                self.is_loading = False

        threading.Thread(target=run, daemon=True).start()

    def get_unit_for_param(self, param_name):
        if any(x in param_name for x in ['stapm', 'ppt']):
            return "W"
        elif any(x in param_name for x in ['tdc', 'edc']):
            return "A"
        elif any(x in param_name for x in ['thm', 'stt']):
            return "°C"
        elif any(x in param_name for x in ['freq']):
            return "MHz"
        return ""

state = AppState()
psutil.cpu_percent(None)  # Initialize CPU monitoring

window = pyglet.window.Window(1000, 600, 'Better Ryzen Controller', resizable=True)
imgui.create_context()
impl = PygletRenderer(window)
io = imgui.get_io()
io.fonts.clear()
io.fonts.add_font_from_file_ttf(r"C:\\Windows\\Fonts\\msyh.ttc", 20)
impl.refresh_font_texture()

themes = [
    {'bg': (30/255,30/255,30/255,1), 'text': (230/255,230/255,230/255,1)},  # Dark
    {'bg': (245/255,245/255,245/255,1), 'text': (20/255,20/255,20/255,1)},  # Light
]

def apply_theme():
    t = themes[state.theme] if state.theme in (0,1) else themes[0]
    style = imgui.get_style()
    style.colors[imgui.COLOR_WINDOW_BACKGROUND] = t['bg']
    style.colors[imgui.COLOR_TEXT] = t['text']
    style.colors[imgui.COLOR_HEADER] = (0.26, 0.59, 0.98, 0.31)
    style.colors[imgui.COLOR_HEADER_HOVERED] = (0.26, 0.59, 0.98, 0.8)
    style.colors[imgui.COLOR_HEADER_ACTIVE] = (0.06, 0.53, 0.98, 1.0)

def render_notification():
    if state.last_error:
        imgui.set_next_window_size(500, 200)
        imgui.begin('Error', True, imgui.WINDOW_NO_RESIZE)
        imgui.text_colored("RyzenAdj Error:", 1, 0.4, 0.4)
        imgui.separator()
        imgui.text_wrapped(state.last_error.strip())
        if "permission" in state.last_error.lower():
            imgui.text_colored("Try running with administrator privileges.", 1, 0.6, 0.3)
        if imgui.button("Dismiss"):
            state.last_error = None
        imgui.end()

def render_welcome():
    imgui.text('Welcome to Better Ryzen Controller')
    imgui.separator()
    imgui.text('Use Adjust to configure parameters and Monitor to view metrics.')
    imgui.spacing()
    imgui.text('Key Features:')
    imgui.bullet_text('Real-time monitoring of Ryzen processor parameters')
    imgui.bullet_text('Adjust power and thermal limits')
    imgui.bullet_text('Visualize CPU usage history')

def render_adjust():
    imgui.text('Adjust RyzenAdj Parameters')
    imgui.separator()
    metrics = state.metrics
    
    if state.is_loading:
        imgui.text_colored("Loading parameters...", 1, 1, 0)
        return
    
    imgui.begin_child('ra_panel', 0, 300, border=True)
    for group, params in RA_PARAMS.items():
        open_, _ = imgui.collapsing_header(group)
        if open_:
            for key, desc in params:
                raw = metrics.get(key)
                if raw:
                    default = int(raw["value"])
                    maximum = int(default * 1.5)  # Allow 50% over default
                    estimated = False
                else:
                    default = 0
                    maximum = 100000
                    estimated = True
                
                try:
                    val = int(state.ra_args.get(key, default))
                except:
                    val = default
                
                changed, val_new = imgui.slider_int(key, val, 0, maximum)
                if estimated:
                    imgui.same_line()
                    imgui.text_disabled("⚠")
                    if imgui.is_item_hovered():
                        imgui.begin_tooltip()
                        imgui.text("Estimated value - not available from RyzenAdj")
                        imgui.end_tooltip()
                
                imgui.same_line()
                changed2, val_inp = imgui.input_int(f"{key}_inp", val, step=1)
                if changed: state.ra_args[key] = str(val_new)
                if changed2: state.ra_args[key] = str(val_inp)
                
                if imgui.is_item_hovered() and desc:
                    imgui.begin_tooltip()
                    imgui.text(desc)
                    imgui.end_tooltip()
    
    imgui.end_child()
    
    if imgui.button('Apply Settings'):
        if not os.path.isfile(state.ra_path):
            state.last_error = f"Invalid RyzenAdj path: {state.ra_path}"
        else:
            def apply():
                try:
                    args = [f"--{k}={v}" for k, v in state.ra_args.items() if v]
                    subprocess.run([state.ra_path] + args, check=True)
                    state.last_error = None
                    state.fetch_metrics()  # Refresh after applying
                except subprocess.CalledProcessError as e:
                    state.last_error = e.stderr or str(e)
            threading.Thread(target=apply, daemon=True).start()
    
    imgui.same_line()
    if imgui.button('Reset to Defaults'):
        state.ra_args = {}
        state.fetch_metrics()

def render_monitor():
    # CPU Usage Graph
    cpu = psutil.cpu_percent(None)
    state.cpu_history.append(cpu)
    if len(state.cpu_history) > 100:
        state.cpu_history.pop(0)

    imgui.text(f'CPU Usage: {cpu:.1f}%')
    data = array('f', state.cpu_history)
    imgui.plot_lines('##cpu_history', data, graph_size=(0, 150))
    
    # Auto-refresh logic
    if time.time() - state.last_update > state.refresh_interval:
        state.fetch_metrics()
    
    imgui.same_line()
    if imgui.button("Refresh"):
        state.fetch_metrics()
    
    imgui.same_line()
    _, state.refresh_interval = imgui.slider_int("Interval (s)", state.refresh_interval, 1, 60)
    
    imgui.separator()
    
    # Metrics Table
    if state.is_loading:
        imgui.text_colored("Loading metrics...", 1, 1, 0)
        return
    
    if not state.metrics:
        imgui.text("No metrics available")
        return
    
    flags = (imgui.TABLE_BORDERS | imgui.TABLE_RESIZABLE | 
             imgui.TABLE_ROW_BG | imgui.TABLE_SCROLLY)
    
    if imgui.begin_table('metric_table', 4, flags):
        # Setup columns
        imgui.table_setup_column('Parameter', imgui.TABLE_COLUMN_WIDTH_STRETCH)
        imgui.table_setup_column('Value', imgui.TABLE_COLUMN_WIDTH_STRETCH)
        imgui.table_setup_column('Offset', imgui.TABLE_COLUMN_WIDTH_STRETCH)
        imgui.table_setup_column('Hex Data', imgui.TABLE_COLUMN_WIDTH_STRETCH)
        imgui.table_headers_row()
        
        # Display metrics in a specific order
        param_order = [
            'stapm-value', 'ppt-fast', 'ppt-slow', 'ppt-apu',
            'tdc-vdd', 'tdc-soc', 'edc-vdd', 'edc-soc',
            'thm-core', 'stt-apu', 'stt-dgpu',
            'max-freq', 'base-freq'
        ]
        
        for key in param_order:
            info = state.metrics.get(key)
            if not info:
                continue
                
            value = info.get("value", float("nan"))
            offset = info.get("offset", "N/A")
            hexdata = info.get("hexdata", "N/A")
            unit = info.get("unit", "")
            
            imgui.table_next_row()
            
            # Parameter name
            imgui.table_set_column_index(0)
            imgui.text(key.replace('-', ' ').title())
            
            # Value with unit
            imgui.table_set_column_index(1)
            if "freq" in key:
                imgui.text(f"{value:.0f} {unit}")
            else:
                imgui.text(f"{value:.2f} {unit}")
            
            # Offset
            imgui.table_set_column_index(2)
            imgui.text(offset)
            
            # Hex Data
            imgui.table_set_column_index(3)
            imgui.text(hexdata)
        
        imgui.end_table()

def save_settings():
    config['Settings'] = {
        'start_with_system': str(state.start_with_system),
        'language': str(state.language),
        'theme': str(state.theme),
        'ra_path': state.ra_path,
        'refresh_interval': str(state.refresh_interval)
    }
    with open(CONFIG_PATH, 'w') as f: 
        config.write(f)

def render_settings():
    changed = False
    
    _, state.start_with_system = imgui.checkbox('Start with system', state.start_with_system)
    changed = changed or imgui.is_item_deactivated()
    
    _, state.language = imgui.combo('Language', state.language, ['English','中文'])
    changed = changed or imgui.is_item_deactivated()
    
    _, state.theme = imgui.combo('Theme', state.theme, ['Dark','Light','System Default'])
    changed = changed or imgui.is_item_deactivated()
    
    imgui.separator()
    
    imgui.text('RyzenAdj Executable Path:')
    path_changed, state.ra_path = imgui.input_text('##ra_path', state.ra_path, 256)
    changed = changed or path_changed
    
    imgui.same_line()
    if imgui.button("Browse..."):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(
                title="Select RyzenAdj executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if file_path:
                state.ra_path = file_path
                changed = True
        except Exception as e:
            state.last_error = f"Failed to open file dialog: {str(e)}"
    
    imgui.separator()
    
    _, state.refresh_interval = imgui.slider_int('Refresh Interval (seconds)', 
                                               state.refresh_interval, 1, 60)
    changed = changed or imgui.is_item_deactivated()
    
    imgui.separator()
    
    if imgui.button('Save Settings'):
        save_settings()
    
    if not changed:
        imgui.pop_style_var()

@window.event
def on_draw():
    window.clear()
    imgui.new_frame()
    apply_theme()
    
    w, h = window.get_size()
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(w, h)
    
    imgui.begin('FullWindow', False,
        imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_MOVE | 
        imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SCROLLBAR)
    
    # Sidebar Menu
    imgui.begin_child('Menu', 200, h, border=True)
    for name, label in [('welcome','Welcome'), ('adjust','Adjust'), 
                       ('monitor','Monitor'), ('settings','Settings')]:
        active = state.page == name
        if active:
            imgui.push_style_color(imgui.COLOR_BUTTON, 0.26, 0.59, 0.98, 0.8)
        else:
            imgui.push_style_color(imgui.COLOR_BUTTON, *imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND])
        
        if imgui.button(label, 180):
            state.page = name
            if name == 'monitor':
                state.fetch_metrics()
        
        imgui.pop_style_color(1)
    imgui.end_child()
    
    # Main Content Area
    imgui.same_line()
    imgui.begin_child('Content', w-210, h, border=False)
    
    if state.page == 'welcome': 
        render_welcome()
    elif state.page == 'adjust': 
        render_adjust()
    elif state.page == 'monitor': 
        render_monitor()
    else: 
        render_settings()
    
    render_notification()
    imgui.end_child()
    imgui.end()
    
    imgui.render()
    impl.render(imgui.get_draw_data())

@window.event
def on_resize(width, height):
    """Handle window resize events"""
    # Update ImGui display size
    io = imgui.get_io()
    io.display_size = width, height
    
    # Handle high DPI scaling
    fb_width, fb_height = window.get_framebuffer_size()
    io.display_fb_scale = (
        fb_width / width if width > 0 else 1.0,
        fb_height / height if height > 0 else 1.0
    )
    
    # Set minimum window size
    if width < 800 or height < 600:
        window.set_size(max(800, width), max(600, height))

import win32api
import win32con
try:
    pyglet.app.run()
except Exception as error:
    win32api.MessageBox(win32con.ERROR,str(error), 'Error', win32con.MB_OK)
