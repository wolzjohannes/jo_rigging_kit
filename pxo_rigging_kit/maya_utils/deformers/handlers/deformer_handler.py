import traceback
import queue
import threading
import sys
import select
from typing import List, Dict, Any, Tuple, Iterable, Callable
from dataclasses import dataclass
import logging

# Import built-in modules
from builtins import str


# Import third-party modules
from maya.api import OpenMaya as om2  # noqa: import error

# Import local modules
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import exceptions
from pxo_rigging_kit.maya_utils.deformers.operators import skincluster_op
from pxo_rigging_kit.maya_utils.deformers.operators.deformer_op_base import DeformerOperator

##########################################################
# GLOBALS
##########################################################


_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.INFO)

DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

AVAILABLE_DEFORMER_OPERATORS = {
    "skin_cluster": skincluster_op.SkinClusterOperator,
    # Add more deformers here
}


# Quick method to just print something on error /i am loosing it <3


def format_step_error(operator, step_name, method, kwargs, exc):
    return (
        f"\n# --- STEP ERROR ----------------------------------------\n"
        f"# Operator:      {operator.transform_name}\n"
        f"# Step:          {step_name}\n"
        f"# Method:        {method.__qualname__}\n"
        f"# kwargs type:     {type(kwargs).__name__}\n"
        f"# kwargs value:    {kwargs}\n"
        f"# Exception:     {type(exc).__name__}: {exc}\n"
        f"# Traceback:\n{''.join(traceback.format_tb(exc.__traceback__))}"
        f"--------------------------------------------------------\n"
    )


# makes it easier to get the operation map (and we can even switch it to pydantic
# to always be correct in what we give, as i learned with fastAPI)
@dataclass
class OperationContext:
    """Summarizes what we want, like operation and additional parameters."""
    operation_type: str  # like import and export etc pp
    additional_arguments: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_arguments is None:
            self.additional_arguments = {}


# this we need to easily inject options
class DeformerOperationMap:
    """
    Defines step sequences for each operation type.
    Each step is a tuple: (method_name: str, args: dict)
    """

    def get_steps(self, context: OperationContext) -> List[Tuple[str, dict]]:
        args = context.additional_arguments or {}

        steps: Dict[str, List[Tuple[str, dict]]] = {
            "export": [
                ("gather_scene_internal_data", {}),
                ("export_data", args),
            ],
            "import": [
                ("gather_scene_external_data", {}),
                ("import_data", args),
            ],
            "prune": [
                ("rebuild_pruned", {}),
            ],
            "rename": [
                ("rename_deformer", {}),
            ],
            "kill": [
                ("gather_scene_internal_data", {}),
                ("kill_deformer", {}),
            ],

        }

        if context.operation_type not in steps:
            raise exceptions.DeformerHandlerError(
                f"Unsupported operation type: {context.operation_type}"
            )

        return steps[context.operation_type]


# Callbacks so we can use our UI and commandline?


class IOCallbacks:
    def __init__(
            self,
            main_progress=None,
            sub_progress=None,
            message=None,
            error=None,
            step_finished=None,
            finished=None,
            cancelled=None,
    ):
        self.main_progress = main_progress
        self.sub_progress = sub_progress
        self.message = message
        self.error = error
        self.step_finished = step_finished
        self.finished = finished
        self.cancelled = cancelled

    def emit_error(self, msg):
        if self.error:
            self.error(msg)

    def emit_step_finished(self, step_name):
        if self.step_finished:
            self.step_finished(step_name)

    def emit_finished(self):
        if self.finished:
            self.finished()

    def emit_cancelled(self):
        if self.cancelled:
            self.cancelled()


class ScriptEditorCallbacks(IOCallbacks):
    def __init__(self):
        # we only load what we want to be displayed
        super().__init__(
            main_progress=self._main_progress,
            sub_progress=self._sub_progress,
            message=self._message,
        )

    def _main_progress(self, pct, msg):
        _LOGGER.info(f"[Mainstep: {pct}%] {msg}")

    def _sub_progress(self, pct, msg):
        _LOGGER.info(f"[Substep:  {pct}%] {msg}")

    def _message(self, msg):
        _LOGGER.info(f"[Additional Info] {msg}")


