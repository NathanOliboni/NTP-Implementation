import socket
import struct
import time
import argparse
import hmac
import hashlib
import os
import sys

NTP_EPOCH = 2208988800

SHARED_SECRET = os.environ.get("NTP_SECRET_KEY", "").encode()


def criarPacoteNTP():
    li_vn_mode = (0 << 6) | (4 << 3) | 3
    originate = int((time.time() + NTP_EPOCH) * (2**32))
    return struct.pack(
        "!BBBbIIIQQQQ",
        li_vn_mode,
        0, 0, 0,
        0, 0, 0,
        0, 0, 0,
        originate
    ), originate

def criarPacoteAutenticado(pacote_ntp):
    return pacote_ntp + hmac.new(SHARED_SECRET, pacote_ntp, hashlib.sha256).digest()

def validarResposta(data):
    return hmac.compare_digest(
        hmac.new(SHARED_SECRET, data[:48], hashlib.sha256).digest(),
        data[48:80]
    )
    
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


def executarCliente(server, port, usar_autenticacao):
    pacote_ntp, t1_ntp = criarPacoteNTP()
    data = criarPacoteAutenticado(pacote_ntp) if usar_autenticacao else pacote_ntp

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(5)
        sock.sendto(data, (server, port))
        
        try:
            data, _ = sock.recvfrom(1024)
            t4_unix = time.time()
            
            if usar_autenticacao and not validarResposta(data):
                print("Autenticação falhou!")
                return

            unpacked = struct.unpack("!BBBbIIIQQQQ", data.ljust(48, b'\x00')[:48])
            
            t2_ntp = unpacked[9]
            t3_ntp = unpacked[10]
            
            t1_unix = (t1_ntp / (2**32)) - NTP_EPOCH
            t2_unix = (t2_ntp / (2**32)) - NTP_EPOCH
            t3_unix = (t3_ntp / (2**32)) - NTP_EPOCH
            
            offset = ((t2_unix - t1_unix) + (t3_unix - t4_unix)) / 2
            
            if abs(offset) > 25:
                print("Ajustando tempo do sistema")
                ajustarTempoDoSistema(offset)
                return
            
            print(f"Offset: {offset:.6f}s | Hora: {time.ctime(time.time() + offset)}")
            
        except socket.timeout:
            print("Timeout: Sem resposta")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente NTP")
    parser.add_argument("--server", default="pool.ntp.org")
    parser.add_argument("--port", type=int, default=123)
    parser.add_argument("--auth", action="store_true")
    args = parser.parse_args()
    
    if args.auth and not SHARED_SECRET:
        print("Chave secreta não configurada!")
        exit(1)
        
    executarCliente(args.server, args.port, args.auth)
