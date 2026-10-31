(function () {
  'use strict';
  var dispose = null;
  function close() { if (dispose) dispose(); dispose = null; }
  function geometry(buffer) {
    var view = new DataView(buffer);
    if (buffer.byteLength < 28 || view.getUint32(0,true) !== 0x46546c67 || view.getUint32(4,true) !== 2 || view.getUint32(8,true) !== buffer.byteLength) throw new Error('GLB 文件不完整');
    var size = view.getUint32(12,true); if (size > 8*1024*1024 || size % 4 || size+28 > buffer.byteLength || view.getUint32(16,true) !== 0x4e4f534a) throw new Error('GLB JSON 块无效');
    var doc = JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(new Uint8Array(buffer,20,size))), start = 28+size;
    if (view.getUint32(24+size,true) !== 0x004e4942 || view.getUint32(20+size,true) !== buffer.byteLength-start || doc.buffers.length !== 1 || doc.buffers[0].uri) throw new Error('只预览内嵌资源 GLB');
    // The signed native exporter emits one triangle mesh, without node transforms.
    if ((doc.nodes || []).some(function (n) { return n.matrix || n.translation || n.rotation || n.scale; })) throw new Error('此文件含节点变换，请导出查看');
    var positions = [], indices = [], low = [Infinity,Infinity,Infinity], high = [-Infinity,-Infinity,-Infinity];
    function accessor(index,position) {
      var a = doc.accessors[index], b = a && doc.bufferViews[a.bufferView], unit = a && (a.componentType === 5126 || a.componentType === 5125 ? 4 : a.componentType === 5123 ? 2 : a.componentType === 5121 ? 1 : 0), width = position ? 3 : 1;
      if (!a || !b || b.buffer !== 0 || a.sparse || !unit || a.count < 1 || a.count > (position ? 1000000 : 2000000) || a.type !== (position ? 'VEC3' : 'SCALAR') || position && a.componentType !== 5126 || !position && [5121,5123,5125].indexOf(a.componentType) < 0) throw new Error('网格超出预览范围，可导出查看');
      var offset = (b.byteOffset || 0)+(a.byteOffset || 0), stride = b.byteStride || width*unit;
      if (offset < 0 || stride < width*unit || (a.byteOffset || 0)+(a.count-1)*stride+width*unit > b.byteLength || offset+(a.count-1)*stride+width*unit > buffer.byteLength-start) throw new Error('GLB 顶点或索引越界');
      var out = [];
      for (var i=0;i<a.count;i++) for (var j=0;j<width;j++) { var at=start+offset+i*stride+j*unit, v=position ? view.getFloat32(at,true) : unit === 4 ? view.getUint32(at,true) : unit === 2 ? view.getUint16(at,true) : view.getUint8(at); if (!Number.isFinite(v)) throw new Error('网格包含无效数值'); out.push(v); }
      return out;
    }
    (doc.meshes || []).forEach(function (mesh) { mesh.primitives.forEach(function (p) {
      if (p.mode !== undefined && p.mode !== 4 || p.extensions) throw new Error('只预览未压缩三角网格');
      var v = accessor(p.attributes.POSITION,true), ix = p.indices === undefined ? Array.from({length:v.length/3},function (_,i) { return i; }) : accessor(p.indices,false), base=positions.length/3;
      if (ix.length % 3 || base+v.length/3 > 1000000 || indices.length+ix.length > 2000000) throw new Error('网格超出预览范围，可导出查看');
      for (var i=0;i<v.length;i++) { var axis=i%3; low[axis]=Math.min(low[axis],v[i]); high[axis]=Math.max(high[axis],v[i]); positions.push(v[i]); }
      ix.forEach(function (i) { if (i>=v.length/3) throw new Error('GLB 索引越界'); indices.push(base+i); });
    }); });
    if (!positions.length) throw new Error('GLB 没有网格');
    var scale=Math.max(high[0]-low[0],high[1]-low[1],high[2]-low[2]); if (!Number.isFinite(scale) || scale<=0) throw new Error('GLB 网格尺寸无效');
    for (var i=0;i<positions.length;i++) positions[i]=(positions[i]-(low[i%3]+high[i%3])/2)*2/scale;
    return {positions:new Float32Array(positions),indices:new Uint32Array(indices)};
  }
  function open(canvas,status,url,bytes) {
    close(); var abort=new AbortController(), cancelled=false, gl=null, buffers=[], program=null, observer=null;
    dispose=function () { cancelled=true; abort.abort(); if (observer) observer.disconnect(); if (gl) { buffers.forEach(function (b) { gl.deleteBuffer(b); }); if (program) gl.deleteProgram(program); var ext=gl.getExtension('WEBGL_lose_context'); if (ext) ext.loseContext(); } };
    if (bytes>128*1024*1024) { status.textContent='文件超过 128 MiB 预览上限，请导出查看。'; return; }
    fetch(url,{signal:abort.signal}).then(function (r) {
      if (!r.ok || Number(r.headers.get('Content-Length'))>128*1024*1024 || !r.body) throw new Error('无法读取本地 GLB');
      var reader=r.body.getReader(), chunks=[], total=0;
      function next() { return reader.read().then(function (part) { if (part.done) { var joined=new Uint8Array(total), offset=0; chunks.forEach(function (c) { joined.set(c,offset); offset+=c.length; }); return joined.buffer; } total+=part.value.byteLength; if (total>128*1024*1024) { reader.cancel(); throw new Error('文件超过预览上限'); } chunks.push(part.value); return next(); }); }
      return next();
    }).then(function (buffer) {
      if (cancelled) return; var mesh=geometry(buffer); gl=canvas.getContext('webgl2',{antialias:true}); if (!gl) throw new Error('当前 WebView 未提供 WebGL 2，请导出查看');
      function shader(type,source) { var s=gl.createShader(type); gl.shaderSource(s,source); gl.compileShader(s); if (!gl.getShaderParameter(s,gl.COMPILE_STATUS)) { gl.deleteShader(s); throw new Error('无法创建几何预览'); } return s; }
      var vs=shader(gl.VERTEX_SHADER,'#version 300 es\nin vec3 p; uniform vec3 r; out vec3 v; void main(){float cy=cos(r.x),sy=sin(r.x),cx=cos(r.y),sx=sin(r.y); vec3 q=vec3(cy*p.x+sy*p.z,p.y,-sy*p.x+cy*p.z); q=vec3(q.x,cx*q.y-sx*q.z,sx*q.y+cx*q.z); v=q; gl_Position=vec4(q.x*r.z*0.75,q.y*r.z,q.z*0.2,1.0); }');
      var fs=shader(gl.FRAGMENT_SHADER,'#version 300 es\nprecision highp float; in vec3 v; out vec4 color; void main(){vec3 n=normalize(cross(dFdx(v),dFdy(v))); float l=0.35+0.65*abs(dot(n,normalize(vec3(0.4,0.7,1.0)))); color=vec4(vec3(0.38,0.68,0.72)*l,1.0); }');
      program=gl.createProgram(); gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('无法链接几何预览');gl.useProgram(program);
      function bind(target,data) { var b=gl.createBuffer();buffers.push(b);gl.bindBuffer(target,b);gl.bufferData(target,data,gl.STATIC_DRAW); }
      bind(gl.ARRAY_BUFFER,mesh.positions);var p=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(p);gl.vertexAttribPointer(p,3,gl.FLOAT,false,0,0);bind(gl.ELEMENT_ARRAY_BUFFER,mesh.indices);
      var rotation=gl.getUniformLocation(program,'r'), yaw=.5,pitch=-.2,zoom=.72,pointers=new Map(), pinch=0;
      function draw() { if(cancelled)return;var w=Math.min(1200,Math.max(1,canvas.clientWidth*devicePixelRatio));canvas.width=w;canvas.height=w*.75;gl.viewport(0,0,canvas.width,canvas.height);gl.enable(gl.DEPTH_TEST);gl.clearColor(.065,.085,.10,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniform3f(rotation,yaw,pitch,zoom);gl.drawElements(gl.TRIANGLES,mesh.indices.length,gl.UNSIGNED_INT,0); }
      canvas.onpointerdown=function(ev){pointers.set(ev.pointerId,[ev.clientX,ev.clientY]);canvas.setPointerCapture(ev.pointerId);};
      canvas.onpointermove=function(ev){var prev=pointers.get(ev.pointerId);if(!prev)return;pointers.set(ev.pointerId,[ev.clientX,ev.clientY]);if(pointers.size===2){var a=Array.from(pointers.values()),d=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]);if(pinch)zoom=Math.max(.1,Math.min(3,zoom*d/pinch));pinch=d;}else{yaw+=(ev.clientX-prev[0])*.01;pitch+=(ev.clientY-prev[1])*.01;}draw();};
      canvas.onpointerup=canvas.onpointercancel=function(ev){pointers.delete(ev.pointerId);pinch=0;};canvas.onwheel=function(ev){ev.preventDefault();zoom=Math.max(.1,Math.min(3,zoom*Math.exp(-ev.deltaY*.001)));draw();};
      observer=new ResizeObserver(draw);observer.observe(canvas);draw();status.textContent='几何预览 · 拖动旋转 / 缩放；材质随 GLB 导出。';
    }).catch(function (err) { if (!cancelled) { var text=err.message; close(); status.textContent=text; } });
  }
  window.LMAGlbPreview={open:open,close:close,geometry:geometry};
}());
