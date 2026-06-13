#!/bin/bash
echo "🚀 SYLENTH Agent Deployment"
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate
pip install -r requirements.txt -q
echo "✅ Ready! Run: python main.py"
