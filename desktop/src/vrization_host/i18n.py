"""English-first UI catalog. Language preference is independent of stream settings."""
import json
import os
from pathlib import Path
import tempfile

# Keep original Chinese keys stable so existing UI strings stay readable in source.
ENGLISH = {
    'VRization · 桌面 VR 串流': 'VRization · Desktop VR Streaming',
    '把桌面带入你的视野  /  DESKTOP → POCKET VR': 'DESKTOP → POCKET VR',
    'F8  紧急停止控制': 'F8  Stop control',
    '01   连接手机': '01   Connect your phone',
    '电脑地址  {ip} : 8765': 'PC address  {ip} : 8765',
    '手机与电脑连接同一个可信 Wi-Fi，输入地址和六位配对码。': 'Use the same trusted Wi-Fi. Enter the PC address and six-digit pairing code.',
    '开始串流  /  START': 'Start streaming', '停止': 'Stop', '复制连接': 'Copy connection',
    '02   选择模式': '02   Viewing mode', '全屏  Full': 'Full screen',
    '大屏幕  Cinema': 'Cinema', 'FPS 游戏': 'FPS game',
    '串流设置  /  STREAM': 'Stream', 'VR 画面  /  VIEW': 'VR view',
    '游戏控制  /  INPUT': 'Game control',
    '●  尚未启动  /  READY': '●  Ready', '●  已停止  /  STOPPED': '●  Stopped',
    '●  手机已连接  /  LIVE': '●  Phone connected', '●  等待手机连接  /  WAITING': '●  Waiting for phone',
    'JPEG · 局域网 · v0.1.1': 'JPEG · Local network · v0.1.1',
    '就绪。全屏不跟随转头；大屏幕在虚拟空间中显示；FPS 可在桌面授权后控制鼠标。': 'Ready. Full screen stays fixed; Cinema places a screen in VR; FPS controls the mouse after you enable it here.',
    '捕获显示器': 'Capture display', '最长输出边': 'Maximum output edge',
    '目标帧率': 'Target frame rate', 'JPEG 质量': 'JPEG quality',
    ' 选区捕获 · 物理像素坐标 ': ' Region capture · Physical pixels ',
    '启用选区': 'Use region', '左 X': 'Left X', '上 Y': 'Top Y', '宽': 'Width', '高': 'Height',
    '应用': 'Apply', '拖动框选屏幕区域': 'Drag to select a screen region',
    '建议先使用 1280 / 30 FPS / 75 质量。降低宽度和质量可减少网络延迟。\n若游戏呈现黑屏，请切换为无边框窗口模式。声音暂不串流。': 'Start with 1280 / 30 FPS / quality 75. A smaller edge and lower quality reduce traffic.\nIf a game appears black, try a borderless window. Audio streaming is not available yet.',
    '手机盒子适配 · 画面缩放': 'Headset fit · Image scale',
    '画面水平位置': 'Horizontal position', '画面垂直位置': 'Vertical position',
    '双眼画面间距': 'Eye image spacing', '视野角度': 'Field of view',
    '大屏幕距离': 'Cinema screen distance', '镜片畸变补偿': 'Lens distortion',
    '恢复画面默认': 'Reset view',
    '设置会同步到已连接的手机，并自动保存。': 'Settings sync to the connected phone and save automatically.',
    '手机转头 → 游戏视角': 'Head movement → Game camera',
    '1  在手机选择 FPS 模式，保持手机传感器运行。\n2  在下方勾选允许控制，然后在 5 秒内切换到游戏窗口。\n3  按 F8 随时停止。切换窗口、断线或传感器超时也会自动停止。': '1  Select FPS mode on your phone and keep its sensors running.\n2  Enable control below, then switch to your game within 5 seconds.\n3  F8 stops control. Focus changes, disconnects and sensor timeouts also stop it.',
    '转头灵敏度 · 像素 / 弧度': 'Sensitivity · Pixels / radian',
    '反转垂直方向': 'Invert vertical direction',
    '允许手机陀螺仪控制当前游戏鼠标': 'Allow phone head tracking to control the game mouse',
    '控制已停止 / DISARMED': 'Control stopped', '控制已启用 / ARMED': 'Control enabled',
    '重新居中 / RECENTER': 'Recenter',
    '仅在可信局域网使用。部分使用原始输入、管理员权限或反作弊保护的游戏\n可能忽略系统鼠标输入。此软件不绕过游戏保护。': 'Use a trusted local network. Games using raw input, elevated privileges or anti-cheat\nmay ignore system mouse input. VRization does not bypass game protection.',
    '选区超出桌面范围 / Region is outside the desktop': 'The capture region is outside the desktop.',
    '检查串流设置': 'Check stream settings', '拖动选择区域 · Esc 取消': 'Drag to select a region · Esc to cancel',
    '串流服务已启动。如 Windows 询问防火墙，请只允许专用网络。': 'Streaming started. If Windows asks about the firewall, allow private networks only.',
    '无法启动': 'Unable to start', '请先开始串流，再复制连接地址。': 'Start streaming before copying the connection address.',
    '连接地址已复制，请只分享给自己的手机。': 'Connection address copied. Share it only with your own phone.',
    'F8 热键不可用，暂不能启用游戏控制。': 'F8 is unavailable. Game control cannot be enabled.',
    '设置未保存: {error}': 'Could not save settings: {error}',
    '手机已连接。': 'Phone connected.', '手机已断开，控制已停止。': 'Phone disconnected. Control stopped.',
    '语言设置未保存: {error}': 'Could not save language: {error}',
    '先连接手机 / Connect a headset first': 'Connect a headset first.',
    '先选择 FPS 模式 / Select FPS mode first': 'Select FPS mode first.',
    '手机陀螺仪未就绪 / No live headset pose': 'No live headset pose. Check phone sensors.',
    '已启用，5 秒内切换到游戏；F8 停止 / Armed; switch to game, F8 stops': 'Control enabled. Switch to your game within 5 seconds; F8 stops control.',
    'F8 热键被占用，请关闭占用程序 / F8 is in use': 'F8 is in use by another app. Close that app to enable game control.',
}

