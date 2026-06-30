"""Peças geradas por template (sem IA): substabelecimento, carta de
preposição e juntada. Custo zero. Ajuste os textos ao padrão do escritório."""
from datetime import date


def substabelecimento(d: dict) -> str:
    return f"""SUBSTABELECIMENTO

Pelo presente instrumento, {d.get('advogado_substabelecente','[ADVOGADO]')}, \
OAB nº {d.get('oab_substabelecente','[OAB]')}, SUBSTABELECE, com reserva de \
iguais poderes, ao(à) advogado(a) {d.get('advogado_substabelecido','[ADVOGADO]')}, \
OAB nº {d.get('oab_substabelecido','[OAB]')}, os poderes que lhe foram \
conferidos nos autos do processo nº {d.get('numero_processo','[Nº]')}, em que \
figura como parte {d.get('reclamada','[RECLAMADA]')}.

{d.get('comarca','[Comarca]')}, {date.today().strftime('%d/%m/%Y')}.

____________________________________
{d.get('advogado_substabelecente','[ADVOGADO]')} — OAB {d.get('oab_substabelecente','[OAB]')}
"""


def carta_preposicao(d: dict) -> str:
    return f"""CARTA DE PREPOSIÇÃO

{d.get('reclamada','[RECLAMADA]')}, inscrita no CNPJ sob nº \
{d.get('cnpj','[CNPJ]')}, nomeia como seu preposto o(a) Sr.(a) \
{d.get('preposto','[PREPOSTO]')}, portador(a) do CPF nº {d.get('cpf_preposto','[CPF]')}, \
para representá-la na audiência designada nos autos do processo nº \
{d.get('numero_processo','[Nº]')}, com poderes para prestar depoimento, \
transigir e firmar acordos.

{d.get('comarca','[Comarca]')}, {date.today().strftime('%d/%m/%Y')}.

____________________________________
{d.get('reclamada','[RECLAMADA]')}
"""


def juntada(d: dict) -> str:
    return f"""PETIÇÃO DE JUNTADA

Excelentíssimo(a) Senhor(a) Juiz(a) do Trabalho da \
{d.get('vara','[VARA]')} de {d.get('comarca','[Comarca]')}.

Processo nº {d.get('numero_processo','[Nº]')}

{d.get('reclamada','[RECLAMADA]')}, já qualificada nos autos em epígrafe, vem, \
respeitosamente, à presença de Vossa Excelência, requerer a JUNTADA do \
substabelecimento e da carta de preposição em anexo, para os devidos fins.

Nestes termos, pede deferimento.

{d.get('comarca','[Comarca]')}, {date.today().strftime('%d/%m/%Y')}.
"""


def gerar_pacote(d: dict) -> dict:
    """Substab + CP + juntada de uma vez, com os dados do processo."""
    return {
        "substabelecimento": substabelecimento(d),
        "carta_preposicao": carta_preposicao(d),
        "juntada": juntada(d),
    }
