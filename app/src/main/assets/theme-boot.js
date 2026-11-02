(function () {
  'use strict';
  var choice = 'dark';
  try { if (window.Android && window.Android.themePreference) choice = window.Android.themePreference(); } catch (_) {}
  if (['dark', 'light', 'system'].indexOf(choice) < 0) choice = 'dark';
  var dark = choice === 'dark' || (choice === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  document.documentElement.style.background = dark ? '#121a29' : '#f5f7fa';
}());
