from PyQt5.QtCore import QSemaphore, QMutex
from queue import Queue


class Buffer(object):

    def __init__(self, buffer_size=5):
        self.buffer_size = buffer_size
        self.free_slots = QSemaphore(self.buffer_size)
        self.used_slots = QSemaphore(0)
        self.clear_buffer_add = QSemaphore(1)
        self.clear_buffer_get = QSemaphore(1)
        self.queue_mutex = QMutex()
        self.queue = Queue(self.buffer_size)

    def add(self, data, drop_if_full=False):
        self.clear_buffer_add.acquire()
        if drop_if_full:
            if self.free_slots.tryAcquire():
                self.queue_mutex.lock()
                self.queue.put(data)
                self.queue_mutex.unlock()
                self.used_slots.release()
        else:
            self.free_slots.acquire()
            self.queue_mutex.lock()
            self.queue.put(data)
            self.queue_mutex.unlock()
            self.used_slots.release()

        self.clear_buffer_add.release()

    def get(self):
        # acquire semaphores
        self.clear_buffer_get.acquire()
        self.used_slots.acquire()
        self.queue_mutex.lock()
        data = self.queue.get()
        self.queue_mutex.unlock()
        # release semaphores
        self.free_slots.release()
        self.clear_buffer_get.release()
        # return item to caller
        return data

    def clear(self):
        # check if buffer contains items
        if self.queue.qsize() > 0:
            # stop adding items to buffer (will return false if an item is currently being added to the buffer)
            if self.clear_buffer_add.tryAcquire():
                # stop taking items from buffer (will return false if an item is currently being taken from the buffer)
                if self.clear_buffer_get.tryAcquire():
                    # release all remaining slots in queue
                    self.free_slots.release(self.queue.qsize())
                    # acquire all queue slots
                    self.free_slots.acquire(self.buffer_size)
                    # reset used_slots to zero
                    self.used_slots.acquire(self.queue.qsize())
                    # clear buffer
                    for _ in range(self.queue.qsize()):
                        self.queue.get()
                    # release all slots
                    self.free_slots.release(self.buffer_size)
                    # allow get method to resume
                    self.clear_buffer_get.release()
                else:
                    return False
                # allow add method to resume
                self.clear_buffer_add.release()
                return True
            else:
                return False
        else:
            return False

    def size(self):
        return self.queue.qsize()

    def maxsize(self):
        return self.buffer_size

    def isfull(self):
        return self.queue.qsize() == self.buffer_size

    def isempty(self):
        return self.queue.qsize() == 0
