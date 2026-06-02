#!/usr/bin/env python3
"""Génère un fichier Excel template avec quelques BDs belges d'exemple."""
import sys

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
except ImportError:
    sys.exit("pip install openpyxl")

HEADERS = [
    "serie",
    "type",
    "editeur",
    "genre",
    "tome",
    "titre",
    "isbn",
    "date_parution",
    "nb_pages",
    "scenariste",
    "dessinateur",
    "coloriste",
    "synopsis",
    "dans_collection",
    "publier_sur_web",
]

DEMO_DATA = [
    # Tintin
    (
        "Les Aventures de Tintin",
        "bd",
        "Casterman",
        "Aventure",
        1,
        "Tintin au pays des Soviets",
        "9782203001015",
        "1999-09-01",
        142,
        "Hergé",
        "Hergé",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Les Aventures de Tintin",
        "bd",
        "Casterman",
        "Aventure",
        2,
        "Tintin au Congo",
        "9782203001022",
        "1999-09-01",
        62,
        "Hergé",
        "Hergé",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Les Aventures de Tintin",
        "bd",
        "Casterman",
        "Aventure",
        7,
        "L'Île Noire",
        "9782203001077",
        "1999-09-01",
        62,
        "Hergé",
        "Hergé",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Les Aventures de Tintin",
        "bd",
        "Casterman",
        "Aventure",
        12,
        "Le Trésor de Rackham le Rouge",
        "9782203001121",
        "1999-09-01",
        62,
        "Hergé",
        "Hergé",
        "",
        "",
        "oui",
        "oui",
    ),
    # Astérix
    (
        "Astérix",
        "bd",
        "Hachette",
        "Humour",
        1,
        "Astérix le Gaulois",
        "9782012101357",
        "1999-01-01",
        48,
        "René Goscinny",
        "Albert Uderzo",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Astérix",
        "bd",
        "Hachette",
        "Humour",
        2,
        "La Serpe d'or",
        "9782012101364",
        "1999-01-01",
        48,
        "René Goscinny",
        "Albert Uderzo",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Astérix",
        "bd",
        "Hachette",
        "Humour",
        10,
        "Astérix légionnaire",
        "9782012101456",
        "1999-01-01",
        48,
        "René Goscinny",
        "Albert Uderzo",
        "",
        "",
        "non",
        "oui",
    ),
    # Thorgal
    (
        "Thorgal",
        "bd",
        "Le Lombard",
        "Fantastique",
        1,
        "La Magicienne trahie",
        "9782803611034",
        "1980-01-01",
        46,
        "Jean Van Hamme",
        "Grzegorz Rosiński",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Thorgal",
        "bd",
        "Le Lombard",
        "Fantastique",
        2,
        "L'Île des mers gelées",
        "9782803611041",
        "1981-01-01",
        46,
        "Jean Van Hamme",
        "Grzegorz Rosiński",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Thorgal",
        "bd",
        "Le Lombard",
        "Fantastique",
        3,
        "Les Trois Vieillards du pays d'Aran",
        "9782803611058",
        "1981-01-01",
        46,
        "Jean Van Hamme",
        "Grzegorz Rosiński",
        "",
        "",
        "non",
        "oui",
    ),
    # Lucky Luke
    (
        "Lucky Luke",
        "bd",
        "Lucky Comics",
        "Western",
        1,
        "La Mine d'or de Dick Digger",
        "9782884711241",
        "2000-01-01",
        44,
        "Morris",
        "Morris",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Lucky Luke",
        "bd",
        "Lucky Comics",
        "Western",
        7,
        "Hors-la-loi",
        "9782884711302",
        "2000-01-01",
        44,
        "René Goscinny",
        "Morris",
        "",
        "",
        "oui",
        "oui",
    ),
    # Largo Winch
    (
        "Largo Winch",
        "bd",
        "Dupuis",
        "Thriller",
        1,
        "L'Héritier",
        "9782800124063",
        "1992-01-01",
        48,
        "Jean Van Hamme",
        "Philippe Francq",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Largo Winch",
        "bd",
        "Dupuis",
        "Thriller",
        2,
        "Le Groupe W",
        "9782800124070",
        "1993-01-01",
        48,
        "Jean Van Hamme",
        "Philippe Francq",
        "",
        "",
        "oui",
        "oui",
    ),
    # Blacksad
    (
        "Blacksad",
        "bd",
        "Dargaud",
        "Polar",
        1,
        "Quelque part entre les ombres",
        "9782205051964",
        "2000-11-01",
        56,
        "Juan Díaz Canales",
        "Juanjo Guarnido",
        "",
        "",
        "oui",
        "oui",
    ),
    (
        "Blacksad",
        "bd",
        "Dargaud",
        "Polar",
        2,
        "Arctic-Nation",
        "9782205054965",
        "2003-01-01",
        56,
        "Juan Díaz Canales",
        "Juanjo Guarnido",
        "",
        "",
        "oui",
        "oui",
    ),
]


def create_template(outfile="tools/demo_template.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Albums"

    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, row in enumerate(DEMO_DATA, 2):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Largeurs colonnes
    widths = [22, 8, 14, 12, 5, 28, 16, 13, 8, 20, 20, 15, 30, 10, 12]
    for col_idx, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    ws.freeze_panes = "A2"
    wb.save(outfile)
    print(f"✅  Template créé : {outfile}  ({len(DEMO_DATA)} albums d'exemple)")


if __name__ == "__main__":
    create_template()
