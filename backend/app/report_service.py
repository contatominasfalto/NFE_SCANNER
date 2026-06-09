import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent


def safe_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def generate_xml(notas, filtros, output_path):
    """
    Gera relatório XML das notas fiscais cadastradas.
    XML completo conforme os campos disponíveis no banco do projeto.
    """

    root = Element("relatorio_notas_fiscais")

    metadata = SubElement(root, "metadata")
    SubElement(metadata, "sistema").text = "NFE Scanner"
    SubElement(metadata, "data_geracao").text = datetime.now().isoformat()
    SubElement(metadata, "filtros").text = safe_text(filtros)
    SubElement(metadata, "total_notas").text = str(len(notas))
    SubElement(metadata, "valor_total").text = str(sum(n.valor_total or 0 for n in notas))

    notas_node = SubElement(root, "notas")

    for nota in notas:
        nota_node = SubElement(notas_node, "nota_fiscal")

        SubElement(nota_node, "id").text = safe_text(nota.id)
        SubElement(nota_node, "numero_nf").text = safe_text(nota.numero_nf)
        SubElement(nota_node, "serie").text = safe_text(nota.serie)
        SubElement(nota_node, "data_emissao").text = safe_text(nota.data_emissao)
        SubElement(nota_node, "cnpj_fornecedor").text = safe_text(nota.cnpj_fornecedor)
        SubElement(nota_node, "nome_fornecedor").text = safe_text(nota.nome_fornecedor)
        SubElement(nota_node, "valor_total").text = safe_text(nota.valor_total)
        SubElement(nota_node, "chave_acesso").text = safe_text(nota.chave_acesso)
        SubElement(nota_node, "local").text = safe_text(nota.local)
        SubElement(nota_node, "produto").text = safe_text(nota.produto)
        SubElement(nota_node, "quantidade").text = safe_text(nota.quantidade)
        SubElement(nota_node, "transportador").text = safe_text(nota.transportador)
        SubElement(nota_node, "faturista").text = safe_text(nota.faturista)
        SubElement(nota_node, "lider_operacional").text = safe_text(nota.lider_operacional)
        SubElement(nota_node, "observacao").text = safe_text(nota.observacao)
        SubElement(nota_node, "caminho_arquivo_imagem").text = safe_text(nota.caminho_arquivo_imagem)
        SubElement(nota_node, "data_cadastro").text = safe_text(nota.data_cadastro)

    tree = ElementTree(root)
    indent(tree, space="    ", level=0)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
