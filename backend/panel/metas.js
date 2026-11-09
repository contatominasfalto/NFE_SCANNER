/* Planejamento independente de notas e relatórios. Valores em toneladas. */
(() => {
    const state = { tipo: "expedicao", saved: [], record: null, draft: null, editing: false, dirty: false, busy: false };
    const fields = ["meta_a1br", "meta_a2br", "ajuste_a1br", "ajuste_a2br"];
    const labels = { meta_a1br: "Meta A1BR", meta_a2br: "Meta A2BR", ajuste_a1br: "Ajuste A1BR", ajuste_a2br: "Ajuste A2BR" };
    const title = () => state.tipo === "expedicao" ? "Expedição" : "Recebimento";
    const activeFields = () => state.tipo === "expedicao" ? fields.slice(0, 2) : fields;
    const canWrite = () => !!currentUser?.permissions?.modules?.metas && !!currentUser?.permissions?.actions?.operate;
    const periodKey = month => `${month.ano}-${String(month.mes).padStart(2, "0")}`;
    const periodLabel = month => `${String(month.mes).padStart(2, "0")}/${month.ano}`;
    const dayLabel = value => value.split("-").reverse().join("/");
    const clone = value => JSON.parse(JSON.stringify(value));

    // Usar milésimos inteiros evita erros de soma de ponto flutuante.
    function parseTon(value, allowNegative = false) {
        let text = String(value ?? "").trim();
        if (!text) return null;
        if (text.includes(",")) {
            if (!/^-?(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,3}$/.test(text)) throw new Error("Use até três casas decimais, por exemplo 1.234,567.");
            text = text.replaceAll(".", "").replace(",", ".");
        }
        if (!/^-?\d+(?:\.\d{1,3})?$/.test(text)) throw new Error("Informe um número em toneladas com até três casas decimais.");
        const negative = text.startsWith("-");
        const [whole, fraction = ""] = text.replace(/^-/, "").split(".");
        let milli = BigInt(whole) * 1000n + BigInt(fraction.padEnd(3, "0"));
        if (negative) milli = -milli;
        if (!allowNegative && milli < 0n) throw new Error("A meta não pode ser negativa.");
        if (milli > 999999999999999n || milli < -999999999999999n) throw new Error("O valor máximo é 999.999.999.999,999 toneladas.");
        const abs = milli < 0n ? -milli : milli;
        return `${milli < 0n ? "-" : ""}${abs / 1000n}.${String(abs % 1000n).padStart(3, "0")}`;
    }

    function milliTon(value) {
        const text = String(value ?? "0");
        const [whole, fraction = ""] = text.replace(/^-/, "").split(".");
        const result = BigInt(whole) * 1000n + BigInt(fraction.padEnd(3, "0"));
        return text.startsWith("-") ? -result : result;
    }

    function formatMilli(value) {
        const absolute = value < 0n ? -value : value;
        return `${value < 0n ? "-" : ""}${new Intl.NumberFormat("pt-BR").format(absolute / 1000n)},${String(absolute % 1000n).padStart(3, "0")}`;
    }

    function message(text = "", error = false) {
        $("metasMessage").textContent = text;
        $("metasMessage").classList.toggle("error", error);
    }

    async function request(path, options = {}) {
        const response = await fetch(path, { ...options, credentials: "include", headers: { "Content-Type": "application/json", ...options.headers } });
        let data;
        try { data = await response.json(); } catch { throw new Error("Não foi possível interpretar a resposta do servidor."); }
        if (!response.ok) {
            let detail = data.detail;
            if (Array.isArray(detail)) detail = detail.map(item => `${(item.loc || []).slice(1).join(".")}: ${item.msg}`).join("; ");
            const error = new Error(detail || `Erro ${response.status}`);
            error.status = response.status;
            throw error;
        }
        return data;
    }

    function setBusy(busy) {
        state.busy = busy;
        $("metasModalSection").setAttribute("aria-busy", String(busy));
        $("metasDialog").querySelectorAll("button,input,select").forEach(element => {
            element.disabled = busy || (element.matches("[data-meta-field]") && !state.editing);
        });
    }

    function confirmMeta(title, text) {
        return new Promise(resolve => {
            confirm(title, text, () => resolve(true));
            $("confirmDialog").addEventListener("close", () => resolve(false), { once: true });
        });
    }

    async function discardChanges() {
        return !state.dirty || await confirmMeta("Descartar alterações?", "Existem alterações não salvas. Deseja descartá-las?");
    }

    function showActions() {
        const writable = canWrite();
        $("metasNewForm").hidden = !writable;
        $("metasEdit").hidden = !writable || !state.record || state.editing;
        $("metasDelete").hidden = !writable || !state.record || state.editing;
        $("metasSave").hidden = !writable || !state.editing;
        $("metasCancel").hidden = !state.editing;
        $("metasDirty").textContent = state.dirty ? "Alterações não salvas" : "";
    }

    function updateTotals() {
        if (!state.draft) return;
        const totals = Object.fromEntries(fields.map(field => [field, 0n]));
        let valid = true;
        for (const input of $("metasTableBody").querySelectorAll("[data-meta-field]")) {
            try {
                const field = input.dataset.metaField;
                const value = parseTon(input.value, field.startsWith("ajuste"));
                input.setAttribute("aria-invalid", "false");
                totals[field] += milliTon(value);
            } catch {
                input.setAttribute("aria-invalid", "true");
                valid = false;
            }
        }
        for (const field of activeFields()) $("metasTotal_" + field).textContent = valid ? formatMilli(totals[field]) : "Valor inválido";
        $("metasTotalGeral").textContent = valid ? formatMilli(totals.meta_a1br + totals.meta_a2br) : "—";
        if (state.tipo === "recebimento") $("metasAjusteGeral").textContent = valid ? formatMilli(totals.ajuste_a1br + totals.ajuste_a2br) : "—";
        showActions();
    }

    function render() {
        $("metasTitle").textContent = `Meta ${title()}`;
        $("metasTableWrap").hidden = !state.draft;
        $("metasEmpty").hidden = !!state.draft;
        $("metasTableBody").innerHTML = "";
        if (!state.draft) {
            $("metasStatus").textContent = "Selecione um mês cadastrado ou crie um planejamento.";
            showActions();
            return;
        }
        const { ano, mes, dias } = state.draft;
        $("metasCaption").textContent = `${title()} · ${periodLabel({ ano, mes })} · valores em toneladas`;
        $("metasStatus").textContent = state.record
            ? `${periodLabel(state.record)} · Último salvamento: ${date(state.record.atualizado_em)} por ${state.record.atualizado_por}`
            : `${periodLabel({ ano, mes })} · Novo planejamento, ainda não salvo`;
        const receiving = state.tipo === "recebimento";
        $("metasHelp").textContent = `Valores em toneladas, com até três casas decimais (ex.: 1.234,567). Campos vazios representam dias sem meta.${receiving ? " Os ajustes podem ser positivos ou negativos e possuem total separado." : ""}${canWrite() ? "" : " Seu acesso permite somente consulta."}`;
        $("metasTableHead").innerHTML = `<tr><th rowspan="2" scope="col">Data</th><th colspan="2" scope="colgroup">Meta ${title()} (TON)</th>${receiving ? '<th colspan="2" scope="colgroup">Ajuste Recebimento (TON)</th>' : ""}${state.editing ? '<th rowspan="2" scope="col">Ações</th>' : ""}</tr><tr>${activeFields().map(field => `<th scope="col">${field.endsWith("a1br") ? "A1BR" : "A2BR"}</th>`).join("")}</tr>`;
        $("metasTableBody").innerHTML = dias.map((day, index) => `<tr><th scope="row">${dayLabel(day.data)}</th>${activeFields().map(field => `<td><input type="text" inputmode="decimal" autocomplete="off" data-meta-field="${field}" data-meta-day="${index}" aria-label="${labels[field]} em ${dayLabel(day.data)}" placeholder="—" value="${day[field] == null ? "" : esc(formatMilli(milliTon(day[field])))}" ${state.editing ? "" : "disabled"}></td>`).join("")}${state.editing ? `<td><button class="secondary metas-clear" type="button" data-clear-day="${index}" aria-label="Limpar valores de ${dayLabel(day.data)}">Limpar dia</button></td>` : ""}</tr>`).join("");
        $("metasTableFoot").innerHTML = `<tr><th scope="row">Total (TON)</th>${activeFields().map(field => `<td id="metasTotal_${field}"></td>`).join("")}${state.editing ? "<td></td>" : ""}</tr><tr><th scope="row">Total geral (TON)</th><td colspan="2" id="metasTotalGeral"></td>${receiving ? '<td colspan="2" id="metasAjusteGeral"></td>' : ""}${state.editing ? "<td></td>" : ""}</tr>`;
        updateTotals();
    }

    async function refreshMonths() {
        state.saved = await request(`/metas/${state.tipo}/meses/`);
        const selected = state.record ? periodKey(state.record) : "";
        $("metasSavedMonth").innerHTML = '<option value="">Selecione um mês</option>' + state.saved.map(month => `<option value="${periodKey(month)}">${periodLabel(month)}</option>`).join("");
        $("metasSavedMonth").value = selected;
    }

    async function loadMonth(key) {
        if (state.busy) return;
        if (!await discardChanges()) {
            $("metasSavedMonth").value = state.record ? periodKey(state.record) : "";
            return;
        }
        setBusy(true);
        message();
        try {
            if (key) {
                const [year, month] = key.split("-");
                const record = await request(`/metas/${state.tipo}/${year}/${Number(month)}/`);
                state.record = record;
                state.draft = clone(record);
                $("metasReference").value = key;
            } else { state.record = null; state.draft = null; }
            state.editing = false;
            state.dirty = false;
            $("metasSavedMonth").value = key;
            render();
        } catch (error) {
            $("metasSavedMonth").value = state.record ? periodKey(state.record) : "";
            message(error.message, true);
        } finally { setBusy(false); }
    }

    async function open(tipo) {
        if (!currentUser?.permissions?.modules?.metas) { toast("Acesso não autorizado.", true); return; }
        if (state.busy || !await discardChanges()) return;
        Object.assign(state, { tipo, record: null, draft: null, editing: false, dirty: false });
        message();
        render();
        if (!$("metasDialog").open) $("metasDialog").showModal();
        setModalMaximized("metasModalSection", true);
        const now = new Date();
        $("metasReference").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
        setBusy(true);
        try { await refreshMonths(); }
        catch (error) { message(error.message, true); }
        finally { setBusy(false); }
    }

    async function createMonth(event) {
        event.preventDefault();
        if (!canWrite() || state.busy || !$("metasNewForm").reportValidity()) return;
        const key = $("metasReference").value;
        if (state.saved.some(month => periodKey(month) === key)) { loadMonth(key); return; }
        if (!await discardChanges()) return;
        const [ano, mes] = key.split("-").map(Number);
        const days = new Date(ano, mes, 0).getDate();
        const dias = Array.from({ length: days }, (_, index) => ({ data: `${key}-${String(index + 1).padStart(2, "0")}`, ...Object.fromEntries(fields.map(field => [field, null])) }));
        Object.assign(state, { record: null, draft: { ano, mes, dias }, editing: true, dirty: true });
        $("metasSavedMonth").value = "";
        message();
        render();
    }

    async function save() {
        if (!canWrite() || !state.editing || !state.draft || state.busy) return;
        message();
        const dias = state.draft.dias.map(day => ({ ...day }));
        for (const input of $("metasTableBody").querySelectorAll("[data-meta-field]")) {
            try { dias[Number(input.dataset.metaDay)][input.dataset.metaField] = parseTon(input.value, input.dataset.metaField.startsWith("ajuste")); }
            catch (error) { message(`${input.getAttribute("aria-label")}: ${error.message}`, true); input.focus(); return; }
        }
        const payload = { ano: state.draft.ano, mes: state.draft.mes, dias };
        if (state.record) { payload.versao = state.record.versao; payload.id = state.record.id; }
        const path = state.record ? `/metas/${state.tipo}/${payload.ano}/${payload.mes}/` : `/metas/${state.tipo}/`;
        setBusy(true);
        try {
            const record = await request(path, { method: state.record ? "PUT" : "POST", body: JSON.stringify(payload) });
            Object.assign(state, { record, draft: clone(record), editing: false, dirty: false });
            render();
            message("Metas salvas com sucesso e registradas na rastreabilidade.");
            try { await refreshMonths(); }
            catch { message("Metas salvas. Não foi possível atualizar a lista; use Atualizar lista.", true); }
        } catch (error) { message(error.message, true); }
        finally { setBusy(false); }
    }

    async function remove() {
        if (!canWrite() || !state.record || state.busy) return;
        if (!await confirmMeta("Excluir planejamento mensal?", `Excluir todas as metas de ${title()} de ${periodLabel(state.record)}? A exclusão ficará registrada na rastreabilidade.`)) return;
        setBusy(true);
        message();
        try {
            const month = state.record;
            await request(`/metas/${state.tipo}/${month.ano}/${month.mes}/?versao=${month.versao}&id=${month.id}`, { method: "DELETE" });
            Object.assign(state, { record: null, draft: null, editing: false, dirty: false });
            render();
            message("Planejamento excluído e registrado na rastreabilidade.");
            try { await refreshMonths(); } catch { message("Mês excluído. Atualize a lista de meses.", true); }
        } catch (error) { message(error.message, true); }
        finally { setBusy(false); }
    }

    async function close() {
        if (state.busy || !await discardChanges()) return;
        state.dirty = false;
        $("metasDialog").close();
        setModalMaximized("metasModalSection", false);
    }

    $("metasMenuToggle").addEventListener("click", () => {
        if (document.body.classList.contains("sidebar-collapsed")) setSidebarCollapsed(false);
        const expanded = $("metasMenuToggle").getAttribute("aria-expanded") !== "true";
        $("metasMenuToggle").setAttribute("aria-expanded", String(expanded));
        $("metasSubmenu").hidden = !expanded;
        $("metasMenu").classList.toggle("open", expanded);
    });
    $("openMetasExpedicao").addEventListener("click", () => open("expedicao"));
    $("openMetasRecebimento").addEventListener("click", () => open("recebimento"));
    $("metasNewForm").addEventListener("submit", createMonth);
    $("metasSavedMonth").addEventListener("change", event => loadMonth(event.target.value));
    $("metasReload").addEventListener("click", async () => {
        if (state.busy) return;
        setBusy(true);
        try { await refreshMonths(); message("Lista atualizada. Selecione o mês para recarregar os valores salvos."); }
        catch (error) { message(error.message, true); }
        finally { setBusy(false); }
    });
    $("metasEdit").addEventListener("click", () => {
        if (!canWrite() || !state.record || state.busy) return;
        state.draft = clone(state.record); state.editing = true; state.dirty = false;
        message(); render();
    });
    $("metasCancel").addEventListener("click", async () => {
        if (state.busy || !await discardChanges()) return;
        state.draft = state.record ? clone(state.record) : null;
        state.editing = false; state.dirty = false;
        message(); render();
    });
    $("metasSave").addEventListener("click", save);
    $("metasDelete").addEventListener("click", remove);
    $("metasClose").addEventListener("click", close);
    $("metasFooterClose").addEventListener("click", close);
    $("metasDialog").addEventListener("cancel", event => { event.preventDefault(); close(); });
    $("metasTableBody").addEventListener("input", event => {
        if (event.target.matches("[data-meta-field]") && state.editing) { state.dirty = true; updateTotals(); }
    });
    $("metasTableBody").addEventListener("focusout", event => {
        const input = event.target;
        if (!input.matches("[data-meta-field]") || !state.editing) return;
        try { const value = parseTon(input.value, input.dataset.metaField.startsWith("ajuste")); input.value = value === null ? "" : formatMilli(milliTon(value)); } catch { /* Mantém o valor para correção. */ }
    });
    $("metasTableBody").addEventListener("click", event => {
        const button = event.target.closest("[data-clear-day]");
        if (!button || !state.editing || state.busy) return;
        $("metasTableBody").querySelectorAll(`[data-meta-day="${button.dataset.clearDay}"]`).forEach(input => { input.value = ""; });
        state.dirty = true; updateTotals();
    });
    window.addEventListener("beforeunload", event => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } });
})();
