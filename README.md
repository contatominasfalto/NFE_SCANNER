# NFE Scanner

Sistema operacional para leitura de chaves de acesso de NF-e, consulta dos dados fiscais, conferência, armazenamento e geração de XML.

O projeto possui três interfaces que utilizam o mesmo backend:

- aplicativo mobile/desktop em KivyMD para o operador bipar e conferir notas;
- painel web para acompanhamento, edição e administração dos registros;
- Swagger para documentação e testes completos da API.

> O fluxo atual não utiliza OCR nem fotografia da nota. A leitura é feita pela chave de acesso de 44 dígitos, obtida por um leitor de código de barras ou digitada manualmente.

## Funcionalidades atuais

- Seleção direta do local de alocação na tela inicial:
  - `CDMA`
  - `PRU`
- Leitura da chave NF-e por leitor de código de barras.
- Validação da chave com 44 dígitos.
- Consulta dos dados reais da nota pela API MeuDanfe.
- Avanço para a conferência mesmo quando a API fiscal não retornar os dados, registrando a chave como erro.
- Conferência e edição dos dados antes do cadastro.
- Fluxo contínuo com `Salvar e próxima` ou encerramento com `Salvar e finalizar`.
- Registro da chave no painel com campos `ERRO` quando o salvamento falhar por qualquer motivo diferente de duplicidade.
- Fila local no app para sincronizar registros de erro quando o backend voltar a ficar disponível.
- Cadastro individual das notas no backend.
- Listagem, busca, edição, exclusão e geração de XML no app.
- Painel web com atualização automática da tabela.
- Botão `Refresh NFes Erro` no painel para consultar novamente somente as chaves cujo campo Produto contenha `ERRO`.
- Filtros por texto, local e faturista no painel.
- Cadastro, ativação e desativação de faturistas.
- Faturista padrão `BIPE` nos lançamentos realizados pelo app.
- Geração de XML individual ou geral.
- Swagger com fluxo completo para consultar, cadastrar, editar e excluir notas.
- Logs da API e da integração fiscal com mascaramento das chaves de acesso.

## Arquitetura

```text
Leitor de código de barras
          |
          v
App KivyMD ou Painel Web
          |
          v
Backend FastAPI
          |
          +----> API MeuDanfe
          |
          +----> Banco SQLite
          |
          +----> Arquivos XML
```

O app e o painel podem operar simultaneamente. O SQLite utiliza modo WAL e timeout de 30 segundos para permitir leituras contínuas do painel enquanto o app grava novas notas.

## Estrutura do projeto

```text
nfe_scanner/
├── backend/
│   ├── app/
│   │   ├── barcode_service.py    # Extração e validação da chave
│   │   ├── config.py             # Variáveis de ambiente e diretórios
│   │   ├── crud.py               # Operações no banco
│   │   ├── database.py           # Conexão, WAL e migrações
│   │   ├── integra_api.py        # Integração com a API MeuDanfe
│   │   ├── logging_config.py     # Configuração dos logs
│   │   ├── main.py               # API FastAPI e Swagger
│   │   ├── models.py             # Modelos SQLAlchemy
│   │   ├── report_service.py     # Geração dos arquivos XML
│   │   └── schemas.py            # Contratos Pydantic
│   ├── panel/
│   │   ├── index.html
│   │   ├── app.js
│   │   ├── styles.css
│   │   └── logo.jpg
│   ├── logs/
│   ├── reports/
│   ├── scripts/
│   ├── .env
│   ├── nfe_scanner.db
│   └── requirements.txt
├── mobile/
│   ├── assets/
│   ├── screens/
│   ├── services/
│   ├── api_config.json
│   ├── buildozer.spec
│   ├── main.py
│   ├── requirements.txt
│   └── ui.py
└── README.md
```

## Tecnologias

### Backend e painel

- Python 3.11+
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- Pydantic
- `urllib` da biblioteca padrão para integração fiscal
- HTML, CSS e JavaScript

### Aplicativo

- Python
- Kivy
- KivyMD
- Requests
- Plyer
- Buildozer para geração do APK Android

## Dados armazenados

### Tabela `notas_fiscais`

| Campo | Descrição |
| --- | --- |
| `id` | Identificador interno |
| `chave_acesso` | Chave NF-e, única, com 44 dígitos |
| `data_cadastro` | Data e hora do bip/cadastro |
| `data_emissao` | Data de emissão da NF-e |
| `numero_nf` | Número da nota |
| `serie` | Série da nota |
| `local` | Local selecionado: CDMA ou PRU |
| `produto` | Produto obtido do XML fiscal |
| `quantidade` | Quantidade ou peso líquido |
| `transportador` | Nome do transportador |
| `faturista` | Faturista; padrão do app: BIPE |
| `lider_operacional` | Líder operacional |
| `nome_fornecedor` | Razão social do fornecedor |
| `cnpj_fornecedor` | CNPJ do fornecedor |
| `valor_total` | Valor total da nota |
| `observacao` | Informação adicional ou observação operacional |
| `caminho_arquivo_imagem` | Campo legado opcional |

