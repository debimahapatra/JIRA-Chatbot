from jira import JIRA
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to JIRA using credentials from .env
jira = JIRA(
    server=os.getenv("JIRA_URL"),
    basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
)

def validate_project_key(project_key):
    try:
        project = jira.project(project_key)
        return project is not None
    except:
        return False

def create_issue(project_key, summary, description, issue_type="Task", parent_key=None):
    issue_dict = {
        'project': { 'key': project_key },
        'summary': summary,
        'description': description,
        'issuetype': { 'name': issue_type },
    }

    # If this is a Story or Sub-task and has a parent (Epic), include it
    if parent_key and issue_type.lower() in ["story"]:
        issue_dict['parent'] = { 'key': parent_key }
    
    issue = jira.create_issue(fields=issue_dict)
    return issue.key
