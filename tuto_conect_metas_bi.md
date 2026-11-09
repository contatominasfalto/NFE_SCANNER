# Tutorial de conexão de Metas com Power BI

**Projeto:** NFE Scanner / Painel Scanner Agera

**Preparado em:** 09/11/2026

**Destinatários:** gerente responsável pelo BI e administrador do projeto.

Este documento explica como consultar no Power BI as metas de Expedição e
Recebimento cadastradas no painel. A conexão é diretamente com o PostgreSQL do
Render. O gerente não precisa exportar planilhas nem deixar o painel aberto.

**Situação desta entrega:** preparação na branch `dev_testes`. Produção só será
publicada após aprovação do proprietário. Credenciais reais não ficam neste
documento. A conta PostgreSQL exclusiva do BI é criada separadamente pelo
administrador; publicar o código não cria nem revela uma senha de acesso.

## 1. O que precisa estar pronto

Antes de começar, o gerente deve receber do administrador:

| Informação | Homologação | Produção, após liberação |
| --- | --- | --- |
| Serviço do banco no Render | `nfe-scanner-dev-db` | `nfe-scanner-db` |
| Nome do banco PostgreSQL | `nfe_scanner_dev` | `nfe_scanner` |
| Host | Host **externo** informado pelo administrador | Host **externo** informado pelo administrador |
| Porta | `5432` | `5432` |
| Login exclusivo de BI | `powerbi_metas_testes` | `powerbi_metas` |
| Senha | Recebida por canal privado | Recebida por canal privado |
| Acesso de rede | IP/origem da conexão autorizado | IP/origem da conexão autorizado |

Os nomes de login acima são os utilizados pelo provisionador deste projeto.
O administrador deve confirmar que a conta foi criada antes de entregar a
conexão. Não usar `adm`, `BIPE`, a senha do painel ou o usuário principal do backend.

**Não misturar os ambientes.** As metas digitadas em testes não aparecem em
produção. Na promoção, o código e a estrutura são publicados; os cadastros não
são copiados automaticamente.

## 2. Quais dados o Power BI deve carregar

O projeto prepara três views, que são consultas salvas no PostgreSQL:

| View | Conteúdo |
| --- | --- |
| `powerbi.vw_metas` | Expedição e Recebimento em uma base única; opção recomendada |
| `powerbi.vw_metas_expedicao` | Somente Expedição |
| `powerbi.vw_metas_recebimento` | Somente Recebimento, incluindo ajustes |

**Escolha a view unificada OU as duas separadas. Não junte as três como se fossem
dados diferentes, pois as views separadas repetem as linhas da unificada.**

A view unificada tem uma linha para cada combinação de data, operação e unidade.
Um mês com 30 dias gera 60 linhas por operação: 30 para A1BR e 30 para A2BR.
Dias sem valores informados continuam presentes, com valores nulos.

### Dicionário dos campos

| Campo | Significado | Tipo sugerido no Power BI |
| --- | --- | --- |
| `mes_id` | Identificador interno do planejamento mensal | Número inteiro |
| `dia_id` | Identificador interno do dia; aparece uma vez por unidade | Número inteiro |
| `data` | Data para a qual a meta foi planejada | Data |
| `ano` | Ano de referência | Número inteiro |
| `mes` | Número do mês, de 1 a 12 | Número inteiro |
| `competencia` | Primeiro dia do mês de referência | Data |
| `operacao` | `expedicao` ou `recebimento` | Texto |
| `unidade` | `A1BR` ou `A2BR` | Texto |
| `meta_ton` | Meta diária, já em toneladas | Número decimal fixo |
| `ajuste_ton` | Ajuste de Recebimento, já em toneladas | Número decimal fixo |
| `meta_informada` | Indica se a meta foi preenchida, inclusive com zero | Verdadeiro/Falso |
| `ajuste_informado` | Indica se o ajuste foi preenchido, inclusive com zero | Verdadeiro/Falso |
| `versao` | Versão do último salvamento do planejamento | Número inteiro |
| `atualizado_em` | Data/hora local de São Paulo do último salvamento | Data/Hora |
| `atualizado_por` | Usuário que fez o último salvamento | Texto |

### Regras para interpretar corretamente

- **Os valores já estão em toneladas. Não dividir por 1.000.**
- Meta em branco é diferente de meta preenchida com zero. Não substituir
  automaticamente os nulos por zero se essa distinção for importante no relatório.
- Metas são não negativas; ajustes de Recebimento podem ser positivos ou negativos.
- Ajustes são apresentados separadamente. Não são somados nem subtraídos da meta
  pela view. Uma regra de “meta ajustada” depende de decisão da operação.
