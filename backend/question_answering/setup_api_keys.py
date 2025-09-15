"""
API Keys Setup Script
Helps configure API keys for the RAG system
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file in current directory
load_dotenv('.env')

def setup_api_keys():
    """Interactive setup for API keys"""
    
    print("🔑 RAG SYSTEM API KEYS SETUP")
    print("=" * 50)
    
    # Check current environment
    print("\n📋 CURRENT API KEY STATUS:")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    llama_key = os.getenv("LLAMA_API_KEY") or os.getenv("GROQ_API_KEY")
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    
    print(f"✅ OpenAI API Key: {'SET' if openai_key else 'MISSING'}")
    print(f"❌ LLaMA API Key: {'SET' if llama_key else 'MISSING'}")
    print(f"❓ Hugging Face Token: {'SET' if hf_token else 'MISSING'}")
    
    print("\n🔧 REQUIRED API KEYS:")
    print("1. OPENAI_API_KEY - For GPT-4o-mini (Primary LLM)")
    print("2. LLAMA_API_KEY or GROQ_API_KEY - For LLaMA 3.1 70B/405B")
    print("3. HUGGINGFACE_TOKEN - For Hugging Face models (Optional)")
    
    print("\n📝 SETUP INSTRUCTIONS:")
    print("1. Create a .env file in your project root")
    print("2. Add the following lines:")
    print("")
    print("OPENAI_API_KEY=your_openai_key_here")
    print("LLAMA_API_KEY=your_llama_api_key_here")
    print("GROQ_API_KEY=your_groq_api_key_here")
    print("HUGGINGFACE_TOKEN=your_hf_token_here")
    print("")
    
    print("🌐 WHERE TO GET API KEYS:")
    print("• OpenAI: https://platform.openai.com/api-keys")
    print("• Groq: https://console.groq.com/keys")
    print("• Together AI: https://api.together.xyz/settings/api-keys")
    print("• Hugging Face: https://huggingface.co/settings/tokens")
    
    print("\n⚡ PRIORITY ORDER:")
    print("1. OPENAI_API_KEY (Required - Primary LLM)")
    print("2. GROQ_API_KEY (Recommended - LLaMA 3.1 70B)")
    print("3. HUGGINGFACE_TOKEN (Optional - Fallback)")
    
    return {
        'openai': bool(openai_key),
        'llama': bool(llama_key),
        'huggingface': bool(hf_token)
    }

def test_api_keys():
    """Test API key configuration"""
    print("\n🧪 TESTING API KEY CONFIGURATION...")
    
    try:
        from services.llm_generator import LLMGenerator
        
        llm_gen = LLMGenerator()
        status = llm_gen.get_system_status()
        
        print("\n📊 LLM PROVIDER STATUS:")
        for provider, config in status['providers'].items():
            status_icon = "✅" if config.get('available') else "❌"
            models = config.get('models', [])
            model_names = [m.value for m in models] if models else ['None']
            print(f"  {status_icon} {provider}: {', '.join(model_names)}")
        
        return status
        
    except Exception as e:
        print(f"❌ Error testing API keys: {str(e)}")
        return None

if __name__ == "__main__":
    setup_api_keys()
    test_api_keys()