# The actual deformer system, cheers

class DeformerOperatorManager:
    """Responsible for discovering and instantiating deformer operators lazily."""

    def __init__(self, transforms: List[str], available_ops: Dict[str, type]):
        self.transforms = transforms
        self.available_ops = available_ops

    @DECORATORS.x_timer
    def build(self) -> Iterable[Callable[[], DeformerOperator]]:
        """Yield factory callables that instantiate operators lazily."""

        if not self.transforms:
            raise exceptions.DeformerHandlerError("No transforms provided.")

        for transform in self.transforms:
            for key, op_cls in self.available_ops.items():

                if hasattr(op_cls, "is_valid_for") and not op_cls.is_valid_for(transform):
                    continue

                def factory(op_cls=op_cls,
                            transform=transform
                            ):

                    return op_cls(transform)

                yield factory


class OperatorPrefetcher:
    """Prefetches operators one ahead using background threads."""

    def __init__(self,
                 factories: List[Callable[[], DeformerOperator]]
                 ):

        self.factories = factories
        self.total = len(factories)
        self.index = 0

        self._queue = queue.Queue(maxsize=1)
        self._prefetch_thread = None

        self._start_prefetch()

    def _start_prefetch(self):
        if self.index >= self.total:
            return

        factory = self.factories[self.index]

        def run():
            try:
                op = factory()
                self._queue.put(op)
            except Exception as e:
                self._queue.put(e)

        self._prefetch_thread = threading.Thread(target=run,
                                                 daemon=True,
                                                 )
        self._prefetch_thread.start()

    def get_next(self):
        """Blocks until the prefetched operator is ready, then starts prefetching the next."""
        if self.index >= self.total:
            return None

        result = self._queue.get()
        self.index += 1

        # Start prefetching the next operator
        self._start_prefetch()

        if isinstance(result, Exception):
            raise result

        return result


class DeformerTaskRunner:
    """Step-based executor with retry/skip logic and ESC cancellation."""

    def __init__(
        self,
        operators: Iterable[Callable[[], DeformerOperator]],
        context: OperationContext,
        step_map: List[Tuple[str, dict]],
        max_retries: int = 2,
    ):
        # Convert factories to list (cheap)
        factories = list(operators)
        if not factories:
            raise exceptions.DeformerHandlerError(
                "No valid deformers found for given transforms."
            )

        self.prefetcher = OperatorPrefetcher(factories)
        self.total = self.prefetcher.total

        self.context = context
        self.step_map = step_map

        self.max_retries = max_retries
        self.current_retries = 0

        self.index = 0
        self.substep = 0
        self.cancel_requested = False

        self.current_operator = None

        _LOGGER.info("task runner initialized")

    def _load_next_operator(self):
        """Get the next operator from the prefetcher."""
        op = self.prefetcher.get_next()
        self.current_operator = op
        return op is not None

    def has_more_work(self) -> bool:
        return self.index < self.total

    def run_step(self, callbacks: IOCallbacks) -> bool:
        self._assert_main_thread()

        if self.cancel_requested:
            callbacks.message("Operation cancelled.")
            callbacks.emit_cancelled()
            return False

        # Lazy load operator
        if self.current_operator is None:
            if not self._load_next_operator():
                callbacks.message("All operations completed.")
                callbacks.emit_finished()
                return False

        op = self.current_operator
        method_name, kwargs = self.step_map[self.substep]
        method = getattr(op, method_name)

        # Sub-progress
        if callbacks.sub_progress:
            pct = int(((self.substep + 1) / len(self.step_map)) * 100)
            callbacks.sub_progress(
                pct,
                f"Transform: {op.deformer_operator_name} "
                f"Deformer:{op.deformer_name} "
                f"Step: {method_name}"
            )

        # Execute step
        try:
            method(**(kwargs or {}))
            self.current_retries = 0
            callbacks.emit_step_finished(method_name)

        except Exception as e:
            detailed = format_step_error(
                operator=op,
                step_name=method_name,
                method=method,
                kwargs=kwargs,
                exc=e,
            )
            _LOGGER.error(detailed)
            callbacks.message(f"Error in {op.deformer_name}: {e}")
            callbacks.emit_error(f"{op.deformer_name}: {method_name}")

            if self.current_retries < self.max_retries:
                self.current_retries += 1
                _LOGGER.warning(
                    f"Retry {self.current_retries}/{self.max_retries} "
                    f"for {op.deformer_name} on step '{method_name}'"
                )
                return True

            # Skip operator
            _LOGGER.error(f"Skipping {op.deformer_name} after repeated failures.")
            callbacks.message(f"Skipping {op.deformer_name} after repeated failures.")

            self.current_retries = 0
            self.substep = 0
            self.index += 1
            self.current_operator = None
            self._update_main_progress(callbacks)
            return self.has_more_work()

        # Advance step
        self.substep += 1

        if self.substep >= len(self.step_map):
            self.substep = 0
            self.index += 1
            self.current_operator = None
            self._update_main_progress(callbacks)

            if self.check_for_escape():
                _LOGGER.warning("ESC detected — cancelling operation.")
                callbacks.message("Operation cancelled by ESC.")
                callbacks.emit_cancelled()
                self.cancel_requested = True
                return False

        return self.has_more_work()

    def _update_main_progress(self, callbacks: IOCallbacks):
        if not callbacks.main_progress:
            return

        pct = int((self.index / self.total) * 100)
        name = (
            self.current_operator.deformer_name
            if self.current_operator is not None
            else ""
        )
        callbacks.main_progress(pct, f"Processed {name}")



    @staticmethod
    def _assert_main_thread():
        try:
            om2.MGlobal.getActiveSelectionList()
        except Exception as e:
            raise RuntimeError(
                "OpenMaya 2.0 call failed — not running on the main thread.\n"
                f"Error: {e}"
            )

    # ESC detection
    def check_for_escape(self) -> bool:
        stdin = sys.stdin
        if not hasattr(stdin, "isatty"):
            return False
        if not stdin.isatty():
            return False
        dr, _, _ = select.select([stdin], [], [], 0)
        if dr:
            ch = stdin.read(1)
            if ch == "\x1b":
                return True
        return False


