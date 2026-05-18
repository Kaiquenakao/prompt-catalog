import httpx
import streamlit as st

BASE_URL = st.secrets["API_GATEWAY_URL"]
API_KEY = st.secrets["API_KEY"]


def _headers():
    return {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }


def list_models() -> list[dict]:
    resp = httpx.get(f"{BASE_URL}/models", headers=_headers(), timeout=10.0)
    resp.raise_for_status()
    return resp.json()["models"]