- Expedição não tem ajustes; `ajuste_ton` fica nulo nessa operação.
- As views mostram o estado atual salvo. Edições aparecem na próxima consulta;
  uma exclusão remove as linhas na próxima atualização completa do BI.
- As views não representam um histórico de versões. A rastreabilidade completa
  continua na auditoria do painel, fora da permissão deste login de BI.

## 3. Conectar no Power BI Desktop

1. Abra uma versão atual do **Power BI Desktop**.
2. Selecione **Página Inicial → Obter dados → Mais**.
3. Procure **Banco de dados PostgreSQL** e clique em **Conectar**.
4. Em **Servidor**, informe o host externo recebido. Exemplo de formato:
   `SEU_HOST_EXTERNO:5432`. Não cole a URL `/painel` nesse campo.
5. Em **Banco de dados**, informe `nfe_scanner_dev` para testes ou
   `nfe_scanner` para produção, conforme a conexão liberada.
6. Selecione **Importar** como modo inicial e confirme.
7. Na autenticação, escolha **Banco de dados** e informe o login e a senha do BI.
8. Mantenha a conexão criptografada. Se houver erro de TLS/certificado, peça ao
   administrador que confira o host e a rede; não aceite conexão sem criptografia.
9. No navegador, procure o schema **powerbi** e marque **vw_metas**.
10. Selecione **Transformar dados**, confira os tipos da tabela acima e renomeie
    a consulta para **Metas**.
11. Selecione **Fechar e aplicar**.

O conector atual já inclui o provedor PostgreSQL. Não é necessário instalar
driver Python, SQLAlchemy ou bibliotecas do Scanner no computador do gerente.

Se o relatório já se conecta ao mesmo banco, adicione a view pela conexão
existente ou crie uma consulta adicional. Confirme as permissões dessa credencial;
o usuário exclusivo de Metas não recebe acesso às notas automaticamente.

## 4. Modelo e medidas iniciais

Na tabela **Metas**, formate `meta_ton` e `ajuste_ton` para exibição com três
casas decimais. No formato brasileiro, `1.234,567` significa 1.234,567 toneladas.
Use valores numéricos para somar; não converta essas colunas em texto.

Em **Modelagem → Nova medida**, crie:

```dax
Meta Total (TON) = SUM(Metas[meta_ton])
```

```dax
Meta Expedição (TON) =
CALCULATE(
    [Meta Total (TON)],
    Metas[operacao] = "expedicao"
)
```

```dax
Meta Recebimento (TON) =
CALCULATE(
    [Meta Total (TON)],
    Metas[operacao] = "recebimento"
)
```

```dax
Ajuste Recebimento (TON) =
CALCULATE(
    SUM(Metas[ajuste_ton]),
    Metas[operacao] = "recebimento"
)
```

Se a instalação utilizar separador DAX localizado, substitua as vírgulas entre
argumentos por ponto e vírgula. Não mude as vírgulas de dados manualmente.

Para começar, monte:

- Segmentações por `competencia`, `operacao` e `unidade`.
- Uma matriz com `data` nas linhas, `unidade` nas colunas e a medida da meta
  correspondente nos valores.
- Cartões para os totais de Expedição e Recebimento.
- Uma matriz separada para ajustes de Recebimento.

Filtre a competência desejada antes de comparar o total com o painel.
Para totais operacionais, mantenha Expedição e Recebimento separados; somar as
duas operações pode não representar o indicador que a empresa deseja acompanhar.

Se houver tabela Calendário, relacione `Calendario[Data]` a `Metas[data]` como
**um para muitos**, com filtragem da dimensão para as metas. Para confrontar
metas e realizado, use dimensões comuns; não una diretamente as linhas de notas
às linhas de metas apenas pela data, pois isso pode multiplicar os valores.

### Comparação com o realizado

As metas são por A1BR/A2BR. As notas atuais têm local CDMA/PRU. O gerente e a
operação precisam definir a correspondência: esses campos não são equivalentes
automaticamente. Também é necessário definir a fonte de realizado de Expedição
e Recebimento e se a referência será emissão ou bipagem. A view não inventa essa
regra. Se usar as notas existentes, escolher `quantidade_ton` na view de notas;
essa coluna já converte os kg armazenados no cadastro.

## 5. Conferir os resultados

1. No painel, escolha uma operação, um mês e uma unidade com valores salvos.
2. No BI, aplique exatamente os mesmos filtros e clique em **Atualizar**.
3. Compare a soma de `meta_ton` com o total da coluna no painel.
4. Em Recebimento, compare separadamente a soma de `ajuste_ton`.
5. Confira um dia em branco e um dia com zero; eles devem continuar distintos.
6. Se um mês foi excluído, execute atualização completa da consulta para refletir
   a exclusão. Este projeto não configura atualização incremental automaticamente.

