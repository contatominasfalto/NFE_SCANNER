# NFE Scanner

Sistema operacional para bipagem, consulta, cadastro, auditoria e relatorios de NF-e da Minasfalto.

O projeto centraliza o recebimento de notas fiscais por chave de acesso de 44 digitos. A chave e lida pelo aplicativo Android ou informada no painel web, o backend consulta a API fiscal MeuDanfe, grava os dados no banco PostgreSQL e disponibiliza acompanhamento operacional em tempo real.

## Ambiente atual

| Item | Ambiente oficial |
| --- | --- |
| Codigo fonte | GitHub |
| Aplicacao web/API | Render Web Service |
| Banco de dados | PostgreSQL Render |
| Painel | `https://nfe-scanner-api.onrender.com/painel` |
| APK Android | Distribuido conforme necessidade interna |
| Backend antigo no servidor | Desativado |

O servidor Windows antigo nao e mais necessario para operar o NFE Scanner. Ele foi substituido pelo Render e pelo PostgreSQL gerenciado.

## Arquitetura

```text
Aplicativo Android / Painel Web
              |
              v
        FastAPI no Render
              |
      +-------+--------+
      |                |
      v                v
PostgreSQL Render   API MeuDanfe
```

O painel e o aplicativo nao acessam o banco diretamente. Toda comunicacao passa pelo backend FastAPI.

## Componentes

### Backend

Local: `backend/app`

Responsavel por:

- autenticacao por sessao;
- validacao de chave NF-e;
- consulta da API MeuDanfe;
- cadastro, edicao, exclusao e listagem de notas;
- cadastro e controle de usuarios;
- auditoria de modificacoes;
- relatorios operacionais;
- exportacao PDF, Excel e XML;
- entrega do painel web e do APK.

### Painel web

Local: `backend/panel`

Principais recursos:

- listagem de notas fiscais;
- filtros por texto, erro, data de bip, data de emissao e local;
- totais proporcionais ao filtro aplicado;
- exportacao em Excel conforme filtro ativo;
- bipagem por remessa;
- refresh de NF-es com erro;
- gestao de usuarios;
- relatorios operacionais;
- rastreabilidade/auditoria;
- layout responsivo para celular, com cards no mobile e tabela no desktop.

### Aplicativo Android

Local: `mobile`

Versao atual:

```text
0.1.13
```

O app aponta para:

```text
https://nfe-scanner-api.onrender.com
```

Fluxo do app:

1. Operador escolhe o local (`CDMA` ou `PRU`).
2. Bipa ou digita a chave da NF-e.
3. App chama o backend.
4. Backend consulta a API MeuDanfe.
5. App mostra os dados para conferencia.
6. Nota e salva como usuario `BIPE`.
7. Se houver falha tratavel, o app registra a nota como pendente/com erro.

## Banco de dados

Banco oficial:

```text
PostgreSQL Render
```

Tabelas principais:

| Tabela | Finalidade |
| --- | --- |
| `users` | Usuarios do painel e do aplicativo |
| `notas_fiscais` | Notas fiscais cadastradas |
| `audit_logs` | Rastreabilidade das alteracoes |

SQLite esta bloqueado no codigo atual para evitar perda de dados por conexao acidental com banco local. A aplicacao aceita MySQL para cenarios legados e PostgreSQL para producao atual.

## Variaveis de ambiente

O backend depende das seguintes variaveis:

```env
DATABASE_URL=postgresql://usuario:senha@host/banco
MEUDANFE_API_BASE_URL=https://api.meudanfe.com.br/v2/fd/get/xml
MEUDANFE_API_KEY=sua-chave-meudanfe
SECRET_KEY=chave-secreta-da-aplicacao
LOG_LEVEL=INFO
```

No Render, utilize a `Internal Database URL` ou a `DATABASE_URL` gerada pelo proprio Render para o Web Service.

Para consultas externas pelo computador local, use a `External Database URL` com SSL:

