# -*- coding: utf-8 -*-
"""The threads and associated worker classes.

Thumbnail and file-load work on carried out on secondary threads.
Each thread is assigned a single Worker - usually responsible for taking
*QModelIndexes* from the thread's python Queue.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import time
import base64
import json
import Queue
import functools
import weakref
import collections

from PySide2 import QtCore, QtGui, QtWidgets

import bookmarks.images as images
import bookmarks.bookmark_db as bookmark_db
import bookmarks.common as common
import bookmarks.defaultpaths as defaultpaths
import OpenImageIO


THREADS = {}


class ThreadMonitor(QtWidgets.QWidget):
    """A progress label used to display the number of items currently in the
    processing queues across all threads.

    """
    def __init__(self, parent=None):
        super(ThreadMonitor, self).__init__(parent=parent)
        self.timer = QtCore.QTimer(parent=self)
        self.timer.setInterval(200)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.update)
        self.metrics = QtGui.QFontMetrics(
            common.font_db.primary_font(common.SMALL_FONT_SIZE()))

    def showEvent(self, event):
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.SMALL_FONT_SIZE()),
            self.rect(),
            self.text(),
            QtCore.Qt.AlignCenter,
            common.ADD
        )
        painter.end()

    def update(self):
        self.setFixedWidth(self.metrics.width(self.text()) + common.MARGIN())
        super(ThreadMonitor, self).update()

    @staticmethod
    def text():
        l = 0
        for thread in THREADS.itervalues():
            if thread.worker is None:
                continue
            l += len(thread.worker.data_queue.queue)

        if l == 0:
            return u''

        return u'Loading... ({} left)'.format(l)




class UniqueQueue(Queue.Queue):
    """A queue for queuing only unique items.
    https://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue"""

    def _init(self, maxsize):
        self.queue = collections.deque()

    def put(self, item, block=True, timeout=None, force=False):
        '''Put an item into the queue.
        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until a free slot is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Full exception if no free slot was available within that time.
        Otherwise ('block' is false), put an item on the queue if a free slot
        is immediately available, else raise the Full exception ('timeout'
        is ignored in that case).
        '''
        with self.not_full:
            if self.maxsize > 0:
                if not block:
                    if self._qsize() >= self.maxsize:
                        raise Queue.Full
                elif timeout is None:
                    while self._qsize() >= self.maxsize:
                        self.not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    endtime = time.time() + timeout
                    while self._qsize() >= self.maxsize:
                        remaining = endtime - time.time()
                        if remaining <= 0.0:
                            raise Queue.Full
                        self.not_full.wait(remaining)
            self._put(item, force=force)
            self.unfinished_tasks += 1
            self.not_empty.notify()

    def _put(self, item, force=False):
        if force:  # Force the item to the beginning of the queue
            self.queue.append(item)
        else:  # otherwise append to the end
            self.queue.appendleft(item)

    def _get(self):
        return self.queue.pop()


def process(func):
    """Decorator wraps the worker's process_data call.

    Takes and passes the next available data in the queue for processing
    and emits the `dataReady` signal if the data has been correctly loaded.

    """
    @functools.wraps(func)
    def func_wrapper(self):
        result = None
        try:
            result = func(self, self.data_queue.get(False))
            if not result:
                return
            self.dataReady.emit(result)
            self.data_queue.task_done()
        except Queue.Empty:
            return
        except:
            common.Log.error(u'Failed whilst processing data')
        finally:
            self.interrupt = False

    return func_wrapper


class BaseWorker(QtCore.QObject):
    """Base thread worker class.

    Each work has its own queue. The thread controllers also control the workers
    via the `dataRequested` signal. When this is emited the worker will
    take the next available data from the queue.

    """
    dataRequested = QtCore.Signal()
    dataReady = QtCore.Signal(dict)
    resetQueue = QtCore.Signal()

    def __init__(self, parent=None):
        super(BaseWorker, self).__init__(parent=parent)
        self.interrupt = False
        self.data_queue = UniqueQueue()
        self.dataRequested.connect(
            self.process_data, QtCore.Qt.DirectConnection)

        self.resetQueue.connect(
            lambda: common.Log.debug(u'resetQueue --> reset_queue', self))
        self.resetQueue.connect(
            self.reset_queue, type=QtCore.Qt.QueuedConnection)

    @QtCore.Slot()
    def reset_queue(self):
        common.Log.debug('reset_queue()', self)

        self.interrupt = True
        try:
            while True:
                self.data_queue.get(False)
        except Queue.Empty:
            return
        except Exception:
            common.Log.error('Error resetting the queue')

    @process
    @QtCore.Slot()
    def process_data(self, ref):
        if self.interrupt:
            return None
        return ref


