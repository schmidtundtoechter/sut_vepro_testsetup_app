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
		("user", "users.json"),
		("email_account", "email_accounts.json"),
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

# Workspaces belonging to these apps are explicitly excluded from backups.
# All other workspaces (including those with no module) are included.
_WORKSPACE_EXCLUDED_APPS = {"frappe", "erpnext", "eu_einvoice", "helpdesk"}


def _get_excluded_module_names():
	"""Returns module names that belong to excluded apps."""
	all_modules = frappe.db.get_all("Module Def", fields=["name", "app_name"])
	return {m.name for m in all_modules if m.app_name in _WORKSPACE_EXCLUDED_APPS}


@frappe.whitelist()
def backup_workspace():
	"""Exports all non-excluded, non-personal Workspaces to backup_data/workspaces.json.

	Included:
	- Workspaces with no module (manually created in the UI)
	- Workspaces whose module belongs to an app not in _WORKSPACE_EXCLUDED_APPS

	Excluded:
	- Personal workspaces (for_user set)
	- Workspaces from apps listed in _WORKSPACE_EXCLUDED_APPS
	"""
	frappe.only_for("System Manager")

	excluded_modules = _get_excluded_module_names()

	workspaces = frappe.db.get_all(
		"Workspace",
		fields=["name", "module", "for_user"],
		filters={"for_user": ["is", "not set"]},
	)

	data = []
	skipped = 0
	for ws in workspaces:
		# Always include workspaces with no module (manually created)
		if ws.module and ws.module in excluded_modules:
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
		"message": _("{0} Workspaces gesichert ({1} übersprungen)").format(len(data), skipped),
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


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

# System accounts that are never backed up.
_USER_SKIP = {"Administrator", "Guest"}

_USER_FIELDS = [
	"name",
	"first_name",
	"last_name",
	"full_name",
	"username",
	"gender",
	"birth_date",
	"language",
	"time_zone",
	"user_type",
	"enabled",
	"module_profile",
	"role_profile_name",
]


@frappe.whitelist()
def backup_user():
	"""Exports all non-system Users with roles and User Permissions to backup_data/users.json."""
	frappe.only_for("System Manager")

	users = frappe.db.get_all(
		"User",
		fields=["name"],
		filters={"name": ["not in", list(_USER_SKIP)]},
	)
	data = []
	for u in users:
		try:
			doc = frappe.get_doc("User", u.name)
			entry = {f: doc.get(f) for f in _USER_FIELDS if doc.get(f) is not None}
			entry["roles"] = [{"role": r.role} for r in doc.roles]
			entry["user_permissions"] = frappe.db.get_all(
				"User Permission",
				fields=["allow", "for_value", "apply_to_all_doctypes", "applicable_for"],
				filters={"user": u.name},
			)
			data.append(entry)
		except Exception as e:
			frappe.log_error(f"backup_user – {u.name}: {e}")

	filepath = os.path.join(get_backup_data_path(), "users.json")
	with open(filepath, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False, default=str)

	return {"message": _("{0} Nutzer gesichert").format(len(data)), "count": len(data)}


