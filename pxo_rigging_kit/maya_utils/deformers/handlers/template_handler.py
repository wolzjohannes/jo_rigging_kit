
from abc import ABC, abstractmethod

class IOCallbacksBase(ABC):
    """
    Abstract callback interface for IO pipelines.
    Concrete UIs implement these methods.
    """


    @abstractmethod
    def main_progress(self, value: int, message: str = ""):
        """Update the main progress bar."""
        pass

    @abstractmethod
    def sub_progress(self, value: int, message: str = ""):
        """Update the sub progress bar."""
        pass


    @abstractmethod
    def message(self, text: str):
        """Display a status message."""
        pass

    @abstractmethod
    def error(self, text: str):
        """Display an error message."""
        pass


    @abstractmethod
    def step_finished(self, step_name: str):
        """Called when a pipeline step completes."""
        pass

    @abstractmethod
    def finished(self):
        """Called when the entire pipeline completes."""
        pass

    @abstractmethod
    def cancelled(self):
        """Called when the pipeline is cancelled."""
        pass


class IOHandlerBase(ABC):
    """
    Abstract template for any IO pipeline.
    Concrete subclasses implement the actual work.
    """

    def __init__(self, items):
        self.items = items
        self.index = 0
        self.cancel_requested = False
        self._assert_main_thread()


    @abstractmethod
    def initialize(self):
        """Prepare operators or resources."""
        pass

    @abstractmethod
    def process_item(self, item, callbacks, **kwargs):
        """Process a single item."""
        pass


    def on_start(self, callbacks):
        """Called once before processing begins."""
        pass

    def on_finish(self, callbacks):
        """Called once after all work is done."""
        pass

    def on_cancel(self, callbacks):
        """Called if cancel is requested."""
        pass

    def request_cancel(self):
        self.cancel_requested = True

    def has_more_work(self):
        return self.index < len(self.items)

    def run_step(self, callbacks: IOCallbacksBase, **kwargs):
        """
        Template method that defines the pipeline flow.
        Subclasses only implement the abstract hooks.
        """

        self._assert_main_thread()

        # First-time initialization
        if self.index == 0:
            callbacks.message("Initializing...")
            self.initialize()
            self.on_start(callbacks)

        # Cancel?
        if self.cancel_requested:
            callbacks.message("Operation cancelled.")
            self.on_cancel(callbacks)
            return False

        # Finished?
        if not self.has_more_work():
            callbacks.message("All operations completed.")
            self.on_finish(callbacks)
            return False

        # Process one item
        item = self.items[self.index]
        pct = int((self.index / len(self.items)) * 100)

        callbacks.main_progress(pct, f"Processing {item}")
        self.process_item(item, callbacks, **kwargs)

        self.index += 1
        return self.has_more_work()


    def _assert_main_thread(self):
        try:
            om2.MGlobal.getActiveSelectionList()
        except Exception as e:
            raise RuntimeError(
                "Importer is NOT running on the main thread.\n"
                f"Error: {e}"
            )

