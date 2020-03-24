# -*- coding: utf-8 -*-
"""**Bookmarks is a simple asset browser used to create and navigate
the files and folders of animation or film productions.**

"""

import sys
import os
import importlib
import traceback
import platform

name = u'bookmarks'
author = 'Gergely Wootsch'
website = 'https://gergely-wootsch.com'
email = 'hello@gergely-wootsch.com'
__version__ = u'0.3.0'


def get_info():
    """Returns an array of string with the dependent library versions and information
    about the author.

    """
    return (
        u'Author:   {}'.format(author),
        u'Email:    {}'.format(email),
        u'Website:  {}'.format(website),
        u'Version:  {}'.format(__version__),
        u'\n',
        u'Python {} {}'.format(
            platform.python_version(), platform.python_compiler()),
        u'OpenImageIO {}'.format(
            importlib.import_module('OpenImageIO').__version__),
        u'{}'.format(
            importlib.import_module('alembic').Abc.GetLibraryVersion()),
        u'PySide2 {}'.format(
            importlib.import_module('PySide2.QtCore').__version__),
    )


def exec_(debug=False):
    """Starts the product as a standalone PySide2 application.

    .. code-block:: python

        import bookmarks
        bookmarks.exec_()

    """
    # Some basic debugging information
    for info in get_info():
        sys.stdout.write(u'{}\n'.format(info))

    bookmarks = importlib.import_module(
        u'{}.standalone'.format(name))

    from PySide2 import QtWidgets, QtCore

    if QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication.instance()
    else:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        app = bookmarks.StandaloneApp([])

    if debug:
        import bookmarks.common as common
        common.DEBUG_ON = True
        logview = common.LogView()
        logview.show()

    widget = bookmarks.StandaloneMainWidget()

    import bookmarks.mainwidget as mainwidget
    mainwidget.show_window()
    
    app.exec_()
