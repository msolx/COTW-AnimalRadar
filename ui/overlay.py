"""与完整窗口共享过滤结果的轻量浮窗；配置只保存布局，不保存动物坐标。"""
import json
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtGui import QPainter,QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
                              QSlider,QSizeGrip,QApplication,QSizePolicy)
import config
from ui.radar_widget import RadarWidget
from services.species import chinese
from services.reserves import RESERVES


def load_settings(path):
    defaults = dict(x=config.OVERLAY_OFFSET[0],y=config.OVERLAY_OFFSET[1],
                    size=config.OVERLAY_SIZE,height=config.OVERLAY_HEIGHT,
                    alpha=config.OVERLAY_BACKGROUND_ALPHA,enabled=True)
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw,dict):
            return defaults
        for key,low,high in (('x',0,10000),('y',0,10000),
                             ('size',config.OVERLAY_MIN_SIZE,config.OVERLAY_MAX_SIZE),
                             ('height',config.OVERLAY_MIN_SIZE+100,config.OVERLAY_MAX_SIZE+100),('alpha',30,240)):
            value = raw.get(key)
            if type(value) is int and low <= value <= high:
                defaults[key] = value
        if type(raw.get('enabled')) is bool:
            defaults['enabled'] = raw['enabled']
    except (OSError,ValueError):
        pass
    return defaults


