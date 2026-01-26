# tests/test_api.py

from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from run_voice_lab_api import app

client = TestClient(app)

def test_record():
    resp = client.post("/api/record", json={"device_id": "default"})
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "profiling" in data
    assert data["profiling"]["vad"] > 0
    assert data["profiling"]["stt"] > 0

def test_chat():
    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "profiling" in data
    assert data["profiling"]["llm"] > 0

def test_tts():
    resp = client.post("/api/tts", json={"text": "Hi there!"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "url" in data
    assert data["profiling"]["tts"] > 0
