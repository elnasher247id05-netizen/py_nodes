import sys
import json
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QMainWindow,
    QMenu,
    QGraphicsDropShadowEffect,
)

# Load theme configuration from theme.json
BASE_DIR = Path(__file__).resolve().parent
THEME_PATH = BASE_DIR / "theme.json"

try:
    with open(THEME_PATH, "r", encoding="utf-8") as f:
        THEME = json.load(f)
except Exception as e:
    print(f"Failed to load theme.json, using defaults: {e}")
    THEME = {}


class ConnectionEdge(QGraphicsPathItem):
    """Connection line between two notes with selection, styling, and deletion support."""

    def __init__(self, start_note, end_note):
        super().__init__()
        self.start_note = start_note
        self.end_note = end_note

        self.start_note.add_edge(self)
        self.end_note.add_edge(self)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )

        self.setZValue(-1)
        self.update_style()
        self.update_position()

    def update_style(self):
        """Update line color and thickness based on theme configuration and selection state."""
        edge_conf = THEME.get("edge", {})
        
        if self.isSelected():
            color = edge_conf.get("selected_color", "#0a84ff")
        else:
            color = edge_conf.get("color", "#444444")
            
        width = edge_conf.get("width", 2.0)

        pen = QPen(QColor(color), width, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def paint(self, painter, option, widget=None):
        self.update_style()
        super().paint(painter, option, widget)

    def update_position(self):
        """Recalculate path curve when connected notes move."""
        if not self.start_note or not self.end_note:
            return

        p1 = self.start_note.sceneBoundingRect().center()
        p2 = self.end_note.sceneBoundingRect().center()

        path = QPainterPath(p1)
        dx = (p2.x() - p1.x()) / 2
        ctrl1 = QPointF(p1.x() + dx, p1.y())
        ctrl2 = QPointF(p2.x() - dx, p2.y())
        
        path.cubicTo(ctrl1, ctrl2, p2)
        self.setPath(path)

    def keyPressEvent(self, event):
        """Delete connection on Delete or Backspace key."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.remove_self()
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """Context menu to disconnect/delete the edge."""
        menu = QMenu()
        disconnect_action = menu.addAction("✂ Disconnect")
        action = menu.exec_(event.screenPos())
        if action == disconnect_action:
            self.remove_self()

    def remove_self(self):
        """Safely remove edge from notes and scene."""
        if self.start_note:
            self.start_note.remove_edge(self)
        if self.end_note:
            self.end_note.remove_edge(self)
        if self.scene():
            self.scene().removeItem(self)


class StickyNote(QGraphicsRectItem):
    """Interactive sticky note supporting"""

    def __init__(self, x: float, y: float, title: str = "Title", body: str = "Description"):
        super().__init__(0, 0, 200, 140)
        self.setPos(x, y)

        self.edges = []

        # Загружаем конфиг темы
        note_conf = THEME.get("note", {})
        bg_color = note_conf.get("background", "#2d2d2d")
        border_color = note_conf.get("border", "#3d3d3d")
        border_width = note_conf.get("border_width", 1.0)
        self.border_radius = note_conf.get("border_radius", 12)
        
        # Обязательно считываем настройки шапки
        show_header = note_conf.get("show_header", False)
        header_height = note_conf.get("header_height", 28)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )

        self.setBrush(QBrush(QColor(bg_color)))
        self.setPen(QPen(QColor(border_color), border_width))

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        # Поле заголовка
        self.title_item = QGraphicsTextItem(title, self)
        title_font = QFont("SF Pro Display", 9)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_item.setFont(title_font)
        self.title_item.setTextWidth(172)
        self.title_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)

        # Поле описания
        self.body_item = QGraphicsTextItem(body, self)
        self.body_item.setFont(QFont("SF Pro Display", 9))
        self.body_item.setTextWidth(172)
        self.body_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)

        # Позиционирование с учетом шапки
        if show_header:
            self.title_item.setPos(10, 4)
            self.body_item.setPos(14, header_height + 8)
        else:
            self.title_item.setPos(14, 10)
            self.body_item.setPos(14, 35)
    

    def update_style(self):
        """Update Stick, when interactive with it"""
        note_conf = THEME.get("note", {})

        if self.isSelected():
            border_color = note_conf.get("selected_color", "#0a84ff" )
        else:
            border_color = note_conf.get("border", "#3d3d3d" )

        border_width = note_conf.get("border_width", 1.0)

        pen = QPen(QColor(border_color), border_width)
        self.setPen(pen)

    def draw_header(self, painter):
        """Draws a header for note"""
        note_conf = THEME.get("note")

        if not note_conf.get("show_header", False):
            return

        header_height = note_conf.get("header_height", 28)
        header_color = QColor(note_conf.get("header_color", "#3d3d3d"))

        rect = self.rect()

        painter.save()

        header_rect = rect.adjusted(0, 0, 0, -(rect.height() - header_height))
        painter.setBrush(QBrush(header_color))
        painter.setPen(Qt.PenStyle.NoPen)

        path = QPainterPath()
        path.addRoundedRect(rect, self.border_radius, self.border_radius)
        painter.setClipPath(path)

        painter.drawRect(header_rect)

        painter.restore()

    def paint(self, painter, option, widget=None):
        """Override paint to render smooth rounded rectangles."""
        self.update_style()

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()


        painter.setBrush(self.brush())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self.border_radius, self.border_radius)

        self.draw_header(painter)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(self.pen())
        painter.drawRoundedRect(rect, self.border_radius, self.border_radius)


    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

    def itemChange(self, change, value):
        """Update connected edge positions when note moves."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)

    def keyPressEvent(self, event):
        """Handle hotkeys: 'N' for connection mode, Delete/Backspace for removal."""
        if self.text_item.hasFocus():
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_N:
            view = self.scene().views()[0]
            view.start_connection_mode(self)
            event.accept()
            return

        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_note()
            event.accept()
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """Context menu for note actions."""
        menu = QMenu()
        connect_action = menu.addAction("🔗 Connect with... (N)")
        delete_action = menu.addAction("🗑 Delete Note")

        action = menu.exec_(event.screenPos())
        if action == delete_action:
            self.delete_note()
        elif action == connect_action:
            view = self.scene().views()[0]
            view.start_connection_mode(self)

    def delete_note(self):
        """Remove note and all its connected edges."""
        for edge in list(self.edges):
            edge.remove_self()
        if self.scene():
            self.scene().removeItem(self)


class InfiniteCanvasScene(QGraphicsScene):
    """Custom scene that renders an elegant dot grid background."""

    def drawBackground(self, painter, rect):
        canvas_conf = THEME.get("canvas", {})
        bg_color = canvas_conf.get("background", "#1e1e1e")
        grid_color = QColor(canvas_conf.get("grid_color", "#333333"))
        spacing = canvas_conf.get("grid_spacing", 32)
        dot_size = canvas_conf.get("dot_size", 2.0)

        # Fill background color
        painter.fillRect(rect, QColor(bg_color))

        # Draw dot grid
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grid_color))

        left = int(rect.left()) - (int(rect.left()) % spacing)
        top = int(rect.top()) - (int(rect.top()) % spacing)

        for x in range(left, int(rect.right()) + spacing, spacing):
            for y in range(top, int(rect.bottom()) + spacing, spacing):
                painter.drawEllipse(QPointF(x, y), dot_size / 2, dot_size / 2)


