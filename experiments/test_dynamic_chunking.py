"""Test dynamic chunking with different embedding providers.

This script demonstrates how the chunking system adapts to different
provider token limits:
- Jina v4: 32,000 tokens (allows very large chunks)
- Jina v3: 8,192 tokens (moderate chunks)
- Google Gemini: 2,048 tokens (small chunks, requires more splitting)
"""

import asyncio
import os

from causaganha.analysis.embedding_service import EmbeddingService
from causaganha.analysis.text_chunker import create_chunker_for_provider


# Sample long legal decision text (simulated)
SAMPLE_LEGAL_TEXT = (
    """
ACÓRDÃO

RELATÓRIO

O Excelentíssimo Senhor Desembargador Relator João da Silva proferiu o seguinte relatório:

Trata-se de apelação cível interposta por EMPRESA XYZ LTDA contra sentença que julgou procedente o pedido de indenização por danos morais e materiais formulado pelo autor JOSÉ DOS SANTOS.

A sentença de primeiro grau condenou a empresa ao pagamento de R$ 50.000,00 a título de danos morais e R$ 15.000,00 a título de danos materiais, além de custas processuais e honorários advocatícios fixados em 20% sobre o valor da condenação.

A apelante alega, em síntese:
1. Cerceamento de defesa por não ter sido oportunizada a produção de prova pericial;
2. Inexistência de nexo de causalidade entre a conduta da empresa e os danos alegados;
3. Excessividade dos valores fixados a título de indenização;
4. Inaplicabilidade do Código de Defesa do Consumidor ao caso concreto.

Requer o provimento do recurso para:
a) Anular a sentença e determinar a produção de prova pericial;
b) Subsidiariamente, julgar improcedente o pedido inicial;
c) Mais subsidiariamente, reduzir substancialmente os valores da condenação.

O apelado apresentou contrarrazões pugnando pela manutenção integral da sentença recorrida.

O Ministério Público manifestou-se pelo não conhecimento do recurso quanto ao primeiro pedido e, no mérito, pelo seu desprovimento.

É o relatório.

FUNDAMENTAÇÃO

VOTO DO RELATOR

Desembargador João da Silva (Relator):

1. DO CONHECIMENTO DO RECURSO

Preenchidos os requisitos de admissibilidade, conheço do recurso.

2. DO MÉRITO

2.1. Do cerceamento de defesa

Não prospera a alegação de cerceamento de defesa. O magistrado de primeiro grau fundamentou adequadamente a desnecessidade da perícia técnica requerida pela apelante, tendo em vista que a materialidade dos fatos já estava suficientemente comprovada pela prova documental e testemunhal produzida nos autos.

Com efeito, a jurisprudência pacífica do Superior Tribunal de Justiça estabelece que o juiz é o destinatário das provas, cabendo a ele determinar quais são necessárias ao deslinde da controvérsia. Nesse sentido, o indeferimento de prova desnecessária ou protelatória não configura cerceamento de defesa.

Precedentes: STJ, REsp 1.234.567/SP, Rel. Min. Fulano de Tal, DJe 15/03/2023; TJSP, Apelação 9876543-21.2022.8.26.0100, Rel. Des. Beltrano, j. 20/04/2023.

Assim, rejeito a preliminar de cerceamento de defesa.

2.2. Do nexo de causalidade

A sentença recorrida analisou de forma adequada e completa o nexo de causalidade entre a conduta da empresa apelante e os danos sofridos pelo apelado.

Conforme restou demonstrado nos autos, a empresa deixou de prestar o serviço contratado de forma adequada, causando transtornos e prejuízos significativos ao consumidor. As testemunhas ouvidas em juízo confirmaram que o autor ficou sem o serviço contratado por período superior a 60 (sessenta) dias, mesmo após diversas reclamações e tentativas de resolução amigável.

A responsabilidade civil da fornecedora de serviços é objetiva, nos termos do artigo 14 do Código de Defesa do Consumidor, bastando a comprovação do dano e do nexo causal. No caso em análise, ambos os elementos restaram sobejamente demonstrados.

Portanto, mantenho o reconhecimento do nexo de causalidade.

2.3. Dos valores da indenização

Quanto aos valores fixados a título de indenização, entendo que merecem redução, porém não na proporção pretendida pela apelante.

No que tange aos danos morais, o valor de R$ 50.000,00 mostra-se excessivo diante das circunstâncias do caso concreto. Considerando:
- A gravidade da conduta da empresa (média);
- A extensão do dano sofrido pelo consumidor (moderada);
- A capacidade econômica das partes;
- O caráter pedagógico da indenização;

Entendo razoável e proporcional a redução do valor dos danos morais para R$ 30.000,00 (trinta mil reais).

Já os danos materiais no valor de R$ 15.000,00 estão adequadamente comprovados e fundamentados, não merecendo qualquer alteração.

2.4. Da aplicabilidade do CDC

A relação entre as partes é claramente de consumo, enquadrando-se perfeitamente nos conceitos de fornecedor e consumidor previstos nos artigos 2º e 3º do Código de Defesa do Consumidor. A tese da inaplicabilidade do CDC não merece acolhida.

3. CONCLUSÃO

Ante o exposto, DOU PARCIAL PROVIMENTO ao recurso, apenas para reduzir o valor da indenização por danos morais de R$ 50.000,00 para R$ 30.000,00, mantendo inalterados os demais termos da sentença recorrida.

É como voto.

VOTO DO 2º JUIZ

Desembargadora Maria Fernandes (2ª Juíza):

Acompanho integralmente o voto do Eminente Relator, pelos mesmos fundamentos.

VOTO DO 3º JUIZ

Desembargador Pedro Oliveira (3º Juiz):

Com a devida vênia, divirjo parcialmente do voto do Relator.

Entendo que os valores arbitrados na sentença de primeiro grau estão adequados às peculiaridades do caso concreto. A empresa ré demonstrou completo descaso com os direitos do consumidor, ignorando reiteradas reclamações e mantendo o autor sem o serviço essencial por mais de dois meses.

Nesse contexto, o valor de R$ 50.000,00 a título de danos morais não se mostra excessivo, mas sim necessário ao cumprimento das funções compensatória e pedagógica da reparação civil.

Dessa forma, voto pelo DESPROVIMENTO INTEGRAL do recurso.

DECISÃO

Por maioria de votos, a Turma Julgadora decidiu DAR PARCIAL PROVIMENTO ao recurso de apelação, nos termos do voto do Relator, vencido o 3º Juiz que votou pelo desprovimento integral.

Participaram do julgamento os Excelentíssimos Senhores Desembargadores João da Silva (Relator e Presidente), Maria Fernandes (2ª Juíza) e Pedro Oliveira (3º Juiz - vencido).

São Paulo, 15 de junho de 2025.

DESEMBARGADOR JOÃO DA SILVA
Relator
"""
    * 3
)  # Multiply by 3 to create a longer document


