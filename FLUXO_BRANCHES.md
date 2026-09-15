# Fluxo de branches do NFE Scanner

O repositorio utiliza duas branches fixas:

- `main`: producao e desenvolvimento do aplicativo Android.
- `dev_testes`: desenvolvimento e homologacao do painel/backend.

## Configuracao em uma nova maquina

Depois de clonar ou atualizar o repositorio na `dev_testes`, execute:

```powershell
.\scripts\configurar_git.ps1
```

O comando ativa os hooks versionados apenas naquele clone.

## Painel e backend

```powershell
git switch dev_testes
git pull origin dev_testes
```

Desenvolva, teste e publique na homologacao:

```powershell
git add backend
git commit -m "descricao_da_alteracao"
git push origin dev_testes
```

Depois de aprovar a homologacao, promova para producao:

```powershell
git switch main
git pull origin main
git merge --no-ff dev_testes
git push origin main
git switch dev_testes
```

## Aplicativo Android

```powershell
git switch main
git pull origin main
```

Desenvolva e publique pelo fluxo atual:

```powershell
git add mobile
git commit -m "descricao_da_alteracao_android"
git push origin main
```

Depois sincronize a alteracao para evitar divergencia:

```powershell
git switch dev_testes
git pull origin dev_testes
git merge main
git push origin dev_testes
```

## Protecoes locais

- `mobile/` nao pode ser commitado em `dev_testes`.
- `backend/` nao pode ser commitado diretamente em `main`.
- O merge `dev_testes -> main` continua permitido.
- O hook nao apaga alteracoes; apenas cancela o commit incorreto.
- Em cada novo clone, execute novamente `scripts/configurar_git.ps1`.

## Ambientes Render

- Producao: servico atual, branch `main`, banco produtivo.
- Homologacao: novo servico, branch `dev_testes`, banco exclusivo de testes.
- A chave MeuDanfe pode ser compartilhada conforme a decisao operacional.
- `DATABASE_URL`, `SECRET_KEY` e `PUBLIC_API_KEYS` devem ser diferentes.

O servico de homologacao nunca deve receber a `DATABASE_URL` produtiva.
