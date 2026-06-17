const $=id=>document.getElementById(id);let notes=[],faturistas=[],filtered=[],refreshing=false,confirmCallback=null,currentUser=null;
const fields=["numero_nf","serie","data_emissao","cnpj_fornecedor","nome_fornecedor","valor_total","chave_acesso","local","produto","quantidade","transportador","faturista","lider_operacional","observacao"];
const money=v=>new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(v||0);
const date=v=>v?new Date(v).toLocaleString("pt-BR"):"—";const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
async function api(path,options={}){options.credentials="include";const r=await fetch(path,options);if(!r.ok){let m=`Erro ${r.status}`;try{m=(await r.json()).detail||m}catch{}throw new Error(m)}return r.headers.get("content-type")?.includes("json")?r.json():r}
function toast(message,error=false){const el=$("toast");el.textContent=message;el.className=error?"show error":"show";setTimeout(()=>el.className="",3200)}
function showLogin(message){$("loginError").textContent=message||"";document.body.classList.remove("authenticated");const dialog=$("loginDialog");if(!dialog.open){dialog.showModal();}}
function hideLogin(){document.body.classList.add("authenticated");const dialog=$("loginDialog");if(dialog.open){dialog.close();}$("loginError").textContent="";}
async function ensureAuthenticated(){try{currentUser=await api("/auth/me/");const isAdmin=currentUser.role==="admin",isViewer=currentUser.role==="viewer";$("userBadge").textContent=`${currentUser.username}${isAdmin?" (admin)":isViewer?" (viewer)":""}`;$("logoutButton").hidden=false;$("openNotes").hidden=false;$("mainPanel").hidden=false;$("openBatchScan").hidden=isViewer;$("openScan").hidden=isViewer;$("downloadAll").hidden=isViewer;$("openFaturistas").hidden=!isAdmin;$("openSwagger").hidden=!isAdmin;$("refreshErrorsButton").hidden=!isAdmin;hideLogin();return true;}catch(err){currentUser=null;$("userBadge").textContent="";$("logoutButton").hidden=true;$("openNotes").hidden=false;$("mainPanel").hidden=false;$("openBatchScan").hidden=false;$("openScan").hidden=false;$("downloadAll").hidden=false;$("openFaturistas").hidden=true;$("openSwagger").hidden=true;$("refreshErrorsButton").hidden=true;showLogin("");return false;}}
async function loginUser(){try{await api("/auth/login/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:$("loginUsername").value,password:$("loginPassword").value})});await ensureAuthenticated();await loadAll(true);}catch(err){$("loginError").textContent=err.message;}}
async function loadAll(silent=false){if(refreshing)return;refreshing=true;try{if(currentUser?.role==="admin"){[notes,faturistas]=await Promise.all([api("/notas/?limit=500"),api("/faturistas/?incluir_inativos=true")]);}else{notes=await api("/notas/?limit=500");faturistas=[];}renderBillingOptions();applyFilters();if(currentUser?.role==="admin")renderFaturistas();$("lastUpdate").textContent=`Atualizado ${new Date().toLocaleTimeString("pt-BR")}`;if(!silent)toast("Dados atualizados")}catch(e){toast(e.message,true)}finally{refreshing=false}}
function isErrorNote(n){return Boolean(n.erro_salvamento)||fields.some(k=>String(n[k]??"").trim().toUpperCase()==="ERRO")}
function applyFilters(){const q=$("searchInput").value.toLowerCase().trim(),onlyErrors=$("errorOnlyFilter").checked,local=$("localFilter").value,bill=$("billingFilter").value;filtered=notes.filter(n=>(!onlyErrors||isErrorNote(n))&&(!local||n.local===local)&&(!bill||n.faturista===bill)&&(!q||Object.values(n).some(v=>String(v??"").toLowerCase().includes(q))));render()}
function render(){const body=$("notesTable");body.innerHTML=filtered.map(n=>{
	const canManageNotes = currentUser?.role==="admin";
	const canDownloadXml = currentUser?.role!=="viewer";
	const editAction = canManageNotes?`<button title="Editar" onclick="editNote(${n.id})">✎</button>`:"";
	const xmlAction = canDownloadXml?`<button title="Gerar XML" onclick="downloadXML(${n.id})">↓</button>`:"";
	const deleteAction = canManageNotes?`<button title="Excluir" onclick="askDelete(${n.id})">×</button>`:"";
	if(isErrorNote(n)){
		const errorCell = `<td class="error-value" title="${esc(n.erro_detalhe||"Falha ao salvar nota")}">ERRO</td>`;
		return `<tr class="save-error">
<td class="sticky"><div class="row-actions">${editAction}${deleteAction}</div></td>
<td>${n.id}</td><td title="${esc(n.chave_acesso)}">${esc(n.chave_acesso)}</td>${errorCell.repeat(4)}
<td><span class="badge">${esc(n.local||"—")}</span></td>${errorCell.repeat(8)}</tr>`;
	}
	return `<tr>
<td class="sticky"><div class="row-actions">${editAction}${xmlAction}${deleteAction}</div></td>
<td>${n.id}</td><td title="${esc(n.chave_acesso)}">${esc(n.chave_acesso)}</td><td>${date(n.data_cadastro)}</td><td>${date(n.data_emissao)}</td><td>${esc(n.nome_fornecedor)}</td><td><strong>${esc(n.numero_nf)}</strong></td>
<td><span class="badge">${esc(n.local||"—")}</span></td><td title="${esc(n.produto)}">${esc(n.produto||"—")}</td><td>${esc(n.quantidade||"—")}</td><td>${money(n.valor_total)}</td>
<td>${esc(n.transportador||"—")}</td><td>${esc(n.faturista||"BIPE")}</td><td>${esc(n.lider_operacional||"—")}</td><td>${esc(n.cnpj_fornecedor)}</td>
<td title="${esc(n.observacao)}">${esc(n.observacao||"—")}</td></tr>`}).join("");
$("emptyState").hidden=filtered.length>0;$("resultCount").textContent=`${filtered.length} registro(s)`;$("metricTotal").textContent=notes.length;$("metricWeight").textContent=new Intl.NumberFormat("pt-BR").format(notes.reduce((s,n)=>s+(n.quantidade||0),0));$("metricValue").textContent=money(notes.reduce((s,n)=>s+(n.valor_total||0),0));$("metricPending").textContent=notes.filter(n=>!n.erro_salvamento&&!n.lider_operacional).length}
function renderBillingOptions(){const active=faturistas.length?faturistas.filter(f=>f.ativo):[...new Set(notes.map(n=>n.faturista).filter(Boolean))].sort((a,b)=>a.localeCompare(b)).map(nome=>({nome,ativo:true})),current=$("billingFilter").value;$("billingFilter").innerHTML='<option value="">Todos os usuários</option>'+active.map(f=>`<option>${esc(f.nome)}</option>`).join("");$("billingFilter").value=current;$("faturista").innerHTML=active.map(f=>`<option>${esc(f.nome)}</option>`).join("")} 
function renderFaturistas(){const admin=currentUser?.role==="admin";$("billingList").innerHTML=faturistas.map(f=>`<div class="billing-item"><div class="${f.ativo?"":"inactive"}"><strong>${esc(f.nome)}</strong><small>${f.ativo?"Ativo":"Desativado"}</small></div><div>${f.nome==="BIPE"?"Padrão do app":f.nome==="viewer_user"?`${admin?`<button class="secondary" onclick="editBilling(${f.id})">Editar senha</button><button class="secondary" onclick="toggleBilling(${f.id},${!f.ativo})">${f.ativo?"Desativar":"Reativar"}</button>`:"Somente administrador"}`:`${admin?`<button class="secondary" onclick="editBilling(${f.id})">Editar senha</button><button class="danger" onclick="deleteBilling(${f.id})">Excluir</button><button class="secondary" onclick="toggleBilling(${f.id},${!f.ativo})">${f.ativo?"Desativar":"Reativar"}</button>`:"Somente administrador"}`}</div></div>`).join("")} 
function setBillingFormMode(mode,faturista=null){const editing=mode==="edit";$("billingId").value=editing?faturista?.id:"";$("billingName").value=editing?faturista?.nome:"";$("billingName").readOnly=editing;$("billingName").required=!editing;$("billingPassword").value="";$("billingPassword").required=true;$("billingSubmit").textContent=editing?"Salvar senha":"＋ Cadastrar";} 
function closeDialog(id){const dialog=$(id);if(dialog?.open){dialog.close()}if(id==="reportsDialog"){const reportsSection=$("reportsModalSection");reportsSection?.classList.remove("maximized")}} 
document.querySelectorAll("[data-close]").forEach(btn=>btn.addEventListener("click",e=>{e.preventDefault();const target=btn.dataset.close;if(target){closeDialog(target)}}));
document.querySelectorAll("[data-maximize]").forEach(btn=>btn.addEventListener("click",e=>{e.preventDefault();const target=document.getElementById(btn.dataset.maximize);if(target){target.classList.toggle("maximized")}}));
function fillNote(n,mode="edit"){fields.forEach(k=>{const el=$(k);let v=n[k]??"";if(k==="data_emissao"&&v)v=v.slice(0,16);el.value=v});const faturistaSelect=$("faturista");if(n.faturista&&![...faturistaSelect.options].some(o=>o.value===n.faturista)){faturistaSelect.insertAdjacentHTML("beforeend",`<option>${esc(n.faturista)}</option>`)}faturistaSelect.value=n.faturista||"BIPE";$("noteId").value=mode==="edit"?n.id:"";$("noteMode").textContent=mode==="edit"?"EDIÇÃO DE NOTA":"CONFERÊNCIA DA LEITURA";$("noteTitle").textContent=mode==="edit"?`Editar NF ${n.numero_nf}`:"Conferir nota fiscal";$("noteDialog").showModal()}
window.editNote=id=>fillNote(notes.find(n=>n.id===id));
async function downloadReport(params,name){try{const r=await fetch(`/relatorio/?${params}` ,{method:"POST"});if(!r.ok){const data=await r.json();throw new Error(data.detail||`Erro ${r.status}`)}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}catch(e){toast(e.message,true)}}
window.downloadXML=id=>downloadReport(`nota_id=${id}&formato=xml`,`nota_fiscal_${id}.xml`);
window.askDelete=id=>confirm("Excluir nota fiscal?","A nota será removida permanentemente.",async()=>{try{await api(`/notas/${id}/`,{method:"DELETE"});toast("Nota excluída");loadAll(true)}catch(e){toast(e.message,true)}})
window.toggleBilling=async(id,ativo)=>{const f=faturistas.find(x=>x.id===id);try{await api(`/faturistas/${id}/`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome:f.nome,ativo})});toast(ativo?"Usuário reativado":"Usuário desativado");loadAll(true)}catch(e){toast(e.message,true)}}
function confirm(title,message,callback){$("confirmTitle").textContent=title;$("confirmMessage").textContent=message;confirmCallback=callback;$("confirmDialog").showModal()}
$("confirmCancel").onclick=()=>$("confirmDialog").close();$("confirmAction").onclick=()=>{ $("confirmDialog").close();confirmCallback?.()};
function showRefreshErrorsLog(result){$("refreshErrorsSummary").innerHTML=`<strong>${result.atualizadas} chave(s) atualizada(s)</strong><span>${result.encontradas} encontrada(s) | ${result.falhas} ainda com erro</span>`;$("refreshErrorsLog").innerHTML=result.itens.length?result.itens.map(item=>`<div class="${item.atualizado?"success":"failure"}"><strong>${esc(item.chave_acesso)}</strong><span>${esc(item.detalhe)}</span></div>`).join(""):'<div class="empty-log">Nenhuma NF-e sinalizada com ERRO.</div>';$("refreshErrorsDialog").showModal()}
async function refreshErrorNotes(){const button=$("refreshErrorsButton"),original=button.textContent;button.disabled=true;button.textContent="Atualizando...";try{const result=await api("/notas/erro/refresh/",{method:"POST"});await loadAll(true);showRefreshErrorsLog(result)}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent=original}}
function parseBatchKeys(text){let chunks=String(text||"").split(/[\n,;]+/).map(item=>item.trim()).filter(Boolean);chunks=chunks.flatMap(item=>{const matches=item.match(/\d{44}/g);return matches&&matches.length>1?matches:[item]});return [...new Set(chunks)]}
function showBatchResult(result){$("batchResultSummary").innerHTML=`<strong>${result.cadastradas} cadastrada(s)</strong><span>${result.erros} com erro | ${result.duplicadas} duplicada(s) | ${result.invalidas} inválida(s)</span>`;$("batchResultList").innerHTML=result.itens.length?result.itens.map(item=>`<div class="${esc(item.status)}"><strong>${esc(item.chave_acesso)}</strong><span>${esc(item.status)} - ${esc(item.detalhe)}${item.numero_nf?` | NF ${esc(item.numero_nf)}`:""}</span></div>`).join(""):'<div class="empty-log">Nenhuma chave processada.</div>';$("batchResultDialog").showModal()}
async function submitBatch(){const local=$("batchLocal").value,chaves=parseBatchKeys($("batchKeys").value);if(!local){toast("Selecione o local da remessa.",true);return}if(!chaves.length){toast("Informe ao menos uma chave para a remessa.",true);return}const button=$("batchSubmit"),original=button.textContent;button.disabled=true;button.textContent="Processando...";try{const result=await api("/notas/importar-remessa/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({local,chaves})});$("batchDialog").close();$("batchForm").reset();await loadAll(true);showBatchResult(result);toast("Remessa processada")}catch(error){toast(error.message,true)}finally{button.disabled=false;button.textContent=original}}
$("noteForm").addEventListener("submit",async e=>{e.preventDefault();const payload={};fields.forEach(k=>payload[k]=$(k).value||null);payload.valor_total=Number(payload.valor_total||0);payload.quantidade=payload.quantidade?Number(payload.quantidade):null;payload.caminho_arquivo_imagem=null;const id=$("noteId").value;try{await api(id?`/notas/${id}/`:"/notas/",{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});$("noteDialog").close();toast(id?"Nota atualizada":"Nota cadastrada");loadAll(true)}catch(err){toast(err.message,true)}});
$("scanForm").addEventListener("submit",async e=>{e.preventDefault();try{const result=await api("/barcode-nf/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({codigo_barras:$("scanKey").value})});const n={...result.nota,local:$("scanLocal").value,faturista:"BIPE"};$("scanDialog").close();fillNote(n,"create")}catch(err){toast(err.message,true)}});
$("batchForm").addEventListener("submit",async e=>{e.preventDefault();await submitBatch()});
$("billingForm").addEventListener("submit",async e=>{e.preventDefault();const nome=$("billingName").value.trim();const senha=$("billingPassword").value.trim();const id=$("billingId").value;try{if(id){const faturista=faturistas.find(f=>f.id===Number(id));await api(`/faturistas/${id}/`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome:faturista.nome,ativo:faturista?.ativo??true,senha})});toast("Senha do usuário atualizada");}else{await api("/faturistas/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome,senha})});toast("Usuário cadastrado");}$("billingName").value="";$("billingPassword").value="";$("billingId").value="";setBillingFormMode("create");$("faturistasDialog").close();loadAll(true)}catch(err){toast(err.message,true)}});
function editBilling(id){const faturista=faturistas.find(f=>f.id===id);if(!faturista)return;setBillingFormMode("edit",faturista);$("billingPassword").focus();$("faturistasDialog").showModal();}
async function deleteBilling(id){const faturista=faturistas.find(f=>f.id===id);if(!faturista)return;confirm("Excluir usuário","Deseja realmente excluir este usuário?",async()=>{try{await api(`/faturistas/${id}/`,{method:"DELETE"});toast("Usuário excluído");loadAll(true)}catch(err){toast(err.message,true)}})}
$("loginForm").addEventListener("submit",async e=>{e.preventDefault();await loginUser();});
$("loginDialog").addEventListener("cancel",e=>{e.preventDefault();});
$("logoutButton").onclick=async()=>{try{await api("/auth/logout/",{method:"POST"});currentUser=null;$("logoutButton").hidden=true;$("userBadge").textContent="";showLogin("");}catch(err){toast(err.message,true)}};
$("openBatchScan").onclick=()=>{$("batchForm").reset();$("batchDialog").showModal()};$("openScan").onclick=()=>{$("scanForm").reset();$("scanDialog").showModal()};$("openFaturistas").addEventListener("click",async e=>{e.preventDefault();if(!currentUser||currentUser.role!=="admin")return;await loadAll(true);setBillingFormMode("create");const faturistasDialog=$("faturistasDialog"); faturistasDialog.showModal ? faturistasDialog.showModal() : faturistasDialog.show();});$("refreshErrorsButton").onclick=refreshErrorNotes;$("refreshButton").onclick=()=>loadAll();$("searchInput").oninput=applyFilters;$("errorOnlyFilter").onchange=applyFilters;$("localFilter").onchange=applyFilters;$("billingFilter").onchange=applyFilters;
$("downloadAll").onclick=()=>downloadReport("formato=xml","notas_fiscais.xml");
showLogin("");
(async()=>{if(await ensureAuthenticated()){await loadAll(true);setInterval(()=>loadAll(true),4000);}})();

// Reports functionality
const reportColors=["#f29129","#ffc46b","#f7a94c","#ffd994","#e68a22","#ffe7b8","#cc741c","#fff0cf","#b86212","#f6d08a"];
const tons=v=>`${new Intl.NumberFormat("pt-BR",{minimumFractionDigits:3,maximumFractionDigits:3}).format(v||0)} TON`;
const reportDate=v=>new Date(v).toLocaleString("pt-BR",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"});
const reportInputDate=v=>String(v||"").slice(0,16);
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
		options:{responsive:true,maintainAspectRatio:false,radius:"74%",layout:{padding:{left:90,right:90,top:28,bottom:28}},plugins:{chartGradientBackground:{colors:["#eef6ff","#fbfdff","#d8e5f0"]},title:{display:true,text:"Quantidade por produto",color:"#29292e",font:{size:17,weight:"bold"}},legend:{position:"bottom",labels:{boxWidth:14,padding:14,color:"#29292e",font:{size:12}}},tooltip:{callbacks:{label:context=>`${context.label}: ${tons(context.raw)}`}}}},
		plugins:[chartGradientBackground,pieValueLabels]
	});
}
async function renderReports(){
	try{
		const report=await api("/relatorios/operacional/");
		destroyReports();
		renderPeriodReport(report.mes,"Month","chartMonthProducts");
		renderPeriodReport(report.dia,"Day","chartDayProducts");
		$("materialStart").value=reportInputDate(report.mes.inicio);
		$("materialEnd").value=reportInputDate(report.dia.fim);
		$("sectorStart").value=reportInputDate(report.mes.inicio);
		$("sectorEnd").value=reportInputDate(report.dia.fim);
		$("receiptStart").value=reportInputDate(report.mes.inicio);
		$("receiptEnd").value=reportInputDate(report.dia.fim);
		await renderMaterialReport();
		await renderSectorReport();
		await renderReceiptReport();
	}catch(error){toast(error.message,true)}
}
async function renderMaterialReport(){
	const start=$("materialStart").value,end=$("materialEnd").value;
	if(!start||!end)return;
	if(start>end){toast("A data inicial deve ser anterior ou igual à data final.",true);return}
	const result=await api(`/relatorios/material/?data_inicio=${encodeURIComponent(start)}&data_fim=${encodeURIComponent(end)}`);
	$("materialReportTotal").textContent=tons(result.total_ton);
	$("materialReportNotes").textContent=`${new Intl.NumberFormat("pt-BR").format(result.total_nfes)} NF-es`;
	$("materialReportBody").innerHTML=result.materiais.map(item=>`<tr><td>${esc(item.material)}</td><td>${tons(item.quantidade_ton)}</td><td>${new Intl.NumberFormat("pt-BR").format(item.quantidade_nfes)}</td></tr>`).join("");
	$("materialReportEmpty").hidden=result.materiais.length>0;
}
$("materialReportForm").addEventListener("submit",async event=>{
	event.preventDefault();
	try{await renderMaterialReport()}catch(error){toast(error.message,true)}
});
async function renderSectorReport(){
	const start=$("sectorStart").value,end=$("sectorEnd").value;
	if(!start||!end)return;
	if(start>end){toast("A data inicial deve ser anterior ou igual à data final.",true);return}
	const result=await api(`/relatorios/material-local/?data_inicio=${encodeURIComponent(start)}&data_fim=${encodeURIComponent(end)}`);
	$("sectorReportBody").innerHTML=result.materiais.map(item=>`<tr><td>${esc(item.material)}</td><td>${tons(item.quantidade_cdma_ton)}</td><td>${new Intl.NumberFormat("pt-BR").format(item.quantidade_nfes_cdma)}</td><td>${tons(item.quantidade_pru_ton)}</td><td>${new Intl.NumberFormat("pt-BR").format(item.quantidade_nfes_pru)}</td></tr>`).join("");
	$("sectorReportEmpty").hidden=result.materiais.length>0;
}
$("sectorReportForm").addEventListener("submit",async event=>{
	event.preventDefault();
	try{await renderSectorReport()}catch(error){toast(error.message,true)}
});
async function renderReceiptReport(){
	const start=$("receiptStart").value,end=$("receiptEnd").value,material=$("receiptMaterial").value;
	if(!start||!end)return;
	if(start>end){toast("A data inicial deve ser anterior ou igual à data final.",true);return}
	const params=new URLSearchParams({data_inicio:start,data_fim:end});if(material)params.set("material",material);
	const result=await api(`/relatorios/recebimento-diario/?${params}`);
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
		options:{responsive:true,maintainAspectRatio:false,layout:{padding:{top:30,right:12}},plugins:{chartGradientBackground:{colors:["#eef6ff","#fbfdff","#d8e5f0"]},title:{display:true,text:selected?`Recebimento diário - ${selected}`:"Composição diária por material",color:"#29292e",font:{size:17,weight:"bold"}},tooltip:{callbacks:{label:context=>`${context.dataset.label}: ${tons(context.raw)}`}}},scales:{x:{stacked:true,title:{display:true,text:"Data de emissão"}},y:{stacked:true,beginAtZero:true,grace:"15%",title:{display:true,text:"Toneladas"},ticks:{callback:value=>new Intl.NumberFormat("pt-BR").format(value)}}}},
		plugins:[chartGradientBackground,barValueLabels]
	});
	reportCharts.receiptShare=new Chart($("receiptShareChart").getContext("2d"),{
		type:"doughnut",
		data:{labels:materials,datasets:[{data:result.totais_materiais.map(item=>item.total_ton),backgroundColor:materials.map((_,index)=>reportColors[index%reportColors.length]),borderColor:"#fff",borderWidth:2}]},
		options:{responsive:true,maintainAspectRatio:false,cutout:"58%",layout:{padding:{left:20,right:20,top:8}},plugins:{chartGradientBackground:{colors:["#eef6ff","#fbfdff","#d8e5f0"]},title:{display:true,text:"Participação total por material",color:"#29292e",font:{size:17,weight:"bold"}},legend:{position:"bottom"},tooltip:{callbacks:{label:context=>`${context.label}: ${tons(context.raw)}`}}}},
		plugins:[chartGradientBackground,pieValueLabels]
	});
}
$("receiptReportForm").addEventListener("submit",async event=>{
	event.preventDefault();
	try{await renderReceiptReport()}catch(error){toast(error.message,true)}
});
async function exportOperationalReport(format){
	const values={
		material_inicio:$("materialStart").value,
		material_fim:$("materialEnd").value,
		setor_inicio:$("sectorStart").value,
		setor_fim:$("sectorEnd").value,
		recebimento_inicio:$("receiptStart").value,
		recebimento_fim:$("receiptEnd").value,
	};
	if($("receiptMaterial").value)values.recebimento_material=$("receiptMaterial").value;
	if(Object.values(values).some(value=>!value)){toast("Preencha todos os períodos antes de exportar.",true);return}
	if(values.material_inicio>values.material_fim||values.setor_inicio>values.setor_fim||values.recebimento_inicio>values.recebimento_fim){toast("A data inicial deve ser anterior ou igual à data final.",true);return}
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
	$("reportsModalSection").classList.add("maximized");
	if(!$("reportsDialog").open)$("reportsDialog").showModal();
	await renderReports();
}
$("openReports").addEventListener("click",async event=>{
	event.preventDefault();
	if(!await ensureAuthenticated())return;
	await openReportsModal();
});
