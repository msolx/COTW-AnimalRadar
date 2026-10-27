import time
from dataclasses import replace
from PySide6.QtCore import QTimer, QSignalBlocker
from PySide6.QtGui import QGuiApplication,QColor
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
                              QComboBox,QPushButton,QListWidget,QTableWidget,QTableWidgetItem,
                              QAbstractItemView,QHeaderView,QCheckBox)
import config
from services.scanner import Scanner
from services.mock import MockSource
from services.species import chinese,canonical
from services.reserves import RESERVES,species_for,unexpected_species,mission_species
from services.coordinate import aggregate
from ui.radar_widget import RadarWidget
from services.animal_details import STATE_LABELS,details_row,animal_tooltip,matches_state
from services.trophy import region_quality,trophy_text,COLORS
from services.i18n import init_i18n, t, toggle_lang, get_lang

class MainWindow(QMainWindow):
    def __init__(self,source=None,start_scanner=True):
        super().__init__()
        init_i18n(config.ROOT / 'radar_settings.json')
        self.source = source or config.SOURCE
        self.field_test = self.source == 'field_test'
        self.session_ended = False
        self.closing = False
        self.reserve_confirmed = False
        self.scene_notice = False
        self.setWindowTitle(t('app_title_radar'))
        radar_ico = config.ROOT / 'icons' / 'radar.ico'
        if radar_ico.exists():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(radar_ico)))
        self.resize(1000,740)
        self.current = None
        self.overlay = None
        self.game_pid = 0
        self.display_regions = []
        self.selected_reserve = 'layton' if self.source == 'mock' else config.INITIAL_RESERVE
        self.setStyleSheet('''
            QWidget { background: #131f25; color: #e2edf0; font-size: 14px; }
            QPushButton { padding: 6px 12px; background: #233e47; border: 1px solid #365b67; border-radius: 4px; color: #e5f1f3; }
            QPushButton:hover { background: #2d505c; border: 1px solid #4a7d8d; }
            QPushButton:pressed { background: #1a2f36; }
            QPushButton:disabled { background: #18282e; border: 1px solid #23373e; color: #657e85; }
            QPushButton:checked { background: #25606e; border: 1px solid #3ea2b8; color: #ffffff; }
            QComboBox { padding: 6px 10px; background: #233e47; border: 1px solid #365b67; border-radius: 4px; color: #e5f1f3; }
            QComboBox:hover { border: 1px solid #4a7d8d; }
            QComboBox QAbstractItemView { background: #182b32; border: 1px solid #365b67; selection-background-color: #2b5665; selection-color: #ffffff; color: #e2edf0; }
            QListWidget { background: #16242a; border: 1px solid #28444e; border-radius: 4px; padding: 4px; }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #1e333b; border-radius: 3px; }
            QListWidget::item:hover { background: #1f3640; }
            QListWidget::item:selected { background: #2b5463; color: #ffffff; }
            QTableWidget { background: #16242a; alternate-background-color: #192a31; border: 1px solid #28444e; border-radius: 4px; gridline-color: #233a44; }
            QTableWidget::item:selected { background: #2b5463; color: #ffffff; }
            QHeaderView::section { background: #20353e; color: #a4c7cf; font-weight: bold; padding: 5px; border: none; border-right: 1px solid #28444e; border-bottom: 1px solid #28444e; }
            QCheckBox { spacing: 8px; color: #cbdbe0; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #3d6370; border-radius: 3px; background: #1a2d34; }
            QCheckBox::indicator:hover { border: 1px solid #548799; }
            QCheckBox::indicator:checked { background: #00bcd4; border: 1px solid #00e5ff; }
            QScrollBar:vertical { background: #131f25; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #2a4752; min-height: 20px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #39606e; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        ''')
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        top_row = QHBoxLayout()
        if self.field_test:
            self.notice_label = QLabel(t('radar_banner_notice'))
            self.notice_label.setWordWrap(True)
            self.notice_label.setStyleSheet('color: #f3c46e; padding: 8px; background: #1a2f38; border-left: 3px solid #f3c46e; border-radius: 4px;')
            top_row.addWidget(self.notice_label, 1)
            self.reserve_confirm = QPushButton(t('enable_north_up'))
            self.reserve_confirm.setToolTip(t('north_up_tooltip'))
            self.reserve_confirm.clicked.connect(self.confirm_reserve)
            top_row.addWidget(self.reserve_confirm)
        else:
            top_row.addStretch()

        self.lang_btn = QPushButton(t('lang_btn_text'))
        self.lang_btn.setObjectName('lang_btn')
        self.lang_btn.setStyleSheet('background: #254a57; border: 1px solid #488a9e; color: #a5f3fc; font-weight: bold; padding: 6px 12px;')
        self.lang_btn.clicked.connect(self.toggle_language)
        top_row.addWidget(self.lang_btn)
        layout.addLayout(top_row)

        self.state = QLabel('启动中')
        self.state.setWordWrap(True)
        self.state.setStyleSheet('color: #6fe3b8; font-weight: bold; padding: 4px;')
        layout.addWidget(self.state)
        reserve_row = QHBoxLayout()
        self.reserve_label = QLabel(t('reserve_prefix'))
        reserve_row.addWidget(self.reserve_label)
        self.reserve = QComboBox()
        self.reserve.addItem('保护区未确认／其它（仅当前采样）',None)
        for key,(label,_) in RESERVES.items():
            self.reserve.addItem(f'{label} · {len(RESERVES[key][1])}种（手动选择）',key)
        self.reserve.setCurrentIndex(max(0,self.reserve.findData(self.selected_reserve)))
        reserve_row.addWidget(self.reserve,1)
        self.reserve_lock = QPushButton(t('reserve_lock'))
        self.reserve_lock.setCheckable(True)
        self.reserve_lock.toggled.connect(self.set_reserve_lock)
        self.reserve_lock.setChecked(self.selected_reserve in RESERVES)
        reserve_row.addWidget(self.reserve_lock)
        self.life_filter = QComboBox()
        self.life_filter.addItem('全部状态（含尸体）',None)
        for key,label in STATE_LABELS.items():
            self.life_filter.addItem('存活（含受伤）' if key == 'alive' else label,key)
        reserve_row.addWidget(self.life_filter)
        layout.addLayout(reserve_row)
        controls = QHBoxLayout()
        self.species = QComboBox()
        self.rebuild_species()
        if self.field_test:
            self.reserve_confirm.setEnabled(self.selected_reserve in config.NORTH_UP_RESERVES)
        controls.addWidget(self.species)
        scale = QComboBox()
        for value in config.RADAR_RANGES:
            scale.addItem(f'{value}米半径',value)
        scale.setCurrentIndex(config.RADAR_RANGES.index(config.RADAR_RANGE))
        controls.addWidget(scale)
        interval = QComboBox()
        for value in config.REFRESH_CHOICES:
            interval.addItem(f'每{value}秒刷新',value)
        interval.setCurrentIndex(config.REFRESH_CHOICES.index(config.REFRESH_SECONDS))
        controls.addWidget(interval)
        self.pause = QPushButton('暂停刷新')
        controls.addWidget(self.pause)
        reconnect = QPushButton('重新连接')
        self.reconnect_button = reconnect
        controls.addWidget(reconnect)
        layout.addLayout(controls)
        body = QHBoxLayout()
        self.radar = RadarWidget()
        self.radar.radius = config.RADAR_RANGE
        self.radar.north_up = False  # 开窗未确认北向；采样失败不撤销用户的手动选项。
        body.addWidget(self.radar,3)
        side = QVBoxLayout()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet('background: #182b32; border: 1px solid #27434e; border-radius: 6px; padding: 8px;')
        side.addWidget(self.summary)
        self.regions = QListWidget()
        side.addWidget(self.regions)
        self.details_label = QLabel('选择区域查看个体详情；未验证字段显示未知')
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet('color: #a4c7cf; font-size: 13px; padding-top: 3px;')
        side.addWidget(self.details_label)
        self.details = QTableWidget(0,8)
        self.details.setHorizontalHeaderLabels(['个体','状态','性别','生命值','毛色','难度','存档评分','潜在评级'])
        self.details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.details.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.details.verticalHeader().hide()
        self.details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.details.horizontalHeader().setStretchLastSection(True)
        self.details.setMinimumHeight(150)
        side.addWidget(self.details)
        self.target = QLabel('点击区域选择探索目标；无地理朝向校准。')
        self.target.setWordWrap(True)
        self.target.setStyleSheet('background: #182b32; border: 1px solid #27434e; border-radius: 6px; padding: 8px; color: #a4dbe7;')
        side.addWidget(self.target)
        body.addLayout(side,2)
        layout.addLayout(body)
        if self.source == 'mock':
            factory = MockSource
        elif self.source in ('live','field_test'):
            from services.live import LiveSource
            factory = lambda: LiveSource(field_test=self.field_test)
        else:
            raise ValueError('SOURCE 必须为 mock / live / field_test')
        self.scanner = Scanner(factory,config.REFRESH_SECONDS)
        self.scanner.set_reserve(self.selected_reserve)
        if self.field_test:
            self.details_trial = QCheckBox('属性试验：存档唯一匹配性别/评分；毛色、难度、奖牌为预测（尚待实机核对）')
            self.details_trial.setChecked(config.DETAILS_JOIN_ENABLED)
            self.details_trial.toggled.connect(self.toggle_details_trial)
            layout.addWidget(self.details_trial)
        self.trophy_highlight = QCheckBox('亮色块提示潜在白银/黄金及💎钻石（评分预测，需有效属性来源）')
        self.trophy_highlight.setChecked(config.TROPHY_HIGHLIGHT_ENABLED)
        self.trophy_highlight.toggled.connect(self.toggle_trophy_highlight)
        layout.addWidget(self.trophy_highlight)
        self.scanner.snapshot.connect(self.receive)
        self.scanner.finished.connect(self.scanner_finished)
        self.session_timer = QTimer(self)
        self.session_timer.setSingleShot(True)
        self.session_timer.timeout.connect(self.end_session)
        if start_scanner:
            self.scanner.start()
            if self.field_test and config.FIELD_TEST_SESSION_SECONDS > 0:
                self.session_timer.start(config.FIELD_TEST_SESSION_SECONDS*1000)
        self.pause.clicked.connect(self.toggle_pause)
        self.reserve.currentIndexChanged.connect(self.change_reserve)
        reconnect.clicked.connect(self.reconnect)
        self.species.currentIndexChanged.connect(self.render)
        self.life_filter.currentIndexChanged.connect(self.render)
        scale.currentIndexChanged.connect(lambda: self.change_scale(scale.currentData()))
        interval.currentIndexChanged.connect(lambda: self.scanner.set_interval(interval.currentData()))
        self.radar.selected.connect(self.select_region)
        self.regions.currentRowChanged.connect(self.select_row)
        self.watchdog = QTimer(self)
        self.watchdog.timeout.connect(self.check_stale)
        self.watchdog.start(1000)
        # 离屏测试不枚举真实窗口、不注册系统快捷键，也不启动第二个扫描器。
        if config.OVERLAY_ENABLED and QGuiApplication.platformName() != 'offscreen':
            from ui.overlay import MiniRadar
            self.overlay = MiniRadar(self,native=self.source != 'mock')
            overlay_row = QHBoxLayout()
            self.btn_show_overlay = QPushButton(t('btn_toggle_overlay'))
            self.btn_edit_overlay = QPushButton(t('btn_edit_overlay'))
            self.btn_show_overlay.clicked.connect(self.overlay.toggle)
            self.btn_edit_overlay.clicked.connect(self.edit_overlay)
            overlay_row.addWidget(self.btn_show_overlay)
            overlay_row.addWidget(self.btn_edit_overlay)
            self.overlay_hint = QLabel(t('overlay_hint_text'))
            self.overlay_status = self.overlay_hint
            self.overlay_hint.setWordWrap(True)
            overlay_row.addWidget(self.overlay_hint,1)
            layout.addLayout(overlay_row)
            if self.overlay.backend and self.overlay.backend.error:
                self.overlay_hint.setText(self.overlay.backend.error)
            if self.source == 'mock':
                self.overlay_hint.setText('模拟小雷达：点“调整微型雷达”预览；真实浮窗使用现场测试入口')

    def edit_overlay(self):
        if not self.overlay:
            return
        self.overlay.settings['enabled'] = True
        self.overlay.set_editing(True)
        if self.source == 'mock':
            self.overlay.move(self.pos())
            self.overlay.show()
        else:
            self.overlay.follow()

    def sync_overlay(self,message=None):
        if self.overlay:
            self.overlay.sync(message)

    def toggle_trophy_highlight(self,enabled):
        self.radar.highlight_trophies = bool(enabled)
        self.render()
        self.radar.update()
        self.sync_overlay()

    def toggle_details_trial(self,enabled):
        self.scanner.set_details_enabled(enabled)
        self.current = None
        self.clear_data('属性试验选项已更新，等待新采样；未匹配记录显示未知')
        self.state.setText('属性试验已开启（来源分列标注）' if enabled else '属性试验已关闭')

    def receive(self,snapshot):
        if self.session_ended or self.closing or snapshot.generation != self.scanner.generation:
            return
        changed = snapshot.scene_changed or (self.current and self.current.scene_id
                  and snapshot.scene_id and self.current.scene_id != snapshot.scene_id)
        if self.field_test and (changed or not snapshot.connected):
            self.radar.target = None
            # 连接状态不等于游戏地图ID；重连/瞬时失败不能推翻手动选择。
            # 只清理实体与目标，保留保护区和其已启用北向，真实切图由用户更换。
            if changed and self.current is not None and self.selected_reserve in RESERVES:
                self.scene_notice = True
        self.current = snapshot
        if snapshot.game_pid:
            self.game_pid = snapshot.game_pid
        self.rebuild_species(a.species for a in snapshot.animals)
        if not self.scanner.paused.is_set():
            self.render()

    def render(self,*_):
        s = self.current
        if self.scanner.paused.is_set() or self.session_ended:
            return
        if not s:
            return
        if time.time()-s.timestamp > max(3,self.scanner.interval*2.5):
            self.clear_data('数据已过期，等待下一次有效采样')
            return
        self.state.setText(f'{s.message} | 更新时间 {time.strftime("%H:%M:%S",time.localtime(s.timestamp))}')
        if self.scene_notice:
            self.state.setText(self.state.text()+' | 连接/场景已更新，保留手动保护区；若已切图请点“更换保护区”')
        if not s.connected or not s.player:
            self.clear_data('当前无有效实时数据，已清理标记')
            return
        species = self.species.currentData()
        allowed = set(species_for(self.selected_reserve,(a.species for a in s.animals)))
        allowed.update(mission_species(self.selected_reserve))
        mismatches = unexpected_species(self.selected_reserve,(a.species for a in s.animals))
        if mismatches:
            self.state.setText(self.state.text()+' | 名录外候选：'+
                               '、'.join(chinese(name) for name in mismatches)+'；请核对保护区，已从雷达排除')
        # 名称仅作规范拼写转换；不能根据保护区把含糊的缩写猜成某个物种。
        animals = [replace(a,species=canonical(a.species)) for a in s.animals
                   if a.status == 'loaded' and canonical(a.species) in allowed
                   and (not species or canonical(a.species) == species)
                   and matches_state(a.vital_status,self.life_filter.currentData())]
        missions = set(mission_species(self.selected_reserve)) & {a.species for a in animals}
        if missions:
            self.state.setText(self.state.text()+' | 任务专属候选：'+
                               '、'.join(chinese(name) for name in sorted(missions)))
        self.display_regions = aggregate(animals,s.player.position)
        self.radar.north_up = self.field_test and self.reserve_confirmed and config.FIELD_TEST_NORTH_UP
        self.radar.set_data(s.player,self.display_regions)
        self.target.setText('点击区域选择探索目标；参照雷达标注的坐标朝向。')
        self.clear_details()
        with QSignalBlocker(self.regions):
            self.regions.clear()
            for i,r in enumerate(self.display_regions):
                number,quality = region_quality(r) if self.radar.highlight_trophies else (0,None)
                tag = ''
                if number:
                    if quality == 'diamond':
                        tag = f' · 💎潜在钻石 {number}只（预测）'
                    elif quality == 'great_one':
                        tag = f' · 👑潜在珍奇 {number}只（预测）'
                    elif quality == 'gold':
                        tag = f' · ★潜在黄金 {number}只（预测）'
                    else:
                        tag = f' · ★潜在白银+ {number}只（预测）'
                self.regions.addItem(f'区域{i+1} · {chinese(r.species)} · {STATE_LABELS.get(r.vital_status,"未知")} {r.count}个\n约{r.distance_min:g}～{r.distance_max:g}米'+tag)
                if number:
                    item = self.regions.item(i)
                    item.setForeground(QColor(COLORS[quality]))
                    if quality in ('diamond', 'great_one'):
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)
                if r.key == self.radar.target:
                    self.regions.setCurrentRow(i)
                    self.select_region(r)
        name = chinese(species) if species else '所有动物'
        if not animals:
            filtered = '（当前状态筛选）' if self.life_filter.currentData() else ''
            self.summary.setText(f'当前目标：{name}\n当前未检测到已加载的{name}{filtered}，不代表整个保护区不存在{name}。')
        else:
            nearest = self.display_regions[0]
            unknown = sum(a.vital_status == 'unknown' for a in animals)
            alive = sum(a.vital_status == 'alive' for a in animals)
            dead = sum(a.vital_status == 'dead' for a in animals)
            wounded = sum(a.vital_status == 'wounded' for a in animals)
            label = '已加载候选（生命状态未知）' if unknown == len(animals) else '已加载'
            reserve = (RESERVES[self.selected_reserve][0]+'（手动锁定）'
                       if self.selected_reserve in RESERVES and self.reserve_lock.isChecked() else
                       RESERVES[self.selected_reserve][0]+'（手动选择）'
                       if self.selected_reserve in RESERVES else '未确认／其它，仅当前采样')
            self.summary.setText(f'当前目标：{name}\n{label}：{len(animals)}个\n存活{alive+wounded}（受伤{wounded}） / 尸体{dead} / 未知{unknown}\n最近区域：约{nearest.distance_min:g}～{nearest.distance_max:g}米\n保护区：{reserve}\n选择区域查看当前个体详情。')
        self.sync_overlay()

    def clear_data(self,message):
        self.radar.set_data(None,[])
        self.regions.clear()
        self.display_regions = []
        self.summary.setText(message)
        self.target.setText('尚未选择有效区域')
        self.clear_details()
        self.sync_overlay(message)

    def clear_details(self):
        self.details.setRowCount(0)
        self.details_label.setText('选择区域查看个体详情；未验证字段显示未知')

    def show_details(self,region):
        self.details_label.setText(f'{chinese(region.species)} · {STATE_LABELS.get(region.vital_status,"未知")} · {region.count}个\n生命值为当前/最大值比例；性别、毛色、难度需独立验证')
        self.details.setRowCount(len(region.members))
        for row,animal in enumerate(region.members):
            for column,value in enumerate((str(row+1),)+details_row(animal)+trophy_text(animal)):
                item = QTableWidgetItem(value)
                item.setToolTip(animal_tooltip(animal))
                if column == 7:
                    pred = getattr(animal, 'trophy_prediction', None)
                    if pred == 'diamond':
                        item.setText('💎 ' + value)
                        item.setForeground(QColor('#00f0ff'))
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)
                    elif pred == 'great_one':
                        item.setText('👑 ' + value)
                        item.setForeground(QColor('#ff6bdf'))
                    elif pred == 'gold':
                        item.setText('★ ' + value)
                        item.setForeground(QColor('#ffd45f'))
                    elif pred == 'silver':
                        item.setText('★ ' + value)
                        item.setForeground(QColor('#d4e9f7'))
                self.details.setItem(row,column,item)

    def select_row(self,index):
        if 0 <= index < len(self.display_regions):
            self.select_region(self.display_regions[index])

    def select_region(self,region):
        self.radar.target = region.key
        self.radar.update()
        self.show_details(region)
        self.target.setText(f'探索目标：{chinese(region.species)} · {STATE_LABELS.get(region.vital_status,"未知")} · {region.count}只\n约{region.distance_min:g}～{region.distance_max:g}米\n参照雷达高亮区域前往。')
        self.sync_overlay()

    def change_scale(self,value):
        self.radar.radius = value
        self.radar.update()
        self.sync_overlay()

    def toggle_pause(self):
        self.current = None
        if self.scanner.paused.is_set():
            self.scanner.resume_refresh()
            self.pause.setText('暂停刷新')
            self.state.setText('等待新采样')
        else:
            self.scanner.pause_refresh()
            self.pause.setText('恢复刷新')
            self.state.setText('已暂停刷新；无实时标记')
        self.clear_data('等待新采样；暂停期间不展示实时位置')

    def reconnect(self):
        self.current = None
        # 重连只重置连接，不擅自恢复用户暂停的内存读取。
        message = ('已请求重置连接；刷新仍暂停，请点击“恢复刷新”'
                   if self.scanner.paused.is_set() else '正在等待重新连接')
        self.state.setText(message)
        self.clear_data(message)
        self.scanner.request_reconnect()

    def set_reserve_lock(self,locked):
        # 防止切屏回来时滚轮/键盘意外更改保护区；用户可明确解锁再选择。
        self.reserve.setEnabled(not locked)
        self.reserve_lock.setText('更换保护区' if locked else '锁定选择')

    def rebuild_species(self,observed=()):
        previous = self.species.currentData()
        observed = {canonical(name) for name in observed}
        items = [('所有动物',None)]
        items += [(chinese(name),name) for name in species_for(self.selected_reserve,observed)]
        items += [(chinese(name)+'（任务专属候选）',name)
                  for name in sorted(set(mission_species(self.selected_reserve)) & observed)]
        # 名录未变化时保留控件，避免每秒重建打断用户展开菜单或键盘选择。
        if items == [(self.species.itemText(i),self.species.itemData(i))
                     for i in range(self.species.count())]:
            return
        with QSignalBlocker(self.species):
            self.species.clear()
            for label,name in items:
                self.species.addItem(label,name)
            index = self.species.findData(previous)
            self.species.setCurrentIndex(max(0,index))

    def change_reserve(self,*_):
        self.selected_reserve = self.reserve.currentData()
        self.scanner.set_reserve(self.selected_reserve)
        self.reserve_confirmed = False
        self.radar.north_up = False
        self.scene_notice = False
        self.reserve_lock.setChecked(self.selected_reserve in RESERVES)
        if self.field_test:
            self.reserve_confirm.setEnabled(self.selected_reserve in config.NORTH_UP_RESERVES)
            self.reserve_confirm.setText(t('enable_north_up'))
            self.reserve_confirm.setStyleSheet('')
        self.rebuild_species()
        # 先丢弃旧帧并增加代次，再让后台重新连接，不能用旧地图快照填充新菜单。
        self.reconnect()

    def confirm_reserve(self):
        if self.selected_reserve not in config.NORTH_UP_RESERVES:
            return
        self.reserve_confirmed = True
        self.scene_notice = False
        self.radar.north_up = config.FIELD_TEST_NORTH_UP
        if hasattr(self, 'reserve_confirm'):
            self.reserve_confirm.setText(t('north_up_enabled'))
            self.reserve_confirm.setStyleSheet('background: #1f5442; color: #82f5c2; font-weight: bold; border: 1px solid #338a6a;')
        self.render()
        self.radar.update()

    def toggle_language(self):
        toggle_lang()
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(t('app_title_radar'))
        if hasattr(self, 'lang_btn'):
            self.lang_btn.setText(t('lang_btn_text'))
        if hasattr(self, 'notice_label'):
            self.notice_label.setText(t('radar_banner_notice'))
        if hasattr(self, 'reserve_confirm'):
            self.reserve_confirm.setText(t('north_up_enabled') if self.reserve_confirmed else t('enable_north_up'))
            self.reserve_confirm.setToolTip(t('north_up_tooltip'))
        if hasattr(self, 'reserve_label'):
            self.reserve_label.setText(t('reserve_prefix'))
        if hasattr(self, 'reserve_lock'):
            self.reserve_lock.setText(t('reserve_lock'))
        if hasattr(self, 'pause'):
            self.pause.setText(t('resume_refresh') if (hasattr(self, 'scanner') and self.scanner.paused) else t('pause_refresh'))
        if hasattr(self, 'reconnect_button'):
            self.reconnect_button.setText(t('reconnect'))
        if hasattr(self, 'details_label'):
            self.details_label.setText(t('select_group_details'))
        if hasattr(self, 'target'):
            self.target.setText(t('click_to_track'))
        if hasattr(self, 'details'):
            self.details.setHorizontalHeaderLabels(t('details_headers'))
        if hasattr(self, 'details_trial'):
            self.details_trial.setText(t('details_trial_label'))
        if hasattr(self, 'trophy_highlight'):
            self.trophy_highlight.setText(t('trophy_highlight_label'))
        if hasattr(self, 'btn_show_overlay'):
            self.btn_show_overlay.setText(t('btn_toggle_overlay'))
        if hasattr(self, 'btn_edit_overlay'):
            self.btn_edit_overlay.setText(t('btn_edit_overlay'))
        if hasattr(self, 'overlay_hint'):
            self.overlay_hint.setText(t('overlay_hint_text'))
        self.radar.update()
        if self.overlay:
            self.overlay.retranslate_ui()

    def check_stale(self):
        if self.current and time.time()-self.current.timestamp > max(3,self.scanner.interval*2.5):
            self.clear_data('数据已过期，等待下一次有效采样')

    def end_session(self):
        self.session_timer.stop()
        self.session_ended = True
        self.scanner.stop()
        self.scanner.wait(3000)
        self.current = None
        self.clear_data('本轮只读现场测试已结束，无实时标记；可关闭窗口')
        self.state.setText('本轮读取结束；等待线程释放句柄' if self.scanner.isRunning()
                           else '本轮读取结束；扫描停止，句柄已释放')
        self.pause.setEnabled(False)
        self.reconnect_button.setEnabled(False)

    def closeEvent(self,event):
        self.closing = True
        self.session_timer.stop()
        self.watchdog.stop()
        self.scanner.stop()
        # 不强杀仍持有进程句柄的线程，等待只读调用完成并由 finally 释放。
        if self.scanner.wait(3000):
            if self.overlay:
                self.overlay.shutdown()
            event.accept()
        else:
            self.state.setText('正在等待扫描线程退出，请稍候关闭')
            event.ignore()

    def scanner_finished(self):
        if self.closing:
            self.close()
        elif not self.session_ended:
            self.current = None
            self.state.setText('后台扫描已停止，请关闭窗口后重新打开；查看诊断日志')
            self.clear_data('扫描已停止，无实时数据')
            self.pause.setEnabled(False)
            self.reconnect_button.setEnabled(False)
