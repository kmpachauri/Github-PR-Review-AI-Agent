from app.llms.openrouter_llm import OpenRouterLLM
from app.tasks.worker import celery_app
from app.core.utils import save_result
from app.core.config import settings
import requests
import json
from app.core.logging import setup_logger

logger = setup_logger()

@celery_app.task(name="app.tasks.analyzer.analyze_pull_request")
def analyze_pull_request(repo_url, pr_number, github_token=None):
    from celery import current_task
    
    task_id = current_task.request.id

    # Fetch PR files
    headers = {
        "Authorization": f"token {github_token}" if github_token else "",
        "Accept": "application/vnd.github.v3+json"
    }
    owner_repo = repo_url.replace("https://github.com/", "")
    files_url = f"{settings.GITHUB_API_BASE}/repos/{owner_repo}/pulls/{pr_number}/files"

    try:
        logger.info("🔍 Starting analysis", extra={"task_id": task_id})
        response = requests.get(files_url, headers=headers)
        response.raise_for_status()
        files = response.json()
    except Exception as e:
        logger.error("❌ GitHub API error", extra={"task_id": task_id, "error_message": str(e)})
        save_result(task_id, {"task_id": task_id, "status": "failed", "error": f"GitHub API error: {str(e)}"})
        return

    # Prepare input for AI agent
    input_files = []
    for file in files:
        patch = file.get("patch")
        if patch:
            input_files.append(f"File: {file['filename']}\nPatch:\n{patch}\n\n")

    if not input_files:
        save_result(task_id, {"task_id": task_id, "status": "failed", "error": "No valid file changes found."})
        return

    prompt = (
        "You are a senior code review assistant.\n\n"
        "Analyze the following code changes according to these : "
        "- Code style and formatting issues"
        "- Potential bugs or errors"
        "- Performance improvements"
        "- Best practices" 
        "and return a structured JSON with:\n"
        "- filename\n"
        "- line number (if available)\n"
        "- type \n"
        "- description\n"
        "- suggestion\n\n"
        "Respond ONLY in JSON using this format:\n\n"
        "{\n"
        "  \"files\": [\n"
        "    {\n"
        "      \"name\": \"file.py\",\n"
        "      \"issues\": [\n"
        "        {\n"
        "          \"type\": \"style\",\n"
        "          \"line\": 10,\n"
        "          \"description\": \"Line too long\",\n"
        "          \"suggestion\": \"Break line into multiple lines\"\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Code changes:\n" + "\n".join(input_files)
    )



    llm_client = OpenRouterLLM(
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.MODEL_NAME  
    )


    try:
        logger.info("💬 Sending request to AI", extra={"task_id": task_id})
        result_text = llm_client.call(prompt)

        parsed_result = json.loads(result_text)

        total_files = len(parsed_result.get("files", []))
        total_issues = sum(len(f.get("issues", [])) for f in parsed_result.get("files", []))
        critical_issues = sum(
            1 for f in parsed_result.get("files", []) for i in f.get("issues", []) if i.get("type") == "bug"
        )

        final_result = {
            "task_id": task_id,
            "status": "completed",
            "results": {
                **parsed_result,
                "summary": {
                    "total_files": total_files,
                    "total_issues": total_issues,
                    "critical_issues": critical_issues,
                },
            },
        }

        save_result(task_id, final_result)

        logger.info(
            "✅ Analysis completed",
            extra={"task_id": task_id, "total_files": total_files, "total_issues": total_issues, "critical_issues": critical_issues},
        )

    except Exception as e:
        logger.error("❌ AI processing error", extra={"task_id": task_id, "error_message": str(e)})
        save_result(task_id, {"task_id": task_id, "status": "failed", "error": f"AI call failed: {str(e)}"})
