import threading
import hashlib
import socket
import struct
import psutil
import time
import hmac
import os

'''Como o servidor porderá ser alterado pelo usuário, a variável SERVER foi definida como global'''
SERVER = "pool.ntp.org"
SHARED_SECRET = b"my_secret_key"

def obterEnderecoMAC():
    """Obtém o endereço MAC do dispositivo."""
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:                               # Endereço MAC
                return addr.address
    return "00:00:00:00:00:00"                                              # Retorna um MAC genérico se não for encontrado

def criarPacoteNTP():
    li_vn_mode = (0 << 6) | (4 << 3) | 3                                    # Primeiro byte: LI = 0, Version = 4, Mode = 3 (Client mode)
    stratum = 0                                                             # Outros valores padrão
    poll = 0
    precision = 0
    root_delay = 0
    root_dispersion = 0
    reference_id = 0
    reference_timestamp = 0
    originate_timestamp = int((time.time() + 2208988800) * (2**32))         # T1
    receive_timestamp = 0
    transmit_timestamp = 0
    
    packet = struct.pack(                                                   # Montar o pacote NTP
        "!BBBbIIIQQQQ",                                                     # Formato da string de empacotamento (48 bytes) 
        li_vn_mode,             
        stratum,                
        poll,               
        precision,
        root_delay,
        root_dispersion,
        reference_id,
        reference_timestamp,
        originate_timestamp,
        receive_timestamp,
        transmit_timestamp
    )
    return packet, originate_timestamp

def calcularHMACHex(message, key):
    """Calcula o HMAC-SHA256 de uma mensagem e retorna em bytes."""
    return hmac.new(key, message, hashlib.sha256).digest()

def criarPacoteComAutenticacao(ntp_packet, key):
    """Cria o pacote NTP com HMAC."""
    # Obtém os últimos 4 bytes do endereço MAC
    mac_address = obterEnderecoMAC()
    mac_hex = mac_address.replace(":", "").replace("-", "")  # Remove separadores
    mac_int = int(mac_hex, 16)  # Converte para inteiro de 48 bits
    key_id = mac_int & 0xFFFFFFFF  # Pega apenas os últimos 4 bytes (32 bits)
    # Agora key_id estará dentro do intervalo permitido para struct.pack("!I", key_id)
    key_identifier = struct.pack("!I", key_id)
    hmac_value = calcularHMACHex(ntp_packet, key)                           # Calcular o HMAC da mensagem
    return ntp_packet + key_identifier + hmac_value


def analisarPacoteNTP(data, originate_timestamp, destination_time):
    """Analisa e processa um pacote NTP recebido."""
    unpacked_data = struct.unpack("!BBBbIIIQQQQ", data[:48])                # Desempacotar o pacote NTP
                                                                            # Timestamps extraídos
                                                                            # T1 = Originate Timestamp pego na função criarPacoteNTP
    receive_timestamp = unpacked_data[9]                                    # T2
    transmit_timestamp = unpacked_data[10]                                  # T3
    destination_timestamp = int((destination_time + 2208988800) * (2**32))  # T4

    rtt = (destination_timestamp - originate_timestamp) - (transmit_timestamp - receive_timestamp)
    print(f"Round-Trip Time: {rtt} segundos")                               
    offset = ((receive_timestamp - originate_timestamp) +                   # Calcular Offset: (T2 - T1) + (T3 - T4) / 2
              (transmit_timestamp - destination_timestamp)) / 2.0
    offset_seconds = offset / (2**32)                                       
    ajustarTempoDoSistema(offset_seconds)                                   # Ajustar o relógio local

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

def enviarPacoteNTP(SERVER, PORT=123):
    packet, originate_timestamp = criarPacoteNTP()
    packet_with_auth = criarPacoteComAutenticacao(packet, SHARED_SECRET)        # Adiciona autenticação ao pacote
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(5)                                                      # Timeout de 5 segundos
        sock.sendto(packet, (SERVER, PORT))
        destination_time = time.time()

        try:
            data, _ = sock.recvfrom(1024)
            analisarPacoteNTP(data, originate_timestamp, destination_time)
        except socket.timeout:
            print("Tempo limite atingido ao aguardar resposta.")
            
def validarPacoteNTP(received_packet, key):
    """Valida a autenticação do pacote recebido."""
                                                                                # Dividir os componentes do pacote
    ntp_packet = received_packet[:-36]                                          # Cabeçalho NTP
    received_hmac = received_packet[-32:]                                       # HMAC recebido
                                                                                # Recalcular o HMAC
    calculated_hmac = calcularHMACHex(ntp_packet, key)
                                                                                # Verificar se os HMACs coincidem
    if hmac.compare_digest(received_hmac, calculated_hmac):
        print("Mensagem autenticada com sucesso!")
        return True
    else:
        print("Falha na autenticação da mensagem.")
        return False

if __name__ == "__main__":
    enviarPacoteNTP(SERVER)