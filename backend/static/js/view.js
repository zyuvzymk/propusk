const requestId = window.requestId;

const viewCompany = document.getElementById("viewCompany");
const viewObject = document.getElementById("viewObject");
const viewWork = document.getElementById("viewWork");
const viewManager = document.getElementById("viewManager");
const viewRole = document.getElementById("viewRole");
const viewContacts = document.getElementById("viewContacts");
const viewPeriod = document.getElementById("viewPeriod");
const viewAuditContainer = document.getElementById("viewAuditContainer");
const auditSection = document.getElementById("auditSection");
const visitorsTableBody = document.getElementById("visitorsTableBody");
const approveRequestBtn = document.getElementById("approveRequestBtn");
const rejectRequestBtn = document.getElementById("rejectRequestBtn");
const returnToPendingBtn = document.getElementById("returnToPendingBtn");
const changeDatesBtn = document.getElementById("changeDatesBtn");
const datesModal = document.getElementById("datesModal");
const modalStartDate = document.getElementById("modalStartDate");
const modalEndDate = document.getElementById("modalEndDate");
const closeModalBtn = document.getElementById("closeModalBtn");
const applyDatesBtn = document.getElementById("applyDatesBtn");
const rejectModal = document.getElementById("rejectModal");
const rejectReason = document.getElementById("rejectReason");
const closeRejectModalBtn = document.getElementById("closeRejectModalBtn");
const submitRejectBtn = document.getElementById("submitRejectBtn");
const actionButtonsBlock = document.getElementById("actionButtonsBlock");

const blankCompany = document.getElementById("blankCompany");
const blankObject = document.getElementById("blankObject");
const blankPeriod = document.getElementById("blankPeriod");
const blankVisitorsContainer = document.getElementById("blankVisitorsContainer");

const openFullRequestBtn = document.getElementById("openFullRequestBtn");
const fullRequestModal = document.getElementById("fullRequestModal");
const closeFullRequestBtn = document.getElementById("closeFullRequestBtn");
const fullRequestContent = document.getElementById("fullRequestContent");

let originalData = null;
let excludedVisitorIds = new Set();
let pedestrianVisitorIds = new Set();
let currentStartDateIso = null;
let currentEndDateIso = null;
let auditInfo = null;
let userRole = null;

function formatDateOnly(dateStr) {
    if (!dateStr) return "—";
    const d = new Date(dateStr);
    return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function parseCompositePurpose(purposeStr) {
    const result = { object: "—", work: "—", manager: "—", role: "—", phone: "—", email: "—" };
    if (!purposeStr) return result;
    try {
        const auditMatch = purposeStr.match(/\[Обработал:\s*([^\]]+)\]/);
        if (auditMatch) {
            auditInfo = auditMatch[1].trim();
            purposeStr = purposeStr.replace(auditMatch[0], "").trim();
        }
        if (purposeStr.includes("Объект:") && purposeStr.includes("Работы:")) {
            const parts = purposeStr.split("|");
            parts.forEach(p => {
                const cleanTxt = p.trim();
                if (cleanTxt.startsWith("Объект:")) result.object = cleanTxt.substring(7).trim();
                if (cleanTxt.startsWith("Работы:")) result.work = cleanTxt.substring(7).trim();
                if (cleanTxt.startsWith("Ответственный:")) {
                    let mField = cleanTxt.substring(14).trim();
                    if (mField.includes("(")) {
                        const subParts = mField.split("(");
                        result.manager = subParts[0].trim();
                        result.role = subParts[1].replace(")", "").trim();
                    } else { result.manager = mField; result.role = "Инженер"; }
                }
            });
            const phoneMatch = purposeStr.match(/Тел:\s*([^,;|]+)/);
            if (phoneMatch) result.phone = phoneMatch[1].trim();
            const emailMatch = purposeStr.match(/Email:\s*([^,;|]+)/);
            if (emailMatch) result.email = emailMatch[1].trim();
        } else {
            result.object = "Временный допуск"; result.work = purposeStr;
            if (purposeStr.includes("Ответственный:")) {
                const idx = purposeStr.indexOf("Ответственный:");
                let sub = purposeStr.substring(idx + 14).trim();
                if (sub.includes("|")) sub = sub.split("|")[0].trim();
                if (sub.includes(",")) sub = sub.split(",")[0].trim();
                if (sub.includes("(")) {
                    const parts = sub.split("(");
                    result.manager = parts[0].trim();
                    result.role = parts[1].replace(")", "").trim();
                } else { result.manager = sub; result.role = "Руководитель"; }
            }
        }
    } catch (e) { result.object = "Временный допуск"; }
    if (result.manager && result.manager !== "—") {
        const arr = result.manager.split(/\s+/);
        if (arr.length >= 3) result.manager = arr[0] + " " + arr[1][0] + ". " + arr[2][0] + ".";
        else if (arr.length === 2) result.manager = arr[0] + " " + arr[1][0] + ".";
    }
    return result;
}

