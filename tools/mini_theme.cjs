'use strict';
// Map fixed website declarations to native page containers; never invent theme values.
function functionalTheme(theme){
 const find=(source,selector,mobile=false)=>{const r=theme.rules.find(x=>x.source===source&&x.selector===selector&&(mobile?x.conditions.some(c=>/max-width:600px/.test(c)):!x.conditions.length));if(!r)throw Error('主题选择器漂移：'+selector);return Object.fromEntries(r.declarations.split(';').map(s=>s.trim()).filter(Boolean).map(s=>{const i=s.indexOf(':');return [s.slice(0,i).trim(),s.slice(i+1).trim()];}));};
 const resolve=value=>value.replace(/var\((--[a-z0-9-]+)\)/g,(_,n)=>{if(!theme.tokens[n])throw Error('主题变量缺失');return theme.tokens[n];}).replace(/([\d.]+)rem/g,(_,n)=>Number(n)*16+'px');
 const rule=(selector,values)=>selector+'{'+Object.entries(values).map(([k,v])=>k+':'+resolve(v)).join(';')+'}\n';
 const body=find('theme.css','body.rp-page'),mobile=find('theme.css','body.rp-page',true),h1=find('theme.css','.rp-page h1'),panel=find('theme.css','.rp-page .panel, .rp-page .score-form, .rp-page .summary, .rp-page .feedback-card, .rp-page main > section:not(.panel)'),inner=find('theme.css','.rp-page .panel, .rp-page main > section:not(.panel)',true),spacing=find('theme.css','.rp-page > header, .rp-page > main, .rp-page > footer',true);
 const portrait='@media (max-width: 640px) and (orientation: portrait)';
 const narrow='@media (max-width: 640px)';
 const lookup=(file,selector,condition)=> {
  const source=theme.rules.filter(r=>r.source===file&&r.selector.replace(/\s+/g,' ')===selector&&
   (condition?r.conditions.includes(condition):!r.conditions.length));
  if(!source.length)throw Error('主题选择器漂移：'+selector);
  return Object.assign({},...source.map(r=>Object.fromEntries(r.declarations.split(';').map(d=>d.trim())
   .filter(Boolean).map(d=>{const i=d.indexOf(':');return [d.slice(0,i).trim(),d.slice(i+1).trim()];}))));
 };
 const styles=(selector,condition)=>lookup('styles.css',selector,condition);
 const select=(values,properties)=>Object.fromEntries(properties.map(key=>[key,values[key]]).filter(([,value])=>value!==undefined));
 const mapRules=(mappings,condition)=>mappings.map(([web,native,properties])=>{
  const values=styles(web,condition);
  return rule(native,properties?select(values,properties):values);
 }).join('');
 const selectProperties=['width','min-height','padding','background','border','color','border-radius','font-size','line-height'];
 const mapSelect='.map-section .map-fields .select, .ocr-workspace .map-fields .select';
 const schemeSelect='.results .result-toolbar .scheme-select';
 const garageButtons='.garage .garage-action-group button';
 const dialogButton='.map-ban-dialog .map-ban-actions button';
 const resultLayout=styles('#resultGrid .result-item',portrait);
 const mobileResults=mapRules([
  ['.result-panel','.results .result-toolbar',['gap','align-items']],
  ['#resultGrid','.results .result-grid'],
  ['#resultGrid .result-item','.results .result-row',['padding','text-align']],
  ['#resultGrid .result-map','.results .result-map',['margin','font-size','overflow-wrap']],
  ['#resultGrid .result-bigmap','.results .result-big',['margin','font-size','overflow-wrap']],
  ['#resultGrid .result-car','.results .result-car',['font-size','padding','overflow-wrap']],
  ['#resultGrid .result-car.empty','.results .result-car.empty',['text-align']],
  ['#resultGrid .result-stars','.results .result-stars'],
  ['#resultGrid .result-score','.results .result-time',['margin','font-size','text-align','white-space']],
  ['#mapRowsContainer .map-row','.map-section .map-row, .ocr-workspace .map-row',['gap','padding']],
  ['#mapRowsContainer .map-index','.map-section .map-row .number, .ocr-workspace .map-row .number'],
  ['#mapRowsContainer select',mapSelect,['min-height','padding','font-size','text-overflow']],
  ['.garage-actions button',garageButtons,['min-height','font-size']],
 ],portrait)+
 rule('.results .result-main',{display:resultLayout.display,...select(resultLayout,['grid-template-columns','align-items','gap'])})+
 rule('.results .result-row, .results .result-track',{display:'grid','row-gap':resultLayout.gap.split(' ')[0]});
 const narrowGarage=mapRules([
  ['.garage-body > .garage-actions','.garage .garage-actions'],
  ['.garage-action-group','.garage .garage-action-group'],
  ['.garage-actions #garageSaveStatus','.garage .garage-actions .save-status'],
 ],narrow)+rule(garageButtons,{flex:styles('.garage-action-group button',narrow).flex,
  'padding-left':styles('.garage-action-group button',narrow)['padding-inline'],
  'padding-right':styles('.garage-action-group button',narrow)['padding-inline']});
 const routeToggle='.results .route-row .route-toggle';
 const touchCondition='@media(max-width:700px)';
 const touchButton=lookup('ui.css','button,.ui-button',touchCondition);
 const picker=styles('.result-guidance-picker');
 const dialog=lookup('theme.css','.rp-page dialog');
 const homeControls=mapRules([
  ['.action','.page .action'],
  ['.recommend-btn','.page .action .recommend-btn',['min-height','padding','background','border','color','font-weight','font-size','line-height','border-radius']],
  ['.recommend-btn:hover','.page .action .recommend-btn.button-hover',['background']],
  ['.garage-body > .garage-actions','.garage .garage-actions'],
  ['.garage-actions','.garage .garage-actions'],
  ['.garage-action-group','.garage .garage-action-group'],
  ['.garage-actions button,.garage-confirm button',garageButtons,['background','color']],
  ['.garage-actions button',garageButtons,['display','align-items','justify-content','flex','min-height','padding','border','border-radius','font-size','line-height','white-space','word-break','overflow-wrap']],
  ['.garage-actions #garageSaveStatus','.garage .garage-actions .save-status'],
  ['.result-panel','.page .results'],
  ['.result-title','.results .result-toolbar .result-heading'],
  ['.badge-pareto','.results .result-toolbar .badge'],
  ['select',mapSelect,selectProperties],
  ['select',schemeSelect,selectProperties],
  ['.scheme-selector select',schemeSelect],
  ['.result-grid','.results .result-grid'],
  ['.result-item','.results .result-row',['min-width','background','border-radius','padding','text-align','border']],
  ['.result-item.is-empty','.results .result-row.is-empty'],
  ['.result-map','.results .result-map'],
  ['.result-bigmap','.results .result-big'],
  ['.result-car','.results .result-car'],
  ['.result-item.is-empty .result-car.empty','.results .result-row.is-empty .result-car.empty'],
  ['.result-stars','.results .result-stars'],
  ['.result-item .result-score','.results .result-time'],
  ['.result-unit','.results .result-unit'],
  ['.sc-control','.results .route-row'],
  ['.sc-control .sc-toggle',routeToggle,['display','flex','white-space','align-items','gap','padding','border','border-radius','background','color','font-size']],
  ['.sc-control .sc-select','.results .route-row .route-select',['min-width','max-width','margin','padding','border','border-radius','background','color','font-size']],
  ['.result-guidance-picker h2','.map-ban-dialog .map-ban-title'],
  ['.result-guidance-picker button, .result-guidance .ui-button',dialogButton,['display','align-items','justify-content','min-height','padding','border','border-radius','background','color','font-size','line-height']],
  ['.result-guidance-picker button.ui-primary',dialogButton+'.primary'],
  ['.map-ban-list','.map-ban-dialog .map-ban-choices',['margin','gap']],
  ['.map-ban-list label','.map-ban-dialog .map-ban-choice',['display','align-items','flex-wrap','gap','min-height','border-bottom','overflow-wrap']],
  ['.map-ban-list label span','.map-ban-dialog .map-ban-current'],
  ['.map-ban-actions','.map-ban-dialog .map-ban-actions'],
 ])+rule('.page.home-page, .map-ban-dialog',select(body,['font-size','line-height']))+
 rule(routeToggle,{'line-height':body['line-height']})+
 rule('.hub-dialog.map-ban-dialog',{...select(picker,['width','max-height','background','color','border','border-radius','box-shadow']),...dialog})+
 rule('.map-ban-dialog .map-ban-content',{padding:picker.padding});
 const sharedHomeStyles=[
  ['.toggle-group','.toolbar .mode-row',['gap','padding','border','border-radius','background']],
  ['.toggle-group button.active, .toggle-group .toggle-choice.active','.toolbar .toggle-choice.active',['background','color','font-weight']],
  ['.car-tag','.garage .car-row',['background','color','border','border-radius','font-size','line-height']],
  ['.car-tag.selected','.garage .car-row.selected',['background','color','border-color','font-weight']],
  ['.star-display','.garage .star-select',['color','border-radius','line-height']],
  ['.class-filter-btn','.garage .class-filter button',['background','color','border','border-radius','font-size','line-height']],
  ['.class-filter-btn.active','.garage .class-filter button.active',['background','color','border-color']],
  ['.garage-search','.garage .search',['background','color','border','border-radius','font-size']],
  ['.sc-control.is-on','.results .route-row.is-on',['background','color','border-color']],
  ['.map-ban-hint','.map-ban-dialog .map-ban-hint',['color','font-size','line-height']],
  ['#resultGrid .map-ban-trigger','.results .result-car .map-ban-trigger',['min-height','padding','border','border-radius','background','color','font-size','white-space']],
  ['#resultGrid .map-ban-trigger[data-active]','.results .result-car .map-ban-trigger.is-active',['color']],
  ['.route-video-links','.route-video-group',['display','gap','margin-top','font-size','line-height','overflow-wrap']],
  ['.route-video-links a','.route-video-group .top-video-link',['color']],
  ['.route-video-links summary','.route-video-group .top-videos-toggle',['color']],
 ];
 const homeStyles=mapRules(sharedHomeStyles);
 return '/* Generated mobile theme mapping; rem uses the website root 16px. */\n'+
 rule('.mirror-page',{padding:mobile.margin.split(' ')[0],'font-size':body['font-size'],'line-height':body['line-height']})+
 rule('.mirror-page>.mirror-surface.panel',{background:body.background,border:body.border,'border-radius':mobile['border-radius'],padding:spacing.padding,margin:'0'})+
 rule('.mirror-page .panel',{background:panel.background,border:panel.border,'border-radius':panel['border-radius'],padding:inner.padding,'margin-bottom':'20px'})+
 rule('.mirror-page .page-title',h1)+
 '.mirror-page .heading{font-size:17.6px;font-weight:600;margin:16px 0 8px}.mirror-page .muted,.mirror-page .tag{font-size:13.6px;color:'+(theme.tokens['--rp-text-2']||theme.tokens['--rp-muted'])+'}\n'+
 '.mirror-page button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;padding:8px 13px;border-radius:8px;line-height:1.4}.mirror-page .field-label{font-size:14px;margin-bottom:5px}\n'+
 homeStyles+homeControls+
 portrait+'{\n'+mobileResults+'}\n'+narrow+'{\n'+narrowGarage+'}\n'+
 touchCondition+'{'+rule(routeToggle,touchButton)+'}\n';
}
module.exports={functionalTheme};