```text
postgresql://usuario:senha@host.render.com/banco?sslmode=require
```

Nunca versione credenciais reais no GitHub.

## Permissoes de usuario

| Perfil | Acesso |
| --- | --- |
| `admin` | Acesso completo ao painel, usuarios, relatorios, rastreabilidade e operacoes |
| `user` | Operacao de notas, remessas, relatorios e downloads permitidos |
| `viewer` | Visualizacao e relatorios, sem operacoes de escrita/download restrito |
| `BIPE` | Usuario padrao utilizado pelo aplicativo Android |

As abas laterais do painel sao exibidas conforme a permissao do usuario logado.

## Regras operacionais importantes

- Chave NF-e deve conter exatamente 44 digitos.
- `chave_acesso` e unica no banco.
- Lancamentos pelo app Android sao registrados como `BIPE`.
- Lancamentos pelo painel usam o usuario logado.
- Notas com erro mantem a data/hora real do bip.
- Relatorios usam filtro unico de periodo e material.
- Grafico de pizza e demais relatorios respeitam o filtro aplicado.
- O painel carrega por padrao o periodo de bip do primeiro dia do mes vigente ate o dia atual.
- O Excel da tela principal exporta conforme o estado atual dos filtros.

## Relatorios

A aba **Relatorios** apresenta:

- acumulado do periodo;
- grafico de quantidade por produto;
- relatorio por periodo e material;
- relatorio por periodo, material e local;
- recebimento diario por data de emissao;
- exportacao em PDF;
- exportacao em Excel.

Os filtros ficam no topo e controlam todos os graficos e tabelas abaixo.

## Rastreabilidade

A aba **Rastreabilidade** registra eventos administrativos e operacionais, incluindo:

- cadastro de nota;
- edicao de nota;
- exclusao de nota;
- importacao por remessa;
- cadastro/edicao/exclusao de usuarios;
- atualizacao de notas com erro.

Cada evento registra:

- data e hora;
- usuario;
- acao;
- area;
- registro afetado;
- descricao;
- detalhes.

## Executar localmente

Na raiz do projeto:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Crie `backend/.env` com uma `DATABASE_URL` valida.

Executar backend:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

URLs locais:

| Recurso | URL |
| --- | --- |
| Painel | `http://127.0.0.1:8000/painel` |
| Swagger | `http://127.0.0.1:8000/docs` |
| Health check | `http://127.0.0.1:8000/health/` |
| Pagina do APK | `http://127.0.0.1:8000/app` |

## Deploy no Render

O Web Service do Render executa o backend a partir do GitHub.

Comando de start:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Variaveis obrigatorias no Render:

```env
DATABASE_URL=postgresql://...
MEUDANFE_API_BASE_URL=https://api.meudanfe.com.br/v2/fd/get/xml
MEUDANFE_API_KEY=...
SECRET_KEY=...
LOG_LEVEL=INFO
```

A cada `git push` na branch `main`, o Render faz novo deploy.

## Gerar APK Android

O APK e gerado pelo Buildozer em ambiente Linux/WSL.

No WSL:

```bash
cd /mnt/c/Users/Administrativo/Max/auto/nfe_scanner/mobile
buildozer android debug
```

Arquivo gerado:

```text
mobile/bin/nfescanner-0.1.13-arm64-v8a-debug.apk
```

Antes de gerar uma nova versao, atualize em `mobile/buildozer.spec`:

```text
version
android.numeric_version
```

O arquivo `mobile/api_config.json` define o backend usado pelo APK.

## Consultar o PostgreSQL do Render

Instale o driver no ambiente local:

```powershell
.\venv\Scripts\python.exe -m pip install "psycopg[binary]"
```

Defina a URL externa do banco:

```powershell
$env:PG_URL = "postgresql://usuario:senha@host.render.com/nfe_scanner?sslmode=require"
```

Consultar totais:

