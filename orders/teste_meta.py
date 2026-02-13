import requests
import time
import hashlib
import json

# --- PREENCHA SEUS DADOS AQUI ---
PIXEL_ID = "1463841368643880" 
ACCESS_TOKEN = "EAAK2xtj5h7YBQl5oBK98Ws1TrXekG2vU9XOviYGOKmF6LUhMtdD0teYhFqTwCXaIKYZAjMxoVTYJDJRQ6FQJfhpHoJk0swB2QKtWX3gh5Sz3atcu5LyXKisu39fCy9XYyV6TZBhYSaTuQhRxaKZB23Az7ELYK2otZBZBMZAPtJpl87ZAXtmvsPN1ZC7wygJNQfqShQZDZD"
TEST_CODE = "TEST74749" # Pegue na aba "Testar Eventos" do Facebook
# --------------------------------

def run_test():
    print(f"--- TESTANDO CONEXÃO COM META (Pixel: {PIXEL_ID}) ---")
    
    # 1. Prepara dados fake
    email_hash = hashlib.sha256("denny@teste.com".encode('utf-8')).hexdigest()
    
    payload = {
        "data": [
            {
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "action_source": "website",
                "event_source_url": "http://localhost:8000/teste",
                "user_data": {
                    "em": [email_hash],
                    "client_ip_address": "127.0.0.1",
                    "client_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                },
                "custom_data": {
                    "currency": "BRL",
                    "value": 150.00
                },
                "event_id": f"TESTE_{int(time.time())}"
            }
        ],
        "test_event_code": TEST_CODE # Envia o código explicitamente
    }

    # 2. Envia
    url = f"https://graph.facebook.com/v19.0/{PIXEL_ID}/events?access_token={ACCESS_TOKEN}"
    
    try:
        print("Enviando requisição...")
        response = requests.post(url, json=payload)
        
        print(f"\nSTATUS CODE: {response.status_code}")
        print("RESPOSTA COMPLETA:")
        print(json.dumps(response.json(), indent=4))
        
        if response.status_code == 200:
            print("\n✅ SUCESSO! O evento deve aparecer na aba 'Testar Eventos' agora.")
        else:
            print("\n❌ FALHA! Leia a mensagem de erro acima (message/type/code).")
            
    except Exception as e:
        print(f"Erro de conexão: {e}")

if __name__ == "__main__":
    run_test()