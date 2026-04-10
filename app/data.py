import streamlit as st
from app.services.mapping_service import hascol, ign, load_and_process_data as load_and_process_data_service, safe
from app.services.quality_service import detect_errors as detect_errors_service, health_score as health_score_service


@st.cache_data(show_spinner=False)
def load_and_process_data(fb: bytes):
    """Cached Streamlit wrapper around the pure mapping service."""
    return load_and_process_data_service(fb)


@st.cache_data(show_spinner=False)
def detect_errors(df, name: str):
    """Cached Streamlit wrapper around the pure quality service."""
    return detect_errors_service(df, name)


@st.cache_data(show_spinner=False)
def health_score(df, sheet_name: str):
    """Cached Streamlit wrapper around the pure quality service."""
    return health_score_service(df, sheet_name)
