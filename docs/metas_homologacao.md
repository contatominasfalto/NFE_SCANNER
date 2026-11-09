# Módulo Meta — homologação

Implementação baseada em **Planejamento Aba Metas Painel Scanner Agera.docx**.
Escopo exclusivo do painel/backend, na branch `dev_testes`. O APK não muda.
A publicação em produção depende de nova aprovação após a homologação.

## Funcionalidades e critérios de aceitação

- O menu **Meta** fica abaixo de **Rastreabilidade**, com **Expedição** e
  **Recebimento** independentes.
- Selecionar mês e ano em **Mês de referência** e clicar em **Criar mês** gera
  todos os dias do período. Fevereiro considera os anos bissextos.
- Expedição tem as metas **A1BR** e **A2BR**.
- Recebimento tem metas **A1BR/A2BR** e ajustes **A1BR/A2BR**.
- Os valores são em **toneladas**, com até três casas decimais. A entrada aceita
  `1234,567`, `1.234,567` ou `1234.567`; a tela mostra `1.234,567`.
- Campos vazios permanecem vazios no banco; zero é um valor informado.
- Metas não podem ser negativas. Ajustes podem ser positivos ou negativos,
  permitindo correções. Ajustes e metas têm totais gerais separados, como no
  modelo do documento; ajustes não alteram implicitamente a meta.
- **Salvar metas** grava o mês completo. **Editar mês** permite alterações;
  **Cancelar edição** recupera o último salvamento. **Limpar dia** esvazia os
  campos daquele dia na edição; é necessário salvar para confirmar.
- **Meses cadastrados** lista somente os meses salvos daquela operação, do
  mais recente para o mais antigo. Selecionar um mês carrega o último estado
  salvo. Criar um período já existente abre o planejamento cadastrado.
- **Excluir mês** exige confirmação e exclui somente o mês e a operação
  selecionados. A auditoria é preservada.
- Toda criação, edição e exclusão grava **Rastreabilidade**, com usuário,
  período e valores anteriores/novos. A gravação das metas e da auditoria
  pertence à mesma transação; se a auditoria falhar, as metas não mudam.
- Dois usuários não podem sobrescrever silenciosamente a edição um do outro:
  cada gravação verifica a versão e a identidade do planejamento.
- Acesso padrão somente para Admin. Admin pode conceder **Metas** em
  **Usuários → Módulos permitidos** a Standard e Viewer. Standard autorizado
  pode operar; Viewer autorizado pode consultar, mantendo a regra geral de
  somente leitura do projeto. A restrição é verificada também nas rotas HTTP.
- Não são concedidos módulos automaticamente aos usuários existentes.

## Banco, deploy e rollback

São adicionadas duas tabelas relacionadas no banco do serviço:

| Tabela | Conteúdo |
| --- | --- |
| `metas_meses` | Operação, ano/mês único, versão, usuário e data do último salvamento |
| `metas_dias` | Data, metas A1BR/A2BR e ajustes A1BR/A2BR em `NUMERIC(15,3)` |

Separar o cabeçalho mensal dos valores diários permite períodos vazios,
unicidade, controle de versão e exclusão consistente. Não há novas colunas,
conversões, exclusões ou migração dos dados de notas, usuários ou auditoria.
As tabelas são registradas antes do `Base.metadata.create_all()` já existente
na inicialização. Repetir a inicialização preserva tabelas e registros.
`ensure_schema()` não foi alterado.

Primeira publicação exclusivamente em `nfe-scanner-dev`, cujo banco deve ser
`nfe_scanner_dev`. O `.env` local não deve ser usado para iniciar a aplicação:
ele pode apontar para produção. Os testes usam uma aplicação separada com
SQLite em memória, sem importar `app.main`, `config` ou `.env`; o bloqueio de
SQLite do backend operacional permanece intacto.

Antes de promover a produção: validar os critérios acima em homologação,
confirmar o banco de cada serviço, fazer backup de `nfe-scanner-db` e registrar
o commit aprovado. A autorização de homologação não autoriza promoção.

Rollback de código: reverter a promoção/publicação com um commit de reversão
ou voltar ao deploy anterior no Render. **Preservar as tabelas novas e seus
dados**. Voltar o código remove o acesso ao módulo, mas não apaga o planejamento.
Não executar `DROP`, apagar tabelas ou remover auditoria durante rollback.

## Verificações locais

Dependências adicionais de teste em `backend/requirements-dev.txt` (`httpx`).

```powershell
Push-Location backend
..\venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py"
Pop-Location
node --check backend/panel/metas.js
node --check backend/panel/app.js
```

Os testes HTTP cobrem CRUD, auditoria atômica, restauração após falha,
concorrência, duplicidade, permissões, calendários, limites e precisão decimal.
O DDL também é compilado para PostgreSQL. A validação real em PostgreSQL é
feita no serviço de homologação após o deploy, nunca usando o banco produtivo.
