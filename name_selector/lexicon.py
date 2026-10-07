"""Curated spelling data the INE files cannot give us.

INE publishes names upper-cased and without accents (``LUCIA``), so the real written
form (``Lucía``) and its pronunciation must come from here. Names absent from these
tables are assumed to be written as plain title case (``JULIA`` -> ``Julia``).
"""

from typing import NamedTuple

from name_selector.models import Sex


class Spelling(NamedTuple):
    written: str
    pronunciation: str | None = None  # only when Spanish stress rules misread `written`


FEMALE_LEXICON: dict[str, Spelling] = {
    # Written with a tilde in standard Spanish.
    "AFRICA": Spelling("África"),
    "ANGELA": Spelling("Ángela"),
    "FATIMA": Spelling("Fátima"),
    "INES": Spelling("Inés"),
    "LIA": Spelling("Lía"),
    "LUCIA": Spelling("Lucía"),
    "MARIA": Spelling("María"),
    "ROCIO": Spelling("Rocío"),
    "SOFIA": Spelling("Sofía"),
    # Common outside the newborn top 100, so names typed without accents still score right.
    "ANGELES": Spelling("Ángeles"),
    "ASCENSION": Spelling("Ascensión"),
    "ASUNCION": Spelling("Asunción"),
    "BARBARA": Spelling("Bárbara"),
    "BELEN": Spelling("Belén"),
    "CONCEPCION": Spelling("Concepción"),
    "DEBORA": Spelling("Débora"),
    "ENCARNACION": Spelling("Encarnación"),
    "ESTEFANIA": Spelling("Estefanía"),
    "JOSE": Spelling("José"),  # second word of María José
    "MIRIAM": Spelling("Míriam"),
    "MONICA": Spelling("Mónica"),
    "NOEMI": Spelling("Noemí"),
    "PURIFICACION": Spelling("Purificación"),
    "ROSALIA": Spelling("Rosalía"),
    "URSULA": Spelling("Úrsula"),
    "VERONICA": Spelling("Verónica"),
    # Usually registered without a tilde, but not pronounced the way it is written.
    "MIA": Spelling("Mia", pronunciation="Mía"),
    "YASMIN": Spelling("Yasmin", pronunciation="Yasmín"),
    "CHLOE": Spelling("Chloe", pronunciation="Cloe"),
    "NOUR": Spelling("Nour", pronunciation="Nur"),
}

MALE_LEXICON: dict[str, Spelling] = {
    # Written with a tilde in standard Spanish.
    "AARON": Spelling("Aarón"),
    "ADRIAN": Spelling("Adrián"),
    "ALEX": Spelling("Álex"),
    "ALVARO": Spelling("Álvaro"),
    "ANDRES": Spelling("Andrés"),
    "ANGEL": Spelling("Ángel"),
    "DARIO": Spelling("Darío"),
    "ELIAS": Spelling("Elías"),
    "HECTOR": Spelling("Héctor"),
    "IVAN": Spelling("Iván"),
    "JESUS": Spelling("Jesús"),
    "JOSE": Spelling("José"),
    "MARTI": Spelling("Martí"),  # Catalan form, keeps its accent
    "MARTIN": Spelling("Martín"),
    "MATIAS": Spelling("Matías"),
    "MAXIMO": Spelling("Máximo"),
    "NICOLAS": Spelling("Nicolás"),
    "RAUL": Spelling("Raúl"),
    "RUBEN": Spelling("Rubén"),
    "SAUL": Spelling("Saúl"),
    "TOMAS": Spelling("Tomás"),
    "VICTOR": Spelling("Víctor"),
    # Common outside the newborn top 100, so names typed without accents still score right.
    "AGUSTIN": Spelling("Agustín"),
    "BENJAMIN": Spelling("Benjamín"),
    "CESAR": Spelling("César"),
    "CRISTOBAL": Spelling("Cristóbal"),
    "EFRAIN": Spelling("Efraín"),
    "FELIX": Spelling("Félix"),
    "FERMIN": Spelling("Fermín"),
    "GERMAN": Spelling("Germán"),
    "GINES": Spelling("Ginés"),
    "IÑIGO": Spelling("Íñigo"),
    "JOAQUIN": Spelling("Joaquín"),
    "JONAS": Spelling("Jonás"),
    "JOSUE": Spelling("Josué"),
    "JULIAN": Spelling("Julián"),
    "LAZARO": Spelling("Lázaro"),
    "MARIA": Spelling("María"),  # second word of José María
    "MOISES": Spelling("Moisés"),
    "NOE": Spelling("Noé"),
    "OSCAR": Spelling("Óscar"),
    "RAMON": Spelling("Ramón"),
    "SEBASTIAN": Spelling("Sebastián"),
    "SIMON": Spelling("Simón"),
    "VALENTIN": Spelling("Valentín"),
    # Usually registered without a tilde, but not pronounced the way it is written.
    "ADAM": Spelling("Adam", pronunciation="Ádam"),
    "ANDER": Spelling("Ander", pronunciation="Ánder"),
    "ARNAU": Spelling("Arnau", pronunciation="Arnáu"),
    "AXEL": Spelling("Axel", pronunciation="Áxel"),
    "ERIC": Spelling("Eric", pronunciation="Éric"),
    "ERIK": Spelling("Erik", pronunciation="Érik"),
    "IAN": Spelling("Ian", pronunciation="Ían"),
    "IKER": Spelling("Iker", pronunciation="Íker"),
    "LIAM": Spelling("Liam", pronunciation="Líam"),
    "NOAH": Spelling("Noah", pronunciation="Nóa"),
    "OLIVER": Spelling("Oliver", pronunciation="Óliver"),
    "THIAGO": Spelling("Thiago", pronunciation="Tiago"),
    "UNAI": Spelling("Unai", pronunciation="Unái"),
}

LEXICONS: dict[Sex, dict[str, Spelling]] = {Sex.FEMALE: FEMALE_LEXICON, Sex.MALE: MALE_LEXICON}


def spelling_for(key: str, sex: Sex = Sex.FEMALE) -> Spelling:
    spelling = LEXICONS[sex].get(key) or Spelling(key.title())
    return Spelling(spelling.written, spelling.pronunciation or spelling.written)