class DeformerHandler:
    """Wires it all together."""

    def __init__(self,
                 transforms: List[str],
                 operation_type: str,
                 deformer_type: str,
                 additional_arguments=None,
                 esc_listener=None,
                 ):

        self.esc_listener = esc_listener

        if additional_arguments is None:
            additional_arguments = {}

        if deformer_type not in AVAILABLE_DEFORMER_OPERATORS:
            raise exceptions.DeformerHandlerError(
                f"Unknown deformer type '{deformer_type}'. "
                f"Available: {list(AVAILABLE_DEFORMER_OPERATORS.keys())}"
            )

        self.context = OperationContext(
            operation_type=operation_type,
            additional_arguments=additional_arguments,
        )

        manager = DeformerOperatorManager(
            transforms=transforms,
            available_ops={deformer_type: AVAILABLE_DEFORMER_OPERATORS[deformer_type]},
        )

        operators = manager.build()

        op_map = DeformerOperationMap()
        steps = op_map.get_steps(self.context)

        self.runner = DeformerTaskRunner(
            operators=operators,
            context=self.context,
            step_map=steps,
        )

    @property
    def cancel_requested(self):
        return self.runner.cancel_requested

    def request_cancel(self):
        self.runner.request_cancel()

    def has_more_work(self):
        return self.runner.has_more_work()

    def run_step(self, callbacks):
        return self.runner.run_step(callbacks)


# maya entry points
def run_deformer_handler_no_ui(transforms: List[str],
                               operation: str,
                               deformer_type: str,
                               additional_parameters: Dict | None = None,
                               ):
    """

    Args:
        transforms:
        operation:
        deformer_type:
        additional_parameters:

    Returns:

    """
    handler = DeformerHandler(
        transforms=transforms,
        operation_type=operation,
        deformer_type=deformer_type,
        additional_arguments=additional_parameters or {},
    )

    callbacks = ScriptEditorCallbacks()

    while handler.has_more_work():
        try:
            keep_going = handler.run_step(callbacks)
            if not keep_going:
                break

        except KeyboardInterrupt:
            _LOGGER.warning("ESC pressed — cancelling operation.")
            handler.request_cancel()
            break

    _LOGGER.info("ScriptEditor operation finished.")