async function fetchRequestDetails() {
    try {
        const response = await fetch("/api/admin/requests/" + requestId, { credentials: "include" });
        if (response.status === 401 || response.status === 403) { window.location.href = "/login"; return; }
        if (!response.ok) throw new Error("Ошибка загрузки заявки");
        originalData = await response.json();

        originalData.visitors.forEach(v => {
            if (v.is_pedestrian) pedestrianVisitorIds.add(v.id);
            if (v.is_excluded) excludedVisitorIds.add(v.id);
        });

        const parsed = parseCompositePurpose(originalData.purpose);
        currentStartDateIso = originalData.start_date;
        currentEndDateIso = originalData.end_date;

        viewCompany.innerText = originalData.company_name;
        viewObject.innerText = parsed.object;
        viewWork.innerText = parsed.work;
        viewManager.innerText = parsed.manager;
        viewRole.innerText = parsed.role;
        viewContacts.innerText = `${parsed.phone !== "—" ? parsed.phone : "—"} / ${parsed.email !== "—" ? parsed.email : "—"}`;
        viewPeriod.innerText = `${formatDateOnly(originalData.start_date)} по ${formatDateOnly(originalData.end_date)}`;

        if (userRole === "Администратор" && auditInfo) {
            auditSection.classList.remove("hidden");
            viewAuditContainer.innerHTML = `<div class="audit-entry">${auditInfo}</div>`;
        } else {
            auditSection.classList.add("hidden");
        }

        if (userRole === "Охрана") {
            actionButtonsBlock.style.display = "none";
            changeDatesBtn.style.display = "none";
        }

        if (userRole === "Администратор" && (originalData.status === "Одобрен" || originalData.status === "Отклонен")) {
            returnToPendingBtn.classList.remove("hidden");
        } else {
            returnToPendingBtn.classList.add("hidden");
        }

        blankCompany.innerText = originalData.company_name;
        blankObject.innerText = parsed.object;
        blankPeriod.innerText = `${formatDateOnly(originalData.start_date)} по ${formatDateOnly(originalData.end_date)}`;

        // === ИНДИКАТОР ДАТ ===
        const datesWarn = document.getElementById("datesWarnIndicatorPreview");
        if (originalData.dates_changed) {
            datesWarn.style.display = "inline-block";
        } else {
            datesWarn.style.display = "none";
        }

        renderVisitorsPreview(originalData.visitors);
        renderVisitorsTable(originalData.visitors);
        blockInteractiveElements();
    } catch (err) {
        alert("Ошибка загрузки данных: " + err.message);
    }
}

function renderVisitorsPreview(visitors) {
    if (!visitors || visitors.length === 0) {
        blankVisitorsContainer.innerHTML = "<p style='margin: 2px 0; color: #94a3b8;'>Нет посетителей</p>";
        return;
    }
    let html = "";
    visitors.forEach(v => {
        if (excludedVisitorIds.has(v.id)) return;
        const isPedestrian = pedestrianVisitorIds.has(v.id);
        let transport = isPedestrian ? "ПЕШКОМ" : (originalData.car_info || "—");
        if (isPedestrian) {
            transport = `<span style="color: #dc2626; font-weight: 700;">ПЕШКОМ</span>`;
        }
        html += `<p style="margin: 2px 0; font-size: 11px;">${v.full_name} (Паспорт: ${v.passport_series || ""} ${v.passport_number || ""}) / ${transport}</p>`;
    });
    blankVisitorsContainer.innerHTML = html;
}

