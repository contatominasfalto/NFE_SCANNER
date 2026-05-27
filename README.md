# 📱 NFE Scanner

Sistema completo para escaneamento, leitura OCR, armazenamento e emissão de relatórios de Notas Fiscais Eletrônicas (NF-e), desenvolvido em Python com aplicativo Android integrado.

---

# 📌 Visão Geral

O projeto **NFE Scanner** foi desenvolvido para automatizar o processo de captura e controle de notas fiscais através de dispositivos móveis Android.

A aplicação permite:

* Escanear notas fiscais utilizando a câmera do celular;
* Extrair informações automaticamente via OCR;
* Confirmar e validar os dados antes do armazenamento;
* Salvar os dados em banco SQL;
* Consultar notas cadastradas;
* Emitir relatórios em PDF e Excel;
* Centralizar as informações em um backend FastAPI.

O sistema foi projetado para operações corporativas que necessitam controle rápido de documentos fiscais diretamente em campo.

---

# 🏗️ Arquitetura do Projeto

O projeto está dividido em dois módulos principais:

## 1. Mobile Android

Aplicativo desenvolvido em Python utilizando:

* Kivy
* KivyMD
* Buildozer

Responsável por:

* Interface do usuário;
* Captura da imagem da nota fiscal;
* Comunicação com API;
* Consulta de registros;
* Emissão de relatórios.

---

## 2. Backend API

Backend desenvolvido com:

* FastAPI
* SQLAlchemy
* SQLite/PostgreSQL
* OCR com Tesseract

Responsável por:

* Processamento OCR;
* Armazenamento das notas fiscais;
* Geração de relatórios;
* Disponibilização da API REST;
* Gerenciamento do banco de dados.

---

# 📂 Estrutura do Projeto

```bash
nfe_scanner/
│
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   ├── crud.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── ocr_service.py
│   │   ├── report_service.py
│   │   ├── schemas.py
│   │   └── utils.py
│   │
│   ├── scripts/
│   │   └── create_db.sql
│   │
│   ├── requirements.txt
│   └── .env
│
├── mobile/
│   ├── assets/
│   │   └── logo.jpg
│   │
│   ├── screens/
│   │   ├── confirm_screen.py
│   │   ├── home_screen.kv
│   │   ├── list_screen.py
│   │   ├── report_screen.py
│   │   └── scan_screen.py
│   │
│   ├── services/
│   │   └── api_client.py
│   │
│   ├── main.py
│   ├── ui.py
│   ├── buildozer.spec
│   ├── requirements.txt
│   └── api_config.json
│
├── reports/
├── uploads/
├── nfe_scanner.db
└── README.md
```

---

# ⚙️ Tecnologias Utilizadas

## Backend

| Tecnologia    | Finalidade                 |
| ------------- | -------------------------- |
| Python        | Linguagem principal        |
| FastAPI       | API REST                   |
| SQLAlchemy    | ORM banco de dados         |
| SQLite        | Banco local                |
| PostgreSQL    | Banco produção             |
| Tesseract OCR | Leitura de texto das notas |
| ReportLab     | Relatórios PDF             |
| OpenPyXL      | Relatórios Excel           |
| Uvicorn       | Servidor ASGI              |

---

## Mobile

| Tecnologia | Finalidade               |
| ---------- | ------------------------ |
| Kivy       | Interface Android        |
| KivyMD     | Componentes visuais      |
| Buildozer  | Compilação APK           |
| Plyer      | Recursos nativos Android |
| Requests   | Comunicação HTTP         |

---

# 🔍 Funcionalidades

## 📸 Escaneamento de NF-e

O aplicativo permite capturar imagens diretamente pela câmera do dispositivo Android.

Fluxo:

1. Usuário abre tela de escaneamento;
2. Captura a imagem da nota fiscal;
3. Imagem é enviada para API;
4. OCR processa os dados;
5. Sistema identifica:

* Número da NF;
* Série;
* Data emissão;
* CNPJ fornecedor;
* Nome fornecedor;
* Valor total;
* Chave de acesso;
* Observações.

---

## 🧠 OCR Inteligente

O backend utiliza OCR para leitura automática dos dados presentes na nota fiscal.

A aplicação foi preparada para:

* Extrair informações estruturadas;
* Tratar caracteres inválidos;
* Melhorar reconhecimento de texto;
* Automatizar cadastro fiscal.

---

## ✅ Confirmação Manual

Antes de gravar a nota no banco:

* Usuário pode validar os dados;
* Corrigir inconsistências;
* Confirmar o envio.

Isso reduz falhas do OCR.

---

## 🗄️ Banco de Dados

As notas ficam armazenadas em banco SQL.

Tabela principal:

```python
notas_fiscais
```

Campos:

| Campo                  | Tipo     |
| ---------------------- | -------- |
| id                     | Integer  |
| numero_nf              | String   |
| serie                  | String   |
| data_emissao           | DateTime |
| cnpj_fornecedor        | String   |
| nome_fornecedor        | String   |
| valor_total            | Float    |
| chave_acesso           | String   |
| observacao             | Text     |
| caminho_arquivo_imagem | String   |
| data_cadastro          | DateTime |

---

## 📊 Relatórios

O sistema gera relatórios:

### PDF

Utilizando ReportLab.

### Excel

Utilizando OpenPyXL.

Filtros disponíveis:

* Data inicial;
* Data final;
* Fornecedor;
* Valor mínimo;
* Valor máximo.

---

# 🌐 Endpoints da API