@frappe.whitelist()
def restore_user():
	"""Restores Users (roles, permissions) from backup_data/users.json.

	Passwords are never stored and remain unchanged for existing users.
	New users are inserted without a password – they must use "Forgot Password".
	"""
	frappe.only_for("System Manager")
	filepath = os.path.join(get_backup_data_path(), "users.json")
	if not os.path.exists(filepath):
		frappe.throw(_("Keine Nutzer-Sicherung gefunden."))

	with open(filepath, "r", encoding="utf-8") as f:
		data = json.load(f)

	restored = 0
	for user_data in data:
		email = user_data.get("name")
		if not email or email in _USER_SKIP:
			continue
		try:
			permissions = user_data.pop("user_permissions", [])
			roles = user_data.pop("roles", [])

			if frappe.db.exists("User", email):
				doc = frappe.get_doc("User", email)
				for key, value in user_data.items():
					if key == "name":
						continue
					try:
						setattr(doc, key, value)
					except Exception:
						pass
				doc.roles = []
				for r in roles:
					doc.append("roles", {"role": r["role"]})
				doc.save(ignore_permissions=True)
			else:
				doc = frappe.get_doc({"doctype": "User", **user_data})
				doc.flags.ignore_password_policy = True
				doc.send_welcome_email = 0
				for r in roles:
					doc.append("roles", {"role": r["role"]})
				doc.insert(ignore_permissions=True)

			# Restore User Permissions
			frappe.db.delete("User Permission", {"user": email})
			for perm in permissions:
				frappe.get_doc(
					{
						"doctype": "User Permission",
						"user": email,
						"allow": perm.get("allow"),
						"for_value": perm.get("for_value"),
						"apply_to_all_doctypes": perm.get("apply_to_all_doctypes"),
						"applicable_for": perm.get("applicable_for"),
					}
				).insert(ignore_permissions=True)

			restored += 1
		except Exception as e:
			frappe.log_error(f"restore_user – {email}: {e}")

	frappe.db.commit()
	return {
		"message": _("{0} Nutzer wiederhergestellt (Passwörter unverändert)").format(restored),
		"count": restored,
	}


# ---------------------------------------------------------------------------
# Email Accounts
# ---------------------------------------------------------------------------

# Sensitive fields that are never written to the backup file.
_EMAIL_ACCOUNT_SENSITIVE = {"password", "smtp_password", "api_key", "api_secret", "connected_user"}


@frappe.whitelist()
def backup_email_account():
	"""Exports all Email Accounts (without passwords) to backup_data/email_accounts.json."""
	frappe.only_for("System Manager")

	accounts = frappe.db.get_all("Email Account", fields=["name"])
	data = []
	for acc in accounts:
		try:
			doc = frappe.get_doc("Email Account", acc.name)
			entry = doc.as_dict()
			for field in _EMAIL_ACCOUNT_SENSITIVE:
				entry.pop(field, None)
			data.append(entry)
		except Exception as e:
			frappe.log_error(f"backup_email_account – {acc.name}: {e}")

	filepath = os.path.join(get_backup_data_path(), "email_accounts.json")
	with open(filepath, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False, default=str)

	return {
		"message": _("{0} E-Mail-Konten gesichert (ohne Passwörter)").format(len(data)),
		"count": len(data),
	}


@frappe.whitelist()
def restore_email_account():
	"""Restores Email Accounts from backup_data/email_accounts.json.

	Passwords are not stored in the backup and must be re-entered manually after restore.
	"""
	frappe.only_for("System Manager")
	filepath = os.path.join(get_backup_data_path(), "email_accounts.json")
	if not os.path.exists(filepath):
		frappe.throw(_("Keine E-Mail-Konto-Sicherung gefunden."))

	with open(filepath, "r", encoding="utf-8") as f:
		data = json.load(f)

	restored = 0
	for acc_data in data:
		name = acc_data.get("name") or acc_data.get("email_account_name")
		if not name:
			continue
		try:
			# Remove metadata and sensitive fields before writing
			clean = {
				k: v
				for k, v in acc_data.items()
				if k not in _EMAIL_ACCOUNT_SENSITIVE
				and k not in ("creation", "modified", "modified_by", "owner", "docstatus", "idx")
			}
			if frappe.db.exists("Email Account", name):
				doc = frappe.get_doc("Email Account", name)
				for key, value in clean.items():
					if key in ("name", "doctype"):
						continue
					if value is not None:
						try:
							setattr(doc, key, value)
						except Exception:
							pass
				doc.save(ignore_permissions=True)
			else:
				doc = frappe.get_doc(clean)
				doc.insert(ignore_permissions=True)
			restored += 1
		except Exception as e:
			frappe.log_error(f"restore_email_account – {name}: {e}")

	frappe.db.commit()
	return {
		"message": _(
			"{0} E-Mail-Konten wiederhergestellt (Passwörter müssen manuell eingetragen werden)"
		).format(restored),
		"count": restored,
	}
