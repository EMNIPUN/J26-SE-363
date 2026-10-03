# Import all task modules so the worker registers all agent tasks on startup.
from . import performance_tasks  # noqa: F401
from . import planning_tasks     # noqa: F401
from . import security_tasks     # noqa: F401
from . import tutor_tasks        # noqa: F401
