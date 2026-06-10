const $=id=>document.getElementById(id);let notes=[],faturistas=[],filtered=[],refreshing=false,confirmCallback=null,currentUser=null;
const fields=["numero_nf","serie","data_emissao","cnpj_fornecedor","nome_fornecedor","valor_total","chave_acesso","local","produto","quantidade","transportador","faturista","lider_operacional","observacao"];
const money=v=>new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(v||0);
const date=v=>v?new Date(v).toLocaleString("pt-BR"):"—";const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
async function api(path,options={}){options.credentials="include";const r=await fetch(path,options);if(!r.ok){let m=`Erro ${r.status}`;try{m=(await r.json()).detail||m}catch{}throw new Error(m)}return r.headers.get("content-type")?.includes("json")?r.json():r}
function toast(message,error=false){const el=$("toast");el.textContent=message;el.className=error?"show error":"show";setTimeout(()=>el.className="",3200)}
function showLogin(message){$("loginError").textContent=message||"";document.body.classList.remove("authenticated");const dialog=$("loginDialog");if(!dialog.open){dialog.showModal();}}
function hideLogin(){document.body.classList.add("authenticated");const dialog=$("loginDialog");if(dialog.open){dialog.close();}$("loginError").textContent="";}
async function ensureAuthenticated(){try{currentUser=await api("/auth/me/");$("userBadge").textContent=`${currentUser.username}${currentUser.role==="admin"?" (admin)":""}`;$("logoutButton").hidden=false;$("openFaturistas").hidden = currentUser.role !== "admin";hideLogin();return true;}catch(err){currentUser=null;$("userBadge").textContent="";$("logoutButton").hidden=true;$("openFaturistas").hidden = true;showLogin("");return false;}}
async function loginUser(){try{await api("/auth/login/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:$("loginUsername").value,password:$("loginPassword").value})});await ensureAuthenticated();await loadAll(true);}catch(err){$("loginError").textContent=err.message;}}
async function loadAll(silent=false){if(refreshing)return;refreshing=true;try{[notes,faturistas]=await Promise.all([api("/notas/?limit=500"),api("/faturistas/?incluir_inativos=true")]);renderBillingOptions();applyFilters();renderFaturistas();$("lastUpdate").textContent=`Atualizado ${new Date().toLocaleTimeString("pt-BR")}`;if(!silent)toast("Dados atualizados")}catch(e){toast(e.message,true)}finally{refreshing=false}}
function applyFilters(){const q=$("searchInput").value.toLowerCase().trim(),local=$("localFilter").value,bill=$("billingFilter").value;filtered=notes.filter(n=>(!local||n.local===local)&&(!bill||n.faturista===bill)&&(!q||Object.values(n).some(v=>String(v??"").toLowerCase().includes(q))));render()}
function render(){const body=$("notesTable");body.innerHTML=filtered.map(n=>{
	const canDelete = currentUser?.role==="admin";
	return `<tr>
<td class="sticky"><div class="row-actions"><button title="Editar" onclick="editNote(${n.id})">✎</button><button title="Gerar XML" onclick="downloadXML(${n.id})">↓</button>${canDelete?`<button title="Excluir" onclick="askDelete(${n.id})">×</button>`:""}</div></td>
<td>${n.id}</td><td title="${esc(n.chave_acesso)}">${esc(n.chave_acesso)}</td><td>${date(n.data_cadastro)}</td><td>${date(n.data_emissao)}</td><td>${esc(n.nome_fornecedor)}</td><td><strong>${esc(n.numero_nf)}</strong></td>
<td><span class="badge">${esc(n.local||"—")}</span></td><td title="${esc(n.produto)}">${esc(n.produto||"—")}</td><td>${esc(n.quantidade||"—")}</td><td>${money(n.valor_total)}</td>
<td>${esc(n.transportador||"—")}</td><td>${esc(n.faturista||"BIPE")}</td><td>${esc(n.lider_operacional||"—")}</td><td>${esc(n.cnpj_fornecedor)}</td>
<td title="${esc(n.observacao)}">${esc(n.observacao||"—")}</td></tr>`}).join("");
$("emptyState").hidden=filtered.length>0;$("resultCount").textContent=`${filtered.length} registro(s)`;$("metricTotal").textContent=notes.length;$("metricWeight").textContent=new Intl.NumberFormat("pt-BR").format(notes.reduce((s,n)=>s+(n.quantidade||0),0));$("metricValue").textContent=money(notes.reduce((s,n)=>s+(n.valor_total||0),0));$("metricPending").textContent=notes.filter(n=>!n.lider_operacional).length}
function renderBillingOptions(){const active=faturistas.filter(f=>f.ativo),current=$("billingFilter").value;$("billingFilter").innerHTML='<option value="">Todos os faturistas</option>'+active.map(f=>`<option>${esc(f.nome)}</option>`).join("");$("billingFilter").value=current;$("faturista").innerHTML=active.map(f=>`<option>${esc(f.nome)}</option>`).join("")} 
function renderFaturistas(){const admin=currentUser?.role==="admin";$("billingList").innerHTML=faturistas.map(f=>`<div class="billing-item"><div class="${f.ativo?"":"inactive"}"><strong>${esc(f.nome)}</strong><small>${f.ativo?"Ativo":"Desativado"}</small></div><div>${f.nome==="BIPE"?"Padrão do app":`${admin?`<button class="secondary" onclick="editBilling(${f.id})">Editar senha</button><button class="danger" onclick="deleteBilling(${f.id})">Excluir</button><button class="secondary" onclick="toggleBilling(${f.id},${!f.ativo})">${f.ativo?"Desativar":"Reativar"}</button>`:"Somente administrador"}`}</div></div>`).join("")} 
function setBillingFormMode(mode,faturista=null){const editing=mode==="edit";$("billingId").value=editing?faturista?.id:"";$("billingName").value=editing?faturista?.nome:"";$("billingName").readOnly=editing;$("billingName").required=!editing;$("billingPassword").value="";$("billingPassword").required=true;$("billingSubmit").textContent=editing?"Salvar senha":"＋ Cadastrar";} 
function closeDialog(id){const dialog=$(id);if(dialog?.open){dialog.close()}if(id==="reportsDialog"){const reportsSection=$("reportsModalSection");reportsSection?.classList.remove("maximized")}} 
document.querySelectorAll("[data-close]").forEach(btn=>btn.addEventListener("click",e=>{e.preventDefault();const target=btn.dataset.close;if(target){closeDialog(target)}}));
document.querySelectorAll("[data-maximize]").forEach(btn=>btn.addEventListener("click",e=>{e.preventDefault();const target=document.getElementById(btn.dataset.maximize);if(target){target.classList.toggle("maximized")}}));
function fillNote(n,mode="edit"){fields.forEach(k=>{const el=$(k);let v=n[k]??"";if(k==="data_emissao"&&v)v=v.slice(0,16);el.value=v});const faturistaSelect=$("faturista");if(n.faturista&&![...faturistaSelect.options].some(o=>o.value===n.faturista)){faturistaSelect.insertAdjacentHTML("beforeend",`<option>${esc(n.faturista)}</option>`)}faturistaSelect.value=n.faturista||"BIPE";$("noteId").value=mode==="edit"?n.id:"";$("noteMode").textContent=mode==="edit"?"EDIÇÃO DE NOTA":"CONFERÊNCIA DA LEITURA";$("noteTitle").textContent=mode==="edit"?`Editar NF ${n.numero_nf}`:"Conferir nota fiscal";$("noteDialog").showModal()}
window.editNote=id=>fillNote(notes.find(n=>n.id===id));
async function downloadReport(params,name){try{const r=await fetch(`/relatorio/?${params}` ,{method:"POST"});if(!r.ok){const data=await r.json();throw new Error(data.detail||`Erro ${r.status}`)}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}catch(e){toast(e.message,true)}}
window.downloadXML=id=>downloadReport(`nota_id=${id}&formato=xml`,`nota_fiscal_${id}.xml`);
window.askDelete=id=>confirm("Excluir nota fiscal?","A nota será removida permanentemente.",async()=>{try{await api(`/notas/${id}/`,{method:"DELETE"});toast("Nota excluída");loadAll(true)}catch(e){toast(e.message,true)}})
window.toggleBilling=async(id,ativo)=>{const f=faturistas.find(x=>x.id===id);try{await api(`/faturistas/${id}/`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome:f.nome,ativo})});toast(ativo?"Faturista reativado":"Faturista desativado");loadAll(true)}catch(e){toast(e.message,true)}}
function confirm(title,message,callback){$("confirmTitle").textContent=title;$("confirmMessage").textContent=message;confirmCallback=callback;$("confirmDialog").showModal()}
$("confirmCancel").onclick=()=>$("confirmDialog").close();$("confirmAction").onclick=()=>{ $("confirmDialog").close();confirmCallback?.()};
$("noteForm").addEventListener("submit",async e=>{e.preventDefault();const payload={};fields.forEach(k=>payload[k]=$(k).value||null);payload.valor_total=Number(payload.valor_total||0);payload.quantidade=payload.quantidade?Number(payload.quantidade):null;payload.caminho_arquivo_imagem=null;const id=$("noteId").value;try{await api(id?`/notas/${id}/`:"/notas/",{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});$("noteDialog").close();toast(id?"Nota atualizada":"Nota cadastrada");loadAll(true)}catch(err){toast(err.message,true)}});
$("scanForm").addEventListener("submit",async e=>{e.preventDefault();try{const result=await api("/barcode-nf/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({codigo_barras:$("scanKey").value})});const n={...result.nota,local:$("scanLocal").value,faturista:"BIPE"};$("scanDialog").close();fillNote(n,"create")}catch(err){toast(err.message,true)}});
$("billingForm").addEventListener("submit",async e=>{e.preventDefault();const nome=$("billingName").value.trim();const senha=$("billingPassword").value.trim();const id=$("billingId").value;try{if(id){const faturista=faturistas.find(f=>f.id===Number(id));await api(`/faturistas/${id}/`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome:faturista.nome,ativo:faturista?.ativo??true,senha})});toast("Senha do faturista atualizada");}else{await api("/faturistas/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome,senha})});toast("Faturista cadastrado");}$("billingName").value="";$("billingPassword").value="";$("billingId").value="";setBillingFormMode("create");$("faturistasDialog").close();loadAll(true)}catch(err){toast(err.message,true)}});
function editBilling(id){const faturista=faturistas.find(f=>f.id===id);if(!faturista)return;setBillingFormMode("edit",faturista);$("billingPassword").focus();$("faturistasDialog").showModal();}
async function deleteBilling(id){const faturista=faturistas.find(f=>f.id===id);if(!faturista)return;confirm("Excluir faturista","Deseja realmente excluir este faturista?",async()=>{try{await api(`/faturistas/${id}/`,{method:"DELETE"});toast("Faturista excluído");loadAll(true)}catch(err){toast(err.message,true)}})}
$("loginForm").addEventListener("submit",async e=>{e.preventDefault();await loginUser();});
$("loginDialog").addEventListener("cancel",e=>{e.preventDefault();});
$("logoutButton").onclick=async()=>{try{await api("/auth/logout/",{method:"POST"});currentUser=null;$("logoutButton").hidden=true;$("userBadge").textContent="";showLogin("");}catch(err){toast(err.message,true)}};
$("openScan").onclick=()=>{$("scanForm").reset();$("scanDialog").showModal()};$("openFaturistas").addEventListener("click",async e=>{e.preventDefault();if(!currentUser||currentUser.role!=="admin")return;await loadAll(true);setBillingFormMode("create");const faturistasDialog=$("faturistasDialog"); faturistasDialog.showModal ? faturistasDialog.showModal() : faturistasDialog.show();});$("refreshButton").onclick=()=>loadAll();$("searchInput").oninput=applyFilters;$("localFilter").onchange=applyFilters;$("billingFilter").onchange=applyFilters;
$("downloadAll").onclick=()=>downloadReport("formato=xml","notas_fiscais.xml");
showLogin("");
(async()=>{if(await ensureAuthenticated()){loadAll(true);setInterval(()=>loadAll(true),4000);}})();

// Reports functionality
$("openReports").addEventListener("click",async e=>{e.preventDefault();if(!await ensureAuthenticated()) return;$("reportsDialog").showModal();await renderReports();});
let reportCharts = {};
function destroyReports(){Object.values(reportCharts).forEach(c=>{try{c.destroy()}catch{} }); reportCharts={};}
async function renderReports(){try{if(!notes || notes.length===0){await loadAll(true)}const data = notes;
		const total = data.length;
		const totalValue = data.reduce((s,n)=>s+(n.valor_total||0),0);
		const totalWeight = data.reduce((s,n)=>s+(n.quantidade||0),0);
		const suppliers = new Set(data.map(n=>n.nome_fornecedor||""));
		$("reportsTotal").textContent=total;$("reportsValue").textContent=money(totalValue);$("reportsWeight").textContent=new Intl.NumberFormat("pt-BR").format(totalWeight)+" kg";$("reportsSuppliers").textContent=suppliers.size;

		const byLocal = data.reduce((acc,n)=>{const k=n.local||"Não alocado";acc[k]=(acc[k]||0)+1;return acc},{})
		const localLabels = Object.keys(byLocal);const localValues = localLabels.map(l=>byLocal[l]);

		const prodMap = data.reduce((acc,n)=>{const k=(n.produto||"(sem produto)").trim();acc[k]=(acc[k]||0)+1;return acc},{})
		const prodPairs = Object.entries(prodMap).sort((a,b)=>b[1]-a[1]).slice(0,10);
		const prodLabels = prodPairs.map(p=>p[0]);const prodValues = prodPairs.map(p=>p[1]);

		const valMap = data.reduce((acc,n)=>{const k=(n.nome_fornecedor||"(sem fornecedor)").trim();acc[k]=(acc[k]||0)+(n.valor_total||0);return acc},{})
		const valPairs = Object.entries(valMap).sort((a,b)=>b[1]-a[1]).slice(0,10);
		const valLabels = valPairs.map(p=>p[0]);const valValues = valPairs.map(p=>p[1]);

		const monthMap = data.reduce((acc,n)=>{const d=n.data_emissao?new Date(n.data_emissao):null;const k=d?`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`:"(sem data)";acc[k]=(acc[k]||0)+1;return acc},{})
		const monthPairs = Object.entries(monthMap).sort((a,b)=>a[0].localeCompare(b[0]));const monthLabels = monthPairs.map(p=>p[0]);const monthValues = monthPairs.map(p=>p[1]);

		destroyReports();
		const ctxLocal = document.getElementById('chartByLocal').getContext('2d');
		reportCharts.local = new Chart(ctxLocal,{type:'doughnut',data:{labels:localLabels,datasets:[{data:localValues,backgroundColor:['#4e79a7','#f28e2b','#e15759','#76b7b2']}]},options:{plugins:{legend:{position:'right',labels:{color:'#222',font:{weight:'700',size:14}}},title:{display:true,text:'Notas por local',color:'#111',font:{weight:'800',size:18}}},elements:{arc:{borderWidth:1,borderColor:'#fff'}},layout:{padding:12}},plugins:[chartDataLabelPlugin]});

		const ctxProd = document.getElementById('chartByProduct').getContext('2d');
		reportCharts.prod = new Chart(ctxProd,{
			type:'bar',
			data:{
				labels:prodLabels,
				datasets:[{label:'Quantidade',data:prodValues,backgroundColor:'#3d7a3f',borderColor:'#315f34',borderWidth:1}],
			},
			options:{
				indexAxis:'y',
				plugins:{legend:{display:false},title:{display:true,text:'Top 10 produtos por volume',color:'#111',font:{weight:'800',size:18}}},
				scales:{
					x:{title:{display:true,text:'Quantidade',color:'#111',font:{size:14}},ticks:{color:'#111',font:{size:13}}},
					y:{title:{display:false},ticks:{color:'#111',font:{size:13}}},
				},
			},
			plugins:[chartDataLabelPlugin],
		});

		const ctxVal = document.getElementById('chartValueBySupplier').getContext('2d');
		reportCharts.val = new Chart(ctxVal, {
			type: 'bar',
			data: {
				labels: valLabels,
				datasets: [{label: 'Valor (R$)', data: valValues, backgroundColor: '#edc948',borderColor:'#caa937',borderWidth:1}],
			},
			options: {
				plugins: {legend: {display: false}, title: {display: true, text: 'Top 10 fornecedores por valor',color:'#111',font:{weight:'800',size:18}}},
				scales: {
					y: {
						ticks: {
							callback: v => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(v),
							color:'#111',
							font:{size:13},
						},
						title:{display:true,text:'Valor (R$)',color:'#111',font:{size:14}},
					},
					x: {
						ticks:{color:'#111',font:{size:13}},
						title:{display:true,text:'Fornecedores',color:'#111',font:{size:14}},
					},
				},
			},
			plugins:[chartDataLabelPlugin],
		});
		reportCharts.month = new Chart(ctxMonth, {
			type: 'line',
			data: {
				labels: monthLabels,
				datasets: [{
					label: 'Notas por mês',
					data: monthValues,
					borderColor: '#1b1b1b',
					backgroundColor: 'rgba(27,27,27,0.22)',
					fill: true,
					pointBackgroundColor:'#111',
					pointBorderColor:'#fff',
					pointRadius:5,
				}],
			},
			options: {
				plugins: {legend: {display: false}, title: {display: true, text: 'Notas por mês',color:'#111',font:{weight:'800',size:18}}},
				scales: {
					x: {
						ticks: {maxRotation: 0,color:'#111',font:{size:13}},
						title:{display:true,text:'Mês',color:'#111',font:{size:14}},
					},
					y: {
						ticks: {
							precision: 0,
							color:'#111',
							font:{size:13},
						},
						title:{display:true,text:'Notas',color:'#111',font:{size:14}},
					},
				},
			},
			plugins:[chartDataLabelPlugin],
		});

		const materialBySector = data.reduce((acc,n)=>{
			const material=(n.produto||"(sem produto)").trim()||"(sem produto)";
			const sector=n.local||"Não alocado";
			if(!acc[material]){acc[material]={};}
			acc[material][sector]=(acc[material][sector]||0)+(n.quantidade||0);
			return acc;
		},{})
		const orderedMaterials = Object.entries(materialBySector)
			.map(([material, sectors]) => [material, sectors])
			.sort((a,b)=>{const totalA=Object.values(a[1]).reduce((sum,v)=>sum+v,0);const totalB=Object.values(b[1]).reduce((sum,v)=>sum+v,0);return totalB-totalA});
		const materialLabels = orderedMaterials.map(([material])=>material);
		const fixedSectors = ["A1BR","A1BR/PRU","A2BR"];
		const extraSectors = Array.from(new Set(Object.values(materialBySector).flatMap(sectors=>Object.keys(sectors)).filter(s=>!fixedSectors.includes(s))));
		const sectorKeys = fixedSectors.concat(extraSectors);
		const sectorColors = ['#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f','#edc948'];
		const materialDatasets = sectorKeys.map((sector,index)=>({
			label: sector,
			data: materialLabels.map(material => materialBySector[material][sector]||0),
			backgroundColor: sectorColors[index % sectorColors.length],
		}));

		const ctxMaterial = document.getElementById('chartMaterialBySector').getContext('2d');
		reportCharts.material = new Chart(ctxMaterial, {
			type: 'bar',
			data: {
				labels: materialLabels,
				datasets: materialDatasets,
			},
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {position: 'bottom', labels:{color:'#111',font:{weight:'700',size:14}}},
					title: {display: true, text: 'Quantidade por tipo de material e setor',color:'#111',font:{weight:'800',size:18}},
				},
				scales: {
					x: {title: {display: true, text: 'Quantidade',color:'#111',font:{size:14}},ticks:{color:'#111',font:{size:13}}},
					y: {title: {display: true, text: 'Material',color:'#111',font:{size:14}},ticks:{color:'#111',font:{size:13}}},
				},
			},
			plugins:[chartDataLabelPlugin],
		});
	}catch(e){toast(e.message,true)} }
