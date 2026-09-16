# Instrucoes operacionais para agentes Codex — NFE Scanner

Estas instrucoes se aplicam a todo o repositorio. Todo agente deve ler este arquivo por completo antes de analisar, editar, testar, versionar ou orientar deploy do projeto.

## 1. Regra central do projeto

O repositorio possui somente duas branches permanentes:

| Branch | Finalidade | Render | Banco |
| --- | --- | --- | --- |
| `main` | Producao do painel/backend e desenvolvimento/publicacao do APK | `nfe-scanner-api` | `nfe-scanner-db` |
| `dev_testes` | Desenvolvimento e homologacao exclusivos do painel/backend | `nfe-scanner-dev` | `nfe-scanner-dev-db` |

Fluxos obrigatorios:

```text
Painel/backend: dev_testes -> homologacao -> validacao -> main -> producao
Aplicativo APK: main -> producao
```

- Nao criar branches `feature/*`, `hotfix/*` ou branches temporarias sem pedido expresso do proprietario.
- Nao desenvolver `backend/` diretamente em `main`.
- Nao desenvolver `mobile/` em `dev_testes`.
- O hook local reforca essas regras, mas nao substitui a conferencia humana.
- Nunca usar `--no-verify` sem autorizacao expressa e justificativa registrada.

## 2. Ambientes isolados

### Producao

- URL: `https://nfe-scanner-api.onrender.com`
- Painel: `https://nfe-scanner-api.onrender.com/painel`
- Branch do deploy: `main`
- Banco: `nfe-scanner-db`
- Contem usuarios, notas e operacao reais.

### Homologacao

- URL: `https://nfe-scanner-dev.onrender.com`
- Painel: `https://nfe-scanner-dev.onrender.com/painel`
- Branch do deploy: `dev_testes`
- Banco: `nfe-scanner-dev-db`
- Dados sao independentes e podem ser diferentes ou estar vazios.
- A integracao MeuDanfe e real e usa a chave disponivel para o projeto.

O ambiente `Staging` do Render organiza a homologacao; `Production` organiza a producao. Mover um recurso entre esses grupos nao deve ser confundido com copiar dados.

## 3. Separacao entre codigo, configuracao e dados

- Git versiona codigo; merge e push nao copiam usuarios, notas, auditoria ou qualquer registro entre bancos.
- Cada Web Service recebe suas proprias variaveis no Render.
- `DATABASE_URL` determina qual banco sera alterado. Ela e o principal limite de seguranca entre os ambientes.
- Producao nunca pode receber a URL de `nfe-scanner-dev-db`.
- Homologacao nunca pode receber a URL de `nfe-scanner-db`.
- `SECRET_KEY` e `PUBLIC_API_KEYS` devem ser diferentes entre os ambientes.
- `MEUDANFE_API_KEY` pode ser compartilhada por decisao operacional, mas nunca deve ser exibida, registrada ou versionada.
- Nao criar, editar, copiar ou substituir `.env` com credenciais reais sem autorizacao.
- Nunca inserir segredos em README, AGENTS, commits, logs, prints ou respostas.

Variaveis relevantes:

```text
DATABASE_URL
SECRET_KEY
PUBLIC_API_KEYS
MEUDANFE_API_KEY
MEUDANFE_API_BASE_URL
MEUDANFE_ADD_BASE_URL
MEUDANFE_ADD_BEFORE_GET
MEUDANFE_ADD_WAIT_SECONDS
MEUDANFE_404_RETRY_DELAYS
LOG_LEVEL
```

## 4. Alerta especial sobre inicializacao e banco

O backend executa na inicializacao:

```python
models.Base.metadata.create_all(bind=engine)
ensure_schema()
```

Portanto, iniciar a aplicacao pode alterar o esquema do banco apontado por `DATABASE_URL`. Antes de rodar backend, testes de integracao, shell ou deploy:

1. identificar a branch atual;
2. identificar de onde vem `DATABASE_URL`;
3. confirmar explicitamente que ela nao aponta para producao;
4. inspecionar mudancas em `models.py`, `database.py`, `ensure_schema()` e SQL;
5. avaliar compatibilidade com dados antigos e repeticao segura da operacao.

