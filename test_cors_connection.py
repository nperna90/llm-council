import requests
import sys

def test_cors_connection():
    print("TEST CONNESSIONE BACKEND E CORS\n")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    # Test 1: Health Check
    print("\n1. Test Health Check (GET /)")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print(f"   OK - Backend raggiungibile: {response.json()}")
        else:
            print(f"   ERRORE - Status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"   ERRORE - Backend non raggiungibile su {base_url}")
        print("   Verifica che il backend sia in esecuzione!")
        return False
    except Exception as e:
        print(f"   ERRORE - {e}")
        return False
    
    # Test 2: CORS Preflight (OPTIONS)
    print("\n2. Test CORS Preflight (OPTIONS /api/token)")
    try:
        response = requests.options(
            f"{base_url}/api/token",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=5
        )
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
        }
        
        print(f"   Status Code: {response.status_code}")
        print(f"   CORS Headers ricevuti:")
        for key, value in cors_headers.items():
            if value:
                print(f"      {key}: {value}")
            else:
                print(f"      {key}: MANCANTE")
        
        if response.status_code == 200 and cors_headers["Access-Control-Allow-Origin"]:
            print("   OK - CORS Preflight funziona!")
        else:
            print("   ERRORE - CORS Preflight non configurato correttamente")
            return False
            
    except Exception as e:
        print(f"   ERRORE - {e}")
        return False
    
    # Test 3: POST Request (simula login)
    print("\n3. Test POST Request (simula login)")
    try:
        response = requests.post(
            f"{base_url}/api/token",
            headers={
                "Origin": "http://localhost:5173",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "username": "test_user",
                "password": "test_password"
            },
            timeout=5
        )
        
        # Verifica header CORS nella risposta
        cors_origin = response.headers.get("Access-Control-Allow-Origin")
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Access-Control-Allow-Origin: {cors_origin}")
        
        # Prova a leggere il body per vedere l'errore
        try:
            error_detail = response.json()
            print(f"   Dettaglio errore: {error_detail.get('detail', 'N/A')}")
        except:
            print(f"   Response body: {response.text[:200]}")
        
        if cors_origin:
            print("   OK - Header CORS presente nella risposta POST")
        else:
            print("   ATTENZIONE - Header CORS mancante")
            print("   NOTA: Il backend potrebbe non essere stato riavviato con le nuove modifiche")
        
        # Il login fallirà (credenziali errate), ma vogliamo solo verificare CORS
        if response.status_code in [200, 400, 401]:
            print("   OK - Richiesta POST processata correttamente")
            return True
        elif response.status_code == 500:
            print("   ERRORE 500 - Problema interno del server")
            print("   IMPORTANTE: Riavvia il backend per applicare le modifiche CORS!")
            if cors_origin:
                print("   Tuttavia, gli header CORS sono presenti, quindi il CORS funziona.")
                return True
            else:
                return False
        else:
            print(f"   ERRORE - Status code inatteso: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ERRORE - {e}")
        return False
    
    print("\n" + "=" * 50)
    print("RISULTATO: Connessione e CORS configurati correttamente!")
    print("Il frontend dovrebbe poter connettersi al backend.")
    return True

if __name__ == "__main__":
    success = test_cors_connection()
    sys.exit(0 if success else 1)
