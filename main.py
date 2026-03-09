import asyncio
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any
import os

import streamlit as st

from agent import agent

# ─────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────
st.set_page_config(page_title="Productivity Pro", page_icon="🤖", layout="wide")

st.title("🤖 Productivity Pro")
st.caption("Your personal productivity assistant")

# ─────────────────────────────────────────────
# Session state initialization
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content}]

if "trace" not in st.session_state:
    st.session_state.trace = []  # [{tool, args, result}]

if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None  # {type, data}

if "message_history" not in st.session_state:
    # PydanticAI message history for multi-turn
    st.session_state.message_history = []


# ─────────────────────────────────────────────
# Layout: two columns
# ─────────────────────────────────────────────
chat_col, trace_col = st.columns([2, 1])

# ─────────────────────────────────────────────
# TRACE PANEL (right column)
# ─────────────────────────────────────────────
with trace_col:
    st.subheader("🔍 Execution Trace")
    st.caption("See exactly what the agent is doing")

    if not st.session_state.trace:
        st.info("Tool calls will appear here as the agent works.")
    else:
        for i, step in enumerate(reversed(st.session_state.trace)):
            with st.expander(f"🔧 {step['tool']}", expanded=(i == 0)):
                st.markdown("**Arguments:**")
                st.json(step["args"])
                st.markdown("**Result:**")
                st.json(step["result"])

# ─────────────────────────────────────────────
# CHAT PANEL (left column)
# ─────────────────────────────────────────────
with chat_col:
    st.subheader("💬 Chat")

    # Check for a likely placeholder or missing Gemini API key.
    # This prevents confusing runtime errors and instead shows clear guidance.
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_config_ok = bool(gemini_key) and "your_gemini_api_key_here" not in gemini_key

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Human-in-the-loop approval gate ──
    if st.session_state.pending_approval:
        approval = st.session_state.pending_approval
        st.warning("⚠️ **Agent is requesting approval before sending this email:**")

        with st.container(border=True):
            st.markdown(f"**To:** {approval['to']}")
            st.markdown(f"**Subject:** {approval['subject']}")
            st.markdown(f"**Body:**\n\n{approval['body']}")

        col1, col2, col3 = st.columns(3)

        if col1.button("✅ Approve & Send", type="primary"):
            from agent.tools.email_tool import send_email

            result = send_email(approval["to"], approval["subject"], approval["body"])
            st.session_state.trace.append(
                {
                    "tool": "send_email",
                    "args": {"to": approval["to"], "subject": approval["subject"]},
                    "result": result,
                }
            )
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"✅ Email sent to **{approval['to']}** with subject **'{approval['subject']}'**.",
                }
            )
            st.session_state.pending_approval = None
            st.rerun()

        if col2.button("✏️ Edit (coming soon)"):
            st.info("Edit mode: modify the draft above, then re-approve.")

        if col3.button("❌ Reject"):
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": "Understood — email was **not sent**. Let me know if you'd like to change anything.",
                }
            )
            st.session_state.pending_approval = None
            st.rerun()

    # ── Chat input ──
    user_input = None
    if not gemini_config_ok:
        st.warning(
            "The app is running, but a valid `GEMINI_API_KEY` is not configured.\n\n"
            "Update your `.env` file with a real Gemini API key to enable the assistant.\n\n"
            "You can still browse the UI, but chat will be disabled until this is fixed."
        )
    else:
        # If a quick-prompt button was clicked, immediately treat it as a
        # submitted user message on the next run. This gives the effect of
        # “click to send” instead of just storing text.
        prefill = st.session_state.pop("prefill", None)
        if prefill:
            user_input = prefill
        else:
            user_input = st.chat_input(
                "Ask me anything... e.g. 'What's on my calendar today?'"
            )

    if user_input:
        # Add user message to display
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Run the agent synchronously with a robust helper to
                    # avoid occasional \"Event loop is closed\" issues.
                    def _run_agent_sync(prompt: str, history: list[Any]):
                        try:
                            return asyncio.run(
                                agent.run(prompt, message_history=history)
                            )
                        except RuntimeError as e:
                            # In rare cases, the default loop can be in a bad/closed
                            # state between Streamlit reruns; create a fresh loop.
                            if "event loop is closed" in str(e).lower():
                                loop = asyncio.new_event_loop()
                                try:
                                    asyncio.set_event_loop(loop)
                                    return loop.run_until_complete(
                                        agent.run(prompt, message_history=history)
                                    )
                                finally:
                                    loop.close()
                                    asyncio.set_event_loop(None)
                            raise

                    result = _run_agent_sync(
                        user_input, st.session_state.message_history
                    )

                    # Update conversation history for next turn
                    st.session_state.message_history = result.all_messages()

                    # Extract tool calls from the result and add to trace
                    for msg in result.all_messages():
                        # PydanticAI exposes tool calls in message parts
                        if hasattr(msg, "parts"):
                            for part in msg.parts:
                                if hasattr(part, "tool_name"):
                                    st.session_state.trace.append(
                                        {
                                            "tool": part.tool_name,
                                            "args": getattr(part, "args", {}),
                                            "result": getattr(part, "content", {}),
                                        }
                                    )

                    # PydanticAI v0.0.14+ returns `AgentRunResult` with `.output`
                    # as the top-level model/text. Older code used `.data`.
                    response_text = getattr(result, "data", None) or result.output

                    # Check if the response contains a draft email awaiting approval
                    # The agent will include PENDING_APPROVAL in its draft_email response
                    # We detect this by checking if the last trace item is a draft
                    last_trace = (
                        st.session_state.trace[-1] if st.session_state.trace else None
                    )
                    if (
                        last_trace
                        and last_trace["tool"] == "tool_draft_email"
                        and isinstance(last_trace["result"], dict)
                        and last_trace["result"].get("status") == "PENDING_APPROVAL"
                    ):
                        draft = last_trace["result"]
                        st.session_state.pending_approval = {
                            "to": draft["to"],
                            "subject": draft["subject"],
                            "body": draft["body"],
                        }
                        response_text = (
                            f"I've drafted the email below. Please review it and approve before I send.\n\n"
                            f"**To:** {draft['to']}\n**Subject:** {draft['subject']}"
                        )

                    st.markdown(response_text)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text}
                    )

                except Exception as e:
                    error_msg = f"Sorry, something went wrong: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

        st.rerun()

# ─────────────────────────────────────────────
# Sidebar: quick actions & info
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚡ Quick Try")
    st.caption("Click to paste into chat:")

    quick_prompts = [
        "What's on my calendar today?",
        "Find Sarah's last email",
        "Draft a reply to Sarah saying I'll be 10 mins late",
        "Search for best jollof rice restaurants in Accra",
        "Save a note: Team meeting recap - discussed Q3 targets",
        "List my saved notes",
        "Am I free tomorrow at 2pm?",
    ]

    for prompt in quick_prompts:
        if st.button(prompt, use_container_width=True):
            st.session_state["prefill"] = prompt

    st.divider()
    st.subheader("ℹ️ Agent Info")
    st.markdown(f"**Today:** {date.today().isoformat()}")
    st.markdown("**Model:** gemini-2.5-flash")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.trace = []
        st.session_state.message_history = []
        st.session_state.pending_approval = None
        st.rerun()
