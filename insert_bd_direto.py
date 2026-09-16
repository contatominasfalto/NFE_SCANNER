"""Importa notas de um JSON diretamente na tabela ``notas_fiscais``.

O comando NAO consulta a MeuDanfe. Por seguranca, apenas valida e simula por
padrao. A gravacao exige ``--executar``; producao exige tambem uma confirmacao
literal. As URLs dos bancos nunca devem ser gravadas neste arquivo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import MetaData, Table, bindparam, create_engine, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


ENVIRONMENTS = {
    "testes": {
        "variable": "NFE_SCANNER_TEST_DATABASE_URL",
        "database": "nfe_scanner_dev",
        "label": "HOMOLOGACAO",
    },
    "producao": {
        "variable": "NFE_SCANNER_PROD_DATABASE_URL",
        "database": "nfe_scanner",
        "label": "PRODUCAO",
    },
}
PRODUCTION_CONFIRMATION = "INSERIR_EM_PRODUCAO"
HISTORICAL_START = datetime(2025, 12, 1)
HISTORICAL_END = datetime(2026, 7, 1)
HISTORICAL_INDEX = "uq_notas_chave_fora_carga_historica"
REQUIRED_COLUMNS = {
    "numero_nf",
    "serie",
    "data_emissao",
    "cnpj_fornecedor",
    "nome_fornecedor",
    "valor_total",
    "chave_acesso",
    "local",
    "produto",
    "quantidade",
    "transportador",
    "faturista",
    "observacao",
    "erro_salvamento",
    "data_cadastro",
}


class ImportValidationError(ValueError):
    """Erro de entrada que deve ser corrigido antes de acessar o banco."""


@dataclass(frozen=True)
class PreparedImport:
    rows: list[dict[str, Any]]
    repeated_in_file: list[str]
    source_hash: str


def normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "_", normalized.upper()).strip("_")


def clean_text(value: Any, *, field: str, maximum: int | None = None) -> str:
    if value is None:
        raise ImportValidationError(f"{field} nao informado")
    result = str(value).strip()
    if not result:
        raise ImportValidationError(f"{field} vazio")
    if maximum is not None and len(result) > maximum:
        raise ImportValidationError(f"{field} excede {maximum} caracteres")
    return result


def parse_datetime(value: Any, field: str) -> datetime:
    text = clean_text(value, field=field)
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )
    for date_format in formats:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError as exc:
        raise ImportValidationError(
            f"{field} invalida: {text!r}; use AAAA-MM-DD HH:MM:SS"
        ) from exc


def parse_number(value: Any, field: str) -> float:
    if value is None or isinstance(value, bool):
        raise ImportValidationError(f"{field} invalido")
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    else:
        text = str(value).strip().replace(" ", "")
        if not text:
            raise ImportValidationError(f"{field} vazio")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            number = Decimal(text)
        except InvalidOperation as exc:
            raise ImportValidationError(f"{field} invalido: {value!r}") from exc
    if not number.is_finite():
        raise ImportValidationError(f"{field} deve ser finito")
    return float(number)


def map_row(raw: Any, position: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ImportValidationError(f"item {position} nao e um objeto JSON")
    item = {normalize_key(key): value for key, value in raw.items()}

    chave = re.sub(r"\D", "", clean_text(item.get("CHAVE_NF"), field="CHAVE NF"))
    if len(chave) != 44:
        raise ImportValidationError(f"CHAVE NF deve possuir 44 digitos; recebido {len(chave)}")

    local = clean_text(item.get("LOCAL"), field="LOCAL", maximum=20).upper()
    if local not in {"CDMA", "PRU"}:
        raise ImportValidationError("LOCAL deve ser CDMA ou PRU")

    data_emissao = parse_datetime(item.get("DATA_EMISSAO"), "DATA EMISSAO")
    data_cadastro = parse_datetime(item.get("DATA_HORA_DO_BIP"), "DATA/HORA DO BIP")
    if data_emissao > data_cadastro:
        raise ImportValidationError("DATA EMISSAO nao pode ser posterior a DATA/HORA DO BIP")
    if not HISTORICAL_START <= data_cadastro < HISTORICAL_END:
        raise ImportValidationError(
            "DATA/HORA DO BIP fora da carga historica permitida "
            "(01/12/2025 a 30/06/2026)"
        )
    quantidade = parse_number(item.get("QUANTIDADE"), "QUANTIDADE")
    valor_total = parse_number(item.get("VALOR_TOTAL"), "VALOR TOTAL")
    if quantidade < 0:
        raise ImportValidationError("QUANTIDADE nao pode ser negativa")
    if valor_total < 0:
        raise ImportValidationError("VALOR TOTAL nao pode ser negativo")

    return {
        "numero_nf": clean_text(item.get("NF"), field="NF", maximum=30),
        # Estrutura oficial da chave NF-e: cUF(2) + AAMM(4) + CNPJ(14) +
        # modelo(2) + serie(3) + numero(9) + demais campos.
        "serie": chave[22:25],
        "data_emissao": data_emissao,
        "cnpj_fornecedor": clean_text(item.get("CNPJ"), field="CNPJ", maximum=20),
        "nome_fornecedor": clean_text(item.get("FORNECEDOR"), field="FORNECEDOR", maximum=255),
        "valor_total": valor_total,
        "chave_acesso": chave,
        "local": local,
        "produto": clean_text(item.get("PRODUTO"), field="PRODUTO"),
        "quantidade": quantidade,
        "transportador": clean_text(item.get("TRANSPORTADOR"), field="TRANSPORTADOR", maximum=255),
        "faturista": clean_text(item.get("USUARIO"), field="USUARIO", maximum=100),
        "lider_operacional": None,
        "observacao": clean_text(item.get("OBSERVACAO"), field="OBSERVACAO"),
        "erro_salvamento": False,
        "erro_detalhe": None,
        "caminho_arquivo_imagem": None,
        "data_cadastro": data_cadastro,
    }


def prepare_file(path: Path) -> PreparedImport:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ImportValidationError(f"nao foi possivel ler {path}: {exc}") from exc
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportValidationError(f"JSON invalido em {path}: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise ImportValidationError("o arquivo deve conter uma lista JSON nao vazia")

    rows: list[dict[str, Any]] = []
    repeated: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []
    for position, raw in enumerate(payload, start=1):
        try:
            row = map_row(raw, position)
            if row["chave_acesso"] in seen:
                repeated.append(row["chave_acesso"])
            seen.add(row["chave_acesso"])
            rows.append(row)
        except ImportValidationError as exc:
            errors.append(f"item {position}: {exc}")
    if errors:
        preview = "\n".join(f"  - {error}" for error in errors[:20])
        suffix = f"\n  ... e mais {len(errors) - 20} erro(s)" if len(errors) > 20 else ""
        raise ImportValidationError(f"foram encontrados {len(errors)} erro(s):\n{preview}{suffix}")
    return PreparedImport(rows, repeated, hashlib.sha256(content).hexdigest())


def chunks(values: list[str], size: int = 500) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def get_database_url(environment: str) -> str:
    config = ENVIRONMENTS[environment]
    url = (os.getenv(config["variable"]) or os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise ImportValidationError(
            f"defina {config['variable']} (preferencial) ou DATABASE_URL no ambiente"
        )
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise ImportValidationError("URL do banco invalida") from exc
    database = (parsed.database or "").strip()
    if database != config["database"]:
        raise ImportValidationError(
            f"ambiente {environment!r} exige o banco {config['database']!r}, "
            f"mas a URL aponta para {database!r}"
        )
    if not parsed.drivername.startswith("postgresql"):
        raise ImportValidationError("este importador aceita somente PostgreSQL")
    return url


def reflect_tables(connection) -> tuple[Table, Table | None]:
    inspector = inspect(connection)
    if "notas_fiscais" not in inspector.get_table_names():
        raise ImportValidationError("tabela notas_fiscais nao encontrada")
    metadata = MetaData()
    notes = Table("notas_fiscais", metadata, autoload_with=connection)
    missing = REQUIRED_COLUMNS - set(notes.c.keys())
    if missing:
        raise ImportValidationError(f"colunas ausentes em notas_fiscais: {', '.join(sorted(missing))}")
    indexes = {index.get("name") for index in inspector.get_indexes("notas_fiscais")}
    if HISTORICAL_INDEX not in indexes:
        raise ImportValidationError(
            "indice historico ainda nao foi aplicado; aguarde o deploy/migracao do ambiente"
        )
    audit = (
        Table("audit_logs", metadata, autoload_with=connection)
        if "audit_logs" in inspector.get_table_names()
        else None
    )
    return notes, audit


def find_existing(connection, notes: Table, keys: list[str]) -> dict[str, str | None]:
    existing: dict[str, str | None] = {}
    for group in chunks(keys):
        result = connection.execute(
            select(notes.c.chave_acesso, notes.c.serie).where(notes.c.chave_acesso.in_(group))
        )
        existing.update({str(row.chave_acesso): row.serie for row in result})
    return existing


def file_was_imported(connection, audit: Table | None, source_hash: str) -> bool:
    if audit is None:
        return False
    result = connection.execute(
        select(audit.c.id)
        .where(
            audit.c.acao.in_(
                ["Importou carga historica direta", "Importou carga direta"]
            )
        )
        .where(audit.c.detalhes.contains(f"SHA256: {source_hash}"))
        .limit(1)
    ).first()
    return result is not None


def write_manifest(
    environment: str,
    database: str,
    prepared: PreparedImport,
    inserted: list[str],
    repaired_series: list[str],
) -> Path:
    directory = Path("logs_importacao")
    directory.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"importacao_{environment}_{timestamp}.json"
    payload = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "ambiente": environment,
        "banco": database,
        "sha256_arquivo_origem": prepared.source_hash,
        "quantidade_inserida": len(inserted),
        "chaves_inseridas": inserted,
        "quantidade_series_corrigidas": len(repaired_series),
        "chaves_com_serie_corrigida": repaired_series,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_import(args: argparse.Namespace) -> int:
    source = Path(args.arquivo).resolve()
    prepared = prepare_file(source)
    print(f"Arquivo validado: {source}")
    print(f"Registros validos no arquivo: {len(prepared.rows)}")
    print(f"Ocorrencias com chave repetida mantidas para insercao: {len(prepared.repeated_in_file)}")

    if args.validar_apenas:
        print("Validacao concluida sem acessar o banco.")
        return 0

    url = get_database_url(args.ambiente)
    config = ENVIRONMENTS[args.ambiente]
    print(f"Ambiente selecionado: {config['label']}")
    print(f"Banco confirmado: {config['database']}")

    if args.executar and args.ambiente == "producao" and args.confirmar_producao != PRODUCTION_CONFIRMATION:
        raise ImportValidationError(
            f"para gravar em producao, informe --confirmar-producao {PRODUCTION_CONFIRMATION}"
        )

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            notes, audit = reflect_tables(connection)
            already_imported = file_was_imported(connection, audit, prepared.source_hash)
            if already_imported:
                raise ImportValidationError(
                    "este arquivo ja foi importado integralmente; operacao bloqueada para evitar repeticao acidental"
                )
            existing = find_existing(connection, notes, [row["chave_acesso"] for row in prepared.rows])
            new_rows = prepared.rows
            series_repairs = [
                {"_chave": key, "_serie": key[22:25]}
                for key, current_series in existing.items()
                if not str(current_series or "").strip()
            ]
            print(f"Chaves distintas do arquivo que ja existem no banco: {len(existing)}")
            print(f"Registros historicos prontos para insercao: {len(new_rows)}")
            print(f"Registros existentes sem serie encontrados: {len(series_repairs)}")

            if not args.executar:
                print("SIMULACAO concluida: nenhuma alteracao foi gravada.")
                print("Revise os totais e execute novamente com --executar para confirmar.")
                return 0
            if series_repairs and not args.corrigir_series_existentes:
                print("Series existentes nao serao alteradas sem --corrigir-series-existentes.")
            repairs_to_apply = series_repairs if args.corrigir_series_existentes else []
            if not new_rows and not repairs_to_apply:
                print("Nenhuma nota nova ou correcao autorizada. Banco nao alterado.")
                return 0

            database_columns = set(notes.c.keys())
            rows_for_database = [
                {key: value for key, value in row.items() if key in database_columns}
                for row in new_rows
            ]
            if rows_for_database:
                connection.execute(notes.insert(), rows_for_database)
            if repairs_to_apply:
                correction = (
                    notes.update()
                    .where(notes.c.chave_acesso == bindparam("_chave"))
                    .values(serie=bindparam("_serie"))
                )
                connection.execute(correction, repairs_to_apply)
            if audit is not None:
                connection.execute(
                    audit.insert().values(
                        created_at=datetime.now(),
                        usuario="insert_bd_direto",
                        acao="Importou carga historica direta",
                        area="Notas fiscais",
                        entidade="NotaFiscal",
                        entidade_id=None,
                        descricao=(
                            f"Carga direta inseriu {len(new_rows)} nota(s) e corrigiu "
                            f"{len(repairs_to_apply)} serie(s) em {config['label']}."
                        ),
                        detalhes=(
                            f"Arquivo: {source.name} | SHA256: {prepared.source_hash} | "
                            f"Chaves ja existentes no banco: {len(existing)} | "
                            f"Ocorrencias repetidas mantidas: {len(prepared.repeated_in_file)}"
                        ),
                    )
                )
        inserted = [row["chave_acesso"] for row in new_rows]
        repaired = [item["_chave"] for item in repairs_to_apply]
        manifest = write_manifest(args.ambiente, config["database"], prepared, inserted, repaired)
        print(f"SUCESSO: {len(inserted)} nota(s) inserida(s) em uma unica transacao.")
        print(f"SUCESSO: {len(repaired)} serie(s) existente(s) corrigida(s) na mesma transacao.")
        print(f"Manifesto local para conferencia/rollback: {manifest.resolve()}")
        return 0
    except IntegrityError as exc:
        raise ImportValidationError(
            "a transacao foi revertida por conflito de integridade; nenhuma nota deste lote foi inserida"
        ) from exc
    except SQLAlchemyError as exc:
        raise ImportValidationError(
            "falha de banco; a transacao foi revertida e a URL nao sera exibida"
        ) from exc
    finally:
        engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida e insere base_json.json diretamente no PostgreSQL do NFE Scanner."
    )
    parser.add_argument("--ambiente", choices=sorted(ENVIRONMENTS), required=False)
    parser.add_argument("--arquivo", default="base_json.json")
    parser.add_argument(
        "--validar-apenas",
        action="store_true",
        help="valida o JSON sem acessar qualquer banco",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="grava a transacao; sem esta opcao o banco e apenas consultado",
    )
    parser.add_argument("--confirmar-producao", default="")
    parser.add_argument(
        "--corrigir-series-existentes",
        action="store_true",
        help="preenche serie vazia apenas nas chaves presentes no JSON",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.validar_apenas and not args.ambiente:
        parser.error("--ambiente e obrigatorio, exceto com --validar-apenas")
    if args.validar_apenas and args.executar:
        parser.error("--validar-apenas e --executar nao podem ser usados juntos")
    try:
        return run_import(args)
    except ImportValidationError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