### Tabela `faturistas`

Armazena nome, situação e data de cadastro dos faturistas disponíveis no painel. O registro `BIPE` é criado automaticamente e não pode ser desativado ou renomeado.

## Configuração do backend

Crie ou atualize `backend/.env`:

```env
DATABASE_URL=sqlite:///./nfe_scanner.db
REPORT_DIR=reports
LOG_DIR=logs
LOG_LEVEL=INFO
MEUDANFE_API_BASE_URL=https://api.meudanfe.com.br/v2/fd/get/xml
MEUDANFE_API_KEY=sua-chave-da-api
```

Não publique ou versione a chave da API. Se uma chave real tiver sido exposta, ela deve ser revogada e substituída.

Os caminhos relativos de banco, relatórios e logs são resolvidos dentro da pasta `backend`.

## Executar o backend e o painel

Na raiz do projeto, usando PowerShell:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r backend\requirements.txt
venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Com recarregamento automático durante o desenvolvimento:

```powershell
venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Endereços:

| Recurso | URL |
| --- | --- |
| Painel operacional | `http://127.0.0.1:8000/painel` |
| Swagger API | `http://127.0.0.1:8000/docs` |
| Health check | `http://127.0.0.1:8000/health/` |

Se a porta 8000 estiver ocupada, identifique o processo:

```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object State, OwningProcess
```

## Executar o aplicativo no computador

Instale as dependências do app:

```powershell
python -m venv venv-mobile
venv-mobile\Scripts\python.exe -m pip install -r mobile\requirements.txt
```

Confirme que `mobile/api_config.json` aponta para o backend:

```json
{
  "base_url": "http://127.0.0.1:8000"
}
```

Execute:

```powershell
cd mobile
..\venv-mobile\Scripts\python.exe main.py
```

## Executar no Android

No smartphone, `127.0.0.1` aponta para o próprio telefone. Antes de gerar o APK, configure `mobile/api_config.json` com o IP do computador ou servidor acessível pela rede:

```json
{
  "base_url": "http://192.168.1.100:8000"
}
```

O backend deve estar iniciado com `--host 0.0.0.0`, e o firewall deve permitir acesso à porta utilizada.

Em ambiente Linux com Buildozer:

```bash
cd mobile
buildozer android debug
```

O APK será gerado na pasta `mobile/bin/`.

## Fluxo operacional do app

1. O operador seleciona `CDMA` ou `PRU` na tela inicial.
2. O app abre a leitura com o local escolhido.
3. O local escolhido permanece visível na tela de leitura.
4. Bipa ou digita a chave de acesso da NF-e.
5. O app chama `POST /barcode-nf/`.
6. O backend valida a chave e consulta a API MeuDanfe.
7. O app abre a tela de conferência preenchida.
8. O operador revisa os dados.
9. Em `Salvar e próxima`, a nota é gravada e o leitor é reaberto mantendo o local.
10. Em `Salvar e finalizar`, a nota é gravada e o fluxo é encerrado.

Cada nota é salva individualmente. Dessa forma, uma falha posterior não perde as notas já confirmadas.

## Painel operacional

O painel apresenta os registros em uma tabela atualizada automaticamente e permite:

- bipar/consultar nova nota;
- editar ou excluir uma nota;
- gerar XML individual;
- gerar XML geral;
- buscar qualquer conteúdo da nota;
- filtrar por local e faturista;
- acompanhar totais, peso líquido, valor e pendências;
- cadastrar, visualizar, ativar e desativar faturistas;
- editar o faturista associado a uma nota.
- visualizar relatórios acumulados do dia e do mês vigente.

Ao abrir **Relatórios**, o painel apresenta um modal maximizado com dois gráficos de
pizza agrupados por produto. Os períodos usam a data de emissão (`data_emissao`):
do primeiro ao último dia do mês vigente e do primeiro ao último minuto do dia
vigente. As quantidades armazenadas em kg são exibidas em
toneladas, e notas marcadas com erro não entram nos acumulados.

Abaixo dos gráficos, o relatório dinâmico permite informar data/hora inicial e
final para agrupar as notas por material. A tabela apresenta a quantidade total
em toneladas e a quantidade de NF-es de cada material no período selecionado.

O relatório por período, material e local apresenta todos os materiais do período
e separa as quantidades em toneladas e o número de NF-es entre CDMA e PRU.

O relatório de recebimento diário permite filtrar o período e um material
específico ou todos os materiais. Cada dia possui uma única barra empilhada,
dividida proporcionalmente entre os materiais recebidos. A rosca apresenta a
participação total de cada material no período.

Os botões **Baixar PDF** e **Baixar Excel** exportam o relatório completo usando
os períodos atualmente configurados nas consultas dinâmicas. O navegador inicia
o download do arquivo para a pasta de downloads configurada no computador.

O PDF utiliza a identidade visual **SCAN-NFE MINASFALTO**, incluindo logo,
cabeçalho e rodapé paginados, moldura externa, seções delimitadas e gráficos
organizados em páginas individuais para melhorar a leitura.