Um banco de testes sem meses cadastrados retorna views vazias. Isso não é erro
de conexão. As views passam a retornar linhas quando os planejamentos são salvos.

## 6. Publicar e manter a atualização no Power BI Service

No modo Importar, o BI mantém uma cópia dos dados. Alterar o painel não atualiza
o relatório instantaneamente: é necessário atualizar o modelo semântico.

1. Salve o arquivo `.pbix` e publique no workspace autorizado da empresa.
2. No Power BI Service, abra as configurações do modelo semântico publicado.
3. Configure a conexão de nuvem PostgreSQL ou a conexão por gateway, conforme a
   rede da empresa, com o mesmo servidor/banco e a credencial de BI.
4. Execute **Atualizar agora** e confira o histórico de atualização.
5. Depois de uma execução bem-sucedida, configure a atualização agendada nos
   horários necessários e habilite notificações de falha.
6. Teste a atualização com o computador do gerente desligado. Se ela depender de
   gateway instalado nesse computador, precisará de uma máquina sempre ligada.

O conector PostgreSQL admite conexão de nuvem e por gateway. A necessidade de
gateway depende da rede e da configuração do modelo, não apenas de o banco estar
no Render. Frequência disponível e compartilhamento dependem da licença/capacidade
do Power BI. Use os limites apresentados no workspace da empresa.

**DirectQuery** é uma alternativa para consultar a fonte durante a navegação do
relatório, com maior dependência da disponibilidade e do desempenho do banco.
Comece com Importar para o planejamento mensal; avalie DirectQuery se necessário.

## 7. Trocar a conexão de testes pela de produção

Somente depois da aprovação e publicação produtiva:

1. O administrador confirma as views e provisiona `powerbi_metas` no banco
   `nfe_scanner`. O usuário `powerbi_metas_testes` não é uma credencial produtiva.
2. Faça uma cópia do `.pbix` homologado para preservar o teste.
3. No Power BI Desktop, abra **Transformar dados → Configurações da fonte de
   dados → Alterar fonte** e informe servidor e banco produtivos. Se usar a opção
   Power Query abaixo, altere os parâmetros de servidor/banco.
4. Informe a credencial produtiva, atualize e confira os totais novamente.
5. Publique na área produtiva e ajuste também a conexão do modelo no Service.
6. Confirme que o relatório consulta produção, sem misturar os dois ambientes.

## 8. Alternativa com consulta Power Query

Se preferir configurar por código, crie uma **Consulta em branco**, abra o
**Editor avançado** e use o modelo abaixo. Os valores são marcadores, não dados
reais. Não coloque usuário ou senha no código M; use a janela de credenciais.

```powerquery
let
    Servidor = "SEU_HOST_EXTERNO:5432",
    Banco = "nfe_scanner_dev",
    Fonte = PostgreSQL.Database(Servidor, Banco, [CreateNavigationProperties=false]),
    Metas = Fonte{[Schema="powerbi", Item="vw_metas"]}[Data]
in
    Metas
```

Para produção, informe o host produtivo e `nfe_scanner`, somente após a liberação.

## 9. Solução de problemas

| Sintoma | O que conferir |
| --- | --- |
| Servidor não encontrado ou timeout | Host externo completo, porta 5432, rede/firewall e origem autorizada no Render |
| Erro de senha | Login PostgreSQL de BI do ambiente correto; não é o login do painel |
| Schema/view não aparece | Administrador confirma deploy e provisionamento; reconectar/atualizar o navegador de dados |
| Permissão negada | Conta precisa de USAGE no schema e SELECT nas três views; não usar a conta principal para contornar |
| Erro TLS/certificado | Conferir host completo e criptografia; atualizar o cliente e envolver o administrador |
| View vazia | Conferir banco e existência de meses salvos naquela operação |
| Total em dobro | Não combinar a view unificada com as duas filtradas nem multiplicar metas em junção com notas |
| Valor mil vezes menor | As metas já são TON; remover divisão por 1.000 |
| Desktop atualiza, Service não | Credenciais/conexão do modelo, rede, gateway quando utilizado e histórico de atualização |
| Alteração ou exclusão ainda não aparece | Salvar no painel e executar atualização completa no BI |

## 10. Preparação técnica — somente administrador

Esta seção não precisa ser executada pelo gerente. Não executar ações produtivas
antes da autorização final do proprietário.

### 10.1 Views e verificação

O arquivo `backend/app/metas_bi.sql` é a fonte das views. O backend as cria ou
atualiza em transação durante a inicialização PostgreSQL, depois das tabelas.
Não muda valores cadastrados, contas do painel nem permissões de outros usuários.
O arquivo geral `docs/powerbi_setup.sql` continua destinado à camada já existente;
não é preciso executá-lo para liberar somente as metas.

