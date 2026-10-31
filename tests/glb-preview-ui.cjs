/* Actual WebGL rendering and cleanup, using colored program fixtures. */
const assert=require('node:assert/strict'),zlib=require('node:zlib');
function crc(bytes){let c=0xffffffff;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
function png(rgb){
 const chunk=(kind,data)=>{const type=Buffer.from(kind),out=Buffer.alloc(data.length+12);out.writeUInt32BE(data.length);type.copy(out,4);data.copy(out,8);out.writeUInt32BE(crc(Buffer.concat([type,data])),data.length+8);return out;};
 const h=Buffer.alloc(13);h.writeUInt32BE(2);h.writeUInt32BE(2,4);h[8]=8;h[9]=2;
 return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',h),chunk('IDAT',zlib.deflateSync(Buffer.from([0,...rgb.slice(0,6),0,...rgb.slice(6)]))),chunk('IEND',Buffer.alloc(0))]);
}
function fixture(change=()=>{},options={}){
 const binary=[],views=[];let length=0;
 const append=data=>{const offset=length;binary.push(data);length+=data.length;const padding=(4-length%4)%4;if(padding){binary.push(Buffer.alloc(padding));length+=padding;}views.push({buffer:0,byteOffset:offset,byteLength:data.length});return views.length-1;};
 const floats=items=>{const b=Buffer.alloc(items.length*4);items.forEach((v,i)=>b.writeFloatLE(v,i*4));return b;};
 const pos=append(floats([-1,-1,0,1,-1,0,1,1,0,-1,1,0])),uv=append(floats([0,1,1,1,1,0,0,0])),ix=append(Buffer.from([0,0,1,0,2,0,0,0,2,0,3,0]));
 const image=append(png([245,24,24,24,245,24,24,24,245,245,245,24]));
 const mr=append(png(Array(4).fill([255,options.roughness??204,options.metal??0]).flat()));
 const doc={asset:{version:'2.0',generator:'LMA UI FIXTURE; no trained output'},buffers:[{byteLength:length}],bufferViews:views,accessors:[{bufferView:pos,componentType:5126,count:4,type:'VEC3'},{bufferView:uv,componentType:5126,count:4,type:'VEC2'},{bufferView:ix,componentType:5123,count:6,type:'SCALAR'}],images:[{bufferView:image,mimeType:'image/png'},{bufferView:mr,mimeType:'image/png'}],samplers:[{magFilter:9728,minFilter:9728,wrapS:33071,wrapT:33071}],textures:[{source:0,sampler:0},{source:1,sampler:0}],materials:[{doubleSided:true,pbrMetallicRoughness:{baseColorTexture:{index:0},metallicRoughnessTexture:{index:1},roughnessFactor:1,metallicFactor:1}}],meshes:[{primitives:[{mode:4,attributes:{POSITION:0,TEXCOORD_0:1},indices:2,material:0}]}],nodes:[{mesh:0}],scenes:[{nodes:[0]}],scene:0};
 change(doc);let json=Buffer.from(JSON.stringify(doc));json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);const out=Buffer.alloc(28+json.length+length);
 out.writeUInt32LE(0x46546c67);out.writeUInt32LE(2,4);out.writeUInt32LE(out.length,8);out.writeUInt32LE(json.length,12);out.writeUInt32LE(0x4e4f534a,16);json.copy(out,20);out.writeUInt32LE(length,20+json.length);out.writeUInt32LE(0x004e4942,24+json.length);Buffer.concat(binary).copy(out,28+json.length);return out;
}
function probe(){
 const p={draws:0,frames:[],counts:{},handlers:new Map(),restore:[]};window.__lmaPreviewProbe=p;
 function hook(object,key,replacement){const old=object[key];object[key]=replacement(old);p.restore.push(()=>object[key]=old);}
 for(const noun of ['Buffer','Texture','Shader','Program'])for(const verb of ['create','delete'])hook(WebGL2RenderingContext.prototype,verb+noun,old=>function(...args){p.counts[verb+noun]=(p.counts[verb+noun]||0)+1;return old.apply(this,args);});
 hook(WebGL2RenderingContext.prototype,'drawElements',old=>function(...args){const result=old.apply(this,args);p.draws++;const points=[];for(const y of [.37,.63])for(const x of [.39,.61]){const pixel=new Uint8Array(4);this.readPixels(Math.floor(this.canvas.width*x),Math.floor(this.canvas.height*y),1,1,this.RGBA,this.UNSIGNED_BYTE,pixel);points.push(Array.from(pixel));}p.frames.push(points);return result;});
 for(const name of ['addEventListener','removeEventListener'])hook(HTMLCanvasElement.prototype,name,old=>function(type,listener,...rest){if(['pointerdown','pointermove','pointerup','pointercancel','wheel'].includes(type)){let set=p.handlers.get(this);if(!set){set=new Set();p.handlers.set(this,set);}if(name==='addEventListener')set.add(listener);else set.delete(listener);}return old.call(this,type,listener,...rest);});
 p.finish=()=>{p.restore.reverse().forEach(f=>f());delete window.__lmaPreviewProbe;};
}
async function checks(page,checked,capture=async()=>{}){
 const glb=fixture(),route='**/artifacts/material_result';let current=glb;
 await page.route(route,r=>r.fulfill({contentType:'model/gltf-binary',body:current}));await page.evaluate(probe);
 try{
  await page.evaluate(bytes=>{const f=window.__fixture,j=f.jobs[0];j.state='succeeded';j.artifacts=['material_result'];f.artifacts.push({id:'material_result',available:true,jobId:j.id,bytes,origin:{kind:'generated'},metadata:{mime:'model/gltf-binary',vertices:4,triangles:2,textures:2},provenance:{execution:'COLORED UI FIXTURE; no model output',request:j.request}});window.LMA.receive(f);},glb.length);
  await page.locator('.job-card [data-action="jobResults"]').click();await page.waitForFunction(()=>document.getElementById('glbPreviewStatus')?.textContent.includes('PBR 材质预览'));
  const data=await page.evaluate(()=>({frames:window.__lmaPreviewProbe.frames.at(-1),counts:window.__lmaPreviewProbe.counts,handlers:[...window.__lmaPreviewProbe.handlers.values()].reduce((n,s)=>n+s.size,0)}));
  assert.equal(data.counts.createTexture,3);assert.equal(data.handlers,4);checked('PBR preview decodes the two embedded PNGs and owns bounded canvas handlers');
  const [bottomLeft,bottomRight,topLeft,topRight]=data.frames;
  assert(bottomLeft[2]>bottomLeft[0]*2&&bottomLeft[2]>bottomLeft[1]*2);assert(bottomRight[0]>bottomRight[2]*2&&bottomRight[1]>bottomRight[2]*2);assert(topLeft[0]>topLeft[1]*2&&topLeft[0]>topLeft[2]*2);assert(topRight[1]>topRight[0]*2&&topRight[1]>topRight[2]*2);checked('Actual GPU pixels preserve UV orientation and all four albedo quadrants');
  await capture('06-material-preview.png','UI FIXTURE · Actual local PBR renderer; colored program geometry, not model output');
  const canvas=page.locator('#modal canvas').first(),box=await canvas.boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+18,box.y+box.height/2+9);await page.mouse.up();
  assert(await page.evaluate(()=>window.__lmaPreviewProbe.draws)>1);checked('PBR material preview rotates through the production pointer handler');
  async function reopen(value,withoutBitmap=false){current=value;await page.evaluate(noBitmap=>{const old=document.querySelector('#modal canvas'),c=old.cloneNode(),s=document.getElementById('glbPreviewStatus');window.LMAGlbPreview.close();old.replaceWith(c);s.textContent='loading';if(noBitmap){window.__bitmapPrevious=window.createImageBitmap;window.createImageBitmap=undefined;}window.LMAGlbPreview.open(c,s,'/artifacts/material_result',4096);},withoutBitmap);await page.waitForFunction(()=>document.getElementById('glbPreviewStatus').textContent.includes('PBR 材质预览'));return page.evaluate(()=>window.__lmaPreviewProbe.frames.at(-1));}
  const shiny=await reopen(fixture(()=>{},{metal:255,roughness:32}));assert.notDeepEqual(shiny,data.frames);checked('Metallic in B and roughness in G affect actual rendered pixels');
  const fallback=await reopen(glb,true);assert.deepEqual(fallback,data.frames);await page.evaluate(()=>{window.createImageBitmap=window.__bitmapPrevious;delete window.__bitmapPrevious;});checked('Image-element decode fallback preserves PBR pixels and releases local object URLs');
  const cases=[['external_image',d=>d.images[0].uri='https://example.invalid/x.png'],['oversized_pixels',d=>d.images.push({...d.images[0]})],['missing_uv',d=>delete d.meshes[0].primitives[0].attributes.TEXCOORD_0],['bad_uv_count',d=>d.accessors[1].count=3],['out_of_bounds_image',d=>d.bufferViews[3].byteLength=999999],['negative_stride',d=>d.bufferViews[0].byteStride=-12],['fractional_accessor',d=>d.accessors[0].count=3.5],['out_of_bounds_material',d=>d.meshes[0].primitives[0].material=9],['unsupported_uv_transform',d=>d.materials[0].pbrMetallicRoughness.baseColorTexture.extensions={KHR_texture_transform:{offset:[1,0]}}],['unsupported_blend',d=>d.materials[0].alphaMode='BLEND']];
  // The pixel-limit case edits a PNG IHDR directly. Decoding must never start.
  for(const [label,change] of cases){let file=fixture(change);if(label==='oversized_pixels'){const at=28+file.readUInt32LE(12)+92;file.writeUInt32BE(8192,at+16);}const accepted=await page.evaluate(b64=>{try{window.LMAGlbPreview.geometry(Uint8Array.from(atob(b64),c=>c.charCodeAt(0)).buffer);return true;}catch(_){return false;}},file.toString('base64'));assert(!accepted,label);checked('PBR parser rejects '+label+' before image decoding');}
  await page.keyboard.press('Escape');const released=await page.evaluate(()=>{const p=window.__lmaPreviewProbe;return {counts:p.counts,handlers:[...p.handlers.values()].reduce((n,s)=>n+s.size,0)};});
  assert.equal(released.handlers,0);for(const noun of ['Buffer','Texture','Shader','Program'])assert.equal(released.counts['create'+noun],released.counts['delete'+noun],noun);checked('Closing and reopening PBR results releases all owned GPU objects and canvas handlers');
 }catch(error){console.error('PBR preview status:',await page.locator('#glbPreviewStatus').textContent().catch(()=>''));throw error;}
 finally{await page.evaluate(()=>{window.LMAGlbPreview.close();if(window.__bitmapPrevious){window.createImageBitmap=window.__bitmapPrevious;delete window.__bitmapPrevious;}window.__lmaPreviewProbe?.finish();});await page.unroute(route);}
}
module.exports={checks,fixture};
