# -*- coding: utf-8 -*-
"""Contains the popup-widget associated with the FilesWidget tab. It is responsible
for letting the user pick a folder to get files from.

Data keys are subfolders inside the root of the asset folder. They are usually are
associated with a task or data-type eg, ``render``, ``comp``, ``textures``.

To describe the function of each folder we can define the folder and a description
in the common module.

"""
import weakref
from functools import partial
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks._scandir as _scandir
import bookmarks.common as common

from bookmarks.delegate import paintmethod
from bookmarks.baselistwidget import BaseModel
from bookmarks.baselistwidget import initdata
from bookmarks.delegate import BaseDelegate
import bookmarks.images as images
from bookmarks.basecontextmenu import BaseContextMenu
import bookmarks.threads as threads


class DataKeyContextMenu(BaseContextMenu):
    """The context menu associated with the DataKeyView."""

    def __init__(self, index, parent=None):
        super(DataKeyContextMenu, self).__init__(index, parent=parent)
        self.add_reveal_item_menu()


class DataKeyViewDelegate(BaseDelegate):
    """The delegate used to paint the available subfolders inside the asset folder."""

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self.get_paint_arguments(painter, option, index)
        self.paint_background(*args)
        self.paint_name(*args)
        self.paint_selection_indicator(*args)

    def get_text_segments(self):
        return []

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(option.rect)
        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - common.ROW_SEPARATOR)
        rect.moveCenter(center)
        background = QtGui.QColor(common.BACKGROUND)
        background.setAlpha(150)
        color = common.BACKGROUND_SELECTED if selected or hover else background
        painter.setBrush(color)
        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints the name and the number of files available for the given data-key."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        if index.data(common.TodoCountRole):
            color = common.TEXT_SELECTED if hover else common.TEXT
        else:
            color = common.TEXT if hover else common.BACKGROUND_SELECTED
        color = common.TEXT_SELECTED if selected else color

        font = common.font_db.primary_font()
        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(rect.right() - common.MARGIN)

        text = index.data(QtCore.Qt.DisplayRole).upper()
        width = 0
        width = common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)

        items = []
        # Adding an indicator for the number of items in the folder
        if index.data(common.TodoCountRole):
            if index.data(common.TodoCountRole) >= 999:
                text = u'999+ items'
            else:
                text = u'{} items'.format(
                    index.data(common.TodoCountRole))
            color = common.TEXT_SELECTED if selected else common.FAVOURITE
            color = common.TEXT_SELECTED if hover else color
            items.append((text, color))
        else:
            color = common.TEXT if selected else common.BACKGROUND
            color = common.TEXT if hover else color
            items.append((u'n/a', color))

        if index.data(QtCore.Qt.ToolTipRole):
            color = common.TEXT_SELECTED if selected else common.SECONDARY_TEXT
            color = common.TEXT_SELECTED if hover else color
            items.append((index.data(QtCore.Qt.ToolTipRole), color))

        for idx, val in enumerate(items):
            text, color = val
            if idx == 0:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            else:
                align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight

            width = common.draw_aliased_text(
                painter, common.font_db.secondary_font(), rect, u'    |    ', align, common.SEPARATOR)
            rect.setLeft(rect.left() + width)

            width = common.draw_aliased_text(
                painter, common.font_db.secondary_font(), rect, text, align, color)
            rect.setLeft(rect.left() + width)

    def sizeHint(self, option, index):
        """Returns the size of the DataKeyViewDelegate items."""
        height = index.data(QtCore.Qt.SizeHintRole).height()
        return QtCore.QSize(1, height)


