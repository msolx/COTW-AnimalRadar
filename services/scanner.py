"""扫描线程拥有数据源；UI 通过信号接收不可变快照。"""
import threading
import time
import logging
from dataclasses import replace
from PySide6.QtCore import QThread, Signal
from models.player import Snapshot

class Scanner(QThread):
    snapshot = Signal(object)

    def __init__(self,factory,interval):
        super().__init__()
        self.factory, self.interval = factory,interval
        self.stop_event = threading.Event()
        self.paused = threading.Event()
        self.reconnect_event = threading.Event()
        self.wake_event = threading.Event()
        self.control_lock = threading.Lock()
        self._generation = 0
        self.reserve_id = None
        import config
        self.details_enabled = config.DETAILS_JOIN_ENABLED

    def set_details_enabled(self,enabled):
        with self.control_lock:
            self.details_enabled = bool(enabled)
        self.request_reconnect()  # 丢弃更改前排队的旧帧；暂停状态不改变

    def set_reserve(self,reserve):
        # 只传递普通值，后台线程不访问 Qt 控件；换区由现有重连代次清理旧帧。
        with self.control_lock:
            self.reserve_id = reserve

    @property
    def generation(self):
        with self.control_lock:
            return self._generation

    def pause_refresh(self):
        with self.control_lock:
            self._generation += 1
            self.paused.set()
        self.wake_event.set()

    def resume_refresh(self):
        with self.control_lock:
            self._generation += 1
            self.paused.clear()
        self.wake_event.set()

    def request_reconnect(self):
        with self.control_lock:
            self._generation += 1
            self.reconnect_event.set()
        self.wake_event.set()

    def set_interval(self,value):
        if value <= 0:
            raise ValueError('刷新间隔必须为正')
        self.interval = value
        self.wake_event.set()

    def _publish(self,result,generation):
        if (not self.stop_event.is_set() and not self.paused.is_set()
            and generation == self.generation):
            self.snapshot.emit(replace(result,generation=generation))

    def run(self):
        source = None
        factory_failed = False
        try:
            suspended = False
            while not self.stop_event.is_set():
                self.wake_event.clear()
                if self.stop_event.is_set():
                    break
                reconnect = self.reconnect_event.is_set()
                if reconnect:
                    self.reconnect_event.clear()
                if source is None:
                    # 初始化错误也允许通过“重新连接”恢复，但不自行反复创建失败的数据源。
                    if factory_failed and not reconnect:
                        self.wake_event.wait()
                        continue
                    try:
                        source = self.factory()
                        factory_failed = False
                    except Exception as exc:
                        factory_failed = True
                        self._publish(Snapshot(None,(),time.time(),f'数据源启动失败：{exc}',False),self.generation)
                        self.wake_event.wait()
                        continue
                elif reconnect:
                    if hasattr(source,'reconnect'):
                        source.reconnect()
                    # 重连会清除数据源自身的暂停状态，必须重新同步，不能沿用旧标记。
                    suspended = False
                if self.paused.is_set():
                    if not suspended and hasattr(source,'suspend'):
                        source.suspend()
                    suspended = True
                    self.wake_event.wait()
                    continue
                else:
                    suspended = False
                    generation = self.generation
                    try:
                        if hasattr(source,'set_details_enabled'):
                            with self.control_lock:
                                details_enabled = self.details_enabled
                            source.set_details_enabled(details_enabled)
                        if hasattr(source,'set_reserve'):
                            with self.control_lock:
                                reserve = self.reserve_id
                            source.set_reserve(reserve)
                        result = source.scan()
                    except Exception as exc:
                        result = Snapshot(None,(),time.time(),f'采样失败：{exc}',False)
                    self._publish(result,generation)
                self.wake_event.wait(self.interval)
        except Exception as exc:
            # 暂停时不发布坐标快照，但线程异常仍需留下可检查的诊断。
            logging.exception('扫描线程异常停止')
            self._publish(Snapshot(None,(),time.time(),f'数据源启动失败：{exc}',False),self.generation)
        finally:
            if source:
                source.close()

    def stop(self):
        with self.control_lock:
            self._generation += 1
        self.stop_event.set()
        self.wake_event.set()
