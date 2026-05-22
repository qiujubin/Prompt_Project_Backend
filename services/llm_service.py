from utils.httpx_compat import httpx_compat as httpx
import json
import hashlib
import random
import time
from typing import List, Dict, Any
from core.config import settings

class TranslationService:
    def __init__(self):
        # DeepSeek Config
        self.llm_api_key = settings.DEEPSEEK_API_KEY
        self.llm_api_url = settings.DEEPSEEK_API_URL
        
        # Baidu Config
        self.baidu_appid = settings.BAIDU_TRANS_APPID
        self.baidu_key = settings.BAIDU_TRANS_KEY
        self.baidu_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    async def translate(self, items: List[Dict[str, str]], engine: str = "baidu") -> List[Dict[str, str]]:
        """
        统一翻译入口
        
        Args:
            items: List of dicts
            engine: 'baidu' | 'deepseek'
        """
        if engine == "deepseek":
            return await self._translate_with_llm(items)
        else:
            return await self._translate_with_baidu(items)

    async def _translate_with_baidu(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """使用百度翻译API"""
        if not items:
            return []
            
        async with httpx.AsyncClient() as client:
            for item in items:
                try:
                    # Determine direction
                    q = ""
                    from_lang = "auto"
                    to_lang = "en"
                    
                    if item.get("word") and not item.get("translation"):
                        # EN -> ZH
                        q = item["word"]
                        from_lang = "en"
                        to_lang = "zh"
                    elif item.get("translation") and not item.get("word"):
                        # ZH -> EN
                        q = item["translation"]
                        from_lang = "zh"
                        to_lang = "en"
                    else:
                        continue # Skip if both or neither present
                        
                    salt = str(random.randint(32768, 65536))
                    sign_str = self.baidu_appid + q + salt + self.baidu_key
                    sign = hashlib.md5(sign_str.encode()).hexdigest()
                    
                    params = {
                        "q": q,
                        "from": from_lang,
                        "to": to_lang,
                        "appid": self.baidu_appid,
                        "salt": salt,
                        "sign": sign
                    }
                    
                    resp = await client.get(self.baidu_url, params=params, timeout=10.0)
                    result = resp.json()
                    
                    if "trans_result" in result:
                        dst = result["trans_result"][0]["dst"]
                        if to_lang == "zh":
                            item["translation"] = dst
                        else:
                            item["word"] = dst
                    
                    # Avoid rate limit (Baidu free api limit)
                    time.sleep(0.1) 
                    
                except Exception as e:
                    print(f"Baidu translation error for {q}: {e}")
                    
        return items

    async def _translate_with_llm(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        使用 LLM 批量翻译补全提示词。
        """
        if not items:
            return []

        # 构造 Prompt
        prompt_content = json.dumps(items, ensure_ascii=False)
        system_prompt = (
            """You are a professional translator specialized in AI art prompts (Stable Diffusion).  
            The user will provide a JSON array of objects, each containing two fields: "word" (English) and "translation" (Chinese).  
            Some fields may be empty strings ("").  

            Your task:  
              - If "word" is non-empty and "translation" is empty → translate "word" from English to Chinese.  
            - If "translation" is non-empty and "word" is empty → translate "translation" from Chinese to English.  
            - If both are non-empty or both are empty, leave them unchanged.    

            Rules:  
            1. Preserve all punctuation, brackets, weights, and syntax exactly as in the original (e.g., "(masterpiece:1.2)", "[solo]", "1girl" must remain intact in structure).  
            2. Use standard, widely accepted translations common in the Stable Diffusion Chinese community (e.g., "masterpiece" → "杰作", "best quality" → "最佳质量").  
            3. Do NOT add, remove, or reorder any elements. Maintain the exact input order.  
            4. Output ONLY a valid, compact JSON array string compliant with RFC 8259 — no markdown, no explanations, no extra whitespace or comments.  

            Input:"""
        )

        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_content}
            ],
            "temperature": 0.1,
            "stream": False
        }

        try:
            async with httpx.AsyncClient() as client:
                # 假设 deepseek 兼容 OpenAI 格式
                url = f"{self.llm_api_url}/chat/completions"
                response = await client.post(url, json=data, headers=headers, timeout=60.0)
                
                if response.status_code != 200:
                    print(f"LLM API Error: {response.text}")
                    return items # Fallback: return original

                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 清理可能的 markdown 标记
                content = content.replace("```json", "").replace("```", "").strip()
                
                translated_items = json.loads(content)
                return translated_items

        except Exception as e:
            print(f"Translation failed: {e}")
            return items

translation_service = TranslationService()
