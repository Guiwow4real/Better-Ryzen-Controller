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

# 配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'settings.ini')
DEFAULT_SETTINGS = {
    'start_with_system': 'False',
    'language': '0',
    'theme': '2',
    'ra_path': 'ryzenadj.exe'
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
        self.cpu_history = []
        self.ra_args = {}
        self.metrics = {}
        self.last_error = None
        self.fetch_metrics()

    def fetch_metrics(self):
        OFFSET_NAME_MAP = {
            "0x0000": "param-0",
            "0x0004": "param-4",
            "0x0008": "param-8",
            "0x000c": "param-c",
            "0x0010": "param-10",
            "0x0014": "param-14",
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
        }

        def run():
            try:
                proc = subprocess.run([self.ra_path, '--dump-table'], capture_output=True, text=True, check=True)
                metrics = {}
                lines = proc.stdout.splitlines()
                # 跳过前三行（标题+表头）
                for line in lines[3:]:
                    parts = line.strip().split()
                    if len(parts) == 3:
                        offset = parts[0].lower()
                        hexdata = parts[1]
                        try:
                            value = float(parts[2])
                        except:
                            value = float('nan')
                        name = OFFSET_NAME_MAP.get(offset, offset)  # 找不到就用offset做名字
                        metrics[name] = {
                            "offset": offset,
                            "hexdata": hexdata,
                            "value": value
                        }
                self.metrics = metrics
                self.last_error = None
            except subprocess.CalledProcessError as e:
                self.last_error = e.stderr or str(e)

        threading.Thread(target=run, daemon=True).start()


state = AppState()
psutil.cpu_percent(None)

window = pyglet.window.Window(1000, 600, 'Better Ryzen Controller', resizable=True)
imgui.create_context(); impl = PygletRenderer(window)
io = imgui.get_io(); io.fonts.clear(); io.fonts.add_font_from_file_ttf(r"C:\\Windows\\Fonts\\msyh.ttc", 20); impl.refresh_font_texture()
themes = [
    {'bg': (30/255,30/255,30/255,1), 'text': (230/255,230/255,230/255,1)},
    {'bg': (245/255,245/255,245/255,1), 'text': (20/255,20/255,20/255,1)},
]

def apply_theme():
    t = themes[state.theme] if state.theme in (0,1) else themes[0]
    style = imgui.get_style()
    style.colors[imgui.COLOR_WINDOW_BACKGROUND] = t['bg']
    style.colors[imgui.COLOR_TEXT] = t['text']

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

def render_adjust():
    imgui.text('Adjust RyzenAdj Parameters')
    imgui.separator()
    metrics = state.metrics
    imgui.begin_child('ra_panel', 0, 300, border=True)
    for group, params in RA_PARAMS.items():
        open_, _ = imgui.collapsing_header(group)
        if open_:
            for key, desc in params:
                raw = metrics.get(key)
                if raw:
                    default = int(raw[0])
                    maximum = int(raw[1]) if not (raw[1] is None or raw[1] != raw[1]) else 100000
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
                    imgui.text_disabled("\u26a0")
                    if imgui.is_item_hovered():
                        imgui.begin_tooltip()
                        imgui.text("Estimated value — not available from RyzenAdj")
                        imgui.end_tooltip()
                imgui.same_line()
                changed2, val_inp = imgui.input_int(f"{key}_inp", val, step=1)
                if changed: state.ra_args[key] = str(val_new)
                if changed2: state.ra_args[key] = str(val_inp)
    imgui.end_child()
    if imgui.button('Apply RyzenAdj'):
        if not os.path.isfile(state.ra_path):
            state.last_error = f"Invalid RyzenAdj path: {state.ra_path}"
        else:
            def apply():
                try:
                    args = [f"--{k}={v}" for k, v in state.ra_args.items() if v]
                    subprocess.run([state.ra_path] + args, check=True)
                    state.last_error = None
                except subprocess.CalledProcessError as e:
                    state.last_error = e.stderr or str(e)
            threading.Thread(target=apply, daemon=True).start()
def render_monitor():
    cpu = psutil.cpu_percent(None)
    state.cpu_history.append(cpu)
    if len(state.cpu_history) > 100:
        state.cpu_history.pop(0)

    imgui.text(f'CPU Usage: {cpu:.1f}%')
    data = array('f', state.cpu_history)
    imgui.plot_lines('History', data, graph_size=(0, 150))
    imgui.separator()

    metrics = state.metrics
    if imgui.begin_table('metric_table', 4):  # 4列表格
        imgui.table_setup_column('Parameter')
        imgui.table_setup_column('Value')
        imgui.table_setup_column('Offset')
        imgui.table_setup_column('Hex Data')
        imgui.table_headers_row()

        for key, info in metrics.items():
            value = info.get("value", float("nan"))
            offset = info.get("offset", "N/A")
            hexdata = info.get("hexdata", "N/A")

            # 判断单位
            if "thm" in key or "stt" in key:
                unit = "°C"
            elif "tdc" in key or "edc" in key:
                unit = "A"
            elif "ppt" in key or "stapm" in key:
                unit = "W"
            else:
                unit = ""

            imgui.table_next_row()
            imgui.table_set_column_index(0); imgui.text(key)
            imgui.table_set_column_index(1); imgui.text(f"{value:.2f} {unit}")
            imgui.table_set_column_index(2); imgui.text(offset)
            imgui.table_set_column_index(3); imgui.text(hexdata)

        imgui.end_table()


def save_settings():
    config['Settings'] = {
        'start_with_system': str(state.start_with_system),
        'language': str(state.language),
        'theme': str(state.theme),
        'ra_path': state.ra_path
    }
    with open(CONFIG_PATH, 'w') as f: config.write(f)

def render_settings():
    _, state.start_with_system = imgui.checkbox('Start with system', state.start_with_system)
    _, state.language = imgui.combo('Language', state.language, ['English','中文'])
    _, state.theme = imgui.combo('Theme', state.theme, ['Dark','Light','System Default'])
    imgui.separator()
    imgui.text('RyzenAdj Executable Path:')
    changed, path = imgui.input_text('##ra_path', state.ra_path, 256)
    if changed: state.ra_path = path
    if imgui.button('Save'): save_settings()

@window.event
def on_draw():
    window.clear(); imgui.new_frame(); apply_theme()
    w, h = window.get_size(); imgui.set_next_window_position(0, 0); imgui.set_next_window_size(w, h)
    imgui.begin('FullWindow', False,
        imgui.WINDOW_NO_TITLE_BAR|imgui.WINDOW_NO_MOVE|imgui.WINDOW_NO_RESIZE|imgui.WINDOW_NO_SCROLLBAR)
    imgui.begin_child('Menu', 200, h, border=True)
    for name, label in [('welcome','Welcome'), ('adjust','Adjust'), ('monitor','Monitor'), ('settings','Settings')]:
        imgui.push_style_color(imgui.COLOR_BUTTON, *imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND])
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *imgui.get_style().colors[imgui.COLOR_WINDOW_BACKGROUND])
        if imgui.button(label, 180):
            state.page = name
            state.fetch_metrics()
        imgui.pop_style_color(2)
    imgui.end_child(); imgui.same_line()
    imgui.begin_child('Content', w-210, h, border=False)
    if state.page == 'welcome': render_welcome()
    elif state.page == 'adjust': render_adjust()
    elif state.page == 'monitor': render_monitor()
    else: render_settings()
    render_notification()
    imgui.end_child(); imgui.end(); imgui.render(); impl.render(imgui.get_draw_data())

pyglet.app.run()