async def test_dynamic_chunking() -> None:
    """Test dynamic chunking with different providers."""
    # Test configuration
    test_text = SAMPLE_LEGAL_TEXT
    text_length = len(test_text)
    text_length // 4  # Rough estimate: 1 token ≈ 4 chars

    # Test 1: Jina v4 (32K tokens)

    try:
        jina_v4_service = EmbeddingService(
            provider="jina",
            model="jina-embeddings-v4",
            dimension=1024,
        )

        # Show provider token limit
        chunker_v4 = create_chunker_for_provider(jina_v4_service.provider)

        # Chunk using semantic sections (auto strategy)
        chunks_v4_auto = chunker_v4.chunk_text(test_text, strategy="auto")
        for _i, _chunk in enumerate(chunks_v4_auto, 1):
            pass

        # Chunk using sliding window
        chunks_v4_window = chunker_v4.chunk_text(test_text, strategy="sliding_window")
        for _i, _chunk in enumerate(chunks_v4_window, 1):
            pass

    except Exception:
        pass

    # Test 2: Jina v3 (8K tokens)

    try:
        jina_v3_service = EmbeddingService(
            provider="jina",
            model="jina-embeddings-v3",
            dimension=1024,
        )

        chunker_v3 = create_chunker_for_provider(jina_v3_service.provider)

        chunks_v3 = chunker_v3.chunk_text(test_text, strategy="auto")
        for _i, _chunk in enumerate(chunks_v3, 1):
            pass

    except Exception:
        pass

    # Test 3: Google Gemini (2K tokens)

    if os.getenv("GOOGLE_API_KEY"):
        try:
            google_service = EmbeddingService(
                provider="google",
                model="gemini-embedding-001",
                dimension=768,
            )

            chunker_google = create_chunker_for_provider(google_service.provider)

            chunks_google = chunker_google.chunk_text(test_text, strategy="auto")
            for _i, _chunk in enumerate(chunks_google, 1):
                pass

        except Exception:
            pass
    else:
        pass

    # Summary comparison


if __name__ == "__main__":
    asyncio.run(test_dynamic_chunking())
