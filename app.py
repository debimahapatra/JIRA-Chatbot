import streamlit as st
from dotenv import load_dotenv
from jira_utils import validate_project_key, create_issue
from claude_utils import get_next_epic, get_stories_for_epic

load_dotenv()

st.set_page_config(page_title="JIRA AI Chatbot", layout="wide")
st.title("🤖 JIRA AI Chatbot")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "project_key" not in st.session_state:
    st.session_state.project_key = None
if "epic_queue" not in st.session_state:
    st.session_state.epic_queue = []
if "story_queue" not in st.session_state:
    st.session_state.story_queue = []
if "current_epic" not in st.session_state:
    st.session_state.current_epic = None
if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False
if "current_story_index" not in st.session_state:
    st.session_state.current_story_index = 0
if "mode" not in st.session_state:
    st.session_state.mode = "idle"
if "last_user_input" not in st.session_state:
    st.session_state.last_user_input = ""
if "input_type" not in st.session_state:
    st.session_state.input_type = "project_key"  # New state to track what input we're expecting
if "needs_next_epic" not in st.session_state:
    st.session_state.needs_next_epic = False

# Display message history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Check if we need to process the next epic immediately (outside of user input flow)
if st.session_state.needs_next_epic:
    st.session_state.needs_next_epic = False
    st.session_state.current_story_index = 0
    st.session_state.story_queue = []
    
    # If there are more epics, process the next one
    if st.session_state.epic_queue:
        st.session_state.current_epic = st.session_state.epic_queue.pop(0)
        epic = st.session_state.current_epic
        st.session_state.story_queue = get_stories_for_epic(epic, epic.get("description", ""))
        st.session_state.current_story_index = 0
        epic_msg = f"### 📘 Epic: {epic['summary']}\n{epic['description']}\n\nShall I proceed?"
        st.session_state.messages.append({"role": "assistant", "content": epic_msg})
        with st.chat_message("assistant"):
            st.markdown(epic_msg)
        st.session_state.mode = "epic_confirm"
    else:
        st.session_state.mode = "idle"
        completion_msg = "🎉 All epics and stories reviewed."
        st.session_state.messages.append({"role": "assistant", "content": completion_msg})
        with st.chat_message("assistant"):
            st.markdown(completion_msg)
    st.rerun()

# Ask for JIRA Project Key if not yet provided
if not st.session_state.project_key:
    # Only show assistant message if it's not already in the messages
    if not any(msg["role"] == "assistant" and "Please enter your JIRA project key" in msg["content"] 
               for msg in st.session_state.messages):
        with st.chat_message("assistant"):
            st.markdown("Please enter your JIRA project key to get started.")
            st.session_state.messages.append({"role": "assistant", "content": "Please enter your JIRA project key to get started."})
    
    # Only show Project Key input when we need it
    user_key = st.chat_input("Enter your JIRA Project Key")
    
    if user_key:
        st.session_state.messages.append({"role": "user", "content": user_key})
        with st.chat_message("user"):
            st.markdown(user_key)
            
        if validate_project_key(user_key):
            st.session_state.project_key = user_key
            st.session_state.input_type = "requirements"
            with st.chat_message("assistant"):
                success_msg = f"✅ Project key **{user_key}** validated. Now send me your product requirements."
                st.markdown(success_msg)
                st.session_state.messages.append({"role": "assistant", "content": success_msg})
        else:
            with st.chat_message("assistant"):
                error_msg = "❌ Invalid project key. Please try again."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        st.rerun()