CHINESE = {
    'headset disconnected': '手机已断开', 'new headset session': '新的手机连接',
    'mode changed': '观看模式已更改', 'mouse armed; switch to your game within 5 seconds': '控制已启用，请在 5 秒内切换到游戏',
    'pose heartbeat expired': '手机姿态数据超时', 'no game window selected within 5 seconds': '5 秒内未选择游戏窗口',
    'foreground window changed': '前台窗口已更改', 'server stopping': '串流服务正在停止',
    'server stopped': '串流服务已停止', 'stream connection stalled': '串流连接已停滞',
    'emergency stop': '紧急停止控制', 'F8 emergency stop': 'F8 紧急停止控制',
    'desktop emergency stop': '电脑端紧急停止控制', 'desktop control disabled': '已关闭电脑控制',
    'selecting capture region': '正在选择捕获区域', 'global F8 unavailable': '全局 F8 热键不可用',
    'language changed': '界面语言已更改，控制已停止',
    'Connect a headset first.': '请先连接手机。', 'Select FPS mode first.': '请先选择 FPS 模式。',
}


def translate(text: str, language: str = 'en', **values) -> str:
    result = CHINESE.get(text, text) if language == 'zh' else ENGLISH.get(text, text)
    return result.format(**values) if values else result


def language_path() -> Path:
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'VRization' / 'language.json'


def load_language(path: Path | None = None) -> str:
    try:
        value = json.loads((path or language_path()).read_text(encoding='utf-8'))
        return 'zh' if value == 'zh' else 'en'
    except (OSError, ValueError):
        return 'en'


def save_language(language: str, path: Path | None = None):
    if language not in ('en', 'zh'):
        raise ValueError('unsupported language')
    path = path or language_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='language-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(language, output)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