class BaseThread(QtCore.QThread):
    """Base thread controller.

    """
    startTimer = QtCore.Signal()
    stopTimer = QtCore.Signal()

    def __init__(self, cls, interval=1000, parent=None):
        super(BaseThread, self).__init__(parent=parent)
        if repr(self) not in THREADS:
            THREADS[repr(self)] = self

        self._interval = interval
        self.worker = cls
        self.timer = None
        self.setTerminationEnabled(True)

        self.started.connect(
            lambda: common.Log.debug(u'started --> move_worker_to_thread', self))
        self.started.connect(self.move_worker_to_thread)

        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.quit)
        QtGui.QGuiApplication.instance().lastWindowClosed.connect(self.quit)

    def run(self):
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(False)
        self.timer.setInterval(self._interval)
        self.timer.setTimerType(QtCore.Qt.CoarseTimer)

        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.timer.stop)
        QtGui.QGuiApplication.instance().lastWindowClosed.connect(self.timer.stop)
        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.timer.deleteLater)
        QtGui.QGuiApplication.instance().lastWindowClosed.connect(self.timer.deleteLater)

        self.exec_()

    @QtCore.Slot()
    def move_worker_to_thread(self):
        common.Log.debug(u'move_worker_to_thread', self)

        self.worker.moveToThread(self)

        self.timer.timeout.connect(
            self.worker.dataRequested, QtCore.Qt.DirectConnection)

        self.startTimer.connect(
            lambda: common.Log.debug(u'startTimer --> timer.start', self))
        self.startTimer.connect(self.timer.start, QtCore.Qt.QueuedConnection)

        self.stopTimer.connect(
            lambda: common.Log.debug(u'stopTimer --> timer.stop', self))
        self.stopTimer.connect(self.timer.stop, QtCore.Qt.QueuedConnection)

    def put(self, ref, force=False):
        """Main method to add an item to the thread's worker queue.

        Because the underlying data structure wil be destroyed by sorting and
        data reloads, we'll take weakrefs to the data. The worker will have
        to check whilst processing to verify the data is still valid.

        """
        if not isinstance(ref, weakref.ref):
            raise TypeError(u'Invalid data type. Must be <type \'weakref\'>')
        try:
            self.worker.interrupt = False
            if force:
                self.worker.data_queue.put(ref)
            else:
                if ref not in self.worker.data_queue.queue:
                    self.worker.data_queue.put(ref)
        except Queue.Full:
            pass


