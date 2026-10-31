(function () {
  'use strict';
  var labels = {any: '所有功能', text: '生文', image: '生图', video: '生视频', audio: '生音频', '3d': '生 3D'};
  function policy(state) { return state && state.recommendations || {}; }
  function entries(state) { var value = policy(state).entries; return Array.isArray(value) ? value : []; }
  window.LMARecommendations = {
    bind: function (model, state) {
      var text = policy(state).preservedTextIds || ['m08', 'm06', 'm01'];
      var rank = text.indexOf(model.id);
      if (!model.isBundle) return rank < 0 ? model : Object.assign({}, model, {recommendationOrder: rank});
      var list = entries(state), index = list.findIndex(function (item) { return item.bundleId === model.bundleId || item.bundleId === model.id; });
      if (index < 0) return model;
      return Object.assign({}, model, {recommended: true, recommendation: list[index], recommendationOrder: text.length + index});
    },
    compare: function (a, b) {
      return (a.recommendationOrder == null ? 1000 : a.recommendationOrder) - (b.recommendationOrder == null ? 1000 : b.recommendationOrder);
    },
    card: function (html, model) {
      if (!model.recommendation) return html;
      var item = model.recommendation, template = document.createElement('template');
      template.innerHTML = html;
      var article = template.content.querySelector('article');
      if (!article) return html;
      article.dataset.recommendedTask = item.task;
      var note = document.createElement('div'); note.className = 'recommendation-note';
      var badge = document.createElement('span'); badge.className = 'tag recommended'; badge.textContent = '推荐 · ' + item.reason;
      var hint = document.createElement('p'); hint.textContent = item.hint;
      note.appendChild(badge); note.appendChild(hint); article.appendChild(note);
      return template.innerHTML;
    },
    counts: function (models, active, enabled) {
      var counts = {any: 0, text: 0, image: 0, video: 0, audio: 0, '3d': 0};
      models.filter(function (model) { return model.recommended; }).forEach(function (model) {
        counts.any++;
        var task = model.recommendation && model.recommendation.task || (!model.isBundle ? 'text' : '');
        if (task in counts) counts[task]++;
      });
      document.querySelectorAll('[data-task]').forEach(function (button) {
        var task = button.dataset.task; if (!(task in labels)) return;
        var signature = labels[task] + ':' + (active && enabled ? counts[task] : 'off');
        if (button.dataset.recommendationCount === signature) return; button.dataset.recommendationCount = signature;
        button.textContent = labels[task]; button.removeAttribute('aria-label');
        if (!active || !enabled) return;
        var count = document.createElement('span'); count.className = 'recommendation-count'; count.textContent = String(counts[task]);
        button.appendChild(count); button.setAttribute('aria-label', labels[task] + '，' + counts[task] + ' 个推荐模型');
      });
    }
  };
}());
