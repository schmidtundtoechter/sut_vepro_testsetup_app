# sut_vepro_testsetup_app

Frappe-App zur Sicherung und Wiederherstellung der ERPNext-Konfiguration des VePro-Testsystems. Damit kann das Testsystem nach einem Reset schnell in den gewünschten Zustand zurückversetzt werden.

---

## Inhalt

- [Was wird gesichert?](#was-wird-gesichert)
- [Installation](#installation)
- [Backend: Sicherungen in Git pflegen](#backend-sicherungen-in-git-pflegen)
- [Website: Sicherungen erstellen und einspielen](#website-sicherungen-erstellen-und-einspielen)
- [Entwicklung](#entwicklung)

---

## Was wird gesichert?

| Bereich | Datei | Beschreibung |
|---|---|---|
| **Unternehmen** | `backup_data/companies.json` | Alle Company-Dokumente (Grunddaten, Währung, Land, Steuer-ID, Buchungskonten) |
| **Favicon** | `backup_data/favicon.*` + `favicon.json` | Favicon-Datei und Pfad aus den Website-Einstellungen |
| **Workspaces** | `backup_data/workspaces.json` | Alle nicht-nativen Workspaces (kein Frappe/ERPNext-Core) |

Workspaces aus `frappe`, `erpnext`, `eu_einvoice` und `helpdesk` werden übersprungen. Alle anderen Workspaces werden gesichert – auch solche ohne Modulzuordnung (manuell im UI erstellt). Weitere auszuschließende Apps können in `_WORKSPACE_EXCLUDED_APPS` in `api.py` eingetragen werden.

---

## Installation

```bash
cd /pfad/zum/bench
bench get-app git@github.com:schmidtundtoechter/sut_vepro_testsetup_app.git --branch develop
bench --site <sitename> install-app sut_vepro_testsetup_app
```

---

## Backend: Sicherungen in Git pflegen

Alle Sicherungsdateien liegen im Verzeichnis der App:

```
apps/sut_vepro_testsetup_app/sut_vepro_testsetup_app/backup_data/
```

Diese Dateien werden durch die Webseite erzeugt (Klick auf „Jetzt sichern"). Sie existieren zunächst nur lokal auf dem Server. Damit sie bei einem System-Reset noch vorhanden sind, müssen sie in das Git-Repository committet werden.

### Was ist ein Git-Commit?

Git ist ein Versionskontrollsystem. Ein Commit speichert den aktuellen Stand von Dateien dauerhaft im Repository-Verlauf. Mit `git push` werden die Änderungen auf GitHub hochgeladen – erst dann sind sie auch nach einem System-Neuaufbau noch verfügbar.

### Voraussetzungen

- Git ist im Dev-Container verfügbar
- SSH-Zugang zu GitHub ist eingerichtet (wird für `git push` benötigt)
- Das Repository `sut_vepro_testsetup_app` ist auf GitHub vorhanden

### Ablauf: Sicherung in Git speichern

**Schritt 1:** Nach dem Erstellen einer Sicherung (Klick auf „Jetzt sichern") ins App-Verzeichnis wechseln:

```bash
cd /workspace/development/frappe-bench/apps/sut_vepro_testsetup_app
```

**Schritt 2:** Den aktuellen Status prüfen (zeigt welche Dateien sich geändert haben):

```bash
git status
```

**Schritt 3:** Die Sicherungsdateien zum Commit vormerken:

```bash
git add sut_vepro_testsetup_app/backup_data/
```

**Schritt 4:** Commit erstellen mit einer aussagekräftigen Nachricht:

```bash
git commit -m "backup: Konfiguration gesichert $(date '+%Y-%m-%d')"
```

**Schritt 5:** Auf GitHub hochladen:

```bash
git push
```

### Wann muss ein Git-Commit gemacht werden?

Immer nach einem Klick auf „Jetzt sichern" auf der Webseite, wenn die Sicherung dauerhaft erhalten bleiben soll. Ohne Commit sind die JSON-Dateien nur lokal vorhanden und gehen bei einem System-Reset verloren.

### Ablauf: Wiederherstellen nach einem System-Reset

```bash
# 1. App neu installieren – Sicherungsdateien kommen automatisch mit
bench get-app git@github.com:schmidtundtoechter/sut_vepro_testsetup_app.git --branch develop
bench --site <sitename> install-app sut_vepro_testsetup_app

# 2. Dann über die Webseite einspielen (siehe unten)
```

---

## Website: Sicherungen erstellen und einspielen

Die Verwaltungsseite ist erreichbar unter:

```
http://<hostname>/app/vepro_setup
```

Beispiel für die lokale Entwicklungsumgebung:

```
http://d-code.localhost:8000/app/vepro_setup
```

> Zugriff nur für Benutzer mit der Rolle **System Manager**.

### Sicherung erstellen

1. Seite öffnen
2. Beim gewünschten Bereich auf **„Jetzt sichern"** klicken
3. Die Sicherungsdatei wird im `backup_data/`-Verzeichnis der App gespeichert
4. Datum der letzten Sicherung wird sofort angezeigt
5. **Danach per Git committen** (siehe Backend-Abschnitt)

### Einstellungen einspielen

1. Seite öffnen
2. Beim gewünschten Bereich auf **„Einspielen"** klicken
3. Sicherheitsabfrage bestätigen
4. Die gesicherten Daten werden in ERPNext wiederhergestellt

> **Achtung:** Das Einspielen überschreibt bestehende Daten ohne weitere Rückfrage.

> **Passwörter werden niemals gesichert.** Nach dem Einspielen müssen E-Mail-Passwörter
> manuell eingetragen werden. Neu angelegte Nutzer müssen ihr Passwort über
> *„Passwort vergessen"* selbst setzen.

### Übersicht der Bereiche

| Bereich | Sichern speichert | Einspielen stellt wieder her |
|---|---|---|
| **Unternehmen** | Alle Company-Felder (außer Name/Kürzel) | Aktualisiert bestehende Companies |
| **Favicon** | Favicon-Datei + URL-Pfad | Lädt Datei hoch, setzt URL in Website-Einstellungen |
| **Workspaces** | Alle nicht-nativen Workspaces (vollständig) | Löscht bestehende Version, importiert neu |
| **Nutzer** | Rollen, Rechte (kein Passwort) | Aktualisiert bestehende Nutzer, legt fehlende neu an |
| **E-Mail-Konten** | Servereinstellungen (kein Passwort) | Aktualisiert bestehende Konten, legt fehlende neu an |

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
