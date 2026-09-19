from __future__ import annotations

from enum import Enum
from typing import Optional


class Dialect(Enum):
    """Single source of truth for all supported Spanish dialects.

    Each member carries display metadata and a linguistic description
    that is dynamically injected into AI prompts so the model actually
    understands what each dialect means.
    """

    CASTELLANO = (
        "castellano",
        "Castellano",
        "\U0001f1ea\U0001f1f8",
        ("Spain",),
        (
            "Estándar peninsular. Uso del «vosotros» y sus conjugaciones "
            "(habláis, coméis). Distinción entre /s/ y /θ/ (cero vs. sero). "
            "Uso de «tú» para trato informal. Vocabulario propio: «ordenador», "
            "«móvil», «coche», «zumo». Pretérito perfecto compuesto frecuente "
            "en contextos cotidianos («hoy he comido»). El «leísmo» es aceptado "
            "por la RAE en algunos contextos."
        ),
    )

    MEXICANO = (
        "mexicano",
        "Mexicano",
        "\U0001f1f2\U0001f1fd",
        ("Mexico",),
        (
            "Español de México. Uso predominante del «tú» para trato informal. "
            "El «usted» se usa con respeto o en contextos formales. Diminutivos "
            "muy frecuentes: «-ito/-ita». Vocabulario propio: «computadora», "
            "«celular», «carro», «jugo». Uso del «ustedes» como pronombre de "
            "plural (no «vosotros»). Pronunciación clara de la «s». Expresiones "
            "como «¡qué onda!», «¿qué pedo?», «güey». Uso frecuente de "
            "«a poco» para expresar sorpresa."
        ),
    )

    CARIBENO = (
        "caribeno",
        "Caribe\u00f1o",
        "\U0001f1e8\U0001f1fa\U0001f1f5\U0001f1f7\U0001f1e9\U0001f1f4",
        ("Cuba", "Puerto Rico", "Dominican Republic"),
        (
            "Español del Caribe (Cuba, Puerto Rico, República Dominicana). "
            "Aspiración o pérdida de la «s» al final de sílaba y palabra "
            "(«loh studenteh»). Uso frecuente del «tú» (Cuba, Rep. Dom.) o "
            "«usted» para trato cercano (Colombia Caribbean, Rep. Dom.). "
            "Vocabulario propio: «asere» (Cuba), «¡qué bolá!» (Cuba), "
            "«chévere» (Rep. Dom., Puerto Rico), «bobito» (Rep. Dom.). "
            "Reducción de consonantes finales. Contracciones y fusiones "
            "de palabras. Ritmo y entonación particulares."
        ),
    )

    RIOPLATENSE = (
        "rioplatense",
        "Rioplatense",
        "\U0001f1e6\U0001f1f7\U0001f1fa\U0001f1fe",
        ("Argentina", "Uruguay"),
        (
            "Español del Río de la Plata (Argentina y Uruguay). Uso del "
            "«voseo» con conjugaciones propias: «vos tenés», «vos sabés», "
            "«vení». Pronunciación con «yeísmo» y rehilamiento de la «ll» "
            "y «y» (suena como /ʃ/ o /ʒ/: «calle» → «cashe», «yo» → «sho»). "
            "Vocabulario propio: «laburo» (trabajo), «pibe» (chico), "
            "«bondi» (colectivo/autobús), «fiaca» (pereza). Uso del "
            "«che» como interjección. Pretérito perfecto compuesto "
            "frecuente: «hoy comí» → «hoy he comido»."
        ),
    )

    CHILENO = (
        "chileno",
        "Chileno",
        "\U0001f1e8\U0001f1f1",
        ("Chile",),
        (
            "Español de Chile. Uso del «voseo»口语 (informal, especialmente "
            "entre jóvenes): «vos querís», «vos podís». En contextos formales "
            "se usa «tú» o «usted». Pronunciación con aspiration de la «s» "
            "y «ch» debilitada. Extenso uso de diminutivos y aumentativos. "
            "Vocabulario muy propio: «cachai» (¿entendes?), «polola» (novia), "
            "«guata» (panza), «once» (merienda), «al tiro» (ahora mismo), "
            "«fome» (aburrido). Uso del «wei» (tío, persona). Expresiones "
            "como «¡weón!» con múltiples matices según contexto."
        ),
    )

    # -- constructor ----------------------------------------------------------
    def __init__(
        self,
        slug: str,
        display_name: str,
        emoji: str,
        countries: tuple[str, ...],
        description: str,
    ) -> None:
        self.slug = slug
        self.display_name = display_name
        self.emoji = emoji
        self.countries = countries
        self.description = description

    # -- lookups --------------------------------------------------------------
    @classmethod
    def from_slug(cls, slug: str) -> Dialect:
        """Look up a dialect by its URL-safe slug (case-insensitive)."""
        slug_lower = slug.strip().lower()
        for member in cls:
            if member.slug == slug_lower:
                return member
        return cls.CASTELLANO

    @classmethod
    def from_name(cls, name: str) -> Dialect:
        """Flexible lookup: tries slug, display name, then enum name.

        Falls back to CASTELLANO if nothing matches.
        """
        clean = name.strip()
        slug_lower = clean.lower()
        for member in cls:
            if (
                member.slug == slug_lower
                or member.display_name.lower() == slug_lower
                or member.name.lower() == slug_lower
            ):
                return member
        return cls.CASTELLANO

    @classmethod
    def valid_slugs(cls) -> list[str]:
        return [m.slug for m in cls]

    @classmethod
    def valid_names(cls) -> list[str]:
        return [m.display_name for m in cls]

    def prompt_text(self) -> str:
        """Return dialect name + description, formatted for AI prompts."""
        return f"{self.display_name} ({', '.join(self.countries)}):\n{self.description}"