```powershell
@'
from sqlalchemy import create_engine, text
import os

url = os.environ["PG_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    for tabela in ["users", "notas_fiscais", "audit_logs"]:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
        print(f"{tabela}: {total}")
'@ | .\venv\Scripts\python.exe
```

## Integracao Power BI

O projeto possui uma camada pronta de views para consumo no Power BI.

Arquivos:

| Arquivo | Finalidade |
| --- | --- |
| `docs/powerbi_setup.sql` | Cria o schema `powerbi` e as views de indicadores |
| `docs/powerbi_guia.md` | Passo a passo para conectar o Power BI ao PostgreSQL Render |

Fluxo recomendado:

```text
aplicar docs/powerbi_setup.sql no PostgreSQL Render
criar usuario somente leitura para Power BI
conectar Power BI Desktop usando a External Database URL
selecionar as views do schema powerbi
```

## Endpoints principais

| Metodo | Endpoint | Finalidade |
| --- | --- | --- |
| `GET` | `/health/` | Verificar status da API |
| `POST` | `/auth/login/` | Login do painel/app |
| `POST` | `/auth/logout/` | Encerrar sessao |
| `GET` | `/auth/me/` | Usuario autenticado |
| `POST` | `/barcode-nf/` | Consultar dados fiscais por chave |
| `POST` | `/notas/` | Cadastrar nota |
| `GET` | `/notas/` | Listar notas |
| `PUT` | `/notas/{nota_id}/` | Editar nota |
| `DELETE` | `/notas/{nota_id}/` | Excluir nota |
| `POST` | `/notas/importar-remessa/` | Importar lote de chaves |
| `POST` | `/notas/erro/` | Registrar nota com erro |
| `POST` | `/notas/erro/refresh/` | Reprocessar notas com erro |
| `GET` | `/faturistas/` | Listar usuarios/faturistas |
| `POST` | `/faturistas/` | Criar usuario/faturista |
| `PUT` | `/faturistas/{id}/` | Editar usuario/faturista |
| `DELETE` | `/faturistas/{id}/` | Excluir usuario/faturista |
| `GET` | `/auditoria/` | Listar rastreabilidade |
| `GET` | `/relatorios/*` | Consultas operacionais |
| `POST` | `/relatorio/` | Gerar XML |
| `GET` | `/app` | Pagina para download do APK |

Documentacao completa:

```text
https://nfe-scanner-api.onrender.com/docs
```

## Estrutura do projeto

```text
nfe_scanner/
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   |-- crud.py
|   |   |-- database.py
|   |   |-- config.py
|   |   |-- integra_api.py
|   |   |-- report_service.py
|   |   |-- note_author.py
|   |   |-- barcode_service.py
|   |   `-- logging_config.py
|   |-- panel/
|   |   |-- index.html
|   |   |-- app.js
|   |   |-- styles.css
|   |   |-- logo.jpg
|   |   `-- assinatura-maxwell.png
|   |-- requirements.txt
|   `-- mysql_setup.sql
|-- mobile/
|   |-- main.py
|   |-- api_config.json
|   |-- buildozer.spec
|   |-- screens/
|   |-- services/
|   |-- assets/
|   `-- bin/
`-- README.md
```

## Seguranca

- Nao publicar `.env` com credenciais reais.
- Nao expor `MEUDANFE_API_KEY`.
- Usar HTTPS em producao.
- Manter SQLite bloqueado para evitar banco local acidental.
- Usar PostgreSQL Render como banco oficial.
- Remover portas antigas abertas no servidor legado.

## Manutencao

Fluxo recomendado:

```text
alterar codigo local -> testar -> commit -> git push -> Render deploy
```

Depois do deploy, validar:

```text
/health/
/painel
/docs
```

## Autor

Maxwell Viana

Projeto desenvolvido para uso operacional da Minasfalto.

Assinatura visual utilizada no painel: `backend/panel/assinatura-maxwell.png`.
