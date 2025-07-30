import pymysql
from datetime import datetime
from multiprocessing import Pool, TimeoutError
import time
import logging
import socket
import json
from cryptography.fernet import Fernet

# --- CONFIGURAÇÃO DOS LOGS ---
logger = logging.getLogger("inventario_logger")
logger.setLevel(logging.DEBUG)

# Log geral
fh_info = logging.FileHandler("inventario.log")
fh_info.setLevel(logging.INFO)
fh_info.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Log de erros
fh_error = logging.FileHandler("inventario_error.log")
fh_error.setLevel(logging.ERROR)
fh_error.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger.addHandler(fh_info)
logger.addHandler(fh_error)

# --- CONFIGS ---
MAX_PROCESSES = 5
TIMEOUT_POR_HOST = 30  # segundos

def carregar_configuracoes():
    with open("/opt/flex/inventario_leitores_conectcar/chave.key", "rb") as key_file:
        key = key_file.read()

    fernet = Fernet(key)

    with open("/opt/flex/inventario_leitores_conectcar/db_config.json.enc", "rb") as enc_file:
        encrypted_data = enc_file.read()

    decrypted_data = fernet.decrypt(encrypted_data)
    return json.loads(decrypted_data)

config = carregar_configuracoes()

banco_node_config = config['banco_node']
banco_remoto_config = config['banco_remoto']
banco_destino_config = config['banco_destino']


colunas = [
    'nod_id', 'root_id',
    'vpn', 'erp', 'nome', 'fabricante', 'modeloLeitor', 'macAddr', 'serialNumber', 'fw',
    'embedded', 'owner', 'connectedClients', 'ipLeitor', 'pista', 'ipToten', 'portaTotem',
    'idLeitor', 'pistaSys', 'pracaSys', 'tipo', 'conveniado', 'portaSlt', 'status', 'hostname', 'host',
    'data_coleta'
]

def buscar_hosts():
    try:
        conn = pymysql.connect(**banco_node_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT n.nod_id as root_id, n.ip, SUBSTRING_INDEX(n.host_name, ' - ', 1) AS erp, TRIM(SUBSTRING_INDEX(n.host_name, ' - ', -1)) AS host_name, n1.nod_id, n1.host_name as leitor, SUBSTRING_INDEX(SUBSTRING_INDEX(n1.instance, 'ARG1=', -1), ';', 1) AS instance
                FROM node n
                INNER JOIN node n1 ON n1.root_id = n.nod_id
                WHERE n1.mol_id = 10731 AND n1.live = 1 AND n.live = 1
            """)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao buscar hosts: {e}")
        return []

def inserir_dados_na_tabela(dados):
    try:
        conn = pymysql.connect(**banco_destino_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            placeholders = ','.join(['%s'] * len(colunas))
            updates = ', '.join([f"{col}=VALUES({col})" for col in colunas if col != 'nod_id'])

            sql = f"""
                INSERT INTO inventario_leitores ({','.join(colunas)})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {updates}
            """

            valores = [tuple(row.get(col, None) for col in colunas) for row in dados]
            cursor.executemany(sql, valores)
            conn.commit()
    except Exception as e:
        logger.error(f"Erro ao inserir dados no destino: {e}")

def processar_host(info):
    socket.setdefaulttimeout(10)

    host_ip = info['ip']
    filtro_ip = info['instance']
    nod_id = info['nod_id']
    root_id = info['root_id']
    nome = info['host_name']
    erp = info['erp']

    logger.info(f"[{host_ip}] ▶️ Iniciando coleta...")

    try:
        conn = pymysql.connect(
            host=host_ip,
            user=banco_remoto_config['user'],
            password=banco_remoto_config['password'],
            database=banco_remoto_config['database'],
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM coleta_elementos WHERE ipLeitor = %s", (filtro_ip,))
            rows = cursor.fetchall()
            if not rows:
                logger.info(f"[{host_ip}] ⚠️ Nenhum dado encontrado para ipLeitor = {filtro_ip}")
                return

            for row in rows:
                row['host'] = host_ip
                row['data_coleta'] = datetime.now()
                row['nod_id'] = nod_id
                row['root_id'] = root_id
                row['nome'] = nome
                row['erp'] = erp

            inserir_dados_na_tabela(rows)
            logger.info(f"[{host_ip}] ✅ {len(rows)} registros inseridos.")
    except Exception as e:
        logger.error(f"[{host_ip}] ❌ ERRO: {e}")

def main():
    hosts = buscar_hosts()
    logger.info(f"🌐 {len(hosts)} hosts encontrados.")

    with Pool(processes=MAX_PROCESSES) as pool:
        results = []

        for host_info in hosts:
            result = pool.apply_async(processar_host, (host_info,))
            results.append((result, host_info['ip']))

        for result, ip in results:
            try:
                result.get(timeout=TIMEOUT_POR_HOST)
            except TimeoutError:
                logger.error(f"[{ip}] ⛔ Timeout (>{TIMEOUT_POR_HOST}s)")
            except Exception as e:
                logger.error(f"[{ip}] ❌ Erro: {e}")

    logger.info("🏁 Finalizado.")

if __name__ == '__main__':
    main()