class InfoWorker(BaseWorker):
    """A worker used to retrieve file information.

    For large number of files this involves multiple IO calls that while
    don't want to do in the main thread.

    """
    @process
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        """Slot to load all necessary file-information."""
        if not ref() or self.interrupt:
            return None
        ref = self.process_file_information(ref)
        if not ref():
            return None
        return ref

    @classmethod
    def process_file_information(cls, ref):
        """Populates the DataDict instance with all file information.

        Args:
            ref (weakref): An internal model data DataDict instance's weakref.

        Returns:
            weakref: The original weakref, or None if loading fails.

        """
        if not ref():
            return None
        if ref()[common.FileInfoLoaded]:
            return ref

        # The call should already be thread-safe guarded by a lock
        if not ref():
            return None
        pp = ref()[common.ParentPathRole]
        db = bookmark_db.get_db(
            QtCore.QModelIndex(),
            server=pp[0],
            job=pp[1],
            root=pp[2]
        )
        if not db:
            return None

        # DATABASE --BEGIN--
        with db.transactions():
            # Item description
            if not ref():
                return None
            k = common.proxy_path(ref())

            # Description
            v = db.value(k, u'description')
            if v:
                if not ref():
                    return None
                ref()[common.DescriptionRole] = v

            v = db.value(k, u'notes')
            count = 0
            if v:
                try:
                    v = base64.b64decode(v)
                    v = json.loads(v)
                    count = [k for k in v if v[k][u'text']
                             and not v[k][u'checked']]
                    count = len(count)
                except:
                    common.Log.error(u'Could not read notes')

            if not ref():
                return None
            ref()[common.TodoCountRole] = count

            # Item flags
            if not ref():
                return None
            flags = ref()[
                common.FlagsRole] | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled
            v = db.value(k, u'flags')
            if v:
                flags = flags | v

            if not ref():
                return None
            ref()[common.FlagsRole] = flags

        # For sequence items we will work out the name of the sequence based on
        # the frames.
        if not ref():
            return None
        if ref()[common.TypeRole] == common.SequenceItem:
            if not ref():
                return None
            frs = ref()[common.FramesRole]
            intframes = [int(f) for f in frs]
            padding = len(frs[0])
            rangestring = common.get_ranges(intframes, padding)

            if not ref():
                return None
            seq = ref()[common.SequenceRole]
            startpath = \
                seq.group(1) + \
                unicode(min(intframes)).zfill(padding) + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            endpath = \
                seq.group(1) + \
                unicode(max(intframes)).zfill(padding) + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            seqpath = \
                seq.group(1) + \
                u'[' + rangestring + u']' + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            thumb_k = \
                seq.group(1) + \
                u'[0]' + \
                seq.group(3) + \
                u'.' + \
                seq.group(4)
            seqname = seqpath.split(u'/')[-1]

            # Setting the path names
            if not ref():
                return None
            ref()[common.StartpathRole] = startpath
            if not ref():
                return None
            ref()[common.EndpathRole] = endpath
            if not ref():
                return None
            ref()[QtCore.Qt.StatusTipRole] = seqpath
            if not ref():
                return None
            ref()[QtCore.Qt.ToolTipRole] = seqpath
            if not ref():
                return None
            ref()[QtCore.Qt.DisplayRole] = seqname
            if not ref():
                return None
            ref()[QtCore.Qt.EditRole] = seqname
            if not ref():
                return None
            ref()[common.ThumbnailPathRole] = db.thumbnail_path(thumb_k)

            # We saved the DirEntry instances previously in `__initdata__` but
            # only for the thread to extract the information from it.
            if not ref():
                return None
            er = ref()[common.EntryRole]
            if er:
                mtime = 0
                for entry in er:
                    stat = entry.stat()
                    mtime = stat.st_mtime if stat.st_mtime > mtime else mtime
                    if not ref():
                        return None
                    ref()[common.SortBySizeRole] += stat.st_size
                if not ref():
                    return None
                ref()[common.SortByLastModifiedRole] = mtime
                mtime = common.qlast_modified(mtime)

                if not ref():
                    return None
                info_string = \
                    unicode(len(intframes)) + u'f;' + \
                    mtime.toString(u'dd') + u'/' + \
                    mtime.toString(u'MM') + u'/' + \
                    mtime.toString(u'yyyy') + u' ' + \
                    mtime.toString(u'hh') + u':' + \
                    mtime.toString(u'mm') + u';' + \
                    common.byte_to_string(ref()[common.SortBySizeRole])
                if not ref():
                    return None
                ref()[common.FileDetailsRole] = info_string

        if not ref():
            return None
        if ref()[common.TypeRole] == common.FileItem:
            if not ref():
                return None
            er = ref()[common.EntryRole]
            if er:
                stat = er[0].stat()
                mtime = stat.st_mtime
                ref()[common.SortByLastModifiedRole] = mtime
                mtime = common.qlast_modified(mtime)
                ref()[common.SortBySizeRole] = stat.st_size
                info_string = \
                    mtime.toString(u'dd') + u'/' + \
                    mtime.toString(u'MM') + u'/' + \
                    mtime.toString(u'yyyy') + u' ' + \
                    mtime.toString(u'hh') + u':' + \
                    mtime.toString(u'mm') + u';' + \
                    common.byte_to_string(ref()[common.SortBySizeRole])
                if not ref():
                    return None
                ref()[common.FileDetailsRole] = info_string
            if not ref():
                return None
            ref()[common.ThumbnailPathRole] = db.thumbnail_path(
                ref()[QtCore.Qt.StatusTipRole])

        # Finally, set flag to mark this loaded
        if not ref():
            return None
        ref()[common.FileInfoLoaded] = True

        if not ref():
            return None
        return ref


class BackgroundInfoWorker(InfoWorker):
    """An alternate file information loader.

    Instead of a taking a single file, it concerns itself with iterating over
    all items in a data-set.

    """
    modelLoaded = QtCore.Signal(weakref.ref)

    @process
    @QtCore.Slot(weakref.ref)
    def process_data(self, ref):
        """Iterates over all items in a model data segment.

        It does not return the original reference but emits the `modelLoaded`
        signal that triggers all necessary refresh slots.

        Args:
            ref (type): Internal model data DataDict.

        """
        if not ref() or self.interrupt:
            return None

        changed = False
        for item in ref().itervalues():
            if not ref() or self.interrupt:
                return None
            if item[common.FileInfoLoaded]:
                continue
            self.process_file_information(weakref.ref(item))
            changed = True

        if not ref() or self.interrupt:
            return None
        if changed:
            common.Log.debug('modelLoaded.emit()', self)
            self.modelLoaded.emit(ref)
        return None

    def reset_queue(self):
        common.Log.debug('reset_queue()', self)

        self.interrupt = True


