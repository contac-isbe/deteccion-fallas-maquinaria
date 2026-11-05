"use strict";
const monitorUnits={"Rotational speed [rpm]":"rpm","Torque [Nm]":"Nm","Air temperature [K]":"K","Process temperature [K]":"K","Tool wear [min]":"min"};
let chartFeature="Rotational speed [rpm]";
let monitorState=null;
let lastDrawKey="";
const svgNS="http://www.w3.org/2000/svg";
function svgElement(tag,attrs={},text){const e=document.createElementNS(svgNS,tag);for(const [name,value] of Object.entries(attrs))e.setAttribute(name,value);if(text!==undefined)e.textContent=text;return e;}
function numberLabel(value){return Number(value).toLocaleString('es-PE',{maximumFractionDigits:1});}
function coordinates(rows,feature,width,height,padX,padY){
  const values=rows.map(row=>row[feature]);
  let min=Math.min(...values),max=Math.max(...values);
  const margin=Math.max((max-min)*.13,Math.abs(max)*.015,.1);min-=margin;max+=margin;
  return {min,max,points:values.map((v,i)=>({x:rows.length===1?width/2:padX+i*(width-2*padX)/(rows.length-1),y:height-padY-(v-min)*(height-2*padY)/(max-min),value:v}))};
}
function drawCharts(state){
  const rows=state.series || [];
  const chart=document.getElementById('trace');chart.replaceChildren();
  const width=Math.max(chart.clientWidth || 760,280),height=190,padX=44,padY=25;
  chart.setAttribute('viewBox',`0 0 ${width} ${height}`);
  document.getElementById('chart-empty').hidden=rows.length>0;
  const featureUnit=monitorUnits[chartFeature];
  document.getElementById('chart-current').textContent=rows.length?`${numberLabel(rows.at(-1)[chartFeature])} ${featureUnit}`:`— ${featureUnit}`;
  const scale=rows.length?coordinates(rows,chartFeature,width,height,padX,padY):null;
  for(let i=0;i<4;i++){
    const y=padY+i*(height-2*padY)/3;
    chart.append(svgElement('line',{x1:padX,x2:width-padX,y1:y,y2:y,stroke:'#e8e3f0','stroke-dasharray':'4 5'}));
    if(scale)chart.append(svgElement('text',{x:padX-10,y:y+4,'text-anchor':'end',class:'chart-axis'},numberLabel(scale.max-i*(scale.max-scale.min)/3)));
  }
  if(rows.length){
    const {points}=scale;
    const line=points.map((p,i)=>`${i?'L':'M'}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ');
    const defs=svgElement('defs');const gradient=svgElement('linearGradient',{id:'trace-fill',x1:'0',y1:'0',x2:'0',y2:'1'});gradient.append(svgElement('stop',{offset:'0%','stop-color':'#8270d8','stop-opacity':'.2'}),svgElement('stop',{offset:'100%','stop-color':'#8270d8','stop-opacity':'.01'}));defs.append(gradient);chart.append(defs);
    chart.append(svgElement('path',{d:`${line} L${points.at(-1).x} ${height-padY} L${points[0].x} ${height-padY} Z`,fill:'url(#trace-fill)'}));
    chart.append(svgElement('path',{d:line,fill:'none',stroke:'#7761c3','stroke-width':'2.3','stroke-linejoin':'round','stroke-linecap':'round'}));
    points.forEach((p,i)=>{
      if(rows[i].alert || i===points.length-1){
        const dot=svgElement('circle',{cx:p.x,cy:p.y,r:rows[i].alert?4.5:3.5,fill:rows[i].alert?'#c8784c':'#7761c3',stroke:'#fff','stroke-width':'2'});
        dot.append(svgElement('title',{},`UDI ${rows[i].UDI}: ${numberLabel(p.value)} ${featureUnit}${rows[i].alert?' · Predicción de falla':''}`));chart.append(dot);
      }
    });
    chart.append(svgElement('text',{x:padX,y:height-3,class:'chart-axis'},`#${state.processed-rows.length+1}`));
    if(rows.length>1)chart.append(svgElement('text',{x:width-padX,y:height-3,'text-anchor':'end',class:'chart-axis'},`#${state.processed}`));
    chart.setAttribute('aria-label',`${chartFeature}: ${rows.length} registros procesados en orden de reproducción, del UDI ${rows[0].UDI} al UDI ${rows.at(-1).UDI}. Último valor ${numberLabel(rows.at(-1)[chartFeature])} ${featureUnit}.`);
  }else chart.setAttribute('aria-label','Sin registros procesados. El gráfico aparecerá al avanzar la simulación.');
  document.getElementById('chart-range').textContent=rows.length?`${rows.length} registros · Escala ${featureUnit}`:'Sin registros';
  for(const spark of document.querySelectorAll('[data-spark]')){
    spark.replaceChildren();
    if(!rows.length)continue;
    const sparkPoints=coordinates(rows,spark.dataset.spark,160,28,2,3).points;
    spark.append(svgElement('path',{d:sparkPoints.map((p,i)=>`${i?'L':'M'}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' '),fill:'none',stroke:'#a18cd1','stroke-width':'1.5','stroke-linecap':'round','stroke-linejoin':'round'}));
  }
}
function updateMonitor(state){
  monitorState=state;
  document.body.dataset.run=state.status;
  document.body.dataset.alert=String(Boolean(state.last?.alert));
  const key=`${state.processed}/${state.last?.UDI || ''}`;
  if(key===lastDrawKey)return;
  lastDrawKey=key;
  const row=state.last;
  document.getElementById('machine-rpm').textContent=row?`${numberLabel(row['Rotational speed [rpm]'])} rpm`:'— rpm';
  document.getElementById('machine-torque').textContent=row?`${numberLabel(row['Torque [Nm]'])} Nm`:'— Nm';
  document.getElementById('decision-explanation').textContent=!row?'El árbol de decisión analizará las seis variables de cada registro.':row.alert?'El patrón de esta observación fue clasificado como una condición con falla.':'El modelo no detectó una condición de falla en esta observación.';
  const alerts=(state.series || []).filter(r=>r.alert).reverse();
  document.getElementById('window-alerts').textContent=alerts.length;
  const feed=document.getElementById('alert-feed');feed.replaceChildren();
  if(!alerts.length){const empty=document.createElement('div');empty.className='alert-empty';empty.textContent=state.processed?'Sin predicciones de falla en esta ventana.':'Todo empieza con una observación.';const p=document.createElement('p');p.textContent='Aquí aparecen las alertas de los últimos 60 registros procesados.';empty.append(p);feed.append(empty);}
  for(const alert of alerts.slice(0,5)){
    const item=document.createElement('div');item.className='alert-event';
    const symbol=document.createElement('span');symbol.className='alert-event-icon';symbol.textContent='!';
    const text=document.createElement('div');const title=document.createElement('strong');title.textContent=`UDI ${alert.UDI}`;
    const description=document.createElement('span');description.textContent=alert.outcome==='FP'?'Falsa alarma · Etiqueta sin falla':'Falla detectada · Etiqueta con falla';text.append(title,description);
    const tag=document.createElement('span');tag.className='alert-event-type';tag.textContent=alert.Type;item.append(symbol,text,tag);feed.append(item);
  }
  drawCharts(state);
  if(row && !matchMedia('(prefers-reduced-motion: reduce)').matches){for(const value of document.querySelectorAll('.sensor>strong'))value.animate([{opacity:.35},{opacity:1}],{duration:250});}
}
document.querySelectorAll('[data-feature]').forEach(button=>button.addEventListener('click',()=>{
  chartFeature=button.dataset.feature;
  document.querySelectorAll('[data-feature]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  if(monitorState)drawCharts(monitorState);
}));
window.addEventListener('simulation-state',event=>updateMonitor(event.detail));
window.addEventListener('portal-panel',event=>{if(event.detail==='ejecucion' && monitorState)requestAnimationFrame(()=>drawCharts(monitorState));});
let monitorResizeFrame;
window.addEventListener('resize',()=>{cancelAnimationFrame(monitorResizeFrame);monitorResizeFrame=requestAnimationFrame(()=>{if(monitorState)drawCharts(monitorState);});});
if(typeof lastState!=='undefined' && lastState)updateMonitor(lastState);
