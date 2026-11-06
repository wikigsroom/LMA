(function () {
  'use strict';
  var ui, last = '', current = 'chat', wide = window.matchMedia('(min-width:1080px)'), open = wide.matches;
  var root = document.documentElement, sidebar = document.getElementById('workspaceSidebar'), toggle = document.getElementById('sidebarToggle');
  var titles = {chat:'对话',models:'模型库',tasks:'任务与作品',server:'API 服务',settings:'设置'};
  function drawer() { return open && !wide.matches; }
  function update() {
    root.dataset.sidebar = open ? 'expanded' : 'collapsed';
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? '收起侧边栏' : '展开侧边栏');
    sidebar.setAttribute('role', drawer() ? 'dialog' : 'complementary');
    if (drawer()) sidebar.setAttribute('aria-modal', 'true'); else sidebar.removeAttribute('aria-modal');
    document.getElementById('main').inert = drawer();
    document.querySelector('.topbar').inert = drawer();
    document.getElementById('errorBanner').inert = drawer();
  }
  function collapse(restore) {
    if (!drawer()) return false;
    open = false; update();
    if (restore) toggle.focus();
    return true;
  }
  function receive() {
    if (!ui) return;
    var chat = ui.state().chat || {}, sessions = chat.sessions || [];
    var signature = JSON.stringify([chat.sessionId, sessions.map(function(s){return [s.id,s.title];})]);
    var selected = sessions.find(function(s){return s.id === chat.sessionId;});
    document.getElementById('workspaceChatTitle').textContent = selected && selected.title || '新对话';
    document.getElementById('page-chat').classList.toggle('is-empty', !(chat.messages || []).length);
    if (last === signature) return; last = signature;
    var list = document.getElementById('sidebarSessions');
    list.replaceChildren();
    sessions.slice(0, 24).forEach(function(s) {
      var button = document.createElement('button'), label = document.createElement('span');
      button.type = 'button'; button.className = 'sidebar-session'; button.dataset.action = 'selectSession'; button.dataset.id = s.id;
      if (s.id === chat.sessionId) button.setAttribute('aria-current', 'true');
      label.textContent = s.title || '未命名对话'; button.title = label.textContent; button.append(label); list.append(button);
    });
    if (!sessions.length) {var empty = document.createElement('p'); empty.className = 'sidebar-empty'; empty.textContent = '从新对话开始，记录会保存在当前手机。'; list.append(empty);}
  }
  document.addEventListener('click', function(event) {
    var button = event.target.closest('[data-workspace="toggle"]');
    if (button) {open = !open; update(); return;}
    if (drawer() && event.target.closest('[data-action]')) collapse(false);
  }, true);
  document.addEventListener('keydown', function(event) {
    if (!drawer()) return;
    if (event.key === 'Escape') {event.preventDefault(); event.stopImmediatePropagation(); collapse(true); return;}
    if (event.key !== 'Tab') return;
    var buttons = Array.from(sidebar.querySelectorAll('button,a[href]')).filter(function(e){return !e.disabled && e.getClientRects().length;});
    var first = buttons[0], end = buttons[buttons.length-1];
    if (event.shiftKey && (document.activeElement === first || !sidebar.contains(document.activeElement))) {event.preventDefault(); end.focus();}
    else if (!event.shiftKey && (document.activeElement === end || !sidebar.contains(document.activeElement))) {event.preventDefault(); first.focus();}
  }, true);
  function resize() {open = wide.matches; update();}
  if (wide.addEventListener) wide.addEventListener('change', resize); else wide.addListener(resize);
  window.LMAWorkspace = {
    init:function(bridge) {ui = bridge; update(); receive();},
    receive:receive,
    route:function(next) {current = next; document.getElementById('workspacePageTitle').textContent = titles[current]; collapse(false); receive();},
    back:function() {return collapse(true);}
  };
  update();
}());
