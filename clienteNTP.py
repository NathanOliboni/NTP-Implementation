import socket
import struct
import time
import argparse
import hmac
import hashlib
import os

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
    return pacote_ntp + struct.pack("!I", 0) + hmac.new(SHARED_SECRET, pacote_ntp, hashlib.sha256).digest()

def validarResposta(data):
    return hmac.compare_digest(
        hmac.new(SHARED_SECRET, data[:48], hashlib.sha256).digest(),
        data[52:84]
    )

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
                print("❌ Autenticação falhou!")
                return

            unpacked = struct.unpack("!BBBbIIIQQQQ", data.ljust(48, b'\x00')[:48])
            
            t2_ntp = unpacked[9]
            t3_ntp = unpacked[10]
            
            t1_unix = (t1_ntp / (2**32)) - NTP_EPOCH
            t2_unix = (t2_ntp / (2**32)) - NTP_EPOCH
            t3_unix = (t3_ntp / (2**32)) - NTP_EPOCH
            
            offset = ((t2_unix - t1_unix) + (t3_unix - t4_unix)) / 2
            
            if abs(offset) > 3600:
                print(f"⚠ Offset inválido: {offset}")
                return
            
            print(f"⏱ Offset: {offset:.6f}s | Hora: {time.ctime(time.time() + offset)}")
            
        except socket.timeout:
            print("⌛ Timeout: Sem resposta")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente NTP")
    parser.add_argument("--server", default="pool.ntp.org")
    parser.add_argument("--port", type=int, default=123)
    parser.add_argument("--auth", action="store_true")
    args = parser.parse_args()
    
    if args.auth and not SHARED_SECRET:
        print("❌ Chave secreta não configurada!")
        exit(1)
        
    executarCliente(args.server, args.port, args.auth)