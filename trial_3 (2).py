# -*- coding: utf-8 -*-
"""Trial 3.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1hnZ5KdJUx4yC4AJvEWprEMwJuTzbWu1U
"""

# imports and setup

import re
import datetime
import random
import pandas as pd
import dateparser
import streamlit as st
import os

# Simulated fine-tuned BERT model output
def simulate_bert_scores(message):
  # Placeholder for actual model inference
  urgency_score = random.uniform(0.3, 1.0)
  importance_score = random.uniform(0.3, 1.0)
  return urgency_score, importance_score

# Rule-based urgency score based on deadline proximity

def rule_based_urgency(message_date, deadline=None):
    if deadline:
        days_diff = (deadline - message_date).days
        if days_diff < 0:
            return 0.0
        elif days_diff <= 1:
            return 1.0
        elif days_diff <= 3:
            return 0.75
        elif days_diff <= 7:
            return 0.5
        else:
            return 0.25
    return 0.0

# Rule-based flags for urgency keywords
def rule_based_flags(message):
    keywords = ['urgent', 'asap', 'immediately', 'critical', 'important']
    score = 0.0
    for word in keywords:
        if re.search(rf'\b{word}\b', message, re.IGNORECASE):
            score += 0.3  # Increased weight per keyword
    return min(score, 1.0)

# Deadline Extraction (including relative dates)
def extract_deadline_from_message(message, reference_date):
    deadline_phrases = re.findall(
        r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})|(?:tomorrow|today|next\s+\w+|this\s+\w+|on\s+\w+day))\b',
        message,
        re.IGNORECASE
    )

    for phrase in deadline_phrases:
        parsed = dateparser.parse(phrase, settings={'RELATIVE_BASE': reference_date, 'PREFER_DATES_FROM': 'future'})
        if parsed:
            return parsed
    return None

def combine_scores(urgency_rule_score, urgency_flag_score, urgency_bert_score, importance_bert_score,
                   weight_rule=0.4, weight_bert=0.6):
    rule_total = min(urgency_rule_score + urgency_flag_score, 1.0)
    total_weight = weight_rule + weight_bert
    normalized_rule_weight = weight_rule / total_weight
    normalized_bert_weight = weight_bert / total_weight
    combined_urgency = normalized_rule_weight * rule_total + normalized_bert_weight * urgency_bert_score
    return min(combined_urgency, 1.0), importance_bert_score

def analyze_message(message, message_date):
    deadline = extract_deadline_from_message(message, message_date)
    urgency_rule_score = rule_based_urgency(message_date, deadline)
    urgency_flag_score = rule_based_flags(message)
    urgency_bert_score, importance_bert_score = simulate_bert_scores(message)
    final_urgency, final_importance = combine_scores(
        urgency_rule_score,
        urgency_flag_score,
        urgency_bert_score,
        importance_bert_score
    )
    escalate = final_urgency > 0.7 and final_importance > 0.7
    response = generate_response(final_urgency, final_importance, escalate)

    return {
        "date_sent": message_date,
        "message": message,
        "deadline": deadline,
        "project_name": "",  # placeholder for LLM
        "action": "",        # placeholder for LLM
        "status": "Not Started",
        "escalate": escalate,
        "response": response
    }

def generate_response(urgency, importance, escalate):
    if escalate:
        return "🚨 This message appears to be both urgent and important. Recommended action: escalate to your project lead or take immediate steps to address the issue."
    elif urgency > 0.5 or importance > 0.5:
        return "⚠️ This message has moderate urgency or importance. You may want to review it soon and follow up if needed."
    else:
        return "✅ This message does not require immediate attention. You can monitor it for now."

# Add a banner and title
st.markdown("""
    <div style="background-color:#003366;padding:10px;border-radius:5px">
        <h1 style="color:white;text-align:center;">📬 Cognizant Message Analyzer</h1>
    </div>
""", unsafe_allow_html=True)

# Create tabs with clearer names
tab1, tab2 = st.tabs(["📊 Urgency Calculator", "📋 Dashboard"])

with tab1:
    st.header("📊 Urgency Calculator")

    full_message_input = st.text_area("Paste the full message including any deadlines or urgency indicators:")
    message_date_input = st.date_input("Date the message was sent", datetime.date.today(), format="DD/MM/YYYY")

    analyze_button = st.button("Analyze")

    if analyze_button and full_message_input:
        message_date = datetime.datetime.combine(message_date_input, datetime.datetime.min.time())
        result = analyze_message(full_message_input, message_date)

        st.markdown(f"**Response:** {result['response']}")

        if "escalated_tasks" not in st.session_state:
            st.session_state.escalated_tasks = []

        if result["escalate"]:
            st.success("✅ Task added to dashboard.")
            st.session_state.escalated_tasks.append(result)

with tab2:
    st.header("📋 Escalated Tasks Dashboard")

    if "escalated_tasks" not in st.session_state or not st.session_state.escalated_tasks:
        st.info("No escalated tasks yet.")
    else:
        df = pd.DataFrame(st.session_state.escalated_tasks)

        # Format date columns
        df["Date of Message"] = pd.to_datetime(df["date_sent"]).dt.strftime("%d/%m/%Y")
        df["Deadline"] = pd.to_datetime(df["deadline"], errors="coerce").dt.strftime("%d/%m/%Y")

        # Drop unused columns
        df = df.drop(columns=["date_sent", "deadline", "response", "escalate"], errors="ignore")

        # Reorder and rename columns
        df = df.rename(columns={
            "message": "Message",
            "project_name": "Project Name",
            "action": "Action",
            "status": "Status"
        })

        # Filter by project name
        project_filter = st.selectbox("Filter by project", ["All"] + sorted(df["Project Name"].unique()))
        if project_filter != "All":
            df = df[df["Project Name"] == project_filter]

        # Status dropdown options
        status_options = ["Not Started", "In Progress", "Completed"]

        # Editable columns
        editable_cols = ["Project Name", "Action", "Deadline", "Status"]
        df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=status_options),
            },
            key="dashboard_editor"
        )

        # Row highlighting based on status
        def highlight_row(row):
            color = {
                "Not Started": "#ffe6e6",   # pale red
                "In Progress": "#fff5cc",   # pale yellow
                "Completed": "#e6ffe6"      # pale green
            }.get(row["Status"], "white")
            return [f"background-color: {color}"] * len(row)

        st.dataframe(df.style.apply(highlight_row, axis=1))