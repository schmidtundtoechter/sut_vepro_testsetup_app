import datetime
import json
import os
import shutil

import frappe
from frappe import _


def get_backup_data_path():
	"""Returns the path to the backup_data directory within the app."""
	app_path = frappe.get_app_path("sut_vepro_testsetup_app")
	backup_path = os.path.join(app_path, "backup_data")
	os.makedirs(backup_path, exist_ok=True)
	return backup_path


@frappe.whitelist()
def get_backup_status():
	"""Returns status info about existing backup files."""
	frappe.only_for("System Manager")
	backup_path = get_backup_data_path()
	status = {}
	for key, filename in [
		("company", "companies.json"),
		("favicon", "favicon.json"),
		("workspace", "workspaces.json"),
	]:
		filepath = os.path.join(backup_path, filename)
		if os.path.exists(filepath):
			mtime = os.path.getmtime(filepath)
			status[key] = {
				"exists": True,
				"modified": datetime.datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M:%S"),
			}
		else:
			status[key] = {"exists": False, "modified": None}
	return status


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

_COMPANY_FIELDS = [
	"company_name",
	"abbr",
	"default_currency",
	"country",
	"tax_id",
	"date_of_establishment",
	"domain",
	"chart_of_accounts",
	"default_letter_head",
	"email",
	"phone_no",
	"fax",
	"website",
	"parent_company",
	"company_logo",
	"round_off_account",
	"round_off_cost_center",
	"default_receivable_account",
	"default_payable_account",
	"default_bank_account",
	"default_cash_account",
	"default_expense_account",
	"default_income_account",
	"write_off_account",
	"discount_allowed_account",
	"discount_received_account",
	"exchange_gain_loss_account",
	"unrealized_exchange_gain_loss_account",
	"default_payroll_payable_account",
	"default_employee_advance_account",
	"cost_center",
]


@frappe.whitelist()
def backup_company():
	"""Exports all Company documents to backup_data/companies.json."""
	frappe.only_for("System Manager")
	companies = frappe.get_all("Company", fields=["name"])
	data = []
	for c in companies:
		try:
			doc = frappe.get_doc("Company", c.name)
			data.append({field: doc.get(field) for field in _COMPANY_FIELDS})
		except Exception as e:
			frappe.log_error(f"backup_company – {c.name}: {e}")

	filepath = os.path.join(get_backup_data_path(), "companies.json")
	with open(filepath, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False, default=str)

	return {"message": _("{0} Unternehmen gesichert").format(len(data)), "count": len(data)}


@frappe.whitelist()
def restore_company():
	"""Restores Company data from backup_data/companies.json."""
	frappe.only_for("System Manager")
	filepath = os.path.join(get_backup_data_path(), "companies.json")
	if not os.path.exists(filepath):
		frappe.throw(_("Keine Sicherung gefunden. Bitte zuerst eine Sicherung erstellen."))

	with open(filepath, "r", encoding="utf-8") as f:
		data = json.load(f)

	restored = 0
	for company_data in data:
		company_name = company_data.get("company_name")
		if not company_name:
			continue
		if not frappe.db.exists("Company", company_name):
			frappe.msgprint(
				_("Unternehmen {0} nicht gefunden – übersprungen.").format(company_name),
				indicator="orange",
			)
			continue
		doc = frappe.get_doc("Company", company_name)
		for key, value in company_data.items():
			if key not in ("company_name", "abbr") and value is not None:
				try:
					setattr(doc, key, value)
				except Exception:
					pass
		doc.save(ignore_permissions=True)
		restored += 1

	frappe.db.commit()
	return {"message": _("{0} Unternehmen wiederhergestellt").format(restored), "count": restored}


# ---------------------------------------------------------------------------
# Favicon
# ---------------------------------------------------------------------------


