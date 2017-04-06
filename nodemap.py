#!/usr/bin/python3
"""
NodeMap application.

"""
import itertools
import random
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QBrush, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QDesktopWidget, QMainWindow, QAction, qApp,
    QDialog, QToolTip, QPushButton, QMessageBox, QLabel,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QLineEdit, QTextEdit, QInputDialog
)

APPLICATION_NAME = 'NodeMap'
VERSION = 'v0.0.0'
AUTHOR = 'Artem Panov'

app = None


class MainApp(QApplication):

    icon_logo = None
    confirm_exit = False    # may set to `True` or make it a property
    
    # For drag'n'drop operations.
    NODE_MIMETYPE = 'application/x-qt-windows-mime;value="NodeWidget"'

    # Maps node IDs to node data dictionary.
    nodes = {
        1: {'x': 100, 'y': 100, 'text': 'Node 1'},
        2: {'x': 200, 'y': 200, 'text': 'Node 2'},
        3: {'x': 300, 'y': 300, 'text': 'Node 3'},
        4: {'x': 400, 'y': 200, 'text': 'Node 4'},
    }

    edges = {
        1: set([4]),
        2: set([1, 3]),
        3: set([2]),
        4: set([1]),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon_logo = QIcon('pixmaps/icon_32x32.xpm')


class AboutWindow(QDialog):
    """ Typical 'About' modal dialog. Nothing special. """
    
    table_data = (
        ('Author', AUTHOR),
        ('Version', VERSION),
    )

    def __init__(self, *args, **kwargs):      
        super().__init__(*args, **kwargs)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('About')
        self.setWindowIcon(app.icon_logo)

        # Render table with values
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setVerticalSpacing(4)
        row = 1

        label = QLabel()    # TODO: self - to use or not to use?
        label.setPixmap(QPixmap('pixmaps/icon_32x32.xpm'))

        grid.addWidget(label, row, 0)
        grid.addWidget(QLabel('<b>%s</b>' % APPLICATION_NAME), row, 1)

        row += 1

        # Draw the table.
        for k,v in self.table_data:
            textbox = QLineEdit()
            textbox.setText(v)
            textbox.setReadOnly(True)
            grid.addWidget(QLabel(k), row, 0)
            grid.addWidget(textbox, row, 1)
            row += 1
        
        self.setLayout(grid)
        self.show()

        # This window can't be resized.
        self.setFixedSize(self.size())


class NodeWidget(QtWidgets.QWidget):
    """
    Custom widget that renders graph nodes as circles, provides context menu
    and edit/remove actions, implements drag'n'drop, highlights selected nodes.
    (note: overlayed node captions are rendered separately by the parent window)

    """
    color = None
    color_dimmed = None

    node_id = None

    # Generate color choices: primary (RGB), secondary (CMY) and white.
    RGB_COLORS = tuple(filter(any, itertools.product((0, 255), repeat=3)))

    def __init__(self, *args, **kwargs):      
        self.node_id = kwargs.pop('node_id')
        node_data = kwargs.pop('node_data')
        super().__init__(*args, **kwargs)

        # Choose random color for drawing the node
        rgb = random.choice(self.RGB_COLORS)
        self.color = QColor(*rgb)
        # Dimmed color is used to mark selected nodes.
        self.color_dimmed = QColor(*[x // 2 for x in rgb])
        
        self.initUI()
        
    def initUI(self):
        self.resize(32, 32)
        self.setMinimumSize(32, 32)
        
        data = app.nodes[self.node_id]
        self.move(data['x'], data['y'])

        # Context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu);
        self.customContextMenuRequested[QtCore.QPoint].connect(self.contextMenuRequested)
        self.show()

    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
      
    def drawWidget(self, qp):
        """
        Draw the node as circle (styling depends on node's selection status).

        """
        # Prepare brush.
        brush = QtGui.QBrush()
        brush.setStyle(Qt.SolidPattern)
        if self.is_selected():
            # Fill selected circle with dimmed color
            brush.setColor(self.color_dimmed)
        else:
            brush.setColor(self.parentWidget().BACKGROUND_COLOR)
        qp.setBrush(brush)

        # Prepare pen.
        pen = QtGui.QPen()
        pen.setColor(self.color)
        pen.setWidth(2);
        qp.setPen(pen)

        size = self.size()
        w = size.width()
        h = size.height()
        center = QPoint(w // 2, h // 2)
        radius = min(w, h) // 2 - 2
        
        qp.drawEllipse(center, radius, radius)

    def mouseMoveEvent(self, e):
        """
        We are setting custom mimetype for draggable nodes here to distinguish
        them from any other junk user may try to drop into the main window.
        Otherwise the app is likely to crash on reckless mouse movements.

        """
        if e.buttons() != Qt.LeftButton:
            return

        mimeData = QtCore.QMimeData()
        mimeData.setData(
            app.NODE_MIMETYPE,
            QtCore.QByteArray(bytes('data string', 'utf-8')),
        )

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setHotSpot(e.pos() - self.rect().topLeft())
        
        dropAction = drag.exec_(Qt.MoveAction)

    def mousePressEvent(self, e):
        """
        Mark the node as selected on mouse click (and deselect any other
        selected nodes).

        """
        super().mousePressEvent(e)
        if e.button() in (Qt.LeftButton, Qt.RightButton):

            modifiers = app.keyboardModifiers()
            if modifiers != QtCore.Qt.ControlModifier:
                self.parentWidget().clear_selection()

            self.parentWidget().add_to_selection(self.node_id)
            self.repaint()
        e.accept()

    def is_selected(self):
        return self.node_id in self.parentWidget().selected_nodes
    
    def contextMenuRequested(self, point):
        """
        Context menu triggered when user right-clicks on the node.

        """
        menu = QtWidgets.QMenu()
        action_rename = menu.addAction('Rename...')
        action_rename.triggered.connect(self.rename)
        action_delete = menu.addAction('Delete')
        action_delete.triggered.connect(self.delete)
        menu.exec_(self.mapToGlobal(point))

    def rename(self, event):
        node_data = app.nodes[self.node_id]
        text, ok = QInputDialog.getText(
            self, 'Rename',
            'Enter new name for node (#%s):' % self.node_id,
            text=node_data['text']
        )
        if ok:
            app.nodes[self.node_id]['text'] = text
        self.parentWidget().repaint()
        
    def delete(self, event):
        node_data = app.nodes[self.node_id]
        reply = QMessageBox.question(self,
            'Confirmation',
            'Are you sure you want to delete node "{}" (id={})?'.format(
                node_data['text'], self.node_id
            ),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # TODO: find more safe and clean way to delete
            del app.nodes[self.node_id]
            del app.edges[self.node_id]
            del self.parentWidget().nodes[self.node_id]
            self.close()
            self.destroy()

        self.parentWidget().repaint()


class MainWindow(QMainWindow):
    """
    Main application window. Serves as parent window to all graph node widgets.
    Provides context menu to create new nodes on the right-click in the empty
    space. Renders overlay captions below the nodes.
    Can be used as target for drag'n'drop (node movements).
    Handles main menu, status bar, toolbar and other generic stuff.

    """
    NODE_LABEL_MAX_WIDTH = 200      # max pixels
    NODE_LABEL_MAX_LENGTH = 32      # max characters (otherwise truncated)
    BACKGROUND_COLOR = QColor(8, 8, 8)

    actions = {}
    selected_nodes = set()

    nodes = {}      # maps node IDs to actual widget instances
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() in (Qt.LeftButton, Qt.RightButton):
            self.clear_selection()
            self.repaint()

    def clear_selection(self):
        self.selected_nodes.clear()
        self.statusBar().showMessage('')

    def add_to_selection(self, node_id):
        self.selected_nodes.add(node_id)
        self.statusBar().showMessage(
            'Selected node: #{}.'.format(node_id)
        )
        self.repaint()

    def center(self):
        """ Center window on the screen. """
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def about(self):
        """ Show 'About' dialog. """
        dialog = AboutWindow(self).exec()

    def confirm_exit(self):
        if not app.confirm_exit:
            return True
        reply = QMessageBox.question(self,
            'Confirm application close', 'Are you sure you want to quit?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def closeEvent(self, event):
        """ Exit (with confirmation dialog). """
        if self.confirm_exit():
            event.accept()
        else:
            event.ignore()
        
    def initUI(self):

        # Window title
        self.setWindowTitle('{} {}'.format(APPLICATION_NAME, VERSION))
        self.setWindowIcon(app.icon_logo)
        
        # Set a font used to render all tooltips.
        QToolTip.setFont(QFont('SansSerif', 10))

        # Window size and position
        self.resize(640, 480)
        self.center()

        # Background color
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Background, self.BACKGROUND_COLOR)
        self.setPalette(palette)

        # Actions
        action_icon = QIcon.fromTheme('application-exit')
        action = QAction(action_icon, '&Exit', self)
        action.setShortcut('Ctrl+Q')
        action.setStatusTip('Exit application.')
        action.triggered.connect(self.close)
        self.actions['exit'] = action

        action_icon = QIcon.fromTheme('list-add')
        action = QAction(action_icon, '&Connect nodes', self)
        action.triggered.connect(self.connect_nodes)
        action.setShortcut('Ctrl+J')
        action.setStatusTip('Connect selected nodes.')
        self.actions['connect_nodes'] = action
        
        action_icon = QIcon.fromTheme('list-remove')
        action = QAction(action_icon, '&Disconnect nodes', self)
        action.triggered.connect(self.disconnect_nodes)
        action.setShortcut('Ctrl+D')
        action.setStatusTip('Disconnect selected nodes.')
        self.actions['disconnect_nodes'] = action
        
        action = QAction(app.icon_logo, '&About %s...' % APPLICATION_NAME, self)
        action.triggered.connect(self.about)
        self.actions['about'] = action

        # Menu
        menubar = self.menuBar()
        menu = menubar.addMenu('&File')
        menu.addAction(self.actions['exit'])
        menu = menubar.addMenu('&Edit')
        menu.addAction(self.actions['connect_nodes'])
        menu.addAction(self.actions['disconnect_nodes'])
        menu = menubar.addMenu('&About')
        menu.addAction(self.actions['about'])

        # Toolbar
        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.addAction(self.actions['connect_nodes'])
        self.toolbar.addAction(self.actions['disconnect_nodes'])
        
        # Status bar
        bar = QtWidgets.QStatusBar()
        bar.setStyleSheet(
            "background-color: rgb(224, 224, 224);"
            "color: rgb(0, 0, 0);"
        )
        self.setStatusBar(bar)
        self.statusBar().showMessage('Ready.')

        # Context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu);
        self.customContextMenuRequested[QtCore.QPoint].connect(self.contextMenuRequested)

        # Drag and drop
        self.setAcceptDrops(True)

        # Initialize nodes
        for node_id, node_data in app.nodes.items():
            widget = NodeWidget(self, node_id=node_id, node_data=node_data) 
            self.nodes[node_id] = widget
        self.show()

    def dragEnterEvent(self, e):
        """
        If we ignore wrong content types here we will have troubles with them
        in `dropEvent` handler. So be it by now (some arcane wizardry here).

        """
        # TODO: Do it properly.
        # TODO: Redraw widget while dragging.
        e.accept()

    def dropEvent(self, e):
        # Ignore objects with unsupported content-type.
        data = e.mimeData().data(app.NODE_MIMETYPE).data().decode('utf-8')
        if not data:
            e.ignore()
            return  

        # Show new coordinates in status bar.
        self.statusBar().showMessage('Moved node {} to ({}, {}).'.format(
            e.source().node_id, e.pos().x(), e.pos().y()
        ))

        # Actually move the node.
        e.source().move(e.pos())
        e.setDropAction(Qt.MoveAction)
        self.repaint()
        e.accept()

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        self.draw_edges(event, qp)
        self.draw_node_labels(event, qp)
        qp.end()

    def draw_edges(self, event, qp):
        pen = QtGui.QPen(Qt.gray, 2, Qt.SolidLine)

        qp.setPen(pen)

        for src_id, trg_ids in app.edges.items():
            src_rect = self.nodes[src_id].geometry()
            src_x = src_rect.x() + src_rect.width() // 2
            src_y = src_rect.y() + src_rect.height() // 2

            for trg_id in trg_ids:
                trg_rect = self.nodes[trg_id].geometry()
                trg_x = trg_rect.x() + trg_rect.width() // 2
                trg_y = trg_rect.y() + trg_rect.height() // 2

                qp.drawLine(src_x, src_y, trg_x, trg_y)
        
    def draw_node_labels(self, event, qp):
        '''
        Draw overlay on parent window with all node labels
        (text labels are rendered separately from node widgets themselves).

        '''
        font = qp.font()
        font.setPointSize(10)

        for node_id, node_widget in self.nodes.items():

            # Selected nodes' labels are rendered bold. Choosing the font here.
            if node_widget.is_selected():
                font.setBold(True)
                qp.setPen(Qt.white)
            else:
                font.setBold(False)
                qp.setPen(Qt.gray)
            qp.setFont(font)
            
            # Limit max label size (truncate and append "..." if necessary)
            label_text = app.nodes[node_id]['text']
            if len(label_text) > self.NODE_LABEL_MAX_LENGTH-3:
                label_text = "%s..." % label_text[:self.NODE_LABEL_MAX_LENGTH-4]

            # Determine actual text width via "font metrics".
            # Limit max widget width accordingly.
            metrics = qp.fontMetrics()
            label_width = metrics.width(label_text)
            widget_width = min(label_width, self.NODE_LABEL_MAX_WIDTH)

            # Place the label below the node widget, symmetrically.
            node_rect = node_widget.geometry()
            x = node_rect.x()
            y = node_rect.y()
            rect = QtCore.QRect(
                node_rect.x() + (node_rect.width() - widget_width) // 2,
                node_rect.bottom() + 4,
                widget_width, 16
            )

            # If label is truncated then it should be aligned left, not center
            # (otherwise we will only see the middle part of the label).
            if label_width < widget_width:
                alignment = Qt.AlignCenter
            else:
                alignment = Qt.AlignLeft

            # Render
            qp.drawText(rect, alignment, label_text)
    
    def contextMenuRequested(self, point):
        """
        Context menu triggered when user right-clicks somewhere in the empty
        space of the main window.

        """
        menu = QtWidgets.QMenu()
        action1 = menu.addAction('Add node...')
        action1.triggered.connect(lambda: self.add_node(point))
        menu.exec_(self.mapToGlobal(point))

    def add_node(self, point):

        # Poor man's autoincrement.
        node_id = max(app.nodes.keys() or [0]) + 1 

        app.nodes[node_id] = {
            'text': 'Node %s' % node_id,
            'x': point.x(),
            'y': point.y(),
        }
        app.edges[node_id] = set()
        widget = NodeWidget(self, node_id=node_id, node_data=app.nodes[node_id]) 
        self.nodes[node_id] = widget

        self.repaint()

    def connect_nodes(self):
        """ Connect all selected nodes. """
        for src_id, trg_id in itertools.product(self.selected_nodes, repeat=2):
            app.edges[src_id].add(trg_id)
        self.repaint()

    def disconnect_nodes(self):
        """ Disconnect all selected nodes. """
        for src_id, trg_id in itertools.product(self.selected_nodes, repeat=2):
            app.edges[src_id].remove(trg_id)
        self.repaint()


if __name__ == '__main__':
    app = MainApp(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
