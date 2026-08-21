#!/bin/sh
exec streamlit run app.py --server.port 8555 --server.headless true --browser.gatherUsageStats false
