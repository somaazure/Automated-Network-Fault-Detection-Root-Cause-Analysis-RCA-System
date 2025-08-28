import os
import streamlit as st
from dotenv import load_dotenv
from storage.rca_vector_store import RCAVectorStore
from storage.log_processor import LogProcessor
import pandas as pd
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv(override=True)

# Directories
LOGS_DIR = os.path.join(os.getcwd(), "logs")
RCA_DIR = os.path.join(os.getcwd(), "rca_reports")

# Initialize Log Processor and Vector Store
log_processor = LogProcessor()
vector_store = RCAVectorStore()

# Streamlit page config
st.set_page_config(
    page_title="Network Fault Detection Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📊 Analytics", "📂 RCA Management", "🔍 RCA Search"]
)


# ------------------- RCA MANAGEMENT TAB -------------------
def render_rca_management():
    st.title("🧠 RCA Management")
    st.write("Logs are automatically processed and indexed into Pinecone.")

    # 1. Process logs into RCA reports automatically
    reports_generated = log_processor.process_logs(LOGS_DIR, RCA_DIR)

    if reports_generated:
        st.success(f"✅ {reports_generated} new RCA reports generated!")
    else:
        st.info("No new logs found to process.")

    # 2. Auto-chunk RCA reports and push to Pinecone
    msg = vector_store.chunk_and_store_reports(RCA_DIR)
    st.info(msg)

    # 3. Show RCA reports preview
    st.subheader("📄 Recent RCA Reports")
    if os.path.exists(RCA_DIR):
        reports = sorted(os.listdir(RCA_DIR), reverse=True)
        for report in reports[:5]:
            with open(os.path.join(RCA_DIR, report), "r", encoding="utf-8") as f:
                st.markdown(f"**{report}**")
                st.code(f.read()[:500] + " ...")
    else:
        st.warning("No RCA reports found yet!")


# ------------------- RCA SEARCH TAB -------------------
def render_rca_search():
    st.title("🔍 Search RCA Knowledge Base")
    query = st.text_input("Enter your RCA-related query:")

    if query:
        try:
            rag = vector_store.answer_query(query, top_k=5)
            st.subheader("🧠 Consolidated Answer")
            st.write(rag.get("answer", ""))

            sources = rag.get("sources", [])
            if sources:
                st.markdown("**Sources:** " + ", ".join(sources))

            with st.expander("Show retrieved chunks"):
                results = vector_store.search_similar(query)
                if results:
                    for match in results:
                        score = match["score"]
                        source = match["metadata"].get("source", "Unknown")
                        st.markdown(f"**Source:** {source} | **Relevance:** {score:.2f}")
                        st.write(match["metadata"])
                else:
                    st.info("No relevant results found.")
        except Exception as e:
            st.error(f"Error searching Pinecone: {str(e)}")


# ------------------- ANALYTICS TAB -------------------
def render_analytics():
    st.title("📊 RCA Analytics Dashboard")

    # Generate a mock summary from RCA reports
    if not os.path.exists(RCA_DIR) or len(os.listdir(RCA_DIR)) == 0:
        st.warning("No RCA reports available for analytics.")
        return

    fault_counts = {}
    for file in os.listdir(RCA_DIR):
        if file.endswith(".txt"):
            with open(os.path.join(RCA_DIR, file), "r", encoding="utf-8") as f:
                content = f.read()
                if "network" in content.lower():
                    fault_counts["Network"] = fault_counts.get("Network", 0) + 1
                if "hardware" in content.lower():
                    fault_counts["Hardware"] = fault_counts.get("Hardware", 0) + 1
                if "software" in content.lower():
                    fault_counts["Software"] = fault_counts.get("Software", 0) + 1

    if not fault_counts:
        st.info("No specific fault categories detected in RCA reports.")
        return

    df = pd.DataFrame(list(fault_counts.items()), columns=["Fault Type", "Count"])

    st.bar_chart(df.set_index("Fault Type"))

    st.subheader("📄 RCA Insights")
    st.write(df)


# ------------------- ROUTER -------------------
if page == "📂 RCA Management":
    render_rca_management()
elif page == "🔍 RCA Search":
    render_rca_search()
else:
    render_analytics()
