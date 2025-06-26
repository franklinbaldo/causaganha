import re
import unicodedata
import logging  # Added for validate_decision

# It's good practice for a library module to not configure logging directly.
# Instead, it should get a logger and use it. Application configures logging.
logger = logging.getLogger(__name__)


def normalize_lawyer_name(name: str) -> str:
    """
    Normalizes a lawyer's name by uppercasing, removing titles,
    normalizing accents, and cleaning up whitespace.
    """
    if not isinstance(name, str):
        return ""  # Or raise TypeError

    # 1. Convert the name to uppercase.
    text = name.upper()

    # 2. Remove common titles.
    # Using regex with word boundaries \b to avoid partial matches in names.
    # Titles like "dr.", "dra.", "dr ", "dra ", "doutor ", "doutora "
    # 2. Remove common titles. Iteratively.
    # List of titles to remove, from longest to shortest, and handling variations.
    # These will be checked at the beginning of the string.
    # Order is important: "dr. " before "dr.", "doutora " before "dra. " etc.
    # And "dra. " before "dr. " to correctly parse "dra. dra." if such a case existed.
    # Titles with trailing space (to be removed with the space)
    titles_with_space = [
        "DOUTORA ",
        "DOUTOR ",
        "DRA. ",
        "DR. ",  # With period and space
        "DRA ",
        "DR ",  # Without period but with space
    ]
    # Titles without trailing space (to be removed if they are exactly at the end or followed by non-alpha)
    # For simplicity now, this list will be for titles that might be directly followed by name characters
    # e.g. "Dra.Ana". We remove these specific prefixes.
    titles_without_space = [
        "DOUTORA",
        "DOUTOR",  # e.g. "DoutoraAna"
        "DRA.",
        "DR.",  # e.g. "Dra.Ana"
        "DRA",
        "DR",  # e.g. "DraAna"
    ]

    # Iteratively remove titles
    # This loop helps with multiple titles like "Dr. Dr. Name" or "Dra. Dr. Name"
    # and also ensures that variations are caught (e.g. "Dr.Dra. Name")
    previous_text_state = ""
    while previous_text_state != text:
        previous_text_state = text
        current_text_temp = (
            text.strip()
        )  # Work on a stripped version for prefix checking

        # First, try to remove titles that are followed by a space (more common)
        for title in titles_with_space:
            if current_text_temp.startswith(title):
                current_text_temp = current_text_temp[len(title) :].strip()

        # Then, try to remove titles that might not be followed by a space (e.g., "Dra.Ana")
        # This is more aggressive and needs care.
        if (
            current_text_temp == text.strip()
        ):  # Only proceed if no change was made by titles_with_space
            for title in titles_without_space:
                if current_text_temp.startswith(title):
                    # Check if what follows the title is not a letter, or if it's the end.
                    # This is to avoid accidentally truncating names like "Andrea" if "Dr" was removed.
                    # However, for "Dra.Ana", we want to remove "Dra.".
                    # A simple prefix removal is what the examples "Dra.Ana" -> "ana" imply.
                    current_text_temp = current_text_temp[len(title) :].strip()
                    break  # Remove one such prefix per iteration to be safe and allow re-looping for multiple.

        text = current_text_temp.strip()

    # 3. Normalize accents using unicodedata. Remove combining marks only for
    # Latin characters to avoid altering other scripts.
    decomposed = unicodedata.normalize("NFD", text)
    stripped_chars = []
    last_base = ""
    for ch in decomposed:
        if unicodedata.category(ch) == "Mn" and unicodedata.name(
            last_base, ""
        ).startswith("LATIN"):
            continue
        stripped_chars.append(ch)
        if unicodedata.category(ch)[0] != "M":
            last_base = ch
    text = "".join(stripped_chars)

    # 4. Replace multiple spaces with a single space, and strip leading/trailing whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def validate_decision(decision: dict) -> bool:
    """
    Validates a decision dictionary based on specific criteria.
    Logs the reason for invalidity if any check fails.
    """
    if not isinstance(decision, dict):
        logger.warning("Validation failed: decision is not a dictionary.")
        return False

    # 1. Check numero_processo
    numero_processo = decision.get("numero_processo")
    if not numero_processo:
        logger.warning("Validation failed: 'numero_processo' is missing or empty.")
        return False
    if not isinstance(numero_processo, str):
        logger.warning(
            f"Validation failed: 'numero_processo' is not a string (got {type(numero_processo)}). Value: {numero_processo}"
        )
        return False
    # Using flexible regex: r"[\d.-]{15,25}"
    # For stricter CNJ: r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$"
    if not re.fullmatch(r"[\d.-]{15,25}", numero_processo):
        logger.warning(
            f"Validation failed: 'numero_processo' ({numero_processo}) does not match pattern [\d.-]{{15,25}}."
        )
        return False

    # 2. Check partes - handle both old format (partes dict) and new format (polo_ativo/polo_passivo)
    partes = decision.get("partes")
    if partes and isinstance(partes, dict):
        # Old format
        requerente = partes.get("requerente")
        requerido = partes.get("requerido")
    else:
        # New format
        requerente = decision.get("polo_ativo")
        requerido = decision.get("polo_passivo")

    if not requerente:  # Checks for None or empty list/string
        logger.warning("Validation failed: 'requerente/polo_ativo' is missing or empty.")
        return False
    if not (isinstance(requerente, list) or isinstance(requerente, str)):
        logger.warning(
            f"Validation failed: 'requerente/polo_ativo' is not a list or string (got {type(requerente)})."
        )
        return False
    if isinstance(requerente, list) and not any(
        requerente
    ):  # handles list of empty strings if that's an issue
        logger.warning(
            "Validation failed: 'requerente/polo_ativo' list contains no actual content."
        )
        return False

    if not requerido:  # Checks for None or empty list/string
        logger.warning("Validation failed: 'requerido/polo_passivo' is missing or empty.")
        return False
    if not (isinstance(requerido, list) or isinstance(requerido, str)):
        logger.warning(
            f"Validation failed: 'requerido/polo_passivo' is not a list or string (got {type(requerido)})."
        )
        return False
    if isinstance(requerido, list) and not any(requerido):
        logger.warning(
            "Validation failed: 'requerido/polo_passivo' list contains no actual content."
        )
        return False

    # 3. Check resultado
    resultado = decision.get("resultado")
    if not resultado:  # Checks for None or empty string
        logger.warning("Validation failed: 'resultado' is missing or empty.")
        return False
    if not isinstance(resultado, str):
        logger.warning(
            f"Validation failed: 'resultado' is not a string (got {type(resultado)})."
        )
        return False

    logger.info(f"Decision (processo: {numero_processo}) passed validation.")
    return True