Após o deploy, um Admin autenticado no painel pode abrir, no mesmo navegador:

```text
https://nfe-scanner-dev.onrender.com/metas/bi/status/
```

O diagnóstico mostra o nome do banco, as três views e suas contagens. Não fornece
senha ou dados das linhas. Acesso restrito a Admin. Em produção, após autorização,
usar o mesmo caminho em `https://nfe-scanner-api.onrender.com`.

### 10.2 Criar a credencial exclusiva

Usar um terminal interativo, na raiz do projeto, com as dependências do backend.
O provisionador não importa o backend operacional nem lê `.env`. Ele aceita só
o banco explicitamente correspondente ao ambiente e exige SSL.

Simular em homologação:

```powershell
.\venv\Scripts\python.exe .\scripts\preparar_metas_bi.py --ambiente testes
```

Informe a URL administrativa externa **na entrada oculta solicitada**, não em
arquivo, print, histórico de comando ou chat. A simulação não grava nada.
Alternativamente, o administrador pode disponibilizar a URL por variável de
ambiente exclusiva `NFE_SCANNER_TEST_DATABASE_URL` em seu processo seguro.

Depois de conferir a simulação:

```powershell
.\venv\Scripts\python.exe .\scripts\preparar_metas_bi.py --ambiente testes --executar
```

Será solicitada uma senha nova de pelo menos 20 caracteres e sua confirmação,
ambas ocultas. Armazene essa senha no gerenciador de senhas da empresa. O script
não imprime nem salva a senha. Entregue-a ao gerente por canal privado.

O provisionador cria `powerbi_metas_testes` com login, sem privilégios de
administração, com USAGE em `powerbi` e SELECT apenas nas três views de metas.
Também configura transações de leitura por padrão. Não concede SELECT nas
tabelas internas, não concede acesso a notas/usuários/auditoria e não libera
todas as views do schema. Permissões amplas já herdadas de PUBLIC provocam
recusa e rollback, para revisão do administrador.

Se o login já existir, o script recusa alterar senha/permissões automaticamente.
O administrador deve verificar quem o utiliza antes de qualquer ajuste.
É necessária uma conta PostgreSQL administrativa com permissão de criar roles;
o login de Admin do painel não concede essa permissão no PostgreSQL.

Não usar o botão de **nova credencial padrão** do Render para criar este usuário
limitado. O provisionador cria uma role SQL separada, sem substituir o usuário
padrão ou modificar a `DATABASE_URL` do backend.

### 10.3 Preparação produtiva, somente após aprovação

Confirmar a homologação, fazer backup de `nfe-scanner-db` e publicar o módulo
aprovado. Em seguida, simular e executar a criação do login produtivo:

```powershell
.\venv\Scripts\python.exe .\scripts\preparar_metas_bi.py --ambiente producao
```

```powershell
.\venv\Scripts\python.exe .\scripts\preparar_metas_bi.py --ambiente producao --executar --confirmar-producao PREPARAR_BI_EM_PRODUCAO
```

A URL deve ser a externa de `nfe_scanner`; se utilizar variável, o nome exclusivo
é `NFE_SCANNER_PROD_DATABASE_URL`. Não usar o computador local para iniciar o
backend ou executar migrações apontando para produção. Este utilitário é uma
operação administrativa explícita, separada do backend, a ser executada somente
com autorização produtiva.

### 10.4 Rede, segurança e rollback

No Render, conferir a origem autorizada das conexões externas. Desktop e Power
BI Service podem sair por origens diferentes; se houver gateway, conferir a
origem de saída dele. Não desativar TLS para resolver falha de conexão.

O acesso direto não usa as permissões de módulo do painel. O administrador do
Power BI também deve controlar workspace, compartilhamento e eventual segurança
por linha do relatório. O login descrito lê as metas de todas as unidades.

Em rollback de código, preservar tabelas, metas e auditoria. As views podem ser
mantidas enquanto houver relatórios dependentes. Se for necessário suspender o
BI, o administrador deve suspender especificamente o login exclusivo, sem trocar
a senha ou a conexão do backend. Não apagar dados para desfazer a integração.

## 11. Referências oficiais

- [Microsoft — Conector PostgreSQL](https://learn.microsoft.com/en-us/power-query/connectors/postgresql)
- [Microsoft — Atualização de dados no Power BI](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data)
- [Render — Conexão PostgreSQL, TLS e rede](https://render.com/docs/postgresql-creating-connecting)
- [Render — Diferença entre credencial padrão e usuário SQL](https://render.com/docs/postgresql-credentials)
