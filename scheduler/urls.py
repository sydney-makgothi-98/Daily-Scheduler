from django.urls import path

from . import views

urlpatterns = [
    path("", views.stats, name="queues_home"),
    path("stats.json", views.stats_json, name="queues_home_json"),
    path("queues/<str:queue_name>/workers/", views.queue_workers, name="queue_workers"),
    path("queues/<str:queue_name>/<str:registry_name>/jobs", views.list_registry_jobs, name="queue_registry_jobs"),
    path(
        "queues/<str:queue_name>/<str:registry_name>/<str:action>/",
        views.queue_registry_actions,
        name="queue_registry_action",
    ),
    path("queues/<str:queue_name>/confirm-action/", views.queue_confirm_job_action, name="queue_confirm_job_action"),
    path("queues/<str:queue_name>/actions/", views.queue_job_actions, name="queue_job_actions"),
]

urlpatterns += [
    path("workers/", views.workers_list, name="workers_home"),
    path("workers/<str:name>/", views.worker_details, name="worker_details"),
    path("jobs/<str:job_name>/", views.job_detail, name="job_details"),
    path("jobs/<str:job_name>/<str:action>/", views.job_action, name="job_detail_action"),
]

urlpatterns += [
    path("prayers/", views.prayer_settings, name="prayer_settings"),
    path("prayers/api/", views.get_prayer_times_api, name="prayer_times_api"),
    path("prayers/create/", views.create_prayer, name="create_prayer"),
    path("prayers/<int:prayer_id>/update/", views.update_prayer, name="update_prayer"),
    path("prayers/<int:prayer_id>/delete/", views.delete_prayer, name="delete_prayer"),
]

urlpatterns += [
    path("calendar/", views.calendar_view, name="calendar_view"),
    path("calendar/<int:year>/<int:month>/<int:day>/", views.task_data_view, name="task_data_view"),
    path("calendar/<int:year>/<int:month>/<int:day>/create/", views.create_personal_task, name="create_personal_task"),
    path("tasks/<int:task_id>/edit/", views.edit_personal_task, name="edit_personal_task"),
    path("tasks/<int:task_id>/delete/", views.delete_personal_task, name="delete_personal_task"),
    path("api/tasks/<int:task_id>/toggle/", views.toggle_task_completion, name="toggle_task_completion"),
    path("api/tasks/<int:year>/<int:month>/<int:day>/", views.get_tasks_by_date_api, name="get_tasks_api"),
]

urlpatterns += [
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("api/analytics/chart-data/", views.get_chart_data_api, name="get_chart_data_api"),
]
