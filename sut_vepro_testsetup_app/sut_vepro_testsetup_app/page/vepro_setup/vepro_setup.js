frappe.pages["vepro_setup"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "VePro Test-System Setup",
		single_column: true,
	});

	new VeproSetupPage(wrapper, page);
};

class VeproSetupPage {
	constructor(wrapper, page) {
		this.page = page;
		this.body = page.body;
		this.render();
		this.load_status();
	}

	render() {
		$(this.body).html(`
			<div class="p-5">
				<div class="row">
					<div class="col-md-9">
						${this.html_instructions()}
						${this.html_card(
							"company",
							"Unternehmen (Company)",
							"fa-building",
							"Sichert alle Unternehmen: Grunddaten, Währung, Land, Steuer-ID und Buchungskonten."
						)}
						${this.html_card(
							"favicon",
							"Favicon",
							"fa-image",
							"Sichert das Favicon aus den Website-Einstellungen als Datei im Repository."
						)}
						${this.html_card(
							"workspace",
							"Workspaces (nicht-native)",
							"fa-th-large",
							"Sichert alle Workspaces, die nicht zu Frappe oder ERPNext gehören (z. B. eigene und angepasste Workspaces)."
						)}
						${this.html_card(
							"user",
							"Nutzer (User)",
							"fa-users",
							"Sichert alle Nutzer (außer Administrator und Guest) mit ihren Rollen und Berechtigungen. Passwörter werden nicht gesichert."
						)}
						${this.html_card(
							"email_account",
							"E-Mail-Konten (Email Account)",
							"fa-envelope",
							"Sichert alle E-Mail-Konten mit Servereinstellungen. Passwörter werden aus Sicherheitsgründen nicht gesichert und müssen nach dem Einspielen manuell eingetragen werden."
						)}
					</div>
				</div>
			</div>
		`);
		this.bind_events();
	}

	html_instructions() {
		return `
			<div class="frappe-card mb-4 p-4">
				<h5 class="text-muted mb-3">
					<i class="fa fa-info-circle mr-2"></i>Anleitung
				</h5>
				<p class="mb-2">
					Dieses Werkzeug sichert die ERPNext-Konfiguration des VePro-Testsystems,
					damit es nach einem Reset schnell wiederhergestellt werden kann.
				</p>
				<ol class="mb-3">
					<li class="mb-1">
						<strong>Sichern:</strong> Klicke bei jeder Einstellungsgruppe auf
						<em>Jetzt sichern</em>. Die Daten werden als JSON-Datei im
						App-Verzeichnis (<code>backup_data/</code>) gespeichert.
					</li>
					<li class="mb-1">
						<strong>Git-Commit:</strong> Committe den Ordner <code>backup_data/</code>
						ins Repository, damit die Sicherung dauerhaft erhalten bleibt.
					</li>
					<li class="mb-1">
						<strong>Einspielen:</strong> Nach einem System-Reset die App installieren
						und auf <em>Einspielen</em> klicken, um die gesicherten Einstellungen
						wiederherzustellen.
					</li>
				</ol>
				<div class="alert alert-warning small mb-2">
					<i class="fa fa-exclamation-triangle mr-1"></i>
					<strong>Achtung:</strong> Das Einspielen überschreibt bestehende
					Einstellungen ohne weitere Rückfrage.
				</div>
				<div class="alert alert-danger small mb-0">
					<i class="fa fa-lock mr-1"></i>
					<strong>Passwörter werden niemals gesichert.</strong>
					Nach dem Einspielen müssen E-Mail-Passwörter manuell eingetragen werden.
					Neu angelegte Nutzer müssen ihr Passwort über <em>„Passwort vergessen"</em>
					selbst setzen.
				</div>
			</div>
		`;
	}

	html_card(key, title, icon, description) {
		return `
			<div class="frappe-card mb-3 p-4">
				<h5 class="mb-1">
					<i class="fa ${icon} mr-2 text-muted"></i>${title}
				</h5>
				<p class="text-muted small mb-3">${description}</p>
				<div class="mb-3 small text-muted">
					Letzte Sicherung: <strong id="ts-${key}">–</strong>
				</div>
				<button
					class="btn btn-sm btn-primary mr-2 btn-vepro-action"
					data-action="backup"
					data-key="${key}"
				>
					<i class="fa fa-cloud-download mr-1"></i>Jetzt sichern
				</button>
				<button
					class="btn btn-sm btn-warning btn-vepro-action"
					data-action="restore"
					data-key="${key}"
					disabled
				>
					<i class="fa fa-cloud-upload mr-1"></i>Einspielen
				</button>
			</div>
		`;
	}

	load_status() {
		frappe.call({
			method: "sut_vepro_testsetup_app.api.get_backup_status",
			callback: (r) => {
				if (!r.message) return;
				Object.entries(r.message).forEach(([key, info]) => {
					if (info.exists) {
						$(`#ts-${key}`).text(info.modified);
						$(`.btn-vepro-action[data-action="restore"][data-key="${key}"]`).prop(
							"disabled",
							false
						);
					} else {
						$(`#ts-${key}`).text("Keine Sicherung vorhanden");
						$(`.btn-vepro-action[data-action="restore"][data-key="${key}"]`).prop(
							"disabled",
							true
						);
					}
				});
			},
		});
	}

	bind_events() {
		$(this.body).on("click", ".btn-vepro-action", (e) => {
			const $btn = $(e.currentTarget);
			const action = $btn.data("action");
			const key = $btn.data("key");

			if (action === "restore") {
				frappe.confirm(
					__(
						"Die aktuellen Einstellungen werden mit der gesicherten Version überschrieben. Fortfahren?"
					),
					() => this.call_api(action, key, $btn)
				);
			} else {
				this.call_api(action, key, $btn);
			}
		});
	}

	call_api(action, key, $btn) {
		const method = `sut_vepro_testsetup_app.api.${action}_${key}`;
		const orig_html = $btn.html();
		const re_enable = () => $btn.prop("disabled", false).html(orig_html);

		$btn.prop("disabled", true).html(
			'<i class="fa fa-spinner fa-spin mr-1"></i>Läuft...'
		);

		frappe.call({
			method: method,
			callback: (r) => {
				re_enable();
				if (r.message && r.message.message) {
					frappe.show_alert({ message: r.message.message, indicator: "green" }, 5);
				}
				this.load_status();
			},
			error: () => {
				re_enable();
			},
		});
	}
}
