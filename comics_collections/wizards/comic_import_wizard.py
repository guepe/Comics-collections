import base64
import csv
import re
from datetime import date, datetime, timedelta, timezone
from io import BytesIO, StringIO
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from odoo import fields, models
from odoo.exceptions import UserError


class ComicImportWizard(models.TransientModel):
    _name = 'comic.import.wizard'
    _description = "Assistant d'import de bandes dessinées"

    state = fields.Selection(
        selection=[
            ('draft', 'Upload'),
            ('mapping', 'Mapping'),
            ('preview', 'Prévisualisation'),
            ('done', 'Terminé'),
        ],
        default='draft',
        required=True,
    )
    template_format = fields.Selection(
        selection=[
            ('xlsx', 'XLSX'),
            ('csv', 'CSV'),
        ],
        string='Format du modèle',
        default='xlsx',
        required=True,
    )
    template_file = fields.Binary(string='Fichier généré', readonly=True, attachment=False)
    template_filename = fields.Char(string='Nom du fichier', readonly=True)
    import_file = fields.Binary(string='Fichier à importer', attachment=False)
    import_filename = fields.Char(string='Nom du fichier')
    import_policy = fields.Selection(
        selection=[
            ('update', 'Mettre à jour si ISBN existant'),
            ('create', 'Toujours créer'),
        ],
        string="Politique d'import",
        default='update',
        required=True,
    )
    preview_html = fields.Html(string='Prévisualisation', readonly=True)
    result_html = fields.Html(string='Rapport', readonly=True)
    error_report_file = fields.Binary(string="Rapport d'erreurs", readonly=True, attachment=False)
    error_report_filename = fields.Char(string="Nom du rapport d'erreurs", readonly=True)
    mapping_line_ids = fields.One2many(
        'comic.import.mapping.line',
        'wizard_id',
        string='Mapping des colonnes',
    )

    def action_download_template(self):
        self.ensure_one()
        if self.template_format == 'csv':
            content = self._build_csv_template()
            filename = 'modele_import_albums_bd.csv'
        else:
            content = self._build_xlsx_template()
            filename = 'modele_import_albums_bd.xlsx'

        self.write({
            'template_file': base64.b64encode(content),
            'template_filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': (
                '/web/content/?model=%s&id=%s&field=template_file'
                '&filename_field=template_filename&download=true'
            ) % (self._name, self.id),
            'target': 'self',
        }

    def action_prepare_mapping(self):
        self.ensure_one()
        rows = self._get_source_rows()
        if not rows:
            raise UserError("Le fichier ne contient aucune ligne.")

        headers = rows[0]
        sample_row = rows[1] if len(rows) > 1 else []
        commands = [(5, 0, 0)]
        for index, header in enumerate(headers):
            column_name = str(header or '').strip() or "Colonne %s" % (index + 1)
            sample_value = sample_row[index] if index < len(sample_row) else ''
            commands.append((0, 0, {
                'sequence': index + 1,
                'column_name': column_name,
                'sample_value': sample_value,
                'target_field': self._guess_target_field(column_name),
            }))

        self.write({
            'state': 'mapping',
            'mapping_line_ids': commands,
            'preview_html': False,
            'result_html': False,
            'error_report_file': False,
            'error_report_filename': False,
        })
        return self._action_reopen()

    def action_preview_import(self):
        self.ensure_one()
        rows = self._get_import_rows()
        preview_rows = rows[:10]
        self.write({
            'state': 'preview',
            'preview_html': self._build_preview_html(preview_rows, len(rows)),
            'result_html': False,
        })
        return self._action_reopen()

    def action_import(self):
        self.ensure_one()
        rows = self._get_import_rows()
        stats = {
            'created': 0,
            'updated': 0,
            'errors': [],
        }
        for index, row in enumerate(rows, start=2):
            try:
                result = self._import_row(row)
            except Exception as exc:
                stats['errors'].append({
                    'line': index,
                    'error': str(exc),
                    'row': row,
                })
                continue
            stats[result] += 1

        report = self._build_error_report_csv(stats['errors'])
        self.write({
            'state': 'done',
            'result_html': self._build_result_html(stats),
            'error_report_file': base64.b64encode(report) if report else False,
            'error_report_filename': 'rapport_erreurs_import_bd.csv' if report else False,
        })
        return self._action_reopen()

    def action_back_to_mapping(self):
        self.ensure_one()
        self.write({
            'state': 'mapping',
            'preview_html': False,
            'result_html': False,
            'error_report_file': False,
            'error_report_filename': False,
        })
        return self._action_reopen()

    def action_reset(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'mapping_line_ids': [(5, 0, 0)],
            'preview_html': False,
            'result_html': False,
            'error_report_file': False,
            'error_report_filename': False,
        })
        return self._action_reopen()

    def action_download_error_report(self):
        self.ensure_one()
        if not self.error_report_file:
            raise UserError("Aucun rapport d'erreurs n'est disponible.")
        return {
            'type': 'ir.actions.act_url',
            'url': (
                '/web/content/?model=%s&id=%s&field=error_report_file'
                '&filename_field=error_report_filename&download=true'
            ) % (self._name, self.id),
            'target': 'self',
        }

    def _action_reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Import CSV/Excel",
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_import_rows(self):
        self.ensure_one()
        rows = self._get_source_rows()
        if self.mapping_line_ids:
            return self._normalise_mapped_rows(rows)
        return self._normalise_import_rows(rows)

    def _get_source_rows(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError("Veuillez sélectionner un fichier à importer.")
        filename = (self.import_filename or '').lower()
        content = base64.b64decode(self.import_file)
        if filename.endswith('.xlsx'):
            return self._read_xlsx_rows(content)
        if filename.endswith('.xls'):
            return self._read_xls_rows(content)
        if filename.endswith('.csv') or not filename:
            return self._read_csv_rows(content)
        raise UserError("Formats acceptés : CSV, XLS ou XLSX.")

    def _normalise_mapped_rows(self, rows):
        if not rows:
            raise UserError("Le fichier ne contient aucune ligne.")

        mapped_columns = [
            (line.sequence - 1, line.target_field)
            for line in self.mapping_line_ids.sorted('sequence')
            if line.target_field
        ]
        if not mapped_columns:
            raise UserError("Veuillez mapper au moins une colonne.")

        normalised = []
        for row in rows[1:]:
            values = {}
            for index, target_field in mapped_columns:
                value = row[index] if index < len(row) else ''
                if not value:
                    continue
                if target_field == 'compact_content':
                    values.update(self._parse_collection_content(value))
                    continue
                if values.get(target_field):
                    values[target_field] = "%s\n%s" % (values[target_field], value)
                else:
                    values[target_field] = value
            if any(values.values()):
                normalised.append(values)

        if not normalised:
            raise UserError("Aucune ligne exploitable n'a été trouvée dans le fichier.")
        return normalised

    @classmethod
    def _normalise_import_rows(cls, rows):
        if not rows:
            raise UserError("Le fichier ne contient aucune ligne.")

        headers = [cls._normalise_header(value) for value in rows[0]]
        data_rows = rows[1:]
        if headers[:2] == ['n', 'contenu']:
            normalised = [
                cls._parse_collection_content(row[1] if len(row) > 1 else '')
                for row in data_rows
                if len(row) > 1 and row[1]
            ]
        else:
            normalised = []
            for row in data_rows:
                values = {}
                for index, header in enumerate(headers):
                    if header:
                        values[header] = row[index] if index < len(row) else ''
                if any(values.values()):
                    normalised.append(values)

        if not normalised:
            raise UserError("Aucune ligne exploitable n'a été trouvée dans le fichier.")
        return normalised

    @classmethod
    def _normalise_header(cls, value):
        value = str(value or '').strip().lower()
        value = value.replace('°', '').replace(' ', '_').replace('-', '_')
        aliases = {
            'serie': 'serie_name',
            'série': 'serie_name',
            'titre': 'titre_album',
            'titre_de_l_album': 'titre_album',
            'contenu': 'contenu',
        }
        return aliases.get(value, value)

    @classmethod
    def _guess_target_field(cls, column_name):
        header = cls._normalise_header(column_name)
        if header == 'contenu':
            return 'compact_content'
        available_fields = {column['name'] for column in cls._template_columns()}
        return header if header in available_fields else False

    @classmethod
    def _parse_collection_content(cls, content):
        content = str(content or '').strip()
        match = re.search(r'\b(0[1-9]|1[0-2])/\d{4}\b', content)
        if match:
            left = content[:match.start()].strip()
            date_parution = cls._parse_date(match.group(0))
            right = content[match.end():].strip()
        else:
            left = content
            date_parution = ''
            right = ''

        purchase_match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', right)
        editeur = right[:purchase_match.start()].strip() if purchase_match else right.strip()
        serie_name, tome, titre_album = cls._split_series_title(left)
        return {
            'serie_name': serie_name,
            'tome': tome,
            'titre_album': titre_album,
            'date_parution': date_parution,
            'editeur': editeur,
            'etat_lecture': 'non_lu',
        }

    @staticmethod
    def _split_series_title(value):
        value = value.strip()
        match = re.match(r'^(?P<serie>.+?)\s+-(?P<tome>[^-]+)-\s+(?P<title>.+)$', value)
        if match:
            tome_match = re.search(r'\d+', match.group('tome'))
            return (
                match.group('serie').strip(),
                tome_match.group(0) if tome_match else '',
                match.group('title').strip(),
            )

        if ' - ' in value:
            serie, title = value.split(' - ', 1)
            return serie.strip(), '', title.strip()
        return value, '', value

    @classmethod
    def _read_csv_rows(cls, content):
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('cp1252')
        sample = text[:2048]
        delimiter = ';' if sample.count(';') >= sample.count(',') else ','
        reader = csv.reader(StringIO(text), delimiter=delimiter)
        return [[cell.strip() for cell in row] for row in reader]

    @classmethod
    def _read_xlsx_rows(cls, content):
        with ZipFile(BytesIO(content)) as workbook:
            shared_strings = cls._xlsx_shared_strings(workbook)
            date_style_ids = cls._xlsx_date_style_ids(workbook)
            date_1904 = cls._xlsx_uses_1904_dates(workbook)
            sheet_path = cls._xlsx_first_sheet_path(workbook)
            root = ET.fromstring(workbook.read(sheet_path))
        namespace = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        rows = []
        for row in root.findall('.//main:sheetData/main:row', namespace):
            values = []
            for cell in row.findall('main:c', namespace):
                column_index = cls._xlsx_column_index(cell.attrib.get('r', 'A1'))
                while len(values) < column_index - 1:
                    values.append('')
                values.append(
                    cls._xlsx_cell_value(
                        cell,
                        shared_strings,
                        date_style_ids,
                        date_1904,
                    )
                )
            rows.append(values)
        return rows

    @staticmethod
    def _read_xls_rows(content):
        try:
            import xlrd
        except ImportError as exc:
            raise UserError(
                "L'import XLS nécessite la bibliothèque Python xlrd. "
                "Convertissez le fichier en XLSX ou installez xlrd côté serveur."
            ) from exc

        workbook = xlrd.open_workbook(file_contents=content)
        sheet = workbook.sheet_by_index(0)
        rows = []
        for row_index in range(sheet.nrows):
            values = []
            for column_index in range(sheet.ncols):
                cell = sheet.cell(row_index, column_index)
                value = cell.value
                if cell.ctype == xlrd.XL_CELL_DATE:
                    date_value = xlrd.xldate_as_datetime(value, workbook.datemode).date()
                    values.append(date_value.isoformat())
                elif cell.ctype == xlrd.XL_CELL_NUMBER and float(value).is_integer():
                    values.append(str(int(value)))
                else:
                    values.append(str(value or '').strip())
            rows.append(values)
        return rows

    @staticmethod
    def _xlsx_shared_strings(workbook):
        if 'xl/sharedStrings.xml' not in workbook.namelist():
            return []
        namespace = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        root = ET.fromstring(workbook.read('xl/sharedStrings.xml'))
        strings = []
        for item in root.findall('main:si', namespace):
            strings.append(
                ''.join(
                    text.text or ''
                    for text in item.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                )
            )
        return strings

    @staticmethod
    def _xlsx_uses_1904_dates(workbook):
        if 'xl/workbook.xml' not in workbook.namelist():
            return False
        namespace = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        root = ET.fromstring(workbook.read('xl/workbook.xml'))
        workbook_properties = root.find('main:workbookPr', namespace)
        return (
            workbook_properties is not None
            and workbook_properties.attrib.get('date1904') in ('1', 'true', 'True')
        )

    @classmethod
    def _xlsx_date_style_ids(cls, workbook):
        if 'xl/styles.xml' not in workbook.namelist():
            return set()

        namespace = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        root = ET.fromstring(workbook.read('xl/styles.xml'))
        custom_date_formats = set()
        for number_format in root.findall('main:numFmts/main:numFmt', namespace):
            number_format_id = int(number_format.attrib.get('numFmtId', '0'))
            format_code = number_format.attrib.get('formatCode', '')
            if cls._is_xlsx_date_format(format_code):
                custom_date_formats.add(number_format_id)

        date_style_ids = set()
        cell_formats = root.find('main:cellXfs', namespace)
        if cell_formats is None:
            return date_style_ids

        for style_index, cell_format in enumerate(cell_formats.findall('main:xf', namespace)):
            number_format_id = int(cell_format.attrib.get('numFmtId', '0'))
            if number_format_id in cls._xlsx_builtin_date_format_ids() or number_format_id in custom_date_formats:
                date_style_ids.add(style_index)
        return date_style_ids

    @staticmethod
    def _is_xlsx_date_format(format_code):
        format_code = re.sub(r'".*?"', '', format_code.lower())
        format_code = re.sub(r'\[.*?\]', '', format_code)
        return bool(re.search(r'(^|[^a-z])[dmyh]([^a-z]|$)', format_code))

    @staticmethod
    def _xlsx_builtin_date_format_ids():
        return {
            14, 15, 16, 17, 18, 19, 20, 21, 22,
            27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
            45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58,
        }

    @classmethod
    def _xlsx_first_sheet_path(cls, workbook):
        rel_namespace = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
        rels = ET.fromstring(workbook.read('xl/_rels/workbook.xml.rels'))
        for rel in rels.findall('rel:Relationship', rel_namespace):
            target = rel.attrib.get('Target', '')
            if 'worksheets/' in target:
                return target.lstrip('/') if target.startswith('/xl/') else 'xl/' + target
        raise UserError("Aucune feuille XLSX exploitable n'a été trouvée.")

    @staticmethod
    def _xlsx_column_index(reference):
        letters = ''.join(char for char in reference if char.isalpha())
        index = 0
        for char in letters:
            index = index * 26 + ord(char.upper()) - 64
        return index or 1

    @staticmethod
    def _xlsx_cell_value(cell, shared_strings, date_style_ids=None, date_1904=False):
        namespace = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        cell_type = cell.attrib.get('t')
        value = cell.find('main:v', namespace)
        if cell_type == 's' and value is not None:
            return shared_strings[int(value.text or 0)]
        if cell_type == 'inlineStr':
            inline = cell.find('main:is', namespace)
            if inline is None:
                return ''
            return ''.join(
                text.text or ''
                for text in inline.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
            )
        style_id = int(cell.attrib.get('s', '0'))
        if value is not None and style_id in (date_style_ids or set()):
            return ComicImportWizard._excel_serial_date(value.text, date_1904)
        return (value.text or '').strip() if value is not None else ''

    @staticmethod
    def _excel_serial_date(value, date_1904=False):
        try:
            serial = float(value)
        except (TypeError, ValueError):
            return ''
        if date_1904:
            return (date(1904, 1, 1) + timedelta(days=int(serial))).isoformat()
        return (date(1899, 12, 30) + timedelta(days=int(serial))).isoformat()

    def _import_row(self, row):
        title = (row.get('titre_album') or row.get('name') or '').strip()
        serie_name = (row.get('serie_name') or '').strip()
        if not title and not serie_name:
            raise UserError("le titre ou la série est obligatoire")
        if not title:
            title = serie_name

        isbn = self._clean_isbn(row.get('isbn'))
        values = self._album_values(row, title, serie_name)
        album = self.env['comic.album']
        existing = album.browse()
        if self.import_policy == 'update' and isbn:
            existing = album.search(
                ['|', ('isbn', '=', isbn), ('isbn', '=', row.get('isbn', '').strip())],
                limit=1
            )
        if existing:
            existing.write(values)
            return 'updated'
        album.create(values)
        return 'created'

    def _album_values(self, row, title, serie_name):
        isbn = self._clean_isbn(row.get('isbn'))
        values = {
            'name': title,
            'isbn': isbn,
            'tome': self._parse_integer(row.get('tome')),
            'date_parution': self._parse_date(row.get('date_parution')),
            'nb_pages': self._parse_integer(row.get('nb_pages')),
            'etat_lecture': self._parse_reading_state(row.get('etat_lecture')),
            'note': self._parse_float(row.get('note')),
            'dans_collection': True,
            'url_club_be': self._clean_text(row.get('url_club_be')),
            'url_amazon_be': self._clean_text(row.get('url_amazon_be')),
        }
        if serie_name:
            values['serie_id'] = self._get_or_create_serie(serie_name, row).id
        author_commands = self._author_commands(row)
        if author_commands:
            values['auteur_line_ids'] = author_commands
        return values

    def _get_or_create_serie(self, serie_name, row):
        serie = self.env['comic.serie'].search([('name', '=', serie_name)], limit=1)
        if serie:
            return serie
        values = {
            'name': serie_name,
        }
        genre_name = self._clean_text(row.get('genre'))
        if genre_name:
            genre = self._get_or_create_by_name('comic.genre', genre_name)
            values['genre_id'] = genre.id
        editeur_name = self._clean_text(row.get('editeur'))
        if editeur_name:
            editeur = self._get_or_create_by_name('comic.editeur', editeur_name)
            values['editeur_id'] = editeur.id
        return self.env['comic.serie'].create(values)

    def _author_commands(self, row):
        commands = [(5, 0, 0)]
        for column, role in [
            ('scenariste', 'scenariste'),
            ('dessinateur', 'dessinateur'),
            ('coloriste', 'coloriste'),
        ]:
            names = self._split_names(row.get(column))
            for name in names:
                partner = self._get_or_create_by_name('res.partner', name)
                commands.append((0, 0, {
                    'partner_id': partner.id,
                    'role': role,
                }))
        return commands if len(commands) > 1 else []

    def _get_or_create_by_name(self, model_name, name):
        record = self.env[model_name].search([('name', '=', name)], limit=1)
        if record:
            return record
        return self.env[model_name].create({'name': name})

    @staticmethod
    def _normalize_author_name(name):
        """Transforme "Nom, Prénom" en "Prénom Nom". Laisse les autres formes intactes."""
        if ',' in name:
            parts = name.split(',', 1)
            last = parts[0].strip()
            first = parts[1].strip()
            if first:
                return '%s %s' % (first, last)
        return name

    @staticmethod
    def _split_names(value):
        return [
            ComicImportWizard._normalize_author_name(name.strip())
            for name in re.split(r'[;\n|]+', str(value or ''))
            if name.strip()
        ]

    @staticmethod
    def _clean_text(value):
        return str(value or '').strip()

    @staticmethod
    def _clean_isbn(value):
        """
        Normalise un ISBN : supprime tirets/espaces et convertit ISBN-10 → EAN-13.
        Retourne une chaîne de 13 chiffres ou False.
        """
        import re as _re
        raw = _re.sub(r'[\-\s]', '', str(value or '').strip())
        if not raw:
            return False
        if len(raw) == 13 and raw.isdigit():
            return raw
        if len(raw) == 10:
            # Conversion ISBN-10 → EAN-13 : préfixe 978 + recalcul du chiffre de contrôle
            digits9 = raw[:9]
            if not digits9.isdigit():
                return raw  # laisse passer, la validation le signalera
            base = '978' + digits9
            total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
            check = (10 - total % 10) % 10
            return base + str(check)
        return raw or False

    @staticmethod
    def _parse_integer(value):
        value = str(value or '').strip()
        match = re.search(r'\d+', value)
        return int(match.group(0)) if match else 0

    @staticmethod
    def _parse_float(value):
        value = str(value or '').strip().replace(',', '.')
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_reading_state(value):
        value = str(value or '').strip().lower()
        value = value.replace(' ', '_').replace('-', '_')
        aliases = {
            '': 'non_lu',
            'non_lu': 'non_lu',
            'non_lu(e)': 'non_lu',
            'nonlu': 'non_lu',
            'a_lire': 'non_lu',
            'à_lire': 'non_lu',
            'en_cours': 'en_cours',
            'en_cours_de_lecture': 'en_cours',
            'lu': 'lu',
            'lue': 'lu',
        }
        return aliases.get(value, 'non_lu')

    @staticmethod
    def _parse_date(value):
        value = str(value or '').strip()
        for date_format in ['%Y-%m-%d', '%d/%m/%Y']:
            try:
                return datetime.strptime(value, date_format).date().isoformat()
            except ValueError:
                pass
        try:
            return datetime.strptime(value, '%m/%Y').date().replace(day=1).isoformat()
        except ValueError:
            return False

    @classmethod
    def _build_preview_html(cls, rows, total):
        headers = [column['name'] for column in cls._template_columns()]
        table = ['<table class="table table-sm table-hover"><thead><tr>']
        table.extend('<th>%s</th>' % escape(header) for header in headers)
        table.append('</tr></thead><tbody>')
        for row in rows:
            table.append('<tr>')
            table.extend(
                '<td>%s</td>' % escape(str(row.get(header, '') or ''))
                for header in headers
            )
            table.append('</tr>')
        table.append('</tbody></table>')
        return (
            '<p>%s ligne(s) détectée(s). Prévisualisation des 10 premières.</p>%s'
            % (total, ''.join(table))
        )

    @staticmethod
    def _build_result_html(stats):
        errors = ''.join(
            '<li>Ligne %s : %s</li>' % (
                error['line'],
                escape(error['error']),
            )
            for error in stats['errors']
        )
        error_block = '<ul>%s</ul>' % errors if errors else '<p>Aucune erreur.</p>'
        return """
            <p><strong>%s</strong> album(s) créé(s).</p>
            <p><strong>%s</strong> album(s) mis à jour.</p>
            <p><strong>%s</strong> erreur(s).</p>
            %s
        """ % (stats['created'], stats['updated'], len(stats['errors']), error_block)

    @classmethod
    def _build_error_report_csv(cls, errors):
        if not errors:
            return False

        buffer = StringIO(newline='')
        writer = csv.writer(buffer, delimiter=';', lineterminator='\n')
        headers = [column['name'] for column in cls._template_columns()]
        writer.writerow(['ligne', 'erreur', *headers])
        for error in errors:
            row = error['row']
            writer.writerow([
                error['line'],
                error['error'],
                *[row.get(header, '') for header in headers],
            ])
        return buffer.getvalue().encode('utf-8')

    @classmethod
    def _template_columns(cls):
        return [
            {
                'name': 'serie_name',
                'description': 'Nom de la série',
                'example': "Agent 212 (L')",
            },
            {
                'name': 'tome',
                'description': 'Numéro du tome',
                'example': '5',
            },
            {
                'name': 'titre_album',
                'description': "Titre de l'album",
                'example': 'Poulet aux amendes',
            },
            {
                'name': 'isbn',
                'description': 'ISBN EAN-13, sans tirets de préférence',
                'example': '',
            },
            {
                'name': 'date_parution',
                'description': 'Date au format YYYY-MM-DD',
                'example': '1985-05-01',
            },
            {
                'name': 'nb_pages',
                'description': 'Nombre de pages',
                'example': '',
            },
            {
                'name': 'editeur',
                'description': "Nom de l'éditeur",
                'example': 'Dupuis',
            },
            {
                'name': 'scenariste',
                'description': 'Scénaristes, séparés par ;, | ou retour ligne',
                'example': '',
            },
            {
                'name': 'dessinateur',
                'description': 'Dessinateurs, séparés par ;, | ou retour ligne',
                'example': '',
            },
            {
                'name': 'coloriste',
                'description': 'Coloristes, séparés par ;, | ou retour ligne',
                'example': '',
            },
            {
                'name': 'genre',
                'description': 'Genre principal',
                'example': 'Humour',
            },
            {
                'name': 'etat_lecture',
                'description': 'Valeurs acceptées : non_lu, en_cours, lu',
                'example': 'non_lu',
            },
            {
                'name': 'note',
                'description': 'Note entre 0 et 5',
                'example': '',
            },
            {
                'name': 'url_couverture',
                'description': 'URL de la couverture',
                'example': '',
            },
            {
                'name': 'url_club_be',
                'description': "URL d'achat Club.be",
                'example': '',
            },
            {
                'name': 'url_amazon_be',
                'description': "URL d'achat Amazon.com.be",
                'example': '',
            },
        ]

    @classmethod
    def _instruction_rows(cls):
        return [
            (
                'Format CSV',
                'Utiliser un encodage UTF-8 et le séparateur point-virgule (;).',
            ),
            (
                'Dates',
                'Utiliser YYYY-MM-DD. Si la source contient seulement MM/YYYY, '
                'mettre le premier jour du mois, par exemple 05/1985 -> 1985-05-01.',
            ),
            (
                'Auteurs',
                'Séparer plusieurs auteurs par point-virgule, barre verticale '
                'ou retour ligne dans scenariste, dessinateur ou coloriste. '
                'Les virgules sont conservées dans les noms.',
            ),
            (
                'État de lecture',
                'Valeurs techniques attendues : non_lu, en_cours, lu.',
            ),
            (
                'Excel fourni',
                "Le fichier Albums_Collection_En_Ligne.xlsx contient les colonnes N° "
                "et Contenu. La colonne Contenu doit être éclatée vers série, tome, "
                "titre, date de parution et éditeur avant import.",
            ),
            (
                'Exemple source',
                "Agent 212 (L') -5- Poulet aux amendes 05/1985 Dupuis 11/03/2017 Neuf 12",
            ),
            (
                'Liens',
                'url_club_be et url_amazon_be sont optionnels ; ils pourront aussi '
                'être générés automatiquement par le connecteur BDGest.',
            ),
        ]

    @classmethod
    def _build_csv_template(cls):
        buffer = StringIO(newline='')
        writer = csv.writer(buffer, delimiter=';', lineterminator='\n')
        columns = cls._template_columns()
        writer.writerow([column['name'] for column in columns])
        writer.writerow([column['example'] for column in columns])
        return buffer.getvalue().encode('utf-8')

    @classmethod
    def _build_xlsx_template(cls):
        columns = cls._template_columns()
        album_rows = [
            [column['name'] for column in columns],
            [column['example'] for column in columns],
        ]
        instruction_rows = [
            ['Sujet', 'Instruction'],
            *cls._instruction_rows(),
            [],
            ['Colonne', 'Description'],
            *[(column['name'], column['description']) for column in columns],
        ]

        output = BytesIO()
        with ZipFile(output, 'w', ZIP_DEFLATED) as workbook:
            files = {
                '[Content_Types].xml': cls._xlsx_content_types(),
                '_rels/.rels': cls._xlsx_root_rels(),
                'docProps/app.xml': cls._xlsx_app_props(),
                'docProps/core.xml': cls._xlsx_core_props(),
                'xl/workbook.xml': cls._xlsx_workbook(),
                'xl/_rels/workbook.xml.rels': cls._xlsx_workbook_rels(),
                'xl/styles.xml': cls._xlsx_styles(),
                'xl/worksheets/sheet1.xml': cls._xlsx_sheet(
                    album_rows,
                    column_widths=[18, 10, 24, 18, 16, 12, 18, 22, 22, 22, 16, 16, 10, 28, 28, 28],
                ),
                'xl/worksheets/sheet2.xml': cls._xlsx_sheet(
                    instruction_rows,
                    column_widths=[22, 110],
                    wrap_from_row=2,
                ),
            }
            for path, content in files.items():
                workbook.writestr(path, content)
        return output.getvalue()

    @staticmethod
    def _xlsx_content_types():
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    @staticmethod
    def _xlsx_root_rels():
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

    @staticmethod
    def _xlsx_app_props():
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Odoo</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>2</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="2" baseType="lpstr">
      <vt:lpstr>Albums</vt:lpstr>
      <vt:lpstr>Instructions</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
</Properties>"""

    @staticmethod
    def _xlsx_core_props():
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        created_at = created_at.replace('+00:00', 'Z')
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Modèle d'import albums BD</dc:title>
  <dc:creator>Odoo Comic Collection</dc:creator>
  <cp:lastModifiedBy>Odoo Comic Collection</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created_at}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created_at}</dcterms:modified>
</cp:coreProperties>"""

    @staticmethod
    def _xlsx_workbook():
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Albums" sheetId="1" r:id="rId1"/>
    <sheet name="Instructions" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""

    @staticmethod
    def _xlsx_workbook_rels():
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    @staticmethod
    def _xlsx_styles():
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

    @classmethod
    def _xlsx_sheet(cls, rows, column_widths=None, wrap_from_row=None):
        max_columns = max((len(row) for row in rows), default=1)
        dimension = 'A1:%s%s' % (cls._xlsx_column_name(max_columns), max(len(rows), 1))
        cols_xml = cls._xlsx_cols(column_widths or [18] * max_columns)
        rows_xml = '\n'.join(
            cls._xlsx_row(index, row, wrap=index >= wrap_from_row if wrap_from_row else False)
            for index, row in enumerate(rows, start=1)
        )
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
           xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="{dimension}"/>
  <sheetViews>
    <sheetView workbookViewId="0">
      <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>
    </sheetView>
  </sheetViews>
  {cols_xml}
  <sheetData>
{rows_xml}
  </sheetData>
</worksheet>"""

    @classmethod
    def _xlsx_cols(cls, column_widths):
        cols = []
        for index, width in enumerate(column_widths, start=1):
            cols.append(
                '<col min="%s" max="%s" width="%s" customWidth="1"/>'
                % (index, index, width)
            )
        return '<cols>%s</cols>' % ''.join(cols)

    @classmethod
    def _xlsx_row(cls, row_index, values, wrap=False):
        cells = []
        for column_index, value in enumerate(values, start=1):
            style = 1 if row_index == 1 else 2 if wrap else None
            cells.append(cls._xlsx_cell(row_index, column_index, value, style=style))
        return '    <row r="%s">%s</row>' % (row_index, ''.join(cells))

    @classmethod
    def _xlsx_cell(cls, row_index, column_index, value, style=None):
        reference = '%s%s' % (cls._xlsx_column_name(column_index), row_index)
        style_attr = ' s="%s"' % style if style is not None else ''
        if value in (None, ''):
            return '<c r="%s"%s/>' % (reference, style_attr)
        text = escape(str(value))
        return (
            '<c r="%s" t="inlineStr"%s><is><t>%s</t></is></c>'
            % (reference, style_attr, text)
        )

    @staticmethod
    def _xlsx_column_name(index):
        letters = ''
        while index:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters


class ComicImportMappingLine(models.TransientModel):
    _name = 'comic.import.mapping.line'
    _description = "Ligne de mapping d'import BD"
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'comic.import.wizard',
        string='Assistant',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Séquence', default=10)
    column_name = fields.Char(string='Colonne source', required=True, readonly=True)
    sample_value = fields.Char(string='Exemple', readonly=True)
    target_field = fields.Selection(
        selection='_selection_target_field',
        string='Champ cible',
    )

    def _selection_target_field(self):
        return [
            (column['name'], column['description'])
            for column in ComicImportWizard._template_columns()
        ] + [
            ('compact_content', 'Contenu compact export collection'),
        ]