class DragTitle(QLabel):
    def mousePressEvent(self,event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().editing:
            self.anchor = event.globalPosition().toPoint()-self.window().pos()

    def mouseMoveEvent(self,event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self,'anchor'):
            self.window().move(event.globalPosition().toPoint()-self.anchor)

    def mouseReleaseEvent(self,event):
        self.window().remember_geometry()


class MiniRadar(QWidget):
    def __init__(self,owner,native=True):
        super().__init__(None)
        self.owner = owner
        self.settings = load_settings(config.OVERLAY_SETTINGS_FILE)
        self.editing = False
        self.bounds = None
        self.backend = None
        self.dragging_layout = False
        self.last_follow_state = None
        self.setWindowTitle('Animal Navigator 小雷达')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet('QWidget { background: transparent; color: #edf7f8; font-size: 12px; } '
                           'QPushButton { background: #29434b; padding: 4px; }')
        self.setMinimumSize(config.OVERLAY_MIN_SIZE,config.OVERLAY_MIN_SIZE+100)
        self.setMaximumSize(config.OVERLAY_MAX_SIZE,config.OVERLAY_MAX_SIZE+100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,8,10,8)
        layout.setSpacing(2)
        self.title = DragTitle('COTW · 探索雷达')
        layout.addWidget(self.title)
        self.caption = QLabel('等待新采样')
        layout.addWidget(self.caption)
        self.radar = RadarWidget(compact=True)
        self.radar.selected.connect(owner.select_region)
        layout.addWidget(self.radar,1)
        self.info = QLabel('50米区域 · 橙色受伤 / 灰叉尸体')
        layout.addWidget(self.info)
        self.hint = QLabel('')
        self.hint.setVisible(False)
        layout.addWidget(self.hint)
        for label in (self.title,self.caption,self.hint,self.info):
            label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.tools = QWidget()
        row = QHBoxLayout(self.tools)
        row.setContentsMargins(0,0,0,0)
        self.bg_label = QLabel('背景')
        row.addWidget(self.bg_label)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(30,240)
        self.opacity.setValue(self.settings['alpha'])
        self.opacity.valueChanged.connect(self.change_alpha)
        self.opacity.sliderReleased.connect(self.save)
        row.addWidget(self.opacity,1)
        self.lock_btn = QPushButton('锁定')
        self.lock_btn.clicked.connect(lambda:self.set_editing(False))
        row.addWidget(self.lock_btn)
        self.grip = QSizeGrip(self)
        row.addWidget(self.grip)
        layout.addWidget(self.tools)
        self.retranslate_ui()
        self.resize(self.settings['size'],self.settings['height'])
        self.set_editing(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.follow)
        if native:
            from services.overlay_windows import WindowBackend
            self.backend = WindowBackend(self.hotkey)
            self.backend.start()
            self.timer.start(config.OVERLAY_POLL_MS)

    def retranslate_ui(self):
        from services.i18n import t, get_lang
        self.setWindowTitle(t('overlay_title'))
        self.title.setText(t('overlay_title'))
        self.info.setText(t('overlay_info'))
        self.bg_label.setText(t('overlay_bg_label'))
        self.lock_btn.setText(t('overlay_lock_btn'))
        if self.editing:
            is_zh = get_lang() == 'zh'
            self.hint.setText('拖动标题移位 · 右下角缩放 · 点击下方锁定' if is_zh else 'Drag title to move · Drag corner to resize · Click Lock')
        self.radar.update()

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor('#52747d'))
        painter.setBrush(QColor(16,30,36,self.settings['alpha']))
        painter.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),12,12)

    def sync(self,message=None):
        owner = self.owner
        self.radar.north_up = owner.radar.north_up
        self.radar.radius = owner.radar.radius
        self.radar.target = owner.radar.target
        self.radar.highlight_trophies = owner.radar.highlight_trophies
        self.radar.set_data(owner.radar.player,owner.display_regions)
        reserve = RESERVES.get(owner.selected_reserve,('保护区未确认',()))[0]
        species = chinese(owner.species.currentData()) if owner.species.currentData() else '所有动物'
        self.title.setText(f'{reserve} · {species}'+(' · 拖动标题调整' if self.editing else ''))
        self.title.setToolTip(self.title.text())
        if not owner.radar.player:
            self.caption.setText(message or owner.summary.text().split('\n')[0])
        else:
            regions = owner.display_regions
            alive = sum(r.count for r in regions if r.vital_status in ('alive','wounded'))
            dead = sum(r.count for r in regions if r.vital_status == 'dead')
            unknown = sum(r.count for r in regions if r.vital_status == 'unknown')
            nearest = f'约{regions[0].distance_min:g}～{regions[0].distance_max:g}米' if regions else '未检测到目标'
            from services.trophy import region_quality
            quality = sum(region_quality(r)[0] for r in regions) if self.radar.highlight_trophies else 0
            diamonds = sum(sum(1 for a in r.members if getattr(a,'trophy_prediction',None) in ('diamond','great_one')) for r in regions) if self.radar.highlight_trophies else 0
            trophy_tag = ''
            if diamonds:
                trophy_tag = f' · 💎潜在钻石 {diamonds}只'
            elif quality:
                trophy_tag = f' · 潜在白银+ {quality}（预测）'
            self.caption.setText(f'活{alive} / 尸{dead} / 未知{unknown} · {nearest}'+trophy_tag)
        self.caption.setToolTip(owner.state.text())
        self.radar.update()

    def set_editing(self,editing):
        self.remember_geometry()
        self.editing = editing
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        if not editing:
            flags |= Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        self.tools.setVisible(editing)
        self.hint.setVisible(editing)
        from services.i18n import get_lang
        is_zh = get_lang() == 'zh'
        if editing:
            self.hint.setText('拖动标题移位 · 右下角缩放 · 点击下方锁定' if is_zh else 'Drag title to move · Drag corner to resize · Click Lock')
        self.sync()
        self.save()
        if was_visible:
            self.show()

    def hotkey(self,action):
        # 全局快捷键只在游戏前台或本程序正在调整时生效，避免干扰其它应用。
        found = self.backend.locate(self.owner.game_pid) if self.backend else None
        if not (found and found[1]) and not (self.editing and (self.isActiveWindow() or self.owner.isActiveWindow())):
            return
        if action == 'toggle':
            self.toggle()
        else:
            self.settings['enabled'] = True
            self.set_editing(not self.editing)
            self.follow()

    def toggle(self):
        self.settings['enabled'] = not self.settings['enabled']
        self.save()
        if not self.settings['enabled']:
            self.hide()
        self.follow()

    def change_alpha(self,value):
        self.settings['alpha'] = value
        self.update()

    def remember_geometry(self):
        if self.bounds is not None and self.editing:
            self.settings.update(x=max(0,self.x()-self.bounds.x()),y=max(0,self.y()-self.bounds.y()),
                                 size=self.width(),height=self.height())
            self.save()

    def save(self):
        try:
            path = config.OVERLAY_SETTINGS_FILE
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8')
            temp.replace(path)
        except OSError as exc:
            self.hint.setText(f'布局保存失败：{exc}')

    def follow(self):
        if not self.backend:
            return
        found = self.backend.locate(self.owner.game_pid)
        own_edit = self.editing and (self.isActiveWindow() or self.owner.isActiveWindow())
        if not self.settings['enabled'] or not found or (not found[1] and not own_edit):
            self.hide()
            reason = ('已在主界面隐藏' if not self.settings['enabled'] else
                      (self.backend.error or '等待可见游戏窗口（未启动、最小化或尚未连接）') if not found else
                      '游戏不在前台，浮窗已隐藏')
            self.report_follow_state(reason)
            return
        bounds,_ = found
        self.bounds = bounds
        # 尺寸恢复与拖动都夹到当前客户区，切分辨率后不遗留屏幕外浮窗。
        width = min(self.width() if self.editing else self.settings['size'],bounds.width())
        height = min(self.height() if self.editing else self.settings['height'],bounds.height())
        if bounds.width() < self.minimumWidth() or bounds.height() < self.minimumHeight():
            self.hide()  # 客户区过小时不把面板画到游戏之外
            self.report_follow_state('游戏客户区过小，浮窗已隐藏')
            return
        self.resize(width,height)
        x = min(self.settings['x'],max(0,bounds.width()-self.width()))
        y = min(self.settings['y'],max(0,bounds.height()-self.height()))
        if not self.editing or not QApplication.mouseButtons():
            self.move(bounds.topLeft()+QPoint(x,y))
        if not self.isVisible():
            self.show()
        self.report_follow_state('调整模式' if self.editing else '显示中（鼠标穿透）')

    def report_follow_state(self,reason):
        """记录变化后的状态；Qt窗口可见不等于游戏画面已通过人工验收。"""
        report = dict(reason=reason,visible=self.isVisible(),editing=self.editing,
                      enabled=self.settings['enabled'],game_pid=self.owner.game_pid,
                      hotkeys_registered=len(getattr(self.backend,'registered',())),
                      backend_error=self.backend.error if self.backend else '')
        if report == self.last_follow_state:
            return
        self.last_follow_state = report
        if hasattr(self.owner,'overlay_status'):
            self.owner.overlay_status.setText('微型雷达：'+reason+
                ('；'+report['backend_error'] if report['backend_error'] else ''))
        try:
            path = config.OVERLAY_STATUS_FILE
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            temp.replace(path)
        except OSError:
            pass  # 诊断失败不影响游戏读取或窗口安全规则

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.editing and self.bounds is not None:
            self.settings['size'] = self.width()
            self.settings['height'] = self.height()

    def shutdown(self):
        self.remember_geometry()
        self.timer.stop()
        if self.backend:
            self.backend.close()
        self.hide()
        self.close()