## Endpoints principais

| Método | Endpoint | Finalidade |
| --- | --- | --- |
| `GET` | `/health/` | Verificar se a API está online |
| `POST` | `/barcode-nf/` | Validar chave e consultar dados fiscais |
| `POST` | `/notas/importar-barcode/` | Consultar e cadastrar em uma chamada, útil no Swagger |
| `POST` | `/notas/` | Cadastrar uma nota já conferida |
| `GET` | `/notas/` | Listar notas cadastradas |
| `GET` | `/relatorios/operacional/` | Obter acumulados operacionais diário e mensal |
| `GET` | `/relatorios/material/` | Agrupar materiais por período informado |
| `GET` | `/relatorios/material-local/` | Agrupar materiais por período e local |
| `GET` | `/relatorios/recebimento-diario/` | Agrupar e calcular a proporção diária dos materiais |
| `GET` | `/relatorios/exportar/` | Exportar o relatório completo em PDF ou Excel |
| `PUT` | `/notas/{nota_id}/` | Editar uma nota |
| `DELETE` | `/notas/{nota_id}/` | Excluir uma nota |
| `POST` | `/faturistas/` | Cadastrar faturista |
| `GET` | `/faturistas/` | Listar faturistas |
| `PUT` | `/faturistas/{faturista_id}/` | Editar ou reativar faturista |
| `DELETE` | `/faturistas/{faturista_id}/` | Desativar faturista |
| `POST` | `/relatorio/` | Gerar XML individual ou geral |

A documentação completa, os schemas, exemplos e códigos de resposta estão disponíveis no Swagger.

## Testar o fluxo completo pelo Swagger

1. Abra `http://127.0.0.1:8000/docs`.
2. Execute `POST /notas/importar-barcode/`.
3. Informe uma chave real de 44 dígitos em `codigo_barras`.
4. Informe um `local` válido.
5. Confirme o cadastro com `GET /notas/`.
6. Edite a nota com `PUT /notas/{nota_id}/`, se necessário.
7. Gere o XML com `POST /relatorio/?nota_id={nota_id}&formato=xml`.
8. Exclua a nota com `DELETE /notas/{nota_id}/` para repetir o teste com a mesma chave.

Uma chave já cadastrada retorna `409 Conflict`. Payloads incompatíveis retornam `422` com o campo inválido detalhado.

## XML

O sistema gera somente XML no fluxo atual.

- XML individual: informe `nota_id`.
- XML geral: omita `nota_id`.
- Filtros opcionais do XML geral:
  - `data_inicio`
  - `data_fim`
  - `fornecedor`
  - `valor_min`
  - `valor_max`

Os arquivos também são armazenados em `backend/reports/`.

## Logs e diagnóstico

Os logs ficam em:

```text
backend/logs/nfe_scanner.log
```

Exibir as últimas linhas no PowerShell:

```powershell
Get-Content backend\logs\nfe_scanner.log -Tail 100
```

Os logs registram requisições, duração, erros de validação, integração fiscal, cadastros, edições, exclusões e geração de XML. As chaves NF-e são mascaradas nos registros de integração.

## Consultar a estrutura do banco

Exemplo usando o Python do ambiente virtual:

```powershell
venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('backend/nfe_scanner.db'); print(c.execute('PRAGMA table_info(notas_fiscais)').fetchall())"
```

Listar notas cadastradas:

```powershell
venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('backend/nfe_scanner.db'); print(c.execute('SELECT id, numero_nf, local, nome_fornecedor, valor_total FROM notas_fiscais').fetchall())"
```

## Regras importantes

- A chave de acesso deve possuir exatamente 44 dígitos.
- `chave_acesso` é única no banco.
- `local` é obrigatório ao cadastrar uma nova nota.
- O app utiliza `BIPE` como faturista padrão.
- A API MeuDanfe pode não retornar uma nota mesmo quando a chave é formalmente válida.
- O app e o painel dependem do backend online.
- A integração fiscal depende de uma `MEUDANFE_API_KEY` válida.
- O sistema ainda não possui autenticação ou controle de permissões.

## Status atual

| Componente | Status |
| --- | --- |
| Backend FastAPI | Funcional |
| Integração MeuDanfe | Funcional, condicionada à credencial |
| Leitura por código de barras | Funcional |
| Cadastro, edição e exclusão de notas | Funcional |
| Aplicativo KivyMD | Funcional no computador e preparado para Android |
| Painel web operacional | Funcional |
| Gestão de faturistas | Funcional |
| Geração de XML | Funcional |
| Swagger | Atualizado |
| Logs operacionais | Funcional |
| Autenticação | Não implementada |

## Segurança

- Mantenha `backend/.env` fora do controle de versão.
- Não distribua a chave da API no app mobile ou no painel.
- Em produção, utilize HTTPS, autenticação, regras de firewall e um servidor de banco adequado ao volume da operação.

## Autor

Maxwell Viana

Projeto desenvolvido para uso corporativo e operacional.
