// Project form: stages, team and publishing (phase 2, task 3).
const ADMIN_API = "construction_core.api.admin";

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new()) return;
		construction.render_stages(frm);
		construction.add_buttons(frm);
	},
});

window.construction = window.construction || {};

construction.render_stages = function (frm) {
	const field = frm.get_field("stages_html");
	if (!field) return;
	frappe.call(`${ADMIN_API}.get_project_stages`, { project: frm.doc.name }).then(({ message }) => {
		const { stages, total_weight, ok } = message;
		const esc = frappe.utils.escape_html;
		const rows = stages
			.map(
				(s, i) => `
			<tr data-stage="${esc(s.name)}">
				<td>${i + 1}</td>
				<td><a href="/app/project-stage/${encodeURIComponent(s.name)}">${esc(s.stage_name)}</a></td>
				<td class="text-right">${format_number(s.weight, null, 2)}</td>
				<td class="text-right">${format_number(s.progress, null, 0)}%</td>
				<td>${esc(__(s.status))}</td>
				<td>${s.planned_start ? frappe.datetime.str_to_user(s.planned_start) : ""}</td>
				<td>${s.planned_end ? frappe.datetime.str_to_user(s.planned_end) : ""}</td>
				<td class="text-nowrap">
					<button class="btn btn-xs btn-default stage-move" data-dir="up" ${i === 0 ? "disabled" : ""} title="${__("Move up")}">↑</button>
					<button class="btn btn-xs btn-default stage-move" data-dir="down" ${i === stages.length - 1 ? "disabled" : ""} title="${__("Move down")}">↓</button>
				</td>
			</tr>`
			)
			.join("");
		const warning = ok
			? ""
			: `<div class="alert alert-warning">${__("Stage weights add up to {0}, not 100.", [total_weight])}</div>`;
		field.$wrapper.html(`
			${warning}
			<table class="table table-bordered table-sm">
				<thead><tr>
					<th>#</th><th>${__("المرحلة")}</th><th class="text-right">${__("الوزن")}</th>
					<th class="text-right">${__("الإنجاز")}</th><th>${__("الحالة")}</th>
					<th>${__("بداية")}</th><th>${__("نهاية")}</th><th></th>
				</tr></thead>
				<tbody>${rows || `<tr><td colspan="8" class="text-muted">${__("مفيش مراحل لسه")}</td></tr>`}</tbody>
				<tfoot><tr><td></td><td>${__("المجموع")}</td><td class="text-right">${format_number(total_weight, null, 2)}</td><td colspan="5"></td></tr></tfoot>
			</table>
			<button class="btn btn-sm btn-default stage-add">${__("+ إضافة مرحلة")}</button>
		`);
		field.$wrapper.find(".stage-move").on("click", function () {
			const stage = $(this).closest("tr").data("stage");
			frappe
				.call(`${ADMIN_API}.move_stage`, { stage, direction: $(this).data("dir") })
				.then(() => construction.render_stages(frm));
		});
		field.$wrapper.find(".stage-add").on("click", () => {
			frappe.new_doc("Project Stage", {
				project: frm.doc.name,
				sort_order: stages.length + 1,
			});
		});
	});
};

construction.add_buttons = function (frm) {
	frm.add_custom_button(__("إضافة عميل"), () => construction.add_client_dialog(frm), __("الفريق"));
	frm.add_custom_button(__("إضافة مهندس"), () => construction.add_engineer_dialog(frm), __("الفريق"));
	frm.add_custom_button(__("لينك جديد"), () => construction.new_link(frm), __("النشر"));
	frm.add_custom_button(__("معاينة بعين الزائر"), () => window.open(`/p/${frm.doc.name}`, "_blank"), __("النشر"));
};

construction.add_client_dialog = function (frm) {
	const d = new frappe.ui.Dialog({
		title: __("إضافة عميل"),
		fields: [
			{ fieldname: "full_name", fieldtype: "Data", label: __("الاسم"), reqd: 1 },
			{
				fieldname: "mobile",
				fieldtype: "Data",
				label: __("الموبايل"),
				reqd: 1,
				description: __("موبايل مصري: 11 رقم يبدأ بـ 010 أو 011 أو 012 أو 015"),
			},
			{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("الإيميل (اختياري)") },
			{
				fieldname: "username",
				fieldtype: "Data",
				label: __("اسم المستخدم"),
				depends_on: "eval:!doc.email",
				mandatory_depends_on: "eval:!doc.email",
				description: __("حروف إنجليزي صغيرة وأرقام، مثلاً ahmed.hassan"),
			},
		],
		primary_action_label: __("إضافة"),
		primary_action(values) {
			if (!/^01[0125][0-9]{8}$/.test((values.mobile || "").replace(/[\s-]/g, ""))) {
				frappe.msgprint(__("Mobile number must be an Egyptian mobile like 01xxxxxxxxx"));
				return;
			}
			frappe
				.call({ method: `${ADMIN_API}.add_client`, args: { project: frm.doc.name, ...values }, freeze: true })
				.then(({ message }) => {
					d.hide();
					frm.reload_doc();
					if (message.temp_password) {
						construction.show_credentials(message);
					} else {
						frappe.show_alert({ message: __("اتضاف العميل واتبعتله إيميل يحدد فيه كلمة السر"), indicator: "green" });
					}
				});
		},
	});
	d.show();
};

construction.show_credentials = function (m) {
	const esc = frappe.utils.escape_html;
	const d = new frappe.ui.Dialog({
		title: __("بيانات الدخول (بتظهر مرة واحدة بس)"),
		fields: [
			{
				fieldtype: "HTML",
				options: `
				<p>${__("رابط الدخول")}: <b dir="ltr">${esc(m.login_url)}</b></p>
				<p>${__("اسم المستخدم")}: <b dir="ltr">${esc(m.username)}</b></p>
				<p>${__("كلمة السر المؤقتة")}: <b dir="ltr" style="font-family:monospace">${esc(m.temp_password)}</b></p>
				<p class="text-muted">${__("أول ما يدخل هيطلب منه يغيّرها.")}</p>`,
			},
		],
		primary_action_label: __("إرسال على واتساب"),
		primary_action() {
			window.open(m.whatsapp_url, "_blank");
		},
	});
	d.show();
};

construction.add_engineer_dialog = function (frm) {
	const d = new frappe.ui.Dialog({
		title: __("إضافة مهندس"),
		fields: [
			{
				fieldname: "user",
				fieldtype: "Link",
				options: "User",
				label: __("المهندس"),
				reqd: 1,
				get_query: () => ({
					query: "construction_core.api.admin.engineer_query",
				}),
			},
		],
		primary_action_label: __("إضافة"),
		primary_action(values) {
			frappe.call(`${ADMIN_API}.add_engineer`, { project: frm.doc.name, user: values.user }).then(() => {
				d.hide();
				frm.reload_doc();
			});
		},
	});
	d.show();
};

construction.new_link = function (frm) {
	frappe.confirm(__("اللينك القديم هيبطل يشتغل. تكمّل؟"), () => {
		frappe.call(`${ADMIN_API}.new_share_link`, { project: frm.doc.name }).then(({ message }) => {
			frm.reload_doc();
			const d = new frappe.ui.Dialog({
				title: __("اللينك الجديد (بيظهر مرة واحدة بس)"),
				fields: [{ fieldtype: "Code", fieldname: "url", read_only: 1, default: message.url }],
				primary_action_label: __("نسخ اللينك"),
				primary_action() {
					frappe.utils.copy_to_clipboard(message.url);
				},
			});
			d.show();
		});
	});
};
