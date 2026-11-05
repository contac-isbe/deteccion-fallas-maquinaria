"use strict";
const panels = [...document.querySelectorAll('[role="tabpanel"]')];
const tabs = [...document.querySelectorAll('[role="tab"]')];
const titles = {documentacion:["Detrás del modelo","Los datos, las decisiones y los resultados de nuestro proyecto."],codigo:["Explora el código","Consulta los archivos y descubre cómo ejecutar el sistema."],ejecucion:["Monitor de maquinaria","Pon en marcha los registros y observa cómo responde el modelo."]};
function selectPanel(name, focus=false) {
  if(!titles[name]) name="ejecucion";
  for(const p of panels) p.hidden=p.id!==name;
  for(const t of tabs){const active=t.dataset.panel===name;t.setAttribute("aria-selected",String(active));t.tabIndex=active?0:-1;if(active && focus)t.focus();}
  document.getElementById("page-title").textContent=titles[name][0];
  document.getElementById("page-description").textContent=titles[name][1];
  document.title=`${titles[name][0]} · Detección de fallas`;
  history.replaceState(null,"",`#${name}`);
  window.dispatchEvent(new CustomEvent("portal-panel",{detail:name}));
}
tabs.forEach((tab,index)=>{
  tab.addEventListener("click",()=>selectPanel(tab.dataset.panel));
  tab.addEventListener("keydown",event=>{
    if(!["ArrowDown","ArrowUp","ArrowRight","ArrowLeft","Home","End"].includes(event.key))return;
    event.preventDefault();
    const next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(index+(["ArrowDown","ArrowRight"].includes(event.key)?1:-1)+tabs.length)%tabs.length;
    selectPanel(tabs[next].dataset.panel,true);
  });
});
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>{selectPanel(b.dataset.go);document.getElementById('page-title').scrollIntoView({block:'start'});}));
selectPanel(location.hash.slice(1));
const percent=x=>(100*x).toLocaleString('es-PE',{minimumFractionDigits:2,maximumFractionDigits:2})+' %';
let sourceRequest=0;
async function showSource(path){
  const generation=++sourceRequest;
  document.getElementById('source-title').textContent=path;
  document.getElementById('source-content').textContent='Cargando archivo…';
  document.getElementById('source-download').href='/project/file?file='+encodeURIComponent(path);
  document.querySelectorAll('[data-source]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.source===path)));
  try{const response=await fetch('/api/source?file='+encodeURIComponent(path));const data=await response.json();if(!response.ok)throw new Error(data.error);if(generation!==sourceRequest)return;document.getElementById('source-content').textContent=data.content;document.getElementById('source-note').textContent=data.notebook?'Vista de las celdas de explicación y código. Descarga el notebook para consultar sus salidas y gráficos.':'Vista de lectura. Los cambios se realizan en los archivos locales del proyecto.';}
  catch(error){if(generation===sourceRequest)document.getElementById('source-content').textContent='No se pudo cargar: '+error.message;}
}
async function loadProject(){
  try{
    const response=await fetch('/api/project');if(!response.ok)throw new Error('No se pudo consultar la documentación local.');const p=await response.json();
    const values={precision:percent(p.metrics.precision),recall:percent(p.metrics.recall),f1:p.metrics.f1.toFixed(4),accuracy:percent(p.metrics.accuracy),tn:p.metrics.true_negative,fp:p.metrics.false_positive,fn:p.metrics.false_negative,tp:p.metrics.true_positive,'check-count':p.verification.checks,'check-result':p.verification.all_passed?'Comprobaciones base superadas':'Revisar comprobaciones','base-revision':p.base_revision,'model-name':p.model};
    for(const [id,value] of Object.entries(values))document.getElementById(id).textContent=value;
    document.getElementById('checks-date').textContent='Ejecución registrada: '+new Date(p.verification.generated_at_utc).toLocaleString('es-PE');
    if(p.runtime?.mode==='web'){document.getElementById('runtime-label').textContent='Sesión web';document.getElementById('session-help').textContent='Tu simulación es independiente de otros navegadores. Las pestañas del mismo navegador comparten sesión. Cambiar de sección no pausa la reproducción. El avance se pierde si el servicio reinicia o tras 15 minutos sin solicitudes: exporta el CSV para conservarlo.';document.getElementById('publication-help').textContent='Aplicación web de demostración. Los archivos y las instrucciones se encuentran en el repositorio. El servicio gratuito puede tardar en arrancar después de un periodo sin visitas.';}
    const tree=document.getElementById('source-tree');
    for(const path of p.source_files){const button=document.createElement('button');button.type='button';button.dataset.source=path;button.title=path;button.textContent=path;button.addEventListener('click',()=>showSource(path));tree.append(button);}
    showSource('README.md');
  }catch(error){document.getElementById('project-error').hidden=false;document.getElementById('project-error').textContent=error.message;}
}
document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);button.textContent='Copiado';}
  catch(_error){button.textContent='Selecciona y copia el comando';}
}));
loadProject();