function renderVisitorsTable(visitors) {
    if (!visitors || visitors.length === 0) {
        visitorsTableBody.innerHTML = "<tr><td colspan='4' style='text-align:center; color:#94a3b8;'>Нет посетителей</td></tr>";
        return;
    }
    let html = "";
    const isSecurity = userRole === "Охрана";
    const disabledAttr = isSecurity ? 'disabled style="opacity:0.6; cursor:not-allowed;"' : '';

    visitors.forEach(v => {
        const isExcluded = excludedVisitorIds.has(v.id);
        const isPedestrian = pedestrianVisitorIds.has(v.id);
        const vBtnText = isExcluded ? "Вернуть" : "Исключить";
        const vBtnClass = isExcluded ? "success" : "danger";
        const carBtnText = isPedestrian ? "Авто" : "Пешком";
        let transportDisplay = originalData.car_info || "—";
        if (isPedestrian) {
            transportDisplay = `<span style="text-decoration: line-through; color: #991b1b;">${transportDisplay}</span>`;
        }
        const isCarDisabled = !originalData.car_info ? "disabled" : "";

        html += `<tr class="${isExcluded ? 'excluded-row' : ''}">
            <td>${v.full_name}</td>
            <td>${v.passport_series || ""} ${v.passport_number || ""}</td>
            <td>${transportDisplay}</td>
            <td style="white-space:nowrap; text-align:center; vertical-align:middle;">
                <div class="action-cell-inner">
                    <button class="table-btn-action ${vBtnClass} toggle-v-btn" data-v-id="${v.id}" ${disabledAttr}>${vBtnText}</button>
                    <button class="table-btn-action toggle-car-btn" data-v-id="${v.id}" ${isCarDisabled} ${disabledAttr}>${carBtnText}</button>
                </div>
            </td>
        </tr>`;
    });
    visitorsTableBody.innerHTML = html;
}

function renderFullRequest() {
    if (!originalData) return;
    const parsed = parseCompositePurpose(originalData.purpose);

    let tableRows = "";
    let index = 1;
    originalData.visitors.forEach(v => {
        if (excludedVisitorIds.has(v.id)) return;
        const isPedestrian = pedestrianVisitorIds.has(v.id);
        let transport = isPedestrian ? "ПЕШКОМ" : (originalData.car_info || "—");
        if (isPedestrian) {
            transport = `<span style="color: #dc2626; font-weight: 700;">ПЕШКОМ</span>`;
        }
        const passport = `${v.passport_series || ""} ${v.passport_number || ""}`.trim() || "—";
        tableRows += `<tr>
            <td style="border: 1px solid #000; padding: 4px; text-align: center;">${index}</td>
            <td style="border: 1px solid #000; padding: 4px;">${v.full_name}</td>
            <td style="border: 1px solid #000; padding: 4px; text-align: center;">${v.position || "—"}</td>
            <td style="border: 1px solid #000; padding: 4px; text-align: center;">${passport}</td>
            <td style="border: 1px solid #000; padding: 4px; text-align: center;">${transport}</td>
            <td style="border: 1px solid #000; padding: 4px; text-align: center;">_________________</td>
        </tr>`;
        index++;
    });
    const tableHtml = tableRows || "<tr><td colspan='6' style='text-align:center; color:#94a3b8;'>Нет посетителей</td></tr>";

    fullRequestContent.innerHTML = `
        <style>
            table { width: 100%; border-collapse: collapse; margin: 1em 0; }
            th, td { border: 1px solid #000; padding: 6px 8px; text-align: left; vertical-align: top; }
            th { background: #f0f0f0; font-weight: bold; }
            strong { font-weight: bold; }
            p { margin: 0.5em 0; }
        </style>
        <table style="width: 100%; border-collapse: collapse; border: none;">
            <colgroup>
                <col style="width: 50%;">
                <col style="width: 50%;">
            </colgroup>
            <thead>
                <tr>
                    <th style="border: none; padding: 4px 0;"><strong>Проход/проезд разрешен</strong></th>
                    <th style="border: none; text-align: right; padding: 4px 0;">
                        <p style="margin: 0;">Форма утверждена 04.08.2025</p>
                        <p style="margin: 0;">ООО «Поморская Судоверфь»</p>
                    </th>
                </tr>
                <tr>
                    <th style="border: none; padding: 4px 0;" colspan="2"><strong>Управляющий __________________ Е.П. Пеньевской</strong></th>
                </tr>
            </thead>
        </table>
        <p style="font-size: 18px; font-weight: bold; text-align: center; margin: 12px 0;">ЗАЯВКА НА ПРОПУСК</p>
        <p><strong>От:</strong> ${originalData.company_name}</p>
        <p><strong>Подрядчик/субподрядчик:</strong> ${originalData.contractor || "—"}</p>
        <p><strong>Объект(ы):</strong> ${parsed.object}</p>
        <p><strong>Период проведения работ:</strong> с ${formatDateOnly(originalData.start_date)} по ${formatDateOnly(originalData.end_date)}</p>
        <p><strong>Допуск на территорию:</strong> с 08.00 МСК по 18.00 МСК</p>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px;">
            <colgroup>
                <col style="width: 6%;">
                <col style="width: 26%;">
                <col style="width: 13%;">
                <col style="width: 22%;">
                <col style="width: 16%;">
                <col style="width: 14%;">
            </colgroup>
            <thead>
                <tr>
                    <th style="border: 1px solid #000; padding: 4px; text-align: center;"><strong>№ П/П</strong></th>
                    <th style="border: 1px solid #000; padding: 4px;"><strong>ФАМИЛИЯ ИМЯ ОТЧЕСТВО</strong></th>
                    <th style="border: 1px solid #000; padding: 4px; text-align: center;"><strong>ДОЛЖНОСТЬ</strong></th>
                    <th style="border: 1px solid #000; padding: 4px; text-align: center;"><strong>ДОКУМЕНТ, СЕРИЯ, НОМЕР</strong></th>
                    <th style="border: 1px solid #000; padding: 4px; text-align: center;"><strong>ТРАНСПОРТ</strong></th>
                    <th style="border: 1px solid #000; padding: 4px; text-align: center;"><strong>ПОДПИСЬ</strong></th>
                </tr>
            </thead>
            <tbody>${tableHtml}</tbody>
        </table>
        <p style="margin: 8px 0;">Подачей настоящей заявки подтверждаем, что:</p>
        <p style="margin: 2px 0 2px 20px;">1. Персональные данные получены лично от их владельцев.</p>
        <p style="margin: 2px 0 2px 20px;">2. Письменные согласия на передачу персональных данных в адрес операторов персональных данных филиала ООО «Поморская Судоверфь» и их обработку в целях организации пропускного режима на территорию ООО «Поморская Судоверфь» от лиц, перечисленных в заявке.</p>
        <p style="margin: 6px 0;"><strong>При нахождении указанных лиц на территории ООО «Поморская Судоверфь» несём ответственность за соблюдение ими Инструкции о пропускном и внутриобъектовом режиме на территории объекта, противопожарной безопасности, норм законодательства РФ об охране труда, об охране окружающей среды, правил дорожного движения.</strong></p>
        <p style="margin: 8px 0 2px 0;"><strong>Представитель организации, подавшей заявку:</strong></p>
        <p style="margin: 2px 0;">${parsed.manager || "—"} / ${parsed.role || "—"}</p>
        <p style="margin: 2px 0;"><strong>Тел.:</strong> ${parsed.phone || "—"}</p>
        <p style="margin: 2px 0;"><strong>E-mail:</strong> ${parsed.email || "—"}</p>
    `;
}

