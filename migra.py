import os
import shutil
import json
import subprocess
import platform
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import charset_normalizer

# =========================================================
# FUNÇÕES AUXILIARES 2.3
# =========================================================

def backup_arquivo(caminho):
    """Cria backup de um arquivo antes de modificá-lo."""
    if os.path.isfile(caminho):
        backup_path = caminho + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(caminho, backup_path)
        return backup_path
    return None

def ler_kettle_properties(caminho_kettle, caminho_json_destino):
    """Converte kettle.properties em JSON de variáveis para o Hop, detectando encoding."""
    # Detecta a codificação
    with open(caminho_kettle, "rb") as f:
        detectado = charset_normalizer.from_bytes(f.read()).best()
        encoding_detectado = detectado.encoding or "utf-8"

    variaveis = {"variables": []}
    with open(caminho_kettle, "r", encoding=encoding_detectado, errors="ignore") as f:
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
    return caminho_json_destino

def atualizar_hop_config(caminho_hop_config, nome_projeto, caminho_projeto, nome_variaveis):
    """Atualiza hop-config.json adicionando novo projeto e environment."""
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

    if not any(e["name"] == nome_variaveis for e in config["projectsConfig"]["lifecycleEnvironments"]):
        config["projectsConfig"]["lifecycleEnvironments"].append(novo_environment)

    with open(caminho_hop_config, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def contar_artefatos(caminho, extensoes):
    """Conta arquivos com extensões específicas em uma pasta."""
    return sum([len([f for f in files if f.lower().endswith(extensoes)]) for _, _, files in os.walk(caminho)])

def criar_projeto_hop(hop_path, destino, nome_projeto, nome_variaveis, caminho_kettle):
    """Cria estrutura de projeto Hop com variáveis, environment e config."""
    projetos_dir = os.path.join(hop_path, "projects")
    os.makedirs(projetos_dir, exist_ok=True)
    projeto_path = os.path.join(projetos_dir, nome_projeto)
    os.makedirs(projeto_path, exist_ok=True)

    # Copia artefatos migrados para pasta do projeto
    for item in os.listdir(destino):
        s = os.path.join(destino, item)
        d = os.path.join(projeto_path, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    # Cria arquivo de variáveis
    variaveis_path = os.path.join(projeto_path, f"{nome_variaveis}.json")
    if os.path.exists(caminho_kettle):
        ler_kettle_properties(caminho_kettle, variaveis_path)
    else:
        with open(variaveis_path, "w", encoding="utf-8") as f:
            json.dump({"variables": []}, f, indent=4)

    # Cria environment.json
    environment_path = os.path.join(projeto_path, "environment.json")
    with open(environment_path, "w", encoding="utf-8") as f:
        json.dump({
            "name": f"{nome_projeto}_env",
            "project": nome_projeto,
            "variables_file": f"{nome_variaveis}.json",
            "description": f"Ambiente para {nome_projeto}"
        }, f, indent=4)

    # Cria project-config.json
    project_config_path = os.path.join(projeto_path, "project-config.json")
    with open(project_config_path, "w", encoding="utf-8") as f:
        json.dump({"projectName": nome_projeto}, f, indent=4)

    return projeto_path, variaveis_path, environment_path, project_config_path

def salvar_relatorio(relatorio, projeto_path):
    """Salva relatório de migração em arquivo de texto."""
    relatorio_path = os.path.join(projeto_path, "relatorio_migracao.txt")
    with open(relatorio_path, "w", encoding="utf-8") as f:
        f.write(relatorio)
    return relatorio_path

# =========================================================
# EXECUTAR HOP-IMPORT COM LOG E PROGRESSO
# =========================================================
def executar_hop_import_com_log(hop_import_cmd, origem, destino):
    """Executa hop-import mostrando log e progresso."""
    process = subprocess.Popen(
        [hop_import_cmd, "-t=kettle", f"-i={origem}", f"-o={destino}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    line_count = 0
    for line in process.stdout:
        line_count += 1
        txt_log.insert(tk.END, line)
        txt_log.see(tk.END)

        # Atualiza barra de progresso (estimativa)
        progress_bar["value"] = min(100, (line_count % 100))
        root.update()

    process.wait()
    progress_bar["value"] = 100
    return process.returncode

# =========================================================
# PROCESSO PRINCIPAL
# =========================================================
def executar_processo():
    hop_import_cmd = entry_hop_import.get()
    origem = entry_origem.get()
    destino = entry_destino.get()
    caminho_kettle = entry_kettle.get()
    nome_projeto = entry_nome_projeto.get()
    nome_variaveis = entry_nome_variaveis.get()

    hop_path = os.path.dirname(hop_import_cmd)
    hop_config = os.path.join(os.path.dirname(hop_path), "hop\\config", "hop-config.json")

    if not os.path.exists(destino):
        os.makedirs(destino)

    txt_log.delete("1.0", tk.END)
    txt_log.insert(tk.END, "=== Executando hop-import... ===\n")
    retorno = executar_hop_import_com_log(hop_import_cmd, origem, destino)
    txt_log.insert(tk.END, f"hop-import finalizado com código: {retorno}\n\n")

    # Cria projeto Hop
    projeto_path, var_path, env_path, proj_config_path = criar_projeto_hop(hop_path, destino, nome_projeto, nome_variaveis, caminho_kettle)
    atualizar_hop_config(hop_config, nome_projeto, destino, nome_variaveis)

    # Comparação de artefatos
    jobs_pdi = contar_artefatos(origem, (".kjb",))
    jobs_hop = contar_artefatos(destino, (".hwf",))
    ktr_pdi = contar_artefatos(origem, (".ktr",))
    ktr_hop = contar_artefatos(destino, (".hpl",))
    conexoes_pdi = contar_artefatos(origem, ("shared.xml",))
    conexoes_hop = contar_artefatos(destino, (".json",))

    # Cria relatório
    relatorio = f"""
Resultado hop-import: {'Sucesso' if retorno == 0 else 'Erro'}

--- Comparação de Arquivos ---
Jobs: Pentaho={jobs_pdi} | Hop={jobs_hop}
Transformations: Pentaho={ktr_pdi} | Hop={ktr_hop}
Conexões: Pentaho={conexoes_pdi} | Hop={conexoes_hop}

--- Estrutura Criada ---
Projeto criado: {projeto_path}
Arquivo de variáveis: {var_path}
Arquivo de environment: {env_path}
Arquivo project-config.json: {proj_config_path}

Agora basta abrir o Apache Hop e selecionar o projeto '{nome_projeto}' para continuar.
"""
    relatorio_path = salvar_relatorio(relatorio, projeto_path)

    # Abre relatório sempre
    try:
        if platform.system() == "Windows":
            os.startfile(relatorio_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", relatorio_path])
        else:
            subprocess.run(["xdg-open", relatorio_path])
    except Exception as e:
        txt_log.insert(tk.END, f"Não foi possível abrir o relatório automaticamente: {e}\n")

    messagebox.showinfo("Migração concluída", "Migração finalizada com sucesso!")

# =========================================================
# INTERFACE TKINTER
# =========================================================
root = tk.Tk()
root.title("Migração Pentaho → Apache Hop")
root.geometry("850x650")

# hop-import
def selecionar_hop_import():
    caminho = filedialog.askopenfilename(title="Selecione hop-import.bat ou hop-import.sh")
    entry_hop_import.delete(0, tk.END)
    entry_hop_import.insert(0, caminho)

tk.Label(root, text="Caminho hop-import.bat / hop-import.sh:").pack()
entry_hop_import = tk.Entry(root, width=90)
entry_hop_import.pack()
tk.Button(root, text="Selecionar", command=selecionar_hop_import).pack()

# Origem Pentaho
def selecionar_origem():
    caminho = filedialog.askdirectory(title="Selecione diretório Pentaho (origem)")
    entry_origem.delete(0, tk.END)
    entry_origem.insert(0, caminho)

tk.Label(root, text="Origem (Pentaho):").pack()
entry_origem = tk.Entry(root, width=90)
entry_origem.pack()
tk.Button(root, text="Selecionar", command=selecionar_origem).pack()

# Destino Hop
def selecionar_destino():
    caminho = filedialog.askdirectory(title="Selecione diretório Hop (destino)")
    entry_destino.delete(0, tk.END)
    entry_destino.insert(0, caminho)

tk.Label(root, text="Destino (Hop):").pack()
entry_destino = tk.Entry(root, width=90)
entry_destino.pack()
tk.Button(root, text="Selecionar", command=selecionar_destino).pack()

# kettle.properties
def selecionar_kettle():
    caminho = filedialog.askopenfilename(title="Selecione kettle.properties", filetypes=[("Properties", "*.properties")])
    entry_kettle.delete(0, tk.END)
    entry_kettle.insert(0, caminho)

tk.Label(root, text="Arquivo kettle.properties:").pack()
entry_kettle = tk.Entry(root, width=90)
entry_kettle.pack()
tk.Button(root, text="Selecionar", command=selecionar_kettle).pack()

# Nome do projeto
tk.Label(root, text="Nome do Projeto:").pack()
entry_nome_projeto = tk.Entry(root, width=90)
entry_nome_projeto.insert(0, "")
entry_nome_projeto.pack()

# Nome arquivo variáveis
tk.Label(root, text="Nome do arquivo de variáveis:").pack()
entry_nome_variaveis = tk.Entry(root, width=90)
entry_nome_variaveis.insert(0, "")
entry_nome_variaveis.pack()

# Botão Executar
tk.Button(root, text="Executar Migração", command=lambda: threading.Thread(target=executar_processo).start(),
          bg="green", fg="white").pack(pady=10)

# Barra de progresso
progress_bar = ttk.Progressbar(root, length=600, mode='determinate')
progress_bar.pack(pady=5)

# Log
txt_log = scrolledtext.ScrolledText(root, width=100, height=15)
txt_log.pack(pady=10)

root.mainloop()