if __name__ == "__main__":
    print("--- Testing normalize_lawyer_name function ---")
    examples_normalize = [
        "Dr. João Álves da Silva",
        "DRA.    MARIA  AUXILIADORA NUNES",
        "Pedro de Alcântara Machado",
        "José das Couves (OAB/RJ 123.456)",
        "DOUTOR Carlos Alberto",
        "Dra.Ana Sem Espaço",
        "Dr.Dr. MultiTitle",
        "  Espaçado Antes e Depois  ",
        "Fábio \t ট্যাবulação Cunha",
    ]

    # Expected outputs for normalize_lawyer_name after potential logic adjustments
    # (e.g. iterative title removal, title regex not needing trailing space)
    # These reflect the new title removal logic.
    expected_normalize_outputs = [
        "JOAO ALVES DA SILVA",  # Dr. João Álves da Silva
        "MARIA AUXILIADORA NUNES",  # DRA.    MARIA  AUXILIADORA NUNES
        "PEDRO DE ALCANTARA MACHADO",  # Pedro de Alcântara Machado
        "JOSE DAS COUVES (OAB/RJ 123.456)",  # José das Couves (OAB/RJ 123.456)
        "CARLOS ALBERTO",  # DOUTOR Carlos Alberto
        "ANA SEM ESPACO",  # Dra.Ana Sem Espaço
        "MULTITITLE",  # Dr.Dr. MultiTitle
        "ESPACADO ANTES E DEPOIS",  #   Espaçado Antes e Depois
        "FABIO ট্যাবULACAO CUNHA",  # Fábio \t ট্যাবulação Cunha - Keeping non-mapped chars
    ]

    all_normalize_passed = True
    for i, example in enumerate(examples_normalize):
        normalized = normalize_lawyer_name(example)
        print(f'Original: "{example}" -> Normalized: "{normalized}"')
        if (
            i < len(expected_normalize_outputs)
            and normalized != expected_normalize_outputs[i]
        ):
            print(f'  MISMATCH! Expected: "{expected_normalize_outputs[i]}"')
            all_normalize_passed = False
    print("-" * 30)
    if all_normalize_passed:
        print("All normalize_lawyer_name examples passed or matched current logic.\n")
    else:
        print("Some normalize_lawyer_name examples had mismatches. Review needed.\n")

    print("\n--- Testing validate_decision function ---")

    valid_decision_example = {
        "numero_processo": "0001234-56.2023.8.22.0001",
        "partes": {
            "requerente": ["Fulano de Tal"],
            "requerido": "Cicrano Indústria Ltda",
        },
        "resultado": "procedente",
    }

    invalid_missing_processo = {
        # "numero_processo": "0001234-56.2023.8.22.0001",
        "partes": {
            "requerente": ["Fulano de Tal"],
            "requerido": ["Cicrano Indústria Ltda"],
        },
        "resultado": "procedente",
    }

    invalid_empty_requerente = {
        "numero_processo": "0001234-56.2023.8.22.0001",
        "partes": {
            "requerente": [],  # Empty list
            "requerido": ["Cicrano Indústria Ltda"],
        },
        "resultado": "improcedente",
    }

    invalid_requerente_list_empty_str = {
        "numero_processo": "0001234-56.2023.8.22.0001",
        "partes": {
            "requerente": [""],  # List with empty string
            "requerido": ["Cicrano Indústria Ltda"],
        },
        "resultado": "improcedente",
    }

    invalid_processo_pattern = {
        "numero_processo": "1234-56.2023.8.22.0001-EXTRA",  # Too long / wrong format
        "partes": {
            "requerente": ["Fulano de Tal"],
            "requerido": ["Cicrano Indústria Ltda"],
        },
        "resultado": "parcialmente_procedente",
    }

    invalid_partes_type = {
        "numero_processo": "0001234-56.2023.8.22.0001",
        "partes": "Não é um dicionário",
        "resultado": "extinto",
    }

    invalid_resultado_missing = {
        "numero_processo": "0001234-56.2023.8.22.0001",
        "partes": {"requerente": ["Requerente Teste"], "requerido": "Requerido Teste"},
        # "resultado": "existente"
    }

    test_decisions = {
        "valid_decision": (valid_decision_example, True),
        "invalid_missing_processo": (invalid_missing_processo, False),
        "invalid_empty_requerente": (invalid_empty_requerente, False),
        "invalid_requerente_list_empty_str": (invalid_requerente_list_empty_str, False),
        "invalid_processo_pattern": (invalid_processo_pattern, False),
        "invalid_partes_type": (invalid_partes_type, False),
        "invalid_resultado_missing": (invalid_resultado_missing, False),
    }

    for name, (decision_data, expected_validity) in test_decisions.items():
        print(f"Validating '{name}':")
        is_valid = validate_decision(decision_data)
        print(
            f"Result: {'Valid' if is_valid else 'Invalid'}. Expected: {'Valid' if expected_validity else 'Invalid'}"
        )
        assert is_valid == expected_validity, (
            f"Test '{name}' failed! Expected {expected_validity} but got {is_valid}"
        )
        print("-" * 20)

    print("\nAll validate_decision examples processed.")

    # Original __main__ content for normalize_lawyer_name (abbreviated for brevity)
    # ... (previous tests for normalize_lawyer_name could be here or refactored)
    # A more robust accent removal using unicodedata:
    name_with_complex_accents = "Jôãö da Silvâ Ñüñes"
    text_normalized_robustly = name_with_complex_accents.upper()
    text_normalized_robustly = "".join(
        c
        for c in unicodedata.normalize("NFD", text_normalized_robustly)
        if unicodedata.category(c) != "Mn"
    )
    logger_main = logging.getLogger(
        __name__ + ".main_demo"
    )  # Use a specific logger for main demo if needed
    logger_main.info(
        f"Robust accent removal demo (unicodedata): Original='{name_with_complex_accents}', Normalized='{text_normalized_robustly}'"
    )
    logger_main.info(
        f"Using current normalize_lawyer_name for '{name_with_complex_accents}': '{normalize_lawyer_name(name_with_complex_accents)}'"
    )
