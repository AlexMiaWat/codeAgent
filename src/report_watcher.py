import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ReportWatcher:
    def __init__(self, report_dir="cursor_results/"):
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)
        self.found_report = False
        self.report_path = None

    def _check_report_content(self, file_path, control_phrase):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if control_phrase in content:
                    return True
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
        return False

    def wait_for_report(self, control_phrase, timeout=60):
        """
        Waits for a report file containing a specific control phrase.

        Args:
            control_phrase (str): The phrase to look for in the report file.
            timeout (int): The maximum time to wait in seconds.

        Returns:
            str: The path to the report file if found, otherwise None.
        """
        print(f"Waiting for report in {self.report_dir} with control phrase: '{control_phrase}' (timeout: {timeout}s)")
        self.found_report = False
        self.report_path = None

        class ReportHandler(FileSystemEventHandler):
            def __init__(self, watcher_instance, phrase):
                super().__init__()
                self.watcher = watcher_instance
                self.control_phrase = phrase

            def on_created(self, event):
                if not event.is_directory and event.src_path.startswith(self.watcher.report_dir):
                    print(f"New file created: {event.src_path}")
                    if self.watcher._check_report_content(event.src_path, self.control_phrase):
                        self.watcher.found_report = True
                        self.watcher.report_path = event.src_path

            def on_modified(self, event):
                if not event.is_directory and event.src_path.startswith(self.watcher.report_dir):
                    print(f"File modified: {event.src_path}")
                    if not self.watcher.found_report and self.watcher._check_report_content(event.src_path, self.control_phrase):
                        self.watcher.found_report = True
                        self.watcher.report_path = event.src_path

        event_handler = ReportHandler(self, control_phrase)
        observer = Observer()
        observer.schedule(event_handler, self.report_dir, recursive=False)
        observer.start()

        start_time = time.time()
        while not self.found_report and (time.time() - start_time) < timeout:
            time.sleep(1)

        observer.stop()
        observer.join()

        if self.found_report:
            print(f"Report found: {self.report_path}")
            return self.report_path
        else:
            print(f"Timeout reached. No report found with control phrase '{control_phrase}'.")
            return None

if __name__ == '__main__':
    # Example usage:
    watcher = ReportWatcher(report_dir="test_reports/") # Use a test directory
    
    # Create a dummy report directory if it doesn't exist
    os.makedirs("test_reports/", exist_ok=True)

    # Simulate a file being created after a delay
    def create_dummy_report(content, delay):
        time.sleep(delay)
        file_path = "test_reports/dummy_report.md"
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created dummy report: {file_path}")
        return file_path

    import threading

    print("--- Test Case 1: Report found ---")
    report_thread = threading.Thread(target=create_dummy_report, args=("This is a test report with control phrase success!", 3))
    report_thread.start()
    found_file = watcher.wait_for_report("success!", timeout=10)
    print(f"Result for Test Case 1: {found_file}")
    if found_file:
        os.remove(found_file) # Clean up
    report_thread.join()

    print("
--- Test Case 2: Report not found (timeout) ---")
    found_file = watcher.wait_for_report("non_existent_phrase", timeout=5)
    print(f"Result for Test Case 2: {found_file}")

    print("
--- Test Case 3: Report found after modification ---")
    # Create an empty file first, then modify it
    initial_file_path = "test_reports/modified_report.md"
    with open(initial_file_path, 'w') as f:
        f.write("Initial content.")
    print(f"Created initial file: {initial_file_path}")

    def modify_dummy_report(content, delay, file_path):
        time.sleep(delay)
        with open(file_path, 'a') as f: # Append content
            f.write(content)
        print(f"Modified dummy report: {file_path}")

    modify_thread = threading.Thread(target=modify_dummy_report, args=(" Added a new success phrase!", 3, initial_file_path))
    modify_thread.start()
    found_file_modified = watcher.wait_for_report("new success phrase!", timeout=10)
    print(f"Result for Test Case 3: {found_file_modified}")
    if found_file_modified:
        os.remove(found_file_modified) # Clean up
    modify_thread.join()

    # Clean up the test directory
    if os.path.exists("test_reports/"):
        os.rmdir("test_reports/")
