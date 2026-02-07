from pathlib import Path
import time
from typing import List, Tuple, Optional

class ReportWatcher:
    """Ожидание файлов-репортов с проверкой контрольных фраз."""

    def check_report_once(
        self,
        report_path: Path,
        control_phrases: List[str],
    ) -> Tuple[bool, Optional[str]]:
        """Проверяет наличие файла по report_path и контрольных фраз в его содержимом один раз."""
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8")
            all_phrases_found = True
            for phrase in control_phrases:
                if phrase not in content:
                    all_phrases_found = False
                    break
            if all_phrases_found:
                return True, content
        return False, None

    def wait_for_report(
        self,
        report_path: Path,
        control_phrases: List[str],
        timeout: int = 300,
        check_interval: int = 10
    ) -> bool:
        """Ожидает появления файла по report_path, проверяет наличие контрольных фраз в его содержимом."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            success, _ = self.check_report_once(report_path, control_phrases)
            if success:
                return True
            time.sleep(check_interval)
        return False
