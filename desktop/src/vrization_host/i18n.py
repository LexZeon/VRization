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
    '大屏幕  Cinema': 'Cinema', 'FPS 游戏': 'First-person',
    '串流设置  /  STREAM': 'Stream', 'VR 画面  /  VIEW': 'VR view',
    '游戏控制  /  INPUT': 'Game control',
    '●  尚未启动  /  READY': '●  Ready', '●  已停止  /  STOPPED': '●  Stopped',
    '●  手机已连接  /  LIVE': '●  Phone connected', '●  等待手机连接  /  WAITING': '●  Waiting for phone',
    'JPEG · 局域网 · v{version}': 'JPEG · Local network · v{version}',
    '就绪。全屏不跟随转头；大屏幕在虚拟空间中显示；FPS 可在桌面授权后控制鼠标。': 'Ready. Full screen stays fixed; Cinema places a screen in VR; First-person controls the mouse after you enable it here.',
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
    '1  在手机选择 FPS 模式，保持手机传感器运行。\n2  在下方勾选允许控制，然后在 5 秒内切换到游戏窗口。\n3  按 F8 随时停止。切换窗口、断线或传感器超时也会自动停止。': '1  Select First-person mode on your phone and keep its sensors running.\n2  Enable control below, then switch to your game within 5 seconds.\n3  F8 stops control. Focus changes, disconnects and sensor timeouts also stop it.',
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
    '先选择 FPS 模式 / Select FPS mode first': 'Select First-person mode first.',
    'Select FPS mode first.': 'Select First-person mode first.',
    '手机陀螺仪未就绪 / No live headset pose': 'No live headset pose. Check phone sensors.',
    '已启用，5 秒内切换到游戏；F8 停止 / Armed; switch to game, F8 stops': 'Control enabled. Switch to your game within 5 seconds; F8 stops control.',
    'F8 热键被占用，请关闭占用程序 / F8 is in use': 'F8 is in use by another app. Close that app to enable game control.',
}

