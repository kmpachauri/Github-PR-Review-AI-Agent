from app.tasks.worker import celery_app

print("Registered tasks:")
for task_name in celery_app.tasks.keys():
    print(task_name)
