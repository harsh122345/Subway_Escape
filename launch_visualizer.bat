@echo off
echo Starting Subway Escape Visualizer Dashboard...
start http://localhost:8000
py -3 visualizer_server.py
pause
