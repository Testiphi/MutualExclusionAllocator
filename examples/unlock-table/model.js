(function(root) {
  'use strict';
  const maps = [
    {id:'city', name:'城市赛道', subtitle:'街区与高架', tracks:['中心街区','环城高架']},
    {id:'coast', name:'海岸赛道', subtitle:'海湾与港口', tracks:['沿海公路','港口弯道']},
    {id:'mountain', name:'山地赛道', subtitle:'山路与峡谷', tracks:['盘山公路','峡谷隧道']}
  ];
  const profiles = {
    guest:{name:'游客',points:0,valid:0,high:0,logged:false},
    near:{name:'即将解锁',points:42,valid:4,high:2,logged:true},
    choose:{name:'一级 · 待选地图',points:75,valid:6,high:3,logged:true},
    partial:{name:'一级 · 已选海岸',points:75,valid:6,high:3,logged:true,chosen:'coast'},
    full:{name:'二级 · 全部开放',points:168,valid:16,high:6,logged:true}
  };
  function level(p) {
    if (!p.logged) return 0;
    if (p.points>=150 && p.valid>=15 && p.high>=5) return 2;
    return p.points>=50 && p.valid>=5 ? 1 : 0;
  }
  function canRead(p,id) { return maps.some(m=>m.id===id) && !!p.logged && (level(p)===2 || (level(p)===1 && p.chosen===id)); }
  function choose(p,id) {
    if (!maps.some(m=>m.id===id) || level(p)!==1 || p.chosen) throw Error('当前状态不能选择地图');
    return {...p,chosen:id};
  }
  function next(p) {
    const target=level(p)>=1?{points:150,valid:15,high:5}:{points:50,valid:5};
    return Object.fromEntries(Object.entries(target).map(([k,v])=>[k,Math.max(0,v-p[k])]));
  }
  // Entirely fictional records. No repository score or workbook is read.
  const rows = [];
  maps.forEach((m,mi)=>m.tracks.forEach((track,ti)=>{
    ['五区','四区'].forEach((zone,zi)=>['理论','高手'].forEach((tier,ki)=>{
      ['演示车辆 A','演示车辆 B','演示车辆 C'].forEach((car,ci)=>rows.push({
        map:m.id,track,zone,tier,car,stars:tier==='理论'?6:5,
        route:ci===2?'特殊跑法':'普通跑法',time:(36+mi*7+ti*4+zi*1.2+ki*.6+ci*.48).toFixed(3)
      }));
    }));
  }));
  const api={maps,profiles,level,canRead,choose,next,rows};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else root.UnlockDemo=api;
})(typeof globalThis!=='undefined'?globalThis:this);
