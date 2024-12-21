import threading
import socket
import struct
import time
import os

'''Como o servidor porderá ser alterado pelo usuário, a variável SERVER foi definida como global'''
SERVER = "192.168.100.175"

def criarPacoteNTP():
    # Primeiro byte: LI = 0, Version = 4, Mode = 3 (Client mode)
    li_vn_mode = (0 << 6) | (4 << 3) | 3

    # Outros valores padrão
    stratum = 0
    poll = 0
    precision = 0
    root_delay = 0
    root_dispersion = 0
    reference_id = 0
    reference_timestamp = 0
    originate_timestamp = int((time.time() + 2208988800) * (2**32))         # T1
    receive_timestamp = 0
    transmit_timestamp = 0

    # Montar o pacote NTP
    packet = struct.pack(
        "!BBBbIIIQQQQ",         # Formato da string de empacotamento (48 bytes) 
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

def analisarPacoteNTP(data, originate_timestamp, destination_time):
    # Desempacotar os primeiros 48 bytes da resposta
    unpacked_data = struct.unpack("!BBBbIIIQQQQ", data[:48])

    # Timestamps extraídos                                                  # T1 = Originate Timestamp pego na função criarPacoteNTP
    receive_timestamp = unpacked_data[9]                                    # T2
    transmit_timestamp = unpacked_data[10]                                  # T3
    destination_timestamp = int((destination_time + 2208988800) * (2**32))  # T4

    rtt = (destination_timestamp - originate_timestamp) - (transmit_timestamp - receive_timestamp)
    print(f"Round-Trip Time: {rtt} segundos")

    # Calcular Offset: (T2 - T1) + (T3 - T4) / 2
    offset = ((receive_timestamp - originate_timestamp) +
              (transmit_timestamp - destination_timestamp)) / 2.0

    # Ajustar o relógio local
    offset_seconds = offset / (2**32)
    ajustarTempoDoSistema(offset_seconds)

def ajustarTempoDoSistema(offset_seconds):
    # Obter o tempo atual
    current_time = time.time()

    # Ajustar o tempo com base no offset
    adjusted_time = current_time + offset_seconds
    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(adjusted_time))
    print(f"Ajustando o relógio para: {formatted_time}")

    # Ajustar o relógio do sistema (precisa de permissões de administrador)
    try:
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

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(5)  # Timeout de 5 segundos
        sock.sendto(packet, (SERVER, PORT))
        destination_time = time.time()

        try:
            data, _ = sock.recvfrom(1024)
            analisarPacoteNTP(data, originate_timestamp, destination_time)
        except socket.timeout:
            print("Tempo limite atingido ao aguardar resposta.")

if __name__ == "__main__":
    enviarPacoteNTP(SERVER)