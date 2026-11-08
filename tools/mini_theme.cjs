'use strict';
// Map fixed website declarations to native page containers; never invent theme values.
function functionalTheme(theme){
 const find=(source,selector,mobile=false)=>{const r=theme.rules.find(x=>x.source===source&&x.selector===selector&&(mobile?x.conditions.some(c=>/max-width:600px/.test(c)):!x.conditions.length));if(!r)throw Error('主题选择器漂移：'+selector);return Object.fromEntries(r.declarations.split(';').map(s=>s.trim()).filter(Boolean).map(s=>{const i=s.indexOf(':');return [s.slice(0,i).trim(),s.slice(i+1).trim()];}));};
 const resolve=value=>value.replace(/var\((--[a-z-]+)\)/g,(_,n)=>{if(!theme.tokens[n])throw Error('主题变量缺失');return theme.tokens[n];}).replace(/([\d.]+)rem/g,(_,n)=>Number(n)*16+'px');
 const rule=(selector,values)=>selector+'{'+Object.entries(values).map(([k,v])=>k+':'+resolve(v)).join(';')+'}\n';
 const body=find('theme.css','body.rp-page'),mobile=find('theme.css','body.rp-page',true),h1=find('theme.css','.rp-page h1'),panel=find('theme.css','.rp-page .panel, .rp-page .score-form, .rp-page .summary, .rp-page .feedback-card, .rp-page main > section:not(.panel)'),inner=find('theme.css','.rp-page .panel, .rp-page main > section:not(.panel)',true),spacing=find('theme.css','.rp-page > header, .rp-page > main, .rp-page > footer',true);
 return '/* Generated mobile theme mapping; rem uses the website root 16px. */\n'+
 rule('.mirror-page',{padding:mobile.margin.split(' ')[0],'font-size':body['font-size'],'line-height':body['line-height']})+
 rule('.mirror-page>.mirror-surface.panel',{background:body.background,border:body.border,'border-radius':mobile['border-radius'],padding:spacing.padding,margin:'0'})+
 rule('.mirror-page .panel',{background:panel.background,border:panel.border,'border-radius':panel['border-radius'],padding:inner.padding,'margin-bottom':'20px'})+
 rule('.mirror-page .page-title',h1)+
 '.mirror-page .heading{font-size:17.6px;font-weight:600;margin:16px 0 8px}.mirror-page .muted,.mirror-page .tag{font-size:13.6px;color:'+theme.tokens['--rp-muted']+'}\n'+
 '.mirror-page button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;padding:8px 13px;border-radius:8px;line-height:1.4}.mirror-page .field-label{font-size:14px;margin-bottom:5px}\n';
}
module.exports={functionalTheme};
