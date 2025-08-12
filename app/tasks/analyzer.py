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


    # --- Step 1: Fetch PR files ---
    headers = {
        "Authorization": f"token {github_token}" if github_token else "",
        "Accept": "application/vnd.github.v3+json"
    }
    owner_repo = repo_url.replace("https://github.com/", "")
    files_url = f"{settings.GITHUB_API_BASE}/repos/{owner_repo}/pulls/{pr_number}/files"


    try:
        logger.info("🔍 Starting analysis", extra={"task_id": task_id, "repo_url": repo_url, "pr_number": pr_number})
        response = requests.get(files_url, headers=headers)
        response.raise_for_status()
        files = response.json()
    except Exception as e:
        logger.error("❌ GitHub API error", extra={"task_id": task_id, "error_message": str(e)})
        save_result(task_id, {
            "task_id": task_id,
            "status": "failed",
            "error": f"GitHub API error: {str(e)}"
        })
        return

    # --- Step 2: Build input for AI ---
    input_files = []
    for file in files:
        filename = file["filename"]
        patch = file.get("patch", "")
        if patch:  # Skip binary or unchanged files
            input_files.append(f"File: {filename}\nPatch:\n{patch}\n\n")

    if not input_files:
        save_result(task_id, {
            "task_id": task_id,
            "status": "failed",
            "error": "No valid file changes found to analyze."
        })
        return

    prompt = (
        "You are a code review assistant.\n\n"
        "Analyze the following code changes according to these : "
        "- Code style and formatting issues"
        "- Potential bugs or errors"
        "- Performance improvements"
        "- Best practices" 
        "and return a structured JSON with:\n"
        "- filename\n"
        "- line number (if available)\n"
        "- type (style, bug, performance, best_practice)\n"
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

    try:
        logger.info("💬 Sending request to AI", extra={"task_id": task_id})
        ai_response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.MODEL_NAME,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )
        ai_response.raise_for_status()

        result_text = ai_response.json()["choices"][0]["message"]["content"]

        try:
            parsed_result = json.loads(result_text)
        except Exception as e:
            logger.error("⚠️ Failed to parse AI response", extra={"task_id": task_id, "error_message": str(e)})
            save_result(task_id, {
                "task_id": task_id,
                "status": "failed",
                "error": f"Failed to parse AI response: {str(e)}",
                "raw_response": result_text  
            })
            return 


        total_files = len(parsed_result.get("files", []))
        total_issues = sum(len(f.get("issues", [])) for f in parsed_result.get("files", []))
        critical_issues = sum(
            1 for f in parsed_result.get("files", [])
            for i in f.get("issues", []) if i.get("type") == "bug"
        )

        final_result = {
            "task_id": task_id,
            "status": "completed",
            "results": {
                **parsed_result,
                "summary": {
                    "total_files": total_files,
                    "total_issues": total_issues,
                    "critical_issues": critical_issues
                }
            }
        }


        save_result(task_id, final_result)
        return final_result
    
        logger.info("✅ Analysis completed", extra={
            "task_id": task_id,
            "total_files": total_files,
            "total_issues": total_issues,
            "critical_issues": critical_issues
        })

    except Exception as e:
        save_result(task_id, {
            "task_id": task_id,
            "status": "failed",
            "error": f"AI call failed: {str(e)}"
        })
        return
