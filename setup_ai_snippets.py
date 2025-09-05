#!/usr/bin/env python3
"""
Setup script for AI-powered snippet generation
"""

import os
import sys
import subprocess

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}")
        return False

def setup_ai_snippets():
    """Setup AI snippet generation dependencies"""
    print("🤖 Setting up AI-powered snippet generation...")
    print("=" * 50)
    
    # Required packages for AI snippet generation
    packages = [
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        "google-generativeai>=0.3.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "requests>=2.28.0"
    ]
    
    print("📦 Installing required packages...")
    success_count = 0
    
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 Installation Summary:")
    print(f"   Successfully installed: {success_count}/{len(packages)} packages")
    
    if success_count == len(packages):
        print("✅ All packages installed successfully!")
    else:
        print("⚠️  Some packages failed to install. Check the errors above.")
    
    # Create environment file template
    env_file = "ai_snippets.env.template"
    env_content = """# AI Snippet Generation Environment Variables
# Copy this file to .env and fill in your API keys

# OpenAI API Key (for GPT-3.5-turbo)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key (for Claude)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Google API Key (for Gemini)
GOOGLE_API_KEY=your_google_api_key_here

# AI Snippet Configuration
AI_SNIPPET_MODEL_TYPE=api
AI_SNIPPET_API_PROVIDER=openai
AI_SNIPPET_MAX_TOKENS=150
AI_SNIPPET_TEMPERATURE=0.3
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n📝 Created environment template: {env_file}")
    print("   Please copy this file to .env and add your API keys")
    
    # Create configuration file
    config_file = "ai_snippet_settings.py"
    config_content = """# AI Snippet Generation Settings
# Add this to your Django settings.py

# AI Snippet Configuration
AI_SNIPPET_CONFIG = {
    'model_type': 'api',  # 'api' or 'local'
    'api_provider': 'openai',  # 'openai', 'anthropic', 'google'
    'max_snippet_length': 200,
    'temperature': 0.3,
    'max_tokens': 150,
    'timeout': 10,
    'use_ai_snippets': True,
    'ai_snippet_priority': True,
}

# API Keys (set in environment variables)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
"""
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"📝 Created configuration file: {config_file}")
    print("   Please add this configuration to your Django settings.py")
    
    print("\n🚀 Setup complete!")
    print("\nNext steps:")
    print("1. Copy ai_snippets.env.template to .env and add your API keys")
    print("2. Add the configuration from ai_snippet_settings.py to your Django settings.py")
    print("3. Test the AI snippet generation with: python manage.py test_ai_snippets")

if __name__ == "__main__":
    setup_ai_snippets()