class InfiniteCanvasView(QGraphicsView):
    """Infinite canvas supporting zooming, panning, and node connections."""

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._connecting_source = None

    def start_connection_mode(self, source_note: StickyNote):
        """Activate crosshair cursor to pick target note for connection."""
        self._connecting_source = source_note
        self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event):
        """Zoom in/out centered on mouse position."""
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if self._connecting_source and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            target_note = None
            if isinstance(item, StickyNote):
                target_note = item
            elif item and isinstance(item.parentItem(), StickyNote):
                target_note = item.parentItem()

            if target_note and target_note != self._connecting_source:
                edge = ConnectionEdge(self._connecting_source, target_note)
                self.scene().addItem(edge)

            self._connecting_source = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._is_panning = True
            self._pan_start_x = event.x()
            self._pan_start_y = event.y()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta_x = event.x() - self._pan_start_x
            delta_y = event.y() - self._pan_start_y
            self._pan_start_x = event.x()
            self._pan_start_y = event.y()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta_x
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta_y
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            self._is_panning = False
            if not self._connecting_source:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            scene_pos = self.mapToScene(event.pos())
            note = StickyNote(scene_pos.x(), scene_pos.y())
            self.scene().addItem(note)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spatial Notes - macOS Style")
        self.resize(1000, 700)

        # Use custom scene with dot grid background
        self.scene = InfiniteCanvasScene(-50000, -50000, 100000, 100000)

        self.view = InfiniteCanvasView(self.scene)
        self.setCentralWidget(self.view)

        # Create initial test notes
        note1 = StickyNote(-160, -60, "Note 1\nPress N to connect")
        note2 = StickyNote(160, -60, "Note 2\nDot grid enabled")
        self.scene.addItem(note1)
        self.scene.addItem(note2)

        edge = ConnectionEdge(note1, note2)
        self.scene.addItem(edge)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())