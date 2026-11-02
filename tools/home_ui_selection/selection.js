(function () {
  'use strict';
  var data = window.LMA_DESIGN_DIRECTIONS || [], selected = [], storageKey = 'lma-home-ui-selection-20261103';
  var dialog = document.getElementById('viewer'), body = document.getElementById('viewerBody'), title = document.getElementById('viewerTitle');
  var noticeTimer;
  try { var saved = JSON.parse(localStorage.getItem(storageKey) || '[]'); if (Array.isArray(saved)) selected = saved.filter(function (id, index) { return data.some(function (d) { return d.id === id; }) && saved.indexOf(id) === index; }).slice(0, 3); } catch (_) {}
  function item(id) { return data.find(function (entry) { return entry.id === id; }); }
  function notice(message) { var target = document.getElementById('notice'); target.textContent = message; clearTimeout(noticeTimer); noticeTimer = setTimeout(function () { target.textContent = ''; }, 4500); }
  function update() {
    document.querySelectorAll('[data-select]').forEach(function (box) { box.checked = selected.indexOf(box.dataset.select) >= 0; box.closest('.design-card').classList.toggle('selected', box.checked); });
    document.getElementById('selectionSummary').textContent = selected.length ? '已选 ' + selected.map(function (id) { return id + ' ' + item(id).zh; }).join(' / ') : '尚未选择 · 可选最多 3 套';
    document.getElementById('compareSelection').disabled = !selected.length;
    document.getElementById('copySelection').disabled = !selected.length;
    try { localStorage.setItem(storageKey, JSON.stringify(selected)); } catch (_) {}
  }
  function show(ids) {
    body.replaceChildren(); body.className = ids.length === 1 ? 'single-view' : '';
    title.textContent = ids.length === 1 ? ids[0] + ' · ' + item(ids[0]).zh : '并排对比 · ' + ids.join(' / ');
    ids.forEach(function (id) {
      var entry = item(id), figure = document.createElement('figure'), img = document.createElement('img'), caption = document.createElement('figcaption');
      img.src = entry.file; img.alt = id + ' ' + entry.zh + ' 首页概念稿'; img.width = 1024; img.height = 1536;
      caption.textContent = id + ' · ' + entry.zh + ' / ' + entry.en + ' — ' + entry.signature;
      figure.append(img, caption); body.appendChild(figure);
      if (ids.length === 1) img.addEventListener('click', function () { body.classList.toggle('full-size'); });
    });
    dialog.showModal();
  }
  document.addEventListener('click', function (event) { var view = event.target.closest('[data-view]'); if (view && item(view.dataset.view)) show([view.dataset.view]); });
  document.addEventListener('change', function (event) {
    var box = event.target.closest('[data-select]'); if (!box) return;
    if (box.checked && selected.indexOf(box.dataset.select) < 0) {
      if (selected.length >= 3) { box.checked = false; notice('最多同时比较 3 套，请先取消一套。'); return; }
      selected.push(box.dataset.select);
    } else if (!box.checked) selected = selected.filter(function (id) { return id !== box.dataset.select; });
    selected.sort(); update();
  });
  document.getElementById('compareSelection').addEventListener('click', function () { if (selected.length) show(selected); });
  document.getElementById('closeViewer').addEventListener('click', function () { dialog.close(); });
  dialog.addEventListener('click', function (event) { if (event.target === dialog) { var rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });
  document.getElementById('clearSelection').addEventListener('click', function () { selected = []; update(); });
  document.getElementById('copySelection').addEventListener('click', async function () {
    var text = 'LMA 首页风格选择：' + selected.map(function (id) { return id + ' ' + item(id).zh + ' / ' + item(id).en; }).join('；');
    try { if (!navigator.clipboard || !window.isSecureContext) throw new Error('fallback'); await navigator.clipboard.writeText(text); notice('已复制选择，可以直接粘贴回复。'); }
    catch (_) { var field = document.createElement('textarea'); field.value = text; field.setAttribute('readonly', ''); field.style.position = 'fixed'; field.style.top = '0'; document.body.appendChild(field); field.select(); var ok = document.execCommand('copy'); field.remove(); if (ok) notice('已复制选择，可以直接粘贴回复。'); else window.prompt('请复制以下选择：', text); }
  });
  update();
})();
