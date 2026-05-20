import requests
import streamlit as st

from app.core.config import settings

API_URL = settings.app.api_url


st.set_page_config(page_title="RAG Recruiter AI", page_icon="🤖", layout="wide")
st.title("🤖 AI Recruitment System")
st.markdown("Hybrid Search System powered by **PostgreSQL (pgvector)** and **OpenAI**")

tab1, tab2 = st.tabs(["🔍 Search Candidates", "➕ Add New Candidate"])

# --- TAB 1: SEARCH ---
with tab1:
    st.header("Find the perfect match")

    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "original_query" not in st.session_state:
        st.session_state.original_query = ""
    if "is_expanded" not in st.session_state:
        st.session_state.is_expanded = False

    def on_query_change():
        st.session_state.is_expanded = False
        st.session_state.original_query = ""

    def expand_callback():
        current_query = st.session_state.search_query

        if not current_query or len(current_query.strip()) < 2:
            st.warning("⚠️ Please enter a query (at least 2 characters)")
            return

        try:
            response = requests.post(
                f"{API_URL}/expand-query",
                json={"query": current_query},
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                expanded_text = result.get("expanded_query", "")

                if expanded_text and expanded_text.strip() != current_query.strip():
                    st.session_state.original_query = current_query
                    st.session_state.search_query = expanded_text
                    st.session_state.is_expanded = True
                    st.toast("✅ Query improved!", icon="✨")
                else:
                    st.toast("ℹ️ Query is already optimal!", icon="ℹ️")
            else:
                st.error(f"❌ Error: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Connection Failed: {e}")

    def restore_callback():
        """Returning old text"""
        st.session_state.search_query = st.session_state.original_query
        st.session_state.is_expanded = False
        st.session_state.original_query = ""
        st.toast("↩️ Restored original query")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.text_input(
            "Search Query",
            placeholder="e.g. 'Python developer with AWS experience'",
            key="search_query",
            on_change=on_query_change,
        )

    with col2:
        location = st.text_input("Location Filter", placeholder="e.g. New York")
    with col3:
        min_exp = st.number_input(
            "Min Experience (Years)", min_value=0, max_value=20, value=0
        )

    btn_col1, btn_col2, btn_spacer = st.columns([1.2, 1.2, 1.6])

    with btn_col1:
        st.button(
            "Expand Query with AI",
            use_container_width=True,
            disabled=st.session_state.is_expanded,
            on_click=expand_callback,
        )

    with btn_col2:
        if st.session_state.is_expanded:
            st.button(
                "↩️ Restore Original",
                use_container_width=True,
                on_click=restore_callback,
            )

    if st.session_state.is_expanded:
        st.info(
            f"🔄 **Expanded from:** `{st.session_state.original_query}` \n\n"
            f"⬇️ \n\n"
            f"**To:** `{st.session_state.search_query}`"
        )

    top_k = st.slider("Number of results", 1, 10, 3)

    if st.button("🔍 Search", type="primary"):
        final_query = st.session_state.search_query

        if not final_query and not location:
            st.warning("Please enter a query or location.")
        else:
            payload = {
                "query": final_query if final_query else None,
                "location": location if location else None,
                "min_experience": min_exp,
                "top_k": top_k,
            }

            with st.spinner("Searching database..."):
                try:
                    response = requests.post(f"{API_URL}/search", json=payload)

                    if response.status_code == 200:
                        results = response.json().get("results", [])

                        if not results:
                            st.info("No candidates found.")
                        else:
                            st.success(f"Found {len(results)} candidates!")

                            for cand in results:
                                score_display = (
                                    f"({cand['score']:.2f})" if "score" in cand else ""
                                )
                                with st.expander(
                                    f"**{cand['full_name']}** - {cand['professional_title']} {score_display}"
                                ):
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        st.markdown(
                                            f"📍 **Location:** {cand.get('location', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"💼 **Experience:** {cand.get('years_experience')} years"
                                        )
                                    with c2:
                                        st.markdown(
                                            f"📧 **Email:** {cand.get('email', 'Hidden')}"
                                        )

                                    st.divider()
                                    st.markdown("### 🤖 AI Summary")
                                    st.info(cand.get("summary", "No summary available"))

                                    st.markdown("### 🛠 Skills")
                                    skills = cand.get("skills")
                                    if isinstance(skills, dict):
                                        st.json(skills)
                                    else:
                                        st.write(str(skills))

                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")

                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

# --- TAB 2: ONBOARDING ---
with tab2:
    st.header("Onboard a new candidate")

    if "form_data" not in st.session_state:
        st.session_state.form_data = {
            "full_name": "",
            "email": "",
            "phone": "",
            "location": "",
            "title": "",
            "exp": 0,
            "education": "",
            "skills": "",
            "tools": "",
            "projects": "",
            "work": "",
            "certs": "",
            "langs": "",
            "summary_preview": "",
        }

    uploaded_file = st.file_uploader("📄 Upload PDF Resume", type="pdf")

    if uploaded_file is not None:  # noqa: SIM102
        if st.button("✨ Extract All Data with AI"):
            with st.spinner("Analyzing PDF... Parsing complex fields..."):
                try:
                    # Reset file pointer to beginning
                    uploaded_file.seek(0)

                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.read(),
                            "application/pdf",
                        )
                    }

                    response = requests.post(
                        f"{API_URL}/extract", files=files, timeout=60
                    )

                    if response.status_code == 200:
                        result = response.json()
                        data = result.get("extracted_data", {})
                        summary = result.get("final_summary", "")

                        st.session_state.form_data["full_name"] = data.get(
                            "full_name", ""
                        )
                        st.session_state.form_data["email"] = data.get("email", "")
                        st.session_state.form_data["phone"] = data.get("phone", "")
                        st.session_state.form_data["location"] = data.get(
                            "location", ""
                        )
                        st.session_state.form_data["title"] = data.get(
                            "professional_title", ""
                        )
                        st.session_state.form_data["exp"] = data.get(
                            "years_experience", 0
                        )
                        st.session_state.form_data["education"] = data.get(
                            "education", ""
                        )
                        st.session_state.form_data["summary_preview"] = summary

                        st.session_state.form_data["skills"] = ", ".join(
                            data.get("skills", [])
                        )
                        st.session_state.form_data["tools"] = ", ".join(
                            data.get("tools_technologies", [])
                        )
                        st.session_state.form_data["langs"] = ", ".join(
                            data.get("spoken_languages", [])
                        )
                        st.session_state.form_data["certs"] = "\n".join(
                            data.get("certifications", [])
                        )

                        st.session_state.form_data["projects"] = "\n".join(
                            data.get("projects", [])
                        )
                        st.session_state.form_data["work"] = "\n".join(
                            data.get("work_history", [])
                        )

                        st.success("Extraction Complete! Review details below.")
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

    st.divider()

    with st.form("onboarding_form"):
        st.subheader("1. Personal Info")
        c1, c2, c3 = st.columns(3)
        with c1:
            f_name = st.text_input(
                "Full Name", value=st.session_state.form_data["full_name"]
            )
            f_email = st.text_input("Email", value=st.session_state.form_data["email"])
        with c2:
            f_phone = st.text_input("Phone", value=st.session_state.form_data["phone"])
            f_loc = st.text_input(
                "Location", value=st.session_state.form_data["location"]
            )
        with c3:
            f_title = st.text_input(
                "Professional Title", value=st.session_state.form_data["title"]
            )
            f_exp = st.number_input(
                "Years Experience",
                min_value=0,
                value=int(st.session_state.form_data["exp"] or 0),
            )

        st.subheader("2. Skills & Stack")
        f_skills = st.text_area(
            "Skills (comma separated)", value=st.session_state.form_data["skills"]
        )
        c4, c5 = st.columns(2)
        with c4:
            f_tools = st.text_area(
                "Tools & Tech", value=st.session_state.form_data["tools"], height=100
            )
        with c5:
            f_langs = st.text_input(
                "Languages", value=st.session_state.form_data["langs"]
            )

        st.subheader("3. Experience & History")
        c6, c7 = st.columns(2)
        with c6:
            f_work = st.text_area(
                "Work History (One per line)",
                value=st.session_state.form_data["work"],
                height=150,
            )
            f_education = st.text_area(
                "Education", value=st.session_state.form_data["education"], height=100
            )
        with c7:
            f_projects = st.text_area(
                "Key Projects (One per line)",
                value=st.session_state.form_data["projects"],
                height=150,
            )
            f_certs = st.text_area(
                "Certifications", value=st.session_state.form_data["certs"], height=100
            )

        if st.session_state.form_data["summary_preview"]:
            st.info(
                f"🤖 **Generated Summary:** {st.session_state.form_data['summary_preview']}"
            )

        submitted = st.form_submit_button("🚀 Save Candidate Profile")

        if submitted:
            if not f_name:
                st.error("Name is required!")
            else:
                payload = {
                    "full_name": f_name,
                    "email": f_email if f_email else None,
                    "phone": f_phone if f_phone else None,
                    "location": f_loc if f_loc else None,
                    "professional_title": f_title,
                    "years_experience": f_exp,
                    "spoken_languages": [
                        x.strip() for x in f_langs.split(",") if x.strip()
                    ],
                    "education": f_education if f_education else None,
                    "certifications": f_certs if f_certs else None,
                    "skills": {
                        "manual_list": [
                            x.strip() for x in f_skills.split(",") if x.strip()
                        ]
                    },
                    "tools_technologies": {
                        "items": [x.strip() for x in f_tools.split(",") if x.strip()]
                    },
                    "work_history": {"raw_summary": f_work.split("\n")},
                    "projects": {"raw_summary": f_projects.split("\n")},
                }

                try:
                    resp = requests.post(f"{API_URL}/onboarding", json=payload)
                    if resp.status_code == 200:
                        st.balloons()
                        st.success(f"Successfully added {f_name}!")
                        for k in st.session_state.form_data:
                            st.session_state.form_data[k] = ""
                    else:
                        st.error(f"Error {resp.status_code}: {resp.text}")
                except Exception as e:
                    st.error(f"API Connection failed: {e}")
