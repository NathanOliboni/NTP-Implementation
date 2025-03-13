import socket
import struct
import time
import threading
import hmac
import hashlib
import os
import sys


NTP_EPOCH = 2208988800
OFFSET = 0.0
MAX_OFFSET_ADJUST = 1.0
SYNC_INTERVAL = 1.0 

SHARED_SECRET = os.environ.get("NTP_SECRET_KEY", "").encode()
if not SHARED_SECRET:
    raise ValueError("Defina NTP_SECRET_KEY no ambiente.")

def calcularHMAC(message):
    return hmac.new(SHARED_SECRET, message, hashlib.sha256).digest()

def validarAutenticacao(data):
    if len(data) not in [48, 84]:
        return False
    if len(data) == 48:
        return True
    
    ntp_packet = data[:48]
    received_hmac = data[52:84]
    return hmac.compare_digest(calcularHMAC(ntp_packet), received_hmac)

def ajustarTempoDoSistema(offset_seconds):
    current_time = time.time()                                              # Obter o tempo atual
    adjusted_time = current_time + offset_seconds                           # Ajustar o tempo com base no offset
    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(adjusted_time))
    print(f"Ajustando o relógio para: {formatted_time}")                    
    try:                                                                    # Ajustar o relógio do sistema (precisa de permissões de administrador)
        if os.name == "nt":  # Windows
            import ctypes
            from datetime import datetime

            dt = datetime.fromtimestamp(adjusted_time)
            ctypes.windll.kernel32.SetSystemTime(
                ctypes.c_uint(dt.year),
                ctypes.c_uint(dt.month),
                ctypes.c_uint(0),  # Dia da semana (opcional, ajustado automaticamente)
                ctypes.c_uint(dt.day),
                ctypes.c_uint(dt.hour),
                ctypes.c_uint(dt.minute),
                ctypes.c_uint(dt.second),
                ctypes.c_uint(0)  # Milissegundos
            )
        else:  # Unix/Linux/MacOS
            os.system(f"sudo date -s '{formatted_time}'")
    except Exception as e:
        print(f"Erro ao ajustar o relógio: {e}")

def sincronizarNTP(server="pool.ntp.org", port=123):
    global OFFSET
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            li_vn_mode = (0 << 6) | (4 << 3) | 3
            t1_unix = time.time()
            originate = int((t1_unix + NTP_EPOCH) * (2**32))
            
            request_packet = struct.pack(
                "!BBBbIIIQQQQ",
                li_vn_mode,
                0, 0, 0,
                0, 0, 0,
                0, 0, 0,
                originate
            )
            
            sock.sendto(request_packet, (server, port))
            response, _ = sock.recvfrom(1024)
            t4_unix = time.time()

            response_data = struct.unpack("!BBBbIIIQQQQ", response[:48])
            t2_ntp = response_data[8]
            t3_ntp = response_data[10]
            
            t2_unix = (t2_ntp / (2**32)) - NTP_EPOCH
            t3_unix = (t3_ntp / (2**32)) - NTP_EPOCH
            
            novo_offset = ((t2_unix - t1_unix) + (t3_unix - t4_unix)) / 2
            OFFSET = novo_offset
            
            print(f"[Sincronização] Offset atualizado: {OFFSET:.6f}s")

            # Se a diferença de tempo for maior que 1 hora, ajuste direto para o tempo do NTP
            if abs(OFFSET) > 25:
                print("[Sincronização] Desvio muito grande, ajustando imediatamente...")
                ajustarTempoDoSistema(t3_unix - time.time())  # Ajusta para o tempo correto
                print("[Sincronização] Tempo ajustado. Reiniciando servidor...")
                
                # Reinicia o próprio script
                python = sys.executable
                os.execl(python, python, *sys.argv)

    except Exception as e:
        print(f"[Sincronização] Erro: {str(e)}")


def criarRespostaNTP(originate_timestamp, client_address, sock, autenticar=False):
    current_time = time.time() + OFFSET
    ntp_time = int((current_time + NTP_EPOCH) * (2**32))
    
    resposta_ntp = struct.pack(
        "!BBBbIIIQQQQ",
        (0 << 6) | (4 << 3) | 4,  # LI=0, VN=4, Mode=4
        1, 0, -20,  # Stratum=1, Poll=0, Precision=-20
        0, 0, 0x4C4F434C,  # Root delay, dispersion, ID
        ntp_time,  # Reference
        originate_timestamp,  # Originate
        ntp_time,  # Receive
        ntp_time  # Transmit
    )
    
    if autenticar:
        resposta_completa = resposta_ntp + struct.pack("!I", 0) + calcularHMAC(resposta_ntp)
    else:
        resposta_completa = resposta_ntp
    
    sock.sendto(resposta_completa, client_address)
    print(f"Resposta para {client_address} (Auth: {autenticar})")

def processarCliente(data, client_address, sock):
    try:
        print(f"Pacote recebido de {client_address} | Tamanho: {len(data)} bytes")
        if not validarAutenticacao(data):
            print(f"Pacote inválido de {client_address}")
            return

        autenticar = len(data) == 84
        pacote = struct.unpack("!BBBbIIIQQQQ", data[:48])
        criarRespostaNTP(pacote[8], client_address, sock, autenticar)
    except Exception as e:
        print(f"Erro no processamento: {str(e)}")

def servidorNTP(host="0.0.0.0", port=123):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))
        print(f"Servidor NTP em {host}:{port}")
        
        def sincronizador():
            while True:
                sincronizarNTP()
                time.sleep(SYNC_INTERVAL)
        
        threading.Thread(target=sincronizador, daemon=True).start()
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                threading.Thread(target=processarCliente, args=(data, addr, sock)).start()
            except KeyboardInterrupt:
                print("\nServidor encerrado")
                break

if __name__ == "__main__":
    servidorNTP()