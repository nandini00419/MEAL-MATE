import requests
import os
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.environ.get('SARVAM_API_KEY', 'sk_756ky6ne_LMPV9QHtDfx2EBmN3HCzB94v')

def test_sarvam():
    url = "https://api.sarvam.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sarvam-105b",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    try:
        print("Testing Sarvam API...")
        print(f"URL: {url}")
        print(f"API Key: {SARVAM_API_KEY[:10]}...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS!")
            data = response.json()
            print(f"Response: {data['choices'][0]['message']['content']}")
        else:
            print(f"FAILED!")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test_sarvam()
