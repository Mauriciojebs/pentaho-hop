# 🔄 Pentaho → Apache Hop Migration Tool

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Ativo-brightgreen)
![GUI](https://img.shields.io/badge/Interface-Tkinter-orange)
![Contributions](https://img.shields.io/badge/Contributions-Bem%20Vindas-success)
![Platform](https://img.shields.io/badge/Compatibilidade-Windows%20%7C%20Linux%20%7C%20MacOS-lightgrey)

🚀 Uma ferramenta **GUI** para automatizar a **migração de projetos Pentaho Data Integration (PDI)** para **Apache Hop**, com conversão de variáveis, criação de ambientes e relatórios automáticos.

---

## ✨ Funcionalidades Principais

✅ **Interface Gráfica amigável** feita em Tkinter  
✅ **Execução do hop-import** com log em tempo real  
✅ **Conversão automática** do `kettle.properties` para JSON  
✅ **Criação completa** da estrutura de projeto no Hop (`projects/`)  
✅ **Backup automático** dos arquivos alterados  
✅ **Comparativo** entre artefatos Pentaho e Hop  
✅ **Relatório final** salvo e aberto automaticamente  

---

## 📸 Screenshots

> Adicione suas imagens na pasta `docs/` e substitua os exemplos abaixo.

| Tela Principal | Log e Progresso |
|---------------|----------------|
| ![Tela Principal](docs/Tela.png) | ![Log de Migração](docs/relatorio.png) |

---

## 📦 Instalação

### 1️⃣ Clonar o repositório
```bash
git clone https://github.com/seu-usuario/pentaho-hop.git
cd pentaho-hop
```

### 2️⃣ Instalar dependências
```bash
pip install -r requirements.txt
```

✅ **Conteúdo do arquivo requirements.txt:
✅ **charset_normalizer

### 3️⃣ Como Usar
#   a) Executar o programa
python migra.py
#   b) Ou utilizar o .exe gerado via PyInstaller

### 4️⃣ Selecionar no programa:
✅ **Caminho do hop-import.bat ou hop-import.sh
✅ **Diretório origem do Pentaho
✅ **Diretório destino no Hop
✅ **Arquivo kettle.properties
✅ **Nome do projeto e nome do arquivo de variáveis

### 5️⃣ Criar Executável (opcional)
```bash
pip install pyinstaller
pyinstaller --onefile --noconsole migra.py
```
✅ **O executável será gerado na pasta dist/