function blockInteractiveElements() {
    const isReadOnly = userRole !== "Администратор" && originalData && originalData.status !== "На рассмотрении";
    const elements = document.querySelectorAll("#changeDatesBtn, #approveRequestBtn, #rejectRequestBtn, .toggle-v-btn, .toggle-car-btn");
    elements.forEach(el => {
        if (isReadOnly) {
            el.disabled = true;
            el.title = "Изменение запрещено: заявка обработана";
        } else {
            el.disabled = false;
            el.title = "";
        }
    });
}

document.addEventListener("DOMContentLoaded", function() {
    fetch("/api/auth/me", { credentials: "include" })
        .then(r => r.json())
        .then(data => {
            userRole = data.role;
            fetchRequestDetails();
        })
        .catch(() => {
            userRole = "Гость";
            fetchRequestDetails();
        });

    visitorsTableBody.addEventListener("click", function(e) {
        if (userRole === "Охрана") return;

        if (e.target.classList.contains("toggle-v-btn")) {
            const vId = parseInt(e.target.dataset.vId);
            if (excludedVisitorIds.has(vId)) {
                excludedVisitorIds.delete(vId);
            } else {
                excludedVisitorIds.add(vId);
            }
            renderVisitorsTable(originalData.visitors);
            renderVisitorsPreview(originalData.visitors);
        }
        if (e.target.classList.contains("toggle-car-btn")) {
            const vId = parseInt(e.target.dataset.vId);
            if (pedestrianVisitorIds.has(vId)) {
                pedestrianVisitorIds.delete(vId);
            } else {
                pedestrianVisitorIds.add(vId);
            }
            renderVisitorsTable(originalData.visitors);
            renderVisitorsPreview(originalData.visitors);
        }
    });

    changeDatesBtn.addEventListener("click", function() {
        modalStartDate.value = currentStartDateIso ? currentStartDateIso.split("T")[0] : "";
        modalEndDate.value = currentEndDateIso ? currentEndDateIso.split("T")[0] : "";
        datesModal.style.display = "flex";
    });

    closeModalBtn.addEventListener("click", function() {
        datesModal.style.display = "none";
    });

    applyDatesBtn.addEventListener("click", function() {
        const start = modalStartDate.value;
        const end = modalEndDate.value;
        if (start && end && new Date(start) <= new Date(end)) {
            currentStartDateIso = start;
            currentEndDateIso = end;
            viewPeriod.innerText = `${formatDateOnly(start)} по ${formatDateOnly(end)}`;
            blankPeriod.innerText = `${formatDateOnly(start)} по ${formatDateOnly(end)}`;

            // === ПОКАЗЫВАЕМ ИНДИКАТОР СРАЗУ ===
            const datesWarn = document.getElementById("datesWarnIndicatorPreview");
            const origStart = originalData.start_date.split("T")[0];
            const origEnd = originalData.end_date.split("T")[0];
            if (start !== origStart || end !== origEnd) {
                datesWarn.style.display = "inline-block";
            } else {
                datesWarn.style.display = "none";
            }

            datesModal.style.display = "none";
            alert("Даты обновлены. Не забудьте сохранить изменения через 'Одобрить'.");
        } else {
            alert("Некорректный диапазон дат.");
        }
    });

    approveRequestBtn.addEventListener("click", function() {
        if (excludedVisitorIds.size === originalData.visitors.length) {
            alert("Нельзя утвердить пропуск, в котором исключены все посетители!");
            return;
        }
        let finalCarInfo = originalData.car_info;
        const updatePayload = {
            status: "Одобрен",
            start_date: currentStartDateIso,
            end_date: currentEndDateIso,
            car_info: finalCarInfo,
            comment: "Скорректировано оператором при согласовании",
            pedestrian_ids: Array.from(pedestrianVisitorIds),
            excluded_ids: Array.from(excludedVisitorIds)
        };
        fetch("/api/admin/requests/" + requestId, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updatePayload),
            credentials: "include"
        }).then(res => {
            if (!res.ok) throw new Error("Ошибка записи");
            alert("Параметры успешно зафиксированы. Пропуск одобрен.");
            window.location.href = "/dashboard";
        }).catch(err => alert("Критическая ошибка: " + err.message));
    });

    rejectRequestBtn.addEventListener("click", function() {
        rejectModal.style.display = "flex";
    });

    closeRejectModalBtn.addEventListener("click", function() {
        rejectModal.style.display = "none";
    });

    submitRejectBtn.addEventListener("click", function() {
        const reason = rejectReason.value.trim();
        const updatePayload = {
            status: "Отклонен",
            start_date: currentStartDateIso,
            end_date: currentEndDateIso,
            car_info: originalData.car_info,
            comment: reason || "Без указания причины",
            pedestrian_ids: Array.from(pedestrianVisitorIds),
            excluded_ids: Array.from(excludedVisitorIds)
        };
        fetch("/api/admin/requests/" + requestId, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updatePayload),
            credentials: "include"
        }).then(res => {
            if (!res.ok) throw new Error("Ошибка записи");
            alert("Заявка отклонена.");
            window.location.href = "/dashboard";
        }).catch(err => alert("Критическая ошибка: " + err.message));
    });

    returnToPendingBtn.addEventListener("click", function() {
        if (!confirm("Вернуть заявку на согласование?")) return;
        const updatePayload = {
            status: "На рассмотрении",
            start_date: currentStartDateIso,
            end_date: currentEndDateIso,
            car_info: originalData.car_info,
            comment: "Возвращено на согласование администратором",
            pedestrian_ids: Array.from(pedestrianVisitorIds),
            excluded_ids: Array.from(excludedVisitorIds)
        };
        fetch("/api/admin/requests/" + requestId, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updatePayload),
            credentials: "include"
        }).then(res => {
            if (!res.ok) throw new Error("Ошибка записи");
            alert("Заявка возвращена на согласование.");
            window.location.href = "/dashboard";
        }).catch(err => alert("Критическая ошибка: " + err.message));
    });
});

// ======== МОДАЛКА ЗАЯВКИ ========
openFullRequestBtn.addEventListener("click", function() {
    renderFullRequest();
    fullRequestModal.style.display = "flex";
});

closeFullRequestBtn.addEventListener("click", function() {
    fullRequestModal.style.display = "none";
});

fullRequestModal.addEventListener("click", function(e) {
    if (e.target === fullRequestModal) fullRequestModal.style.display = "none";
});
