@echo off
REM Thin wrapper around build.py — see build.py for what actually happens.
REM Produces dist\VoiceForge.exe only (no copying elsewhere).

call .venv\Scripts\python.exe build.py