Mudancas de tabela, coluna, indice, constraint, tipo, migracao, `ALTER`, `DROP`, `DELETE` ou atualizacao em massa exigem:

- teste primeiro em `nfe-scanner-dev-db`;
- backup de producao antes da promocao;
- plano de rollback;
- revisao do SQL e do comportamento na reinicializacao;
- autorizacao antes de qualquer acao direta no banco produtivo.

Nunca testar uma migracao apontando o computador local para producao. Nao apagar ou recriar banco, tabela ou volume para corrigir deploy.

### Cargas historicas diretas

`insert_bd_direto.py` e a unica rotina autorizada no repositorio para importar
`base_json.json` sem passar pela MeuDanfe. Essa operacao e de alto risco:

- executar primeiro com `--validar-apenas`;
- simular e depois gravar primeiro em `--ambiente testes`;
- conferir contagens, amostras, TME, TMAC e duplicidades na homologacao;
- fazer backup de `nfe-scanner-db` antes da producao;
- nunca colocar URLs ou credenciais no arquivo Python ou no JSON;
- producao exige `--executar --confirmar-producao INSERIR_EM_PRODUCAO`;
- guardar o manifesto gerado em `logs_importacao/` ate a validacao final;
- nao editar a tabela manualmente para contornar uma validacao do importador.

## 5. Procedimento inicial obrigatorio

Antes de modificar qualquer arquivo:

```powershell
git status --short --branch
git branch --show-current
git fetch --prune
```

- Preservar alteracoes preexistentes do usuario.
- Nao usar `git reset --hard`, `git checkout --`, limpeza destrutiva ou reescrita de historico.
- Se houver trabalho nao relacionado, nao inclui-lo no commit.
- Em cada clone novo, ativar as protecoes:

```powershell
.\scripts\configurar_git.ps1
```

## 6. Fluxo do painel/backend

Preparar:

```powershell
git switch dev_testes
git pull --ff-only origin dev_testes
```

Depois de desenvolver:

```powershell
git status
git diff
git add <arquivos-especificos>
git commit -m "tipo: descricao objetiva"
git push origin dev_testes
```

O push deve implantar somente `nfe-scanner-dev`. Acompanhar logs e testar a URL de homologacao. Nao promover apenas porque o build terminou: validar funcionalidade, regressao, permissoes e dados.

Antes de promover:

```powershell
git fetch origin
git log --oneline origin/main..dev_testes
git diff --stat origin/main...dev_testes
git diff origin/main...dev_testes
```

Promover somente apos aprovacao da homologacao:

```powershell
git switch main
git pull --ff-only origin main
git merge --no-ff dev_testes
```

Rodar novamente os testes e revisar o resultado. Somente entao:

```powershell
git push origin main
```

O push em `main` aciona producao. Acompanhar o deploy e executar smoke tests. Depois sincronizar:

```powershell
git switch dev_testes
git merge main
git push origin dev_testes
```

## 7. Fluxo do APK Android

Alteracoes do aplicativo sao feitas exclusivamente em `main`:

```powershell
git switch main
git pull --ff-only origin main
```

- Escopo principal: `mobile/`.
- Conferir `mobile/api_config.json`; o APK continua apontando para producao.
- Atualizar versao e codigo numerico em `mobile/buildozer.spec` quando aplicavel.
- Gerar e testar o APK antes de publicar.
- Nao redirecionar o APK para homologacao como parte do fluxo do painel.

Depois do push em `main`, sincronizar `main` em `dev_testes` para evitar divergencia, sem iniciar desenvolvimento Android nessa branch.

## 8. Testes minimos

Testes automatizados atuais:

```powershell
Push-Location backend
python -m unittest discover -s tests -p "test_*.py"
Pop-Location
```

Usar o ambiente virtual do projeto quando disponivel. Mudancas devem receber testes proporcionais ao risco.

Checklist de homologacao conforme o escopo:

