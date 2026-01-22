"""Build dynamic phrases using structured party data.

This module creates context-aware phrases for embedding comparison
by incorporating actual party names from structured parquet data.
"""

from causaganha.v2.analysis.parquet_party_loader import PartyInfo


class DynamicPhraseBuilder:
    """Build outcome phrases dynamically using party information."""

    def build_phrases(self, parties: PartyInfo) -> dict[str, list[str]]:
        """Build phrases for each outcome category using party data.

        Args:
            parties: Structured party information

        Returns:
            Dictionary mapping outcome (WIN/LOSS/PARTIAL) to list of phrases
        """
        phrases = {"WIN": [], "LOSS": [], "PARTIAL": []}

        # === WIN phrases ===

        # Generic first instance patterns
        phrases["WIN"].extend(
            [
                "julgo procedente",
                "procedente o pedido",
                "procedentes os pedidos",
                "julgo procedente o pedido",
                "julgo procedentes os pedidos",
                "pedido procedente",
                "pedidos procedentes",
            ]
        )

        # Party-specific WIN phrases
        if parties.autor:
            autor = parties.autor
            phrases["WIN"].extend(
                [
                    f"julgo procedente pedido {autor}",
                    f"procedente pedido {autor}",
                    f"{autor} venceu",
                    f"{autor} ganhou",
                    f"dar provimento apelação {autor}",
                    f"dar provimento recurso {autor}",
                    f"provido recurso {autor}",
                    f"provida apelação {autor}",
                    f"condenar a pagar {autor}",  # defendant ordered to pay author
                ]
            )

        # INSS-specific patterns (very common)
        if parties.is_inss_reu():
            reu = parties.reu
            phrases["WIN"].extend(
                [
                    "negar provimento apelação INSS",
                    "negar provimento recurso INSS",
                    "negado provimento apelação INSS",
                    "negado provimento recurso INSS",
                    "desprovido recurso INSS",
                    "desprovida apelação INSS",
                    "INSS perdeu",
                    f"negar provimento apelação {reu}",
                    f"negar provimento recurso {reu}",
                    f"desprovido recurso {reu}",
                    "condenar INSS",
                    "condenar o INSS",
                    f"condenar {reu}",
                ]
            )

        # Generic defendant phrases
        if parties.reu and not parties.is_inss_reu():
            reu = parties.reu
            phrases["WIN"].extend(
                [
                    f"negar provimento apelação {reu}",
                    f"negar provimento recurso {reu}",
                    f"{reu} perdeu",
                    f"condenar {reu}",
                ]
            )

        # Cross-party WIN phrases
        if parties.autor and parties.reu:
            autor, reu = parties.autor, parties.reu
            phrases["WIN"].extend(
                [
                    f"{autor} venceu {reu}",
                    f"{autor} venceu contra {reu}",
                    f"{autor} ganhou de {reu}",
                ]
            )

        # Mandado de segurança (security writ)
        phrases["WIN"].extend(
            [
                "conceder segurança",
                "deferir segurança",
                "conceder a segurança",
                "deferir a segurança",
                "mandado de segurança concedido",
                "segurança concedida",
            ]
        )

        if parties.autor:
            phrases["WIN"].append(f"conceder segurança {parties.autor}")

        # === LOSS phrases ===

        # Generic first instance patterns
        phrases["LOSS"].extend(
            [
                "julgo improcedente",
                "improcedente o pedido",
                "improcedentes os pedidos",
                "julgo improcedente o pedido",
                "julgo improcedentes os pedidos",
                "pedido improcedente",
                "pedidos improcedentes",
            ]
        )

        # Party-specific LOSS phrases
        if parties.autor:
            autor = parties.autor
            phrases["LOSS"].extend(
                [
                    f"julgo improcedente pedido {autor}",
                    f"improcedente pedido {autor}",
                    f"{autor} perdeu",
                    f"negar provimento apelação {autor}",
                    f"negar provimento recurso {autor}",
                    f"desprovido recurso {autor}",
                    f"desprovida apelação {autor}",
                ]
            )

        # INSS won patterns
        if parties.is_inss_reu():
            reu = parties.reu
            phrases["LOSS"].extend(
                [
                    "dar provimento apelação INSS",
                    "dar provimento recurso INSS",
                    "provido recurso INSS",
                    "provida apelação INSS",
                    "INSS venceu",
                    "INSS ganhou",
                    f"dar provimento apelação {reu}",
                    f"provido recurso {reu}",
                    f"{reu} venceu",
                ]
            )

        # Generic defendant won
        if parties.reu and not parties.is_inss_reu():
            reu = parties.reu
            phrases["LOSS"].extend(
                [
                    f"dar provimento apelação {reu}",
                    f"provido recurso {reu}",
                    f"{reu} venceu",
                    f"{reu} ganhou",
                ]
            )

        # Cross-party LOSS phrases
        if parties.autor and parties.reu:
            autor, reu = parties.autor, parties.reu
            phrases["LOSS"].extend(
                [
                    f"{reu} venceu {autor}",
                    f"{reu} venceu contra {autor}",
                    f"{reu} ganhou de {autor}",
                ]
            )

        # Mandado de segurança denied
        phrases["LOSS"].extend(
            [
                "denegar segurança",
                "indeferir segurança",
                "denegar a segurança",
                "indeferir a segurança",
                "mandado de segurança denegado",
                "segurança denegada",
            ]
        )

        # === PARTIAL phrases ===

        # Generic partial patterns
        phrases["PARTIAL"].extend(
            [
                "julgo parcialmente procedente",
                "parcialmente procedente o pedido",
                "parcialmente procedentes os pedidos",
                "procedente em parte",
                "procedentes em parte",
                "defiro em parte",
                "julgo parcialmente procedente o pedido",
                "julgo parcialmente procedentes os pedidos",
            ]
        )

        # Party-specific PARTIAL phrases
        if parties.autor:
            autor = parties.autor
            phrases["PARTIAL"].extend(
                [
                    f"parcialmente procedente pedido {autor}",
                    f"procedência parcial pedido {autor}",
                    f"julgo parcialmente procedente pedido {autor}",
                    f"{autor} ganhou em parte",
                    f"{autor} venceu parcialmente",
                ]
            )

        if parties.autor and parties.reu:
            autor, reu = parties.autor, parties.reu
            phrases["PARTIAL"].extend(
                [
                    f"{autor} e {reu} ganharam em parte",
                    f"resultado misto {autor} {reu}",
                ]
            )

        return phrases

    def get_phrase_count(self, parties: PartyInfo) -> dict[str, int]:
        """Get count of phrases for each outcome category.

        Useful for debugging and understanding phrase generation.

        Args:
            parties: Structured party information

        Returns:
            Dictionary mapping outcome to phrase count
        """
        phrases = self.build_phrases(parties)
        return {outcome: len(phrase_list) for outcome, phrase_list in phrases.items()}
