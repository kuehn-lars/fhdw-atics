import os
import torch
import threading
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig, TextIteratorStreamer
from typing import Optional, Iterator
from langchain_ollama import OllamaLLM as Ollama
from src.rag_system.core.base import LLMInterface

class HuggingFaceLLM(LLMInterface):
    def __init__(self, model_name: str, use_4bit: bool = True):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Use MPS for Apple Silicon, CUDA for NVIDIA, or CPU
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
            
        # 4-bit quantization configuration (bitsandbytes is mostly CUDA-only)
        bnb_config = None
        if use_4bit and device == "cuda":
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        elif use_4bit and device == "mps":
            print("Note: int4 via bitsandbytes is not fully supported on MPS. Using float16 instead. For int4 on Mac, please use Ollama.")
            
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                torch_dtype=torch.float16 if device != "cpu" else torch.float32,
                device_map="auto" if device != "cpu" else None
            )
        except Exception as e:
            print(f"Warning: Loading with device_map='auto' failed: {e}. Trying explicit device.")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device != "cpu" else torch.float32
            ).to(device)
            
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=512
        )

    def _get_formatted_prompt(self, prompt: str, context: Optional[str] = None) -> str:
        messages = []
        if context:
            messages.append({"role": "system", "content": f"You are a helpful assistant. Use the following context to answer the question: {context}"})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant."})
            
        messages.append({"role": "user", "content": prompt})
        
        return self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )

    def generate(self, prompt: str, context: Optional[str] = None, max_new_tokens: int = 512) -> str:
        full_prompt = self._get_formatted_prompt(prompt, context)
        results = self.pipe(full_prompt, max_new_tokens=max_new_tokens)
        # Handle cases where the model might repeat the prompt
        generated = results[0]["generated_text"]
        if generated.startswith(full_prompt):
            return generated[len(full_prompt):].strip()
        return generated.strip()

    def stream(self, prompt: str, context: Optional[str] = None, max_new_tokens: int = 512) -> Iterator[str]:
        full_prompt = self._get_formatted_prompt(prompt, context)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)
        generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=max_new_tokens)
        
        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        for new_text in streamer:
            yield new_text

class LocalLLMModule(LLMInterface):
    def __init__(self, model_name: str):
        # Intelligent selection: if it looks like a Hugging Face model path, use HuggingFaceLLM
        # Otherwise, assume it's an Ollama model name.
        if "/" in model_name or os.path.exists(model_name):
            self.llm = HuggingFaceLLM(model_name)
        else:
            self.llm = Ollama(model=model_name)
    
    def generate(self, prompt: str, context: Optional[str] = None, max_new_tokens: int = 512) -> str:
        if isinstance(self.llm, Ollama):
            full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
            # Note: Ollama doesn't have a direct 'max_new_tokens' parameter in its standard invoke, 
            # but we can pass it via num_predict
            return self.llm.invoke(full_prompt, num_predict=max_new_tokens)
        return self.llm.generate(prompt, context, max_new_tokens=max_new_tokens)

    def stream(self, prompt: str, context: Optional[str] = None, max_new_tokens: int = 512) -> Iterator[str]:
        if isinstance(self.llm, Ollama):
            full_prompt = f"Context: {context}\n\nQuestion: {prompt}" if context else prompt
            for chunk in self.llm.stream(full_prompt, num_predict=max_new_tokens):
                yield str(chunk)
        else:
            yield from self.llm.stream(prompt, context, max_new_tokens=max_new_tokens)
