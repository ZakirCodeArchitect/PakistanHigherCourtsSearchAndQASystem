"""
Simple script to add API keys to .env file
"""

import os
from dotenv import load_dotenv

def add_api_key(key_name, key_value):
    """Add an API key to the .env file"""
    
    # Load current .env
    load_dotenv()
    
    # Get project root (go up two levels from current directory)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_file = os.path.join(project_root, '.env')
    
    # Read current .env content
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add the key
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key_name}='):
            lines[i] = f'{key_name}={key_value}\n'
            key_found = True
            break
    
    if not key_found:
        lines.append(f'{key_name}={key_value}\n')
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Added {key_name} to .env file")

def main():
    print("🔑 API KEY ADDER")
    print("=" * 30)
    print("1. OpenAI API Key (starts with sk-)")
    print("2. Groq API Key (starts with gsk_)")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            openai_key = input("Enter your OpenAI API key: ").strip()
            if openai_key.startswith('sk-'):
                add_api_key('OPENAI_API_KEY', openai_key)
                print("✅ OpenAI API key added!")
            else:
                print("❌ Invalid OpenAI key format (should start with 'sk-')")
        
        elif choice == '2':
            groq_key = input("Enter your Groq API key: ").strip()
            if groq_key.startswith('gsk_'):
                add_api_key('GROQ_API_KEY', groq_key)
                print("✅ Groq API key added!")
            else:
                print("❌ Invalid Groq key format (should start with 'gsk_')")
        
        elif choice == '3':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