@frappe.whitelist()
def backup_favicon():
	"""Backs up the favicon from Website Settings."""
	frappe.only_for("System Manager")
	favicon_url = frappe.db.get_single_value("Website Settings", "favicon")
	if not favicon_url:
		frappe.throw(_("Kein Favicon in den Website-Einstellungen gefunden."))

	site_path = frappe.get_site_path()
	if favicon_url.startswith("/files/"):
		file_path = os.path.join(site_path, "public", favicon_url.lstrip("/"))
	elif favicon_url.startswith("/private/files/"):
		file_path = os.path.join(site_path, favicon_url.lstrip("/"))
	else:
		frappe.throw(_("Unbekanntes Favicon-Format: {0}").format(favicon_url))

	if not os.path.exists(file_path):
		frappe.throw(_("Favicon-Datei nicht gefunden: {0}").format(file_path))

	backup_path = get_backup_data_path()
	ext = os.path.splitext(favicon_url)[1]
	dest_filename = f"favicon{ext}"
	shutil.copy2(file_path, os.path.join(backup_path, dest_filename))

	meta = {"favicon_url": favicon_url, "filename": dest_filename}
	with open(os.path.join(backup_path, "favicon.json"), "w") as f:
		json.dump(meta, f, indent=2)

	return {"message": _("Favicon gesichert")}


@frappe.whitelist()
def restore_favicon():
	"""Restores the favicon from backup."""
	frappe.only_for("System Manager")
	backup_path = get_backup_data_path()
	meta_path = os.path.join(backup_path, "favicon.json")
	if not os.path.exists(meta_path):
		frappe.throw(_("Keine Favicon-Sicherung gefunden."))

	with open(meta_path) as f:
		meta = json.load(f)

	src_path = os.path.join(backup_path, meta["filename"])
	if not os.path.exists(src_path):
		frappe.throw(_("Favicon-Datei in der Sicherung nicht gefunden."))

	with open(src_path, "rb") as f:
		file_content = f.read()

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": meta["filename"],
			"content": file_content,
			"is_private": 0,
			"decode": False,
		}
	)
	file_doc.save(ignore_permissions=True)

	ws = frappe.get_doc("Website Settings")
	ws.favicon = file_doc.file_url
	ws.save(ignore_permissions=True)
	frappe.db.commit()

	return {"message": _("Favicon wiederhergestellt"), "file_url": file_doc.file_url}


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

# Apps whose workspaces are considered "native" and are not backed up.
_NATIVE_APPS = {"frappe", "erpnext"}


def _get_custom_module_names():
	"""Returns the set of module names that belong to non-native apps."""
	all_modules = frappe.db.get_all("Module Def", fields=["name", "app_name"])
	return {m.name for m in all_modules if m.app_name not in _NATIVE_APPS}


@frappe.whitelist()
def backup_workspace():
	"""Exports all non-native, non-personal Workspaces to backup_data/workspaces.json."""
	frappe.only_for("System Manager")

	custom_modules = _get_custom_module_names()

	workspaces = frappe.db.get_all(
		"Workspace",
		fields=["name", "module", "for_user"],
		filters={"for_user": ["is", "not set"]},
	)

	data = []
	skipped = 0
	for ws in workspaces:
		if ws.module and ws.module not in custom_modules:
			skipped += 1
			continue
		try:
			doc = frappe.get_doc("Workspace", ws.name)
			data.append(doc.as_dict())
		except Exception as e:
			frappe.log_error(f"backup_workspace – {ws.name}: {e}")

	filepath = os.path.join(get_backup_data_path(), "workspaces.json")
	with open(filepath, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False, default=str)

	return {
		"message": _("{0} Workspaces gesichert ({1} native übersprungen)").format(
			len(data), skipped
		),
		"count": len(data),
	}


@frappe.whitelist()
def restore_workspace():
	"""Restores Workspaces from backup_data/workspaces.json."""
	frappe.only_for("System Manager")
	filepath = os.path.join(get_backup_data_path(), "workspaces.json")
	if not os.path.exists(filepath):
		frappe.throw(_("Keine Workspace-Sicherung gefunden. Bitte zuerst eine Sicherung erstellen."))

	with open(filepath, "r", encoding="utf-8") as f:
		data = json.load(f)

	restored = 0
	for ws_data in data:
		name = ws_data.get("name")
		if not name:
			continue
		try:
			if frappe.db.exists("Workspace", name):
				frappe.delete_doc("Workspace", name, ignore_permissions=True, force=True)
			doc = frappe.get_doc(ws_data)
			doc.insert(ignore_permissions=True)
			restored += 1
		except Exception as e:
			frappe.log_error(f"restore_workspace – {name}: {e}")

	frappe.db.commit()
	return {
		"message": _("{0} Workspaces wiederhergestellt").format(restored),
		"count": restored,
	}