class ThumbnailWorker(BaseWorker):
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """The static method responsible for querrying the file item's thumbnail.

        We will get the thumbnail's path, check if a cached thumbnail exists already,
        then load it. If there's no thumbnail, we will try to generate a thumbnail
        using OpenImageIO.

        """
        if not ref() or self.interrupt:
            return None

        if ref()[common.FlagsRole] & common.MarkedAsArchived:
            return None

        # In theory a one of the FileInfoWorkers thread should already have
        # picked the item up as the they have a smaller refresh frequency. Best
        # is to wait a while for the data to load, and abort after...
        n = 0
        while ref() and not ref()[common.FileInfoLoaded]:
            if n > 20:
                return None
            if not ref() or self.interrupt:
                return None
            time.sleep(0.1)
            n += 1

        if not ref() or self.interrupt:
            return None
        if ref()[common.FileThumbnailLoaded]:
            return None

        if not ref() or self.interrupt:
            return None
        thumbnail_path = ref()[common.ThumbnailPathRole]
        if not ref() or self.interrupt:
            return None
        height = ref()[QtCore.Qt.SizeHintRole].height()
        if not ref() or self.interrupt:
            return None
        ext = ref()[QtCore.Qt.StatusTipRole].split(u'.')[-1].lower()
        image = None

        # Checking if we can load an existing image
        if QtCore.QFileInfo(thumbnail_path).exists():
            image = images.ImageCache.get(
                thumbnail_path, int(height), overwrite=True)
            if not image:
                return None

            if not ref() or self.interrupt:
                return None
            ref()[common.ThumbnailRole] = image
            if not ref() or self.interrupt:
                return None
            ref()[common.FileThumbnailLoaded] = True
            if not ref() or self.interrupt:
                return None
            return ref

        # If the item doesn't have a saved thumbnail we will check if
        # OpenImageIO is able to make a thumbnail for it:
        if ext.lower() not in defaultpaths.get_extensions(defaultpaths.OpenImageIOFilter):
            return None

        if not ref() or self.interrupt:
            return None
        ref()[common.FileThumbnailLoaded] = False

        if not self.process_thumbnail(ref):
            return None
        if not ref() or self.interrupt:
            return None
        ref()[common.FileThumbnailLoaded] = True
        if not ref() or self.interrupt:
            return None
        return ref

    @QtCore.Slot(weakref.ref)
    @staticmethod
    def process_thumbnail(ref):
        """Wraps the `oiio_make_thumbnail()` call when the source data is
        a weak dict reference.

        Args:
            ref (weakref.ref):  A weak reference to a data segment.

        Returns:
            bool: `True` when the operation was successful, `False` otherwise

        """
        try:
            # OpenImageIO images.ImageCache instance to control file handles
            cache = OpenImageIO.ImageCache()

            if not ref():
                return False
            source = ref()[QtCore.Qt.StatusTipRole]
            if common.is_collapsed(source):
                source = common.get_sequence_startpath(source)
            if not ref():
                return False
            dest = ref()[common.ThumbnailPathRole]

            # Making sure we're not trying to generate a thumbnail for
            # a very big file
            if QtCore.QFileInfo(source).size() >= pow(1024, 3) * 2: # 1GB
                return False

            if not images.ImageCache.oiio_make_thumbnail(source, dest, common.THUMBNAIL_IMAGE_SIZE):
                return False

            if not ref():
                return False
            image = images.ImageCache.get(
                ref()[common.ThumbnailPathRole],
                # ref()[QtCore.Qt.SizeHintRole].height() - common.ROW_SEPARATOR(),
                ref()[QtCore.Qt.SizeHintRole].height(),
                overwrite=True
            )
            if not ref():
                return False
            ref()[common.ThumbnailRole] = image
            if not ref():
                return False
            return True
        except:
            if ref():
                ref()[common.ThumbnailRole] = ref()[common.DefaultThumbnailRole]
            common.Log.error('Failed to generate thumbnail')
        finally:
            if ref():
                ref()[common.FileThumbnailLoaded] = True
            cache.invalidate(source, force=True)
            cache.invalidate(dest, force=True)


class TaskFolderWorker(BaseWorker):
    @process
    @QtCore.Slot()
    def process_data(self, ref):
        """Counts the number of items in the task folder up to 999.

        """
        if not ref() or self.interrupt:
            return None
        vals = ref().values()
        for _ref in [weakref.ref(f) for f in vals]:
            if not ref() or self.interrupt:
                return None

            count = 0
            for entry in common.walk(_ref()[QtCore.Qt.StatusTipRole]):
                if not ref() or not _ref() or self.interrupt:
                    return None
                if entry.name.startswith(u'.'):
                    continue
                count += 1
                if count > 999:
                    break

            if not ref() or not _ref() or self.interrupt:
                return None
            _ref()[common.TodoCountRole] = count
            if not ref() or not _ref() or self.interrupt:
                return None
            self.dataReady.emit(_ref)
        return None