- `/health/`, `/painel` e `/docs`;
- login, logout e expiracao de sessao;
- perfis Admin, Standard e Viewer;
- modulos personalizados e contas protegidas;
- listagem, filtros, paginacao, totais e atualizacao automatica;
- bipagem, remessa, nota com erro e consulta MeuDanfe;
- inclusao, edicao e exclusao quando autorizadas;
- TME, TMAC e demais relatorios;
- PDF, Excel e XML;
- API publica com chave correta, ausente e incorreta;
- auditoria e logs;
- layout desktop e responsivo quando houver mudanca visual.

Para validar isolamento, uma operacao criada em homologacao nao pode aparecer em producao. Nunca use exclusoes destrutivas em producao como teste.

## 9. Usuarios e permissoes

Perfis de codigo:

- `admin`: controle total;
- `user`: perfil visualmente chamado Standard;
- `viewer`: visualizacao e downloads autorizados, sem operacoes de escrita;
- `BIPE`: conta protegida usada pelo aplicativo.

Contas protegidas no codigo: `adm`, `BIPE` e `viewer_user`. Nao remover protecoes ou alterar seus papeis sem pedido expresso. O acesso efetivo combina perfil e modulos permitidos; validar backend e frontend, pois ocultar botao nao substitui autorizacao no servidor.

## 10. API e rotas

- Rotas publicas `/api/v1/*` usam `X-API-Key` e `PUBLIC_API_KEYS`.
- Rotas operacionais como `/notas/` usam sessao/permissoes e nao devem ser confundidas com a API publica.
- Testar sempre chave correta, incorreta e ausente.
- Swagger e OpenAPI possuem restricao administrativa no codigo atual.
- Nao enfraquecer autenticacao, CORS ou autorizacao para facilitar teste.

## 11. Deploy seguro e rollback

Antes de `main`:

- confirmar branch e diff;
- confirmar testes automatizados e manuais;
- confirmar que nenhum segredo entrou no Git;
- verificar se ha mudanca de banco;
- definir rollback para mudancas de maior risco;
- registrar o commit homologado.

Durante o deploy, observar build, startup, conexao ao banco e excecoes. Um `Deploy succeeded` nao basta. Validar a producao com operacoes predominantemente de leitura e conferir que contagens e dados existentes permanecem coerentes.

Rollback de codigo pode usar o recurso do Render ou reversao Git, mas rollback de codigo nao desfaz automaticamente alteracoes de banco. Nunca presumir reversibilidade de migracao.

## 12. Regras para o agente Codex

- Ler primeiro `AGENTS.md`, depois `README.md` e `FLUXO_BRANCHES.md`.
- Para analise/revisao, fazer apenas inspecoes de leitura; nao implementar sem pedido.
- Para implementacao, apresentar o impacto quando houver risco relevante, editar o menor escopo possivel e testar.
- O pedido recorrente do proprietario e fazer commit e push ao concluir alteracoes autorizadas; ainda assim, revisar diff e testes antes.
- Por padrao, alteracoes do painel/backend sao commitadas e enviadas em `dev_testes`, nunca em `main`.
- Merge e push em `main` constituem publicacao em producao e exigem que a promocao tenha sido solicitada ou confirmada.
- Nao modificar configuracao do Render, banco, integracao externa ou GitHub fora do escopo solicitado.
- Nao declarar producao validada sem conferir o servico produtivo depois do deploy.
- Ao encontrar contradicao, priorizar seguranca dos dados e pedir confirmacao antes de tocar producao.

## 13. Estrutura tecnica resumida

```text
backend/app/       FastAPI, regras, banco, integracao e relatorios
backend/panel/     HTML, CSS e JavaScript do painel
backend/tests/     testes automatizados
mobile/            aplicativo Android
.githooks/         protecoes locais de branch
scripts/           configuracao e verificacoes operacionais
```

Build Render:

```text
pip install -r backend/requirements.txt
```

Start Render:

```text
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 14. Criterio de conclusao

Uma alteracao so esta concluida quando:

1. escopo e branch estao corretos;
2. diff foi revisado;
3. testes passaram;
4. homologacao foi validada quando aplicavel;
5. commit e push foram executados na branch autorizada;
6. deploy correspondente terminou;
7. o ambiente alvo foi testado;
8. riscos ou pendencias foram informados claramente.
