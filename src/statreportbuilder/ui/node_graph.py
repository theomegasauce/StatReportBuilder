from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)

from src.statreportbuilder.core.blocks import Block
from src.statreportbuilder.core.graph import Graph
from src.statreportbuilder.ui.block_region import BLOCK_MIME_TYPE


BLOCK_WIDTH = 180
BLOCK_HEIGHT = 88
PORT_RADIUS = 6
PORT_HIT_RADIUS = 10


class BlockItem(QGraphicsItem):
    def __init__(self, block: Block) -> None:
        super().__init__()
        self.block = block
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._edges: list[EdgeItem] = []

    def boundingRect(self) -> QRectF:
        return QRectF(-PORT_RADIUS, 0, BLOCK_WIDTH + 2 * PORT_RADIUS, BLOCK_HEIGHT)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, BLOCK_WIDTH, BLOCK_HEIGHT)

        if self.isSelected():
            painter.setPen(QPen(QColor("#0066cc"), 2))
        else:
            painter.setPen(QPen(QColor("#888"), 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(rect, 8, 8)

        header_rect = QRectF(0, 0, BLOCK_WIDTH, 26)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#eef2f7")))
        path = QPainterPath()
        path.addRoundedRect(header_rect, 8, 8)
        painter.drawPath(path)
        painter.fillRect(QRectF(0, 18, BLOCK_WIDTH, 8), QColor("#eef2f7"))

        painter.setPen(QColor("#222"))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(10, 4, BLOCK_WIDTH - 20, 20), Qt.AlignVCenter, self.block.title)

        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#666"))
        painter.drawText(
            QRectF(10, 32, BLOCK_WIDTH - 20, 50),
            Qt.AlignTop | Qt.AlignLeft,
            self._summary(),
        )

        for i, _ in enumerate(self.block.inputs):
            pos = self.input_port_pos(i)
            painter.setPen(QPen(QColor("#3a6db1"), 1))
            painter.setBrush(QBrush(QColor("#4a90e2")))
            painter.drawEllipse(pos, PORT_RADIUS, PORT_RADIUS)

        for i, _ in enumerate(self.block.outputs):
            pos = self.output_port_pos(i)
            painter.setPen(QPen(QColor("#a06a30"), 1))
            painter.setBrush(QBrush(QColor("#e2904a")))
            painter.drawEllipse(pos, PORT_RADIUS, PORT_RADIUS)

    def _summary(self) -> str:
        parts: list[str] = []
        for spec in self.block.params_spec:
            value = self.block.params.get(spec.name)
            if value in (None, "", False):
                continue
            text = str(value)
            if len(text) > 22:
                text = text[:19] + "…"
            parts.append(f"{spec.label}: {text}")
            if len(parts) >= 2:
                break
        return "\n".join(parts) if parts else "(unconfigured)"

    def input_port_pos(self, index: int) -> QPointF:
        count = max(len(self.block.inputs), 1)
        spacing = (BLOCK_HEIGHT - 30) / (count + 1)
        return QPointF(0, 30 + spacing * (index + 1))

    def output_port_pos(self, index: int) -> QPointF:
        count = max(len(self.block.outputs), 1)
        spacing = (BLOCK_HEIGHT - 30) / (count + 1)
        return QPointF(BLOCK_WIDTH, 30 + spacing * (index + 1))

    def input_port_scene_pos(self, index: int) -> QPointF:
        return self.mapToScene(self.input_port_pos(index))

    def output_port_scene_pos(self, index: int) -> QPointF:
        return self.mapToScene(self.output_port_pos(index))

    def hit_test_output_port(self, local_pos: QPointF) -> int | None:
        for i in range(len(self.block.outputs)):
            if (local_pos - self.output_port_pos(i)).manhattanLength() <= PORT_HIT_RADIUS:
                return i
        return None

    def hit_test_input_port(self, local_pos: QPointF) -> int | None:
        for i in range(len(self.block.inputs)):
            if (local_pos - self.input_port_pos(i)).manhattanLength() <= PORT_HIT_RADIUS:
                return i
        return None

    def register_edge(self, edge: "EdgeItem") -> None:
        self._edges.append(edge)

    def unregister_edge(self, edge: "EdgeItem") -> None:
        if edge in self._edges:
            self._edges.remove(edge)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            port_idx = self.hit_test_output_port(event.pos())
            if port_idx is not None:
                canvas = self._canvas()
                if canvas is not None:
                    canvas.begin_wire(self, port_idx)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def _canvas(self) -> "GraphCanvas | None":
        scene = self.scene()
        if scene is None:
            return None
        views = scene.views()
        if not views:
            return None
        view = views[0]
        return view if isinstance(view, GraphCanvas) else None

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_path()
        return super().itemChange(change, value)


class EdgeItem(QGraphicsPathItem):
    def __init__(
        self,
        src_block: BlockItem,
        src_port_index: int,
        dst_block: BlockItem,
        dst_port_index: int,
        src_port_name: str,
        dst_port_name: str,
    ) -> None:
        super().__init__()
        self.src = src_block
        self.dst = dst_block
        self.src_port = src_port_index
        self.dst_port = dst_port_index
        self.src_port_name = src_port_name
        self.dst_port_name = dst_port_name

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setPen(QPen(QColor("#666"), 2))
        self.setZValue(-1)
        src_block.register_edge(self)
        dst_block.register_edge(self)
        self.update_path()

    def shape(self):
        stroker_path = QPainterPath(self.path())
        return stroker_path

    def update_path(self) -> None:
        p1 = self.src.output_port_scene_pos(self.src_port)
        p2 = self.dst.input_port_scene_pos(self.dst_port)
        dx = max(abs(p2.x() - p1.x()) * 0.5, 60)
        c1 = QPointF(p1.x() + dx, p1.y())
        c2 = QPointF(p2.x() - dx, p2.y())
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        self.setPath(path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if value:
                self.setPen(QPen(QColor("#0066cc"), 3))
            else:
                self.setPen(QPen(QColor("#666"), 2))
        return super().itemChange(change, value)

    def detach(self) -> None:
        self.src.unregister_edge(self)
        self.dst.unregister_edge(self)


class GraphCanvas(QGraphicsView):
    selection_changed = Signal(object)
    block_dropped = Signal(str, QPointF)
    edge_requested = Signal(str, str, str, str)
    delete_requested = Signal(list, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self.setScene(self._scene)
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#f5f5f5"))
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._block_items: dict[str, BlockItem] = {}
        self._panning = False
        self._pan_start = QPointF()

        self._wire_src: tuple[BlockItem, int] | None = None
        self._wire_temp: QGraphicsPathItem | None = None

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
            event.accept()
            return
        if self._wire_src is not None and self._wire_temp is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._update_wire_temp(scene_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        if self._wire_src is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._finish_wire(scene_pos)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            node_ids: list[str] = []
            edge_keys: list[tuple[str, str, str, str]] = []
            for item in self._scene.selectedItems():
                if isinstance(item, BlockItem):
                    node_ids.append(item.block.node_id)
                elif isinstance(item, EdgeItem):
                    edge_keys.append(
                        (
                            item.src.block.node_id,
                            item.src_port_name,
                            item.dst.block.node_id,
                            item.dst_port_name,
                        )
                    )
            if node_ids or edge_keys:
                self.delete_requested.emit(node_ids, edge_keys)
                event.accept()
                return
        super().keyPressEvent(event)

    def begin_wire(self, src_block: BlockItem, src_port_idx: int) -> None:
        self._wire_src = (src_block, src_port_idx)
        self._wire_temp = QGraphicsPathItem()
        self._wire_temp.setPen(QPen(QColor("#0066cc"), 2, Qt.DashLine))
        self._wire_temp.setZValue(10)
        self._scene.addItem(self._wire_temp)
        self._update_wire_temp(src_block.output_port_scene_pos(src_port_idx))

    def _update_wire_temp(self, end_pos: QPointF) -> None:
        if self._wire_src is None or self._wire_temp is None:
            return
        src_block, src_port = self._wire_src
        p1 = src_block.output_port_scene_pos(src_port)
        dx = max(abs(end_pos.x() - p1.x()) * 0.5, 60)
        c1 = QPointF(p1.x() + dx, p1.y())
        c2 = QPointF(end_pos.x() - dx, end_pos.y())
        path = QPainterPath(p1)
        path.cubicTo(c1, c2, end_pos)
        self._wire_temp.setPath(path)

    def _finish_wire(self, scene_pos: QPointF) -> None:
        src_block, src_port = self._wire_src
        target = self._find_input_port_at(scene_pos, exclude=src_block)

        if self._wire_temp is not None:
            self._scene.removeItem(self._wire_temp)
            self._wire_temp = None
        self._wire_src = None

        if target is None:
            return
        dst_block, dst_port_idx = target
        self.edge_requested.emit(
            src_block.block.node_id,
            src_block.block.outputs[src_port].name,
            dst_block.block.node_id,
            dst_block.block.inputs[dst_port_idx].name,
        )

    def _find_input_port_at(
        self, scene_pos: QPointF, exclude: BlockItem
    ) -> tuple[BlockItem, int] | None:
        for item in self._scene.items(scene_pos):
            if not isinstance(item, BlockItem) or item is exclude:
                continue
            local = item.mapFromScene(scene_pos)
            idx = item.hit_test_input_port(local)
            if idx is not None:
                return item, idx
        for item in self._block_items.values():
            if item is exclude:
                continue
            local = item.mapFromScene(scene_pos)
            idx = item.hit_test_input_port(local)
            if idx is not None:
                return item, idx
        return None

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(BLOCK_MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(BLOCK_MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(BLOCK_MIME_TYPE):
            type_id = bytes(event.mimeData().data(BLOCK_MIME_TYPE)).decode("utf-8")
            scene_pos = self.mapToScene(event.position().toPoint())
            self.block_dropped.emit(type_id, scene_pos)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def viewport_center_in_scene(self) -> QPointF:
        return self.mapToScene(self.viewport().rect().center())

    def _on_selection_changed(self) -> None:
        items = [it for it in self._scene.selectedItems() if isinstance(it, BlockItem)]
        if items:
            self.selection_changed.emit(items[0].block.node_id)
        else:
            self.selection_changed.emit(None)

    def render_graph(self, graph: Graph) -> None:
        self._scene.clear()
        self._block_items = {}
        self._wire_src = None
        self._wire_temp = None

        if not graph.nodes:
            placeholder = self._scene.addText(
                "Empty graph — drag a block from the palette above\n"
                "or pick a preset to get started."
            )
            placeholder.setDefaultTextColor(QColor("#888"))
            placeholder.setPos(-180, -20)
            return

        for node_id, block in graph.nodes.items():
            item = BlockItem(block)
            x, y = graph.positions.get(node_id, (0.0, 0.0))
            item.setPos(x, y)
            self._scene.addItem(item)
            self._block_items[node_id] = item

        for edge in graph.edges:
            src_item = self._block_items.get(edge.src_node)
            dst_item = self._block_items.get(edge.dst_node)
            if src_item is None or dst_item is None:
                continue
            src_idx = _port_index(src_item.block.outputs, edge.src_port)
            dst_idx = _port_index(dst_item.block.inputs, edge.dst_port)
            if src_idx is None or dst_idx is None:
                continue
            edge_item = EdgeItem(
                src_item, src_idx, dst_item, dst_idx, edge.src_port, edge.dst_port
            )
            self._scene.addItem(edge_item)

    def collect_positions(self) -> dict[str, tuple[float, float]]:
        return {
            nid: (item.pos().x(), item.pos().y())
            for nid, item in self._block_items.items()
        }

    def select_node(self, node_id: str | None) -> None:
        for nid, item in self._block_items.items():
            item.setSelected(nid == node_id)

    def refresh_block(self, node_id: str) -> None:
        item = self._block_items.get(node_id)
        if item is not None:
            item.update()


def _port_index(ports, name: str) -> int | None:
    for i, p in enumerate(ports):
        if p.name == name:
            return i
    return None


class NodeGraphBuilder(QWidget):
    node_selected = Signal(object)
    block_dropped = Signal(str, QPointF)
    edge_requested = Signal(str, str, str, str)
    delete_requested = Signal(list, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._canvas = GraphCanvas(self)
        self._canvas.selection_changed.connect(self.node_selected)
        self._canvas.block_dropped.connect(self.block_dropped)
        self._canvas.edge_requested.connect(self.edge_requested)
        self._canvas.delete_requested.connect(self.delete_requested)
        layout.addWidget(self._canvas, stretch=1)

        self._graph: Graph | None = None

    def set_graph(self, graph: Graph | None) -> None:
        self._graph = graph
        if graph is None:
            scene = self._canvas.scene()
            scene.clear()
            placeholder = scene.addText(
                "Open or create a report file to start building."
            )
            placeholder.setDefaultTextColor(QColor("#888"))
            placeholder.setPos(-180, -10)
            return
        self._canvas.render_graph(graph)

    def graph(self) -> Graph | None:
        return self._graph

    def collect_positions(self) -> dict[str, tuple[float, float]]:
        return self._canvas.collect_positions()

    def refresh_block(self, node_id: str) -> None:
        self._canvas.refresh_block(node_id)

    def viewport_center_in_scene(self) -> QPointF:
        return self._canvas.viewport_center_in_scene()

    def select_node(self, node_id: str | None) -> None:
        self._canvas.select_node(node_id)
