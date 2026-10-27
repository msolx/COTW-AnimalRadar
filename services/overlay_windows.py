"""仅查询游戏窗口及注册本程序快捷键；不修改游戏窗口、不安装键盘钩子。"""
import ctypes
import sys
from ctypes import wintypes as W
from PySide6.QtCore import QAbstractNativeEventFilter, QRect
from PySide6.QtGui import QGuiApplication
import config


def match_monitor(screens,monitor):
    """按桌面原点及 DPR 还原的物理尺寸匹配，不把友好名当作 Windows 设备ID。

    Windows 下 Qt 缩放屏幕尺寸但保留原点。拒绝不唯一的镜像/异常布局，
    允许最多2像素的分数缩放取整误差，不按列表顺序或相同分辨率猜屏幕。
    """
    matches = []
    for screen in screens:
        geometry,ratio = screen.geometry(),screen.devicePixelRatio()
        if (abs(geometry.x()-monitor.left) <= 1 and abs(geometry.y()-monitor.top) <= 1
                and abs(round(geometry.width()*ratio)-(monitor.right-monitor.left)) <= 2
                and abs(round(geometry.height()*ratio)-(monitor.bottom-monitor.top)) <= 2):
            matches.append(screen)
    return matches[0] if len(matches) == 1 else None


class WindowBackend(QAbstractNativeEventFilter):
    def __init__(self,callback):
        super().__init__()
        self.callback = callback
        self.registered = []
        self.api = None
        self.error = ''
        if sys.platform != 'win32':
            self.error = '游戏浮窗仅支持 Windows'
            return
        self.api = ctypes.WinDLL('user32',use_last_error=True)
        self.enum_type = ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        # 显式声明 HWND 和指针宽度，避免 x64 句柄被默认 int 截断。
        declarations = {
            'EnumWindows': ([self.enum_type,W.LPARAM],W.BOOL),
            'GetWindowThreadProcessId': ([W.HWND,ctypes.POINTER(W.DWORD)],W.DWORD),
            'IsWindowVisible': ([W.HWND],W.BOOL), 'IsIconic': ([W.HWND],W.BOOL),
            'GetForegroundWindow': ([],W.HWND),
            'GetClientRect': ([W.HWND,ctypes.POINTER(W.RECT)],W.BOOL),
            'ClientToScreen': ([W.HWND,ctypes.POINTER(W.POINT)],W.BOOL),
            'MonitorFromWindow': ([W.HWND,W.DWORD],W.HANDLE),
            'GetMonitorInfoW': ([W.HANDLE,ctypes.c_void_p],W.BOOL),
            'RegisterHotKey': ([W.HWND,ctypes.c_int,W.UINT,W.UINT],W.BOOL),
            'UnregisterHotKey': ([W.HWND,ctypes.c_int],W.BOOL),
        }
        for name,(args,result) in declarations.items():
            fn = getattr(self.api,name)
            fn.argtypes,fn.restype = args,result

    def start(self):
        if not self.api:
            return
        # 取消系统全局热键，避免按键冲突和安全误报；统一在主窗口按钮点击控制
        self.registered = []
        self.error = ''
        self.hotkey_error = ''

    def nativeEventFilter(self,event_type,message):
        msg = W.MSG.from_address(int(message))
        if msg.message == 0x312 and msg.wParam in self.registered:
            # 不在原生消息回调中重建窗口；交回 Qt 事件循环处理。
            from PySide6.QtCore import QTimer
            action = 'toggle' if msg.wParam == 0x61A1 else 'edit'
            QTimer.singleShot(0,lambda: self.callback(action))
            return True,0
        return False,0

    def locate(self,pid):
        """返回客户区 Qt 逻辑坐标和前台状态；只接受扫描器已连接的目标 PID。"""
        if not self.api or not pid:
            return None
        candidates = []
        @self.enum_type
        def visit(hwnd,_):
            owner = W.DWORD()
            self.api.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
            if owner.value == pid and self.api.IsWindowVisible(hwnd) and not self.api.IsIconic(hwnd):
                rect,point = W.RECT(),W.POINT()
                if (self.api.GetClientRect(hwnd,ctypes.byref(rect)) and rect.right > 100 and rect.bottom > 100
                        and self.api.ClientToScreen(hwnd,ctypes.byref(point))):
                    candidates.append((rect.right*rect.bottom,hwnd,rect,point))
            return True
        if not self.api.EnumWindows(visit,0):
            self.error = f'查询游戏窗口失败（Windows {ctypes.get_last_error()}）'
            return None
        if not candidates:
            return None
        _,hwnd,rect,point = max(candidates,key=lambda item:item[0])
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('cbSize',W.DWORD),('rcMonitor',W.RECT),('rcWork',W.RECT),
                        ('dwFlags',W.DWORD),('szDevice',W.WCHAR*32)]
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if not self.api.GetMonitorInfoW(self.api.MonitorFromWindow(hwnd,2),ctypes.byref(info)):
            self.error = '无法查询游戏显示器；浮窗已隐藏'
            return None
        screen = match_monitor(QGuiApplication.screens(),info.rcMonitor)
        if screen is None:
            self.error = '无法匹配游戏显示器的 DPI 坐标；浮窗已隐藏'
            return None
        # 每个显示器分别转换物理像素；保留 Qt 对负坐标、多屏原点的定义。
        ratio = screen.devicePixelRatio()
        origin = screen.geometry().topLeft()
        bounds = QRect(origin.x()+round((point.x-info.rcMonitor.left)/ratio),
                       origin.y()+round((point.y-info.rcMonitor.top)/ratio),
                       round(rect.right/ratio),round(rect.bottom/ratio))
        self.error = getattr(self,'hotkey_error','')
        foreground_pid = W.DWORD()
        self.api.GetWindowThreadProcessId(self.api.GetForegroundWindow(),ctypes.byref(foreground_pid))
        return bounds,foreground_pid.value == pid

    def close(self):
        if self.api:
            for ident in self.registered:
                self.api.UnregisterHotKey(None,ident)
            self.registered.clear()
            QGuiApplication.instance().removeNativeEventFilter(self)
