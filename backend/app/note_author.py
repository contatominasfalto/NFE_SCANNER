APP_FATURISTA = "BIPE"


def usuario_lancamento(username: str | None) -> str:
    username = (username or "").strip()
    return APP_FATURISTA if username == APP_FATURISTA else username


def aplicar_usuario_lancamento(nota_data, username: str | None):
    return nota_data.model_copy(update={"faturista": usuario_lancamento(username)})
