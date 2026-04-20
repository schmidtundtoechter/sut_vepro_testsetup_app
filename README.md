# sut_vepro_testsetup_app

Frappe-App zur Sicherung und Wiederherstellung der ERPNext-Konfiguration des VePro-Testsystems. Damit kann das Testsystem nach einem Reset schnell in den gewünschten Zustand zurückversetzt werden.

---

## Inhalt

- [Was wird gesichert?](#was-wird-gesichert)
- [Installation](#installation)
- [Backend-Funktionen](#backend-funktionen)
- [Webseite: VePro Setup](#webseite-vepro-setup)
- [Entwicklung](#entwicklung)

---

## Was wird gesichert?

| Bereich | Sicherungsdatei(en) | Beschreibung |
|---|---|---|
| **Unternehmen** | `backup_data/companies.json` | Alle Company-Dokumente (Grunddaten, Währung, Land, Steuer-ID, Buchungskonten) |
| **Favicon** | `backup_data/favicon.*` + `backup_data/favicon.json` | Favicon-Bilddatei und Original-URL-Pfad aus den Website-Einstellungen |
| **Workspaces** | `backup_data/workspaces.json` | Alle nicht-nativen Workspaces (kein Frappe/ERPNext-Core, keine persönlichen Workspaces) |

---

## Installation

```bash
cd /pfad/zum/bench
bench get-app git@github.com:schmidtundtoechter/sut_vepro_testsetup_app.git --branch develop
bench --site <sitename> install-app sut_vepro_testsetup_app
bench --site <sitename> migrate
```

---

## Backend-Funktionen

Alle Sicherungsdateien liegen im Verzeichnis der App:

```
apps/sut_vepro_testsetup_app/sut_vepro_testsetup_app/backup_data/
```

Die Dateien sind Teil des Git-Repositories und müssen nach jeder Sicherung manuell committet werden.

### Verfügbare Python-Funktionen (`api.py`)

Alle Funktionen erfordern die Rolle **System Manager** und sind als Frappe-Whitelist-Endpunkte registriert.

---

#### `get_backup_status()`

Gibt den Status aller Sicherungsdateien zurück (ob vorhanden, Datum der letzten Änderung).

- **Rückgabe:** Dictionary mit den Schlüsseln `company`, `favicon`, `workspace`
- **Verwendet von:** Webseite beim Laden – zeigt Datum oder „Keine Sicherung vorhanden"

---

#### `backup_company()`

Exportiert alle Company-Dokumente nach `backup_data/companies.json`.

**Gesicherte Felder:**

| Gruppe | Felder |
|---|---|
| Grunddaten | `company_name`, `abbr`, `default_currency`, `country`, `tax_id`, `date_of_establishment`, `domain` |
| Kontakt | `email`, `phone_no`, `fax`, `website` |
| Struktur | `chart_of_accounts`, `default_letter_head`, `company_logo`, `parent_company`, `cost_center` |
| Buchhaltungskonten | `round_off_account`, `round_off_cost_center`, `default_receivable_account`, `default_payable_account`, `default_bank_account`, `default_cash_account`, `default_expense_account`, `default_income_account`, `write_off_account`, `discount_allowed_account`, `discount_received_account`, `exchange_gain_loss_account`, `unrealized_exchange_gain_loss_account`, `default_payroll_payable_account`, `default_employee_advance_account` |

- **Rückgabe:** Anzahl der gesicherten Unternehmen

---

#### `restore_company()`

Liest `backup_data/companies.json` und aktualisiert die bestehenden Company-Dokumente.

- **Verhalten:** Nur Update – es werden keine neuen Companies angelegt. Nicht gefundene Companies werden übersprungen (Warnung im UI).
- **Geschützte Felder:** `company_name` und `abbr` werden nicht überschrieben.
- **Rückgabe:** Anzahl der wiederhergestellten Unternehmen

---

#### `backup_favicon()`

Liest das Favicon aus den Website-Einstellungen, kopiert die Datei nach `backup_data/favicon.<ext>` und speichert den ursprünglichen Pfad in `backup_data/favicon.json`.

- **Unterstützte Pfade:** `/files/...` (öffentlich) und `/private/files/...`
- **Fehler:** Wirft eine Exception, wenn kein Favicon gesetzt ist oder die Datei nicht gefunden wird.
- **Rückgabe:** Bestätigung der Sicherung

---

#### `restore_favicon()`

Liest `backup_data/favicon.json`, lädt die gesicherte Favicon-Datei als neues File-Dokument hoch und setzt die URL in den Website-Einstellungen.

- **Verhalten:** Erstellt immer eine neue File-Instanz (kein Überschreiben bestehender Dateien).
- **Rückgabe:** Bestätigung und neue Datei-URL

---

#### `backup_workspace()`

Exportiert alle nicht-nativen, nicht-persönlichen Workspaces nach `backup_data/workspaces.json`.

- **Übersprungen werden:**
  - Workspaces mit `for_user` gesetzt (persönliche Workspaces)
  - Workspaces, deren Modul zu `frappe` oder `erpnext` gehört
- **Gesichert wird:** Das vollständige Dokument (`as_dict()`), inkl. Links, Shortcuts, Charts, Number Cards
- **Rückgabe:** Anzahl gesicherter und übersprungener Workspaces

---

#### `restore_workspace()`

Liest `backup_data/workspaces.json` und stellt alle gesicherten Workspaces wieder her.

- **Verhalten:** Bestehende Workspaces mit gleichem Namen werden zuerst gelöscht, dann neu eingefügt.
- **Fehlerbehandlung:** Einzelne Fehler werden geloggt und übersprungen; andere Workspaces werden weiter verarbeitet.
- **Rückgabe:** Anzahl wiederhergestellter Workspaces

---

### Git-Workflow nach einer Sicherung

```bash
cd apps/sut_vepro_testsetup_app
git add sut_vepro_testsetup_app/backup_data/
git commit -m "backup: Konfiguration gesichert ($(date '+%Y-%m-%d'))"
git push
```

### Git-Workflow beim Wiederherstellen nach einem Reset

```bash
# 1. App neu installieren – Sicherungsdateien sind im Repository enthalten
bench get-app git@github.com:schmidtundtoechter/sut_vepro_testsetup_app.git --branch develop
bench --site <sitename> install-app sut_vepro_testsetup_app

# 2. Über die Webseite einspielen (siehe nächster Abschnitt)
```

---

## Webseite: VePro Setup

Die Verwaltungsseite ist erreichbar unter:

```
http://<hostname>/app/vepro_setup
```

> Zugriff nur für Benutzer mit der Rolle **System Manager**.

### Aufbau der Seite

Die Seite besteht aus einer **Anleitung** (oben) und einer **Karte pro Sicherungsbereich**.

Jede Karte zeigt:
- Name und Kurzbeschreibung des Bereichs
- Datum und Uhrzeit der letzten Sicherung (oder „Keine Sicherung vorhanden")
- Button **„Jetzt sichern"** – immer aktiv
- Button **„Einspielen"** – nur aktiv, wenn eine Sicherung vorhanden ist

### Funktion: Sicherung erstellen

1. Seite öffnen (`/app/vepro_setup`)
2. Beim gewünschten Bereich auf **„Jetzt sichern"** klicken
3. Die Sicherungsdatei wird im `backup_data/`-Verzeichnis der App gespeichert
4. Das Datum der letzten Sicherung aktualisiert sich sofort
5. **Anschließend per Git committen** (siehe Backend-Abschnitt)

### Funktion: Einstellungen einspielen

1. Seite öffnen (`/app/vepro_setup`)
2. Beim gewünschten Bereich auf **„Einspielen"** klicken
3. Sicherheitsabfrage bestätigen
4. Die gesicherten Daten werden in ERPNext wiederhergestellt

> **Achtung:** Das Einspielen überschreibt bestehende Daten ohne weitere Rückfrage.

### Verfügbare Bereiche auf der Seite

| Bereich | Sichern | Einspielen |
|---|---|---|
| **Unternehmen (Company)** | Exportiert alle Company-Dokumente als JSON | Aktualisiert bestehende Companies (kein Anlegen neuer) |
| **Favicon** | Kopiert die Favicon-Datei und speichert den Pfad | Lädt Datei neu hoch, setzt URL in Website-Einstellungen |
| **Workspaces (nicht-native)** | Exportiert eigene/angepasste Workspaces vollständig | Löscht alte Version und importiert neu |

---

## Entwicklung

Diese App verwendet `pre-commit` für Code-Formatierung und Linting:

```bash
cd apps/sut_vepro_testsetup_app
pre-commit install
```

Verwendete Tools: `ruff`, `eslint`, `prettier`, `pyupgrade`

---

## Lizenz

MIT
