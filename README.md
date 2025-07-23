# Inventário de Leitores - ConectCar
Autor: Jonathan Faria
Versão: 1.0.1
23/07/2025

Este projeto realiza a coleta automatizada de dados de leitores conectados, armazena as informações em uma base centralizada MySQL e está configurado para executar periodicamente como um serviço no `systemd`. Ele também utiliza criptografia para proteger os dados sensíveis de conexão.

---

## 📁 Estrutura da Tabela `flex4ExternalData.inventario_leitores`

```sql
CREATE TABLE `inventario_leitores` (
  `nod_id` int(11) NOT NULL,
  `root_id` int(11) DEFAULT NULL,
  `erp` varchar(20) DEFAULT NULL,
  `vpn` varchar(50) DEFAULT NULL,
  `nome` varchar(100) DEFAULT NULL,
  `fabricante` varchar(100) DEFAULT NULL,
  `modeloLeitor` varchar(100) DEFAULT NULL,
  `macAddr` varchar(20) DEFAULT NULL,
  `serialNumber` varchar(50) DEFAULT NULL,
  `fw` varchar(50) DEFAULT NULL,
  `embedded` varchar(50) DEFAULT NULL,
  `owner` varchar(100) DEFAULT NULL,
  `connectedClients` int(11) DEFAULT NULL,
  `ipLeitor` varchar(45) DEFAULT NULL,
  `pista` varchar(100) DEFAULT NULL,
  `ipToten` varchar(45) DEFAULT NULL,
  `portaTotem` int(11) DEFAULT NULL,
  `idLeitor` varchar(50) DEFAULT NULL,
  `pistaSys` varchar(50) DEFAULT NULL,
  `pracaSys` varchar(100) DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `conveniado` varchar(100) DEFAULT NULL,
  `portaSlt` int(11) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `hostname` varchar(100) DEFAULT NULL,
  `host` varchar(100) DEFAULT NULL,
  `data_coleta` datetime DEFAULT NULL,
  PRIMARY KEY (`nod_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

🧠 Funcionamento

    O script inventario_leitores_1.0.0.py:

        Conecta-se ao banco de origem (flex4.node) para obter os hosts ativos.

        Conecta-se a cada host coletando dados da tabela coleta_elementos.

        Insere ou atualiza os dados na tabela flex4ExternalData.inventario_leitores.

    O campo erp é extraído da primeira parte do campo host_name, antes do hífen:

    SUBSTRING_INDEX(host_name, ' - ', 1) AS erp

🔐 Configuração com Criptografia

Os dados sensíveis (usuários, senhas e IPs de banco) são armazenados em um arquivo JSON criptografado.

    Caminho da chave: /opt/flex/inventario_leitores_conectcar/chave.key

    Caminho do arquivo de configuração criptografado: /opt/flex/inventario_leitores_conectcar/db_config.json.enc

Scripts para criptografia e leitura do JSON estão integrados ao projeto.
⚙️ Serviço systemd

O script foi transformado em um serviço que roda a cada hora.
Arquivo de serviço: /etc/systemd/system/inventario_leitores.service

[Unit]
Description=Inventário de Leitores ConectCar
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/flex/inventario_leitores_conectcar/inventario_leitores.py
Restart=on-failure
User=flex

[Install]
WantedBy=multi-user.target

Timer para execução horária: /etc/systemd/system/inventario_leitores.timer

[Unit]
Description=Executa inventario_leitores a cada 1 hora

[Timer]
OnBootSec=10min
OnUnitActiveSec=1h
Unit=inventario_leitores.service

[Install]
WantedBy=timers.target

Ativação

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now inventario_leitores.timer

📄 Logs

    inventario.log: Log de execução padrão.

    inventario_error.log: Apenas erros.

✅ Dependências

    Python 3.x

    pymysql

    logging

    multiprocessing

Instale com:

pip install pymysql

📌 Observações

    O script aplica ON DUPLICATE KEY UPDATE para manter os dados sincronizados.

    A coleta ignora hosts que não respondem ou que não possuam dados.

📂 Estrutura do Projeto

/opt/flex/inventario_leitores_conectcar/
├── inventario_leitores.py
├── db_config.json.enc
├── chave.key
├── inventario.log
├── inventario_error.log

🗂 Estrutura dos arquivos importantes

    Script principal:
    /opt/flex/inventario_leitores_conectcar/inventario_leitores.py

    Configuração criptografada:
    /opt/flex/inventario_leitores_conectcar/db_config.json.enc

    Chave de criptografia:
    /opt/flex/inventario_leitores_conectcar/chave.key

    Logs:

        inventario.log: log geral

        inventario_error.log: log de erros

🔐 Gerenciamento seguro de configurações

As credenciais e parâmetros de conexão foram extraídas do script principal e armazenadas em um arquivo JSON criptografado.
1. Estrutura do JSON original

{
  "banco_node_config": {
    "host": "10.202.11.115",
    "user": "flexvision",
    "password": "g4medCFB4u0LNUB@",
    "database": "flex4"
  },
  "banco_remoto_config": {
    "user": "conectpark",
    "password": "iN1OgTb78EkhdqU",
    "database": "coleta_elementos"
  },
  "banco_destino_config": {
    "host": "10.202.11.115",
    "user": "flexvision",
    "password": "g4medCFB4u0LNUB@",
    "database": "flex4ExternalData"
  }
}

2. Processo de criptografia (executado uma vez)

from cryptography.fernet import Fernet
import json

# Gera e salva a chave
key = Fernet.generate_key()
with open("/opt/flex/inventario_leitores_conectcar/chave.key", "wb") as key_file:
    key_file.write(key)

# Lê e criptografa o JSON
with open("/tmp/db_config.json", "rb") as f:
    data = f.read()

fernet = Fernet(key)
encrypted = fernet.encrypt(data)

# Salva criptografado
with open("/opt/flex/inventario_leitores_conectcar/db_config.json.enc", "wb") as f:
    f.write(encrypted)

    ⚠️ Apague o arquivo original /tmp/db_config.json após criptografar!

3. Como o script principal carrega as configurações

import json
from cryptography.fernet import Fernet

def carregar_configuracoes():
    with open("/opt/flex/inventario_leitores_conectcar/chave.key", "rb") as key_file:
        key = key_file.read()

    fernet = Fernet(key)

    with open("/opt/flex/inventario_leitores_conectcar/db_config.json.enc", "rb") as enc_file:
        encrypted_data = enc_file.read()

    decrypted_data = fernet.decrypt(encrypted_data)
    return json.loads(decrypted_data)

config = carregar_configuracoes()

banco_node_config = config['banco_node_config']
banco_remoto_config = config['banco_remoto_config']
banco_destino_config = config['banco_destino_config']

4. Permissões recomendadas

chmod 600 /opt/flex/inventario_leitores_conectcar/chave.key
chmod 600 /opt/flex/inventario_leitores_conectcar/db_config.json.enc

✅ Apenas o usuário responsável pela execução do serviço systemd deve ter acesso.

🧪 Testes

Você pode executar o script manualmente para testar:

python3 /opt/flex/inventario_leitores_conectcar/inventario_leitores.py

Para dúvidas ou manutenção, consulte o responsável técnico do projeto ou revise os logs de erro.
