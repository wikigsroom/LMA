(function () {
  'use strict';
  var dispose = null, MAX_BYTES = 128 * 1024 * 1024;
  function close() { if (dispose) dispose(); dispose = null; }
  function require(ok, message) { if (!ok) throw new Error(message); }
  function integer(value, low, high) { return Number.isSafeInteger(value) && value >= low && value <= high; }
  function geometry(buffer) {
    var view = new DataView(buffer);
    require(buffer.byteLength >= 28 && buffer.byteLength <= MAX_BYTES && view.getUint32(0, true) === 0x46546c67 && view.getUint32(4, true) === 2 && view.getUint32(8, true) === buffer.byteLength, 'GLB 文件不完整或超过预览范围');
    var size = view.getUint32(12, true);
    require(size <= 8 * 1024 * 1024 && size % 4 === 0 && size + 28 <= buffer.byteLength && view.getUint32(16, true) === 0x4e4f534a, 'GLB JSON 块无效');
    var doc = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(new Uint8Array(buffer, 20, size))), start = 28 + size;
    require(view.getUint32(24 + size, true) === 0x004e4942 && view.getUint32(20 + size, true) === buffer.byteLength - start && Array.isArray(doc.buffers) && doc.buffers.length === 1 && !doc.buffers[0].uri && integer(doc.buffers[0].byteLength, 0, buffer.byteLength - start), '只预览内嵌资源 GLB');
    require(!(doc.nodes || []).some(function (n) { return n.matrix || n.translation || n.rotation || n.scale; }), '此文件含节点变换，请导出查看');
    require(!doc.extensionsRequired || doc.extensionsRequired.length === 0, '此文件需要额外 GLB 扩展，请导出查看');
    var positions = [], indices = [], uv = [], draws = [], images = [], pixels = 0;
    var low = [Infinity, Infinity, Infinity], high = [-Infinity, -Infinity, -Infinity];
    function bufferView(index) {
      require(integer(index, 0, (doc.bufferViews || []).length - 1), 'GLB 资源索引无效');
      var b = doc.bufferViews[index], offset = b.byteOffset === undefined ? 0 : b.byteOffset;
      require(b.buffer === 0 && integer(offset, 0, doc.buffers[0].byteLength) && integer(b.byteLength, 1, doc.buffers[0].byteLength - offset), 'GLB 资源越界');
      return {offset: offset, length: b.byteLength, stride: b.byteStride};
    }
    function accessor(index, kind) {
      require(integer(index, 0, (doc.accessors || []).length - 1), 'GLB 网格索引无效');
      var a = doc.accessors[index], b = bufferView(a.bufferView), width = kind === 'position' ? 3 : kind === 'uv' ? 2 : 1;
      var unit = a.componentType === 5126 || a.componentType === 5125 ? 4 : a.componentType === 5123 ? 2 : a.componentType === 5121 ? 1 : 0;
      require(!a.sparse && !a.normalized && unit && integer(a.count, 1, kind === 'indices' ? 2000000 : 1000000) && a.type === (width === 3 ? 'VEC3' : width === 2 ? 'VEC2' : 'SCALAR') && (kind === 'indices' ? [5121, 5123, 5125].indexOf(a.componentType) >= 0 : a.componentType === 5126), '网格超出预览范围，可导出查看');
      var offset = a.byteOffset === undefined ? 0 : a.byteOffset, stride = b.stride === undefined ? width * unit : b.stride;
      require(integer(offset, 0, b.length) && integer(stride, width * unit, 252) && stride % unit === 0 && offset % unit === 0 && b.offset % unit === 0 && offset + (a.count - 1) * stride + width * unit <= b.length, 'GLB 顶点或索引越界');
      var out = [];
      for (var i = 0; i < a.count; i++) for (var j = 0; j < width; j++) {
        var at = start + b.offset + offset + i * stride + j * unit;
        var v = kind !== 'indices' ? view.getFloat32(at, true) : unit === 4 ? view.getUint32(at, true) : unit === 2 ? view.getUint16(at, true) : view.getUint8(at);
        require(Number.isFinite(v), '网格包含无效数值'); out.push(v);
      }
      return out;
    }
    var imageCache = new Map();
    function texture(info) {
      if (info === undefined) return -1;
      require(info && integer(info.index, 0, (doc.textures || []).length - 1) && (info.texCoord === undefined || info.texCoord === 0) && !info.extensions, '此贴图映射超出预览范围，请导出查看');
      var t = doc.textures[info.index];
      require(integer(t.source, 0, (doc.images || []).length - 1) && !t.extensions, 'GLB 贴图来源无效');
      var sampler = t.sampler === undefined ? {} : (doc.samplers || [])[t.sampler];
      require(sampler && (t.sampler === undefined || integer(t.sampler, 0, (doc.samplers || []).length - 1)) && !sampler.extensions && (sampler.wrapS === undefined || [33071, 33648, 10497].indexOf(sampler.wrapS) >= 0) && (sampler.wrapT === undefined || [33071, 33648, 10497].indexOf(sampler.wrapT) >= 0), '贴图采样设置无效');
      var key = t.source + ':' + JSON.stringify(sampler);
      if (imageCache.has(key)) return imageCache.get(key);
      var im = doc.images[t.source]; require(!im.uri && im.mimeType === 'image/png' && !im.extensions, '只预览内嵌 PNG 贴图');
      var b = bufferView(im.bufferView), at = start + b.offset;
      require(b.length >= 33 && b.length <= 32 * 1024 * 1024 && view.getUint32(at, false) === 0x89504e47 && view.getUint32(at + 4, false) === 0x0d0a1a0a && view.getUint32(at + 8, false) === 13 && view.getUint32(at + 12, false) === 0x49484452, 'PNG 贴图头无效');
      var w = view.getUint32(at + 16, false), h = view.getUint32(at + 20, false);
      require(images.length < 8 && integer(w, 1, 4096) && integer(h, 1, 4096) && pixels + w * h <= 16777216, '贴图超过本地预览内存上限，请导出查看');
      pixels += w * h; var index = images.length;
      images.push({bytes: new Uint8Array(buffer, at, b.length), width: w, height: h, sampler: sampler}); imageCache.set(key, index); return index;
    }
    function factor(value, fallback) { var v = value === undefined ? fallback : value; require(typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1, 'GLB 材质参数无效'); return v; }
    (doc.meshes || []).forEach(function (mesh) { mesh.primitives.forEach(function (p) {
      require((p.mode === undefined || p.mode === 4) && !p.extensions && draws.length < 64, '只预览有界的未压缩三角网格');
      var v = accessor(p.attributes.POSITION, 'position'), ix = p.indices === undefined ? Array.from({length: v.length / 3}, function (_, i) { return i; }) : accessor(p.indices, 'indices'), base = positions.length / 3;
      require(ix.length % 3 === 0 && base + v.length / 3 <= 1000000 && indices.length + ix.length <= 2000000, '网格超出预览范围，可导出查看');
      var material = p.material === undefined ? null : (doc.materials || [])[p.material]; require(p.material === undefined || integer(p.material, 0, (doc.materials || []).length - 1), 'GLB 材质索引无效');
      require(!material || (!material.extensions && (!material.alphaMode || material.alphaMode === 'OPAQUE') && !material.normalTexture && !material.occlusionTexture && !material.emissiveTexture && !material.emissiveFactor), '此材质超出预览范围，请导出查看');
      var m = material && material.pbrMetallicRoughness || {}, color = m.baseColorFactor || (material ? [1, 1, 1, 1] : [.38, .68, .72, 1]);
      require(Array.isArray(color) && color.length === 4 && color[3] === 1, '预览需要不透明基础颜色'); color = color.map(function (x) { return factor(x, 1); });
      var albedo = texture(m.baseColorTexture), mr = texture(m.metallicRoughnessTexture), texcoords = p.attributes.TEXCOORD_0 === undefined ? null : accessor(p.attributes.TEXCOORD_0, 'uv');
      require((albedo < 0 && mr < 0 || texcoords) && (!texcoords || texcoords.length === v.length / 3 * 2), '贴图缺少匹配的 UV 坐标');
      draws.push({offset: indices.length * 4, count: ix.length, color: color, albedo: albedo, mr: mr, metallic: factor(m.metallicFactor, material ? 1 : 0), roughness: factor(m.roughnessFactor, material ? 1 : .8)});
      for (var i = 0; i < v.length; i++) { var axis = i % 3; low[axis] = Math.min(low[axis], v[i]); high[axis] = Math.max(high[axis], v[i]); positions.push(v[i]); }
      for (var j = 0; j < v.length / 3 * 2; j++) uv.push(texcoords ? texcoords[j] : 0);
      ix.forEach(function (i) { require(i < v.length / 3, 'GLB 索引越界'); indices.push(base + i); });
    }); });
    require(positions.length > 0, 'GLB 没有网格');
    var scale = Math.max(high[0] - low[0], high[1] - low[1], high[2] - low[2]); require(Number.isFinite(scale) && scale > 0, 'GLB 网格尺寸无效');
    for (var i = 0; i < positions.length; i++) positions[i] = (positions[i] - (low[i % 3] + high[i % 3]) / 2) * 2 / scale;
    return {positions: new Float32Array(positions), indices: new Uint32Array(indices), uv: new Float32Array(uv), draws: draws, images: images};
  }
  function open(canvas, status, url, bytes) {
    close(); var abort = new AbortController(), cancelled = false, gl = null, buffers = [], textures = [], shaders = [], program = null, observer = null, reader = null, handlers = [], pointers = new Map();
    dispose = function () {
      if (cancelled) return; cancelled = true; abort.abort(); if (reader) reader.cancel().catch(function () {}); if (observer) observer.disconnect();
      handlers.forEach(function (h) { canvas.removeEventListener(h[0], h[1]); });
      pointers.forEach(function (_, id) { if (canvas.hasPointerCapture(id)) canvas.releasePointerCapture(id); }); pointers.clear();
      if (gl) { buffers.forEach(function (b) { gl.deleteBuffer(b); }); textures.forEach(function (t) { gl.deleteTexture(t); }); shaders.forEach(function (s) { gl.deleteShader(s); }); if (program) gl.deleteProgram(program); var ext = gl.getExtension('WEBGL_lose_context'); if (ext) ext.loseContext(); }
    };
    if (bytes > MAX_BYTES) { status.textContent = '文件超过 128 MiB 预览上限，请导出查看。'; close(); return; }
    function listen(name, handler, options) { canvas.addEventListener(name, handler, options); handlers.push([name, handler]); }
    function decode(image) {
      var blob = new Blob([image.bytes], {type: 'image/png'});
      if (typeof createImageBitmap === 'function') return createImageBitmap(blob, {imageOrientation: 'none', premultiplyAlpha: 'none', colorSpaceConversion: 'none'});
      return new Promise(function (resolve, reject) {
        var im = new Image(), local = URL.createObjectURL(blob);
        function clean() { URL.revokeObjectURL(local); abort.signal.removeEventListener('abort', stop); im.onload = im.onerror = null; }
        function stop() { clean(); im.src = ''; reject(new Error('预览已关闭')); }
        im.onload = function () { clean(); resolve(im); }; im.onerror = function () { clean(); reject(new Error('无法解码内嵌 PNG')); };
        abort.signal.addEventListener('abort', stop, {once: true}); if (cancelled) stop(); else im.src = local;
      });
    }
    fetch(url, {signal: abort.signal}).then(function (r) {
      require(r.ok && Number(r.headers.get('Content-Length')) <= MAX_BYTES && r.body, '无法读取本地 GLB'); reader = r.body.getReader(); var chunks = [], total = 0;
      function next() { return reader.read().then(function (part) { if (part.done) { var joined = new Uint8Array(total), offset = 0; chunks.forEach(function (c) { joined.set(c, offset); offset += c.length; }); chunks = []; return joined.buffer; } total += part.value.byteLength; require(total <= MAX_BYTES, '文件超过预览上限'); chunks.push(part.value); return next(); }); } return next();
    }).then(async function (buffer) {
      if (cancelled) return; var mesh = geometry(buffer); gl = canvas.getContext('webgl2', {antialias: true}); require(gl, '当前 WebView 未提供 WebGL 2，请导出查看');
      require(mesh.images.every(function (im) { return im.width <= gl.getParameter(gl.MAX_TEXTURE_SIZE) && im.height <= gl.getParameter(gl.MAX_TEXTURE_SIZE); }), '当前设备的贴图尺寸不足，请导出查看');
      function shader(type, source) { var s = gl.createShader(type); shaders.push(s); gl.shaderSource(s, source); gl.compileShader(s); require(gl.getShaderParameter(s, gl.COMPILE_STATUS), '无法创建本地材质预览'); return s; }
      var vs = shader(gl.VERTEX_SHADER, '#version 300 es\nin vec3 p; in vec2 uv; uniform vec3 r; out vec3 v; out vec2 t; void main(){float cy=cos(r.x),sy=sin(r.x),cx=cos(r.y),sx=sin(r.y); vec3 q=vec3(cy*p.x+sy*p.z,p.y,-sy*p.x+cy*p.z); q=vec3(q.x,cx*q.y-sx*q.z,sx*q.y+cx*q.z); v=q; t=uv; gl_Position=vec4(q.x*r.z*0.75,q.y*r.z,q.z*0.2,1.0); }');
      var fs = shader(gl.FRAGMENT_SHADER, '#version 300 es\nprecision highp float; in vec3 v; in vec2 t; uniform sampler2D aTex; uniform sampler2D mTex; uniform vec4 base; uniform vec4 material; out vec4 color; void main(){vec3 n=normalize(cross(dFdx(v),dFdy(v))); if(n.z<0.0)n=-n; vec3 l=normalize(vec3(0.4,0.7,1.0)); vec3 h=normalize(l+vec3(0,0,1)); vec3 a=base.rgb; if(material.z>0.5)a*=texture(aTex,t).rgb; a=pow(a,vec3(2.2)); vec3 mr=material.w>0.5?texture(mTex,t).rgb:vec3(1); float m=clamp(material.x*mr.b,0.0,1.0),r=max(0.06,material.y*mr.g),nl=max(dot(n,l),0.0),nv=max(n.z,0.01),nh=max(dot(n,h),0.0),vh=max(h.z,0.0); float a2=r*r*r*r,den=nh*nh*(a2-1.0)+1.0,D=a2/(3.14159265*den*den),k=(r+1.0)*(r+1.0)/8.0,G=nl/(nl*(1.0-k)+k)*nv/(nv*(1.0-k)+k); vec3 f0=mix(vec3(0.04),a,m),F=f0+(1.0-f0)*pow(1.0-vh,5.0); vec3 diffuse=(1.0-F)*(1.0-m)*a/3.14159265; vec3 lit=a*(0.22+0.08*m)+(diffuse+F*D*G/max(4.0*nl*nv,0.001))*nl*2.5; color=vec4(pow(clamp(lit,0.0,1.0),vec3(1.0/2.2)),1.0); }');
      program = gl.createProgram(); gl.attachShader(program, vs); gl.attachShader(program, fs); gl.linkProgram(program); require(gl.getProgramParameter(program, gl.LINK_STATUS), '无法链接本地材质预览'); gl.useProgram(program);
      function bind(target, data) { var b = gl.createBuffer(); buffers.push(b); gl.bindBuffer(target, b); gl.bufferData(target, data, gl.STATIC_DRAW); }
      function attribute(name, data, width) { bind(gl.ARRAY_BUFFER, data); var p = gl.getAttribLocation(program, name); gl.enableVertexAttribArray(p); gl.vertexAttribPointer(p, width, gl.FLOAT, false, 0, 0); }
      attribute('p', mesh.positions, 3); attribute('uv', mesh.uv, 2); bind(gl.ELEMENT_ARRAY_BUFFER, mesh.indices);
      // Decode sequentially and close each bitmap, including a modal close
      // during decoding. Image headers bound memory before any decode occurs.
      for (var i = 0; i < mesh.images.length; i++) {
        var image = mesh.images[i], bitmap = await decode(image);
        try {
          if (cancelled) return; require(bitmap.width === image.width && bitmap.height === image.height, 'PNG 解码尺寸与文件头不匹配');
          var texture = gl.createTexture(); textures.push(texture); gl.bindTexture(gl.TEXTURE_2D, texture); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, bitmap);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, image.sampler.minFilter === 9728 ? gl.NEAREST : gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, image.sampler.magFilter === 9728 ? gl.NEAREST : gl.LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, image.sampler.wrapS || gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, image.sampler.wrapT || gl.REPEAT);
        } finally { if (bitmap.close) bitmap.close(); }
      }
      if (cancelled) return;
      // Both texture units need a complete texture, including untextured draws.
      var white = gl.createTexture(); textures.push(white); gl.bindTexture(gl.TEXTURE_2D, white); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255])); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.uniform1i(gl.getUniformLocation(program, 'aTex'), 0); gl.uniform1i(gl.getUniformLocation(program, 'mTex'), 1);
      var rotation = gl.getUniformLocation(program, 'r'), base = gl.getUniformLocation(program, 'base'), material = gl.getUniformLocation(program, 'material'), yaw = .5, pitch = -.2, zoom = .72, pinch = 0;
      function draw() {
        if (cancelled) return; var w = Math.min(1200, Math.max(1, Math.round(canvas.clientWidth * devicePixelRatio))); canvas.width = w; canvas.height = Math.max(1, Math.round(w * .75));
        gl.viewport(0, 0, canvas.width, canvas.height); gl.enable(gl.DEPTH_TEST); gl.clearColor(.065, .085, .10, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.uniform3f(rotation, yaw, pitch, zoom);
        mesh.draws.forEach(function (d) { gl.uniform4fv(base, d.color); gl.uniform4f(material, d.metallic, d.roughness, d.albedo >= 0 ? 1 : 0, d.mr >= 0 ? 1 : 0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, d.albedo >= 0 ? textures[d.albedo] : white); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, d.mr >= 0 ? textures[d.mr] : white); gl.drawElements(gl.TRIANGLES, d.count, gl.UNSIGNED_INT, d.offset); });
      }
      listen('pointerdown', function (ev) { pointers.set(ev.pointerId, [ev.clientX, ev.clientY]); canvas.setPointerCapture(ev.pointerId); });
      listen('pointermove', function (ev) { var prev = pointers.get(ev.pointerId); if (!prev) return; pointers.set(ev.pointerId, [ev.clientX, ev.clientY]); if (pointers.size === 2) { var a = Array.from(pointers.values()), d = Math.hypot(a[0][0] - a[1][0], a[0][1] - a[1][1]); if (pinch) zoom = Math.max(.1, Math.min(3, zoom * d / pinch)); pinch = d; } else { yaw += (ev.clientX - prev[0]) * .01; pitch += (ev.clientY - prev[1]) * .01; } draw(); });
      function up(ev) { pointers.delete(ev.pointerId); pinch = 0; }
      listen('pointerup', up); listen('pointercancel', up); listen('wheel', function (ev) { ev.preventDefault(); zoom = Math.max(.1, Math.min(3, zoom * Math.exp(-ev.deltaY * .001))); draw(); }, {passive: false});
      observer = new ResizeObserver(draw); observer.observe(canvas); draw(); status.textContent = mesh.images.length ? 'PBR 材质预览 · 拖动旋转 / 缩放；可导出完整 GLB。' : '几何预览 · 拖动旋转 / 缩放；可导出完整 GLB。';
    }).catch(function (err) { if (!cancelled) { var text = err.message; close(); status.textContent = text; } });
  }
  window.LMAGlbPreview = {open: open, close: close, geometry: geometry};
}());