CHINESE = {
    'First-person': '第一人称',
    '先选择 FPS 模式 / Select FPS mode first': '请先选择第一人称模式。',
    'Select First-person mode first.': '请先选择第一人称模式。',
    'Ready. Full screen stays fixed; Cinema places a screen in VR; First-person controls the mouse after you enable it here.': '就绪。全屏不跟随转头；大屏幕在虚拟空间中显示；第一人称可在电脑端授权后控制鼠标。',
    '1  Select First-person mode on your phone and keep its sensors running.\n2  Enable control below, then switch to your game within 5 seconds.\n3  F8 stops control. Focus changes, disconnects and sensor timeouts also stop it.': '1  在手机选择第一人称模式，保持手机传感器运行。\n2  在下方勾选允许控制，然后在 5 秒内切换到游戏窗口。\n3  按 F8 随时停止。切换窗口、断线或传感器超时也会自动停止。',
    'Headset editor': '画面编辑',
    'Scale {scale} · Eye spacing {spacing} · X {x} · Y {y}': '缩放 {scale} · 双眼间距 {spacing} · X {x} · Y {y}',
    'Drag one eye sideways to adjust eye spacing: that eye follows your drag and the other moves oppositely. Drag vertically to move both, or drag a corner to resize. Save syncs the fit; Discard keeps your previous fit.': '横向拖动任一眼来调整间距：这一眼跟随拖动，另一眼反方向移动。竖向拖动同时移动双眼，拖动顶点缩放。保存同步适配设置，弃用保留之前的设置。',
    'Drag one eye sideways · The other eye moves oppositely': '横向拖动任一眼 · 另一眼反方向移动',
    'Drag a corner to resize around the center. Drag inside to move: left moves the picture right, and right moves it left. Both eyes change together. Save syncs the fit; Discard keeps your previous fit.': '拖动顶点围绕中心等比例缩放。拖动内部移动：向左拖，画面向右；向右拖，画面向左。双眼同步变化，保存同步适配设置，弃用保留之前的设置。',
    'Drag corners to resize · Horizontal movement is reversed': '拖动顶点缩放 · 水平移动反向',
    'Fit the picture by dragging': '拖动画面，适配你的手机盒子',
    'Drag a corner to resize around the center, or drag inside to move. Both eyes change together. Save applies the preview; Discard keeps your previous fit.': '拖动顶点围绕中心等比例缩放，拖动画面内部移动。双眼同步变化。保存后应用预览，弃用保留之前的适配设置。',
    'Open visual headset editor': '打开可视画面编辑器',
    'Reset all settings to defaults': '一键重置所有设置',
    'Reset restores the default picture, low latency, English and automatic USB. Your selected display/region and installed ADB path stay selected.': '恢复默认画面、低延迟预设、英文与自动 USB。保留已选显示器／选区和已安装 ADB 的路径。',
    'Default settings restored.': '已恢复默认设置。',
    'Visual headset editor': '可视画面编辑器',
    'Drag corners to resize · Drag inside to move': '拖动顶点缩放 · 拖动内部移动',
    'Move inward until the inner edges meet. The fit centers near the seam; corner resizing respects this boundary. Your viewing mode and lens settings are retained.': '向内拖动直到中间两边相接。接近接缝时自动对齐中线；顶点缩放会保留双眼边界。保留原观看模式与镜片设置。',
    'Phone preview shape': '手机预览比例',
    'Save': '保存', 'Discard': '弃用',
    'Changes stay in this preview until you save.': '保存前仅在此预览中调整。',
    'Left eye': '左眼', 'Right eye': '右眼',
    'headset editor opened': '已打开画面编辑，控制停止',
    'headset fit saved': '画面适配已保存', 'settings reset': '设置已重置',
    'USB is preferred. Open the phone app after starting. LAN: use the address and code above.': '优先使用 USB。电脑开始串流后打开手机软件。局域网连接可使用上方地址和配对码。',
    'Performance profile': '性能预设',
    'Low latency · 640 / 60 FPS / Q45': '低延迟 · 640 / 60 FPS / 质量 45',
    'Stable · 640 / 30 FPS / Q50': '稳定 · 640 / 30 FPS / 质量 50',
    'Quality · 960 / 30 FPS / Q60': '画质 · 960 / 30 FPS / 质量 60',
    'Custom': '自定义',
    'Low latency is the default for new users. FPS is a capture target; actual latency depends on the phone and connection. Try borderless mode for black games. Audio is not streamed.': '新用户默认低延迟预设。帧率是捕获目标，实际延迟取决于手机和连接。游戏黑屏可尝试无边框窗口模式。暂不串流声音。',
    'USB connection': 'USB 连接',
    'USB connection…': 'USB 连接…',
    'First-person stabilization strength': '第一人称防抖强度',
    '0% keeps the current response. Increase it to reduce small shakes. Stronger stabilization can slow fine aiming. It applies only to First-person mouse control.': '0% 保持当前转头响应。提高数值可减轻微小抖动，较强防抖可能让细微瞄准变慢。仅作用于第一人称鼠标控制。',
    'JPEG · USB / LAN · v{version}': 'JPEG · USB / 局域网 · v{version}',
    'Detect authorized USB phones automatically (recommended)': '自动检测已授权的 USB 手机（推荐）',
    'Automatic (one Android device)': '自动（仅一台安卓设备）',
    'Choose official SDK adb.exe…': '选择官方 SDK 中的 adb.exe…',
    'Download official Android USB tools…': '下载官方安卓 USB 工具…',
    'Import downloaded USB tools ZIP…': '导入已下载的 USB 工具 ZIP…',
    "For Android, download Windows Platform Tools 37.0.1 from Google, read and accept Google's terms, then import the ZIP. VRization does not download or bundle these tools. Existing installations are kept.": '安卓用户请从 Google 下载 Windows Platform Tools 37.0.1，阅读并接受 Google 条款后再导入 ZIP。VRization 不会自动下载或随包附带这些工具，并保留已有安装。',
    'Android USB tool: {path}': '安卓 USB 工具：{path}',
    'Automatic detection': '自动检测',
    'Could not open the download page. Visit developer.android.com/tools/releases/platform-tools.': '无法打开下载页面，请访问 developer.android.com/tools/releases/platform-tools。',
    "Select Google's downloaded Windows Platform Tools 37.0.1 ZIP": '选择从 Google 下载的 Windows Platform Tools 37.0.1 ZIP',
    'Choose an installation folder. A platform-tools subfolder will be added; existing files will not be replaced.': '选择安装文件夹。工具会放入其 platform-tools 子文件夹，不会替换已有文件。',
    'Choose USB tools installation folder': '选择 USB 工具安装文件夹',
    'Choose folder…': '选择文件夹…',
    'Cancel': '取消',
    'Import USB tools': '导入 USB 工具',
    'Checking and importing USB tools…': '正在校验并导入 USB 工具…',
    'USB tools imported. Unlock the phone, allow USB debugging, then start streaming.': 'USB 工具已导入。请解锁手机、允许 USB 调试，然后开始串流。',
    "This ZIP is not the verified Windows Platform Tools 37.0.1 package. Download it from Google's official page.": '此 ZIP 不是已校验的 Windows Platform Tools 37.0.1 安装包，请从 Google 官方页面下载。',
    'This package has a different version. Use official Windows Platform Tools 37.0.1.': '此安装包版本不同，请使用官方 Windows Platform Tools 37.0.1。',
    'The ZIP is incomplete or unsafe. Download the official Windows package again.': '此 ZIP 不完整或含有不安全路径，请重新下载官方 Windows 安装包。',
    'Choose a full folder path without shortcuts, links or junctions.': '请选择完整文件夹路径，不使用快捷方式、符号链接或目录联接。',
    'This folder contains a different Platform Tools installation. It was kept unchanged; choose a new folder.': '此文件夹中已有不同的 Platform Tools 安装，已保留原样，请选择新文件夹。',
    'An import is already using this folder. Wait for it to finish or choose another folder.': '已有导入任务正在使用此文件夹，请等待完成或选择其他文件夹。',
    'Could not import USB tools. Check folder permissions and free space, then try another folder.': '无法导入 USB 工具，请检查文件夹权限和剩余空间，或选择其他文件夹。',
    'Choose adb.exe from official Android Platform Tools': '选择官方 Android Platform Tools 中的 adb.exe',
    "Android needs USB debugging and this computer's approval. iPhone needs Apple Devices and Trust This Computer. USB does not need a LAN firewall rule. Existing USB mappings are never replaced.": '安卓需开启 USB 调试并授权此电脑；iPhone 需 Apple Devices 并信任此电脑。USB 不需要开放局域网防火墙端口，也不会替换其他软件的 USB 映射。',
    'USB off; use LAN address and pairing code': 'USB 已关闭；请使用局域网地址和配对码',
    'Android USB ready: {serial}': '安卓 USB 已就绪：{serial}',
    'USB port is in use by another application; no mapping changed': 'USB 端口被其他软件占用；未更改已有映射',
    'Choose an Android USB device; multiple devices are connected': '已连接多台安卓设备，请选择用于串流的设备',
    'Unlock Android and allow USB debugging for this computer': '请解锁安卓手机，并允许此电脑进行 USB 调试',
    'Android USB offline; reconnect cable, unlock the phone and allow USB debugging': 'Android USB 离线；请重插数据线、解锁手机并允许 USB 调试',
    'Connect only one iPhone for automatic USB pairing': '自动 USB 配对时请只连接一台 iPhone',
    'iPhone found; start streaming and open the phone app': '已发现 iPhone；请开始串流并打开手机软件',
    'USB waiting: install Android Platform Tools or Apple Devices; LAN is available': 'USB 等待中：请安装 Android Platform Tools 或 Apple Devices；也可使用局域网',
    'Android USB unavailable; check the official Platform Tools path': '安卓 USB 不可用；请检查官方 Platform Tools 路径',
    'Connect a USB phone; enable Android USB debugging or install Apple Devices': '请连接 USB 手机；安卓开启 USB 调试，iPhone 安装 Apple Devices',
    'iPhone USB connected': 'iPhone USB 已连接',
    'iPhone USB disconnected': 'iPhone USB 已断开',
    'iOS USB: {detail}': 'iOS USB：{detail}',
    'USB: {detail}': 'USB：{detail}',
    'headset disconnected': '手机已断开', 'new headset session': '新的手机连接',
    'mode changed': '观看模式已更改', 'mouse armed; switch to your game within 5 seconds': '控制已启用，请在 5 秒内切换到游戏',
    'pose heartbeat expired': '手机姿态数据超时', 'no game window selected within 5 seconds': '5 秒内未选择游戏窗口',
    'foreground window changed': '前台窗口已更改', 'server stopping': '串流服务正在停止',
    'server stopped': '串流服务已停止', 'stream connection stalled': '串流连接已停滞',
    'emergency stop': '紧急停止控制', 'F8 emergency stop': 'F8 紧急停止控制',
    'desktop emergency stop': '电脑端紧急停止控制', 'desktop control disabled': '已关闭电脑控制',
    'selecting capture region': '正在选择捕获区域', 'global F8 unavailable': '全局 F8 热键不可用',
    'language changed': '界面语言已更改，控制已停止',
    'Connect a headset first.': '请先连接手机。', 'Select FPS mode first.': '请先选择第一人称模式。',
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
