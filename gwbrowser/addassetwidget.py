# -*- coding: utf-8 -*-
"""Defines ``AddAssetWidget``, the main widget used to add a new asset to an
existing bookmark.

Assets are simple folder-structures, and the main placeholders for files
generated during digital production.

The asset templates themselves are simple zip-files. Adding simply means
unzipping their contents into a specified directory.

"""

import functools
from PySide2 import QtWidgets, QtCore, QtGui

import gwbrowser.common as common
from gwbrowser.addfilewidget import DescriptionEditor
from gwbrowser.common_ui import PaintedButton, PaintedLabel, add_row
from gwbrowser.addfilewidget import ThumbnailButton
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
import gwbrowser.gwscandir as gwscandir
import gwbrowser.settings as Settings


class AddAssetWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the ``AddAssetWidget``."""

    def __init__(self, parent=None):
        super(AddAssetWidgetContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_reveal_item_menu()

    @contextmenu
    def add_reveal_item_menu(self, menu_set):
        """Menu for thumbnail operations."""
        menu_set['Reveal'] = {
            'text': u'Reveal destination',
            'action': functools.partial(common.reveal, self.parent().path)
        }
        return menu_set


class AddAssetWidget(QtWidgets.QDialog):
    """Defines the widget used add an asset to the currently active bookmark."""

    def __init__(self, path, parent=None):
        super(AddAssetWidget, self).__init__(parent=parent)
        self._path = path
        self.last_asset_added = None
        self.thumbnail_image = None

        self.save_button = None
        self.name_widget = None
        self.thumbnail_widget = None
        self.description_widget = None

        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.setWindowTitle(u'Add asset')
        self.installEventFilter(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        self._createUI()
        self._connectSignals()

    @property
    def path(self):
        """The active bookmark"""
        return self._path

    def completer_keywords(self):
        """We can give some hints when naming assets using auto-completion.
        The will contain the already existing folder names and some predefined
        shot, sequence names.

        """
        kw = []
        for entry in gwscandir.scandir(self.path):
            kw.append(entry.name)

        for n in xrange(98):
            shot = u'sh{}0'.format(u'{}'.format(n + 1).zfill(2))
            kw.append(shot)
            kw.append(u'lay_{}'.format(shot))
            kw.append(u'lay_{}'.format(shot))
            kw.append(u'ani_{}'.format(shot))
            kw.append(u'fx_{}'.format(shot))
            for m in xrange(98):
                seq = u'seq{}0'.format(u'{}'.format(m + 1).zfill(2))
                kw.append(u'{}_{}'.format(seq, shot))
                kw.append(u'{}_ani_{}'.format(seq, shot))
                kw.append(u'{}_fx_{}'.format(seq, shot))
                kw.append(u'{}_lay_{}'.format(seq, shot))
        kw = sorted(kw)
        kw = sorted(kw, key=lambda s: len(s))

        return kw

    def _createUI(self):
        """Creates the ``AddAssetsWidget``'s ui and layout."""
        common.set_custom_stylesheet(self)
        #
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedWidth(common.WIDTH)

        mainrow = add_row(u'', parent=self)
        # top label
        label = PaintedLabel(u'Add New Asset', size=common.LARGE_FONT_SIZE)
        mainrow.layout().addSpacing(common.MARGIN / 2)
        mainrow.layout().addWidget(label, 0)
        mainrow.layout().addStretch(1)
        #
        row = add_row(u'', height=common.ASSET_ROW_HEIGHT, parent=self)
        #
        self.thumbnail_widget = ThumbnailButton(
            common.ASSET_ROW_HEIGHT, u'Click to add a thumbnail for this job', parent=self)
        row.layout().addWidget(self.thumbnail_widget)

        # Settings the completer associated with the Editor widget
        self.name_widget = QtWidgets.QLineEdit(parent=self)
        self.name_widget.setPlaceholderText(u'Enter asset name...')
        self.name_widget.setFixedWidth(200)
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex)
        self.name_widget.setValidator(validator)
        completer = QtWidgets.QCompleter(
            sorted(self.completer_keywords()), self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setModelSorting(
            QtWidgets.QCompleter.CaseInsensitivelySortedModel)
        completer.setCompletionMode(
            QtWidgets.QCompleter.InlineCompletion)
        self.name_widget.setCompleter(completer)

        column = add_row(u'', vertical=True,
                         height=common.ASSET_ROW_HEIGHT, parent=row)
        self.description_widget = DescriptionEditor(parent=self)
        column.layout().addWidget(self.description_widget)
        row = add_row(u'', parent=column)
        row.layout().addWidget(self.name_widget)

        self.save_button = PaintedButton(u'Add asset', parent=self)
        self.cancel_button = PaintedButton(u'Cancel', parent=self)

        row.layout().addWidget(self.save_button)
        row.layout().addWidget(self.cancel_button)
        self.layout().addSpacing(common.MARGIN)

    def _connectSignals(self):
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # self.thumbnail_widget.clicked.connect(
        #     self.thumbnail_widget.pick_thumbnail)
        #

    def done(self, result):
        """Slot called by the check button to create a new asset."""
        if result == QtWidgets.QDialog.Rejected:
            return super(AddAssetWidget, self).done(result)

        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Error adding asset')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)

        file_info = QtCore.QFileInfo(self.path)

        if not file_info.exists():
            mbox.setText(
                u'The destination folder does not exists.')
            mbox.setInformativeText(
                u'{} does not exist. Make sure a valid bookmark is activated before trying to add the asset.'.format(file_info.filePath()))
            return mbox.exec_()

        if not file_info.isWritable():
            mbox.setText(
                u'{} is not writable.'.format(file_info.filePath()))
            mbox.setInformativeText(
                u'The destination folder is not writeable. Check if you have permissions to create files and folders.')
            return mbox.exec_()

        if not self.name_widget.text():
            mbox.setText(u'The asset has no name.')
            mbox.setInformativeText(
                u'You must set a name before adding an asset. The description and the thumbnails are optional, albeit highly recommended to add these as well. ')
            return mbox.exec_()

        path = ur'{}/{}'.format(file_info.filePath(), self.name_widget.text())
        file_info = QtCore.QFileInfo(path)
        if file_info.exists():
            mbox.setText(u'"{}" already exists. Try again with a different name...'.format(
                self.name_widget.text()))
            mbox.setInformativeText(u'')
            return mbox.exec_()

        # Finally, let's actually create the asset
        try:
            common.create_asset_from_template(
                self.name_widget.text(), self.path, template=common.MayaAssetTemplate)
            self.save_thumbnail_and_description()
        except Exception as err:
            mbox.setText(u'An error occured when creating the asset:')
            mbox.setInformativeText('{}'.format(err))
            return mbox.exec_()

        mbox.setWindowTitle(u'Success')
        mbox.setText(u'Succesfully added "{}".'.format(
            self.name_widget.text()))
        mbox.setIcon(QtWidgets.QMessageBox.NoIcon)
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        mbox.setDefaultButton(QtWidgets.QMessageBox.No)
        mbox.setInformativeText(
            u'Do you want to add another asset?')
        if mbox.exec_() == QtWidgets.QMessageBox.Yes:
            self.name_widget.setText(u'')
            self.description_widget.setText(u'')
            self.thumbnail_widget.reset_thumbnail()
            return
        else:
            self.last_asset_added = self.name_widget.text()
            common.reveal(u'{}/{}'.format(self.path, self.name_widget.text()))
        super(AddAssetWidget, self).done(result)

    def save_thumbnail_and_description(self):
        """Saves the selected thumbnail and description in the config file."""
        if not self.parent():
            return
        if not hasattr(self.parent(), 'widget'):
            return

        bindex = self.parent().widget(0).model().sourceModel().active_index()
        if not bindex.isValid():
            return

        server, job, root = bindex.data(common.ParentRole)
        asset = self.name_widget.text()
        settings = Settings.AssetSettings(
            QtCore.QModelIndex(), args=(server, job, root, asset))

        description = self.description_widget.text()
        if description:
            settings.setValue(u'config/description', description)
        if self.thumbnail_widget.image:
            if not self.thumbnail_widget.image.isNull():
                self.thumbnail_widget.image.save(settings.thumbnail_path())

        settings.deleteLater()

    def contextMenuEvent(self, event):
        menu = AddAssetWidgetContextMenu(parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = AddAssetWidget(ur'C:\temp')
    w.exec_()
