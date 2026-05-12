#!/usr/bin/env bash
# Render Build Script - Install dependencies and Playwright browser
set -o errexit

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🌐 Installing Playwright Chromium browser for Render environment..."
playwright install chromium

echo "✅ Build completed successfully!"
