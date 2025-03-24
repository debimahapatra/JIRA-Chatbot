#Claude API wrapper

import os
import anthropic
import json
from dotenv import load_dotenv
import re

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

# Load prompt templates from external files
def load_prompt(file_path):
    with open(file_path, "r") as f:
        return f.read()

EPIC_PROMPT = load_prompt("prompts/epic_prompt.txt")
STORY_PROMPT = load_prompt("prompts/story_prompt.txt")

# Clean Claude's markdown-wrapped JSON response
def clean_claude_json_block(raw_text):
    if raw_text.startswith("```"):
        lines = raw_text.strip().splitlines()
        if lines[0].startswith("```") and lines[-1] == "```":
            lines = lines[1:-1]
        raw_text = "\n".join(lines).strip()
    return raw_text

def get_next_epic(requirements):
    msg = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4096,
        temperature=0.5,
        messages=[
            {
                "role": "user",
                "content": EPIC_PROMPT + requirements
            }
        ]
    )

    raw = msg.content[0].text
    print("🧾 Claude raw response:", raw)
    cleaned = clean_claude_json_block(raw)

    try:
        response = json.loads(cleaned)
        return response
    except Exception as e:
        print("❌ Error parsing cleaned epic response:", e)
        return []

def get_stories_for_epic(epic, requirements):
    epic_summary = epic["summary"]
    filled_prompt = STORY_PROMPT.replace("{epic}", epic_summary).replace("{requirements}", requirements)

    # Claude call
    msg = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4096,
        temperature=0.5,
        messages=[{"role": "user", "content": filled_prompt}]
    )

    raw = msg.content[0].text
    cleaned = clean_claude_json_block(raw)
    return json.loads(cleaned)