class DataKeyView(QtWidgets.QListView):
    """The view responsonsible for displaying the available data-keys."""
    ContextMenu = DataKeyContextMenu

    def __init__(self, parent=None, altparent=None):
        super(DataKeyView, self).__init__(parent=parent)
        self.altparent = altparent
        self._context_menu_active = False

        common.set_custom_stylesheet(self)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.clicked.connect(self.activated)
        self.clicked.connect(self.hide)

        if self.altparent:
            self.clicked.connect(self.altparent.signal_dispatcher)

        if self.parent():
            @QtCore.Slot(QtCore.QRect)
            def set_width(rect):
                """Resizes the view to the size of the"""
                rect = browser_widget.stackedwidget.widget(
                    2).viewport().geometry()
                rect.setLeft(0)
                rect.setTop(0)
                self.setGeometry(rect)

            browser_widget = self.parent().parent().parent()
            browser_widget.stackedwidget.widget(2).resized.connect(set_width)

        model = DataKeyModel()
        model.view = self
        self.setModel(model)
        self.setItemDelegate(DataKeyViewDelegate(parent=self))
        self.installEventFilter(self)

    def sizeHint(self):
        """The default size of the widget."""
        if self.parent():
            return QtCore.QSize(self.parent().width(), self.parent().height())
        else:
            return QtCore.QSize(460, 360)

    def inline_icons_count(self):
        return 0

    def hideEvent(self, event):
        """DataKeyView hide event."""
        if self.parent():
            self.parent().verticalScrollBar().setHidden(False)
            self.parent().removeEventFilter(self)
            self.altparent.files_button.update()

    def showEvent(self, event):
        """DataKeyView show event."""
        if self.parent():
            self.parent().verticalScrollBar().setHidden(True)
            self.parent().installEventFilter(self)

    def eventFilter(self, widget, event):
        """We're stopping events propagating back to the parent."""
        if widget == self.parent():
            return True
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.SEPARATOR)
            painter.setOpacity(0.75)
            painter.drawRect(self.rect())
            painter.end()
            return True
        return False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
        elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
            self.hide()
            return
        super(DataKeyView, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if self._context_menu_active:
            return
        if event.lostFocus():
            self.hide()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        width = self.viewport().geometry().width()

        widget = self.ContextMenu(index, parent=self)
        rect = self.visualRect(index)
        offset = self.visualRect(index).height() - common.INDICATOR_WIDTH
        widget.move(
            self.viewport().mapToGlobal(rect.bottomLeft()).x() + offset,
            self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
        )

        widget.setFixedWidth(width - offset)
        common.move_widget_to_available_geo(widget)

        self._context_menu_active = True
        widget.exec_()
        self._context_menu_active = False

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.hide()
            return
        super(DataKeyView, self).mousePressEvent(event)


class DataKeyModel(BaseModel):
    """This model holds all the necessary data needed to display items to
    select for selecting the asset subfolders and/or bookmarks and assets.

    The model keeps track of the selections internally and is updated
    via the signals and slots."""
    ROW_SIZE = QtCore.QSize(120, 30)

    def __init__(self, parent=None):
        self._parent = parent
        super(DataKeyModel, self).__init__(parent=parent)
        self.modelDataResetRequested.connect(self.__resetdata__)

    def initialise_threads(self):
        """Starts and connects the threads."""
        @QtCore.Slot(QtCore.QThread)
        def thread_started(thread):
            """Signals the model an item has been updated."""
            thread.worker.dataReady.connect(
                self.updateRow, QtCore.Qt.QueuedConnection)
            thread.startTimer.emit()

        info_worker = threads.DataKeyWorker()
        info_thread = threads.BaseThread(info_worker, interval=250)
        self.threads[common.InfoThread].append(info_thread)
        info_thread.started.connect(partial(thread_started, info_thread))
        info_thread.start()

    @property
    def parent_path(self):
        """We will use the currently active asset as the parent."""
        if self.view.parent():
            view = self.view.parent().parent().parent().fileswidget
            return view.model().sourceModel().parent_path
        return None

    @parent_path.setter
    def parent_path(self, val):
        pass

    def data_key(self):
        return u'default'

    def data_type(self):
        return common.FileItem

    def sort_data(self):
        """This model is always alphabetical."""
        pass

    @initdata
    def __initdata__(self):
        """Bookmarks and assets are static. But files will be any number of """
        dkey = self.data_key()
        self.INTERNAL_MODEL_DATA[dkey] = common.DataDict({
            common.FileItem: common.DataDict(),
            common.SequenceItem: common.DataDict()
        })

        flags = (
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsDropEnabled |
            QtCore.Qt.ItemIsEditable
        )
        data = self.model_data()

        if not self.parent_path:
            return

        # Thumbnail image
        default_thumbnail = images.ImageCache.get_rsc_pixmap(
            u'folder_sm',
            common.SECONDARY_TEXT,
            self.ROW_SIZE.height())
        default_thumbnail = default_thumbnail.toImage()

        parent_path = u'/'.join(self.parent_path)
        entries = sorted(
            ([f for f in _scandir.scandir(parent_path)]), key=lambda x: x.name)

        for entry in entries:
            if entry.name.startswith(u'.'):
                continue
            if not entry.is_dir():
                continue

            idx = len(data)
            data[idx] = common.DataDict({
                QtCore.Qt.DisplayRole: entry.name,
                QtCore.Qt.EditRole: entry.name,
                QtCore.Qt.StatusTipRole: entry.path.replace(u'\\', u'/'),
                QtCore.Qt.ToolTipRole: u'',
                QtCore.Qt.SizeHintRole: self.ROW_SIZE,
                #
                common.DefaultThumbnailRole: default_thumbnail,
                common.DefaultThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                common.ThumbnailRole: default_thumbnail,
                common.ThumbnailBackgroundRole: QtGui.QColor(0, 0, 0, 0),
                #
                common.FlagsRole: flags,
                common.ParentPathRole: self.parent_path,
                #
                common.FileInfoLoaded: False,
                common.FileThumbnailLoaded: True,
                common.TodoCountRole: 0,
            })
            thread = self.threads[common.InfoThread][0]
            thread.put(weakref.ref(data))
            # thread.worker.dataRequested.emit()