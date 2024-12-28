import socket
import struct
import time
import threading

'''
Ponto para observar depois, há um problema de sincronização, por exemplo, se o horário do servidor for adiantado ou atrasado, 
o cliente não conseguirá se sincronizar com o servidor, pois o horário do servidor é o horário de referência para o cliente, 
fazendo com que o cliente não fique com o horário correto.
'''

NTP_EPOCH = 2208988800                                              # 1 de janeiro de 1900
OFFSET = 0                                                          # Offset inicial, será ajustado pela sincronização
MAX_OFFSET_ADJUST = 5                                               # Máximo ajuste permitido em segundos
SYNC_INTERVAL = 3                                                   # Intervalo de sincronização em segundos


def sincronizarNTP(server="pool.ntp.org", port=123):
    """Sincroniza com um servidor NTP confiável e ajusta o offset global."""
    global OFFSET
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            li_vn_mode = (0 << 6) | (4 << 3) | 3                    # LI = 0, Version = 4, Mode = 3 (Client mode)
            request_packet = struct.pack(
                "!BBBbIIIQQQQ",
                li_vn_mode,
                0, 0, 0,                                            # stratum, poll, precision
                0, 0, 0,                                            # root_delay, root_dispersion, reference_id
                0, 0, 0,                                            # reference, originate, receive timestamps
                int((time.time() + NTP_EPOCH) * (2**32))            # transmit timestamp
            )
            sock.sendto(request_packet, (server, port))
            response, _ = sock.recvfrom(1024)
            response_data = struct.unpack("!BBBbIIIQQQQ", response[:48])

                                                                    # Timestamps da resposta
            t1 = struct.unpack("!Q", request_packet[40:48])[0]      # Originate timestamp
            t2 = response_data[9]                                   # Receive timestamp
            t3 = response_data[10]                                  # Transmit timestamp
            t4 = int((time.time() + NTP_EPOCH) * (2**32))           # Destination timestamp

            # Calcular offset
            novo_offset = ((t2 - t1) + (t3 - t4)) / 2.0 / (2**32)

            # Ajustar gradualmente o offset
            desvio = abs(novo_offset - OFFSET)
            if desvio > MAX_OFFSET_ADJUST:
                print(f"Ajuste grande detectado ({desvio:.6f}s). Aplicando correção gradual.")
                OFFSET += (novo_offset - OFFSET) / 2
            else:
                OFFSET = novo_offset

            print(f"Offset atualizado: {OFFSET:.6f} segundos")
    except Exception as e:
        print(f"Erro ao sincronizar com NTP: {e}")

def criarRespostaNTP(originate_timestamp, client_address, sock):
    """Cria e envia uma resposta NTP ao cliente."""
    global OFFSET
    current_time = time.time() + OFFSET

    receive_timestamp = int((current_time + NTP_EPOCH) * (2**32))   # T2 ajustado
    transmit_timestamp = int((current_time + NTP_EPOCH) * (2**32))  # T3 ajustado

    li_vn_mode = (0 << 6) | (4 << 3) | 4                            # LI = 0, Version = 4, Mode = 4 (Server mode)
    stratum = 1
    poll = 0
    precision = -20
    root_delay = 0
    root_dispersion = 0
    reference_id = 0x4C4F434C                                       # "LOCL"
    reference_timestamp = int((current_time + NTP_EPOCH) * (2**32)) # Horário de referência ajustado

    resposta = struct.pack(
        "!BBBbIIIQQQQ",
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

    sock.sendto(resposta, client_address)
    print(f"Resposta enviada para {client_address}")


def processarCliente(data, client_address, sock):
    """Processa pacotes NTP recebidos de clientes."""
    try:
        pacote = struct.unpack("!BBBbIIIQQQQ", data[:48])
        originate_timestamp = pacote[8]
        criarRespostaNTP(originate_timestamp, client_address, sock)
    except Exception as e:
        print(f"Erro ao processar pacote de {client_address}: {e}")


def servidorNTP(host="0.0.0.0", port=123):
    """Inicia o servidor NTP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))
        print(f"Servidor NTP iniciado em {host}:{port}")

                                                                    # Thread para sincronização periódica
        def atualizar_offset():
            while True:
                sincronizarNTP()
                time.sleep(SYNC_INTERVAL)                           # Sincroniza a cada SYNC_INTERVAL segundos

        threading.Thread(target=atualizar_offset, daemon=True).start()

        while True:
            try:
                data, client_address = sock.recvfrom(1024)
                print(f"Pacote recebido de {client_address}")
                threading.Thread(target=processarCliente, args=(data, client_address, sock)).start()
            except KeyboardInterrupt:
                print("Servidor encerrado.")
                break
            except Exception as e:
                print(f"Erro no servidor: {e}")

if __name__ == "__main__":
    servidorNTP()