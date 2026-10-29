(function () {
  'use strict';
  var ui, host, playing = null;
  function summary(id) { return (ui.state().audioStreams || []).find(function (s) { return s.jobId === id; }); }
  function hint(message) { var node = document.getElementById('audioPreviewStatus'); if (node) node.textContent = message; }
  function stop(message) {
    var p = playing; playing = null;
    if (p) { clearTimeout(p.timer); p.abort.abort(); p.sources.forEach(function (s) { try { s.stop(); } catch (_) {} }); p.sources.clear(); p.context.close().catch(function () {}); }
    var start = document.querySelector('[data-action="startAudioPreview"]'), end = document.querySelector('[data-action="stopAudioPreview"]');
    if (start) start.disabled = false; if (end) end.disabled = true; if (message) hint(message);
  }
  function panel(id) {
    stop(); var stream = summary(id); if (!stream) { ui.toast('试听已过期；完整结果可在结果库查看'); return; }
    ui.openModal('边生成边听', '<div id="audioPreviewPanel" data-job="' + ui.esc(id) + '"><p>点播放后，从本次语音开头逐段试听。生成会继续在手机后台运行。</p><p class="form-help">试听缓存保留最近 4 次任务，应用重启或系统清理缓存后失效；成功生成的完整 WAV 独立保存在结果库。试听速度取决于设备。</p><p id="audioPreviewStatus" role="status">已生成 ' + (stream.durationMs / 1000).toFixed(2) + ' 秒 · ' + (stream.state === 'streaming' ? '仍在生成' : stream.state === 'succeeded' ? '完整结果已保存' : '任务未完成，只有部分试听') + '</p><div class="job-actions">' + host.button('startAudioPreview', id, '播放 / 从头试听', 'primary') + host.button('stopAudioPreview', id, '停止试听', 'secondary', true) + (stream.artifactId ? host.button('artifactInfo', stream.artifactId, '打开完整结果') : '') + '</div></div>', 'audioPreview');
  }
  function integer(value, low, high) { if (typeof value !== 'number' || !Number.isInteger(value) || value < low || value > high) throw new Error('试听片段的边界无效'); return value; }
  async function fetchBytes(p, suffix, json) {
    var response = await fetch('/audio-streams/' + encodeURIComponent(p.id) + suffix, {cache: 'no-store', signal: p.abort.signal});
    if (!response.ok) throw new Error('试听缓存已失效或尚未开始，可稍后重试或查看完整结果');
    return json ? response.json() : response.arrayBuffer();
  }
  function later(p, millis) { if (playing === p) p.timer = setTimeout(function () { pump(p); }, millis); }
  async function pump(p) {
    if (playing !== p) return;
    if (!document.getElementById('audioPreviewPanel') || document.hidden) { stop('试听已停止'); return; }
    try {
      if (p.nextTime - p.context.currentTime > 3) { later(p, 200); return; }
      var update = await fetchBytes(p, '?after=' + p.cursor, true); if (playing !== p) return;
      var f = update.format;
      if (!f || f.schema !== 'lma.audio-stream/1' || f.format !== 'pcm_s16le' || update.jobId !== p.id || f.sampleRate !== p.rate || f.channels !== p.channels || !Array.isArray(update.chunks) || update.chunks.length > 32) throw new Error('试听格式与任务不一致');
      integer(update.nextSequence, p.cursor, 4096);
      for (var i = 0; i < update.chunks.length; i++) {
        if (playing !== p) return; if (p.nextTime - p.context.currentTime > 3) break;
        var chunk = update.chunks[i]; if (chunk.sequence !== p.cursor || chunk.startFrame !== p.frames) throw new Error('试听片段顺序无效');
        var frames = integer(chunk.frames, 1, Math.min(f.maxChunkFrames, 4800)); if (p.frames + frames > f.maxFrames) throw new Error('试听超过本次任务上限');
        var pcm = await fetchBytes(p, '/' + p.cursor, false); if (playing !== p) return;
        if (pcm.byteLength !== frames * p.channels * 2) throw new Error('试听片段不完整');
        var view = new DataView(pcm), buffer = p.context.createBuffer(p.channels, frames, p.rate);
        for (var channel = 0; channel < p.channels; channel++) { var samples = buffer.getChannelData(channel); for (var j = 0; j < frames; j++) samples[j] = view.getInt16((j * p.channels + channel) * 2, true) / 32768; }
        var source = p.context.createBufferSource(); source.buffer = buffer; source.connect(p.context.destination); p.sources.add(source); source.onended = (function (node) { return function () { p.sources.delete(node); }; })(source);
        p.nextTime = Math.max(p.nextTime, p.context.currentTime + 0.05); source.start(p.nextTime); p.nextTime += frames / p.rate; p.cursor++; p.frames += frames;
      }
      hint('试听中 · 已接收 ' + (p.frames / p.rate).toFixed(2) + ' 秒' + (update.state === 'streaming' ? ' · 等待后续片段' : update.state === 'succeeded' ? ' · 完整 WAV 已保存' : ' · 任务未完成，试听为部分内容'));
      if (update.state !== 'streaming' && p.cursor === update.nextSequence) {
        p.timer = setTimeout(function () { if (playing === p) stop(update.state === 'succeeded' ? '试听结束，完整 WAV 可在结果库查看' : '试听结束；任务未完成，未将部分音频保存为成功结果'); }, Math.max(0, (p.nextTime - p.context.currentTime) * 1000 + 50));
      } else later(p, 250);
    } catch (error) { if (playing === p) stop(error.message || '试听中断'); }
  }
  function start(id) {
    stop(); var stream = summary(id), Audio = window.AudioContext || window.webkitAudioContext;
    if (!stream || !Audio) { hint('此系统网页组件暂不支持流式试听；仍可等待并播放完整 WAV'); return; }
    try {
      var f = stream.format, rate = integer(f.sampleRate, 8000, 48000), channels = integer(f.channels, 1, 2), context = new Audio();
      var p = {id: id, rate: rate, channels: channels, cursor: 0, frames: 0, context: context, nextTime: context.currentTime + 0.1, sources: new Set(), abort: new AbortController(), timer: null}; playing = p;
      document.querySelector('[data-action="startAudioPreview"]').disabled = true; document.querySelector('[data-action="stopAudioPreview"]').disabled = false; hint('正在连接本机音频片段…');
      context.resume().then(function () { if (playing === p) pump(p); }).catch(function () { if (playing === p) stop('无法启动声音，请检查系统音频设置'); });
    } catch (error) { stop(error.message || '无法启动试听'); }
  }
  document.addEventListener('visibilitychange', function () { if (document.hidden && playing) stop('试听已暂停，模型继续在后台生成'); });
  window.addEventListener('pagehide', function () { stop(); });
  window.LMAAudioPreview = {
    init: function (bridge, callbacks) { ui = bridge; host = callbacks; }, summary: summary, close: function () { stop(); },
    handle: function (action, el) { if (action === 'audioPreview') { panel(el.dataset.id); return true; } if (action === 'startAudioPreview') { start(el.dataset.id); return true; } if (action === 'stopAudioPreview') { stop('已停止试听，模型继续生成'); return true; } return false; }
  };
})();
