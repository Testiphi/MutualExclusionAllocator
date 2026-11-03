(function(root){
    'use strict';
    function validMaps(maps,catalog){
        return Array.isArray(maps)&&maps.length===5&&maps.every(m=>m&&typeof m.big==='string'&&typeof m.small==='string')&&new Set(maps.map(m=>m.big)).size===5&&
            maps.every(m=>catalog.some(t=>t.big===m.big&&t.small===m.small));
    }
    function compatible(start,current){return start.identity===current.identity&&start.version===current.version&&start.server===current.server;}
    function imageType(file){return file.type||(/\.png$/i.test(file.name)?'image/png':/\.webp$/i.test(file.name)?'image/webp':/\.jpe?g$/i.test(file.name)?'image/jpeg':'');}
    function fileError(files,maxBytes=8*1024*1024){
        if(files.length!==1)return '一次只能上传一张图片。';
        const file=files[0];
        if(!['image/png','image/jpeg','image/webp'].includes(imageType(file)))return '这张图片暂不支持，请换一张。';
        if(!file.size)return '图片无法读取，请换一张。';
        if(file.size>maxBytes)return '图片太大，请换一张。';
        return '';
    }
    if(typeof module!=='undefined')module.exports={validMaps,compatible,imageType,fileError};
    if(!root.document)return;
    let mounted=false;
    async function mount(){
        const host=document.getElementById('mapRecognitionHost')||document.getElementById('mapRecognitionOpen')?.closest('section'),bridge=root.racepickMaps;
        if(mounted||!host||!bridge)return;mounted=true;
        const server=root.APP_CONFIG?.server||root.RACEPICK_SERVER||'cn';
        let csrf='',catalog=null,file=null,attempt=null,generation=0,busy=false,objectURL=null;
        const dialog=document.createElement('section');dialog.id='mapRecognitionWorkspace';dialog.className='map-recognition-dialog mr-inline';host.className='map-recognition-host';
        dialog.innerHTML=`<div class="mr-heading"><div><h2>地图识别</h2><p class="mr-purpose">仅支持能清晰看到五张地图中文名称的游戏截图，自动识别地图并填充。不支持拍屏照片。</p></div></div>
          <label class="mr-upload" id="mrDropZone" for="mrFile"><svg class="mr-upload-icon" viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M24 31V8m0 0-8 8m8-8 8 8M10 28v10a3 3 0 0 0 3 3h22a3 3 0 0 0 3-3V28" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg><strong id="mrDropTitle">拖入或选择已有截图</strong><input id="mrFile" type="file" aria-label="选择已有游戏截图" accept=".png,.jpg,.jpeg,.webp"></label>
          <div class="mr-file-name" id="mrFileName"></div><img id="mrPreview" class="mr-preview" alt="本次选择的截图" hidden>
          <div class="mr-controls" id="mrControls" hidden><button type="button" id="mrStart" hidden>重新识别</button><button type="button" id="mrRetry" hidden>重试</button><button type="button" id="mrCancel" hidden>取消识别</button></div>
          <p id="mrStatus" class="mr-status" role="status" aria-live="polite" hidden></p>
          <div class="mr-grid" id="mrGrid" hidden></div><p id="mrValidation" class="mr-validation" role="status"></p>
          <div class="mr-footer" id="mrFooter" hidden><div class="mr-footer-actions"><button type="button" id="mrDiscard" hidden>移除图片</button><button type="button" id="mrApply" disabled hidden>应用选图</button></div></div>`;
        host.replaceChildren(dialog);
        const $=id=>document.getElementById(id),status=$('mrStatus'),grid=$('mrGrid');
        const applied=document.createElement('p');applied.id='mapRecognitionApplied';applied.className='mr-applied';applied.setAttribute('role','status');dialog.after(applied);
        function say(text,error=false){status.textContent=text;status.hidden=!text;status.classList.toggle('mr-error',error);}
        function setBusy(value){busy=value;$('mrFile').disabled=value;$('mrStart').disabled=value||!file;$('mrCancel').hidden=!value;
            $('mrDropZone').classList.toggle('mr-upload-busy',value);$('mrDropZone').setAttribute('aria-disabled',String(value));
            $('mrStart').hidden=true;$('mrDiscard').hidden=!file;$('mrApply').hidden=!attempt||grid.hidden||value;validate();}
        async function jsonRequest(path,{method='GET',body,headers={}}={}){
            const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
            try{
                const response=await fetch(path,{method,credentials:'same-origin',signal:controller.signal,
                    headers:{...(method==='GET'?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf}),...headers},...(body===undefined?{}:{body})});
                const data=await response.json().catch(()=>({detail:response.status===413?'图片太大，请换一张。':'请求未完成，请稍后重试'}));
                if(!response.ok){const e=new Error(typeof data.detail==='string'?data.detail:'请求未完成，请检查截图后重试');e.status=response.status;throw e;}
                return data;
            }catch(e){if(e.name==='AbortError')throw Error('网络等待超时，任务可能仍在进行，可点击重试继续查询');if(e instanceof TypeError)throw Error('网络连接中断，可点击重试继续查询');throw e;}
            finally{clearTimeout(timer);}
        }
        async function currentCatalog(){
            const me=await jsonRequest('/api/auth/me');csrf=me.csrf;
            const data=await jsonRequest('/api/map-recognition/catalog?server='+server);
            const page=bridge.catalog();
            if(JSON.stringify(page)!==JSON.stringify(data.maps))throw Error('页面地图目录与识别目录不同，请刷新后重试');
            return data;
        }
        function pairs(){return Array.from(grid.querySelectorAll('.mr-slot')).map(card=>({big:card.querySelector('.mr-big').value,small:card.querySelector('.mr-small').value}));}
        function validate(){
            const maps=pairs(),ready=catalog&&maps.length===5&&validMaps(maps,catalog.maps);
            $('mrApply').disabled=busy||!attempt||!ready;
            $('mrFooter').hidden=!file&&grid.hidden;
            $('mrControls').hidden=['mrStart','mrRetry','mrCancel'].every(id=>$(id).hidden);
            $('mrValidation').textContent=grid.hidden?'':ready?'':
                maps.some(m=>!m.big||!m.small)?'请补全地图。':'大地图重复，请修改。';
        }
        function option(value,label){const node=document.createElement('option');node.value=value;node.textContent=label;return node;}
        function render(result){
            grid.replaceChildren();grid.hidden=false;
            const bigs=[...new Set(catalog.maps.map(m=>m.big))];
            result.slots.forEach((slot,index)=>{
                const card=document.createElement('section');card.className='mr-slot';
                const heading=document.createElement('h3');heading.textContent='第'+(index+1)+'张';
                const badge=document.createElement('span');badge.className='mr-slot-state';badge.textContent=slot.state==='matched'?'':'待补充';badge.hidden=slot.state==='matched';
                const big=document.createElement('select');big.className='mr-big';big.setAttribute('aria-label','第'+(index+1)+'张大地图');
                big.append(option('','选择大地图'));bigs.forEach(name=>big.append(option(name,name)));
                const small=document.createElement('select');small.className='mr-small';small.setAttribute('aria-label','第'+(index+1)+'张小地图');
                function fillSmall(value=''){small.replaceChildren(option('','选择小地图'));catalog.maps.filter(m=>m.big===big.value).forEach(m=>small.append(option(m.small,m.small)));small.value=value;small.disabled=!big.value;}
                if(slot.state==='matched'){big.value=slot.big;fillSmall(slot.small);}else fillSmall();
                big.onchange=()=>{fillSmall();badge.hidden=true;validate();};small.onchange=()=>{badge.hidden=true;validate();};
                card.append(heading,badge,big,small);grid.append(card);
            });validate();
        }
        async function disposeJob(item){
            if(!item?.id)return;
            try{await jsonRequest('/api/map-recognition/jobs/'+item.id+'?server='+item.server,{method:'DELETE'});}catch(e){/* TTL removes inaccessible/expired private media. */}
        }
        async function resetJob(){generation++;const old=attempt;attempt=null;setBusy(false);$('mrRetry').hidden=true;grid.hidden=true;grid.replaceChildren();validate();void disposeJob(old);}
        async function selectFile(value){
            const ticket=generation+1;await resetJob();if(ticket!==generation||!dialog.isConnected)return false;file=value;
            if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}
            $('mrPreview').hidden=!file;$('mrFileName').textContent=file?file.name:'';
            $('mrDropZone').classList.toggle('mr-upload-selected',!!file);$('mrDropTitle').textContent=file?'更换截图':'拖入或选择已有截图';
            if(file){objectURL=URL.createObjectURL(file);$('mrPreview').src=objectURL;say('');applied.textContent='';}
            setBusy(false);return true;
        }
        async function poll(item){
            const deadline=Date.now()+180000;let interval=1000;
            while(item.generation===generation&&dialog.isConnected){
                if(Date.now()>deadline)throw Error('识别等待较久，可点击重试继续查询，或取消后重新上传');
                let job;
                try{job=await jsonRequest('/api/map-recognition/jobs/'+item.id+'?server='+item.server);}
                catch(error){if(error.status===429){await new Promise(resolve=>setTimeout(resolve,5000));continue;}throw error;}
                if(item.generation!==generation)return;
                if(job.catalog_version!==item.catalog.version||job.server!==item.server)throw Error('识别结果服别或目录版本不一致，请重新开始');
                if(job.state==='succeeded'){
                    const result=job.result;
                    if(!result||result.schema_version!==1||result.server!==item.server||result.catalog_version!==item.catalog.version||
                       !Array.isArray(result.slots)||result.slots.length!==5||result.slots.some((s,i)=>s.slot!==i+1))throw Error('识别结果不完整，请重新开始');
                    item.finished=true;render(result);setBusy(false);
                    say(result.status==='complete'?'':'有些地图没认出，请补充。');
                    return;
                }
                if(['failed','cancelled','expired'].includes(job.state)){item.failed=true;throw Error(job.error||'本次识别已取消，请重新开始');}
                say(job.state==='queued'?'等待中…':'识别中…');
                await new Promise(resolve=>setTimeout(resolve,interval));interval=Math.min(3000,interval+250);
            }
        }
        async function start(retry=false){
            if(busy||!file)return;
            const ticket=++generation,startingSnapshot=bridge.snapshot();
            try{
                setBusy(true);say('识别中…');$('mrRetry').hidden=true;grid.hidden=true;grid.replaceChildren();
                const current=await currentCatalog();if(ticket!==generation)return;
                if(retry&&attempt&&!attempt.failed){
                    if(!compatible(attempt.catalog,current)||attempt.baseline!==bridge.snapshot())throw Error('会话或当前选图已变化，请重新开始识别');
                    attempt.generation=ticket;
                }else{
                    const old=attempt;attempt=null;await disposeJob(old);
                    catalog=current;attempt={catalog:current,server,baseline:startingSnapshot,generation:ticket,
                        key:crypto.randomUUID(),file,id:null,failed:false,finished:false};
                }
                const item=attempt;
                if(!item.id){
                    const selected=item.file;
                    const mime=imageType(selected);
                    if(!['image/png','image/jpeg','image/webp'].includes(mime)||selected.size>current.max_bytes||!selected.size)throw Error('请选择8MB以内的PNG、JPEG或WebP截图');
                    say('上传中…');
                    const job=await jsonRequest('/api/map-recognition/jobs?'+new URLSearchParams({server,catalog_version:current.version,request_key:item.key}),
                        {method:'POST',body:selected,headers:{'Content-Type':mime}});
                    item.id=job.id;
                }
                if(ticket!==generation){await disposeJob(item);return;}
                await poll(item);
            }catch(error){if(ticket===generation){setBusy(false);say(error.message,true);$('mrRetry').hidden=false;validate();}}
        }
        async function initialize(){
            const openingGeneration=generation;
            try{
                const loaded=await currentCatalog();if(!dialog.isConnected||openingGeneration!==generation)return;catalog=loaded;
                setBusy(false);
            }catch(error){say(error.message,true);}
        };
        async function acceptFiles(files){
            if(busy){say('正在识别，请先等待完成或取消本次识别。');return;}
            const list=Array.from(files),error=fileError(list,catalog?.max_bytes);
            if(error){say(error,true);$('mrFile').value='';return;}
            if(await selectFile(list[0]))await start();
        }
        $('mrFile').onchange=()=>{const files=Array.from($('mrFile').files);$('mrFile').value='';if(files.length)void acceptFiles(files);};
        let dragDepth=0;
        function clearDrag(){dragDepth=0;$('mrDropZone').classList.remove('mr-drag-over');}
        $('mrDropZone').addEventListener('dragenter',event=>{event.preventDefault();event.stopPropagation();dragDepth++;if(!busy)$('mrDropZone').classList.add('mr-drag-over');});
        $('mrDropZone').addEventListener('dragover',event=>{event.preventDefault();event.stopPropagation();if(event.dataTransfer)event.dataTransfer.dropEffect=busy?'none':'copy';});
        $('mrDropZone').addEventListener('dragleave',event=>{event.preventDefault();event.stopPropagation();dragDepth--;if(dragDepth<=0)clearDrag();});
        $('mrDropZone').addEventListener('drop',event=>{event.preventDefault();event.stopPropagation();clearDrag();if(event.dataTransfer)void acceptFiles(event.dataTransfer.files);});
        // An image dropped elsewhere in the open workspace must not navigate
        // the tab away from the user's existing garage/selection.
        dialog.addEventListener('dragover',event=>{event.preventDefault();if(event.dataTransfer)event.dataTransfer.dropEffect='none';});
        dialog.addEventListener('drop',event=>{event.preventDefault();clearDrag();say('请将截图拖入上方虚线区域。');});
        document.addEventListener('dragover',event=>{if(dialog.isConnected&&Array.from(event.dataTransfer?.types||[]).includes('Files'))event.preventDefault();});
        document.addEventListener('drop',event=>{if(dialog.isConnected){event.preventDefault();clearDrag();if(!$('mrDropZone').contains(event.target))say('请将截图拖入上方虚线区域。');}});
        $('mrStart').onclick=()=>start();$('mrRetry').onclick=()=>start(true);
        $('mrCancel').onclick=async()=>{const ticket=generation+1;await resetJob();if(ticket===generation&&dialog.isConnected)say('已取消识别，当前选图未改变。');};
        async function close(){clearDrag();const disposal=resetJob();file=null;$('mrFile').value='';$('mrFileName').textContent='';$('mrPreview').hidden=true;$('mrDropZone').classList.remove('mr-upload-selected');$('mrDropTitle').textContent='拖入或选择已有截图';if(objectURL)URL.revokeObjectURL(objectURL);objectURL=null;say('');applied.textContent='';setBusy(false);await disposal;}
        $('mrDiscard').onclick=close;
        $('mrApply').onclick=async()=>{
            const item=attempt;if(!item||busy)return;
            try{
                $('mrApply').disabled=true;
                const current=await currentCatalog();
                if(item!==attempt||!compatible(item.catalog,current))throw Error('账号、会话或地图目录已变化，请重新识别');
                const maps=pairs();if(!validMaps(maps,current.maps))throw Error('请补全五张地图，且大地图不能重复');
                bridge.apply(maps,item.baseline);
                applied.textContent='已应用';say('');generation++;attempt=null;setBusy(false);await disposeJob(item);
            }catch(error){say(error.message,true);$('mrStart').hidden=!file;validate();}
        };
        setBusy(false);void initialize();
    }
    root.addEventListener('racepick-ready',()=>void mount());if(root.racepickMaps)void mount();
})(globalThis);
