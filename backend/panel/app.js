const $=id=>document.getElementById(id);let notes=[],faturistas=[],filtered=[],refreshing=false,confirmCallback=null,currentUser=null,tablePage=1,tablePageSize=100;
const SHOW_USER_FILTER=false;
const fields=["numero_nf","serie","data_emissao","cnpj_fornecedor","nome_fornecedor","valor_total","chave_acesso","local","produto","quantidade","transportador","faturista","lider_operacional","observacao"];
const money=v=>new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(v||0);
const date=v=>v?new Date(v).toLocaleString("pt-BR"):"—";const dateKey=v=>{if(!v)return"";const d=new Date(v);if(Number.isNaN(d.getTime()))return"";return`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`};const localDateKey=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
async function api(path,options={}){options.credentials="include";const r=await fetch(path,options);if(!r.ok){let m=`Erro ${r.status}`;try{m=(await r.json()).detail||m}catch{}throw new Error(m)}return r.headers.get("content-type")?.includes("json")?r.json():r}
function toast(message,error=false){const el=$("toast");el.textContent=message;el.className=error?"show error":"show";setTimeout(()=>el.className="",3200)}
function showLogin(message){$("loginError").textContent=message||"";document.body.classList.remove("authenticated");const dialog=$("loginDialog");if(!dialog.open){dialog.showModal();}}
function hideLogin(){document.body.classList.add("authenticated");const dialog=$("loginDialog");if(dialog.open){dialog.close();}$("loginError").textContent="";}
async function ensureAuthenticated(){try{currentUser=await api("/auth/me/");const isAdmin=currentUser.role==="admin",isViewer=currentUser.role==="viewer";$("userBadge").textContent=`${currentUser.username}${isAdmin?" (admin)":isViewer?" (viewer)":""}`;$("logoutButton").hidden=false;$("openNotes").hidden=false;$("mainPanel").hidden=false;$("openBatchScan").hidden=isViewer;$("downloadAll").hidden=isViewer;$("openFaturistas").hidden=!isAdmin;$("openAudit").hidden=!isAdmin;$("openSwagger").hidden=!isAdmin;$("refreshErrorsButton").hidden=isViewer;setDefaultBipRange();hideLogin();return true;}catch(err){currentUser=null;$("userBadge").textContent="";$("logoutButton").hidden=true;$("openNotes").hidden=false;$("mainPanel").hidden=false;$("openBatchScan").hidden=false;$("downloadAll").hidden=false;$("openFaturistas").hidden=true;$("openAudit").hidden=true;$("openSwagger").hidden=true;$("refreshErrorsButton").hidden=true;showLogin("");return false;}}
async function loginUser(){try{await api("/auth/login/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:$("loginUsername").value,password:$("loginPassword").value})});await ensureAuthenticated();setDefaultBipRange(true);await loadAll(true);}catch(err){$("loginError").textContent=err.message;}}
function configureOptionalFilters(){const billingFilter=$("billingFilter");if(billingFilter)billingFilter.hidden=!SHOW_USER_FILTER}
const NOTES_PAGE_SIZE=500;
function setDefaultBipRange(force=false){const start=$("bipStartDateFilter"),end=$("bipEndDateFilter");if(!start||!end||(!force&&(start.value||end.value)))return;const today=new Date();start.value=localDateKey(new Date(today.getFullYear(),today.getMonth(),1));end.value=localDateKey(today)}
function getDateRange(startId,endId,label,showMessage=true){const start=$(startId).value,end=$(endId).value;if(Boolean(start)!==Boolean(end)){if(showMessage)toast(`Informe data inicial e final para filtrar por ${label}.`,true);return false}if(start&&end&&start>end){if(showMessage)toast(`A data inicial de ${label} nao pode ser maior que a final.`,true);return false}return start&&end?{start,end}:null}
function inDateRange(value,range){const key=dateKey(value);return !range||Boolean(key&&key>=range.start&&key<=range.end)}
function buildBipQuery(skip,limit,showMessage=true){const range=getDateRange("bipStartDateFilter","bipEndDateFilter","Bip",showMessage);if(range===false)return null;const params=new URLSearchParams({skip:String(skip),limit:String(limit)});if(range){params.set("data_cadastro_inicio",`${range.start}T00:00:00`);params.set("data_cadastro_fim",`${range.end}T23:59:59`)}return params}
async function fetchAllNotes(showMessage=true){const all=[];let skip=0;while(true){const params=buildBipQuery(skip,NOTES_PAGE_SIZE,showMessage);if(!params)return null;const page=await api(`/notas/?${params.toString()}`);all.push(...page);if(page.length<NOTES_PAGE_SIZE)break;skip+=NOTES_PAGE_SIZE;}return all}
async function loadAll(silent=false){if(refreshing)return;refreshing=true;try{const loadedNotes=await fetchAllNotes(!silent);if(loadedNotes===null)return;notes=loadedNotes;if(currentUser?.role==="admin"){faturistas=await api("/faturistas/?incluir_inativos=true")}else{faturistas=[];}renderBillingOptions();applyFilters({resetPage:false,showMessage:!silent});if(currentUser?.role==="admin")renderFaturistas();$("lastUpdate").textContent=`Atualizado ${new Date().toLocaleTimeString("pt-BR")}`;if(!silent)toast("Dados atualizados")}catch(e){toast(e.message,true)}finally{refreshing=false}}
function isErrorNote(n){return Boolean(n.erro_salvamento)||fields.some(k=>String(n[k]??"").trim().toUpperCase()==="ERRO")}
function displayFaturista(n){const value=String(n.faturista??"").trim();return isErrorNote(n)&&(!value||value.toUpperCase()==="ERRO")?(currentUser?.username||"—"):(value||"BIPE")}
function reportBoolean(value){return value===true||value===1||String(value??"").trim().toLowerCase()==="true"}
function isReportExcludedNote(n){return reportBoolean(n.erro_salvamento)||String(n.produto??"").trim().toUpperCase()==="ERRO"}
function noteSortValue(n){const time=new Date(n.data_cadastro||0).getTime();return Number.isNaN(time)?0:time}
function sortNotesForTable(items){return items.sort((a,b)=>Number(isErrorNote(b))-Number(isErrorNote(a))||noteSortValue(b)-noteSortValue(a)||(b.id||0)-(a.id||0))}
function subtotalQuantidade(items){return items.reduce((sum,n)=>sum+Number(n.quantidade||0),0)}
function updateSubtotalMetrics(){$("metricTotal").textContent=filtered.length;$("metricWeight").textContent=new Intl.NumberFormat("pt-BR").format(subtotalQuantidade(filtered))}
function applyFilters(options={resetPage:true,showMessage:true}){const q=$("searchInput").value.toLowerCase().trim(),onlyErrors=$("errorOnlyFilter").checked,bipRange=getDateRange("bipStartDateFilter","bipEndDateFilter","Bip",options.showMessage),issueRange=getDateRange("issueStartDateFilter","issueEndDateFilter","Emissao",options.showMessage),local=$("localFilter").value,bill=$("billingFilter").value;if(bipRange===false||issueRange===false)return;filtered=sortNotesForTable(notes.filter(n=>(!onlyErrors||isErrorNote(n))&&inDateRange(n.data_cadastro,bipRange)&&inDateRange(n.data_emissao,issueRange)&&(!local||n.local===local)&&(!bill||n.faturista===bill)&&(!q||Object.values(n).some(v=>String(v??"").toLowerCase().includes(q)))));if(options.resetPage)tablePage=1;render()}
function getTablePage(){const totalPages=Math.max(1,Math.ceil(filtered.length/tablePageSize));tablePage=Math.min(Math.max(1,tablePage),totalPages);const start=(tablePage-1)*tablePageSize,end=Math.min(start+tablePageSize,filtered.length);return{rows:filtered.slice(start,end),start,end,totalPages}}
function renderPagination(page){const hasRows=filtered.length>0;$("resultCount").textContent=hasRows?`Exibindo ${page.start+1}-${page.end} de ${filtered.length} registro(s)`:"0 registros";$("tablePageInfo").textContent=`Página ${tablePage} de ${page.totalPages}`;$("prevTablePage").disabled=tablePage<=1;$("nextTablePage").disabled=tablePage>=page.totalPages;$("tablePageSize").value=String(tablePageSize)}
function render(){const body=$("notesTable"),page=getTablePage();body.innerHTML=page.rows.map(n=>{
	const canManageNotes = currentUser?.role==="admin";
	const canDownloadXml = currentUser?.role!=="viewer";
	const editAction = canManageNotes?`<button title="Editar" onclick="editNote(${n.id})">✎</button>`:"";
	const xmlAction = canDownloadXml?`<button title="Gerar XML" onclick="downloadXML(${n.id})">↓</button>`:"";
	const deleteAction = canManageNotes?`<button title="Excluir" onclick="askDelete(${n.id})">×</button>`:"";
	if(isErrorNote(n)){
		const errorCell = `<td class="error-value" title="${esc(n.erro_detalhe||"Falha ao salvar nota")}">ERRO</td>`;
		return `<tr class="save-error">
<td class="sticky"><div class="row-actions">${editAction}${deleteAction}</div></td>
<td title="${esc(n.chave_acesso)}">${esc(n.chave_acesso)}</td><td>${date(n.data_cadastro)}</td>${errorCell.repeat(3)}
<td><span class="badge">${esc(n.local||"—")}</span></td>${errorCell.repeat(4)}<td>${esc(displayFaturista(n))}</td>${errorCell.repeat(2)}</tr>`;
	}
	return `<tr>
<td class="sticky"><div class="row-actions">${editAction}${xmlAction}${deleteAction}</div></td>
<td title="${esc(n.chave_acesso)}">${esc(n.chave_acesso)}</td><td>${date(n.data_cadastro)}</td><td>${date(n.data_emissao)}</td><td>${esc(n.nome_fornecedor)}</td><td><strong>${esc(n.numero_nf)}</strong></td>
<td><span class="badge">${esc(n.local||"—")}</span></td><td title="${esc(n.produto)}">${esc(n.produto||"—")}</td><td>${esc(n.quantidade||"—")}</td><td>${money(n.valor_total)}</td>
<td>${esc(n.transportador||"—")}</td><td>${esc(displayFaturista(n))}</td><td>${esc(n.cnpj_fornecedor)}</td>
<td title="${esc(n.observacao)}">${esc(n.observacao||"—")}</td></tr>`}).join("");
$("emptyState").hidden=filtered.length>0;renderPagination(page);updateSubtotalMetrics()}
function renderBillingOptions(){const active=faturistas.length?faturistas.filter(f=>f.ativo):[...new Set(notes.map(n=>n.faturista).filter(Boolean))].sort((a,b)=>a.localeCompare(b)).map(nome=>({nome,ativo:true})),current=$("billingFilter").value;$("billingFilter").innerHTML='<option value="">Usuários</option>'+active.map(f=>`<option>${esc(f.nome)}</option>`).join("");$("billingFilter").value=current;$("faturista").innerHTML=active.map(f=>`<option>${esc(f.nome)}</option>`).join("")}
function renderFaturistas(){const admin=currentUser?.role==="admin";$("billingList").innerHTML=faturistas.map(f=>`<div class="billing-item"><div class="${f.ativo?"":"inactive"}"><strong>${esc(f.nome)}</strong><small>${f.ativo?"Ativo":"Desativado"}</small></div><div>${f.nome==="BIPE"?"Padrão do app":f.nome==="viewer_user"?`${admin?`<button class="secondary" onclick="editBilling(${f.id})">Editar senha</button><button class="secondary" onclick="toggleBilling(${f.id},${!f.ativo})">${f.ativo?"Desativar":"Reativar"}</button>`:"Somente administrador"}`:`${admin?`<button class="secondary" onclick="editBilling(${f.id})">Editar senha</button><button class="danger" onclick="deleteBilling(${f.id})">Excluir</button><button class="secondary" onclick="toggleBilling(${f.id},${!f.ativo})">${f.ativo?"Desativar":"Reativar"}</button>`:"Somente administrador"}`}</div></div>`).join("")} 
function setBillingFormMode(mode,faturista=null){const editing=mode==="edit";$("billingId").value=editing?faturista?.id:"";$("billingName").value=editing?faturista?.nome:"";$("billingName").readOnly=editing;$("billingName").required=!editing;$("billingPassword").value="";$("billingPassword").required=true;$("billingSubmit").textContent=editing?"Salvar senha":"＋ Cadastrar";} 
function closeDialog(id){const dialog=$(id);if(dialog?.open){dialog.close()}if(id==="reportsDialog"){const reportsSection=$("reportsModalSection");reportsSection?.classList.remove("maximized")}} 
document.querySelectorAll("[data-close]").forEach(btn=>btn.addEventListener("click",e=>{e.preventDefault();const target=btn.dataset.close;if(target){closeDialog(target)}}));
document.querySelectorAll("[data-maximize]").forEach(btn=>btn.addEventListener("click",e=>{e.preventDefault();const target=document.getElementById(btn.dataset.maximize);if(target){target.classList.toggle("maximized")}}));
function fillNote(n,mode="edit"){fields.forEach(k=>{const el=$(k);let v=n[k]??"";if(k==="data_emissao"&&v)v=v.slice(0,16);el.value=v});const faturistaSelect=$("faturista"),faturistaValue=mode==="edit"?(n.faturista||"BIPE"):(currentUser?.username||n.faturista||"BIPE");if(faturistaValue&&![...faturistaSelect.options].some(o=>o.value===faturistaValue)){faturistaSelect.insertAdjacentHTML("beforeend",`<option>${esc(faturistaValue)}</option>`)}faturistaSelect.value=faturistaValue;$("noteId").value=mode==="edit"?n.id:"";$("noteMode").textContent=mode==="edit"?"EDIÇÃO DE NOTA":"CONFERÊNCIA DA LEITURA";$("noteTitle").textContent=mode==="edit"?`Editar NF ${n.numero_nf}`:"Conferir nota fiscal";$("noteDialog").showModal()}
window.editNote=id=>fillNote(notes.find(n=>n.id===id));
async function downloadReport(params,name){try{const r=await fetch(`/relatorio/?${params}` ,{method:"POST"});if(!r.ok){const data=await r.json();throw new Error(data.detail||`Erro ${r.status}`)}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}catch(e){toast(e.message,true)}}
function excelText(value){return String(value??"").replace(/[<>&"]/g,c=>({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]))}
function excelCell(value,type="String"){return `<Cell><Data ss:Type="${type}">${excelText(value)}</Data></Cell>`}
function exportTableExcel(){if(!filtered.length){toast("Nenhum registro para exportar.",true);return}const columns=[["id","ID"],["chave_acesso","Chave NF"],["data_cadastro","Data/hora do bip"],["data_emissao","Data emissão"],["nome_fornecedor","Fornecedor"],["numero_nf","NF"],["local","Local"],["produto","Produto"],["quantidade","Quantidade"],["valor_total","Valor total"],["transportador","Transportador"],["faturista","Usuário"],["cnpj_fornecedor","CNPJ"],["observacao","Observação"],["erro_salvamento","Com erro"],["erro_detalhe","Detalhe do erro"]];const summary=`<Row>${excelCell("Total cadastrado")}${excelCell(filtered.length,"Number")}</Row><Row>${excelCell("Peso líquido")}${excelCell(subtotalQuantidade(filtered),"Number")}</Row><Row></Row>`;const rows=filtered.map(n=>`<Row>${columns.map(([key])=>{let value=key==="faturista"?displayFaturista(n):n[key];if(["data_cadastro","data_emissao"].includes(key))value=date(value);if(key==="erro_salvamento")value=isErrorNote(n)?"Sim":"Não";const numeric=typeof value==="number"&&Number.isFinite(value);return excelCell(value,numeric?"Number":"String")}).join("")}</Row>`).join("");const header=`<Row>${columns.map(([,label])=>excelCell(label)).join("")}</Row>`;const workbook=`<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Notas fiscais"><Table>${summary}${header}${rows}</Table></Worksheet></Workbook>`;const blob=new Blob([workbook],{type:"application/vnd.ms-excel;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=`notas_painel_${new Date().toISOString().slice(0,10)}.xls`;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);toast("Excel filtrado baixado")}
window.downloadXML=id=>downloadReport(`nota_id=${id}&formato=xml`,`nota_fiscal_${id}.xml`);
window.askDelete=id=>confirm("Excluir nota fiscal?","A nota será removida permanentemente.",async()=>{try{await api(`/notas/${id}/`,{method:"DELETE"});toast("Nota excluída");loadAll(true)}catch(e){toast(e.message,true)}})
window.toggleBilling=async(id,ativo)=>{const f=faturistas.find(x=>x.id===id);try{await api(`/faturistas/${id}/`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome:f.nome,ativo})});toast(ativo?"Usuário reativado":"Usuário desativado");loadAll(true)}catch(e){toast(e.message,true)}}
function confirm(title,message,callback){$("confirmTitle").textContent=title;$("confirmMessage").textContent=message;confirmCallback=callback;$("confirmDialog").showModal()}
$("confirmCancel").onclick=()=>$("confirmDialog").close();$("confirmAction").onclick=()=>{ $("confirmDialog").close();confirmCallback?.()};
function showRefreshErrorsLog(result){$("refreshErrorsSummary").innerHTML=`<strong>${result.atualizadas} chave(s) atualizada(s)</strong><span>${result.encontradas} encontrada(s) | ${result.falhas} ainda com erro</span>`;$("refreshErrorsLog").innerHTML=result.itens.length?result.itens.map(item=>`<div class="${item.atualizado?"success":"failure"}"><strong>${esc(item.chave_acesso)}</strong><span>${esc(item.detalhe)}</span></div>`).join(""):'<div class="empty-log">Nenhuma NF-e sinalizada com ERRO.</div>';$("refreshErrorsDialog").showModal()}
function auditDate(v){return v?new Date(v).toLocaleString("pt-BR",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"}):"—"}
function renderAuditLogs(logs){$("auditSummary").innerHTML=`<strong>${logs.length} evento(s) listado(s)</strong><span>Ordenado do mais recente para o mais antigo</span>`;$("auditEmpty").hidden=logs.length>0;$("auditTableBody").innerHTML=logs.map(log=>`<tr><td><strong>${auditDate(log.created_at)}</strong></td><td><span class="audit-user">${esc(log.usuario)}</span></td><td><span class="audit-action">${esc(log.acao)}</span></td><td>${esc(log.area)}</td><td>${esc(log.entidade||"—")}${log.entidade_id?` #${esc(log.entidade_id)}`:""}</td><td>${esc(log.descricao)}</td><td title="${esc(log.detalhes||"")}">${esc(log.detalhes||"—")}</td></tr>`).join("")}
function renderAuditError(message){$("auditSummary").innerHTML=`<strong>Não foi possível carregar a rastreabilidade</strong><span>${esc(message)}</span>`;$("auditTableBody").innerHTML="";$("auditEmpty").hidden=false;$("auditEmpty").textContent="Verifique se o backend foi reiniciado após a atualização."}
async function loadAuditLogs(){const button=$("reloadAudit"),original=button?.textContent;if(button){button.disabled=true;button.textContent="Atualizando..."}try{const logs=await api("/auditoria/?limit=300");$("auditEmpty").textContent="Nenhuma modificação registrada até o momento.";renderAuditLogs(logs)}catch(error){renderAuditError(error.message);toast(error.message,true)}finally{if(button){button.disabled=false;button.textContent=original}}}
async function openAuditLog(){if(!currentUser||currentUser.role!=="admin")return;$("auditDialog").showModal();$("auditSummary").innerHTML="<strong>Carregando eventos...</strong><span>Histórico administrativo de alterações</span>";$("auditTableBody").innerHTML="";$("auditEmpty").hidden=true;await loadAuditLogs()}
async function refreshErrorNotes(){const button=$("refreshErrorsButton"),original=button.textContent;button.disabled=true;button.textContent="Atualizando...";try{const result=await api("/notas/erro/refresh/",{method:"POST"});await loadAll(true);showRefreshErrorsLog(result)}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent=original}}
function parseBatchKeys(text){let chunks=String(text||"").split(/[\n,;]+/).map(item=>item.trim()).filter(Boolean);chunks=chunks.flatMap(item=>{const matches=item.match(/\d{44}/g);return matches&&matches.length>1?matches:[item]});return [...new Set(chunks)]}
function showBatchResult(result){$("batchResultSummary").innerHTML=`<strong>${result.cadastradas} cadastrada(s)</strong><span>${result.erros} com erro | ${result.duplicadas} duplicada(s) | ${result.invalidas} inválida(s)</span>`;$("batchResultList").innerHTML=result.itens.length?result.itens.map(item=>`<div class="${esc(item.status)}"><strong>${esc(item.chave_acesso)}</strong><span>${esc(item.status)} - ${esc(item.detalhe)}${item.numero_nf?` | NF ${esc(item.numero_nf)}`:""}</span></div>`).join(""):'<div class="empty-log">Nenhuma chave processada.</div>';$("batchResultDialog").showModal()}
async function submitBatch(){const local=$("batchLocal").value,chaves=parseBatchKeys($("batchKeys").value);if(!local){toast("Selecione o local da remessa.",true);return}if(!chaves.length){toast("Informe ao menos uma chave para a remessa.",true);return}const button=$("batchSubmit"),original=button.textContent;button.disabled=true;button.textContent="Processando...";try{const result=await api("/notas/importar-remessa/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({local,chaves})});$("batchDialog").close();$("batchForm").reset();await loadAll(true);showBatchResult(result);toast("Remessa processada")}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent=original}}
$("noteForm").addEventListener("submit",async e=>{e.preventDefault();const payload={};fields.forEach(k=>payload[k]=$(k).value||null);payload.valor_total=Number(payload.valor_total||0);payload.quantidade=payload.quantidade?Number(payload.quantidade):null;payload.caminho_arquivo_imagem=null;const id=$("noteId").value;try{await api(id?`/notas/${id}/`:"/notas/",{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});$("noteDialog").close();toast(id?"Nota atualizada":"Nota cadastrada");loadAll(true)}catch(err){toast(err.message,true)}});
$("batchForm").addEventListener("submit",async e=>{e.preventDefault();await submitBatch()});
$("billingForm").addEventListener("submit",async e=>{e.preventDefault();const nome=$("billingName").value.trim();const senha=$("billingPassword").value.trim();const id=$("billingId").value;try{if(id){const faturista=faturistas.find(f=>f.id===Number(id));await api(`/faturistas/${id}/`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome:faturista.nome,ativo:faturista?.ativo??true,senha})});toast("Senha do usuário atualizada");}else{await api("/faturistas/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome,senha})});toast("Usuário cadastrado");}$("billingName").value="";$("billingPassword").value="";$("billingId").value="";setBillingFormMode("create");$("faturistasDialog").close();loadAll(true)}catch(err){toast(err.message,true)}});
function editBilling(id){const faturista=faturistas.find(f=>f.id===id);if(!faturista)return;setBillingFormMode("edit",faturista);$("billingPassword").focus();$("faturistasDialog").showModal();}
async function deleteBilling(id){const faturista=faturistas.find(f=>f.id===id);if(!faturista)return;confirm("Excluir usuário","Deseja realmente excluir este usuário?",async()=>{try{await api(`/faturistas/${id}/`,{method:"DELETE"});toast("Usuário excluído");loadAll(true)}catch(err){toast(err.message,true)}})}
$("loginForm").addEventListener("submit",async e=>{e.preventDefault();await loginUser();});
$("loginDialog").addEventListener("cancel",e=>{e.preventDefault();});
$("logoutButton").onclick=async()=>{try{await api("/auth/logout/",{method:"POST"});currentUser=null;$("logoutButton").hidden=true;$("openAudit").hidden=true;$("userBadge").textContent="";showLogin("");}catch(err){toast(err.message,true)}};
$("openBatchScan").onclick=()=>{$("batchForm").reset();$("batchDialog").showModal()};$("openFaturistas").addEventListener("click",async e=>{e.preventDefault();if(!currentUser||currentUser.role!=="admin")return;await loadAll(true);setBillingFormMode("create");const faturistasDialog=$("faturistasDialog"); faturistasDialog.showModal ? faturistasDialog.showModal() : faturistasDialog.show();});$("openAudit").onclick=openAuditLog;$("reloadAudit").onclick=loadAuditLogs;$("refreshErrorsButton").onclick=refreshErrorNotes;$("refreshButton").onclick=()=>loadAll();$("searchInput").oninput=applyFilters;$("errorOnlyFilter").onchange=applyFilters;$("bipStartDateFilter").onchange=()=>loadAll();$("bipEndDateFilter").onchange=()=>loadAll();$("issueStartDateFilter").onchange=applyFilters;$("issueEndDateFilter").onchange=applyFilters;$("localFilter").onchange=applyFilters;$("billingFilter").onchange=applyFilters;
$("tablePageSize").onchange=()=>{tablePageSize=Number($("tablePageSize").value)||100;tablePage=1;render()};$("prevTablePage").onclick=()=>{tablePage-=1;render()};$("nextTablePage").onclick=()=>{tablePage+=1;render()};
$("downloadAll").onclick=()=>downloadReport("formato=xml","notas_fiscais.xml");
$("downloadTableExcel").onclick=exportTableExcel;
configureOptionalFilters();showLogin("");
(async()=>{if(await ensureAuthenticated()){await loadAll(true);setInterval(()=>loadAll(true),4000);}})();

// Reports functionality
const reportColors=["#f29129","#ffc46b","#f7a94c","#ffd994","#e68a22","#ffe7b8","#cc741c","#fff0cf","#b86212","#f6d08a"];
const tons=v=>`${new Intl.NumberFormat("pt-BR",{minimumFractionDigits:3,maximumFractionDigits:3}).format(v||0)} TON`;
const reportDate=v=>new Date(v).toLocaleString("pt-BR",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"});
const localInputDate=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}T${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
function defaultReportRange(){
	const now=new Date(),start=new Date(now.getFullYear(),now.getMonth(),1,0,0,0,0),end=new Date(now.getFullYear(),now.getMonth()+1,0,23,59,0,0);
	return{start:localInputDate(start),end:localInputDate(end)}
}
function getGlobalReportRange(){
	if(!$("reportGlobalStart")||!$("reportGlobalEnd")){toast("Atualize o painel com Ctrl+F5 para carregar a nova tela de relatórios.",true);return null}
	const start=$("reportGlobalStart").value,end=$("reportGlobalEnd").value;
	if(!start||!end){toast("Preencha o período do relatório.",true);return null}
	if(start>end){toast("A data inicial deve ser anterior ou igual à data final.",true);return null}
	return{start,end}
}
function setReportLoading(loading){
	const button=$("applyGlobalReportFilter");
	if(!button)return;
	button.disabled=loading;
	button.textContent=loading?"Aplicando...":"Aplicar filtro";
}
const chartGradientBackground={
	id:"chartGradientBackground",
	beforeDraw(chart,args,options){
		const {ctx,width,height}=chart,colors=options?.colors||["#eef6ff","#fbfdff","#d8e5f0"];
		const gradient=ctx.createLinearGradient(0,0,width,height);
		colors.forEach((color,index)=>gradient.addColorStop(colors.length===1?0:index/(colors.length-1),color));
		const glow=ctx.createRadialGradient(width*.18,height*.12,0,width*.18,height*.12,Math.max(width,height)*.75);
		glow.addColorStop(0,"rgba(255,255,255,.58)");
		glow.addColorStop(.46,"rgba(233,242,250,.20)");
		glow.addColorStop(1,"rgba(92,122,153,.20)");
		ctx.save();
		ctx.fillStyle=gradient;
		ctx.fillRect(0,0,width,height);
		ctx.fillStyle=glow;
		ctx.fillRect(0,0,width,height);
		ctx.restore();
	}
};
const pieValueLabels={
	id:"pieValueLabels",
	afterDatasetsDraw(chart){
		const {ctx,chartArea}=chart,meta=chart.getDatasetMeta(0),values=chart.data.datasets[0].data,isDoughnut=chart.config.type==="doughnut";
		ctx.save();
		meta.data.forEach((arc,index)=>{
			const value=Number(values[index]||0);
			if(value<=0)return;
			ctx.font="700 12px Inter, Segoe UI, Arial, sans-serif";
			ctx.textAlign="center";
			ctx.textBaseline="middle";
			ctx.lineWidth=3;
			ctx.strokeStyle="rgba(0,0,0,.55)";
			ctx.fillStyle="#fff";
			const label=tons(value);
			let position=arc.tooltipPosition();
			if(isDoughnut){
				const angle=(arc.startAngle+arc.endAngle)/2;
				const radius=arc.innerRadius+(arc.outerRadius-arc.innerRadius)*0.48;
				position={x:arc.x+Math.cos(angle)*radius,y:arc.y+Math.sin(angle)*radius};
			}
			const halfWidth=ctx.measureText(label).width/2;
			const x=Math.max(chartArea.left+halfWidth+5,Math.min(position.x,chartArea.right-halfWidth-5));
			const y=Math.max(chartArea.top+10,Math.min(position.y,chartArea.bottom-10));
			ctx.strokeText(label,x,y);
			ctx.fillText(label,x,y);
		});
		ctx.restore();
	}
};
const barValueLabels={
	id:"barValueLabels",
	afterDatasetsDraw(chart){
		const {ctx,chartArea}=chart;
		ctx.save();
		chart.data.datasets.forEach((dataset,datasetIndex)=>{
			chart.getDatasetMeta(datasetIndex).data.forEach((bar,index)=>{
				const value=Number(dataset.data[index]||0);
				if(value<=0)return;
				ctx.font="700 11px Inter, Segoe UI, Arial, sans-serif";
				ctx.textAlign="center";
				ctx.textBaseline="bottom";
				ctx.lineWidth=3;
				ctx.strokeStyle="rgba(255,255,255,.9)";
				ctx.fillStyle="#29292e";
				const label=tons(value);
				const halfWidth=ctx.measureText(label).width/2;
				const x=Math.max(chartArea.left+halfWidth+2,Math.min(bar.x,chartArea.right-halfWidth-2));
				const stacked=chart.options.scales?.x?.stacked&&chart.options.scales?.y?.stacked;
				const segmentHeight=Math.abs((bar.base??bar.y)-bar.y);
				if(stacked&&segmentHeight<18)return;
				const offset=datasetIndex%2===0?6:22;
				const y=stacked?(bar.y+(bar.base-bar.y)/2):Math.max(chartArea.top+14,bar.y-offset);
				ctx.fillStyle=stacked?"#fff":"#29292e";
				ctx.strokeStyle=stacked?"rgba(0,0,0,.55)":"rgba(255,255,255,.9)";
				ctx.strokeText(label,x,y);
				ctx.fillText(label,x,y);
			});
		});
		ctx.restore();
	}
};
let reportCharts={};
function destroyReports(){Object.values(reportCharts).forEach(chart=>chart.destroy());reportCharts={};}
function renderPeriodReport(period,prefix,canvasId){
	$(`report${prefix}Range`).textContent=`${reportDate(period.inicio)} até ${reportDate(period.fim)}`;
	$(`report${prefix}Tons`).textContent=tons(period.total_ton);
	$(`report${prefix}Notes`).textContent=new Intl.NumberFormat("pt-BR").format(period.total_notas);
	const empty=$(`chart${prefix}Empty`),canvas=$(canvasId),hasData=period.produtos.some(item=>item.quantidade_ton>0);
	empty.hidden=hasData;canvas.hidden=!hasData;if(!hasData)return;
	reportCharts[prefix.toLowerCase()]=new Chart(canvas.getContext("2d"),{
		type:"pie",
		data:{labels:period.produtos.map(item=>item.produto),datasets:[{data:period.produtos.map(item=>item.quantidade_ton),backgroundColor:period.produtos.map((_,index)=>reportColors[index%reportColors.length]),borderColor:"#fff",borderWidth:2,radius:"74%"}]},
		options:{responsive:true,maintainAspectRatio:false,radius:"74%",layout:{padding:{left:90,right:90,top:28,bottom:28}},plugins:{chartGradientBackground:{colors:["#eef6ff","#fbfdff","#d8e5f0"]},title:{display:true,text:"Quantidade por produto (data de emissão)",color:"#29292e",font:{size:17,weight:"bold"}},legend:{position:"bottom",labels:{boxWidth:14,padding:14,color:"#29292e",font:{size:12}}},tooltip:{callbacks:{label:context=>`${context.label}: ${tons(context.raw)}`}}}},
		plugins:[chartGradientBackground,pieValueLabels]
	});
}
function renderMaterialPie(result){
	renderPeriodReport({
		inicio:result.inicio,
		fim:result.fim,
		total_ton:result.total_ton,
		total_notas:result.total_nfes,
		produtos:result.materiais.map(item=>({produto:item.material,quantidade_ton:item.quantidade_ton})),
	},"Month","chartMonthProducts");
}
function materialResultFromOperational(period){
	return {
		inicio:period.inicio,
		fim:period.fim,
		total_ton:period.total_ton,
		total_nfes:period.total_notas,
		materiais:period.produtos.map(item=>({
			material:item.produto,
			quantidade_ton:item.quantidade_ton,
			quantidade_nfes:0,
		})),
	};
}
function notesInReportRange(start,end){
	const startTime=new Date(start).getTime(),endTime=new Date(end).getTime();
	if(Number.isNaN(startTime)||Number.isNaN(endTime))return[];
	return notes.filter(note=>{
		if(isReportExcludedNote(note))return false;
		const issueTime=new Date(note.data_emissao||0).getTime();
		const registerTime=new Date(note.data_cadastro||0).getTime();
		const inIssue=!Number.isNaN(issueTime)&&issueTime>=startTime&&issueTime<=endTime;
		const inRegister=!Number.isNaN(registerTime)&&registerTime>=startTime&&registerTime<=endTime;
		return inIssue||inRegister;
	});
}
function reportDateKey(note,start,end){
	const startTime=new Date(start).getTime(),endTime=new Date(end).getTime();
	const issueTime=new Date(note.data_emissao||0).getTime();
	if(!Number.isNaN(issueTime)&&issueTime>=startTime&&issueTime<=endTime)return dateKey(note.data_emissao);
	return dateKey(note.data_cadastro||note.data_emissao);
}
function materialResultFromNotes(start,end){
	const grouped=new Map(),items=notesInReportRange(start,end);
	items.forEach(note=>{
		const material=String(note.produto||"Sem produto").trim()||"Sem produto";
		const current=grouped.get(material)||{material,quantidade_ton:0,quantidade_nfes:0};
		current.quantidade_ton+=Number(note.quantidade||0)/1000;
		current.quantidade_nfes+=1;
		grouped.set(material,current);
	});
	const materiais=[...grouped.values()].map(item=>({...item,quantidade_ton:Number(item.quantidade_ton.toFixed(3))})).sort((a,b)=>b.quantidade_ton-a.quantidade_ton);
	return{inicio:start,fim:end,total_ton:Number(materiais.reduce((sum,item)=>sum+item.quantidade_ton,0).toFixed(3)),total_nfes:items.length,materiais};
}
function sectorResultFromNotes(start,end){
	const grouped=new Map();
	notesInReportRange(start,end).forEach(note=>{
		const local=note.local==="CDMA"||note.local==="PRU"?note.local:null;
		if(!local)return;
		const material=String(note.produto||"Sem produto").trim()||"Sem produto";
		const current=grouped.get(material)||{material,quantidade_cdma_ton:0,quantidade_nfes_cdma:0,quantidade_pru_ton:0,quantidade_nfes_pru:0};
		const quantity=Number(note.quantidade||0)/1000;
		if(local==="CDMA"){current.quantidade_cdma_ton+=quantity;current.quantidade_nfes_cdma+=1}
		if(local==="PRU"){current.quantidade_pru_ton+=quantity;current.quantidade_nfes_pru+=1}
		grouped.set(material,current);
	});
	const materiais=[...grouped.values()].map(item=>({
		...item,
		quantidade_cdma_ton:Number(item.quantidade_cdma_ton.toFixed(3)),
		quantidade_pru_ton:Number(item.quantidade_pru_ton.toFixed(3)),
	})).sort((a,b)=>(b.quantidade_cdma_ton+b.quantidade_pru_ton)-(a.quantidade_cdma_ton+a.quantidade_pru_ton));
	return{inicio:start,fim:end,materiais};
}
function receiptResultFromNotes(start,end,selectedMaterial=""){
	const periodNotes=notesInReportRange(start,end);
	const materiais_disponiveis=[...new Set(periodNotes.map(note=>String(note.produto||"Sem produto").trim()||"Sem produto"))].sort((a,b)=>a.localeCompare(b));
	const material_normalizado=selectedMaterial||"";
	const filteredNotes=material_normalizado?periodNotes.filter(note=>(String(note.produto||"Sem produto").trim()||"Sem produto")===material_normalizado):periodNotes;
	const totals=new Map(),daily=new Map();
	filteredNotes.forEach(note=>{
		const material=String(note.produto||"Sem produto").trim()||"Sem produto";
		const quantity=Number(note.quantidade||0)/1000;
		const key=reportDateKey(note,start,end);
		totals.set(material,(totals.get(material)||0)+quantity);
		if(!daily.has(key))daily.set(key,new Map());
		daily.get(key).set(material,(daily.get(key).get(material)||0)+quantity);
	});
	const totais_materiais=[...totals.entries()].map(([material,total])=>({material,total_ton:Number(total.toFixed(3))})).sort((a,b)=>b.total_ton-a.total_ton);
	const dias=[];
	let current=new Date(`${start.slice(0,10)}T00:00:00`),last=new Date(`${end.slice(0,10)}T00:00:00`);
	while(current<=last){
		const key=dateKey(current);
		const values=daily.get(key)||new Map();
		dias.push({data:key,materiais_ton:Object.fromEntries([...values.entries()].map(([material,total])=>[material,Number(total.toFixed(3))]))});
		current.setDate(current.getDate()+1);
	}
	return{inicio:start,fim:end,material:material_normalizado||null,materiais_disponiveis,totais_materiais,total_ton:Number(totais_materiais.reduce((sum,item)=>sum+item.total_ton,0).toFixed(3)),dias};
}
async function refreshReportNotes(){
	const loadedNotes=await fetchAllNotes();
	if(loadedNotes===null)return notes;
	notes=loadedNotes;
	applyFilters({resetPage:false});
	return notes;
}
async function renderReports(){
	try{
		const current=getGlobalReportRange();
		if(!current)return;
		setReportLoading(true);
		destroyReports();
		await refreshReportNotes();
		const materialResult=await renderMaterialReport();
		if(materialResult)renderMaterialPie(materialResult);
		await renderSectorReport();
		await renderReceiptReport();
	}catch(error){toast(error.message,true)}finally{setReportLoading(false)}
}
function renderMaterialTable(result){
	$("materialReportTotal").textContent=tons(result.total_ton);
	$("materialReportNotes").textContent=`${new Intl.NumberFormat("pt-BR").format(result.total_nfes)} NF-es`;
	$("materialReportBody").innerHTML=result.materiais.map(item=>`<tr><td>${esc(item.material)}</td><td>${tons(item.quantidade_ton)}</td><td>${new Intl.NumberFormat("pt-BR").format(item.quantidade_nfes)}</td></tr>`).join("");
	$("materialReportEmpty").hidden=result.materiais.length>0;
}
async function renderMaterialReport(){
	const range=getGlobalReportRange();
	if(!range)return;
	const {start,end}=range;
	const params=new URLSearchParams({data_inicio:start,data_fim:end});
	const result=await api(`/relatorios/material/?${params}`);
	renderMaterialTable(result);
	return result;
}
async function renderSectorReport(){
	const range=getGlobalReportRange();
	if(!range)return;
	const {start,end}=range;
	const result=sectorResultFromNotes(start,end);
	$("sectorReportBody").innerHTML=result.materiais.map(item=>`<tr><td>${esc(item.material)}</td><td>${tons(item.quantidade_cdma_ton)}</td><td>${new Intl.NumberFormat("pt-BR").format(item.quantidade_nfes_cdma)}</td><td>${tons(item.quantidade_pru_ton)}</td><td>${new Intl.NumberFormat("pt-BR").format(item.quantidade_nfes_pru)}</td></tr>`).join("");
	$("sectorReportEmpty").hidden=result.materiais.length>0;
}
async function renderReceiptReport(){
	const range=getGlobalReportRange();
	if(!range)return;
	const {start,end}=range,material=$("receiptMaterial").value;
	const result=receiptResultFromNotes(start,end,material);
	const materialSelect=$("receiptMaterial"),selected=result.material||"";
	materialSelect.innerHTML='<option value="">Todos os materiais</option>'+result.materiais_disponiveis.map(item=>`<option value="${esc(item)}">${esc(item)}</option>`).join("");
	materialSelect.value=selected;
	$("receiptMaterialTotals").innerHTML=`<span>Total: ${tons(result.total_ton)}</span>`+result.totais_materiais.map(item=>`<span>${esc(item.material)}: ${tons(item.total_ton)}</span>`).join("");
	reportCharts.receiptDaily?.destroy();reportCharts.receiptShare?.destroy();
	const hasData=result.total_ton>0;
	$("receiptDailyEmpty").hidden=hasData;$("receiptShareEmpty").hidden=hasData;$("receiptDailyChart").hidden=!hasData;$("receiptShareChart").hidden=!hasData;
	if(!hasData)return;
	const labels=result.dias.map(item=>new Date(`${item.data}T00:00:00`).toLocaleDateString("pt-BR",{day:"2-digit",month:"2-digit"}));
	const materials=result.totais_materiais.map(item=>item.material);
	const datasets=materials.map((item,index)=>({label:item,data:result.dias.map(day=>day.materiais_ton[item]||0),backgroundColor:reportColors[index%reportColors.length],borderRadius:2}));
	reportCharts.receiptDaily=new Chart($("receiptDailyChart").getContext("2d"),{
		type:"bar",
		data:{labels,datasets},
		options:{responsive:true,maintainAspectRatio:false,layout:{padding:{top:30,right:12}},plugins:{chartGradientBackground:{colors:["#eef6ff","#fbfdff","#d8e5f0"]},title:{display:true,text:selected?`Recebimento diário por data de emissão - ${selected}`:"Composição diária por material (data de emissão)",color:"#29292e",font:{size:17,weight:"bold"}},tooltip:{callbacks:{label:context=>`${context.dataset.label}: ${tons(context.raw)}`}}},scales:{x:{stacked:true,title:{display:true,text:"Data de emissão"}},y:{stacked:true,beginAtZero:true,grace:"15%",title:{display:true,text:"Toneladas"},ticks:{callback:value=>new Intl.NumberFormat("pt-BR").format(value)}}}},
		plugins:[chartGradientBackground]
	});
	reportCharts.receiptShare=new Chart($("receiptShareChart").getContext("2d"),{
		type:"doughnut",
		data:{labels:materials,datasets:[{data:result.totais_materiais.map(item=>item.total_ton),backgroundColor:materials.map((_,index)=>reportColors[index%reportColors.length]),borderColor:"#fff",borderWidth:2}]},
		options:{responsive:true,maintainAspectRatio:false,cutout:"58%",layout:{padding:{left:20,right:20,top:8}},plugins:{chartGradientBackground:{colors:["#eef6ff","#fbfdff","#d8e5f0"]},title:{display:true,text:"Participação total por material (data de emissão)",color:"#29292e",font:{size:17,weight:"bold"}},legend:{position:"bottom"},tooltip:{callbacks:{label:context=>`${context.label}: ${tons(context.raw)}`}}}},
		plugins:[chartGradientBackground,pieValueLabels]
	});
}
$("globalReportFilterForm")?.addEventListener("submit",async event=>{
	event.preventDefault();
	await renderReports();
});
async function exportOperationalReport(format){
	const range=getGlobalReportRange();
	if(!range)return;
	const values={
		data_inicio:range.start,
		data_fim:range.end,
		material_inicio:range.start,
		material_fim:range.end,
		setor_inicio:range.start,
		setor_fim:range.end,
		recebimento_inicio:range.start,
		recebimento_fim:range.end,
	};
	if($("receiptMaterial").value)values.recebimento_material=$("receiptMaterial").value;
	const button=format==="pdf"?$("exportReportPdf"):$("exportReportExcel"),original=button.textContent;
	button.disabled=true;button.textContent="Gerando...";
	try{
		const params=new URLSearchParams({formato:format,...values});
		const response=await fetch(`/relatorios/exportar/?${params}`,{credentials:"include"});
		if(!response.ok){let message=`Erro ${response.status}`;try{message=(await response.json()).detail||message}catch{}throw new Error(message)}
		const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement("a");
		link.href=url;link.download=`relatorio_operacional.${format}`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
		toast(`Relatório ${format.toUpperCase()} baixado`);
	}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent=original}
}
$("exportReportPdf").onclick=()=>exportOperationalReport("pdf");
$("exportReportExcel").onclick=()=>exportOperationalReport("xlsx");
async function openReportsModal(){
	if(!$("globalReportFilterForm")){toast("Atualize o painel com Ctrl+F5 para carregar a nova tela de relatórios.",true);return}
	$("reportsModalSection").classList.add("maximized");
	if(!$("reportsDialog").open)$("reportsDialog").showModal();
	const range=defaultReportRange();
	if(!$("reportGlobalStart").value)$("reportGlobalStart").value=range.start;
	if(!$("reportGlobalEnd").value)$("reportGlobalEnd").value=range.end;
	await renderReports();
}
$("openReports").addEventListener("click",async event=>{
	event.preventDefault();
	if(!await ensureAuthenticated())return;
	await openReportsModal();
});

