"""
LLM Generator Service
Advanced language model integration with LLaMA 3.1 and GPT-4o-mini support
"""

import os
import logging
import time
import json
from typing import Dict, List, Any, Optional, Union, Generator
from dataclasses import dataclass
from enum import Enum
import requests

# Try to import optional dependencies
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None
    pipeline = None

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    LLAMA_LOCAL = "llama_local"
    LLAMA_API = "llama_api"
    HUGGINGFACE = "huggingface"


class LLMModel(Enum):
    """Supported LLM models"""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    LLAMA_3_1_8B = "llama-3.1-8b"
    LLAMA_3_1_70B = "llama-3.1-70b"
    LLAMA_3_1_405B = "llama-3.1-405b"


@dataclass
class LLMConfig:
    """Configuration for LLM generation"""
    provider: LLMProvider
    model: LLMModel
    max_tokens: int = 2000
    temperature: float = 0.3
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 30
    retry_attempts: int = 3
    enable_streaming: bool = True


@dataclass
class GenerationResult:
    """Result of LLM generation"""
    text: str
    provider: str
    model: str
    tokens_used: int
    generation_time: float
    confidence: float
    metadata: Dict[str, Any]
    status: str = "success"
    error: Optional[str] = None


class LLMGenerator:
    """Advanced LLM generator with multiple provider support"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.providers = {}
        self.default_config = self._get_default_config()
        
        # Initialize providers
        self._initialize_openai()
        self._initialize_llama()
        self._initialize_huggingface()
        
        # Configuration
        self.primary_provider = self.config.get('primary_provider', LLMProvider.OPENAI)
        self.fallback_providers = self.config.get('fallback_providers', [LLMProvider.LLAMA_LOCAL])
        self.enable_fallback = self.config.get('enable_fallback', True)
        
        logger.info(f"LLM Generator initialized with primary provider: {self.primary_provider.value}")
    
    def _get_default_config(self) -> Dict[str, LLMConfig]:
        """Get default configurations for all models"""
        return {
            LLMModel.GPT_4O_MINI: LLMConfig(
                provider=LLMProvider.OPENAI,
                model=LLMModel.GPT_4O_MINI,
                max_tokens=2000,
                temperature=0.3,
                timeout=30
            ),
            LLMModel.GPT_4O: LLMConfig(
                provider=LLMProvider.OPENAI,
                model=LLMModel.GPT_4O,
                max_tokens=2000,
                temperature=0.3,
                timeout=30
            ),
            LLMModel.LLAMA_3_1_8B: LLMConfig(
                provider=LLMProvider.LLAMA_LOCAL,
                model=LLMModel.LLAMA_3_1_8B,
                max_tokens=2000,
                temperature=0.3,
                timeout=60
            ),
            LLMModel.LLAMA_3_1_70B: LLMConfig(
                provider=LLMProvider.LLAMA_API,
                model=LLMModel.LLAMA_3_1_70B,
                max_tokens=2000,
                temperature=0.3,
                timeout=60
            )
        }
    
    def _initialize_openai(self):
        """Initialize OpenAI provider"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available - package not installed")
            self.providers[LLMProvider.OPENAI] = {'available': False}
            return
            
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.providers[LLMProvider.OPENAI] = {
                    'client': OpenAI(api_key=api_key),
                    'available': True,
                    'models': [LLMModel.GPT_4O_MINI, LLMModel.GPT_4O, LLMModel.GPT_3_5_TURBO]
                }
                logger.info("OpenAI provider initialized successfully")
            else:
                logger.warning("OpenAI API key not found")
                self.providers[LLMProvider.OPENAI] = {'available': False}
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {str(e)}")
            self.providers[LLMProvider.OPENAI] = {'available': False}
    
    def _initialize_llama(self):
        """Initialize LLaMA provider (local and API)"""
        # Local LLaMA
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available - LLaMA local provider disabled")
            self.providers[LLMProvider.LLAMA_LOCAL] = {'available': False}
        else:
            try:
                if torch.cuda.is_available() or torch.backends.mps.is_available():
                    self.providers[LLMProvider.LLAMA_LOCAL] = {
                        'available': True,
                        'models': [LLMModel.LLAMA_3_1_8B],
                        'device': 'cuda' if torch.cuda.is_available() else 'mps'
                    }
                    logger.info("LLaMA local provider initialized successfully")
                else:
                    logger.warning("CUDA/MPS not available for local LLaMA")
                    self.providers[LLMProvider.LLAMA_LOCAL] = {'available': False}
            except Exception as e:
                logger.error(f"Failed to initialize local LLaMA: {str(e)}")
                self.providers[LLMProvider.LLAMA_LOCAL] = {'available': False}
        
        # LLaMA API (e.g., Groq, Together AI, etc.)
        try:
            llama_api_key = os.getenv("LLAMA_API_KEY") or os.getenv("GROQ_API_KEY")
            if llama_api_key:
                self.providers[LLMProvider.LLAMA_API] = {
                    'api_key': llama_api_key,
                    'available': True,
                    'models': [LLMModel.LLAMA_3_1_70B, LLMModel.LLAMA_3_1_405B],
                    'base_url': os.getenv("LLAMA_API_BASE_URL", "https://api.groq.com/openai/v1")
                }
                logger.info("LLaMA API provider initialized successfully")
            else:
                logger.warning("LLaMA API key not found")
                self.providers[LLMProvider.LLAMA_API] = {'available': False}
        except Exception as e:
            logger.error(f"Failed to initialize LLaMA API: {str(e)}")
            self.providers[LLMProvider.LLAMA_API] = {'available': False}
    
    def _initialize_huggingface(self):
        """Initialize Hugging Face provider"""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available - Hugging Face provider disabled")
            self.providers[LLMProvider.HUGGINGFACE] = {'available': False}
            return
            
        try:
            hf_token = os.getenv("HUGGINGFACE_TOKEN")
            self.providers[LLMProvider.HUGGINGFACE] = {
                'token': hf_token,
                'available': True,
                'models': [LLMModel.LLAMA_3_1_8B]
            }
            logger.info("Hugging Face provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Hugging Face: {str(e)}")
            self.providers[LLMProvider.HUGGINGFACE] = {'available': False}
    
    def generate_answer(self, 
                       system_prompt: str,
                       user_prompt: str,
                       model: Optional[LLMModel] = None,
                       config: Optional[LLMConfig] = None,
                       conversation_history: Optional[List[Dict]] = None) -> GenerationResult:
        """Generate answer using the specified or best available model"""
        
        start_time = time.time()
        
        try:
            # Determine model and provider
            if model is None:
                model = self._select_best_model()
            
            if config is None:
                config = self.default_config.get(model, self.default_config[LLMModel.GPT_4O_MINI])
            
            # Try primary provider first
            result = self._generate_with_provider(
                provider=config.provider,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                config=config,
                conversation_history=conversation_history
            )
            
            # If primary fails and fallback is enabled, try fallback providers
            if result.status != "success" and self.enable_fallback:
                for fallback_provider in self.fallback_providers:
                    if fallback_provider != config.provider:
                        logger.info(f"Trying fallback provider: {fallback_provider.value}")
                        result = self._generate_with_provider(
                            provider=fallback_provider,
                            model=model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            config=config,
                            conversation_history=conversation_history
                        )
                        if result.status == "success":
                            break
            
            result.generation_time = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_answer: {str(e)}")
            return GenerationResult(
                text="",
                provider="error",
                model="error",
                tokens_used=0,
                generation_time=time.time() - start_time,
                confidence=0.0,
                metadata={'error': str(e)},
                status="error",
                error=str(e)
            )
    
    def generate_streaming_answer(self, 
                                 system_prompt: str,
                                 user_prompt: str,
                                 model: Optional[LLMModel] = None,
                                 config: Optional[LLMConfig] = None) -> Generator[Dict[str, Any], None, None]:
        """Generate streaming answer"""
        
        try:
            # Determine model and provider
            if model is None:
                model = self._select_best_model()
            
            if config is None:
                config = self.default_config.get(model, self.default_config[LLMModel.GPT_4O_MINI])
            
            # Generate streaming response
            for chunk in self._generate_streaming_with_provider(
                provider=config.provider,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                config=config
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in generate_streaming_answer: {str(e)}")
            yield {
                'type': 'error',
                'error': str(e),
                'content': ''
            }
    
    def _select_best_model(self) -> LLMModel:
        """Select the best available model"""
        # Priority order: GPT-4o-mini, LLaMA 3.1 70B, LLaMA 3.1 8B, GPT-3.5-turbo
        
        if (self.providers.get(LLMProvider.OPENAI, {}).get('available') and 
            LLMModel.GPT_4O_MINI in self.providers[LLMProvider.OPENAI]['models']):
            return LLMModel.GPT_4O_MINI
        
        if (self.providers.get(LLMProvider.LLAMA_API, {}).get('available') and 
            LLMModel.LLAMA_3_1_70B in self.providers[LLMProvider.LLAMA_API]['models']):
            return LLMModel.LLAMA_3_1_70B
        
        if (self.providers.get(LLMProvider.LLAMA_LOCAL, {}).get('available') and 
            LLMModel.LLAMA_3_1_8B in self.providers[LLMProvider.LLAMA_LOCAL]['models']):
            return LLMModel.LLAMA_3_1_8B
        
        if (self.providers.get(LLMProvider.OPENAI, {}).get('available') and 
            LLMModel.GPT_3_5_TURBO in self.providers[LLMProvider.OPENAI]['models']):
            return LLMModel.GPT_3_5_TURBO
        
        # Fallback to GPT-4o-mini
        return LLMModel.GPT_4O_MINI
    
    def _generate_with_provider(self, 
                               provider: LLMProvider,
                               model: LLMModel,
                               system_prompt: str,
                               user_prompt: str,
                               config: LLMConfig,
                               conversation_history: Optional[List[Dict]] = None) -> GenerationResult:
        """Generate answer with specific provider"""
        
        if provider == LLMProvider.OPENAI:
            return self._generate_with_openai(model, system_prompt, user_prompt, config, conversation_history)
        elif provider == LLMProvider.LLAMA_LOCAL:
            return self._generate_with_llama_local(model, system_prompt, user_prompt, config)
        elif provider == LLMProvider.LLAMA_API:
            return self._generate_with_llama_api(model, system_prompt, user_prompt, config)
        elif provider == LLMProvider.HUGGINGFACE:
            return self._generate_with_huggingface(model, system_prompt, user_prompt, config)
        else:
            return GenerationResult(
                text="",
                provider=provider.value,
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': f'Unknown provider: {provider.value}'},
                status="error",
                error=f'Unknown provider: {provider.value}'
            )
    
    def _generate_with_openai(self, 
                             model: LLMModel,
                             system_prompt: str,
                             user_prompt: str,
                             config: LLMConfig,
                             conversation_history: Optional[List[Dict]] = None) -> GenerationResult:
        """Generate answer using OpenAI"""
        
        if not self.providers.get(LLMProvider.OPENAI, {}).get('available'):
            return GenerationResult(
                text="",
                provider="openai",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': 'OpenAI not available'},
                status="error",
                error="OpenAI not available"
            )
        
        try:
            client = self.providers[LLMProvider.OPENAI]['client']
            
            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if available
            if conversation_history:
                for turn in conversation_history[-3:]:  # Last 3 turns
                    messages.append({"role": "user", "content": turn.get('query', '')})
                    messages.append({"role": "assistant", "content": turn.get('response', '')})
            
            messages.append({"role": "user", "content": user_prompt})
            
            # Generate response
            response = client.chat.completions.create(
                model=model.value,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                timeout=config.timeout
            )
            
            # Extract result
            text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(text, tokens_used, model)
            
            return GenerationResult(
                text=text,
                provider="openai",
                model=model.value,
                tokens_used=tokens_used,
                generation_time=0.0,  # Will be set by caller
                confidence=confidence,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'model_version': model.value,
                    'provider': 'openai'
                },
                status="success"
            )
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            return GenerationResult(
                text="",
                provider="openai",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': str(e)},
                status="error",
                error=str(e)
            )
    
    def _generate_with_llama_local(self, 
                                  model: LLMModel,
                                  system_prompt: str,
                                  user_prompt: str,
                                  config: LLMConfig) -> GenerationResult:
        """Generate answer using local LLaMA"""
        
        if not TORCH_AVAILABLE:
            return GenerationResult(
                text="",
                provider="llama_local",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': 'PyTorch not available'},
                status="error",
                error="PyTorch not available"
            )
        
        if not self.providers.get(LLMProvider.LLAMA_LOCAL, {}).get('available'):
            return GenerationResult(
                text="",
                provider="llama_local",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': 'Local LLaMA not available'},
                status="error",
                error="Local LLaMA not available"
            )
        
        try:
            # Load model and tokenizer
            model_name = self._get_llama_model_name(model)
            device = self.providers[LLMProvider.LLAMA_LOCAL]['device']
            
            # Use pipeline for easier generation
            generator = pipeline(
                "text-generation",
                model=model_name,
                device_map="auto" if device == "cuda" else None,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )
            
            # Format prompt
            full_prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n"
            
            # Generate response
            response = generator(
                full_prompt,
                max_new_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                do_sample=True,
                pad_token_id=generator.tokenizer.eos_token_id
            )
            
            # Extract generated text
            generated_text = response[0]['generated_text']
            text = generated_text[len(full_prompt):].strip()
            
            # Count tokens
            tokens_used = len(generator.tokenizer.encode(text))
            
            # Calculate confidence
            confidence = self._calculate_confidence(text, tokens_used, model)
            
            return GenerationResult(
                text=text,
                provider="llama_local",
                model=model.value,
                tokens_used=tokens_used,
                generation_time=0.0,  # Will be set by caller
                confidence=confidence,
                metadata={
                    'model_name': model_name,
                    'device': device,
                    'provider': 'llama_local'
                },
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Local LLaMA generation error: {str(e)}")
            return GenerationResult(
                text="",
                provider="llama_local",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': str(e)},
                status="error",
                error=str(e)
            )
    
    def _generate_with_llama_api(self, 
                                model: LLMModel,
                                system_prompt: str,
                                user_prompt: str,
                                config: LLMConfig) -> GenerationResult:
        """Generate answer using LLaMA API (Groq, Together AI, etc.)"""
        
        if not self.providers.get(LLMProvider.LLAMA_API, {}).get('available'):
            return GenerationResult(
                text="",
                provider="llama_api",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': 'LLaMA API not available'},
                status="error",
                error="LLaMA API not available"
            )
        
        try:
            api_config = self.providers[LLMProvider.LLAMA_API]
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {api_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # Map model names for API
            api_model_name = self._get_api_model_name(model)
            
            data = {
                "model": api_model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "stream": False
            }
            
            # Make request
            response = requests.post(
                f"{api_config['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=config.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Extract response
            text = result['choices'][0]['message']['content'].strip()
            tokens_used = result['usage']['total_tokens']
            
            # Calculate confidence
            confidence = self._calculate_confidence(text, tokens_used, model)
            
            return GenerationResult(
                text=text,
                provider="llama_api",
                model=model.value,
                tokens_used=tokens_used,
                generation_time=0.0,  # Will be set by caller
                confidence=confidence,
                metadata={
                    'api_model': api_model_name,
                    'provider': 'llama_api'
                },
                status="success"
            )
            
        except Exception as e:
            logger.error(f"LLaMA API generation error: {str(e)}")
            return GenerationResult(
                text="",
                provider="llama_api",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': str(e)},
                status="error",
                error=str(e)
            )
    
    def _generate_with_huggingface(self, 
                                  model: LLMModel,
                                  system_prompt: str,
                                  user_prompt: str,
                                  config: LLMConfig) -> GenerationResult:
        """Generate answer using Hugging Face"""
        
        if not TORCH_AVAILABLE:
            return GenerationResult(
                text="",
                provider="huggingface",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': 'PyTorch not available'},
                status="error",
                error="PyTorch not available"
            )
        
        if not self.providers.get(LLMProvider.HUGGINGFACE, {}).get('available'):
            return GenerationResult(
                text="",
                provider="huggingface",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': 'Hugging Face not available'},
                status="error",
                error="Hugging Face not available"
            )
        
        try:
            # Use Hugging Face Inference API
            api_url = f"https://api-inference.huggingface.co/models/{self._get_hf_model_name(model)}"
            headers = {"Authorization": f"Bearer {self.providers[LLMProvider.HUGGINGFACE]['token']}"}
            
            # Format prompt
            full_prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n"
            
            data = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "return_full_text": False
                }
            }
            
            response = requests.post(api_url, headers=headers, json=data, timeout=config.timeout)
            
            if response.status_code != 200:
                raise Exception(f"Hugging Face API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Extract text
            if isinstance(result, list) and len(result) > 0:
                text = result[0]['generated_text'].strip()
            else:
                text = str(result).strip()
            
            # Estimate tokens
            tokens_used = len(text.split()) * 1.3  # Rough estimation
            
            # Calculate confidence
            confidence = self._calculate_confidence(text, tokens_used, model)
            
            return GenerationResult(
                text=text,
                provider="huggingface",
                model=model.value,
                tokens_used=int(tokens_used),
                generation_time=0.0,  # Will be set by caller
                confidence=confidence,
                metadata={
                    'hf_model': self._get_hf_model_name(model),
                    'provider': 'huggingface'
                },
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Hugging Face generation error: {str(e)}")
            return GenerationResult(
                text="",
                provider="huggingface",
                model=model.value,
                tokens_used=0,
                generation_time=0.0,
                confidence=0.0,
                metadata={'error': str(e)},
                status="error",
                error=str(e)
            )
    
    def _generate_streaming_with_provider(self, 
                                         provider: LLMProvider,
                                         model: LLMModel,
                                         system_prompt: str,
                                         user_prompt: str,
                                         config: LLMConfig) -> Generator[Dict[str, Any], None, None]:
        """Generate streaming response with specific provider"""
        
        if provider == LLMProvider.OPENAI:
            yield from self._generate_streaming_with_openai(model, system_prompt, user_prompt, config)
        else:
            # For non-OpenAI providers, generate full response and stream it
            result = self._generate_with_provider(provider, model, system_prompt, user_prompt, config)
            if result.status == "success":
                # Simulate streaming by yielding chunks
                words = result.text.split()
                for i in range(0, len(words), 5):  # Yield 5 words at a time
                    chunk = " ".join(words[i:i+5])
                    if i + 5 < len(words):
                        chunk += " "
                    yield {
                        'type': 'content',
                        'content': chunk,
                        'provider': result.provider,
                        'model': result.model
                    }
                yield {
                    'type': 'complete',
                    'provider': result.provider,
                    'model': result.model,
                    'tokens_used': result.tokens_used,
                    'confidence': result.confidence
                }
            else:
                yield {
                    'type': 'error',
                    'error': result.error,
                    'provider': result.provider,
                    'model': result.model
                }
    
    def _generate_streaming_with_openai(self, 
                                       model: LLMModel,
                                       system_prompt: str,
                                       user_prompt: str,
                                       config: LLMConfig) -> Generator[Dict[str, Any], None, None]:
        """Generate streaming response using OpenAI"""
        
        if not self.providers.get(LLMProvider.OPENAI, {}).get('available'):
            yield {
                'type': 'error',
                'error': 'OpenAI not available',
                'provider': 'openai',
                'model': model.value
            }
            return
        
        try:
            client = self.providers[LLMProvider.OPENAI]['client']
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = client.chat.completions.create(
                model=model.value,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stream=True,
                timeout=config.timeout
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield {
                        'type': 'content',
                        'content': chunk.choices[0].delta.content,
                        'provider': 'openai',
                        'model': model.value
                    }
            
            yield {
                'type': 'complete',
                'provider': 'openai',
                'model': model.value
            }
            
        except Exception as e:
            logger.error(f"OpenAI streaming error: {str(e)}")
            yield {
                'type': 'error',
                'error': str(e),
                'provider': 'openai',
                'model': model.value
            }
    
    def _get_llama_model_name(self, model: LLMModel) -> str:
        """Get Hugging Face model name for LLaMA"""
        model_mapping = {
            LLMModel.LLAMA_3_1_8B: "meta-llama/Llama-3.1-8B-Instruct",
            LLMModel.LLAMA_3_1_70B: "meta-llama/Llama-3.1-70B-Instruct",
            LLMModel.LLAMA_3_1_405B: "meta-llama/Llama-3.1-405B-Instruct"
        }
        return model_mapping.get(model, "meta-llama/Llama-3.1-8B-Instruct")
    
    def _get_api_model_name(self, model: LLMModel) -> str:
        """Get API model name for LLaMA"""
        model_mapping = {
            LLMModel.LLAMA_3_1_8B: "llama-3.1-8b-instant",
            LLMModel.LLAMA_3_1_70B: "llama-3.1-70b-versatile",
            LLMModel.LLAMA_3_1_405B: "llama-3.1-405b-versatile"
        }
        return model_mapping.get(model, "llama-3.1-8b-instant")
    
    def _get_hf_model_name(self, model: LLMModel) -> str:
        """Get Hugging Face model name"""
        return self._get_llama_model_name(model)
    
    def _calculate_confidence(self, text: str, tokens_used: int, model: LLMModel) -> float:
        """Calculate confidence score for generated text"""
        base_confidence = 0.7
        
        # Adjust based on model quality
        model_confidence = {
            LLMModel.GPT_4O: 0.95,
            LLMModel.GPT_4O_MINI: 0.9,
            LLMModel.LLAMA_3_1_405B: 0.9,
            LLMModel.LLAMA_3_1_70B: 0.85,
            LLMModel.LLAMA_3_1_8B: 0.8,
            LLMModel.GPT_3_5_TURBO: 0.75
        }
        
        base_confidence = model_confidence.get(model, 0.7)
        
        # Adjust based on response length
        if len(text) > 200:
            base_confidence += 0.05
        elif len(text) < 50:
            base_confidence -= 0.1
        
        # Adjust based on token efficiency
        if tokens_used > 0:
            efficiency = len(text) / tokens_used
            if efficiency > 0.5:  # Good efficiency
                base_confidence += 0.05
            elif efficiency < 0.3:  # Poor efficiency
                base_confidence -= 0.05
        
        return min(max(base_confidence, 0.0), 1.0)
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get list of available models by provider"""
        available = {}
        
        for provider, config in self.providers.items():
            if config.get('available'):
                models = config.get('models', [])
                available[provider.value] = [model.value for model in models]
        
        return available
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status for all providers"""
        status = {
            'providers': {},
            'primary_provider': self.primary_provider.value,
            'fallback_providers': [p.value for p in self.fallback_providers],
            'enable_fallback': self.enable_fallback
        }
        
        for provider, config in self.providers.items():
            status['providers'][provider.value] = {
                'available': config.get('available', False),
                'models': [model.value for model in config.get('models', [])],
                'error': config.get('error')
            }
        
        return status