## Health Check

```http
GET /health/
```

Resposta:

```json
{
  "status": "ok"
}
```

---

## OCR da Nota

```http
POST /ocr-nf/
```

Responsável por:

* Receber imagem;
* Executar OCR;
* Retornar dados extraídos.

---

## Criar Nota Fiscal

```http
POST /notas/
```

Responsável por:

* Validar dados;
* Gravar nota no banco.

---

## Upload Completo

```http
POST /upload-nf/
```

Fluxo legado:

* Upload;
* OCR;
* Gravação imediata.

---

## Listar Notas

```http
GET /notas/
```

---

## Gerar Relatório

```http
POST /relatorio/
```

Formatos:

* PDF
* Excel

---

# 🖥️ Instalação do Backend

## 1. Clonar Projeto

```bash
git clone https://github.com/seu-repositorio/nfe_scanner.git
```

---

## 2. Criar Ambiente Virtual

```bash
python -m venv venv
```

Ativar:

### Windows

```bash
venv\Scripts\activate
```

### Linux

```bash
source venv/bin/activate
```

---

## 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

---

## 4. Configurar Variáveis Ambiente

Arquivo:

```env
.env
```

Exemplo:

```env
DATABASE_URL=sqlite:///./nfe_scanner.db
UPLOAD_DIR=uploads
REPORT_DIR=reports
```

---

## 5. Executar Backend

```bash
uvicorn app.main:app --reload
```

API disponível:

```bash
http://127.0.0.1:8000
```

Swagger:

```bash
http://127.0.0.1:8000/docs
```

---

# 📱 Instalação Mobile Android

## Dependências Linux

```bash
sudo apt update
sudo apt install -y \
python3-pip \
build-essential \
git \
zip \
unzip \
openjdk-17-jdk \
autoconf \
libtool \
pkg-config \
zlib1g-dev
```

---

## Instalar Buildozer

```bash
pip install buildozer cython
```

---

## Compilar APK

Dentro da pasta mobile:

```bash
buildozer android debug
```

APK gerado em:

```bash
bin/
```

---

# 📲 Fluxo de Utilização

## Operação do Usuário

1. Abrir aplicativo;
2. Selecionar escaneamento;
3. Fotografar nota fiscal;
4. Aguardar OCR;
5. Confirmar dados;
6. Salvar nota;
7. Consultar relatórios.

---

# 🔒 Segurança

O projeto foi estruturado para permitir futura implementação de:

* JWT Authentication;
* Controle de usuários;
* Criptografia de dados;
* Logs de auditoria;
* Controle de permissões.

---

# 🚀 Melhorias Futuras

Possíveis evoluções:

* Integração SEFAZ;
* Leitura QR Code NF-e;
* Dashboard gerencial;
* Multiempresa;
* Sincronização cloud;
* Backup automático;
* Inteligência artificial para validação fiscal;
* OCR avançado com machine learning.

---

# 📈 Casos de Uso

O sistema pode ser utilizado por:

* Construtoras;
* Transportadoras;
* Distribuidoras;
* Empresas de pavimentação;
* Controle de almoxarifado;
* Setor fiscal;
* Controle financeiro;
* Gestão de compras.

---

# 🧪 Testes Recomendados

## Backend

Testar:

* Upload de imagem;
* OCR;
* Persistência banco;
* Relatórios;
* Filtros;
* Performance.

---

## Mobile

Validar:

* Permissões câmera;
* Layout Android;
* Comunicação API;
* Responsividade;
* Estabilidade APK.

---

# 📋 Requisitos do Sistema

## Backend

* Python 3.11+
* SQLite/PostgreSQL
* Tesseract OCR

---

## Android

* Android 8+
* Internet ativa
* Permissão câmera

---

# 🧾 Exemplo de Fluxo Técnico

```text
Android App
     ↓
Captura Imagem
     ↓
FastAPI Backend
     ↓
OCR Tesseract
     ↓
Extração Dados
     ↓
Validação
     ↓
Banco SQL
     ↓
Relatórios PDF/Excel
```

---

# 👨‍💻 Autor

## Maxwell Viana

Desenvolvedor responsável pela estruturação do sistema NFE Scanner.

Tecnologias principais utilizadas:

* Python
* FastAPI
* Kivy
* OCR
* SQL
* Android Buildozer

---

# 📄 Licença

Projeto desenvolvido para uso corporativo e operacional.

Todos os direitos reservados.

---

# 📞 Observações Técnicas

O projeto já possui:

* Estrutura backend funcional;
* Estrutura mobile organizada;
* Separação de responsabilidades;
* Arquitetura preparada para expansão;
* Modelo adequado para deploy em VPS/Hosting.

Pode ser facilmente adaptado para:

* Docker;
* Railway;
* Render;
* VPS Linux;
* AWS;
* Azure;
* Google Cloud.

---

# ✅ Status Atual do Projeto

| Módulo          | Status       |
| --------------- | ------------ |
| Backend FastAPI | Funcional    |
| OCR             | Implementado |
| Banco de Dados  | Funcional    |
| Relatórios      | Funcional    |
| Mobile Android  | Estruturado  |
| Build APK       | Preparado    |
| Deploy Hosting  | Preparado    |

---

# 📌 Conclusão

O projeto NFE Scanner entrega uma solução prática para digitalização e controle de notas fiscais em ambiente corporativo.

A arquitetura adotada permite crescimento escalável, integração futura com sistemas ERP e adaptação para operações de grande volume.
