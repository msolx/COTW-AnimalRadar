import math
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QWidget, QToolTip
from services.coordinate import radar_point
from services.species import chinese
from services.heading import screen_direction
from services.animal_details import STATE_LABELS,animal_tooltip
from services.trophy import region_quality,COLORS,LABELS
import config

class RadarWidget(QWidget):
    selected = Signal(object)

    def __init__(self,compact=False):
        super().__init__()
        self.compact = compact
        self.setMinimumSize(200,200) if compact else self.setMinimumSize(540,540)
        self.setMouseTracking(True)
        self.regions, self.player, self.hits = [],None,[]
        self.radius = 400
        self.target = None
        self.north_up = False
        self.highlight_trophies = config.TROPHY_HIGHLIGHT_ENABLED

    def set_data(self,player,regions):
        self.player, self.regions = player,regions
        if self.target not in [r.key for r in regions]:
            self.target = None
        self.update()

    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.compact:
            p.fillRect(self.rect(),QColor('#101e24'))
        # 圆周外预留四向文字空间，避免与比例尺和底部说明重叠。
        center = QPointF(self.width()/2,self.height()/2+6)
        pixels = min(self.width(),self.height())/2-(35 if self.compact else 80)
        p.setPen(QPen(QColor('#385158'),1))
        for fraction in (.25,.5,.75,1):
            p.drawEllipse(center,pixels*fraction,pixels*fraction)
            p.drawText(QPointF(center.x()+5,center.y()-pixels*fraction),f'{self.radius*fraction:g}m')
        p.drawLine(QPointF(center.x()-pixels,center.y()),QPointF(center.x()+pixels,center.y()))
        from services.i18n import get_lang
        is_zh = get_lang() == 'zh'
        p.drawLine(QPointF(center.x(),center.y()-pixels),QPointF(center.x(),center.y()+pixels))
        p.setPen(QColor('#b5cacc'))
        legend = (('现场方向初测 · 上 -Z（北）/ 右 +X（东）' if is_zh else 'Live Cardinal Heading · Up -Z (North) / Right +X (East)') if self.north_up
                  else ('世界坐标雷达 · 上 +Z / 右 +X · 非玩家朝向' if is_zh else 'World Coord Radar · Up +Z / Right +X · Non-Player Relative'))
        if not self.compact:
            p.drawText(14,24,legend)
            p.drawText(14,self.height()-31,'橙伤 · 灰叉尸体 · 黄金/白银框 · 💎亮蓝菱形：潜在钻石' if is_zh else 'Orange=Injured · Gray X=Dead · 💎 Cyan=Diamond candidate')
            p.drawText(14,self.height()-12,'50米区域 · 中心箭头：视角朝向' if is_zh else '50m Clusters · Center arrow: Camera heading')
        # 只有已确认的初测北向模式才画地理方位；其它保护区不猜测轴向。
        if self.north_up:
            labels = ('北','东','南','西') if is_zh else ('N','E','S','W')
        else:
            labels = ('+Z','+X','−Z','−X')
        boxes = (
            QRectF(center.x()-24,center.y()-pixels-36,48,30),
            QRectF(center.x()+pixels+8,center.y()-15,48,30),
            QRectF(center.x()-24,center.y()+pixels+6,48,30),
            QRectF(center.x()-pixels-56,center.y()-15,48,30),
        )
        if self.compact:
            boxes = (QRectF(center.x()-18,center.y()-pixels-28,36,24),
                     QRectF(center.x()+pixels,center.y()-12,34,24),
                     QRectF(center.x()-18,center.y()+pixels,36,24),
                     QRectF(center.x()-pixels-34,center.y()-12,34,24))
        p.save()
        font = p.font()
        font.setPointSize((11 if self.north_up else 9) if self.compact else (17 if self.north_up else 12))
        font.setBold(True)
        p.setFont(font)
        for label,box in zip(labels,boxes):
            pill = box.adjusted(4, 2, -4, -2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(16, 30, 36, 190))
            p.drawRoundedRect(pill, 4, 4)
            if self.north_up:
                p.setPen(QColor('#f3c46e') if label == '北' else QColor('#a3d3dc'))
            else:
                p.setPen(QColor('#b5cacc'))
            p.drawText(box,Qt.AlignmentFlag.AlignCenter,label)
        p.restore()
        self.hits = []
        if not self.player:
            p.setPen(QPen(QColor('#385158'),1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(center,5,5)
            p.drawText(14,24,'无有效实时数据')
            return
        colors = {'blacktail deer':'#e7b565','whitetail deer':'#76c6df','moose':'#bb9ee8'}
        for region in self.regions:
            dx,dy = radar_point(region.position,self.player.position,self.radius,pixels)
            if self.north_up:
                dy = -dy
            if math.hypot(dx,dy) > pixels:
                continue
            point = center+QPointF(dx,dy)
            quality_count,quality = region_quality(region) if self.highlight_trophies else (0,None)
            if quality_count:
                # 仍在50米区域中心绘制，不因评级将标记偏移到另一个方向。
                if quality == 'diamond':
                    # 钻石：外层高亮菱形宝石，配合内层高光刻面与十字光芒
                    top = point + QPointF(0, -22)
                    right = point + QPointF(22, 0)
                    bottom = point + QPointF(0, 22)
                    left = point + QPointF(-22, 0)
                    fill = QColor('#00f0ff')
                    fill.setAlpha(85)
                    p.setPen(QPen(QColor('#00f0ff'), 3.2))
                    p.setBrush(fill)
                    p.drawPolygon(QPolygonF([top, right, bottom, left]))
                    # 内层微缩菱形晶格
                    inner_top = point + QPointF(0, -11)
                    inner_right = point + QPointF(11, 0)
                    inner_bottom = point + QPointF(0, 11)
                    inner_left = point + QPointF(-11, 0)
                    p.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawPolygon(QPolygonF([inner_top, inner_right, inner_bottom, inner_left]))
                    p.setPen(QPen(QColor(255, 255, 255, 140), 1))
                    p.drawLine(point + QPointF(0, -21), point + QPointF(0, 21))
                    p.drawLine(point + QPointF(-21, 0), point + QPointF(21, 0))
                elif quality == 'great_one':
                    edge = QColor(COLORS[quality])
                    fill = QColor(edge)
                    fill.setAlpha(90)
                    p.setPen(QPen(edge, 3.5))
                    p.setBrush(fill)
                    p.drawRoundedRect(QRectF(point.x()-19, point.y()-19, 38, 38), 8, 8)
                elif quality == 'gold':
                    edge = QColor(COLORS[quality])
                    fill = QColor(edge)
                    fill.setAlpha(70)
                    p.setPen(QPen(edge, 2.5))
                    p.setBrush(fill)
                    p.drawRoundedRect(QRectF(point.x()-17, point.y()-17, 34, 34), 6, 6)
                else:  # silver
                    edge = QColor(COLORS[quality])
                    fill = QColor(edge)
                    fill.setAlpha(50)
                    p.setPen(QPen(edge, 2))
                    p.setBrush(fill)
                    p.drawRoundedRect(QRectF(point.x()-16, point.y()-16, 32, 32), 4, 4)
            # 标记锚点严格位于网格中心，不能按固定屏幕像素错开生命状态。
            # 400米小雷达中十几个像素可对应数十米，会造成额外的距离/方向误导。
            # 同格状态仍分别聚合、用形状/颜色区分，可从右侧列表选中各组。
            color = QColor(colors.get(region.species,'#8bcc91'))
            if region.vital_status == 'dead': color = QColor('#a8b3b8')
            elif region.vital_status == 'wounded': color = QColor('#f39b42')
            p.setPen(QPen(QColor('#ffffff') if self.target == region.key else color,2))
            p.setBrush(color)
            # 不同物种使用不同形状，色觉差异时仍可分辨。
            if region.vital_status == 'dead':
                p.drawLine(point+QPointF(-8,-8),point+QPointF(8,8))
                p.drawLine(point+QPointF(-8,8),point+QPointF(8,-8))
            elif region.species == 'blacktail deer':
                p.drawEllipse(point,9,9)
            elif region.species == 'whitetail deer':
                p.drawRect(int(point.x()-8),int(point.y()-8),16,16)
            else:
                p.drawRoundedRect(int(point.x()-11),int(point.y()-6),22,12,4,4)

            badge = ''
            if quality_count:
                if quality == 'diamond':
                    badge = f' 💎{quality_count}'
                elif quality == 'great_one':
                    badge = f' 👑{quality_count}'
                else:
                    badge = f' ★{quality_count}'
            p.setPen(QColor('#00f0ff') if quality == 'diamond' else QColor('#ffffff'))
            p.drawText(point+QPointF(20 if quality == 'diamond' else (18 if quality_count else 12),4),
                       str(region.count)+('?' if region.vital_status == 'unknown' else '')+badge)
            self.hits.append((point,region))
        # 中心最后绘制，防止附近区域标记盖住位置及朝向指针。
        p.setPen(QPen(QColor('#ffffff'),1))
        p.setBrush(QColor('#ffffff'))
        p.drawEllipse(center,5,5)
        direction = (screen_direction(self.player.view_direction,self.north_up)
                     if self.player.view_status == 'valid' else None)
        if direction:
            dx,dy = direction
            forward,side = QPointF(dx,dy),QPointF(-dy,dx)
            arrow = QPolygonF([center+forward*25,center-forward*8+side*8,
                               center-forward*3,center-forward*8-side*8])
            p.setPen(QPen(QColor('#e1fcff'),1.5))
            p.setBrush(QColor('#53d7ed'))
            p.drawPolygon(arrow)
        else:
            text = {'vertical':'视角接近垂直，朝向箭头隐藏',
                    'invalid':'朝向数据异常，已停用；重连后重新验证'}.get(
                        self.player.view_status,'视角朝向尚未验证')
            p.setPen(QColor('#b5cacc'))
            if not self.compact:
                p.drawText(14,44,text)

    def mouseMoveEvent(self,event):
        for point,region in sorted(self.hits,key=lambda hit:(hit[0]-event.position()).manhattanLength()):
            if (point-event.position()).manhattanLength() < 22:
                q_count,quality = region_quality(region) if self.highlight_trophies else (0,None)
                q_text = ''
                if q_count:
                    if quality == 'diamond':
                        q_text = f'💎 潜在钻石：{q_count}只（预测）\n'
                    elif quality == 'great_one':
                        q_text = f'👑 潜在珍奇：{q_count}只（预测）\n'
                    elif quality == 'gold':
                        q_text = f'★ 潜在黄金：{q_count}只（预测）\n'
                    else:
                        q_text = f'★ 潜在白银+：{q_count}只（预测）\n'
                QToolTip.showText(event.globalPosition().toPoint(),
                    f'{chinese(region.species)} · {STATE_LABELS.get(region.vital_status,"未知")} · {region.count}只\n约{region.distance_min:g}～{region.distance_max:g}米\n'
                    +q_text
                    +'\n'.join(animal_tooltip(a) for a in region.members[:3])
                    + ('\n更多个体请点击区域查看' if len(region.members)>3 else ''),self)
                return
        QToolTip.hideText()

    def mousePressEvent(self,event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        for point,region in sorted(self.hits,key=lambda hit:(hit[0]-event.position()).manhattanLength()):
            if (point-event.position()).manhattanLength() < 22:
                self.target = region.key
                self.selected.emit(region)
                self.update()
                return