else:
    # Different input prompts based on the current mode
    input_prompt = "Paste your product requirements here..."
    if st.session_state.mode in ["epic_confirm", "story_confirm"]:
        input_prompt = "Type YES or NO to proceed with the current item..."

    # Chat input - only show when appropriate
    user_input = st.chat_input(input_prompt)
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.last_user_input = user_input

        # Handle epic confirmation
        if st.session_state.mode == "epic_confirm":
            if user_input.strip().lower() == "yes":
                epic = st.session_state.current_epic
                epic_key = create_issue(
                    project_key=st.session_state.project_key,
                    summary=epic['summary'],
                    description=epic['description'],
                    issue_type="Epic"
                )
                st.session_state.current_epic["key"] = epic_key
                success_msg = f"✅ Epic created: {epic_key}"
                st.session_state.messages.append({"role": "assistant", "content": success_msg})
                with st.chat_message("assistant"):
                    st.markdown(success_msg)

                if st.session_state.story_queue:
                    story = st.session_state.story_queue[st.session_state.current_story_index]
                    story_msg = f"#### 📝 Story: {story['summary']}\n{story['description']}\n\nShall I proceed?"
                    st.session_state.messages.append({"role": "assistant", "content": story_msg})
                    with st.chat_message("assistant"):
                        st.markdown(story_msg)
                    st.session_state.mode = "story_confirm"
                else:
                    st.session_state.needs_next_epic = True
            else:
                skip_msg = "❌ Skipped epic."
                st.session_state.messages.append({"role": "assistant", "content": skip_msg})
                with st.chat_message("assistant"):
                    st.markdown(skip_msg)
                st.session_state.needs_next_epic = True
            st.rerun()

        # Handle story confirmation
        elif st.session_state.mode == "story_confirm":
            if user_input.strip().lower() == "yes":
                story = st.session_state.story_queue[st.session_state.current_story_index]
                story_key = create_issue(
                    project_key=st.session_state.project_key,
                    summary=story['summary'],
                    description=story['description'],
                    issue_type="Story",
                    parent_key=st.session_state.current_epic.get("key")
                )
                success_msg = f"✅ Story created: {story_key}"
                st.session_state.messages.append({"role": "assistant", "content": success_msg})
                with st.chat_message("assistant"):
                    st.markdown(success_msg)
            else:
                skip_msg = "❌ Skipped story."
                st.session_state.messages.append({"role": "assistant", "content": skip_msg})
                with st.chat_message("assistant"):
                    st.markdown(skip_msg)

            st.session_state.current_story_index += 1
            if st.session_state.current_story_index < len(st.session_state.story_queue):
                story = st.session_state.story_queue[st.session_state.current_story_index]
                story_msg = f"#### 📝 Story: {story['summary']}\n{story['description']}\n\nShall I proceed?"
                st.session_state.messages.append({"role": "assistant", "content": story_msg})
                with st.chat_message("assistant"):
                    st.markdown(story_msg)
            else:
                # All stories for this epic are done, move to next epic
                st.session_state.needs_next_epic = True
            st.rerun()

        # New requirements
        elif st.session_state.mode == "idle":
            with st.spinner("Thinking through your requirements and breaking them into epics..."):
                epics = get_next_epic(user_input)
                if not epics:
                    error_msg = "❌ Claude couldn't extract any epics."
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)
                    st.rerun()
                    
                st.session_state.epic_queue.extend(epics)
                epics_msg = f"📘 Found **{len(epics)}** epics. Starting with the first one..."
                st.session_state.messages.append({"role": "assistant", "content": epics_msg})
                with st.chat_message("assistant"):
                    st.markdown(epics_msg)
                
                # Start next epic
                st.session_state.current_epic = st.session_state.epic_queue.pop(0)
                epic = st.session_state.current_epic
                st.session_state.story_queue = get_stories_for_epic(epic, epic.get("description", ""))
                st.session_state.current_story_index = 0
                epic_msg = f"### 📘 Epic: {epic['summary']}\n{epic['description']}\n\nShall I proceed?"
                st.session_state.messages.append({"role": "assistant", "content": epic_msg})
                with st.chat_message("assistant"):
                    st.markdown(epic_msg)
                st.session_state.mode = "epic_confirm"
                st.rerun()