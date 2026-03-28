import threading
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List
import time
import logging

from config_system import config
from zena_mode.resource_manager import resource_manager

logger = logging.getLogger("BatchManager")


class BatchManager:
    """Simple persistent job queue for batch jobs.

    - Jobs persisted to `jobs.json` in config.BASE_DIR
    - Uses resource_manager to run blocking tasks in threads
    """

    def __init__(self, path: Path = None):
        self._lock = threading.RLock()
        self.path = path or (config.BASE_DIR / "jobs.json")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._jobs = {j["id"]: j for j in data}
        except Exception as e:
            logger.warning(f"Failed to load jobs: {e}")
            self._jobs = {}

    def _save(self):
        tmp = str(self.path) + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(list(self._jobs.values()), f, indent=2)
            Path(tmp).replace(self.path)
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")

    def enqueue(self, job_type: str, params: Dict[str, Any]) -> str:
        with self._lock:
            jid = str(uuid.uuid4())
            job = {
                "id": jid,
                "type": job_type,
                "params": params,
                "status": "queued",
                "created_at": time.time(),
                "updated_at": time.time(),
                "result": None,
                "logs": [],
            }
            self._jobs[jid] = job
            self._save()
            # Auto-start for simple jobs
            self.start_job(jid)
            return jid

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._jobs.values())

    def get_job(self, jid: str) -> Dict[str, Any]:
        return self._jobs.get(jid)

    def start_job(self, jid: str):
        job = self._jobs.get(jid)
        if not job:
            return
        if job["status"] in ("running", "completed"):
            return

        def _run():
            try:
                job["status"] = "running"
                job["updated_at"] = time.time()
                self._save()
                # Dispatch by type
                if job["type"] == "code_review":
                    from zena_mode.analysis import analyze_and_write_report

                    res = analyze_and_write_report(job["params"].get("files", []), job_id=jid)
                    job["result"] = res
                    job["status"] = "completed"
                else:
                    job["logs"].append(f"Unknown job type: {job['type']}")
                    job["status"] = "failed"
            except Exception as e:
                job["logs"].append(str(e))
                job["status"] = "failed"
            finally:
                job["updated_at"] = time.time()
                self._save()

        # Run in tracked thread
        resource_manager.add_worker_thread(_run, daemon=True)


# singleton instance
batch_manager = BatchManager()
