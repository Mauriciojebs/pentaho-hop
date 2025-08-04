import os
import shutil
import json
from datetime import datetime
import subprocess
import sys

# -------------------------------
# Função para verificar bibliotecas
# -------------------------------
def verificar_instalar_bibliotecas(bibliotecas):
    for biblioteca in bibliotecas:
        try:
            __import__(biblioteca)
            print(f"📦 Biblioteca '{biblioteca}' já está instalada.")
        except ImportError:
            print(f"⚠ Biblioteca '{biblioteca}' não encontrada. Instalando...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", biblioteca])
            print(f"✅ Biblioteca '{biblioteca}' instalada com sucesso.")

bibliotecas_necessarias = []  # Nenhuma externa necessária no momento
verificar_instalar_bibliotecas(bibliotecas_necessarias)

# -------------------------------
# Funções auxiliares
# -------------------------------
def localizar_kettle_properties(caminho):
    """Localiza o arquivo kettle.properties se for passada uma pasta."""
    if os.path.isfile(caminho):
        return caminho
    for root, _, files in os.walk(caminho):
        for f in files:
            if f.lower() == "kettle.properties":
                return os.path.join(root, f)
    raise FileNotFoundError("⚠ Arquivo kettle.properties não encontrado no caminho informado.")

def backup_arquivo(caminho):
    """Cria backup do arquivo com timestamp."""
    if os.path.isfile(caminho):
        pasta = os.path.dirname(caminho)
        nome = os.path.basename(caminho)
        backup_path = os.path.join(pasta, f"{nome}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(caminho, backup_path)
        print(f"🗂 Backup criado: {backup_path}")
        return backup_path
    else:
        print(f"⚠ Arquivo {caminho} não encontrado para backup.")
        return None

def ler_kettle_properties(caminho_kettle, caminho_json_destino):
    """Converte kettle.properties para JSON no formato Hop."""
    variaveis = {"variables": []}
    with open(caminho_kettle, "r", encoding="utf-8") as f:
        for linha in f:
            if "=" in linha and not linha.strip().startswith("#"):
                chave, valor = linha.split("=", 1)
                variaveis["variables"].append({
                    "name": chave.strip(),
                    "value": valor.strip(),
                    "description": ""
                })
    with open(caminho_json_destino, "w", encoding="utf-8") as out:
        json.dump(variaveis, out, indent=2)
    print(f"✅ Variáveis convertidas de {caminho_kettle} para {caminho_json_destino}")
    return caminho_json_destino

def atualizar_hop_config(caminho_hop_config, nome_projeto, caminho_projeto, nome_variaveis):
    """Atualiza hop-config.json com novo projeto e environment."""
    backup_arquivo(caminho_hop_config)

    with open(caminho_hop_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    novo_projeto = {
        "projectName": nome_projeto,
        "projectHome": caminho_projeto,
        "configFilename": "project-config.json"
    }
    novo_environment = {
        "name": nome_variaveis,
        "purpose": "Development",
        "projectName": nome_projeto,
        "configurationFiles": [f"${{PROJECT_HOME}}/{nome_variaveis}.json"]
    }

    if not any(p["projectName"] == nome_projeto for p in config["projectsConfig"]["projectConfigurations"]):
        config["projectsConfig"]["projectConfigurations"].append(novo_projeto)

    if not any(e["name"] == nome_variaveis and e["projectName"] == nome_projeto for e in config["projectsConfig"]["lifecycleEnvironments"]):
        config["projectsConfig"]["lifecycleEnvironments"].append(novo_environment)

    with open(caminho_hop_config, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"✅ hop-config.json atualizado com projeto '{nome_projeto}' e environment '{nome_variaveis}'")

def comparar_migracao(origem, destino):
    relatorio = []
    relatorio.append("=== RELATÓRIO DE MIGRAÇÃO ===")
    relatorio.append(f"Data: {datetime.now()}")
    relatorio.append(f"Origem: {origem}")
    relatorio.append(f"Destino: {destino}")
    relatorio.append("\n--- Comparação de Arquivos ---")

    comparacoes = {
        "Jobs (.kjb)": (".kjb",),
        "Transformations (.ktr)": (".ktr",),
        "Arquivos de variáveis": ("kettle.properties", "variables.json"),
        "Conexões (shared.xml ou metadata)": ("shared.xml", ".json")
    }

    for nome, exts in comparacoes.items():
        origem_count = sum([len([f for f in files if f.lower().endswith(exts)]) for _, _, files in os.walk(origem)])
        destino_count = sum([len([f for f in files if f.lower().endswith(exts)]) for _, _, files in os.walk(destino)])
        status = "✅ OK" if origem_count == destino_count else "⚠ Diferença"
        relatorio.append(f"{nome}: Origem={origem_count} | Destino={destino_count} | {status}")

    return relatorio

def criar_projeto_hop(hop_path, destino, nome_projeto, nome_variaveis):
    projetos_dir = os.path.join(hop_path, "projects")
    os.makedirs(projetos_dir, exist_ok=True)

    projeto_path = os.path.join(projetos_dir, nome_projeto)
    os.makedirs(projeto_path, exist_ok=True)

    for item in os.listdir(destino):
        s = os.path.join(destino, item)
        d = os.path.join(projeto_path, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    variaveis_path = os.path.join(projeto_path, f"{nome_variaveis}.json")
    if not os.path.exists(variaveis_path):
        with open(variaveis_path, "w", encoding="utf-8") as f:
            json.dump({"variables": []}, f, indent=4)

    environment_path = os.path.join(projeto_path, "environment.json")
    with open(environment_path, "w", encoding="utf-8") as f:
        json.dump({
            "name": f"{nome_projeto}_env",
            "project": nome_projeto,
            "variables_file": f"{nome_variaveis}.json",
            "description": f"Ambiente gerado automaticamente para o projeto {nome_projeto}"
        }, f, indent=4)

    return projeto_path, variaveis_path, environment_path

def salvar_relatorio(relatorio, projeto_path):
    relatorio_path = os.path.join(projeto_path, "relatorio_migracao.txt")
    with open(relatorio_path, "w", encoding="utf-8") as f:
        f.write("\n".join(relatorio))
    return relatorio_path

# -------------------------------
# Função principal
# -------------------------------
def main():
    print("=== Automação de Pós-Migração Pentaho → Apache Hop ===")

    origem = input("Informe o caminho de ORIGEM (Pentaho): ").strip()
    destino = input("Informe o caminho de DESTINO (Hop importado): ").strip()
    caminho_kettle_input = input("Informe o caminho do arquivo/pasta kettle.properties: ").strip()
    caminho_kettle = localizar_kettle_properties(caminho_kettle_input)

    caminho_hop_config = input("Informe o caminho do hop-config.json: ").strip()

    relatorio = comparar_migracao(origem, destino)

    hop_path = input("Informe o caminho de instalação do Apache Hop: ").strip()
    nome_projeto = input("Informe o nome do novo projeto Hop: ").strip()
    nome_variaveis = input("Informe o nome do arquivo de variáveis (sem extensão): ").strip()

    projeto_path, variaveis_path, environment_path = criar_projeto_hop(
        hop_path, destino, nome_projeto, nome_variaveis
    )

    caminho_variaveis_json = ler_kettle_properties(caminho_kettle, variaveis_path)
    atualizar_hop_config(caminho_hop_config, nome_projeto, projeto_path, nome_variaveis)

    relatorio.append("\n--- Estrutura Criada ---")
    relatorio.append(f"Projeto criado em: {projeto_path}")
    relatorio.append(f"Arquivo de variáveis: {caminho_variaveis_json}")
    relatorio.append(f"Arquivo de environment: {environment_path}")

    relatorio_path = salvar_relatorio(relatorio, projeto_path)

    print("\n🚀 Concluído!")
    print(f"✅ Projeto '{nome_projeto}' criado em {projeto_path}")
    print(f"✅ Variáveis salvas em {caminho_variaveis_json}")
    print(f"✅ Environment salvo em {environment_path}")
    print(f"✅ hop-config.json atualizado")
    print(f"📄 Relatório detalhado salvo em {relatorio_path}")

# -------------------------------
if __name__ == "__main__":
    main()
