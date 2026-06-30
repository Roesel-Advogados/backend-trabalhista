"""Prompts (system + montagem) para geração das peças por IA."""

SYSTEM_CONTESTACAO = (
    "Você é advogado trabalhista do escritório, especialista em defesa do "
    "reclamado. Redige contestações técnicas, no estilo, estrutura e "
    "vocabulário do escritório, seguindo rigorosamente os modelos fornecidos. "
    "Use as teses e a formatação das defesas de referência. Produza um "
    "rascunho completo, pronto para revisão humana — nunca invente fatos não "
    "presentes na petição inicial."
)

SYSTEM_RECURSO = (
    "Você é advogado trabalhista do escritório. Redige Recurso Ordinário "
    "contra sentença desfavorável, no estilo do escritório, atacando os "
    "fundamentos da decisão com técnica recursal e nas teses dos modelos "
    "fornecidos. Não invente fatos fora da sentença e dos autos."
)


def _bloco_referencias(refs: list[dict]) -> str:
    if not refs:
        return "(Nenhuma defesa de referência encontrada na memória.)"
    partes = []
    for i, r in enumerate(refs, 1):
        sim = r.get("similaridade", 0)
        partes.append(
            f"### Modelo {i} — {r.get('titulo','(sem título)')} "
            f"(similaridade {sim:.2f})\n{r.get('conteudo','')}"
        )
    return "\n\n".join(partes)


def prompt_contestacao(inicial: str, refs: list[dict]) -> str:
    return (
        "Gere a CONTESTAÇÃO para a petição inicial abaixo, seguindo o estilo "
        "e as teses dos modelos do escritório.\n\n"
        f"## PETIÇÃO INICIAL (reclamante)\n{inicial}\n\n"
        f"## MODELOS DE REFERÊNCIA DO ESCRITÓRIO\n{_bloco_referencias(refs)}\n\n"
        "## TAREFA\nRedija a contestação completa em texto corrido jurídico, "
        "com preliminares (se cabíveis), mérito ponto a ponto contra cada "
        "pedido, e requerimentos finais."
    )


def prompt_recurso(sentenca: str, refs: list[dict]) -> str:
    return (
        "Gere o RECURSO ORDINÁRIO contra a sentença abaixo, no estilo do "
        "escritório.\n\n"
        f"## SENTENÇA\n{sentenca}\n\n"
        f"## MODELOS DE REFERÊNCIA\n{_bloco_referencias(refs)}\n\n"
        "## TAREFA\nRedija razões recursais completas: tempestividade, "
        "preparo, e impugnação fundamentada de cada capítulo desfavorável."
    )
