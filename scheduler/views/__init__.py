__all__ = [
    "get_statistics",
    "job_action",
    "job_detail",
    "list_registry_jobs",
    "queue_confirm_job_action",
    "queue_job_actions",
    "queue_registry_actions",
    "queue_workers",
    "stats",
    "stats_json",
    "worker_details",
    "workers_list",
    "prayer_settings",
    "get_prayer_times_api",
    "create_prayer",
    "update_prayer",
    "delete_prayer",
    "toggle_prayer_completion",
    "get_daily_prayer_completions",
    "get_prayer_stats",
    "calendar_view",
    "task_data_view",
    "get_tasks_by_date_api",
    "create_personal_task",
    "edit_personal_task",
    "delete_personal_task",
    "toggle_task_completion",
    "create_subtask",
    "toggle_subtask_completion",
    "delete_subtask",
    "get_task_subtasks",
    "analytics_dashboard",
    "get_chart_data_api",
    "get_subtask_chart_data_api",
    "get_prayer_chart_data_api",
]

from .job_views import job_action, job_detail
from .queue_job_actions import queue_confirm_job_action, queue_job_actions
from .queue_registry_actions import queue_registry_actions
from .queue_views import get_statistics, list_registry_jobs, queue_workers, stats, stats_json
from .worker_views import worker_details, workers_list
from .prayer_views import (
    prayer_settings,
    get_prayer_times_api,
    create_prayer,
    update_prayer,
    delete_prayer,
    toggle_prayer_completion,
    get_daily_prayer_completions,
    get_prayer_stats,
)
from .personal_task_views import (
    calendar_view,
    task_data_view,
    get_tasks_by_date_api,
    create_personal_task,
    edit_personal_task,
    delete_personal_task,
    toggle_task_completion,
    create_subtask,
    toggle_subtask_completion,
    delete_subtask,
    get_task_subtasks,
)
from .analytics_views import (
    analytics_dashboard,
    get_chart_data_api,
    get_subtask_chart_data_api,
    get_prayer_chart_data_api,
)
