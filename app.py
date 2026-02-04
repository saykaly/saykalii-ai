import streamlit as st
import streamlit_authenticator as stauth
import yaml
import pandas as pd
import plotly.express as px  # NEW: For interactive charts
from yaml.loader import SafeLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from markdown_pdf import MarkdownPdf, Section
from dotenv import load_dotenv
import io
import os

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="Tony's Data AI", layout="wide")

# Login System
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    with st.sidebar:
        st.title("Settings")
        authenticator.logout('Logout')
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    st.title(f"🚀 Tony's Business Dashboard")
    st.markdown("---")

    # --- FILE UPLOADER & DATA VISUALIZATION ---
    uploaded_file = st.file_uploader("📂 Upload your Excel or CSV file", type=["csv", "xlsx"])
    data_summary = "" 

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
            st.success(f"✅ Loaded {uploaded_file.name}")
            
            # Create two columns: one for data, one for charts
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Data Preview")
                st.dataframe(df.head(10))
            
            with col2:
                st.subheader("Quick Visualization")
                # Identify numeric columns for the Y-axis
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                all_cols = df.columns.tolist()
                
                if numeric_cols:
                    x_axis = st.selectbox("Select X-axis", all_cols)
                    y_axis = st.selectbox("Select Y-axis", numeric_cols)
                    
                    # Create the Plotly Chart
                    fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}", 
                                 color_discrete_sequence=['#00CC96'])
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.warning("No numerical data found for charting.")

            data_summary = f"The user uploaded a file with columns: {', '.join(df.columns)}. "
        except Exception as e:
            st.error(f"Error: {e}")

    # --- CHAT & REPORTING ---
    if not api_key:
        st.error("🔑 Missing GOOGLE_API_KEY!")
    else:
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
            if "messages" not in st.session_state: st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]): st.markdown(message["content"])

            if prompt := st.chat_input("Ask about your data..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    context = f"{data_summary} Use this data to answer: {prompt}"
                    response = llm.invoke([SystemMessage(content="You are a business analyst."), HumanMessage(content=context)])
                    st.markdown(response.content)
                    st.session_state.messages.append({"role": "assistant", "content": response.content})
                    
                    # PDF Report Button
                    pdf = MarkdownPdf(toc_level=1)
                    pdf.add_section(Section(f"# Business Report\n\n{response.content}"))
                    pdf_buffer = io.BytesIO()
                    pdf.save_bytes(pdf_buffer)
                    st.download_button(label="📥 Download PDF Report", data=pdf_buffer.getvalue(), file_name="Report.pdf")

        except Exception as e:
            st.error(f"⚠️ App Error: {e}")