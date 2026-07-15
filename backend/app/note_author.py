APP_FATURISTA = "BIPE"
ERROR_AUTHOR = "ERRO"


def usuario_lancamento(username: str | None) -> str:
    username = (username or "").strip()
    return APP_FATURISTA if username == APP_FATURISTA else username


def usuario_efetivo_erro(faturista: str | None, username: str | None) -> str:
    faturista = (faturista or "").strip()
    if faturista and faturista.upper() != ERROR_AUTHOR:
        return faturista
    return usuario_lancamento(username)


def aplicar_usuario_lancamento(nota_data, username: str | None):
    return nota_data.model_copy(update={"faturista": usuario_lancamento(username)})
