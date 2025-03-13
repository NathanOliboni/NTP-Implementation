# NTP-Implementation

## O que é o NTP?
O **Network Time Protocol (NTP)** é um protocolo usado para sincronizar os relógios de computadores e dispositivos em uma rede. Ele garante que os dispositivos tenham um horário preciso, essencial para diversas aplicações, como logs de sistema, transações financeiras e comunicação entre servidores.

## Como o NTP Funciona?
O NTP opera no modelo **cliente-servidor**, onde clientes solicitam a hora de servidores confiáveis para ajustar seus relógios. O protocolo calcula o deslocamento de tempo (offset) e a latência da rede para melhorar a precisão da sincronização.

### Estrutura do Pacote NTP
O pacote NTP é composto por várias informações essenciais, incluindo:
- **LI (Leap Indicator)**: Indica se haverá um ajuste de segundo intercalado.
- **VN (Version Number)**: Versão do protocolo NTP.
- **Mode**: Define se o pacote é uma requisição, resposta ou outro tipo de mensagem.
- **Stratum**: Indica o nível hierárquico do servidor NTP.
- **Timestamps**: Contêm os registros de tempo usados para calcular o offset e o delay da rede.

### Processo de Sincronização
1. O cliente envia um pacote NTP contendo um timestamp de origem.
2. O servidor responde com os timestamps necessários para calcular a diferença de tempo.
3. O cliente calcula o **offset** e o **delay** com base nos timestamps recebidos.
4. O relógio do cliente é ajustado conforme necessário.

## Estrutura Hierárquica do NTP
O NTP usa uma estrutura de camadas chamada **estratos**:
- **Stratum 0**: Fontes de tempo altamente precisas (ex: relógios atômicos, GPS).
- **Stratum 1**: Servidores que recebem o tempo de uma fonte Stratum 0.
- **Stratum 2+**: Servidores que sincronizam com níveis superiores, mantendo a precisão.

## Segurança no NTP
Para evitar ataques como **spoofing** e **ataques de rejeição de serviço (DoS)**, o NTP pode ser protegido com:
- **Autenticação com HMAC**: Garante que as mensagens não foram alteradas.
- **Configuração de firewalls**: Para restringir o acesso a servidores confiáveis.
- **Monitoração do tráfego NTP**: Para detectar comportamentos suspeitos.

# Cliente NTP com Autenticação

## Visão Geral
O cliente NTP (Network Time Protocol) implementado permite a sincronização do horário do sistema com servidores NTP. Ele suporta autenticação baseada em HMAC-SHA256 para maior segurança e inclui um mecanismo para ajustar o relógio do sistema caso um desvio significativo seja detectado.

## Estrutura do Cliente

### 1. Criação do Pacote NTP
A função responsável pela criação do pacote NTP gera um pacote de requisição seguindo o formato do protocolo, contendo um timestamp de origem que representa o momento em que o pacote foi enviado.

### 2. Autenticação
Caso a autenticação esteja habilitada, o pacote NTP é assinado utilizando HMAC-SHA256 com uma chave secreta compartilhada. Isso garante que a resposta do servidor possa ser validada, prevenindo ataques de spoofing.

### 3. Envio e Recebimento da Resposta
O cliente utiliza um socket UDP para enviar o pacote NTP ao servidor especificado. Ele aguarda a resposta dentro de um tempo limite para evitar bloqueios.

### 4. Processamento da Resposta
Ao receber a resposta, os timestamps contidos no pacote são extraídos para calcular o **offset** e o **delay**. O offset determina a diferença entre o relógio local e o horário fornecido pelo servidor, permitindo a correção do tempo.

### 5. Ajuste do Relógio
Se o offset calculado for significativo, o relógio do sistema é ajustado para corrigir a discrepância. A implementação inclui suporte para Windows e Unix/Linux/MacOS, utilizando chamadas de sistema apropriadas para cada plataforma.

### 6. Argumentos de Linha de Comando
O programa aceita parâmetros para personalizar a execução:
- **`--server`**: Define o servidor NTP a ser consultado.
- **`--port`**: Permite especificar a porta usada na comunicação (padrão 123).
- **`--auth`**: Ativa a autenticação para verificar a integridade da resposta.

# Servidor NTP em Python

## Visão Geral
Este documento descreve a implementação de um servidor NTP (Network Time Protocol) escrito em Python. O servidor é capaz de responder a solicitações de clientes NTP e realizar sincronizações periódicas com servidores NTP externos.

## Principais Funcionalidades
### 1. **Autenticação das Requisições**
- O servidor utiliza HMAC-SHA256 para verificar a autenticidade das requisições, garantindo que apenas clientes autorizados possam sincronizar com ele.
- A chave secreta é obtida da variável de ambiente `NTP_SECRET_KEY`.

### 2. **Sincronização com Servidores NTP Externos**
- O servidor se sincroniza periodicamente com um servidor NTP externo (por padrão `pool.ntp.org`) para manter um relógio preciso.
- Ele calcula o `offset` com base na diferença entre os tempos locais e os tempos recebidos do servidor externo.
- Caso o desvio seja superior a 25 segundos, o relógio do sistema é ajustado imediatamente.

### 3. **Resposta a Solicitações NTP**
- O servidor recebe pacotes NTP dos clientes e processa as requisições.
- Se a autenticação for ativada, ele valida a integridade dos pacotes recebidos.
- O servidor gera um pacote de resposta contendo os timestamps apropriados (referência, recebimento e transmissão).

## Estrutura das Funções
### **Autenticação e Segurança**
- `calcularHMAC(message)`: Calcula o HMAC-SHA256 de um pacote NTP.
- `validarAutenticacao(data)`: Valida se o pacote NTP recebido é autenticado corretamente.

### **Sincronização com Servidores Externos**
- `sincronizarNTP(server, port)`: Envia uma requisição NTP para um servidor externo e ajusta o offset local.
- `ajustarTempoDoSistema(offset_seconds)`: Caso o desvio seja muito grande, ajusta o relógio do sistema.

### **Processamento de Requisições dos Clientes**
- `criarRespostaNTP(originate_timestamp, client_address, sock, autenticar)`: Constrói e envia uma resposta NTP para o cliente.
- `processarCliente(data, client_address, sock)`: Processa os pacotes recebidos e inicia a criação da resposta adequada.

### **Execução do Servidor**
- `servidorNTP(host, port)`: Inicia o servidor, cria threads para processar múltiplos clientes e gerencia a sincronização periódica.




