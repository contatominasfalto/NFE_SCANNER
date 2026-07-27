# Guia Power BI - NFE Scanner

Este guia prepara o consumo dos dados do NFE Scanner no Power BI.

## Objetivo

Deixar o Power BI conectado ao PostgreSQL do Render usando views prontas para indicadores, sem expor tabelas internas desnecessarias e sem permitir escrita no banco.

## Fonte oficial dos dados

```text
PostgreSQL Render
```

O Power BI deve usar a **External Database URL** do banco Render, porque o Power BI roda fora da rede privada do Render.

## Views disponiveis

| View | Uso sugerido |
| --- | --- |
| `powerbi.vw_notas_fiscais` | Base completa para dashboards e filtros |
| `powerbi.vw_notas_validas` | Notas sem erro |
| `powerbi.vw_notas_com_erro` | Acompanhamento de pendencias |
| `powerbi.vw_resumo_dia_bip` | Indicadores por data de bipagem |
| `powerbi.vw_resumo_dia_emissao` | Indicadores por data de emissao |
| `powerbi.vw_resumo_material` | Quantidade por material |
| `powerbi.vw_resumo_material_local` | Quantidade por material e local |
| `powerbi.vw_resumo_usuario` | Produtividade por usuario |
| `powerbi.vw_usuarios` | Usuarios cadastrados |
| `powerbi.vw_auditoria` | Rastreabilidade |

## Passo 1 - Criar as views

Execute o arquivo:

```text
docs/powerbi_setup.sql
```

Onde aplicar:

```text
PostgreSQL do Render
```

Pode aplicar via:

- DBeaver;
- pgAdmin;
- psql;
- script Python local;
- qualquer cliente PostgreSQL que aceite a External Database URL do Render.

Opcao mais simples via PowerShell, na raiz do projeto:

```powershell
$env:PG_URL = "COLE_AQUI_A_EXTERNAL_DATABASE_URL_DO_RENDER_COM_SSLMODE_REQUIRE"
.\venv\Scripts\python.exe docs\apply_powerbi_setup.py
```

## Passo 2 - Criar usuario somente leitura

Recomendado:

```text
powerbi_nfe
```

Esse usuario deve ter apenas:

```text
CONNECT no banco
USAGE no schema powerbi
SELECT nas views do schema powerbi
```

Se o Render nao permitir `CREATE ROLE` via SQL, use uma credencial do proprio Render ou a credencial atual temporariamente.

## Passo 3 - Conectar no Power BI Desktop

No Power BI Desktop:

1. Clique em **Obter dados**.
2. Escolha **Banco de dados PostgreSQL**.
3. Informe o servidor externo do Render.
4. Informe o banco:

```text
nfe_scanner
```

5. Em modo de conectividade, escolha uma das opcoes:

```text
Import
```

ou

```text
DirectQuery
```

## Recomendacao de modo

Para comecar:

```text
Import
```

Motivo:

- dashboard mais rapido;
- menos carga no banco;
- mais simples de manter.

Se a necessidade for quase tempo real:

```text
DirectQuery
```

Motivo:

- consulta o banco na hora;
- melhor para dados operacionais que mudam durante o dia.

## Passo 4 - Selecionar tabelas/views

No navegador do Power BI, selecione o schema:

```text
powerbi
```

E carregue as views desejadas.

Para um painel completo, selecione:

```text
vw_notas_fiscais
vw_notas_com_erro
vw_resumo_dia_bip
vw_resumo_dia_emissao
vw_resumo_material
vw_resumo_material_local
vw_resumo_usuario
vw_auditoria
```

## Campos mais importantes

Na view `vw_notas_fiscais`:

| Campo | Descricao |
| --- | --- |
| `data_hora_bip` | Data e hora real da bipagem |
| `data_bip` | Data da bipagem |
| `data_hora_emissao` | Data e hora de emissao da nota |
| `data_emissao` | Data de emissao |
| `material` | Produto/material |
| `local` | CDMA ou PRU |
| `quantidade_kg` | Peso em kg |
| `quantidade_ton` | Peso em toneladas |
| `usuario_lancamento` | Usuario que lancou a nota |
| `status_nota` | Valida ou Com erro |
| `nota_valida` | Booleano para filtros |

## Indicadores sugeridos

- Total de notas cadastradas.
- Peso total em kg.
- Peso total em toneladas.
- Notas por data de bip.
- Notas por data de emissao.
- Material por periodo.
- Material por local.
- Peso por local.
- Quantidade por usuario.
- Notas com erro.
- Evolucao diaria.
- Rastreabilidade por usuario.

## Observacao de seguranca

Nao usar a senha principal do sistema em arquivos compartilhados.

O ideal e o gerente receber uma credencial somente leitura, criada exclusivamente para Power BI.
