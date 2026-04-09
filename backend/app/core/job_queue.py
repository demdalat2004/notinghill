"""
NotingHill — core/job_queue.py
Simple thread-safe in-memory job queue with worker pool.
"""
import queue
import threading
import time
from typing import Callable, Any

_task_queue: queue.Queue = queue.Queue(maxsize=50000)
_workers: list[threading.Thread] = []
_running = threading.Event()
_progress: dict[int, dict] = {}   # job_id -> progress dict
_lock = threading.Lock()


def start_workers(n: int = 4):
    _running.set()
    for i in range(n):
        t = threading.Thread(target=_worker_loop, daemon=True, name=f"nh-worker-{i}")
        t.start()
        _workers.append(t)


def stop_workers():
    _running.clear()
    for _ in _workers:
        _task_queue.put(None)


def enqueue(fn: Callable, *args, **kwargs):
    _task_queue.put((fn, args, kwargs))


def _worker_loop():
    while _running.is_set():
        try:
            item = _task_queue.get(timeout=1)
            if item is None:
                break
            fn, args, kwargs = item
            try:
                fn(*args, **kwargs)
            except Exception as e:
                import traceback
                print(f"[Worker] Error: {e}\n{traceback.format_exc()}")
            finally:
                _task_queue.task_done()
        except queue.Empty:
            continue


def set_progress(job_id: int, **kwargs):
    with _lock:
        if job_id not in _progress:
            _progress[job_id] = {}
        _progress[job_id].update(kwargs)
        _progress[job_id]["updated_at"] = time.time()


def get_progress(job_id: int) -> dict:
    with _lock:
        return dict(_progress.get(job_id, {}))


def get_all_progress() -> dict:
    with _lock:
        return dict(_progress)


def queue_size() -> int:
    return _task_queue.qsize()
